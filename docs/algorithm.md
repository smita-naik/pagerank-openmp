# Algorithm, correctness and optimization

For `n > 0`, initialize `r[v] = 1/n`. With damping `d = 0.85`, use:

```text
D = sum(r[u] for outdegree[u] == 0)
c[u] = r[u] / outdegree[u] if outdegree[u] > 0 else 0
next[v] = (1 - d + d*D)/n + d * sum(c[u] for edges u -> v)
delta = sum(abs(next[v] - r[v]))
swap(r, next)
stop if tolerance > 0 and delta <= tolerance
```

The dangling term redistributes mass uniformly. Every non-dangling vertex distributes its full rank along its outgoing edges, so the exact-arithmetic rank sum stays one and all ranks remain nonnegative. Parallel edges contribute repeatedly to both the outdegree and the incoming sum; this defines a directed multigraph random walk. On the two-vertex chain `0 → 1`, the exact stationary ranks are `(1/2.85, 1.85/2.85)`, which is tested independently.

The stochastic transition with damping below one is an L1 contraction. The implementation reports the difference between consecutive iterates, not the unknown distance to the fixed point. A fixed-point error bound for the returned iterate is `d/(1-d) * delta` in exact arithmetic. Tolerance zero intentionally disables early stopping. The project uses identical parameters and fixed iterations for runtime comparisons; separate converged runs assess numerical behavior.

## Representation and memory

Incoming CSR stores `offsets[v..v+1]` and 32-bit source IDs; offsets and outdegrees use 64-bit counts. The vertex count is limited to `UINT32_MAX`. Original edge order is preserved within incoming rows. Graph construction uses counting and prefix sums rather than sorting. It takes O(n+m) time and temporarily retains the edge list and an insertion cursor. Input is not streamed directly into a final CSR and the construction peak must fit memory.

The steady graph storage is approximately `24n + 4m + 8` bytes, excluding vector metadata/capacity. Three double vectors (rank, next, contribution) add `24n` bytes during a solve. Thus the main working set is approximately `48n + 4m` bytes, plus partitions and profiling counters. The transient loader additionally holds edge pairs and a cursor; edge vector capacity can exceed its length.

Cached inverse outdegrees remove division from the iteration. A static vertex loop computes contributions once per iteration, replacing repeated source-rank/outdegree operations inside the irregular incoming-edge traversal with one contribution lookup. The reference and all parallel variants share this optimization. There is no floating-point atomic addition and every output row has exactly one owner.

## Parallel execution and synchronization

One OpenMP parallel region encloses all iterations. The contribution/dangling loop uses static scheduling and a reduction. The incoming update uses `schedule(runtime)` for static/dynamic/guided and a convergence reduction. `omp_set_schedule` selects the policy consistently before team creation. Static with chunk 0 uses contiguous block scheduling; a positive chunk uses cyclic blocks. Dynamic/guided chunk 0 maps to 1. The caller's schedule and dynamic-team settings are restored after a solve.

Contributions and dangling mass finish at the first worksharing barrier. Each worker then computes a private base term, avoiding a single-region barrier. The update reduction has `nowait`, followed by an explicit barrier before the buffer swap; this lets optional thread timers finish before waiting for other workers. The swap, convergence decision and reduction-scalar resets share one `single` region and its implicit barrier. Every worker takes the same exit decision. There are three synchronization barriers per iteration; no separate barrier is needed for scalar resets or base calculation. Buffers are allocated once per solve, outside the iteration loop.

Synchronization and reductions have real costs. This implementation favors clear, portable correctness; it does not claim to eliminate barrier overhead. Very small graphs and excessive thread counts can lose to serial execution. Floating-point reductions may associate terms differently, so reproducibility means numerical agreement within tolerance rather than bitwise identity. See the [OpenMP reduction specification](https://openmp.org/spec-html/5.2/openmpsu52.html).

## Edge-balanced partitioning

`offsets[v]` already equals the prefix sum of incoming degrees before vertex `v`. For `p` actual workers, find internal cuts by lower-bounding targets `floor(t*m/p)` in this prefix sum; use endpoints 0 and n. This costs O(p log n), uses O(p) extra memory, and is done once inside the team setup. One contiguous range is assigned to each worker and reused for every iteration. Partition using the **actual** team size, not a promised/requested count. If there are no edges, divide vertices equally. Repeated cuts and empty ranges are valid when there are more workers than useful ranges.

This strategy balances edge counts approximately, not exactly. A row is indivisible: one hub with indegree `H` takes at least O(H) work on a single worker. A lower bound on update work is `max(m/p, max_indegree)`. Long runs of zero-degree rows also cost O(rows), yet contribute nothing to the edge prefix sum. Equal edges do not imply equal cache-miss rates, instruction counts or elapsed time. Splitting giant rows or balancing `degree + row_cost` would address different limitations but is outside this variant, which deliberately tests pure incoming-edge balance.

Contiguous ownership can improve CSR streaming and output locality versus scattered dynamic chunks. Contribution lookups remain irregular and can be cache- or bandwidth-limited. Initialization and graph loading are serial first-touch operations; this version does not promise NUMA-aware placement. Run affinity and interleave experiments explicitly on multisocket machines. Vertex relabeling changes both cache locality and the degree ordering seen by schedulers, so its effect must be interpreted jointly with load diagnostics. Partition construction and team setup are included in total time even when excluded from kernel time.

## Profiling semantics

`--profile` selects an instrumented solver instantiation. Per-thread counters sum assigned rows and incoming edges across all completed iterations. Timers measure update work, runtime dispatch and reduction completion up to the explicit barrier, and exclude that barrier's waiting time. They do not isolate pure arithmetic or count all idle time. Max/mean counters expose cumulative load distribution; cumulative time ratios can hide iteration-to-iteration variation. Normal timing builds skip these counters/timers through compile-time specialization. All variants should be profiled separately with the same settings.
