#!/usr/bin/env python3
"""Summarize ROCprof ATT source mapping from a dispatch directory."""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


def classify_asm(asm: str) -> str:
    s = asm.lower()
    if "s_waitcnt" in s:
        if "vmcnt" in s:
            return "wait-vmem"
        if "lgkmcnt" in s:
            return "wait-lds-smem"
        if "expcnt" in s:
            return "wait-exp"
        return "waitcnt"
    if "s_barrier" in s or "sched_barrier" in s or "s_wait_idle" in s:
        return "barrier"
    if "v_mfma" in s:
        return "mfma"
    if "global_load" in s or "buffer_load" in s or "flat_load" in s:
        return "vmem-load"
    if "global_store" in s or "buffer_store" in s or "flat_store" in s:
        return "vmem-store"
    if "ds_read" in s:
        return "lds-read"
    if "ds_write" in s:
        return "lds-write"
    if "s_load" in s or "s_store" in s:
        return "smem"
    if s.startswith("v_"):
        return "valu"
    if s.startswith("s_"):
        return "salu"
    return "other"


def row_get(row: list, index: int, default=0):
    if len(row) <= index:
        return default
    return row[index]


def load_rows(dispatch_dir: Path) -> list[list]:
    code_path = dispatch_dir / "code.json"
    if not code_path.exists():
        raise SystemExit(f"Missing {code_path}")
    data = json.loads(code_path.read_text())
    rows = data.get("code")
    if not isinstance(rows, list):
        raise SystemExit(f"{code_path} does not contain a code list")
    return rows


def summarize(dispatch_dir: Path, top_source: int) -> dict:
    rows = load_rows(dispatch_dir)
    wave_files = glob.glob(str(dispatch_dir / "se*_sm*_*.json"))
    mapped = 0
    executable = 0
    by_source = defaultdict(lambda: {"rows": 0, "total_cycles": 0, "stall_cycles": 0, "classes": Counter()})
    by_class = Counter()
    by_class_stall = Counter()

    for row in rows:
        asm = str(row_get(row, 0, ""))
        source = row_get(row, 3, "") or "<unknown>"
        pc_index = row_get(row, 2, 0)
        total_cycles = row_get(row, 7, 0)
        stall_cycles = row_get(row, 8, 0)
        try:
            total_cycles = int(total_cycles) if isinstance(total_cycles, (int, float, str)) else 0
        except ValueError:
            total_cycles = 0
        try:
            stall_cycles = int(stall_cycles) if isinstance(stall_cycles, (int, float, str)) else 0
        except ValueError:
            stall_cycles = 0
        if isinstance(pc_index, int) and pc_index != 0:
            executable += 1
        if source != "<unknown>":
            mapped += 1
        cls = classify_asm(asm)
        by_class[cls] += 1
        by_class_stall[cls] += stall_cycles
        rec = by_source[source]
        rec["rows"] += 1
        rec["total_cycles"] += total_cycles
        rec["stall_cycles"] += stall_cycles
        rec["classes"][cls] += stall_cycles

    total_stall = sum(v["stall_cycles"] for v in by_source.values())
    ranked_source = []
    for source, rec in by_source.items():
        classes = rec["classes"]
        dominant = classes.most_common(1)[0][0] if classes else "other"
        ranked_source.append(
            {
                "source": source,
                "rows": rec["rows"],
                "total_cycles": rec["total_cycles"],
                "stall_cycles": rec["stall_cycles"],
                "stall_pct_of_total": (100.0 * rec["stall_cycles"] / total_stall) if total_stall else 0.0,
                "dominant_class": dominant,
            }
        )
    ranked_source.sort(key=lambda x: (x["stall_cycles"], x["total_cycles"], x["rows"]), reverse=True)

    return {
        "dispatch_dir": str(dispatch_dir),
        "row_count": len(rows),
        "executable_row_count": executable,
        "mapped_row_count": mapped,
        "mapped_pct": (100.0 * mapped / len(rows)) if rows else 0.0,
        "wave_file_count": len(wave_files),
        "instruction_class_rows": dict(by_class.most_common()),
        "instruction_class_stall_cycles": dict(by_class_stall.most_common()),
        "top_source": ranked_source[:top_source],
    }


def print_text(summary: dict) -> None:
    print(f"Dispatch: {summary['dispatch_dir']}")
    print(f"Rows: {summary['row_count']} executable={summary['executable_row_count']}")
    print(f"Mapped: {summary['mapped_row_count']} ({summary['mapped_pct']:.1f}%)")
    print(f"Wave files: {summary['wave_file_count']}")
    print("\nInstruction classes by stall cycles:")
    for key, value in summary["instruction_class_stall_cycles"].items():
        print(f"  {key:<14} {value}")
    print("\nTop source lines:")
    for idx, rec in enumerate(summary["top_source"], 1):
        print(
            f"  {idx:>2}. stall={rec['stall_cycles']:<10} "
            f"pct={rec['stall_pct_of_total']:>6.2f}% "
            f"class={rec['dominant_class']:<14} rows={rec['rows']:<5} "
            f"{rec['source']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dispatch_dir")
    parser.add_argument("--top-source", type=int, default=20)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    dispatch_dir = Path(args.dispatch_dir).resolve()
    summary = summarize(dispatch_dir, args.top_source)
    print_text(summary)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
