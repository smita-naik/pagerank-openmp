#!/bin/bash
#SBATCH --job-name=pr-locality
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
#SBATCH --output=logs/pr-locality-%j.out

set -euo pipefail
cd "$HOME/pagerank-openmp"

export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close

OUT="results/locality-${SLURM_JOB_ID}"

echo "=== HARDWARE ==="
hostname
lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket'
taskset -pc $$

echo "=== SAME-NODE LOCALITY BENCHMARK ==="

python3.11 scripts/benchmark.py \
  --graph data/pr-local-100k-1m.mtx \
  --graph data/pr-local-permuted-100k-1m.mtx \
  --threads 1,2,4,8,16 \
  --chunks 0,16,64,256 \
  --repeats 7 \
  --warmup 1 \
  --iterations 100 \
  --output "$OUT"

echo "=== ANALYSIS ==="

python3.11 scripts/analyze.py \
  "$OUT/raw.jsonl" \
  --output "$OUT/summary.csv"

echo "=== VALIDATION ==="
wc -l "$OUT/raw.jsonl"
wc -l "$OUT/summary.csv"

echo "=== LOCALITY BENCHMARK COMPLETED ==="
