#!/bin/bash
#SBATCH --job-name=pr-graphs
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:40:00
#SBATCH --output=logs/pr-graphs-%j.out

set -euo pipefail
cd "$HOME/pagerank-openmp"

for kind in uniform skewed hub local; do
    graph="data/pr-${kind}-100k-1m.mtx"
    if [ ! -f "$graph" ]; then
        python3.11 scripts/generate_graph.py \
            --kind "$kind" \
            --vertices 100000 \
            --edges 1000000 \
            --seed 548 \
            --output "$graph"
    fi
done

graph="data/pr-local-permuted-100k-1m.mtx"
if [ ! -f "$graph" ]; then
    python3.11 scripts/generate_graph.py \
        --kind local \
        --vertices 100000 \
        --edges 1000000 \
        --seed 548 \
        --permute \
        --output "$graph"
fi

echo "=== GENERATED GRAPHS ==="
ls -lh data/pr-*-100k-1m.mtx
echo "GRAPH GENERATION COMPLETED"
