#!/bin/bash
#SBATCH --job-name=pagerank
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
#SBATCH --mem=16G
#SBATCH --output=pagerank-%j.log
# Set your account/partition and load the site's C++17/OpenMP compiler module
# before submission. Submit from the repo root: sbatch scripts/arc.slurm data/graph.mtx
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit this script from the repository root}"
graph=${1:?Usage: sbatch scripts/arc.slurm GRAPH}
export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
make CXX=g++ -j "${SLURM_CPUS_PER_TASK}"
make CXX=g++ test
# Adjust thread list to fit the allocation and physical core topology.
# The entire benchmark process needs the allocation's CPU mask (not one core).
srun --cpu-bind=cores python3 scripts/benchmark.py --graph "$graph" \
    --threads 1,2,4,8,16 --chunks 0,16,256 --repeats 7 --iterations 100 \
    --output "results/arc-${SLURM_JOB_ID}-close"
python3 scripts/analyze.py "results/arc-${SLURM_JOB_ID}-close/raw.jsonl" \
    --output "results/arc-${SLURM_JOB_ID}-close/summary.csv"
