#!/usr/bin/env python3
"""Audit existing ARC measurements, render report figures, and validate exports.

Never invokes PageRank, a graph generator, a scheduler, or a remote service.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FULL = ['full-341571-pr-uniform-100k-1m', 'full-341570-pr-skewed-100k-1m',
        'full-341572-pr-hub-100k-1m', 'full-341573-pr-local-100k-1m',
        'full-341574-pr-local-permuted-100k-1m']
RUNS = FULL + ['profile-341576', 'locality-341577']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def original_hashes():
    return {str(path): sha(path) for folder in Path('results').iterdir() if folder.is_dir()
            for path in folder.rglob('*') if path.is_file()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hardware(meta):
    fields = {}
    for line in meta['cpu'].get('stdout', '').splitlines():
        name, sep, value = line.partition(':')
        if sep:
            fields[name.strip()] = value.strip()
    return dict(model=fields.get('Model name', 'unrecorded'),
                threads_per_core=fields.get('Thread(s) per core', 'unrecorded'),
                sockets=fields.get('Socket(s)', 'unrecorded'),
                cores_per_socket=fields.get('Core(s) per socket', 'unrecorded'))


def audit_run(name):
    from analyze import summarize
    from plot import read_summary, graph_name
    folder = Path('results') / name
    rows = read_summary(folder / 'summary.csv')
    raw = [json.loads(line) for line in (folder / 'raw.jsonl').read_text().splitlines()]
    meta = json.loads((folder / 'metadata.json').read_text())
    profile = name.startswith('profile-')
    expected = 216 if profile else 924 if name.startswith('locality-') else 462
    require(len(raw) == expected == meta['completed_solves'] and 'finished_utc' in meta, f'Incomplete run: {name}')
    require(all(r['verified'] and r['actual_threads'] == r['requested_threads'] and r['iterations'] == 100
                and r['max_iterations'] == 100 and r['tolerance'] == 0 and r['damping'] == .85
                and r['profile'] == profile and abs(r['rank_sum'] - 1) < 1e-8
                and r['verify_l1'] <= 1e-8 and r['verify_linf'] <= 1e-9 for r in raw), f'Invalid raw solve: {name}')
    for r in raw:
        require(r['total_seconds'] >= r['kernel_seconds'] > 0, f'Invalid timing: {name}')
        if profile:
            require(len(r['thread_stats']) == r['actual_threads'], 'Missing worker counters')
            require(sum(s['edges'] for s in r['thread_stats']) == r['edges'] * r['iterations'], 'Missing/duplicated profiled edges')
            require(sum(s['rows'] for s in r['thread_stats']) == r['vertices'] * r['iterations'], 'Missing/duplicated profiled rows')
        else:
            require(not r['thread_stats'], 'Instrumented data in timing run')
    recomputed = summarize(raw)
    require(len(recomputed) == len(rows), f'Summary length mismatch: {name}')
    for actual, expected_row in zip(rows, recomputed):
        for key, value in expected_row.items():
            cell = actual[key]
            if value is None:
                ok = cell == ''
            elif isinstance(value, bool):
                ok = cell == str(value)
            elif isinstance(value, (int, float)):
                ok = math.isfinite(float(cell)) and math.isclose(float(cell), value, rel_tol=1e-9, abs_tol=1e-12)
            else:
                ok = cell == str(value)
            require(ok, f'Summary/raw mismatch: {name}, {key}')
    policies = ['serial', 'static', 'dynamic', 'guided', 'edge-balanced']
    for graph in {r['graph'] for r in rows}:
        observed = {(r['strategy'], int(r['threads']), int(r['chunk'])) for r in rows if r['graph'] == graph}
        expected_grid = {('serial', 1, 0)} | {('edge-balanced', p, 0) for p in [1, 2, 4, 8, 16]}
        expected_grid |= {(s, p, c) for s in policies[1:4] for p in [1, 2, 4, 8, 16]
                          for c in ([0, 64] if profile else [0, 16, 64, 256])}
        require(observed == expected_grid, f'Incomplete configuration grid: {name}')
    return dict(name=name, rows=rows, raw=raw, meta=meta, hardware=hardware(meta),
                label=graph_name(rows[0]['graph']), count=len(raw))


def derived_csv(path, rows):
    from plot import read_summary
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    return read_summary(path)


def derive(runs, out):
    from analyze import summarize
    from plot import graph_name, FIXED_CHUNKS
    totals = {}
    for run in runs:
        totals[run['name']] = derived_csv(out / 'derived' / f"{run['name']}-total.csv", summarize(run['raw'], 'total_seconds'))
    structure = []
    for run in runs[:5]:
        first = run['raw'][0]
        keys = ['vertices', 'edges', 'max_in_degree', 'indegree_cv', 'dangling_vertices', 'isolated_vertices']
        require(all(all(r[k] == first[k] for k in keys) for r in run['raw']), 'Graph properties vary within a run')
        structure.append(dict(label=run['label'], graph=first['graph'], source=f"results/{run['name']}/raw.jsonl",
                              **{k:first[k] for k in keys}, max_edge_fraction=first['max_in_degree']/first['edges']))
    workers=[]
    for index, r in enumerate(runs[5]['raw']):
        if r['actual_threads'] != 16 or r['block'] != 0 or r['strategy'] == 'serial' or r['chunk'] != FIXED_CHUNKS[r['strategy']]:
            continue
        for s in r['thread_stats']:
            workers.append(dict(graph=r['graph'], label=graph_name(r['graph']), strategy=r['strategy'],
                                threads=16, chunk=r['chunk'], worker=s['thread'], block=0,
                                source=f"results/{runs[5]['name']}/raw.jsonl", raw_row=index,
                                rows=s['rows'], edges=s['edges'],
                                row_ratio=s['rows']/(r['vertices']*r['iterations']/16),
                                edge_ratio=s['edges']/(r['edges']*r['iterations']/16)))
    return totals, dict(structure=derived_csv(out/'derived/graph-structure.csv', structure),
                        workers=derived_csv(out/'derived/worker-work.csv', workers))


def validate_points(entries):
    cache={}; count=0
    def cell(source, row, column):
        if source not in cache:
            with open(source) as file: cache[source]=list(csv.DictReader(file))
        return float(cache[source][row][column])
    for entry in entries:
        require(entry['points'], 'Figure has no measured values')
        for p in entry['points']:
            value=cell(p['source'], p['row'], p['column'])*p['scale']
            if 'denominator_source' in p:
                value /= cell(p['denominator_source'],p['denominator_row'],p['denominator_column'])
            require(math.isfinite(value) and math.isclose(value,p['value'],rel_tol=1e-12,abs_tol=1e-12),
                    f"Untraceable plotted value: {entry['name']}")
            count+=1
    return count


def validate_files(entries, out):
    from PIL import Image
    import pymupdf
    results=[]
    for entry in entries:
        for name in entry['files']:
            path=out/name
            require(path.stat().st_size>1000, f'Empty/truncated figure: {path}')
            if path.suffix=='.png':
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    require(image.width>1000 and image.height>500, 'Low-resolution PNG')
                    require(any(lo!=hi for lo,hi in image.convert('RGB').getextrema()), 'Blank PNG')
                    require(min(image.info.get('dpi',(0,0)))>=299, 'PNG below 300 DPI')
            elif path.suffix=='.pdf':
                with pymupdf.open(path) as document:
                    require(document.page_count==1 and document.is_pdf, 'Invalid PDF export')
                    pixmap=document[0].get_pixmap(matrix=pymupdf.Matrix(.3,.3), alpha=False)
                    require(min(pixmap.samples)!=max(pixmap.samples), 'Blank PDF rendering')
            else:
                root=ET.parse(path).getroot()
                require(root.tag.endswith('svg') and bool(root.get('viewBox')), 'Invalid SVG')
                require(any(node.tag.endswith('path') for node in root.iter()), 'SVG has no drawing paths')
            results.append(dict(file=str(path),bytes=path.stat().st_size,sha256=sha(path),status='passed'))
    return results


def reports(runs, winners, out, entries, validation):
    from plot import FIXED_CHUNKS
    full=runs[:5]
    lines=['# ARC PageRank performance summary', '',
      'All values come from the committed ARC measurements. The source CSVs and raw files were left unchanged.', '',
      '## Highest reported paired speedup at 16 threads', '',
      'Selection maximizes the reported median **paired serial speedup**, using the same seven repeats for tuning and reporting. This is exploratory selection, not held-out evidence of a universally best configuration. Chunk 0 is static block scheduling or dynamic/guided default 1. Edge-balanced does not use a chunk.', '',
      '| Graph | Node | Strategy | Chunk | Median kernel ms | Paired speedup | Efficiency | Speedup interval |',
      '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for run,r in zip(full,winners):
        lines.append(f"| {run['label']} | {run['meta']['hostname']} | {r['strategy']} | {r['chunk']} | {float(r['median_seconds'])*1000:.3f} | {float(r['speedup']):.3f}× | {float(r['efficiency'])*100:.2f}% | {float(r['speedup_ci_low']):.3f}–{float(r['speedup_ci_high']):.3f} |")
    lines += ['', 'Speedup = median over repeat blocks of `T_serial(block) / T_parallel(block)`; efficiency = speedup / p. It is **not** generally serial median divided by parallel median. Intervals are the original seeded bootstrap percentile intervals from `scripts/analyze.py`.', '',
      '## Lowest median kernel runtime at 16 threads', '',
      'Runtime minimization gives different winners on skewed and hub, because ratios and medians do not commute. Both rankings are shown instead of silently changing the definition of best.', '',
      '| Graph | Strategy | Chunk | Median kernel ms | Paired speedup | Efficiency |', '| --- | --- | --- | --- | --- | --- |']
    for run in full:
        r=min((r for r in run['rows'] if r['threads']=='16'),key=lambda r:float(r['median_seconds']))
        lines.append(f"| {run['label']} | {r['strategy']} | {r['chunk']} | {float(r['median_seconds'])*1000:.3f} | {float(r['speedup']):.3f}× | {float(r['efficiency'])*100:.2f}% |")
    lines += ['', '## Hardware and evidence boundaries', '',
      '| Run | Measurements | Node | CPU model | Sockets × cores/socket | Threads/core |',
      '| --- | --- | --- | --- | --- | --- |']
    for run in runs:
        h=run['hardware']
        lines.append(f"| {run['name']} | {run['count']} | {run['meta']['hostname']} | {h['model']} | {h['sockets']} × {h['cores_per_socket']} | {h['threads_per_core']} |")
    lines += ['',
      '- All node metadata names Xeon Silver 4110, but c11 reports SMT=2 and c12–c14 SMT=1. Cross-graph timings are independent jobs with different hardware configurations; graph structure is not the only changing factor. Each speedup uses its own graph/run serial baseline.',
      '- Both locality graphs were measured in job 341577 on c11. This reduces node-type confounding. It does not measure cache misses or prove a memory-bandwidth mechanism. The original edge files are not committed, so exact graph isomorphism was not independently rechecked locally; their recorded n, m and degree statistics agree.',
      '- Only close affinity is present. No spread comparison or hardware-counter plots can be produced from the supplied evidence.',
      '- Profiling job 341576 contains only skewed and hub (3 repeats). Its instrumented runtime is kept separate from all non-profiled timing comparisons. Blank non-profiled imbalance fields remain missing.', '',
      '## Observations and limitations', '',
      '- Uniform/local scale much better than the hub in their respective jobs. Edge-balanced has the highest reported p=16 speedup on uniform and local. The hub remains near serial speed despite 16 workers.',
      '- Small dynamic chunks have substantial overhead in these measurements; inspect the chunk-sensitivity panels rather than assuming dynamic scheduling is inherently slow. Runtime dispatch, scattered ownership and memory effects are possible explanations, not directly measured causes.',
      '- Edge-balanced work metrics must be read with update-time imbalance and kernel runtime. Whole rows are indivisible, so one high-indegree hub cannot be distributed across workers by this implementation.',
      '- Local p=16 edge-balanced has high variability (CV '+f"{float(next(r for r in full[3]['rows'] if r['strategy']=='edge-balanced' and r['threads']=='16')['cv']):.3f}"+'); min–max ranges and bootstrap intervals are retained. No outliers were removed.',
      '- Fixed-configuration scaling uses static=0, dynamic=64, guided=64, edge-balanced=0 at every graph and thread count. No curve joins a different best chunk at each point. Separate winner charts are explicitly post-hoc tuning.',
      '- Kernel and total solve time are separate. Derived total summaries use existing raw `total_seconds`; they exclude graph loading and include setup. They never replace the original kernel summaries.',
      '- No confident universal winner or cache-miss explanation follows from these experiments alone.', '',
      '## Reproduce and inspect', '',
      f"See [figure guide](../plots/README.md), [validation report](../{out}/validation.json), and [figure provenance](../{out}/figures.json).",
      'Every measured plotted coordinate and band endpoint is traceable to a CSV row/column; derived totals, graph properties and worker ratios are stored separately under the plot output directory.']
    Path('results/performance_summary.md').write_text('\n'.join(lines)+'\n')
    descriptions=['# ARC performance figures', '',
      'Generated locally from the seven completed ARC result sets. No PageRank benchmark was rerun and no original measurement file was changed.', '',
      '## Reproduction', '', 'Run from the repository root on the Mac:', '', '```sh',
      'python3 -m venv .venv', '.venv/bin/python -m pip install -r requirements.txt',
      'MPLCONFIGDIR=/tmp/pagerank-mpl XDG_CACHE_HOME=/tmp/pagerank-cache .venv/bin/python scripts/build_visualizations.py --output plots/arc',
      '```', '',
      'The output directory must not exist. For a later regeneration choose a new output directory; existing artifacts are preserved. `scripts/plot.py` still accepts a single CSV with `--formats png pdf svg` and is the shared implementation for the detailed plots.', '',
      f"There are **{len(entries)} distinct figures**, each exported as 300-DPI PNG, vector PDF and SVG (**{len(validation['files'])} image files**). All passed parsing/rendering and coordinate-provenance checks. See `arc/validation.json`. Dependency versions are captured in `arc/environment.txt`.", '',
      '## Reading the figures', '',
      'Speedup is the median block-paired serial/parallel ratio, not a ratio of median runtimes. Efficiency divides that speedup by actual threads. Runtime shading is observed min–max; speedup shading is the original bootstrap interval. Locality-ratio shading is an extreme min/max ratio range, **not** a confidence interval. Missing profiling values are never zero-filled.', '',
      'Fixed-chunk comparisons use static blocks (0), dynamic 64, guided 64, and edge-balanced across all thread counts and graphs. Chunk 0 maps to default 1 for dynamic/guided. Serial has only a measured p=1 point. No different per-thread optimum is used to construct a scaling curve.', '',
      'The five independent full runs are on c11/c12/c13/c14. All report Silver 4110, but recorded SMT modes differ. Cross-graph panels show independent observations, not a controlled hardware-normalized graph comparison. Locality figures instead use only same-node job 341577. Profiling uses only job 341576; it covers two graphs.', '',
      '## Figure index', '', '| Figure | Source | Purpose |', '| --- | --- | --- |']
    for entry in entries:
        sources=sorted({p['source'].split('/')[1] if p['source'].startswith('results/') else 'derived raw-data projection' for p in entry['points']})
        descriptions.append(f"| [{entry['name']}]({out.relative_to(Path('plots'))}/{entry['name']}.png) | {', '.join(sources)} | {entry['description']} |")
    descriptions += ['', '## Recommended report figures', '',
      'Use `comparison/speedup-fixed`, `comparison/efficiency-fixed`, `comparison/chunk-sensitivity-16`, the two `comparison/profile-*imbalance` panels, `comparison/locality-runtime-ratio`, and `comparison/best-speedup-16`. The detailed per-run plots preserve every measured chunk; the comparison figures emphasize readable fixed choices.', '',
      'The exploratory highest-speedup winner and lowest-median-runtime winner differ for skewed and hub. Both are documented in [the performance summary](../results/performance_summary.md). Do not report the tuning winner as held-out validation or attribute locality timing differences directly to cache misses.']
    Path('plots/README.md').write_text('\n'.join(descriptions)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('plots/arc'))
    args=parser.parse_args()
    os.chdir(ROOT)
    # Constrain generated artifacts to the expected repository figure directory.
    out=args.output
    require(not out.is_absolute() and out.parts[:1]==('plots',) and '..' not in out.parts, 'Use a new path under plots/')
    require(not out.exists(),f'Output already exists: {out}')
    before=original_hashes()
    runs=[audit_run(name) for name in RUNS]
    require(sum(r['count'] for r in runs[:5])==2310,'Full measurement count differs')
    out.mkdir(parents=True)
    from plot import configure, FigureBook, plot_summary
    configure()
    book=FigureBook(out)
    for run in runs:
        kind='profiled' if run['name'].startswith('profile-') else 'kernel timing'
        plot_summary(run['rows'],book,run['name'],f"{kind} · {run['meta']['hostname']} · job {run['name'].split('-')[1]}")
    totals,derived=derive(runs,out)
    from arc_figures import scaling,runtime_bars,chunk_sensitivity,profiling,locality,best_configurations,additional
    full=runs[:5]; profile=runs[5]; local=runs[6]
    scaling(full,book,'speedup');scaling(full,book,'efficiency')
    runtime_bars(full,book);chunk_sensitivity(full,book);profiling(profile,book);locality(local,book)
    winners=best_configurations(full,book)
    additional(full,profile,totals,derived,book)
    book.manifest()
    points=validate_points(book.entries)
    files=validate_files(book.entries,out)
    require(before==original_hashes(),'Original result files changed during plotting')
    validation=dict(status='passed',figures=len(book.entries),image_files=len(files),traced_coordinates=points,
                    raw_measurements=sum(r['count'] for r in runs),source_hashes_unchanged=True,
                    files=files,input_sha256=before,
                    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                    python=platform.python_version(),fixed_chunks=__import__('plot').FIXED_CHUNKS)
    (out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    versions=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    (out/'environment.txt').write_text('Python '+platform.python_version()+'\n'+versions)
    reports(runs,winners,out,book.entries,validation)
    print(f"PASS: {len(book.entries)} figures, {len(files)} image files, {points} traced coordinates; original results unchanged")


if __name__=='__main__':
    main()
