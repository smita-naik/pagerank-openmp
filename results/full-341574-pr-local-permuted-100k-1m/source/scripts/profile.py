#!/usr/bin/env python3
"""Linux perf stat wrapper. Counters cover the whole process, including graph IO."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, default=Path("build/pagerank"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--events", default="cycles,instructions,cache-references,cache-misses,branches,branch-misses")
    p.add_argument("arguments", nargs=argparse.REMAINDER, help="After --, PageRank arguments")
    a = p.parse_args()
    if not shutil.which("perf"):
        p.error("perf is unavailable: use this script on a Linux compute node")
    if a.repeats < 1:
        p.error("repeats must be positive")
    arguments = a.arguments[1:] if a.arguments[:1] == ["--"] else a.arguments
    if "--verify" in arguments or "--repeat" in arguments or "--warmup" in arguments:
        p.error("Do not include verification, warmups or repeats in the profiled command")
    command = [str(a.binary.resolve(strict=True)), *arguments]
    # Validate independently so reference work does not contaminate perf counters.
    subprocess.run([*command, "--verify"], check=True, capture_output=True, text=True)
    a.output.mkdir(parents=True, exist_ok=False)
    perf = ["perf", "stat", "-x", ",", "-r", str(a.repeats), "-e", a.events,
            "-o", str(a.output / "perf.csv"), "--", *command]
    run = subprocess.run(perf, capture_output=True, text=True)
    (a.output / "pagerank.jsonl").write_text(run.stdout)
    (a.output / "stderr.txt").write_text(run.stderr)
    (a.output / "metadata.json").write_text(json.dumps({"command": perf, "returncode": run.returncode,
        "scope": "whole process including graph loading, allocation and initialization; not kernel-only counters",
        "interpretation": "Inspect unsupported/not-counted events and multiplex percentages before drawing conclusions."}, indent=2) + "\n")
    if run.returncode:
        raise SystemExit(f"perf failed; inspect {a.output}. Hardware events may require cluster administrator access.")


if __name__ == "__main__":
    main()
