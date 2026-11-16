# ARC performance figures

Generated locally from the seven completed ARC result sets. No PageRank benchmark was rerun and no original measurement file was changed.

## Reproduction

Run from the repository root on the Mac:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
MPLCONFIGDIR=/tmp/pagerank-mpl XDG_CACHE_HOME=/tmp/pagerank-cache .venv/bin/python scripts/build_visualizations.py --output plots/arc
```

The output directory must not exist. For a later regeneration choose a new output directory; existing artifacts are preserved. `scripts/plot.py` still accepts a single CSV with `--formats png pdf svg` and is the shared implementation for the detailed plots.

There are **45 distinct figures**, each exported as 300-DPI PNG, vector PDF and SVG (**135 image files**). All passed parsing/rendering and coordinate-provenance checks. See `arc/validation.json`. Dependency versions are captured in `arc/environment.txt`.

## Reading the figures

Speedup is the median block-paired serial/parallel ratio, not a ratio of median runtimes. Efficiency divides that speedup by actual threads. Runtime shading is observed min–max; speedup shading is the original bootstrap interval. Locality-ratio shading is an extreme min/max ratio range, **not** a confidence interval. Missing profiling values are never zero-filled.

Fixed-chunk comparisons use static blocks (0), dynamic 64, guided 64, and edge-balanced across all thread counts and graphs. Chunk 0 maps to default 1 for dynamic/guided. Serial has only a measured p=1 point. No different per-thread optimum is used to construct a scaling curve.

The five independent full runs are on c11/c12/c13/c14. All report Silver 4110, but recorded SMT modes differ. Cross-graph panels show independent observations, not a controlled hardware-normalized graph comparison. Locality figures instead use only same-node job 341577. Profiling uses only job 341576; it covers two graphs.

## Figure index

| Figure | Source | Purpose |
| --- | --- | --- |
| [full-341571-pr-uniform-100k-1m/uniform-median_seconds](arc/full-341571-pr-uniform-100k-1m/uniform-median_seconds.png) | full-341571-pr-uniform-100k-1m | Shading: observed min–max runtime |
| [full-341571-pr-uniform-100k-1m/uniform-speedup](arc/full-341571-pr-uniform-100k-1m/uniform-speedup.png) | full-341571-pr-uniform-100k-1m | Shading: original bootstrap speedup interval |
| [full-341571-pr-uniform-100k-1m/uniform-efficiency](arc/full-341571-pr-uniform-100k-1m/uniform-efficiency.png) | full-341571-pr-uniform-100k-1m | Efficiency = paired speedup / threads |
| [full-341570-pr-skewed-100k-1m/skewed-median_seconds](arc/full-341570-pr-skewed-100k-1m/skewed-median_seconds.png) | full-341570-pr-skewed-100k-1m | Shading: observed min–max runtime |
| [full-341570-pr-skewed-100k-1m/skewed-speedup](arc/full-341570-pr-skewed-100k-1m/skewed-speedup.png) | full-341570-pr-skewed-100k-1m | Shading: original bootstrap speedup interval |
| [full-341570-pr-skewed-100k-1m/skewed-efficiency](arc/full-341570-pr-skewed-100k-1m/skewed-efficiency.png) | full-341570-pr-skewed-100k-1m | Efficiency = paired speedup / threads |
| [full-341572-pr-hub-100k-1m/hub-median_seconds](arc/full-341572-pr-hub-100k-1m/hub-median_seconds.png) | full-341572-pr-hub-100k-1m | Shading: observed min–max runtime |
| [full-341572-pr-hub-100k-1m/hub-speedup](arc/full-341572-pr-hub-100k-1m/hub-speedup.png) | full-341572-pr-hub-100k-1m | Shading: original bootstrap speedup interval |
| [full-341572-pr-hub-100k-1m/hub-efficiency](arc/full-341572-pr-hub-100k-1m/hub-efficiency.png) | full-341572-pr-hub-100k-1m | Efficiency = paired speedup / threads |
| [full-341573-pr-local-100k-1m/local-median_seconds](arc/full-341573-pr-local-100k-1m/local-median_seconds.png) | full-341573-pr-local-100k-1m | Shading: observed min–max runtime |
| [full-341573-pr-local-100k-1m/local-speedup](arc/full-341573-pr-local-100k-1m/local-speedup.png) | full-341573-pr-local-100k-1m | Shading: original bootstrap speedup interval |
| [full-341573-pr-local-100k-1m/local-efficiency](arc/full-341573-pr-local-100k-1m/local-efficiency.png) | full-341573-pr-local-100k-1m | Efficiency = paired speedup / threads |
| [full-341574-pr-local-permuted-100k-1m/local-permuted-median_seconds](arc/full-341574-pr-local-permuted-100k-1m/local-permuted-median_seconds.png) | full-341574-pr-local-permuted-100k-1m | Shading: observed min–max runtime |
| [full-341574-pr-local-permuted-100k-1m/local-permuted-speedup](arc/full-341574-pr-local-permuted-100k-1m/local-permuted-speedup.png) | full-341574-pr-local-permuted-100k-1m | Shading: original bootstrap speedup interval |
| [full-341574-pr-local-permuted-100k-1m/local-permuted-efficiency](arc/full-341574-pr-local-permuted-100k-1m/local-permuted-efficiency.png) | full-341574-pr-local-permuted-100k-1m | Efficiency = paired speedup / threads |
| [profile-341576/hub-median_seconds](arc/profile-341576/hub-median_seconds.png) | profile-341576 | Shading: observed min–max runtime |
| [profile-341576/hub-speedup](arc/profile-341576/hub-speedup.png) | profile-341576 | Shading: original bootstrap speedup interval |
| [profile-341576/hub-efficiency](arc/profile-341576/hub-efficiency.png) | profile-341576 | Efficiency = paired speedup / threads |
| [profile-341576/hub-edge_imbalance](arc/profile-341576/hub-edge_imbalance.png) | profile-341576 | Instrumented runs only |
| [profile-341576/hub-update_time_imbalance](arc/profile-341576/hub-update_time_imbalance.png) | profile-341576 | Instrumented runs only |
| [profile-341576/skewed-median_seconds](arc/profile-341576/skewed-median_seconds.png) | profile-341576 | Shading: observed min–max runtime |
| [profile-341576/skewed-speedup](arc/profile-341576/skewed-speedup.png) | profile-341576 | Shading: original bootstrap speedup interval |
| [profile-341576/skewed-efficiency](arc/profile-341576/skewed-efficiency.png) | profile-341576 | Efficiency = paired speedup / threads |
| [profile-341576/skewed-edge_imbalance](arc/profile-341576/skewed-edge_imbalance.png) | profile-341576 | Instrumented runs only |
| [profile-341576/skewed-update_time_imbalance](arc/profile-341576/skewed-update_time_imbalance.png) | profile-341576 | Instrumented runs only |
| [locality-341577/local-median_seconds](arc/locality-341577/local-median_seconds.png) | locality-341577 | Shading: observed min–max runtime |
| [locality-341577/local-speedup](arc/locality-341577/local-speedup.png) | locality-341577 | Shading: original bootstrap speedup interval |
| [locality-341577/local-efficiency](arc/locality-341577/local-efficiency.png) | locality-341577 | Efficiency = paired speedup / threads |
| [locality-341577/local-permuted-median_seconds](arc/locality-341577/local-permuted-median_seconds.png) | locality-341577 | Shading: observed min–max runtime |
| [locality-341577/local-permuted-speedup](arc/locality-341577/local-permuted-speedup.png) | locality-341577 | Shading: original bootstrap speedup interval |
| [locality-341577/local-permuted-efficiency](arc/locality-341577/local-permuted-efficiency.png) | locality-341577 | Efficiency = paired speedup / threads |
| [comparison/speedup-fixed](arc/comparison/speedup-fixed.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1. Speedup shading preserves the original bootstrap intervals. Independent jobs/nodes and SMT modes differ; cross-graph differences are not controlled hardware comparisons. |
| [comparison/efficiency-fixed](arc/comparison/efficiency-fixed.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1. Speedup shading preserves the original bootstrap intervals. Independent jobs/nodes and SMT modes differ; cross-graph differences are not controlled hardware comparisons. |
| [comparison/runtime-strategies-16](arc/comparison/runtime-strategies-16.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1. Observed min–max ranges. Independent jobs/nodes and SMT modes differ; cross-graph differences are not controlled hardware comparisons. |
| [comparison/chunk-sensitivity-16](arc/comparison/chunk-sensitivity-16.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | All chunks 0/16/64/256 at p=16; categorical x positions. No per-point tuning. |
| [comparison/profile-edge_imbalance](arc/comparison/profile-edge_imbalance.png) | profile-341576 | Only skewed/hub were profiled. Instrumented times are not mixed with primary timing runs. Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1. |
| [comparison/profile-update_time_imbalance](arc/comparison/profile-update_time_imbalance.png) | profile-341576 | Only skewed/hub were profiled. Instrumented times are not mixed with primary timing runs. Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1. |
| [comparison/locality-runtime](arc/comparison/locality-runtime.png) | locality-341577 | Both graphs use the same node/job, executable and parameters. No cache counters were collected. |
| [comparison/locality-runtime-ratio](arc/comparison/locality-runtime-ratio.png) | locality-341577 | Ratio = permuted median / local median; min/max bounds are not confidence intervals. No claim of cache-miss causality. |
| [comparison/best-speedup-16](arc/comparison/best-speedup-16.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Post-hoc maximum paired speedup at p=16; runtime ranking may differ because paired speedup is not a ratio of medians. |
| [comparison/best-efficiency-16](arc/comparison/best-efficiency-16.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Post-hoc maximum paired speedup at p=16; runtime ranking may differ because paired speedup is not a ratio of medians. |
| [comparison/graph-structure](arc/comparison/graph-structure.png) | derived raw-data projection | Raw structural statistics; no unmeasured degree distribution is inferred. |
| [comparison/kernel-vs-total-16](arc/comparison/kernel-vs-total-16.png) | derived raw-data projection, full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Independent medians of kernel and total solve time; total includes setup, but excludes graph IO. |
| [comparison/runtime-variability-16](arc/comparison/runtime-variability-16.png) | full-341570-pr-skewed-100k-1m, full-341571-pr-uniform-100k-1m, full-341572-pr-hub-100k-1m, full-341573-pr-local-100k-1m, full-341574-pr-local-permuted-100k-1m | Variability of every p=16 parallel configuration, without filtering high-variance samples. |
| [comparison/profile-worker-work-16](arc/comparison/profile-worker-work-16.png) | derived raw-data projection | Block 0, p=16, fixed chunks. Ratios normalize raw counters by the team mean; no representative run was cherry-picked. |

## Recommended report figures

Use `comparison/speedup-fixed`, `comparison/efficiency-fixed`, `comparison/chunk-sensitivity-16`, the two `comparison/profile-*imbalance` panels, `comparison/locality-runtime-ratio`, and `comparison/best-speedup-16`. The detailed per-run plots preserve every measured chunk; the comparison figures emphasize readable fixed choices.

The exploratory highest-speedup winner and lowest-median-runtime winner differ for skewed and hub. Both are documented in [the performance summary](../results/performance_summary.md). Do not report the tuning winner as held-out validation or attribute locality timing differences directly to cache misses.
