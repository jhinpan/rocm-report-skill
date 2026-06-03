#!/usr/bin/env python3
"""Suggest an idle AMD GPU from rocm-smi output.

This helper intentionally stays conservative. If it cannot parse rocm-smi JSON,
it prints the raw command output and asks the user to choose manually.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Gpu:
    index: int
    use_pct: float | None = None
    mem_pct: float | None = None
    raw: dict | None = None


def _num(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def parse_json(text: str) -> list[Gpu]:
    data = json.loads(text)
    gpus: list[Gpu] = []
    for key, value in data.items():
        idx_match = re.search(r"(\d+)", str(key))
        if not idx_match or not isinstance(value, dict):
            continue
        idx = int(idx_match.group(1))
        use = None
        mem = None
        for k, v in value.items():
            lk = k.lower()
            if use is None and ("gpu use" in lk or "gpu busy" in lk or "use" == lk):
                use = _num(v)
            if mem is None and ("memory use" in lk or "vram" in lk or "mem use" in lk):
                mem = _num(v)
        gpus.append(Gpu(index=idx, use_pct=use, mem_pct=mem, raw=value))
    return sorted(gpus, key=lambda g: g.index)


def main() -> int:
    cmd = ["rocm-smi", "--showuse", "--showmemuse", "--json"]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        print("rocm-smi not found", file=sys.stderr)
        return 2

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode

    try:
        gpus = parse_json(proc.stdout)
    except Exception:
        print(proc.stdout)
        print("Could not parse rocm-smi JSON; choose GPU manually.", file=sys.stderr)
        return 3

    if not gpus:
        print(proc.stdout)
        print("No GPUs parsed; choose GPU manually.", file=sys.stderr)
        return 3

    def score(g: Gpu) -> tuple[float, float, int]:
        use = 1000.0 if g.use_pct is None else g.use_pct
        mem = 1000.0 if g.mem_pct is None else g.mem_pct
        return (use, mem, g.index)

    best = min(gpus, key=score)
    for gpu in gpus:
        mark = "*" if gpu.index == best.index else " "
        use = "unknown" if gpu.use_pct is None else f"{gpu.use_pct:.1f}%"
        mem = "unknown" if gpu.mem_pct is None else f"{gpu.mem_pct:.1f}%"
        print(f"{mark} GPU {gpu.index}: use={use} mem={mem}")
    print(f"\nSuggested HIP_VISIBLE_DEVICES={best.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
