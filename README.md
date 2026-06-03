# rocm-report-skill

A Claude Code skill for profiling **AMD ROCm / HIP / FlyDSL** GPU kernels and
turning the evidence into one *testable* optimization hypothesis. It covers the
full loop: pick an idle GPU, collect `rocprofv3` stats + Advanced Thread Trace
(ATT), summarize source-line stalls, walk a set of diagnosis dimensions, and
write an evidence-backed report — then retest one scoped change.

> **Status: experimental.** Validated end-to-end on a real FlyDSL kernel
> (`rmsnorm`, gfx950/MI350X → 100% ATT source mapping, VMEM-wait diagnosis) and a
> non-FlyDSL kernel (torch `layer_norm`, stats path). Treat verdicts as a
> first pass until it has been driven on several more kernels.

The entry point is [`SKILL.md`](SKILL.md); the details live in [`references/`](references/).

---

## Lineage: learned from `ncu-report-skill`

This skill is an **independent AMD re-implementation of the pattern** established
by MIT Han Lab's NVIDIA Nsight Compute skill,
[`mit-han-lab/ncu-report-skill`](https://github.com/mit-han-lab/ncu-report-skill)
(part of [Kernel Design Agents](https://github.com/mit-han-lab/kernel-design-agents)).
None of its code is copied — the NVIDIA tooling doesn't transfer — but its
*methodology* did, and that is what made this worth building. (Same spirit as
[ROCmKernelWiki](https://github.com/jhinpan/ROCmKernelWiki), which is inspired by
MIT Han Lab's KernelWiki.)

**What we took (the tool-agnostic discipline):**

- The skill skeleton itself — `SKILL.md` + numbered `reference/` docs + small,
  reusable helper scripts — and the idea that a profiling *workflow* can be made
  repeatable enough for an agent to follow.
- **Run-directory discipline** (`00-directory-layout`): one run dir per
  kernel / shape / attempt; always store the commands and environment; compare
  before/after from `analysis/`, never by overwriting raw artifacts.
- The **workflow shape** (`01-workflow`): frame the exact target → collect →
  parse → walk the analysis dimensions → diagnose → evidence-backed report →
  retest one change.
- The **analysis-dimensions** lens and the core rule: *profile → diagnose → one
  code hypothesis → test again.* "There are bubbles" or "line X is hot" is not a
  diagnosis; generic advice is a failed report.
- The **report template** discipline: name exact artifacts, exact commands, exact
  source lines, exact before/after values.

**What we rebuilt, because NVIDIA → AMD does not port:**

| NVIDIA (`ncu-report-skill`) | AMD (`rocm-report-skill`) |
|---|---|
| `ncu` + `.ncu-rep` + the `ncu_report` Python API | `rocprofv3 --stats/--kernel-trace` CSVs + ATT `code.json` parsed directly |
| Whole-kernel Sections, roofline, occupancy model | single-CU ATT wave-state **sample** (`att_target_cu=1`); launch geometry/occupancy come from `--kernel-trace`/PMC, **not** the ATT trace |
| `harness_template.cu` + header-only safetensors loader | FlyDSL/HIP kernels launched from Python — no standalone `.cu` harness |
| sm_100 (Blackwell / B200) metric names | gfx950 (MI350X / CDNA4) PMC counters + ISA instruction classes |
| ncu source view for per-line stalls | ATT `code.json` positional rows (`ISA, _, LineNumber, Source, Codeobj, Vaddr, Hit, Latency, Stall, Idle`) |
| — | **FlyDSL cold-debug-cache discipline** for source mapping (a no-debug HSACO cached first poisons the mapping) |
| — | ATT-specific quirks documented in `02`/`03`: empty-shell dispatch dirs, `kernel_iteration_range` inner range is a *lower bound*, process-wide `dispatch_<N>` counter |

Helper-script correspondence:

| `ncu-report-skill` | `rocm-report-skill` | both do |
|---|---|---|
| `helpers/extract_stall_hotspots.py` | `scripts/summarize_att_source.py` | per-source-line stall aggregation + instruction classes |
| `helpers/analyze_reports.py` | `scripts/summarize_kernel_stats.py` | pull key timing metrics from the profiler output |
| `helpers/ncu_utils.py` (env/tooling) | `scripts/find_idle_gpu.py` + `init_run_dir.py` | pick a device, lay out a clean run |

---

## What's in this repo

```
.
├── SKILL.md                              ← skill entry point (YAML frontmatter)
├── references/
│   ├── 00-directory-layout.md            ← run-directory conventions (read first)
│   ├── 01-workflow.md                    ← end-to-end loop incl. the code-hypothesis step
│   ├── 02-rocprofv3-collection.md        ← rocprofv3 stats + ATT collection recipes
│   ├── 03-att-artifacts.md               ← how to inspect ATT dispatch dirs
│   ├── 04-analysis-dimensions.md         ← AMD/FlyDSL diagnosis lenses
│   ├── 05-report-template.md             ← markdown report template
│   └── 06-agent-limitations.md           ← what an agent can / cannot infer from a profile
├── scripts/
│   ├── init_run_dir.py                   ← create a clean run directory
│   ├── find_idle_gpu.py                  ← suggest an idle GPU from rocm-smi
│   ├── summarize_kernel_stats.py         ← summarize rocprofv3 *_kernel_stats.csv timing
│   └── summarize_att_source.py           ← summarize ATT code.json source mapping + stalls
└── agents/openai.yaml                    ← skill UI metadata
```

---

## Install

It is a standard Claude Code skill; install at user or project level.

```bash
git clone https://github.com/jhinpan/rocm-report-skill.git ~/workspace/rocm-report-skill

# user-level (available in every project)
mkdir -p ~/.claude/skills && ln -s ~/workspace/rocm-report-skill ~/.claude/skills/rocm-report-skill

# or project-level (scoped to one repo)
cd /path/to/repo && mkdir -p .claude/skills && ln -s ~/workspace/rocm-report-skill .claude/skills/rocm-report-skill
```

Then invoke it with `/rocm-report-skill`, or let the model pick it up when a
conversation matches the description in `SKILL.md`.

## Use it without Claude

The scripts run standalone on any rocprofv3 output:

```bash
python3 scripts/summarize_kernel_stats.py <run>/raw/stats/discover_kernel_stats.csv --include-regex '<kernel>'
python3 scripts/summarize_att_source.py   <run>/att/ui_output_agent_<id>_dispatch_<N> --top-source 20
```

---

## Credits

Methodology and skill structure learned from
[`mit-han-lab/ncu-report-skill`](https://github.com/mit-han-lab/ncu-report-skill)
/ [Kernel Design Agents](https://github.com/mit-han-lab/kernel-design-agents).
This repository is an independent AMD ROCm implementation; profiling tooling,
scripts, and the FlyDSL/ATT specifics are its own.
