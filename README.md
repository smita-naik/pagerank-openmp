# Optimizing PageRank on Multicore CPUs

CSC 548: Parallel Systems final project — Smita Naik, NCSU, Fall 2026.

This project investigates how scheduling, load balancing, and memory locality affect PageRank performance and scalability on multicore CPUs using C++ and OpenMP.

## Implementation

C++17, double-precision, pull-based PageRank with incoming CSR adjacency. All five variants use uniform initialization, damping 0.85 by default, dangling-mass redistribution, cached inverse outdegrees, a contribution buffer, and double-buffered ranks. The serial path has no OpenMP worksharing. Parallel paths keep one OpenMP team alive throughout each solve.

Implemented strategies: `serial`, `static`, `dynamic`, `guided`, and `edge-balanced`. The last partitions contiguous vertex ranges by incoming-edge prefix sums, once per solve. See [algorithm and limitations](docs/algorithm.md).

## Build and test

Linux with GCC and its OpenMP runtime:

```sh
make CXX=g++ -j4
make CXX=g++ test
make CXX=g++ sanitize
```

macOS with Apple Clang:

```sh
brew install libomp
make -j4
make test
make sanitize
```

For an Intel Mac, add `LIBOMP_PREFIX=/usr/local/opt/libomp`. Linux Clang needs its OpenMP development package. Override `OMPFLAGS`/`OMPLIBS` for other toolchains. Use a new `BUILD=build/other` directory when changing compiler or flags; make does not detect command-line flag changes. Default flags are `-O3 -std=c++17 -Wall -Wextra -Wpedantic`, without fast-math or architecture-specific instructions.

Tests cover analytic graphs, an independent dense transition-matrix oracle, randomized graphs, dangling/isolated vertices, duplicate edges, self-loops, hubs, empty edge sets, chunk sizes, more threads than vertices, profiling coverage, both input formats and malformed inputs. AddressSanitizer and UndefinedBehaviorSanitizer are separate from performance builds. Linux CI runs both suites.

## Run

```sh
python3 scripts/generate_graph.py --kind skewed --vertices 10000 --edges 100000 --output data/skewed.mtx
build/pagerank --graph data/skewed.mtx --strategy serial --iterations 1000 --tolerance 1e-10
build/pagerank --graph data/skewed.mtx --strategy dynamic --threads 4 --chunk 64 --verify
build/pagerank --graph data/skewed.mtx --strategy edge-balanced --threads 4 --verify --profile
```

Each measured solve prints one JSON record: graph structure, requested/actual threads, iteration count, convergence, L1 residual, rank sum, timings, compiler/flags, verification errors and optional thread diagnostics. `--help` lists all options. `--tolerance 0` forces exactly `--iterations` iterations; otherwise the maximum iteration count is a cap. A nonconverged capped run is reported explicitly, rather than treated as an input error. `--rank-output PATH` exports ranks in internal vertex-ID order and refuses to overwrite an existing file.

Convergence uses absolute L1 change between consecutive iterates. `--verify` checks ranks against a separate serial solve with the same parameters (L1 ≤ 1e-8 and Linf ≤ 1e-9). The dense-oracle tests use stricter L1 error < 1e-11. Floating-point reduction order can differ across runs; bitwise equality is not required.

## Datasets

Edge lists contain exactly `source destination`, zero-based by default, with `#`/`%` comments. Use `--index-base 1` for one-based edge lists. IDs must be dense nonnegative integers or gaps become isolated vertices; `--vertices N` preserves trailing isolated vertices. Empty edge lists require `--vertices N`.

