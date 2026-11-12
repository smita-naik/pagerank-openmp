# Initial synchronization baseline: exploratory local evaluation

This archive describes the earlier five-barrier version. See [current results](local-validation.md) for the three-barrier implementation. These are local Apple M4 results, not ARC results or final cluster conclusions. The implementation was built with Apple LLVM 17 at `-O3`, C++17, without fast-math, using Homebrew libomp 23.1.5. See [hardware details](local-hardware.txt) and archived source/metadata for exact flags. The OpenMP compile-time macro is 202011.

## Evidence and reproducibility

The final local timing matrix contains **924 verified measured solves**: six graphs × 22 strategy/thread/chunk configurations × seven randomized blocks, each using 100 fixed iterations, damping 0.85, tolerance 0 and one unreported warmup. Parallel thread counts are 1, 2 and 4. Static/dynamic/guided use chunk values 0 and 64; serial and edge-balanced use 0. Chunk 0 means static blocks or dynamic/guided minimum chunk 1. A serial verification solve precedes warmups in each command. A separate instrumented experiment contains **90 solves**: six graphs × five configurations (serial p=1 and each parallel policy p=4) × three blocks, also at 100 iterations. Earlier smoke runs remain in `results/local-study`, `results/local-profile` and `results/local-wiki`; the tables here use only `local-evaluation` and `local-evaluation-profile`.

Source snapshots, per-file source hashes, binary/dataset hashes, commands, raw JSON, summaries and environment are preserved in [the evidence archive](evidence/local-evaluation.tar.gz). Selected CSVs and figures are also directly readable in `report/evidence/`. The binary hash is recorded, while machine-specific binaries and graph files are not committed. Rebuild from the source snapshot and reproduce synthetic data with the commands below. Public dataset retrieval metadata is included. Original absolute paths identify the run's machine; adapt paths when reproducing.

```sh
python3 scripts/generate_graph.py --kind uniform --vertices 20000 --edges 200000 --seed 548 --output data/local-study-uniform.mtx
python3 scripts/generate_graph.py --kind skewed --vertices 20000 --edges 200000 --seed 548 --output data/local-study-skewed.mtx
python3 scripts/generate_graph.py --kind hub --vertices 20000 --edges 200000 --seed 548 --output data/local-study-hub.mtx
python3 scripts/generate_graph.py --kind local --vertices 20000 --edges 200000 --seed 548 --output data/local-study-local.mtx
python3 scripts/generate_graph.py --kind local --vertices 20000 --edges 200000 --seed 548 --permute --output data/local-study-permuted.mtx
python3 scripts/fetch_dataset.py wiki-Vote
```

The hardware has four performance and six efficiency cores, 16 GiB RAM, and macOS 15.7.3. Workers were not pinned to a known performance-core subset. Only `OMP_DYNAMIC=FALSE` was set explicitly for these runs. The sandbox blocked the benchmark's sysctl query; its error is preserved, and a separate permitted hardware query supplies the hardware note. These are warm repeated-solve measurements on a shared interactive computer. They do not establish homogeneous-core, multisocket, NUMA or DRAM-bandwidth behavior.

## Correctness

Release and AddressSanitizer/UndefinedBehaviorSanitizer runs passed 14,143 C++ assertions and 43 CLI/input cases. Four Python experiment tests also pass, including a subprocess benchmark-to-summary integration test. Small-graph tests compare against analytic values and an independent dense transition-matrix oracle. No failure or nonfinite rank was observed in the timing matrix. All ranks passed L1 ≤ 1e-8 and Linf ≤ 1e-9 against the serial reference; observed maximum errors are listed below. Floating-point equality is not assumed.

Maximum observed timing-matrix verification errors: **L1 1.641e-14**, **Linf 5.551e-17**.

## Graph structure

| Graph | n | m | Max indegree | Indegree CV | Dangling | Isolated |
| --- | --- | --- | --- | --- | --- | --- |
| hub | 20000 | 200000 | 179760 | 127.106 | 0 | 0 |
| local | 20000 | 200000 | 23 | 0.318 | 1 | 0 |
| permuted | 20000 | 200000 | 23 | 0.318 | 1 | 0 |
| skewed | 20000 | 200000 | 28881 | 25.021 | 1 | 0 |
| uniform | 20000 | 200000 | 25 | 0.317 | 1 | 0 |
| wiki-Vote | 8298 | 103689 | 457 | 2.386 | 2188 | 1183 |

Raw numeric IDs are retained. For wiki-Vote, 1,183 gaps become isolated vertices, producing n=8,298 and m=103,689. This is a documented vertex-universe choice and is not the compact active-vertex graph in the source statistics. Synthetic local and permuted graphs are the same topology under a seeded relabeling and have identical degree statistics.

## Runtime and four-thread speedup

Serial times are median kernel milliseconds. Speedups are medians of the seven block-paired serial/variant ratios; a ratio of median runtimes may differ slightly. Every policy/thread/chunk result, variability metric and bootstrap interval is retained in [the full summary](evidence/summary.csv).

