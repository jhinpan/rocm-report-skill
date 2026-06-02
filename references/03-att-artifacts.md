# ATT Artifacts

A typical ATT dispatch directory contains:

```text
ui_output_agent_*_dispatch_*/
  code.json
  snapshots.json
  source_*.py
  se*_sm*_*.json
```

Important checks:

- `code.json` row count: approximate number of ISA rows.
- mapped source rows: rows whose source-location field is non-empty.
- top source lines by stall cycles or total cycles.
- top instruction classes: `s_waitcnt`, `s_barrier`, `global/buffer_load`,
  `ds_read/ds_write`, `v_mfma`, stores, and other.
- whether the hottest source line is a real schedule statement or a collapsed
  wrapper/decorator/function line.

Run:

```bash
python3 scripts/summarize_att_source.py <dispatch-dir> --top-source 20
```

Interpretation guardrails:

- If mapped rows are near zero, fix debug-info/cold-cache capture before
  diagnosing performance.
- If most cycles collapse to a function/decorator/helper wrapper line, the trace
  is not yet actionable enough for schedule-level optimization.
- If top stalls are `s_waitcnt`, inspect the producer instruction class before
  the wait and the consumer after the wait. The question is whether the wait is
  too early, too broad, or unavoidable.
- If top stalls are barriers, inspect whether all CTAs/waves reach the barrier
  with similar work. Barrier time often points to imbalance before the barrier.
- If MFMA lines are sparse while VMEM/LDS/wait lines dominate, test whether
  prefetch or staging can feed MFMA earlier.
