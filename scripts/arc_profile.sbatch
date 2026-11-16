#!/bin/bash
#SBATCH --job-name=pr-profile
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
#SBATCH --output=logs/pr-profile-%j.out

set -euo pipefail
cd "$HOME/pagerank-openmp"

export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close

OUT="results/profile-${SLURM_JOB_ID}"

echo "=== ENVIRONMENT ==="
hostname
lscpu | grep -E 'Model name|CPU\(s\)|Core\(s\) per socket'
taskset -pc $$

echo "=== PROFILING ==="

python3.11 scripts/benchmark.py \
  --graph data/pr-skewed-100k-1m.mtx \
  --graph data/pr-hub-100k-1m.mtx \
  --threads 1,2,4,8,16 \
  --chunks 0,64 \
  --repeats 3 \
  --warmup 1 \
  --iterations 100 \
  --profile \
  --output "$OUT"

python3.11 scripts/analyze.py \
  "$OUT/raw.jsonl" \
  --output "$OUT/summary.csv"

echo "=== PROFILE COMPLETED ==="
wc -l "$OUT/raw.jsonl"
wc -l "$OUT/summary.csv"
