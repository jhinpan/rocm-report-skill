# Report Template

Save as `profile/<run-name>/REPORT.md`.

```markdown
# <kernel> ROCm Profiling Report

**Kernel:** <exact name or regex>
**GPU:** <device, architecture>
**ROCm tools:** <rocprofv3 version, relevant viewer/tool versions>
**Date:** YYYY-MM-DD
**Run directory:** `profile/<run-name>/`

## 0. Setup

- Command profiled:
- Shape/workload:
- Dispatch path:
- Baseline:
- Environment:
  - `HIP_VISIBLE_DEVICES=`
  - `FLYDSL_DEBUG_ENABLE_DEBUG_INFO=`
  - `FLYDSL_RUNTIME_CACHE_DIR=`

## 1. Headline

One paragraph with the main finding and confidence.

| Metric | Value | Artifact |
|---|---:|---|
| Duration | | |
| rocprof kernel avg | | `raw/stats/*_kernel_stats.csv` |
| Other timing sources | | note if they disagree |
| Total CTAs / waves | | grid/block from `--kernel-trace` / launch params (not ATT) |
| Mapped source rows | | `analysis/att_source_summary.json` |
| Top source line | | `analysis/att_source_summary.json` |
| Top instruction class | | single-CU ATT sample (`att_target_cu`), not device-wide |

## 2. Evidence

### Launch and tail

<facts, values, artifacts>

### Source hotspots

<top lines with stall/total cycles and dominant instruction classes>

### Wait/barrier/memory/compute classification

<which bubble mechanism is most likely and why>

## 3. Diagnosis

| Finding | Evidence | Confidence | Impact |
|---|---|---|---|
| | | | |

## 4. Next Code Hypothesis

Make exactly one testable claim.

Example:

> Move the K tile prefetch from line X to one loop iteration earlier and keep
> the `vmcnt` wait at line Y. If the diagnosis is right, the wait hotspot on
> line Y should drop and MFMA lines should account for more total cycles without
> increasing duration from lower occupancy.

## 5. Retest Plan

- Branch/worktree:
- Same shape:
- Same GPU or equivalent:
- Before run:
- After run:
- Expected metric movement:

## 6. Caveats

- What the profile cannot prove yet:
- Which artifact would resolve uncertainty:
```

Style rules:

- Put exact numbers in every claim.
- Link or name artifacts.
- Name source lines and instruction classes.
- Do not list more than three optimization priorities.
- Use "hypothesis" when a code change is not yet validated.
