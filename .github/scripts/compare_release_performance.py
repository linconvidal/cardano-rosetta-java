#!/usr/bin/env python3
"""Compare a candidate CSV with an exact performance table published under docs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


EXPECTED_ENDPOINT_COUNT = 8
METRIC_FIELDS = {
    "ID",
    "Endpoint",
    "Max_Concurrency",
    "p95(ms)",
    "p99(ms)",
    "Non_2xx_Responses",
    "Error_Rate(%)",
    "Requests_per_sec",
}
PUBLISHED_HEADERS = {
    "ID": "ID",
    "Endpoint": "Endpoint",
    "Max Concurrency": "Max_Concurrency",
    "p95 (ms)": "p95(ms)",
    "p99 (ms)": "p99(ms)",
    "Non-2xx": "Non_2xx_Responses",
    "Error Rate (%)": "Error_Rate(%)",
    "Reqs/sec": "Requests_per_sec",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-doc", type=Path, required=True)
    parser.add_argument("--stable-tag", required=True)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--candidate-tag")
    parser.add_argument("--deployment")
    parser.add_argument("--documentation-name")
    parser.add_argument("--expected-hardware-profile")
    parser.add_argument("--allow-missing-baseline", action="store_true")
    parser.add_argument("--check-baseline-only", action="store_true")
    return parser.parse_args()


def number(value: str) -> float:
    return float(value.strip().removesuffix("ms").removesuffix("%"))


def endpoint_labels(rows: list[dict[str, str]]) -> list[str]:
    search_occurrence = 0
    labels: list[str] = []
    for row in rows:
        endpoint = row["Endpoint"]
        if endpoint == "/search/transactions":
            search_occurrence += 1
            suffix = "by hash" if search_occurrence == 1 else "by address"
            endpoint = f"{endpoint} ({suffix})"
        labels.append(endpoint)
    return labels


def validate_metrics(rows: list[dict[str, str]], source: Path) -> None:
    if len(rows) != EXPECTED_ENDPOINT_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_ENDPOINT_COUNT} endpoints in {source}, found {len(rows)}"
        )
    missing = METRIC_FIELDS.difference(rows[0])
    if missing:
        raise ValueError(f"Missing columns in {source}: {', '.join(sorted(missing))}")

    labels = endpoint_labels(rows)
    if len(set(labels)) != EXPECTED_ENDPOINT_COUNT:
        raise ValueError(f"Duplicate endpoint labels in {source}")

    for row in rows:
        if int(row["Max_Concurrency"]) <= 0:
            raise ValueError(
                f"No passing concurrency recorded for {row['Endpoint']} in {source}"
            )
        if number(row["Requests_per_sec"]) <= 0:
            raise ValueError(f"No throughput recorded for {row['Endpoint']} in {source}")


def read_candidate_csv(
    path: Path,
    expected_release: str,
    expected_hardware_profile: str | None,
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        # Read the header separately, so a run that aborted after writing only
        # the header reports what is wrong instead of raising IndexError.
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    required = METRIC_FIELDS | {"Release", "Hardware_Profile", "Machine_Specs"}
    missing = required.difference(fieldnames)
    if missing:
        raise ValueError(f"Missing columns in {path}: {', '.join(sorted(missing))}")

    if not rows:
        raise ValueError(f"No result rows in {path}.")

    releases = {row["Release"] for row in rows}
    if releases != {expected_release}:
        raise ValueError(
            f"Expected release {expected_release} in {path}, found {', '.join(sorted(releases))}"
        )

    profiles = {row["Hardware_Profile"] for row in rows}
    if len(profiles) != 1:
        raise ValueError(f"Mixed hardware profiles in {path}: {', '.join(sorted(profiles))}")
    if expected_hardware_profile is not None and profiles != {expected_hardware_profile}:
        raise ValueError(
            f"Expected hardware profile {expected_hardware_profile} in {path}, "
            f"found {', '.join(sorted(profiles))}"
        )

    machine_specs = {row["Machine_Specs"] for row in rows}
    if len(machine_specs) != 1:
        raise ValueError(f"Mixed machine specs in {path}: {', '.join(sorted(machine_specs))}")

    validate_metrics(rows, path)
    return rows


def markdown_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def read_published_doc(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        headers = markdown_cells(line)
        if headers != list(PUBLISHED_HEADERS):
            continue
        if index + 1 >= len(lines):
            break

        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            cells = markdown_cells(row_line)
            if not cells:
                if rows:
                    break
                continue
            if len(cells) != len(headers):
                raise ValueError(f"Invalid published table row in {path}: {row_line}")
            rows.append(
                {
                    PUBLISHED_HEADERS[header]: value
                    for header, value in zip(headers, cells, strict=True)
                }
            )
        validate_metrics(rows, path)
        return rows

    raise ValueError(f"Published performance table not found in {path}")


def delta(previous: float, current: float) -> str:
    if previous == 0:
        return "n/a"
    return f"{((current - previous) / previous) * 100:+.1f}%"


def doc_table(rows: list[dict[str, str]]) -> str:
    labels = endpoint_labels(rows)
    lines = [
        f"- **Hardware Profile:** {rows[0]['Hardware_Profile']}",
        f"- **Machine Specs:** {rows[0]['Machine_Specs']}",
        "",
        "The performance metrics in this table were measured against an SLA of 1000 ms.",
        "",
        "| ID | Endpoint | Max Concurrency | p95 (ms) | p99 (ms) | Non-2xx | Error Rate (%) | Reqs/sec |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row, label in zip(rows, labels, strict=True):
        lines.append(
            "| {id} | {endpoint} | {max_concurrency} | {p95} | {p99} | "
            "{non_2xx} | {error_rate} | {requests_per_sec} |".format(
                id=row["ID"],
                endpoint=label,
                max_concurrency=row["Max_Concurrency"],
                p95=row["p95(ms)"].removesuffix("ms"),
                p99=row["p99(ms)"].removesuffix("ms"),
                non_2xx=row["Non_2xx_Responses"],
                error_rate=row["Error_Rate(%)"],
                requests_per_sec=row["Requests_per_sec"],
            )
        )
    return "\n".join(lines) + "\n"


def comparison_table(
    baseline: list[dict[str, str]],
    candidate: list[dict[str, str]],
    stable_tag: str,
    deployment: str,
    baseline_path: Path,
) -> str:
    baseline_labels = endpoint_labels(baseline)
    candidate_labels = endpoint_labels(candidate)
    if baseline_labels != candidate_labels:
        raise ValueError("Published baseline and candidate endpoint order differs")

    lines = [
        f"# Performance comparison: {deployment}",
        "",
        f"- Stable: `{stable_tag}`",
        f"- Candidate: `{candidate[0]['Release']}`",
        f"- Published baseline: `{baseline_path}`",
        f"- Machine: `{candidate[0]['Machine_Specs']}`",
        "- Decision: manual review required",
        "",
        "Positive latency deltas are slower. Positive concurrency and throughput deltas are higher.",
        "",
        "| Endpoint | Stable max | Candidate max | Max delta | Stable p95 | Candidate p95 | p95 delta | Stable p99 | Candidate p99 | p99 delta | Stable req/s | Candidate req/s | Req/s delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for old, new, label in zip(baseline, candidate, baseline_labels, strict=True):
        old_max = number(old["Max_Concurrency"])
        new_max = number(new["Max_Concurrency"])
        old_p95 = number(old["p95(ms)"])
        new_p95 = number(new["p95(ms)"])
        old_p99 = number(old["p99(ms)"])
        new_p99 = number(new["p99(ms)"])
        old_rps = number(old["Requests_per_sec"])
        new_rps = number(new["Requests_per_sec"])
        lines.append(
            f"| {label} | {old_max:g} | {new_max:g} | {delta(old_max, new_max)} | "
            f"{old_p95:g} | {new_p95:g} | {delta(old_p95, new_p95)} | "
            f"{old_p99:g} | {new_p99:g} | {delta(old_p99, new_p99)} | "
            f"{old_rps:g} | {new_rps:g} | {delta(old_rps, new_rps)} |"
        )

    lines.extend(
        [
            "",
            "## Reliability",
            "",
            "| Endpoint | Stable non-2xx | Candidate non-2xx | Stable error rate | Candidate error rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for old, new, label in zip(baseline, candidate, baseline_labels, strict=True):
        lines.append(
            f"| {label} | {old['Non_2xx_Responses']} | {new['Non_2xx_Responses']} | "
            f"{old['Error_Rate(%)']} | {new['Error_Rate(%)']} |"
        )

    return "\n".join(lines) + "\n"


def missing_baseline_report(
    candidate: list[dict[str, str]],
    stable_tag: str,
    deployment: str,
    baseline_path: Path,
) -> str:
    return "\n".join(
        [
            f"# Performance comparison: {deployment}",
            "",
            f"- Stable: `{stable_tag}`",
            f"- Candidate: `{candidate[0]['Release']}`",
            f"- Expected published baseline: `{baseline_path}`",
            f"- Machine: `{candidate[0]['Machine_Specs']}`",
            "- Decision: published baseline unavailable",
            "",
            "## Published baseline unavailable",
            "",
            "The candidate result is valid for publication, but no historical regression comparison was performed.",
            "This is allowed for the first published result for this deployment.",
            "",
        ]
    )


def validate_documentation_name(name: str) -> str:
    path = Path(name)
    if path.name != name or path.suffix != ".md":
        raise ValueError("--documentation-name must be a Markdown file name")
    return name


def main() -> None:
    args = parse_args()
    baseline_doc = args.baseline_doc.resolve()

    if args.check_baseline_only:
        if not baseline_doc.is_file():
            if args.allow_missing_baseline:
                print(f"::warning::Published baseline unavailable: {baseline_doc}")
                return
            raise FileNotFoundError(f"Published baseline unavailable: {baseline_doc}")
        read_published_doc(baseline_doc)
        print(f"Published baseline: {baseline_doc}")
        return

    required = (
        args.candidate_dir,
        args.candidate_tag,
        args.deployment,
        args.documentation_name,
    )
    if any(value is None for value in required):
        raise SystemExit(
            "--candidate-dir, --candidate-tag, --deployment, and --documentation-name "
            "are required for comparison"
        )

    candidate_dir = args.candidate_dir.resolve()
    candidate_csv = candidate_dir / "summary_results.csv"
    candidate = read_candidate_csv(
        candidate_csv,
        args.candidate_tag,
        args.expected_hardware_profile,
    )

    documentation_name = validate_documentation_name(args.documentation_name)
    candidate_doc = candidate_dir / documentation_name
    candidate_doc.write_text(doc_table(candidate), encoding="utf-8")

    comparison = candidate_dir / "performance-comparison.md"
    if not baseline_doc.is_file():
        if not args.allow_missing_baseline:
            raise FileNotFoundError(f"Published baseline unavailable: {baseline_doc}")
        report = missing_baseline_report(
            candidate,
            args.stable_tag,
            args.deployment,
            baseline_doc,
        )
        comparison.write_text(report, encoding="utf-8")
        print(f"::warning::Published baseline unavailable: {baseline_doc}")
    else:
        baseline = read_published_doc(baseline_doc)
        report = comparison_table(
            baseline,
            candidate,
            args.stable_tag,
            args.deployment,
            baseline_doc,
        )
        comparison.write_text(report, encoding="utf-8")
        print(f"Published baseline: {baseline_doc}")

    print(f"Candidate: {candidate_csv}")
    print(f"Documentation table: {candidate_doc}")
    print(f"Comparison: {comparison}")
    print()
    print(report)


if __name__ == "__main__":
    main()
