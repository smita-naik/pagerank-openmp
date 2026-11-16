#!/usr/bin/env python3
"""Integration tests of real parsing, error paths, JSON output and rank files."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        graph = Path(tmp) / 'graph "quoted".txt'

        def run(text, *flags, good=True):
            nonlocal checks
            graph.write_text(text)
            process = subprocess.run([binary, "--graph", str(graph), *flags], capture_output=True, text=True)
            checks += 1
            if good:
                assert process.returncode == 0, process.stderr
                records = [json.loads(line) for line in process.stdout.splitlines()]
                assert records
                for record in records:
                    assert math.isclose(record["rank_sum"], 1, abs_tol=1e-12)
                return records
            assert process.returncode != 0, f"Should reject {text!r} {flags}"

        edges = "# directed chain\n0 1\n1 2 # comment\n"
        output = Path(tmp) / "ranks.txt"
        record = run(edges, "--vertices", "4", "--verify", "--rank-output", str(output))[0]
        assert record["vertices"] == 4 and record["edges"] == 2 and record["verified"]
        ranks = [float(x) for x in output.read_text().splitlines()]
        assert len(ranks) == 4 and abs(sum(ranks) - 1) < 1e-12
        run(edges, "--rank-output", str(output), good=False)
        assert ranks == [float(x) for x in output.read_text().splitlines()]
        for suffix, text in [("edge", "0 1\n"),
                             ("mtx", "%%MatrixMarket matrix coordinate pattern general\n2 2 1\n1 2\n")]:
            rank_path = Path(tmp) / f"orientation-{suffix}.txt"
            run(text, "--iterations", "1000", "--tolerance", "1e-14", "--rank-output", str(rank_path))
            values = [float(x) for x in rank_path.read_text().splitlines()]
            assert abs(values[0] - 1 / 2.85) < 1e-12 and abs(values[1] - 1.85 / 2.85) < 1e-12
        one_based = run("1 2\n2 3\n", "--index-base", "1", "--vertices", "4")[0]
        assert one_based["rank_sum"] == record["rank_sum"]
        matrix = "%%MatrixMarket matrix coordinate pattern general\n% chain\n4 4 2\n1 2\n2 3\n"
        mtx = run(matrix, "--format", "mtx")[0]
        assert mtx["iterations"] == record["iterations"] and mtx["residual_l1"] == record["residual_l1"]
        for field, values in [("real", "1 2 2.5\n2 3 0\n3 3 1\n"), ("integer", "1 2 2\n2 3 0\n3 3 1\n")]:
            record = run(f"%%MatrixMarket matrix coordinate {field} symmetric\n3 3 3\n{values}")[0]
            assert record["edges"] == 3  # reverse non-diagonal, skip explicit zero
        for name in ["serial", "static", "dynamic", "guided", "edge-balanced"]:
            records = run(edges, "--strategy", name, "--threads", "1" if name == "serial" else "3",
                          "--iterations", "7", "--tolerance", "0", "--repeat", "2", "--warmup", "1",
                          "--verify", "--profile")
            assert len(records) == 2 and all(r["iterations"] == 7 and not r["converged"] for r in records)
        assert run("", "--vertices", "3")[0]["edges"] == 0
        for bad in ["", "-1 2\n", "0 1 garbage\n", "0\n", "0 4294967295\n", "0 1.5\n"]:
            run(bad, good=False)
        for bad in [
            "%%MatrixMarket matrix coordinate pattern general\n2 3 1\n1 2\n",
            "%%MatrixMarket matrix coordinate pattern general\n3 3 2\n1 2\n",
            "%%MatrixMarket matrix coordinate pattern general\n3 3 1\n1 2\n2 3\n",
            "%%MatrixMarket matrix coordinate pattern general\n3 3 1\n0 2\n",
            "%%MatrixMarket matrix coordinate real general\n3 3 1\n1 2 nan\n",
            "%%MatrixMarket matrix coordinate complex general\n3 3 1\n1 2 1 0\n",
            "%%MatrixMarket matrix coordinate pattern skew-symmetric\n3 3 1\n1 2\n",
            "%%MatrixMarket matrix coordinate pattern general\n3 3 1\n4 2\n",
        ]:
            run(bad, good=False)
        for flags in [
            ["--threads", "0"], ["--iterations", "0"], ["--damping", "1"], ["--tolerance", "-1"],
            ["--chunk", "-1"], ["--tolerance", "nan"], ["--threads", "2junk"], ["--vertices", "2"],
            ["--format", "invalid"], ["--format", "mtx"], ["--index-base", "2"], ["--strategy", "other"],
            ["--damping", "0.85junk"], ["--repeat", "0"], ["--unknown", "1"],
        ]:
            run(edges, *flags, good=False)
    print(f"PASS: {checks} CLI/input cases")


if __name__ == "__main__":
    main()
