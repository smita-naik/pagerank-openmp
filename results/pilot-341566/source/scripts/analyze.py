#!/usr/bin/env python3
"""Summarize one homogeneous run; pair speedups with each block's serial solve."""
import argparse
import csv
import json
import math
from pathlib import Path
import random
import statistics


def summarize(records, metric="kernel_seconds"):
    if metric not in {"kernel_seconds", "total_seconds"}:
        raise ValueError("Unsupported metric")
    groups = {}
    baselines = {}
    identities = {}
    for r in records:
        graph = r["graph"]
        identity = tuple(r[k] for k in ("graph_sha256", "binary_sha256", "max_iterations", "tolerance", "damping", "profile"))
        if graph in identities and identities[graph] != identity:
            raise ValueError("Mixed graph/binary/algorithm/profile configurations; analyze runs separately")
        identities[graph] = identity
        if not r["verified"] or not math.isfinite(r[metric]) or r[metric] <= 0:
            raise ValueError("Unverified result or invalid runtime")
        if r["strategy"] == "serial":
            key = (graph, r["block"])
            if key in baselines:
                raise ValueError("Duplicate serial baseline in one block")
            baselines[key] = r
        key = (graph, r["strategy"], r["actual_threads"], r["chunk"])
        groups.setdefault(key, []).append(r)
    output = []
    for (graph, strategy, threads, chunk), group in sorted(groups.items()):
        if len({r["block"] for r in group}) != len(group):
            raise ValueError("Duplicate samples in a configuration/block")
        if {r["block"] for r in group} != {block for name, block in baselines if name == graph}:
            raise ValueError("Incomplete configuration: missing repeat blocks")
        times, speedups = [], []
        edge_imbalance, time_imbalance = [], []
        for r in group:
            baseline = baselines.get((graph, r["block"]))
            if baseline is None:
                raise ValueError("Missing paired serial baseline")
            if r["iterations"] != baseline["iterations"]:
                raise ValueError("Different iteration counts: use fixed iterations for scaling comparisons")
            times.append(r[metric])
            speedups.append(baseline[metric] / r[metric])
            stats = r["thread_stats"]
            for key, target in [("edges", edge_imbalance), ("update_seconds", time_imbalance)]:
                values = [s[key] for s in stats]
                if values and sum(values) > 0:
                    target.append(max(values) / statistics.mean(values))
        median = statistics.median(times)
        speedup = statistics.median(speedups)
        low, high = None, None
        if len(speedups) >= 3:
            rng = random.Random(548)
            boot = sorted(statistics.median(rng.choices(speedups, k=len(speedups))) for _ in range(2000))
            low, high = boot[49], boot[1949]
        output.append({
            "graph": graph, "strategy": strategy, "threads": threads, "chunk": chunk,
            "samples": len(times), "metric": metric, "median_seconds": median,
            "min_seconds": min(times), "max_seconds": max(times),
            "mad_seconds": statistics.median(abs(x - median) for x in times),
            "cv": statistics.stdev(times) / statistics.mean(times) if len(times) > 1 else 0,
            "speedup": speedup, "speedup_ci_low": low, "speedup_ci_high": high,
            "efficiency": speedup / threads,
            "iterations": group[0]["iterations"], "vertices": group[0]["vertices"], "edges": group[0]["edges"],
            "edges_per_second": group[0]["edges"] * group[0]["iterations"] / median,
            "edge_imbalance": statistics.median(edge_imbalance) if edge_imbalance else None,
            "update_time_imbalance": statistics.median(time_imbalance) if time_imbalance else None,
            "profile": group[0]["profile"],
        })
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw", type=Path)
    p.add_argument("--metric", choices=["kernel_seconds", "total_seconds"], default="kernel_seconds")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    metadata = a.raw.parent / "metadata.json"
    if metadata.exists() and "finished_utc" not in json.loads(metadata.read_text()):
        p.error("Run is incomplete; preserve the raw data and rerun into a new directory")
    rows = summarize([json.loads(line) for line in a.raw.read_text().splitlines() if line.strip()], a.metric)
    if not rows:
        p.error("No data")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} summaries to {a.output}")


if __name__ == "__main__":
    main()
