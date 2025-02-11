#!/usr/bin/env bash
set -euo pipefail

progname="$0"

# Default number of cores to use
numcores=$(nproc || sysctl -n hw.ncpu || echo 1)
numcores=$((numcores > 1 ? numcores - 1 : 1))

function usage {
    echo "Usage:"
    echo "  $progname --create-snapshot <snapshot_name>"
    echo "  $progname --restore-snapshot <snapshot_file>"
    echo ""
    echo "Environment variables:"
    echo "  Database credentials (from cardano-rosetta-java env):"
    echo "    DB_HOST     - Database host"
    echo "    DB_PORT     - Database port"
    echo "    DB_NAME     - Database name"
    echo "    DB_USER     - Database user"
    echo "    DB_SECRET   - Database password"
    echo "  Optional:"
    echo "    NETWORK     - Network name corresponding to the schema (e.g., mainnet, preprod, preview)"
    echo "                  Defaults to 'public' if not set."
    echo ""
    echo "  For restoration (if SNAPSHOT_URL is used):"
    echo "    SNAPSHOT_URL - URL to the snapshot file"
    exit 1
}

function check_db_credentials {
    # Ensure all required environment variables are set
    if [ -z "${DB_HOST:-}" ] || [ -z "${DB_PORT:-}" ] || [ -z "${DB_NAME:-}" ] || [ -z "${DB_USER:-}" ] || [ -z "${DB_SECRET:-}" ]; then
        echo "Error: Database credentials not provided."
        echo "Please set the following environment variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_SECRET."
        exit 1
    fi

    # Export variables in the format expected by PostgreSQL tools
    export PGHOST="$DB_HOST"
    export PGPORT="$DB_PORT"
    export PGDATABASE="$DB_NAME"
    export PGUSER="$DB_USER"
    export PGPASSWORD="$DB_SECRET"
}

function check_commands {
    for cmd in pg_dump pg_restore dropdb createdb tar gzip; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: $cmd command not found"
            exit 1
        fi
    done
}

function create_snapshot {
    snapshot_name="$1"
    schema_name="${NETWORK:-public}"

    if [ -z "$snapshot_name" ]; then
        echo "Snapshot name not specified"
        exit 1
    fi

    echo "Creating database snapshot..."
    echo "Schema: $schema_name"

    # Use /node/postgres as the temporary directory
    tmp_dir=$(mktemp -d -p /node/postgres -t db-snapshot-XXXXXXXXXX)
    echo "Working directory: ${tmp_dir}"

    # Dump the database in directory format
    pg_dump --no-owner --schema="$schema_name" --jobs="${numcores}" --format=directory --file="${tmp_dir}/db_dump" "$PGDATABASE"

    # Create a tarball of the dump
    tar -C "$tmp_dir" -czf "${snapshot_name}.tar.gz" .
    echo "Snapshot saved to ${snapshot_name}.tar.gz"

    # Clean up temporary directory
    rm -rf "$tmp_dir"
}

function restore_snapshot {
    snapshot_file="$1"
    schema_name="${NETWORK:-public}"

    if [ -z "${SNAPSHOT_URL:-}" ] && [ -z "$snapshot_file" ]; then
        echo "Error: SNAPSHOT_URL environment variable not set and no snapshot file provided"
        exit 1
    fi

    if [ -n "${SNAPSHOT_URL:-}" ]; then
        echo "Downloading snapshot from $SNAPSHOT_URL..."
        tmp_file=$(mktemp -p /node/postgres)
        function cleanup {
            rm -f "$tmp_file"
        }
        trap cleanup EXIT
        curl -L "$SNAPSHOT_URL" -o "$tmp_file"
        snapshot_file="$tmp_file"
    fi

    if [ ! -f "$snapshot_file" ]; then
        echo "Error: Snapshot file $snapshot_file does not exist"
        exit 1
    fi

    echo "Restoring database snapshot from $snapshot_file..."
    echo "Schema: $schema_name"

    # Use /node/postgres as the temporary directory
    tmp_dir=$(mktemp -d -p /node/postgres -t db-restore-XXXXXXXXXX)
    echo "Working directory: ${tmp_dir}"

    # Extract the snapshot
    tar -xzf "$snapshot_file" -C "$tmp_dir"

    # Drop the existing database
    sudo -u postgres dropdb "$PGDATABASE" || true
    sudo -u postgres createdb "$PGDATABASE"

    # Give postgres user ownership of the working directory
    chown -R postgres:postgres "$tmp_dir"

    # Note: I think this is not enough to drop the database.
    # I probably need to initialize the db as done in the entrypoint.sh

    # Restore the database
    pg_restore -l "${tmp_dir}/db_dump"
    pg_restore \
        --role="$PGUSER" \
        --schema="$schema_name" \
        --jobs="${numcores}" \
        --format=directory \
        --dbname="$PGDATABASE" \
        #--no-owner \
        --exit-on-error \
        "${tmp_dir}/db_dump"

    echo "Database restored successfully"

    # Clean up temporary directory
    rm -rf "$tmp_dir"

    echo "Snapshot restoration completed"
}

if [ $# -lt 1 ]; then
    usage
fi

check_db_credentials
check_commands

case "$1" in
    --create-snapshot)
        if [ $# -ne 2 ]; then
            usage
        fi
        snapshot_name="$2"
        create_snapshot "$snapshot_name"
        ;;
    --restore-snapshot)
        if [ $# -eq 2 ]; then
            snapshot_file="$2"
        else
            snapshot_file=""
        fi
        restore_snapshot "$snapshot_file"
        ;;
    *)
        usage
        ;;
esac