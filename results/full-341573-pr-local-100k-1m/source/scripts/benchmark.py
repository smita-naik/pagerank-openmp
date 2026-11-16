#!/usr/bin/env python3
"""Randomized blocked strong-scaling runs with serial verification and provenance."""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import shlex
import shutil
import subprocess
import sys


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}


def int_list(value):
    try:
        result = sorted(set(int(x) for x in value.split(",")))
    except ValueError as e:
        raise argparse.ArgumentTypeError("Use comma-separated integers") from e
    if not result or min(result) < 0:
        raise argparse.ArgumentTypeError("Values must be nonnegative")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, default=Path("build/pagerank"))
    p.add_argument("--graph", type=Path, action="append", required=True)
    p.add_argument("--threads", type=int_list, default=[1, 2, 4, 8])
    p.add_argument("--chunks", type=int_list, default=[0])
    p.add_argument("--strategies", default="serial,static,dynamic,guided,edge-balanced")
    p.add_argument("--iterations", type=int, default=100)
    p.add_argument("--tolerance", type=float, default=0.0)
    p.add_argument("--damping", type=float, default=0.85)
    p.add_argument("--vertices", type=int)
    p.add_argument("--index-base", type=int, choices=[0, 1], default=0)
    p.add_argument("--format", choices=["auto", "mtx", "edgelist"], default="auto")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--seed", type=int, default=548)
    p.add_argument("--profile", action="store_true", help="Separate diagnostic experiment, not final timing")
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--output", type=Path, required=True, help="New run directory; existing paths refused")
    a = p.parse_args()
    if a.repeats < 1 or a.warmup < 0 or min(a.threads) < 1:
        p.error("repeats and threads must be positive; warmup nonnegative")
    strategies = list(dict.fromkeys(a.strategies.split(",")))
    if "serial" not in strategies or any(s not in {"serial", "static", "dynamic", "guided", "edge-balanced"} for s in strategies):
        p.error("Include serial and valid strategy names")
    binary = a.binary.resolve(strict=True)
    graphs = list(dict.fromkeys(g.resolve(strict=True) for g in a.graph))
    graph_hashes = {str(g): sha256(g) for g in graphs}
    binary_hash = sha256(binary)
    a.output.mkdir(parents=True, exist_ok=False)
    # Preserve exact working-tree source, including untracked implementation files.
    # This complements git metadata when exploratory runs precede a commit.
    root = Path(__file__).resolve().parents[1]
    source_paths = [root / name for name in ["Makefile", "README.md", "requirements.txt"]]
    for directory in ["src", "include", "scripts", "tests"]:
        source_paths.extend(path for path in (root / directory).rglob("*")
                            if path.is_file() and path.suffix in {".cpp", ".hpp", ".py", ".slurm", ".lsf"})
    source_hashes = {}
    for source in source_paths:
        relative = source.relative_to(root)
        destination = a.output / "source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        source_hashes[str(relative)] = sha256(destination)
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv, "platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version, "hostname": platform.node(),
        "binary": str(binary), "binary_sha256": binary_hash,
        "graphs_sha256": graph_hashes,
        "source_sha256": source_hashes,
        "environment": {k: v for k, v in os.environ.items() if k.startswith(("OMP_", "SLURM_", "LSB_", "KMP_", "GOMP_"))},
        "git_head": capture(["git", "rev-parse", "HEAD"]),
        "git_status": capture(["git", "status", "--short"]),
        "git_diff": capture(["git", "diff", "HEAD", "--", "src", "include", "scripts", "Makefile"]),
        "cpu": capture(["sysctl", "-a"]) if platform.system() == "Darwin" else capture(["lscpu"]),
        "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "note": "Fixed iterations by default. Each solve follows a serial verification and warmups. IO excluded.",
    }
    # Limit macOS metadata to hardware/kernel identity rather than unrelated system settings.
    if platform.system() == "Darwin" and "stdout" in metadata["cpu"]:
        metadata["cpu"]["stdout"] = "\n".join(line for line in metadata["cpu"]["stdout"].splitlines() if line.startswith(("hw.", "machdep.cpu.", "kern.osrelease", "kern.version")))
    (a.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    configurations = []
    for graph, strategy in itertools.product(graphs, strategies):
        threads = [1] if strategy == "serial" else a.threads
        chunks = [0] if strategy in {"serial", "edge-balanced"} else a.chunks
        configurations.extend((graph, strategy, t, c) for t, c in itertools.product(threads, chunks))
    rng = random.Random(a.seed)
    completed = 0
    with (a.output / "raw.jsonl").open("x") as raw, (a.output / "commands.jsonl").open("x") as log:
        for block in range(a.repeats):
            rng.shuffle(configurations)
            for graph, strategy, threads, chunk in configurations:
                command = [str(binary), "--graph", str(graph), "--strategy", strategy, "--threads", str(threads),
                           "--chunk", str(chunk), "--iterations", str(a.iterations), "--tolerance", str(a.tolerance),
                           "--damping", str(a.damping), "--warmup", str(a.warmup), "--verify",
                           "--index-base", str(a.index_base), "--format", a.format]
                if a.vertices is not None:
                    command.extend(["--vertices", str(a.vertices)])
                if a.profile:
                    command.append("--profile")
                print(f"block {block + 1}/{a.repeats}: {graph.name} {strategy} p={threads} chunk={chunk}", flush=True)
                run = subprocess.run(command, capture_output=True, text=True, timeout=a.timeout)
                log.write(json.dumps({"block": block, "command": command, "shell_display": shlex.join(command),
                                      "returncode": run.returncode, "stderr": run.stderr}) + "\n")
                log.flush()
                if run.returncode:
                    raise RuntimeError(f"Benchmark failed: {run.stderr}")
                records = [json.loads(line) for line in run.stdout.splitlines()]
                if len(records) != 1:
                    raise RuntimeError("Expected one measured solve per invocation")
                record = records[0]
                if record["actual_threads"] != threads:
                    raise RuntimeError(f"Requested {threads} threads but runtime provided {record['actual_threads']}")
                record.update({"block": block, "graph_sha256": graph_hashes[str(graph)],
                               "binary_sha256": binary_hash, "recorded_utc": datetime.now(timezone.utc).isoformat()})
                raw.write(json.dumps(record) + "\n")
                raw.flush()
                completed += 1
    metadata.update({"finished_utc": datetime.now(timezone.utc).isoformat(), "completed_solves": completed})
    (a.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved {completed} validated measurements to {a.output}")


if __name__ == "__main__":
    main()
