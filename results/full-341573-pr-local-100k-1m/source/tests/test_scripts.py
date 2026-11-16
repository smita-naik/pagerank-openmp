import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ExperimentTests(unittest.TestCase):
    def test_synthetic_topology_and_permutation(self):
        generator = module("generate_graph")
        for kind in ["uniform", "local", "skewed", "hub"]:
            edges = list(generator.generate(37, 200, kind, 548))
            self.assertEqual(edges, list(generator.generate(37, 200, kind, 548)))
            self.assertEqual(len(edges), 200)
            self.assertTrue(all(0 <= s < 37 and 0 <= d < 37 for s, d in edges))
            permuted = list(generator.generate(37, 200, kind, 548, True))
            mapping = {}
            for (s, d), (ps, pd) in zip(edges, permuted):
                for original, new in [(s, ps), (d, pd)]:
                    if original in mapping:
                        self.assertEqual(mapping[original], new)
                    mapping[original] = new
            self.assertEqual(len(set(mapping.values())), len(mapping))

    @staticmethod
    def record(strategy, block, seconds, threads):
        return dict(graph="g", graph_sha256="hash", binary_sha256="binary", max_iterations=10,
                    tolerance=0, damping=0.85, profile=False, verified=True, strategy=strategy,
                    block=block, actual_threads=threads, chunk=0, kernel_seconds=seconds,
                    total_seconds=seconds + 1, iterations=10, vertices=10, edges=20, thread_stats=[])

    def test_paired_baseline_speedup_and_efficiency(self):
        analyze = module("analyze")
        records = []
        for block, serial_time in enumerate([8, 10, 12]):
            records.extend([self.record("serial", block, serial_time, 1),
                            self.record("static", block, serial_time / 2, 4)])
        rows = analyze.summarize(records)
        parallel = next(r for r in rows if r["strategy"] == "static")
        self.assertEqual(parallel["speedup"], 2)
        self.assertEqual(parallel["efficiency"], 0.5)
        self.assertEqual(parallel["speedup_ci_low"], 2)
        self.assertEqual(parallel["speedup_ci_high"], 2)

    def test_reject_invalid_comparisons(self):
        analyze = module("analyze")
        baseline = self.record("serial", 0, 8, 1)
        parallel = self.record("static", 0, 4, 2)
        with self.assertRaises(ValueError):
            analyze.summarize([parallel])
        for key, value in [("iterations", 11), ("binary_sha256", "other"), ("profile", True),
                           ("verified", False), ("kernel_seconds", 0), ("kernel_seconds", float("nan"))]:
            changed = dict(parallel, **{key: value})
            with self.assertRaises(ValueError):
                analyze.summarize([baseline, changed])
        with self.assertRaises(ValueError):
            analyze.summarize([baseline, baseline, parallel])

    def test_benchmark_pipeline(self):
        # Exercise provenance, process invocation, randomized blocks and analysis
        # together, not merely the aggregation formulas.
        binary = ROOT / "build" / "pagerank"
        if not binary.exists():
            self.skipTest("Build the release binary to run experiment integration")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            graph = path / "graph.mtx"
            subprocess.run([sys.executable, str(ROOT / "scripts/generate_graph.py"), "--kind", "skewed",
                            "--vertices", "9", "--edges", "30", "--output", str(graph)], check=True, capture_output=True)
            output = path / "run"
            subprocess.run([sys.executable, str(ROOT / "scripts/benchmark.py"), "--binary", str(binary),
                            "--graph", str(graph), "--threads", "1,2", "--iterations", "3", "--repeats", "2",
                            "--output", str(output)], check=True, capture_output=True)
            records = [json.loads(line) for line in (output / "raw.jsonl").read_text().splitlines()]
            self.assertEqual(len(records), 18)
            metadata = json.loads((output / "metadata.json").read_text())
            self.assertEqual(metadata["completed_solves"], 18)
            self.assertTrue(metadata["finished_utc"])
            self.assertIn("src/pagerank.cpp", metadata["source_sha256"])
            self.assertEqual((output / "source/src/pagerank.cpp").read_bytes(), (ROOT / "src/pagerank.cpp").read_bytes())
            self.assertTrue(all(r["verified"] and r["iterations"] == 3 for r in records))
            subprocess.run([sys.executable, str(ROOT / "scripts/analyze.py"), str(output / "raw.jsonl"),
                            "--output", str(path / "summary.csv")], check=True, capture_output=True)
            self.assertEqual(len((path / "summary.csv").read_text().splitlines()), 10)


if __name__ == "__main__":
    unittest.main()
