#!/usr/bin/env python3
# /// script
# dependencies = ["psycopg[binary]"]
# requires-python = ">=3.11"
# ///
"""
Benchmark index creation for cardano-rosetta-java.

Creates indexes one-by-one, monitors progress, and records timing/sizes.
Outputs results in markdown table format.
"""

import argparse
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime

import psycopg

# Index definitions grouped by migration file
INDEXES = {
    "V1.0_500_0 (transaction)": [
        ("idx_transaction_block", "CREATE INDEX idx_transaction_block ON transaction(block)"),
        ("idx_transaction_block_hash", "CREATE INDEX idx_transaction_block_hash ON transaction(block_hash)"),
    ],
    "V1.0_600_0 (withdrawal)": [
        ("idx_withdrawal_address", "CREATE INDEX idx_withdrawal_address ON withdrawal(address)"),
        ("idx_withdrawal_tx_hash", "CREATE INDEX idx_withdrawal_tx_hash ON withdrawal(tx_hash)"),
    ],
    "V1.0_900_0 (address_utxo)": [
        ("idx_address_utxo_tx_hash", "CREATE INDEX idx_address_utxo_tx_hash ON address_utxo USING btree (tx_hash)"),
    ],
    "V1.0_2500_0 (search)": [
        ("idx_address_utxo_amounts_gin", "CREATE INDEX idx_address_utxo_amounts_gin ON address_utxo USING gin (amounts)"),
        ("idx_address_utxo_owner_addr_tx_hash", "CREATE INDEX idx_address_utxo_owner_addr_tx_hash ON address_utxo USING btree (owner_addr, tx_hash)"),
        ("idx_block_hash_covering", "CREATE INDEX idx_block_hash_covering ON block USING btree (hash) INCLUDE (number, slot)"),
        ("idx_invalid_transaction_hash_slot", "CREATE INDEX idx_invalid_transaction_hash_slot ON invalid_transaction USING btree (tx_hash, slot)"),
        ("idx_transaction_hash_values_join", "CREATE INDEX idx_transaction_hash_values_join ON transaction USING btree (tx_hash)"),
        ("idx_transaction_slot_desc_tx_index_desc", "CREATE INDEX idx_transaction_slot_desc_tx_index_desc ON transaction USING btree (slot DESC, tx_index DESC)"),
    ],
    # Missing indexes identified comparing v2.0 with v1.4.3 (caused ~85,000x slowdown on stake address queries)
    "V1.0_3000_0 (v1.4.3 parity)": [
        ("idx_address_utxo_owner_stake_addr", "CREATE INDEX idx_address_utxo_owner_stake_addr ON address_utxo USING btree (owner_stake_addr)"),
        ("idx_address_utxo_owner_addr", "CREATE INDEX idx_address_utxo_owner_addr ON address_utxo USING btree (owner_addr)"),
        ("idx_address_utxo_owner_paykey_hash", "CREATE INDEX idx_address_utxo_owner_paykey_hash ON address_utxo USING btree (owner_payment_credential)"),
        ("idx_address_utxo_owner_stakekey_hash", "CREATE INDEX idx_address_utxo_owner_stakekey_hash ON address_utxo USING btree (owner_stake_credential)"),
        ("idx_address_utxo_epoch", "CREATE INDEX idx_address_utxo_epoch ON address_utxo USING btree (epoch)"),
    ],
}


@dataclass
class IndexResult:
    name: str
    duration_seconds: float
    size_bytes: int
    size_pretty: str
    error: str | None = None


class DatabaseConfig:
    """Holds database configuration for a single benchmark run."""

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str, schema: str = "public"):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.schema = schema

    def get_connection(self, autocommit: bool = False):
        """Create a new database connection."""
        return psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            autocommit=autocommit,
        )


def index_exists(conn, index_name: str, schema: str) -> bool:
    """Check if an index already exists."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = %s AND schemaname = %s",
            (index_name, schema),
        )
        return cur.fetchone() is not None


def get_index_size(conn, index_name: str, schema: str) -> tuple[int, str]:
    """Get index size in bytes and pretty-printed."""
    with conn.cursor() as cur:
        qualified_name = f"{schema}.{index_name}"
        cur.execute(
            """
            SELECT pg_relation_size(%s::regclass),
                   pg_size_pretty(pg_relation_size(%s::regclass))
            """,
            (qualified_name, qualified_name),
        )
        row = cur.fetchone()
        return row[0], row[1]


def monitor_progress(db_config: DatabaseConfig, index_name: str, stop_event: threading.Event):
    """Monitor index creation progress in a separate thread."""
    conn = db_config.get_connection(autocommit=True)

    try:
        while not stop_event.is_set():
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        phase,
                        blocks_total,
                        blocks_done,
                        tuples_total,
                        tuples_done
                    FROM pg_stat_progress_create_index
                """)
                row = cur.fetchone()

                if row:
                    phase, blocks_total, blocks_done, tuples_total, tuples_done = row
                    blocks_pct = (100.0 * blocks_done / blocks_total) if blocks_total else 0
                    tuples_pct = (100.0 * tuples_done / tuples_total) if tuples_total else 0
                    print(f"\r  [{index_name}] {phase}: blocks {blocks_pct:.1f}%, tuples {tuples_pct:.1f}%", end="", flush=True)

            stop_event.wait(60)  # Poll every 60 seconds
    finally:
        conn.close()


