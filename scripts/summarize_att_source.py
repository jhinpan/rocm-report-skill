#!/usr/bin/env python3
"""Summarize ROCprof ATT source mapping from one or more dispatch directories.

The ATT `code.json` is a list of positional rows; its header documents the
fields as: ISA, _, LineNumber, Source, Codeobj, Vaddr, Hit, Latency, Stall, Idle.
We read ISA(0), LineNumber(2), Source(3), Latency(7) as total_cycles, Stall(8)
as stall_cycles, and skip the leading "; kernel" label rows (not real ISA).
"""

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


def _to_int(value) -> int:
    try:
        return int(float(value))  # tolerate "512", 512, 512.0, "512.0"
    except (TypeError, ValueError):
        return 0


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
    isa_rows = 0          # real ISA instructions (label rows skipped)
    with_line = 0         # ISA rows carrying a non-zero LineNumber
    by_source = defaultdict(lambda: {"rows": 0, "total_cycles": 0, "stall_cycles": 0, "classes": Counter()})
    by_class = Counter()
    by_class_stall = Counter()

    for row in rows:
        asm = str(row_get(row, 0, ""))
        # ROCprof emits label rows such as "; rmsnorm_kernel_0" -- not real ISA.
        if asm.lstrip().startswith(";"):
            continue
        isa_rows += 1
        source = row_get(row, 3, "") or "<unknown>"
        line_number = row_get(row, 2, 0)
        total_cycles = _to_int(row_get(row, 7, 0))
        stall_cycles = _to_int(row_get(row, 8, 0))
        if isinstance(line_number, int) and line_number != 0:
            with_line += 1
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
        "isa_row_count": isa_rows,
        "rows_with_line_number": with_line,
        "mapped_row_count": mapped,
        "mapped_pct": (100.0 * mapped / isa_rows) if isa_rows else 0.0,
        "wave_file_count": len(wave_files),
        "instruction_class_rows": dict(by_class.most_common()),
        "instruction_class_stall_cycles": dict(by_class_stall.most_common()),
        "top_source": ranked_source[:top_source],
    }


def print_text(summary: dict) -> None:
    print(f"Dispatch: {summary['dispatch_dir']}")
    print(f"Rows: {summary['row_count']} (ISA={summary['isa_row_count']}, "
          f"with-line={summary['rows_with_line_number']})")
    print(f"Mapped: {summary['mapped_row_count']} ({summary['mapped_pct']:.1f}% of ISA rows)")
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
    parser.add_argument(
        "dispatch_dir",
        nargs="+",
        help="One or more ui_output_agent_*_dispatch_* directories. A shell glob "
             "may expand to several (empty-shell placeholders + the real capture); "
             "each is summarized separately.",
    )
    parser.add_argument("--top-source", type=int, default=20)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    summaries = []
    for i, d in enumerate(args.dispatch_dir):
        summary = summarize(Path(d).resolve(), args.top_source)
        if i:
            print()
        print_text(summary)
        summaries.append(summary)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = summaries if len(summaries) > 1 else summaries[0]
        out.write_text(json.dumps(payload, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
