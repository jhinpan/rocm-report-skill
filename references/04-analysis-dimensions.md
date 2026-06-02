# Analysis Dimensions

Walk all dimensions before proposing code. Most wrong optimization plans come
from stopping after the first visible hotspot.

## 1. Launch Geometry and Saturation

Question: does the grid produce enough CTAs and waves to fill the GPU?

Signals:

- total CTAs
- waves per CU
- tail wave size
- active CU utilization over time

If the workload cannot fill the chip, communication/compute overlap inside one
CTA will not fix global under-fill.

## 2. Tail and Load Imbalance

Question: do some CTAs finish much later than others?

Signals:

- gradual utilization tail
- per-CTA variable work
- barriers where some waves wait for slower waves

Code hypotheses:

- split large work items
- increase work granularity
- use persistent/work-queue style assignment
- rebalance sequence/page/token ownership

## 3. Dependency Waits

Question: are waits blocking consumers before useful independent work is done?

Signals:

- hot `s_waitcnt vmcnt(...)` or `lgkmcnt(...)`
- adjacent VMEM/LDS producer and MFMA/VALU consumer
- sawtooth timeline, alternating load and compute phases

Code hypotheses:

- move producer earlier
- narrow the wait
- split one wide wait into per-resource waits
- increase staging depth if VGPR/LDS budget allows
- reorder independent math into the wait gap

## 4. MFMA Feed and Compute Utilization

Question: are matrix instructions starved or issued steadily?

Signals:

- low MFMA instruction share for GEMM-like kernels
- MFMA source lines separated by wait-heavy regions
- accumulator/VGPR occupancy constraints

Code hypotheses:

- prefetch next K/V tile
- double-buffer LDS
- pipeline MFMA with LDS/VMEM
- reduce per-wave register pressure if it limits occupancy

## 5. VMEM, LDS, and Bank/Access Patterns

Question: are memory instructions efficient enough to feed the schedule?

Signals:

- VMEM-load or LDS instruction classes dominate stalls
- LDS bank conflict counters
- non-coalesced or strided source lines
- high store pressure in epilogue

Code hypotheses:

- change lane-to-element mapping
- vectorize or de-vectorize loads according to alignment
- swizzle LDS layout
- split or fuse stores only if epilogue dominates

## 6. Source Attribution Quality

Question: can we trust the source line map?

Signals:

- mapped row percentage
- top source lines
- number of distinct mapped source lines
- helper/decorator collapse

If attribution quality is poor, file or fix source-location support first. Do
not infer a schedule rewrite from a collapsed line.

## 7. Baseline Comparison

Question: what does a known-good implementation do differently?

Compare FlyDSL against AITER, CK, hipBLASLt, Triton, or an older branch when
available. The comparison should use the same shape and GPU, not a nearby
benchmark.