def create_index(db_config: DatabaseConfig, index_name: str, create_sql: str, show_progress: bool = True) -> IndexResult:
    """Create a single index and return timing/size results."""
    conn = db_config.get_connection(autocommit=True)  # Required for CREATE INDEX without transaction

    # Check if index already exists
    if index_exists(conn, index_name, db_config.schema):
        size_bytes, size_pretty = get_index_size(conn, index_name, db_config.schema)
        print(f"  {index_name}: already exists ({size_pretty})")
        conn.close()
        return IndexResult(
            name=index_name,
            duration_seconds=0,
            size_bytes=size_bytes,
            size_pretty=size_pretty,
            error="already exists",
        )

    # Start progress monitor thread
    stop_event = threading.Event()
    monitor_thread = None
    if show_progress:
        monitor_thread = threading.Thread(
            target=monitor_progress,
            args=(db_config, index_name, stop_event),
            daemon=True,
        )
        monitor_thread.start()

    print(f"  {index_name}: creating...", end="", flush=True)
    start_time = time.time()
    error = None

    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
    except Exception as e:
        error = str(e)
        print(f"\n  ERROR: {error}")
    finally:
        stop_event.set()
        if monitor_thread:
            monitor_thread.join(timeout=1)

    duration = time.time() - start_time

    if error:
        conn.close()
        return IndexResult(
            name=index_name,
            duration_seconds=duration,
            size_bytes=0,
            size_pretty="N/A",
            error=error,
        )

    size_bytes, size_pretty = get_index_size(conn, index_name, db_config.schema)
    conn.close()

    print(f"\r  {index_name}: {format_duration(duration)} ({size_pretty})" + " " * 40)

    return IndexResult(
        name=index_name,
        duration_seconds=duration,
        size_bytes=size_bytes,
        size_pretty=size_pretty,
    )


def qualify_table_names(create_sql: str, schema: str) -> str:
    """Add schema qualification to table names in CREATE INDEX statements."""
    import re

    # Pattern to match table names after ON keyword (handles both regular and USING clauses)
    # Example: "ON transaction(" or "ON address_utxo USING"
    pattern = r'\bON\s+(\w+)(\s+USING|\()'

    def replace_match(match):
        table_name = match.group(1)
        suffix = match.group(2)
        return f"ON {schema}.{table_name}{suffix}"

    return re.sub(pattern, replace_match, create_sql, flags=re.IGNORECASE)


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def output_markdown_table(results: list[IndexResult], total_duration: float):
    """Output results as markdown table matching the task template."""
    print("\n" + "=" * 60)
    print("RESULTS (Markdown format)")
    print("=" * 60 + "\n")

    print("| Metric | Value |")
    print("|--------|-------|")
    print("| Sync time (no indexes) | |")

    total_size = 0
    for r in results:
        duration_str = format_duration(r.duration_seconds) if not r.error else f"({r.error})"
        size_str = r.size_pretty if r.size_pretty != "N/A" else "-"
        print(f"| `{r.name}` | {duration_str} / {size_str} |")
        total_size += r.size_bytes

    print(f"| **Total index creation** | {format_duration(total_duration)} / {format_size(total_size)} |")
    print("| Concurrent vs sequential | |")


