#!/bin/bash
#SBATCH --job-name=pr-full
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
#SBATCH --output=logs/pr-full-%j.out

set -euo pipefail

cd "$HOME/pagerank-openmp"

GRAPH=${1:?ERROR: Provide a graph filename}

export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close

echo "========== ENVIRONMENT =========="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Allocated CPUs: $SLURM_CPUS_PER_TASK"

lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket'
taskset -pc $$
g++ --version | head -1
python3.11 --version

echo "========== INPUT GRAPH =========="
ls -lh "$GRAPH"

NAME=$(basename "$GRAPH" .mtx)
OUT="results/full-${SLURM_JOB_ID}-${NAME}"

echo "========== BENCHMARK =========="

python3.11 scripts/benchmark.py \
    --graph "$GRAPH" \
    --threads 1,2,4,8,16 \
    --chunks 0,16,64,256 \
    --repeats 7 \
    --warmup 1 \
    --iterations 100 \
    --output "$OUT"

echo "========== ANALYSIS =========="

python3.11 scripts/analyze.py \
    "$OUT/raw.jsonl" \
    --output "$OUT/summary.csv"

echo "========== VALIDATION =========="
wc -l "$OUT/raw.jsonl"
wc -l "$OUT/summary.csv"

echo "========== FULL BENCHMARK COMPLETED =========="
echo "Results: $OUT"
