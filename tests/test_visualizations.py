"""Plotting-only regression tests. Never runs PageRank or a graph generator."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plot import FIXED_CHUNKS, read_summary, point
from arc_figures import select
from build_visualizations import validate_points


class VisualizationTests(unittest.TestCase):
    def test_fixed_selection_keeps_one_chunk_at_all_threads(self):
        rows = read_summary(ROOT/'results/full-341570-pr-skewed-100k-1m/summary.csv', ROOT)
        for strategy, chunk in FIXED_CHUNKS.items():
            selected = select(rows, strategy)
            self.assertEqual({int(r['chunk']) for r in selected}, {chunk})
            self.assertEqual(len(selected), 1 if strategy=='serial' else 5)

    def test_derived_ratio_has_two_exact_source_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'summary.csv'
            path.write_text('graph,strategy,threads,chunk,median_seconds,edge_imbalance\na,static,16,0,2,\nb,static,16,0,3,\n')
            rows = read_summary(path)
            self.assertEqual(rows[0]['edge_imbalance'], '')
            ratio = point(rows[1], 'median_seconds', other=rows[0])
            self.assertEqual(ratio['value'], 1.5)
            self.assertEqual(validate_points([dict(name='ratio',points=[ratio])]),1)
            ratio['value']=9
            with self.assertRaises(ValueError):
                validate_points([dict(name='ratio',points=[ratio])])

    def test_two_winner_definitions_are_not_confused(self):
        for run in ['full-341570-pr-skewed-100k-1m','full-341572-pr-hub-100k-1m']:
            rows=read_summary(ROOT/'results'/run/'summary.csv',ROOT)
            rows=[r for r in rows if r['threads']=='16']
            speed=max(rows,key=lambda r:float(r['speedup']))
            runtime=min(rows,key=lambda r:float(r['median_seconds']))
            self.assertNotEqual((speed['strategy'],speed['chunk']),(runtime['strategy'],runtime['chunk']))


if __name__=='__main__':
    unittest.main()
