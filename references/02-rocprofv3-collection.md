# rocprofv3 Collection

This file gives command shapes, not a promise that every ROCm release exposes
identical flags. Check `rocprofv3 --help` on the target machine when adapting.

## Environment check

```bash
rocprofv3 --version
rocm-smi
python3 scripts/find_idle_gpu.py
```

For FlyDSL source mapping:

```bash
export HIP_VISIBLE_DEVICES=<gpu>
export FLYDSL_DEBUG_ENABLE_DEBUG_INFO=1
export FLYDSL_RUNTIME_CACHE_DIR="$PROFILE_RUN_DIR/cache/flydsl-debug"
export FLYDSL_RUNTIME_ENABLE_CACHE=1
```

Remove or replace the run directory before recapturing if you need a truly cold
debug compile.

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
    kernel_iteration_range: "[0, [1-1]]"
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

After collection, inspect `att/ui_output_agent_*_dispatch_*/`.

Keep the dispatch that has:

- non-empty wave JSON files
- non-empty `code.json`
- source mapping when expected
- the intended kernel name and dispatch ordinal

If every dispatch is empty, increase ATT buffer size, change iteration range, or
profile a larger diagnostic workload.
