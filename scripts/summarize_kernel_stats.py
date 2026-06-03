#!/usr/bin/env python3
"""Summarize rocprofv3 *_kernel_stats.csv files."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def _float(row: dict, *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except ValueError:
                pass
    return 0.0


def summarize(path: Path, include_regex: str | None, limit: int) -> list[dict]:
    pattern = re.compile(include_regex) if include_regex else None
    rows = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("Name") or row.get("KernelName") or ""
            if pattern and not pattern.search(name):
                continue
            rows.append(
                {
                    "name": name,
                    "calls": int(_float(row, "Calls", "TotalCalls")),
                    "total_ns": _float(row, "TotalDurationNs", "TotalDuration", "DurationNs"),
                    "average_ns": _float(row, "AverageNs", "AvgNs", "Average"),
                    "min_ns": _float(row, "MinNs", "MinimumNs"),
                    "max_ns": _float(row, "MaxNs", "MaximumNs"),
                    "percentage": _float(row, "Percentage"),
                }
            )
    rows.sort(key=lambda x: (x["total_ns"], x["calls"]), reverse=True)
    return rows[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel_stats_csv")
    parser.add_argument("--include-regex")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    csv_path = Path(args.kernel_stats_csv)
    if not csv_path.is_file():
        raise SystemExit(f"kernel stats CSV not found: {csv_path}")
    rows = summarize(csv_path, args.include_regex, args.limit)
    if not rows:
        print(f"No rows matched in {csv_path}"
              + (f" (regex {args.include_regex!r})" if args.include_regex else ""))
    for i, row in enumerate(rows, 1):
        print(
            f"{i:>2}. calls={row['calls']:<5} avg={row['average_ns'] / 1000:>9.3f} us "
            f"total={row['total_ns'] / 1000:>10.3f} us pct={row['percentage']:>6.2f}% "
            f"{row['name']}"
        )
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