def extract_table_name(create_sql: str) -> str:
    """Extract table name from CREATE INDEX statement."""
    import re
    # Match: ON schema.table or ON table
    match = re.search(r'\bON\s+(?:\w+\.)?(\w+)', create_sql, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def run_sequential(db_config: DatabaseConfig, use_concurrently: bool = False, dry_run: bool = False):
    """Create all indexes sequentially (one at a time)."""
    results = []
    total_start = time.time()

    for group_name, indexes in INDEXES.items():
        print(f"\n{group_name}:")
        for index_name, create_sql in indexes:
            # Qualify table names with schema
            qualified_sql = qualify_table_names(create_sql, db_config.schema)

            # Add CONCURRENTLY keyword if requested
            if use_concurrently:
                qualified_sql = qualified_sql.replace("CREATE INDEX ", "CREATE INDEX CONCURRENTLY ")

            if dry_run:
                print(f"  [DRY RUN] Would create: {index_name}")
                print(f"    SQL: {qualified_sql}")
            else:
                result = create_index(db_config, index_name, qualified_sql)
                results.append(result)

    total_duration = time.time() - total_start

    if not dry_run:
        output_markdown_table(results, total_duration)

    return results


def run_parallel(db_config: DatabaseConfig, use_concurrently: bool = False, dry_run: bool = False):
    """Create all indexes in parallel (all at once, separate connections)."""
    results = []
    total_start = time.time()

    # Flatten all indexes
    all_indexes = []
    for group_name, indexes in INDEXES.items():
        for index_name, create_sql in indexes:
            # Qualify table names with schema
            qualified_sql = qualify_table_names(create_sql, db_config.schema)

            # Add CONCURRENTLY keyword if requested
            if use_concurrently:
                qualified_sql = qualified_sql.replace("CREATE INDEX ", "CREATE INDEX CONCURRENTLY ")

            all_indexes.append((index_name, qualified_sql))

    if dry_run:
        mode = "concurrently" if use_concurrently else "in parallel"
        for index_name, create_sql in all_indexes:
            print(f"[DRY RUN] Would create {mode}: {index_name}")
            print(f"  SQL: {create_sql}")
        return []

    threads = []
    results_lock = threading.Lock()

    def create_and_store(index_name, create_sql):
        result = create_index(db_config, index_name, create_sql, show_progress=False)
        with results_lock:
            results.append(result)

    mode = "concurrent (non-blocking)" if use_concurrently else "parallel (blocking writes)"
    print(f"\nStarting {mode} index creation...")
    for index_name, create_sql in all_indexes:
        t = threading.Thread(target=create_and_store, args=(index_name, create_sql))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_duration = time.time() - total_start

    # Sort results by name for consistent output
    results.sort(key=lambda r: r.name)
    output_markdown_table(results, total_duration)

    return results


def run_parallel_grouped(db_config: DatabaseConfig, use_concurrently: bool = False, dry_run: bool = False):
    """Create indexes in parallel, but grouped by table to avoid contention."""
    results = []
    total_start = time.time()

    # Group indexes by table
    from collections import defaultdict
    indexes_by_table = defaultdict(list)

    for group_name, indexes in INDEXES.items():
        for index_name, create_sql in indexes:
            qualified_sql = qualify_table_names(create_sql, db_config.schema)

            if use_concurrently:
                qualified_sql = qualified_sql.replace("CREATE INDEX ", "CREATE INDEX CONCURRENTLY ")

            table_name = extract_table_name(qualified_sql)
            indexes_by_table[table_name].append((index_name, qualified_sql))

    if dry_run:
        mode = "concurrently" if use_concurrently else "in parallel"
        print(f"[DRY RUN] Would create {mode}, grouped by table:")
        for table_name, table_indexes in indexes_by_table.items():
            print(f"\n  Table: {table_name}")
            for index_name, create_sql in table_indexes:
                print(f"    - {index_name}")
        return []

    mode = "concurrent (non-blocking)" if use_concurrently else "parallel (blocking writes)"
    print(f"\nStarting {mode} index creation, grouped by table...")

    results_lock = threading.Lock()

    def create_table_indexes(table_name, table_indexes):
        """Create all indexes for a table sequentially."""
        print(f"\n[Thread] Processing table: {table_name} ({len(table_indexes)} indexes)")
        for index_name, create_sql in table_indexes:
            result = create_index(db_config, index_name, create_sql, show_progress=False)
            with results_lock:
                results.append(result)

    # Launch one thread per table
    threads = []
    for table_name, table_indexes in indexes_by_table.items():
        t = threading.Thread(target=create_table_indexes, args=(table_name, table_indexes))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_duration = time.time() - total_start

    # Sort results by name for consistent output
    results.sort(key=lambda r: r.name)
    output_markdown_table(results, total_duration)

    return results


def list_existing_indexes(db_config: DatabaseConfig):
    """List all existing indexes matching our patterns."""
    conn = db_config.get_connection(autocommit=True)

    print("\nExisting indexes:")
    print("-" * 60)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT indexname,
                   pg_size_pretty(pg_relation_size((schemaname || '.' || indexname)::regclass)) AS size
            FROM pg_indexes
            WHERE schemaname = %s
              AND (indexname LIKE 'idx_transaction%%'
                   OR indexname LIKE 'idx_withdrawal%%'
                   OR indexname LIKE 'idx_address_utxo%%'
                   OR indexname LIKE 'idx_block%%'
                   OR indexname LIKE 'idx_invalid%%')
            ORDER BY indexname
        """, (db_config.schema,))

        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

    conn.close()


def drop_indexes(db_config: DatabaseConfig, dry_run: bool = False):
    """Drop all benchmark indexes (for re-testing)."""
    conn = db_config.get_connection(autocommit=True)

    all_index_names = []
    for group_name, indexes in INDEXES.items():
        for index_name, _ in indexes:
            all_index_names.append(index_name)

    print("\nDropping indexes:")
    for index_name in all_index_names:
        if index_exists(conn, index_name, db_config.schema):
            if dry_run:
                print(f"  [DRY RUN] Would drop: {index_name}")
            else:
                print(f"  Dropping {index_name}...")
                with conn.cursor() as cur:
                    qualified_name = f"{db_config.schema}.{index_name}"
                    cur.execute(f"DROP INDEX IF EXISTS {qualified_name}")
                print(f"  Dropped {index_name}")
        else:
            print(f"  {index_name}: does not exist")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark index creation for cardano-rosetta-java",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List existing indexes
  python benchmark_indexes.py --list

  # Dry run to see what would be created
  python benchmark_indexes.py --dry-run

  # Scenario 1: Sequential, blocks writes (default)
  python benchmark_indexes.py --strategy sequential

  # Scenario 2: Sequential, non-blocking
  python benchmark_indexes.py --strategy sequential --concurrently

  # Scenario 3: Parallel, blocks writes
  python benchmark_indexes.py --strategy parallel

  # Scenario 4: Parallel, non-blocking
  python benchmark_indexes.py --strategy parallel --concurrently

  # Scenario 5: Parallel grouped by table, non-blocking
  python benchmark_indexes.py --strategy parallel-grouped --concurrently

  # Drop all benchmark indexes (to re-run test)
  python benchmark_indexes.py --drop

Strategy explanation:
  sequential        - Create indexes one at a time (predictable, no lock contention)
  parallel          - Create all indexes at once (faster wall-clock time, higher resource usage)
  parallel-grouped  - Create indexes in parallel, but per-table sequential (balanced approach)

Concurrently flag:
  --concurrently    - Use CREATE INDEX CONCURRENTLY (allows writes, 2-3x slower creation)
  (no flag)         - Use regular CREATE INDEX (blocks writes, faster creation)
        """,
    )

    parser.add_argument("--host", default=os.getenv("DB_HOST", "localhost"), help="Database host")
    parser.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "5432")), help="Database port")
    parser.add_argument("--dbname", default=os.getenv("DB_NAME", "rosetta-java"), help="Database name")
    parser.add_argument("--user", default=os.getenv("DB_USER", "rosetta_db_admin"), help="Database user")
    parser.add_argument("--password", default=os.getenv("DB_SECRET", "weakpwd#123_d"), help="Database password")
    parser.add_argument("--schema", default=os.getenv("DB_SCHEMA", "public"), help="Database schema")

    parser.add_argument("--list", action="store_true", help="List existing indexes and exit")
    parser.add_argument("--drop", action="store_true", help="Drop all benchmark indexes")
    parser.add_argument(
        "--strategy",
        choices=["sequential", "parallel", "parallel-grouped"],
        default="sequential",
        help="Index creation strategy (default: sequential)"
    )
    parser.add_argument(
        "--concurrently",
        action="store_true",
        help="Use CREATE INDEX CONCURRENTLY (non-blocking, slower)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")

    args = parser.parse_args()

    db_config = DatabaseConfig(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password,
        schema=args.schema,
    )

    print(f"Database: {args.user}@{args.host}:{args.port}/{args.dbname} (schema: {args.schema})")
    print(f"Strategy: {args.strategy}" + (" + CONCURRENTLY" if args.concurrently else ""))
    print(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Test connection
        conn = db_config.get_connection(autocommit=True)
        conn.close()
        print("Connection: OK\n")
    except Exception as e:
        print(f"Connection FAILED: {e}")
        sys.exit(1)

    if args.list:
        list_existing_indexes(db_config)
    elif args.drop:
        drop_indexes(db_config, dry_run=args.dry_run)
    elif args.strategy == "sequential":
        run_sequential(db_config, use_concurrently=args.concurrently, dry_run=args.dry_run)
    elif args.strategy == "parallel":
        run_parallel(db_config, use_concurrently=args.concurrently, dry_run=args.dry_run)
    elif args.strategy == "parallel-grouped":
        run_parallel_grouped(db_config, use_concurrently=args.concurrently, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
