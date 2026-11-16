#!/bin/bash
#SBATCH --job-name=pr-pilot
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00
#SBATCH --output=logs/pr-pilot-%j.out

set -euo pipefail
cd "$HOME/pagerank-openmp"

export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close

echo "=== HARDWARE ==="
hostname
lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket'
taskset -pc $$

echo "=== GENERATE SKEWED GRAPH ==="
GRAPH="data/pilot-skewed-100k-1m.mtx"

if [ ! -f "$GRAPH" ]; then
    python3.11 scripts/generate_graph.py \
      --kind skewed \
      --vertices 100000 \
      --edges 1000000 \
      --seed 548 \
      --output "$GRAPH"
fi

echo "=== BENCHMARK ==="
OUT="results/pilot-${SLURM_JOB_ID}"

python3.11 scripts/benchmark.py \
  --graph "$GRAPH" \
  --threads 1,2,4 \
  --chunks 0,16,64 \
  --repeats 3 \
  --warmup 1 \
  --iterations 100 \
  --output "$OUT"

echo "=== ANALYSIS ==="
python3.11 scripts/analyze.py \
  "$OUT/raw.jsonl" \
  --output "$OUT/summary.csv"

echo "=== PILOT COMPLETED ==="
