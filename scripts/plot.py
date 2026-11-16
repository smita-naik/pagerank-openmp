#!/usr/bin/env python3
"""Measured summary plots, consistent styling, and auditable figure exports."""
import argparse
import csv
import json
from pathlib import Path

COLORS = {"serial": "#666666", "static": "#0072B2", "dynamic": "#D55E00",
          "guided": "#009E73", "edge-balanced": "#8B51A5"}
MARKERS = {"serial": "x", "static": "s", "dynamic": "^", "guided": "D", "edge-balanced": "o"}
STYLES = {0: "-", 16: ":", 64: "--", 256: "-."}
POLICIES = ["serial", "static", "dynamic", "guided", "edge-balanced"]
FIXED_CHUNKS = {"serial": 0, "static": 0, "dynamic": 64, "guided": 64, "edge-balanced": 0}


def configure():
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams.update({"font.size": 10, "axes.spines.top": False,
        "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none",
        "savefig.dpi": 300, "axes.titleweight": "bold"})


def graph_name(path):
    name = Path(path).name
    for key in ["local-permuted", "uniform", "skewed", "hub", "local"]:
        if key in name:
            return key
    return Path(path).stem


def read_summary(path, root=Path(".")):
    path = Path(path)
    with path.open() as file:
        rows = list(csv.DictReader(file))
    for index, row in enumerate(rows):
        try:
            source = path.resolve().relative_to(root.resolve())
        except ValueError:
            source = path.resolve()
        row["_source"] = str(source)
        row["_row"] = index
    return rows


def point(row, column, scale=1, other=None, other_column=None, **labels):
    """Trace each displayed value to an exact CSV cell (zero-based data row)."""
    p = dict(source=row["_source"], row=row["_row"], column=column, scale=scale,
             graph=row.get("graph"), strategy=row.get("strategy"), threads=row.get("threads"),
             chunk=row.get("chunk"), **labels)
    value = float(row[column]) * scale
    if other is not None:
        p.update(denominator_source=other["_source"], denominator_row=other["_row"],
                 denominator_column=other_column or column)
        value /= float(other[other_column or column])
    p["value"] = value
    return p


def curve(ax, rows, metric, points, label, color, scale=1, linestyle="-", marker="o", band=None):
    rows = sorted(rows, key=lambda r: int(r["threads"]))
    if not rows:
        return
    x = [int(r["threads"]) for r in rows]
    y = [point(r, metric, scale, label=label) for r in rows]
    points.extend(y)
    ax.plot(x, [p["value"] for p in y], label=label, color=color, linestyle=linestyle,
            marker=marker, markersize=4)
    if band and all(r.get(band[0]) and r.get(band[1]) for r in rows):
        low = [point(r, band[0], scale, label=label, role="band_low") for r in rows]
        high = [point(r, band[1], scale, label=label, role="band_high") for r in rows]
        points.extend(low + high)
        ax.fill_between(x, [p["value"] for p in low], [p["value"] for p in high],
                        color=color, alpha=0.12)


class FigureBook:
    def __init__(self, root, formats=("png", "pdf", "svg")):
        self.root = Path(root)
        self.formats = formats
        self.entries = []

    def save(self, fig, name, points, description):
        import matplotlib.pyplot as plt
        base = self.root / name
        base.parent.mkdir(parents=True, exist_ok=True)
        paths = []
        for extension in self.formats:
            target = base.with_suffix("." + extension)
            if target.exists():
                raise FileExistsError(target)
            fig.savefig(target, bbox_inches="tight", dpi=300)
            paths.append(str(target.relative_to(self.root)))
        self.entries.append(dict(name=name, files=paths, description=description, points=points))
        plt.close(fig)

    def manifest(self):
        with (self.root / "figures.json").open("x") as file:
            json.dump(self.entries, file, indent=2)
            file.write("\n")


def plot_summary(rows, book, prefix, title):
    import matplotlib.pyplot as plt
    time_label = "Median kernel time (s)" if rows[0]["metric"] == "kernel_seconds" else "Median total time (s)"
    metrics = [("median_seconds", time_label), ("speedup", "Speedup vs serial"),
               ("efficiency", "Parallel efficiency"), ("edge_imbalance", "Max / mean assigned edges"),
               ("update_time_imbalance", "Max / mean update time")]
    for graph in sorted({r["graph"] for r in rows}):
        data = [r for r in rows if r["graph"] == graph]
        for metric, ylabel in metrics:
            valid = [r for r in data if r.get(metric)]
            if not valid:
                continue
            fig, ax = plt.subplots(figsize=(8.8, 4.7))
            points = []
            for strategy in POLICIES:
                for chunk in sorted({int(r["chunk"]) for r in valid if r["strategy"] == strategy}):
                    series = [r for r in valid if r["strategy"] == strategy and int(r["chunk"]) == chunk]
                    label = strategy + (f" c={chunk}" if strategy in {"static", "dynamic", "guided"} else "")
                    band = ("min_seconds", "max_seconds") if metric == "median_seconds" else ("speedup_ci_low", "speedup_ci_high") if metric == "speedup" else None
                    curve(ax, series, metric, points, label, COLORS[strategy],
                          linestyle=STYLES.get(chunk, "-"), marker=MARKERS[strategy], band=band)
            threads = sorted({int(r["threads"]) for r in data})
            if metric == "speedup":
                ax.plot(threads, threads, "k--", alpha=.4, label="ideal linear")
            if metric in {"efficiency", "edge_imbalance", "update_time_imbalance"}:
                ax.axhline(1, color="black", linestyle="--", alpha=.3)
            ax.set(xlabel="OpenMP threads (serial uses 1)", ylabel=ylabel,
                   title=f"{graph_name(graph)} — {title}", xticks=threads)
            if metric == "median_seconds":
                ax.set_yscale("log")
            ax.grid(alpha=.2)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
            note = "Shading: observed min–max runtime" if metric == "median_seconds" else "Shading: original bootstrap speedup interval" if metric == "speedup" else "Instrumented runs only" if "imbalance" in metric else "Efficiency = paired speedup / threads"
            fig.text(.1, .015, note + "; c=0: static blocks, dynamic/guided default 1", fontsize=8)
            fig.subplots_adjust(right=.73, bottom=.17)
            book.save(fig, f"{prefix}/{graph_name(graph)}-{metric}", points, note)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--formats", nargs="+", choices=["svg", "pdf", "png"], default=["svg", "pdf"])
    a = p.parse_args()
    configure()
    a.output.mkdir(parents=True, exist_ok=False)
    book = FigureBook(a.output, a.formats)
    plot_summary(read_summary(a.summary), book, ".", a.summary.parent.name)
    book.manifest()


if __name__ == "__main__":
    main()
