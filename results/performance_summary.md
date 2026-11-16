# ARC PageRank performance summary

All values come from the committed ARC measurements. The source CSVs and raw files were left unchanged.

## Highest reported paired speedup at 16 threads

Selection maximizes the reported median **paired serial speedup**, using the same seven repeats for tuning and reporting. This is exploratory selection, not held-out evidence of a universally best configuration. Chunk 0 is static block scheduling or dynamic/guided default 1. Edge-balanced does not use a chunk.

| Graph | Node | Strategy | Chunk | Median kernel ms | Paired speedup | Efficiency | Speedup interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| uniform | c11 | edge-balanced | 0 | 25.038 | 8.702× | 54.39% | 8.558–8.928 |
| skewed | c11 | edge-balanced | 0 | 80.867 | 3.255× | 20.34% | 3.135–3.458 |
| hub | c12 | dynamic | 64 | 174.152 | 1.428× | 8.93% | 1.330–1.558 |
| local | c13 | edge-balanced | 0 | 15.757 | 11.023× | 68.90% | 10.734–12.085 |
| local-permuted | c14 | static | 0 | 25.936 | 7.722× | 48.26% | 7.429–8.191 |

Speedup = median over repeat blocks of `T_serial(block) / T_parallel(block)`; efficiency = speedup / p. It is **not** generally serial median divided by parallel median. Intervals are the original seeded bootstrap percentile intervals from `scripts/analyze.py`.

## Lowest median kernel runtime at 16 threads

Runtime minimization gives different winners on skewed and hub, because ratios and medians do not commute. Both rankings are shown instead of silently changing the definition of best.

| Graph | Strategy | Chunk | Median kernel ms | Paired speedup | Efficiency |
| --- | --- | --- | --- | --- | --- |
| uniform | edge-balanced | 0 | 25.038 | 8.702× | 54.39% |
| skewed | dynamic | 16 | 80.570 | 3.144× | 19.65% |
| hub | dynamic | 256 | 172.392 | 1.373× | 8.58% |
| local | edge-balanced | 0 | 15.757 | 11.023× | 68.90% |
| local-permuted | static | 0 | 25.936 | 7.722× | 48.26% |

## Hardware and evidence boundaries

| Run | Measurements | Node | CPU model | Sockets × cores/socket | Threads/core |
| --- | --- | --- | --- | --- | --- |
| full-341571-pr-uniform-100k-1m | 462 | c11 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 2 |
| full-341570-pr-skewed-100k-1m | 462 | c11 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 2 |
| full-341572-pr-hub-100k-1m | 462 | c12 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 1 |
| full-341573-pr-local-100k-1m | 462 | c13 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 1 |
| full-341574-pr-local-permuted-100k-1m | 462 | c14 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 1 |
| profile-341576 | 216 | c11 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 2 |
| locality-341577 | 924 | c11 | Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz | 2 × 8 | 2 |

- All node metadata names Xeon Silver 4110, but c11 reports SMT=2 and c12–c14 SMT=1. Cross-graph timings are independent jobs with different hardware configurations; graph structure is not the only changing factor. Each speedup uses its own graph/run serial baseline.
- Both locality graphs were measured in job 341577 on c11. This reduces node-type confounding. It does not measure cache misses or prove a memory-bandwidth mechanism. The original edge files are not committed, so exact graph isomorphism was not independently rechecked locally; their recorded n, m and degree statistics agree.
- Only close affinity is present. No spread comparison or hardware-counter plots can be produced from the supplied evidence.
- Profiling job 341576 contains only skewed and hub (3 repeats). Its instrumented runtime is kept separate from all non-profiled timing comparisons. Blank non-profiled imbalance fields remain missing.

## Observations and limitations

- Uniform/local scale much better than the hub in their respective jobs. Edge-balanced has the highest reported p=16 speedup on uniform and local. The hub remains near serial speed despite 16 workers.
- Small dynamic chunks have substantial overhead in these measurements; inspect the chunk-sensitivity panels rather than assuming dynamic scheduling is inherently slow. Runtime dispatch, scattered ownership and memory effects are possible explanations, not directly measured causes.
- Edge-balanced work metrics must be read with update-time imbalance and kernel runtime. Whole rows are indivisible, so one high-indegree hub cannot be distributed across workers by this implementation.
- Local p=16 edge-balanced has high variability (CV 0.481); min–max ranges and bootstrap intervals are retained. No outliers were removed.
- Fixed-configuration scaling uses static=0, dynamic=64, guided=64, edge-balanced=0 at every graph and thread count. No curve joins a different best chunk at each point. Separate winner charts are explicitly post-hoc tuning.
- Kernel and total solve time are separate. Derived total summaries use existing raw `total_seconds`; they exclude graph loading and include setup. They never replace the original kernel summaries.
- No confident universal winner or cache-miss explanation follows from these experiments alone.

## Reproduce and inspect

See [figure guide](../plots/README.md), [validation report](../plots/arc/validation.json), and [figure provenance](../plots/arc/figures.json).
Every measured plotted coordinate and band endpoint is traceable to a CSV row/column; derived totals, graph properties and worker ratios are stored separately under the plot output directory.
