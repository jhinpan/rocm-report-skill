# rocprofv3 Collection

This file gives command shapes, not a promise that every ROCm release exposes
identical flags. Check `rocprofv3 --help` on the target machine when adapting.

## Environment check

Export the run directory once (the one `init_run_dir.py` created); every command
below writes under it:

```bash
export PROFILE_RUN_DIR="$PWD/profile/<run-name>"
rocprofv3 --version
rocm-smi
python3 scripts/find_idle_gpu.py
```

For FlyDSL source mapping (the debug/ATT run):

```bash
export HIP_VISIBLE_DEVICES=<gpu>
export FLYDSL_DEBUG_ENABLE_DEBUG_INFO=1
export FLYDSL_RUNTIME_CACHE_DIR="$PROFILE_RUN_DIR/cache/flydsl-debug"
```

The cache dir MUST be fresh for the source-mapping run. The central failure mode
is a no-debug HSACO that was cached first: a later debug run reuses it and
`code.json` comes back with empty or misleading source mapping. `init_run_dir.py`
gives you a clean `cache/flydsl-debug`; do not reuse it across runs, and replace
the run directory before recapturing. (`FLYDSL_RUNTIME_ENABLE_CACHE=1` is fine for
a separate non-debug PMC/timing run, but not for this mapping run.)

## Discovery pass

```bash
rocprofv3 \
  --stats \
  --kernel-trace \
  -f csv \
  -o "$PROFILE_RUN_DIR/raw/stats/discover" \
  -- <command>
```

Use the resulting kernel stats CSV to select the target kernel and dispatch
iteration range.

## ATT input file

Place this under `$PROFILE_RUN_DIR/att/input_trace.yaml` and update the regex,
iteration range, output directory, and buffer size.

```yaml
GlobalParameters:
  KeepBuildTmp: True
  AsmDebug: True
jobs:
  -
    kernel_include_regex: "<escaped kernel regex>"
    kernel_iteration_range: "[5, [6-6]]"   # skip 5 warm-up dispatches, trace the 6th (see Dispatch selection)
    output_file: out
    output_directory: <absolute-profile-run-dir>/att
    output_format: [json, csv]
    truncate_kernels: true
    sys_trace: false
    advanced_thread_trace: true
    att_target_cu: 1
    att_shader_engine_mask: "0xf"
    att_simd_select: "0xf"
    att_buffer_size: "0x6000000"
pmc:
  - SQ_INSTS_VALU
  - SQ_INSTS_MFMA
  - SQ_INSTS_VMEM
  - SQ_WAVES
  - SQ_WAIT_INST_LDS
  - SQ_LDS_BANK_CONFLICT
  - GRBM_GUI_ACTIVE
```

Run:

```bash
rocprofv3 -i "$PROFILE_RUN_DIR/att/input_trace.yaml" -- <command>
```

## Dispatch selection

After collection, inspect `att/ui_output_agent_*_dispatch_*/`. Three quirks make
the *first* directory the wrong one to read:

- **Empty-shell dispatch dirs are normal.** rocprofv3 reserves placeholder
  `dispatch_*` dirs (only `code.json` / `filenames.json` / `occupancy.json`, zero
  wave files) before the real capture. The real trace is in a *later*
  `dispatch_<N>`.
- **`<N>` is the process-wide dispatch counter**, not your kernel's iteration. It
  includes non-matching kernels (e.g. torch elementwise/reduce) in interleaved
  slots, so the ordinal is not "the Nth call of my kernel."
- **The inner iteration range is a lower bound.** `"[5, [6-6]]"` reliably yields
  **two** captures, not one; both are valid and make a useful noise-floor check.

Keep the dispatch that has:

- non-empty wave JSON files (`se*_sm*_*.json`) — this is what separates a real
  capture from an empty shell
- non-empty `code.json` with source mapping when expected
- the intended kernel name

`summarize_att_source.py` prints `wave_file_count` per directory, so a glob pass
(`ui_output_agent_*_dispatch_*`) surfaces the shells (`wave_file_count=0`) at a
glance before you select one.

If every dispatch is empty, increase ATT buffer size, change the iteration range,
or profile a larger diagnostic workload — a small grid can also miss
`att_target_cu`.
