# Optimizing PageRank on Multicore CPUs

CSC 548: Parallel Systems final project — Smita Naik, NCSU, Fall 2026.

This project investigates how scheduling, load balancing, and memory locality affect PageRank performance and scalability on multicore CPUs using C++ and OpenMP.

## Project status

Repository setup is complete. Implementation and experimental results are pending.

## Planned implementation

- A serial PageRank reference using a compressed sparse graph representation (CSR).
- An OpenMP implementation with static, dynamic, and guided scheduling.
- A degree-aware or edge-balanced partitioning strategy.
- Correctness checks comparing parallel ranks with the serial reference.
- Experiments on graphs with different sizes and degree distributions.

## Evaluation

Run experiments on NCSU ARC multicore CPU nodes and record the CPU model, core count, compiler version and flags, OpenMP configuration, graph source, and algorithm parameters.

Compare execution time, speedup (`T1 / Tp`), and parallel efficiency (`speedup / p`) across thread counts and scheduling strategies. Use profiling to investigate load imbalance, memory behavior, and scaling limits. Record the chosen single-thread baseline consistently with each result.

## Repository layout

```text
src/          C++ implementation
tests/        Correctness tests and small graph fixtures
scripts/      Experiment and analysis scripts
data/         Local graph datasets (ignored by Git)
results/      Experiment output (ignored by Git)
docs/         Methodology and project documentation
```

The original [project proposal](Smita_Naik_Parallel_System_Proposal.pdf) is included for reference. Build and run instructions will be added with the implementation.

## Development roadmap

- [ ] Implement serial PageRank and graph loading.
- [ ] Add correctness tests and initial profiling.
- [ ] Implement OpenMP PageRank and thread scaling experiments.
- [ ] Compare static, dynamic, and guided scheduling.
- [ ] Implement edge-balanced work distribution.
- [ ] Collect reproducible timings and profiling measurements.
- [ ] Produce runtime, speedup, and efficiency plots.
- [ ] Complete the final report and presentation.