| Graph | Serial ms | Static blocks | Dynamic 1 | Dynamic 64 | Guided 1 | Edge balanced |
| --- | --- | --- | --- | --- | --- | --- |
| hub | 27.369 | 0.957 | 0.246 | 1.002 | 0.972 | 0.977 |
| local | 24.337 | 1.853 | 0.220 | 1.778 | 1.864 | 1.667 |
| permuted | 24.197 | 1.737 | 0.196 | 1.694 | 1.720 | 1.625 |
| skewed | 23.662 | 0.913 | 0.204 | 1.221 | 0.971 | 1.141 |
| uniform | 24.233 | 1.755 | 0.195 | 1.696 | 1.773 | 1.605 |
| wiki-Vote | 9.451 | 0.909 | 0.173 | 0.934 | 0.903 | 0.962 |

On the skewed graph, edge balance improves four-thread runtime compared with static blocks while attaining only a modest speedup over serial. Dynamic chunk 64 is faster still. Dynamic chunk 1 is slower than serial across these small graph families; its high dispatch frequency is a plausible explanation supported by the chunk comparison, though runtime attribution with Linux perf is still needed.

On the hub graph, all useful parallel strategies stay near serial performance. On the vote graph, edge balancing also fails to produce a four-thread speedup. These outcomes demonstrate why balanced assigned edges alone are insufficient evidence of scalable performance.

## Assigned-edge imbalance

Separate profiling runs measure max/mean cumulative incoming edges per worker. Ratios near one indicate balanced edge ownership; this says nothing by itself about cache misses, contribution-pass cost or barrier overhead.

| Graph | Static blocks, p=4 | Edge balanced, p=4 |
| --- | --- | --- |
| hub | 3.69686 | 3.59520 |
| local | 1.00794 | 1.00006 |
| permuted | 1.00424 | 1.00016 |
| skewed | 3.67300 | 1.02690 |
| uniform | 1.00508 | 1.00024 |
| wiki-Vote | 1.28241 | 1.00153 |

Skewed edge imbalance falls from 3.673 to 1.0269. In contrast, the hub has 179,760 of 200,000 edges in a single incoming row. Since rows are indivisible, the max/mean edge-work lower bound at p=4 is `179760 / 50000 = 3.5952`, exactly attained by the edge-balanced partition. This provides a structural explanation for its failure to distribute that row across workers. The pure edge-traversal model's speedup ceiling is only `m / max_indegree ≈ 1.113`, before considering other phases and scheduling costs.

The vote graph's edge ratio also becomes nearly one, yet its wall time remains near serial. Fixed synchronization/row work, memory access, and interactive-machine noise are candidate causes; the current data cannot uniquely identify them.

## Setup cost

For edge-balanced p=4, partition construction is timed independently and included in setup. The table gives median partition/setup microseconds and median total solve milliseconds. Team entry/exit and buffer initialization also contribute to setup. A fair preprocessing comparison must use total time, especially when reducing the number of iterations.

| Graph | Partition µs | Setup µs | Total ms |
| --- | --- | --- | --- |
| hub | 0.62 | 40.04 | 28.071 |
| local | 0.62 | 44.58 | 14.268 |
| permuted | 0.83 | 79.33 | 15.063 |
| skewed | 0.83 | 82.50 | 20.827 |
| uniform | 0.88 | 84.00 | 15.541 |
| wiki-Vote | 0.83 | 59.79 | 9.861 |

See [total-time summaries](evidence/total-summary.csv). These measurements amortize setup over 100 iterations; a final study should also sweep shorter solves to find the crossover where setup matters.

## Locality and uncertainty

The local/permuted comparison does not justify a cache-miss or bandwidth claim. Their serial medians are similar, while some parallel cases differ and show substantial run variation. Relabeling changes contribution addresses and row ordering together. Counter evidence, larger graphs crossing known cache sizes, and controlled worker/memory placement are necessary to explain causality.

No outliers were removed. The following are the five largest coefficients of variation in the timing matrix; max/median exposes occasional severe interruptions. Inspect raw samples and use the repeated ARC runs before relying on these cases. Bootstrap median intervals do not eliminate systematic laptop interference.

| Graph | Policy | p | Chunk | CV | Max/median |
| --- | --- | --- | --- | --- | --- |
| local | dynamic | 4 | 64 | 2.646 | 77544.31 |
| permuted | dynamic | 1 | 64 | 0.747 | 3.85 |
| permuted | guided | 4 | 0 | 0.726 | 3.75 |
| uniform | static | 2 | 0 | 0.415 | 2.29 |
| local | edge-balanced | 2 | 0 | 0.372 | 2.14 |

## Remaining ARC work

Run the supplied Slurm template after selecting the appropriate account/partition and compiler environment. Evaluate additional graph sizes, at least a second real graph, all allocated physical cores, broader chunk sweeps and close/spread affinity. Capture topology, NUMA placement and hardware counters where allowed, plus kernel-versus-total timing. Complete the final report and presentation using those measurements. No cluster job was submitted and no ARC timing, hardware-counter or NUMA result is asserted here.
