# Experimental protocol

## Questions and controlled comparisons

1. **Scheduling overhead:** Compare static blocks against dynamic/guided chunks 1, 16, 64, 256, 1024 on uniform graphs. Include every OpenMP strategy at p=1 to measure overhead against the serial loop. Keep algorithm parameters, graph bytes, executable and iteration count fixed.
2. **Load imbalance:** Compare clustered skewed rows and a hub graph. Test whether edge balance reduces assigned-edge max/mean and wall time together; a reduced edge ratio alone is not proof of better performance. A single hub should expose the row-granularity limit.
3. **Locality:** Compare local versus permuted copies with the same topology, then close versus spread thread affinity. Relabeling also redistributes expensive rows, so examine degree and thread-work statistics before attributing all differences to caches.
4. **Scaling:** Sweep 1,2,4,8,... physical cores, include non-power-of-two counts, then separately label any SMT or multisocket experiments. Use several graph sizes and at least two real graphs. Determine whether speedup saturates consistently across distributions and repeats.
5. **Preprocessing tradeoff:** Compare kernel and total time, particularly for small graphs/few iterations where partition setup may dominate. Partition cost is amortized only within a solve in this implementation.

## Execution procedure

Build release once per toolchain/flag set. Run correctness and sanitizer suites first. On ARC, reserve one compute node with enough physical cores and memory, verify CPU topology with `lscpu`, and avoid performance runs on login nodes. Adapt scripts to the permitted scheduler resources. Do not compare measurements from different node types without labeling them.

Use `OMP_DYNAMIC=FALSE`, `OMP_PLACES=cores`, and a documented `OMP_PROC_BIND=close` or `spread`. Save the actual affinity mask and environment. macOS affinity behavior and heterogeneous performance/efficiency cores differ from a homogeneous HPC node; laptop results are exploratory.

For a separate placement diagnostic, enable `OMP_DISPLAY_AFFINITY=TRUE` if supported by the runtime and retain stderr. The runner's process affinity mask identifies allowed CPUs; it does not identify every worker's final binding. Keep diagnostic output separate from final timing experiments.

Use fixed iterations (`--tolerance 0`, default in the runner), at least 100 iterations for the final study, and enough work for timings to exceed timer/scheduler noise. Do a converged-run study separately with identical tolerances. Start with at least seven measured repeats per configuration; inspect variability and increase repetitions when confidence intervals overlap. One warmup per invocation is the default. Each measured command also performs a serial verification outside timing, so these are warm repeated-solve experiments, not cold-cache experiments.

The runner shuffles all configurations inside each repeat block with a saved seed. It does not parallelize benchmark processes. It aborts on an error, failed correctness check or actual team size different from requested size, leaving partial raw output for diagnosis. A missing `finished_utc` in metadata marks an interrupted/incomplete run. The analyzer requires a serial baseline in the same block and identical iteration counts before forming a speedup; incomplete blocks may need to be excluded explicitly. Do not treat partial outputs as a complete matrix.

Example on an allocated compute node:

```sh
OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close python3 scripts/benchmark.py --graph data/uniform.mtx --graph data/skewed.mtx --threads 1,2,3,4,8,16 --chunks 0,16,64,256 --iterations 100 --repeats 7 --output results/arc-close
python3 scripts/analyze.py results/arc-close/raw.jsonl --output results/arc-close/summary.csv
python3 scripts/analyze.py results/arc-close/raw.jsonl --metric total_seconds --output results/arc-close/total-summary.csv
```

Repeat in a new run directory for spread affinity. Add hub/local/permuted controls and real datasets. Sweep sizes first with a smaller configuration matrix, then expand chunks around useful regions; retain all outcomes rather than reporting only the fastest chunk. Report the selected tuning procedure and avoid choosing a separate unseen best case for every data point.

## Metrics and evidence

- Kernel runtime: wall time of the iterative region, including its synchronization; excludes setup/partitioning.
- Total solve runtime: setup plus kernel plus team exit; graph IO and result validation are excluded.
- Speedup: median of paired `serial_time(block)/variant_time(block)` values, against the serial implementation, not OpenMP p=1.
- Efficiency: speedup divided by actual p. Plot a horizontal ideal line at 1; superlinear results require cache/noise investigation.
- Throughput: `m * completed_iterations / median_runtime`, a logical edge-traversal rate, not measured memory bandwidth.
- Variability: min/max, median absolute deviation (MAD), coefficient of variation; bootstrap median speedup using 2,000 seeded block resamples. These percentile intervals are descriptive, especially with few repeats; they do not remove thermal or node-sharing bias.
- Work/time imbalance: max divided by mean cumulative incoming edges or update seconds per thread, from separate instrumented runs.

Record max incoming degree, indegree coefficient of variation, dangling and isolated counts. Explain why graph size, skew and row ordering affect a policy. An apparent bandwidth plateau requires supporting counters or bandwidth measurements; elapsed time alone cannot distinguish bandwidth, latency, false sharing, dispatch overhead or barrier waits.

Buffers and CSR are serially initialized. For multisocket analysis, explicitly compare default placement against a documented `numactl --interleave=all` experiment if permitted, keeping the CPU mask unchanged. Do not claim first-touch optimization from this version. `OMP_PROC_BIND=spread` changes placement of workers, not allocation policy.

## Evidence to preserve for submission

Keep `metadata.json`, `commands.jsonl`, `raw.jsonl`, the `source/` snapshot, summary CSVs, generator commands, dataset hashes and all plots for every run. Raw results and plots are Git-ignored to avoid accidental large commits; archive chosen evidence deliberately with the report. The runner snapshots source/build/scripts/tests and hashes those files, including untracked implementation files. This preserves an exploratory working tree in addition to git metadata; commit the final source before definitive experiments and retain the binary hash. Always rebuild after source changes: the snapshot identifies the current source but does not itself prove that a stale binary was rebuilt.

Record the node, sockets, physical cores/SMT, cache sizes, NUMA topology, memory, compiler/runtime, flags, affinity, scheduler request, graph sources/semantics, seeds, damping/tolerance/iteration limits and repetitions. Write findings as observations tied to a run identifier. Keep hypotheses separate from hardware-counter evidence.
