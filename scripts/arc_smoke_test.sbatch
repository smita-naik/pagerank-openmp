#!/bin/bash
#SBATCH --job-name=pagerank-test
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
#SBATCH --output=logs/pagerank-smoke-%j.out

set -euo pipefail
cd "$HOME/pagerank-openmp"

echo "========== ENVIRONMENT =========="
hostname
g++ --version | head -1
python3.11 --version
echo "Allocated CPUs: $SLURM_CPUS_PER_TASK"

echo "========== BUILD =========="
make CXX=g++ -j4
make CXX=g++ build/test_pagerank

echo "========== C++ TESTS =========="
./build/test_pagerank

echo "========== PYTHON TESTS =========="
python3.11 tests/test_cli.py --binary build/pagerank
python3.11 -m unittest discover -s tests -p 'test_scripts.py'

echo "========== GENERATE GRAPH =========="
GRAPH="data/arc-smoke-${SLURM_JOB_ID}.mtx"

python3.11 scripts/generate_graph.py \
    --kind skewed \
    --vertices 10000 \
    --edges 100000 \
    --output "$GRAPH"

export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close

echo "========== PAGERANK CORRECTNESS =========="

for strategy in serial static dynamic guided edge-balanced; do
    echo "Testing $strategy"

    if [ "$strategy" = "serial" ]; then
        ./build/pagerank \
            --graph "$GRAPH" \
            --strategy serial \
            --iterations 100 \
            --tolerance 0 \
            --verify
    else
        ./build/pagerank \
            --graph "$GRAPH" \
            --strategy "$strategy" \
            --threads 4 \
            --iterations 100 \
            --tolerance 0 \
            --verify
    fi
done

echo "========== SMALL BENCHMARK =========="
OUT="results/smoke-${SLURM_JOB_ID}"

python3.11 scripts/benchmark.py \
    --graph "$GRAPH" \
    --threads 1,2,4 \
    --chunks 0,16 \
    --repeats 3 \
    --iterations 100 \
    --output "$OUT"

python3.11 scripts/analyze.py \
    "$OUT/raw.jsonl" \
    --output "$OUT/summary.csv"

echo "========== ALL SMOKE TESTS PASSED =========="
