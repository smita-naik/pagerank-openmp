# Optimizing PageRank on Multicore CPUs: Scheduling, Load Balancing, and Memory Locality

Smita Naik — CSC 548, NCSU — Fall 2026

## Status and scope

Implementation, reproducibility tools and correctness tests are provided. This report source documents the method and reserves the final claims for measured experiments. See [measured local validation](local-validation.md) for the completed exploratory evaluation and archived evidence. ARC scaling, hardware-counter analysis and the final presentation remain to be completed using the supplied scripts. No cluster result is implied by a local measurement.

## Problem and research questions

PageRank's pull update traverses incoming edges while reading a source-indexed contribution vector. Irregular indegrees make equal-vertex partitions unequal in work. Dynamic scheduling can redistribute rows at a runtime cost; contiguous edge-balanced partitions trade preprocessing for stable ownership. This project asks which strategy is fastest under controlled graph distributions, how its scalability changes with thread count, and what load and memory evidence explains the change.

## Method

Use incoming CSR, double precision, uniform initialization, damping 0.85, double buffering, inverse outdegree caching and uniform dangling redistribution. Preserve duplicates as parallel edges and document the chosen vertex universe. The serial reference shares the arithmetic and storage optimizations with the parallel versions. The five execution strategies differ in update ownership, not in the PageRank formula. The contribution loop is statically partitioned for every parallel strategy.

Static/dynamic/guided use OpenMP runtime scheduling; edge-balanced lower-bounds incoming-degree prefix targets and assigns one contiguous range per actual worker. All parallel solvers use one persistent team. Numerical agreement is checked with a serial solve; small graphs additionally use analytic answers and an independent dense oracle. See [implementation details](../docs/algorithm.md).

## Experimental design

Follow [the protocol](../docs/experiments.md). Include uniform, skewed, hub, local and permuted-local families at sizes crossing cache capacities, plus public directed graphs. On one ARC CPU-node type, use physical-core counts from one to the allocation limit, chunk sweeps, seven or more randomized repeat blocks and separate close/spread affinity runs. Compare serial-based speedup and efficiency at a fixed iteration count. Collect total time to assess preprocessing amortization. Collect thread diagnostics separately, then obtain hardware counters if permitted.

The final hardware table must identify the actual node model, sockets, cores/SMT, caches, NUMA configuration, memory, compiler/runtime, flags and affinity. Each graph table must identify its source/hash, vertex-ID semantics, n, m, max indegree, degree variation, dangling and isolated counts. These tables must come from run metadata rather than guessed machine specifications.

## Results to fill from ARC evidence

- Runtime, speedup and efficiency plots with variability and all tested strategies.
- Chunk sensitivity on uniform and skewed graphs; quantify dispatch versus load-balance tradeoffs.
- Per-thread edge/time ratios and the hub lower bound.
- Paired topology-preserving relabeling experiments with cache evidence where available.
- Kernel versus total solve time, including partition cost and iteration-count amortization.
- Affinity and socket-boundary behavior with stated memory-placement policy.

For each finding, state graph/run identifier, numeric effect size, variability and evidence supporting the explanation. A negative result is meaningful if the comparison is controlled. Avoid declaring one scheduler universally best.

## Threats to validity and limitations

Reduction ordering can change low bits or convergence iteration counts, so scaling uses fixed iterations. Small graphs magnify barrier and dispatch costs. Laptop heterogeneous cores and thermal effects limit transfer to ARC. Warmups/serial verification create warm repeated-solve conditions. Pure edge partitioning ignores per-row overhead and cannot split a giant row. CSR and buffers are serially first-touched, limiting multisocket conclusions without placement controls. Logical edge throughput is not measured DRAM bandwidth. Whole-process perf counters include loading. Synthetic controls are not substitutes for real graphs; raw sparse IDs can introduce additional isolated vertices. Too few repeats give weak uncertainty estimates.

## Conclusion to complete after evaluation

State which policy benefits which graph family, the thread range in which benefits persist, and where overhead, giant rows or memory effects limit scaling. Distinguish observations from inferred explanations. Final quantitative conclusions require the remaining ARC experiment matrix.

## References

- [Approved proposal](../Smita_Naik_Parallel_System_Proposal.pdf).
- [OpenMP specification](https://www.openmp.org/specifications/) and [reduction semantics](https://openmp.org/spec-html/5.2/openmpsu52.html).
- [NIST Matrix Market format](https://math.nist.gov/MatrixMarket/formats.html).
- [SNAP Wikipedia vote data](https://snap.stanford.edu/data/wiki-Vote.html) and [Google web graph](https://snap.stanford.edu/data/web-Google.html); include their requested dataset citations in the final submission.
- [NCSU parallel job guidance](https://hpc.ncsu.edu/RunningJobs/Parallel.php) and [scheduler transition status](https://hpc.ncsu.edu/RunningJobs/Status.php).
