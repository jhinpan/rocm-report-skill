# Agent Limitations

This skill is deliberately not an automatic kernel optimizer.

What an agent can do well:

- keep profiling artifacts separated and reproducible
- enforce cold debug-cache discipline for FlyDSL source mapping
- summarize ATT `code.json` into source-line and instruction-class evidence
- identify whether the next question is launch geometry, tail, waitcnt,
  barrier, memory access, MFMA feed, or source-location quality
- propose one small code hypothesis and a retest plan

What an agent usually cannot infer from profile data alone:

- the best schedule transformation for a complex kernel
- whether a deeper pipeline is legal without understanding lifetimes and
  hazards
- whether communication/compute overlap is blocked by algorithm structure,
  framework scheduling, or a missing prefetch
- whether a source hotspot is fixable without reading the surrounding kernel
  and comparing against a known-good schedule

Practical rule:

If the answer is "fill the bubble," the report is not done. Translate it into
one of:

- move this producer earlier
- move or narrow this wait
- reduce this barrier imbalance
- change this work assignment
- change this memory layout
- gather a comparison profile because the current evidence is insufficient

Then retest. Kernel engineering progress comes from closing that loop, not from
describing the bubble.
