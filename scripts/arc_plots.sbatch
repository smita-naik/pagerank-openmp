#!/bin/bash
#SBATCH --job-name=pr-plots
#SBATCH --partition=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --output=logs/pr-plots-%j.out

set -euo pipefail

cd "$HOME/pagerank-openmp"

export MPLBACKEND=Agg

echo "=== ENVIRONMENT ==="
hostname
python3.11 --version

echo "=== CHECK PLOTTING LIBRARIES ==="
python3.11 -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)"

echo "=== FULL BENCHMARK PLOTS ==="

for id in 341570 341571 341572 341573 341574; do
    for summary in results/full-${id}-*/summary.csv; do
        echo "Plotting $summary"

        python3.11 scripts/plot.py \
            "$summary" \
            --output "plots/full-${id}" \
            --formats png pdf
    done
done

echo "=== PROFILING PLOTS ==="

python3.11 scripts/plot.py \
    results/profile-341576/summary.csv \
    --output plots/profile-341576 \
    --formats png pdf

echo "=== LOCALITY PLOTS ==="

python3.11 scripts/plot.py \
    results/locality-341577/summary.csv \
    --output plots/locality-341577 \
    --formats png pdf

echo "=== GENERATED FILES ==="
find plots -type f \( -name "*.png" -o -name "*.pdf" \)

echo "=== ALL PLOTS COMPLETED ==="
