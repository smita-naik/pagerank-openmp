# Profiling and interpreting memory behavior

First collect low-overhead timing runs without `--profile`. Then use separate diagnostic runs:

```sh
OMP_PLACES=cores OMP_PROC_BIND=close python3 scripts/benchmark.py --graph data/skewed.mtx --threads 1,2,4 --repeats 3 --iterations 100 --profile --output results/skewed-profile
python3 scripts/analyze.py results/skewed-profile/raw.jsonl --output results/skewed-profile/summary.csv
```

Thread stats account for exactly `n*iterations` rows and `m*iterations` edges across the team, which is tested automatically. `max/mean` edges highlights assignment imbalance. Update times include scheduler/reduction overhead and may be noisy for short phases. These timers do not measure the entire iteration, contribution-loop time or explicit-barrier idle time. Profiling changes execution costs and should not be mixed into the primary performance matrix.

On a Linux compute node with perf access:

```sh
python3 scripts/profile.py --output results/perf-static --repeats 5 -- --graph data/skewed.mtx --strategy static --threads 8 --iterations 1000 --tolerance 0
python3 scripts/profile.py --output results/perf-balanced --repeats 5 -- --graph data/skewed.mtx --strategy edge-balanced --threads 8 --iterations 1000 --tolerance 0
```

The wrapper validates once before profiling, then profiles without the extra reference solve. It records commands and perf status. Counters cover the **whole process**, including IO, allocation and initialization; use enough iterations to amortize those costs and compare with JSON kernel/total/load timings. They are not kernel-only counter measurements. Check `perf.csv` for unsupported/not-counted events and multiplexing percentages; generic cache events have architecture-specific meanings. If counters are blocked by cluster policy, record that limitation and use the instrumented thread stats; do not change system permissions.

For code attribution, compile a separate build with `-O3 -g -fno-omit-frame-pointer`, then run `perf record -g -- build/profile/pagerank ...` and `perf report`. Inspect samples in the incoming-edge loop, scheduler and synchronization runtime. Use `perf list` for node-specific LLC, memory-controller and stall events; do not assume one event name works across Xeon and AMD nodes. Detailed bandwidth/NUMA analysis may need site-provided tools such as Intel VTune or LIKWID and administrator-approved access.

Investigate these hypotheses with evidence:

| Observation | Hypothesis | Additional evidence |
|---|---|---|
| Balanced edges but poor scaling | Cache/latency/bandwidth or barrier costs | Kernel attribution, cache/stall events, topology/affinity comparison |
| Dynamic small chunks slower on uniform graph | Runtime dispatch overhead | Chunk sweep and samples in runtime scheduling |
| Edge-balanced improves skewed graph | Reduced straggler work | Per-thread edge/time ratios, repeated wall-time benefit |
| Hub remains slow for every policy | Indivisible heavy row | Max indegree vs m/p and ownership stats |
| Permuted graph slower | Worse contribution locality, changed row ordering | Same topology check, workload stats, cache events |
| Spread worse across sockets | Remote accesses or placement | NUMA topology, default vs controlled memory placement |

Never infer a specific cache-miss mechanism solely from a speedup plot. Streaming CSR access does not make the contribution lookups sequential. On this Mac, Linux perf and ARC-specific measurements are unavailable; local plots must be labeled accordingly.