Matrix Market input is **one-based, square, coordinate** format (`pattern`, `real`, or `integer`, `general` or `symmetric`). A coordinate `(row, column)` means `row → column`. Symmetric storage expands reverse off-diagonal edges. Explicit zeros are skipped; all other values are treated as unweighted edges. Duplicate entries/edges are preserved as parallel edges; self-loops are retained. No implicit symmetrization is applied to directed edge lists. Complex, skew-symmetric, Hermitian and array formats are rejected. See [dataset preparation](data/README.md) and the [NIST format specification](https://math.nist.gov/MatrixMarket/formats.html).

## Reproducible experiments

```sh
export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close
python3 scripts/benchmark.py --graph data/skewed.mtx --threads 1,2,4 --chunks 0,16,256 --repeats 7 --iterations 100 --output results/skewed-close
python3 scripts/analyze.py results/skewed-close/raw.jsonl --output results/skewed-close/summary.csv
python3 scripts/analyze.py results/skewed-close/raw.jsonl --metric total_seconds --output results/skewed-close/total-summary.csv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
MPLCONFIGDIR=/tmp/pagerank-matplotlib .venv/bin/python scripts/plot.py results/skewed-close/summary.csv --output plots/skewed-close
```

Choose threads within the allocated physical cores. Chunk 0 means static block scheduling or the runtime's dynamic/guided default of 1. Serial and edge-balanced do not accept nonzero chunks. The benchmark randomizes configuration order within each repeat block, verifies each solve, and records environment, CPU, source state, exact commands and binary/dataset SHA-256 hashes. Run directories and generated datasets refuse overwrites. Benchmarks default to fixed iterations for fair strong scaling.

Analysis reports median/min/max/MAD, coefficient of variation, paired serial speedup, efficiency, and a seeded bootstrap interval when at least three repeats are available. Three repeats are only a smoke test; use at least seven, inspect variance and rerun noisy cases. Plot shading represents the runtime min–max range or speedup bootstrap interval. Profile diagnostics should be collected separately from timing experiments.

`kernel_seconds` measures the iterative solve, excluding graph loading, buffer allocation and partition construction. `total_seconds` includes solve setup and team entry/exit; `setup_seconds = total_seconds - kernel_seconds`. `partition_seconds` is included in setup. `load_seconds` is separate. Rank validation, rank-sum calculation, output, and buffer destruction are outside solve timing. Compare both kernel and total time when evaluating preprocessing overhead.

See the [experimental protocol](docs/experiments.md), [profiling instructions](docs/profiling.md), and [report source](report/report.md). Local validation does not replace the final ARC experiments.

## Measured local validation

The [local analysis](report/local-validation.md) records 924 verified timing solves across six graphs and 90 separate profiling solves on an Apple M4. Release and address/undefined-behavior sanitizer suites pass 14,143 C++ checks, 43 CLI/input cases, and four experiment-script tests. The report includes measured speedups, workload imbalance, uncertainty, reproducible source snapshots, compressed raw evidence and selected figures. These results are exploratory; ARC scaling and Linux hardware-counter measurements remain pending.

## ARC execution

[Slurm template](scripts/arc.slurm) requests one node, one task and 16 CPUs; [legacy LSF template](scripts/arc.lsf) keeps all slots on one host. Adapt account, partition/queue, memory, compiler module and thread counts to your allocation. No job has been submitted automatically. NCSU's [current parallel-job guide](https://hpc.ncsu.edu/RunningJobs/Parallel.php) documents Slurm; consult its [migration status](https://hpc.ncsu.edu/RunningJobs/Status.php) before choosing a scheduler.

## Repository layout

```text
src/          C++ implementation
include/      Public graph and solver interfaces
tests/        Correctness tests and small graph fixtures
scripts/      Experiment and analysis scripts
data/         Local graph datasets (ignored by Git)
results/      Experiment output (ignored by Git)
docs/         Methodology and project documentation
plots/        Generated SVG/PDF figures (ignored by Git)
report/       Report source and measured local validation notes
```

The original [project proposal](Smita_Naik_Parallel_System_Proposal.pdf) is preserved.

## Development roadmap

- [x] Implement serial PageRank and graph loading.
- [x] Add automated correctness tests and profiling instrumentation.
- [x] Implement static, dynamic, guided and edge-balanced variants.
- [x] Add reproducible benchmark, analysis, plotting and ARC scripts.
- [x] Run local correctness, sanitizer, six-graph timing and profiling studies.
- [ ] Complete the full ARC dataset/thread/chunk/affinity study.
- [ ] Collect Linux hardware-counter evidence for memory behavior.
- [ ] Complete the final report and presentation.
