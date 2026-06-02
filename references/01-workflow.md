# Workflow

## 0. Decide the question

Before running tools, write down:

- exact kernel or regex
- shape and dispatch path
- target GPU and architecture
- baseline or previous run
- performance question

Bad question: "why is it slow?"

Better question: "At B=1, S=2048, H=32, D=128 on gfx950, is the idle time from
tail waves, VMEM waits before MFMA, barriers, or lack of K/V prefetch overlap?"

## 1. Create a clean run

```bash
python3 scripts/init_run_dir.py profile/<run-name>
```

## 2. Collect discovery stats

Use a stats/kernel-trace pass to identify the real kernel name, call count, and
duration ordering. Do not assume the intended kernel is the only kernel emitted.

## 3. Collect ATT

For FlyDSL, use a fresh debug cache and set debug info before discovery and ATT
capture. Keep one valid dispatch directory and document why it was selected.

## 4. Parse artifacts

Run `scripts/summarize_att_source.py` on the dispatch directory. Verify:

- `code.json` exists
- most ISA rows have source locations when source mapping is expected
- top source lines are real user schedule lines, not only a decorator or helper
  wrapper line

If mapping is empty or collapsed, fix collection/source-location first. Do not
diagnose overlap from a bad map.

## 5. Diagnose

Walk through `04-analysis-dimensions.md`. For each finding, record:

- observed artifact
- metric or count
- source line or ISA class
- interpretation
- confidence

## 6. Turn diagnosis into one code hypothesis

Examples:

- Move K prefetch one loop iteration earlier and keep the wait at the consumer.
- Split a broad wait into a narrower `vmcnt` or `lgkmcnt` wait.
- Increase staging depth only if the profile shows a producer/consumer gap and
  occupancy/VGPR budget can afford it.
- Reassign variable work to reduce CTA tail if the timeline shows under-fill.
- Change vectorization or layout only if VMEM/LDS instruction classes and source
  lines point at the access pattern.

One hypothesis per code branch. Rerun the same shape.

## 7. Report

Use `05-report-template.md`. The report should let another engineer reproduce
the run and challenge the interpretation.
