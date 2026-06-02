---
name: rocm-report-skill
description: Profile and analyze AMD ROCm GPU kernels, especially FlyDSL kernels, with rocprofv3, Advanced Thread Trace, and ROCprof Compute Viewer artifacts. Use when the user asks to profile a ROCm/HIP/FlyDSL kernel, inspect ATT source-line mapping, diagnose bubbles, overlap compute and memory/communication, choose an idle AMD GPU, write a profiling report, or turn profile evidence into a concrete optimization plan. Do not use for NVIDIA Nsight Compute reports.
---

# ROCm Report Skill

Experimental profiling workflow for AMD GPUs. The goal is not to replace a
kernel engineer. The goal is to make evidence collection and first-pass
diagnosis repeatable enough that an agent can propose smaller, testable kernel
engineering hypotheses instead of vague advice.

## Golden Rule

Profile -> diagnose -> form one code hypothesis -> test again.

Do not stop at "there are bubbles" or "source line X is hot." A useful answer
must say which mechanism is likely creating the idle time, which source or ISA
region supports that claim, and what one next code change would validate or
falsify it.

## Quickstart

1. Create a new run directory. Never reuse an existing run.

   ```bash
   python3 scripts/init_run_dir.py profile/<run-name>
   ```

2. Frame the exact target before collecting data:

   - kernel name or regex
   - GPU architecture, for example gfx942 or gfx950
   - workload shape and dispatch path
   - baseline, if comparing
   - question to answer, such as "is the gap a tail effect, waitcnt dependency,
     barrier, memory layout issue, or lack of overlap?"

3. Pick an idle AMD GPU if the machine is shared.

   ```bash
   python3 scripts/find_idle_gpu.py
   ```

4. Collect rocprofv3 stats and ATT. For FlyDSL source mapping, use a fresh
   debug cache:

   ```bash
   export HIP_VISIBLE_DEVICES=<gpu>
   export FLYDSL_DEBUG_ENABLE_DEBUG_INFO=1
   export FLYDSL_RUNTIME_CACHE_DIR="$PWD/profile/<run-name>/cache/flydsl-debug"
   ```

   Then run discovery and ATT collection as described in
   `references/02-rocprofv3-collection.md`.

5. Parse ATT source mapping and hotspots from the kept dispatch directory:

   ```bash
   python3 scripts/summarize_att_source.py \
     profile/<run-name>/att/ui_output_agent_*_dispatch_* \
     --top-source 20 \
     --json-out profile/<run-name>/analysis/att_source_summary.json
   ```

6. Diagnose using `references/04-analysis-dimensions.md`. If the profile shows
   bubble time, classify the bubble before suggesting code:

   - launch/tail under-fill
   - dependency wait, usually visible around `s_waitcnt`
   - explicit barrier or scheduler group barrier
   - VMEM/LDS latency or bank conflict
   - MFMA starvation from missing prefetch/consumer overlap
   - source attribution failure, where the profile is not yet actionable

7. Write `profile/<run-name>/REPORT.md` using
   `references/05-report-template.md`.

8. If optimizing code, make exactly one scoped change, rerun the same shape, and
   compare before/after artifacts. Avoid stacking multiple hypotheses in one
   edit.

## File Index

| Path | Purpose |
|---|---|
| `references/00-directory-layout.md` | Run directory layout and artifact rules |
| `references/01-workflow.md` | End-to-end workflow, including the code-hypothesis loop |
| `references/02-rocprofv3-collection.md` | rocprofv3 stats and ATT collection recipes |
| `references/03-att-artifacts.md` | How to inspect ATT/Compute Viewer artifacts |
| `references/04-analysis-dimensions.md` | AMD/FlyDSL diagnosis lenses |
| `references/05-report-template.md` | Markdown report template |
| `references/06-agent-limitations.md` | What the agent can and cannot infer from profile data |
| `scripts/init_run_dir.py` | Create a clean run directory |
| `scripts/find_idle_gpu.py` | Suggest an idle ROCm GPU from `rocm-smi` output |
| `scripts/summarize_att_source.py` | Summarize ATT `code.json` source mapping and stalls |

## Critical Lessons

- Source mapping is necessary, not sufficient. A line-level hotspot only tells
  where time appears. It does not automatically tell which schedule rewrite will
  overlap communication, memory, and MFMA.
- For FlyDSL, cold debug-cache discipline matters. If a no-debug HSACO was
  cached first, later debug runs can still produce empty or misleading source
  mapping.
- A useful profiling report should name exact artifacts, exact commands, exact
  source lines, and exact before/after values. Generic advice is a failed report.
- When the diagnosis says "overlap more," convert that into a concrete
  experiment: move a prefetch earlier, split a wait, increase staging depth,
  change CTA work assignment, or alter scheduler grouping. Then profile again.
- Mark this skill experimental until it has been validated on several real
  FlyDSL kernels and at least one non-FlyDSL HIP/ROCm kernel.
