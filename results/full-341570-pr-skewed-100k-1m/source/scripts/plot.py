#!/usr/bin/env python3
"""Publication-friendly SVG/PDF figures from measured summary CSV (matplotlib)."""
import argparse
import csv
import hashlib
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--formats", nargs="+", choices=["svg", "pdf", "png"], default=["svg", "pdf"])
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    with a.summary.open() as f:
        rows = list(csv.DictReader(f))
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    for graph in sorted({r["graph"] for r in rows}):
        data = [r for r in rows if r["graph"] == graph]
        slug = Path(graph).stem + "-" + hashlib.sha256(graph.encode()).hexdigest()[:8]
        for metric, label in [("median_seconds", "Runtime (s)"), ("speedup", "Speedup vs serial"),
                              ("efficiency", "Parallel efficiency"), ("edge_imbalance", "Max / mean edges per thread"),
                              ("update_time_imbalance", "Max / mean update time per thread")]:
            fig, ax = plt.subplots(figsize=(6.4, 4))
            plotted = False
            for strategy, chunk in sorted({(r["strategy"], r["chunk"]) for r in data}):
                series = sorted((r for r in data if r["strategy"] == strategy and r["chunk"] == chunk and r[metric]),
                                key=lambda r: int(r["threads"]))
                if not series:
                    continue
                x, y = [int(r["threads"]) for r in series], [float(r[metric]) for r in series]
                legend = strategy + (f" (chunk {chunk})" if strategy in {"static", "dynamic", "guided"} else "")
                ax.plot(x, y, marker="o", label=legend)
                if metric == "speedup" and all(r["speedup_ci_low"] for r in series):
                    ax.fill_between(x, [float(r["speedup_ci_low"]) for r in series],
                                    [float(r["speedup_ci_high"]) for r in series], alpha=0.12)
                if metric == "median_seconds":
                    ax.fill_between(x, [float(r["min_seconds"]) for r in series],
                                    [float(r["max_seconds"]) for r in series], alpha=0.12)
                plotted = True
            if not plotted:
                plt.close(fig)
                continue
            threads = sorted({int(r["threads"]) for r in data})
            if metric == "speedup":
                ax.plot(threads, threads, "k--", alpha=0.4, label="ideal")
            if metric == "efficiency":
                ax.axhline(1, color="black", linestyle="--", alpha=0.4)
            ax.set(xlabel="Threads", ylabel=label, title=f"{Path(graph).name} — {data[0]['metric']}")
            ax.set_xticks(threads)
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8)
            fig.tight_layout()
            for extension in a.formats:
                fig.savefig(a.output / f"{slug}-{metric}.{extension}")
            plt.close(fig)


if __name__ == "__main__":
    main()
