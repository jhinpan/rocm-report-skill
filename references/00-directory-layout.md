# Directory Layout

All profiling artifacts for a run live under one directory. Do not scatter
rocprof outputs across source trees.

```text
profile/<run-name>/
  REPORT.md
  commands/
    collect_stats.sh
    collect_att.sh
    env.txt
  raw/
    stats/
    kernel_trace/
  att/
    input_trace.yaml
    ui_output_agent_*_dispatch_*/
  analysis/
    att_source_summary.json
    notes.md
  cache/
    flydsl-debug/
  logs/
```

Rules:

- One run directory per kernel version, shape, dispatch path, or optimization
  attempt.
- Keep before and after runs separate. Compare from `analysis/`, not by
  overwriting raw artifacts.
- For FlyDSL source mapping, put `FLYDSL_RUNTIME_CACHE_DIR` under the run
  directory so the debug HSACO provenance is clear.
- Keep generated heavy artifacts out of git unless the repo explicitly tracks
  small, curated reproductions.
- Always store the command lines and environment used to collect the profile.

Recommended naming:

```text
profile/flash-attn-gfx950-b1-s2048-baseline/
profile/flash-attn-gfx950-b1-s2048-prefetch-kplus1/
profile/rmsnorm-gfx950-large-m-small-n-known-block-size/
```
