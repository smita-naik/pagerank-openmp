#!/usr/bin/env python3
"""Seeded directed multigraphs; Matrix Market preserves isolated vertices."""
import argparse
import bisect
import itertools
import json
import random
from pathlib import Path


def generate(n, m, kind, seed, permute=False):
    rng = random.Random(seed)
    permutation = list(range(n))
    if permute:
        random.Random(seed + 1).shuffle(permutation)
    cumulative = None
    if kind == "skewed":
        cumulative = list(itertools.accumulate(1.0 / (v + 1) ** 1.1 for v in range(n)))
    for _ in range(m):
        source = rng.randrange(n)
        if kind == "uniform":
            destination = rng.randrange(n)
        elif kind == "local":
            destination = (source + rng.randint(-min(n, 64), min(n, 64))) % n
        elif kind == "hub":
            destination = 0 if rng.random() < 0.9 else rng.randrange(n)
        elif kind == "skewed":
            destination = bisect.bisect_right(cumulative, rng.random() * cumulative[-1])
            destination = min(destination, n - 1)
        else:
            raise ValueError(kind)
        yield permutation[source], permutation[destination]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vertices", type=int, required=True)
    p.add_argument("--edges", type=int, required=True)
    p.add_argument("--kind", choices=["uniform", "local", "skewed", "hub"], required=True)
    p.add_argument("--seed", type=int, default=548)
    p.add_argument("--permute", action="store_true", help="Relabel the same topology with a seeded permutation")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not 0 < a.vertices <= 4294967295 or a.edges < 0:
        p.error("vertices must be in [1, UINT32_MAX]; edges must be nonnegative")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as f:
        f.write("%%MatrixMarket matrix coordinate pattern general\n")
        settings = vars(a).copy()
        settings["output"] = str(a.output)
        f.write("% generator " + json.dumps(settings, sort_keys=True) + "\n")
        f.write(f"{a.vertices} {a.vertices} {a.edges}\n")
        for source, destination in generate(a.vertices, a.edges, a.kind, a.seed, a.permute):
            f.write(f"{source + 1} {destination + 1}\n")


if __name__ == "__main__":
    main()
