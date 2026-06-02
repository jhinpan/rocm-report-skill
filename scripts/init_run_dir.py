#!/usr/bin/env python3
"""Create a clean ROCm profiling run directory."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


SUBDIRS = [
    "commands",
    "raw/stats",
    "raw/kernel_trace",
    "att",
    "analysis",
    "cache/flydsl-debug",
    "logs",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="profile/<run-name>")
    parser.add_argument("--force", action="store_true", help="allow existing empty directory")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if run_dir.exists() and any(run_dir.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to reuse non-empty run directory: {run_dir}")

    for subdir in SUBDIRS:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "cwd": os.getcwd(),
        "status": "draft",
    }
    metadata_path = run_dir / "analysis" / "run_metadata.json"
    if not metadata_path.exists():
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    notes_path = run_dir / "analysis" / "notes.md"
    if not notes_path.exists():
        notes_path.write_text(
            "# Notes\n\n"
            "- Kernel:\n"
            "- Shape/workload:\n"
            "- GPU/arch:\n"
            "- Baseline:\n"
            "- Question:\n"
        )

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
