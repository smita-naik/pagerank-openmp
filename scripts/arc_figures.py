"""Report comparisons of measured ARC data. No benchmark execution."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from plot import COLORS, MARKERS, POLICIES, FIXED_CHUNKS, curve, graph_name, point, read_summary


def select(rows, strategy, threads=None, fixed=True):
    return [r for r in rows if r["strategy"] == strategy
            and (threads is None or int(r["threads"]) == threads)
            and (not fixed or int(r["chunk"]) == FIXED_CHUNKS[strategy])]


def caption(fig, text):
    fig.text(.5, .015, text, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, .95))


def run_title(run):
    return f"{run['label']} · {run['meta']['hostname']} · SMT {run['hardware']['threads_per_core']}"


FIXED_NOTE = "Fixed chunks at every p and graph: static blocks; dynamic 64; guided 64; edge-balanced. Serial is p=1."
HOST_NOTE = "Independent jobs/nodes and SMT modes differ; cross-graph differences are not controlled hardware comparisons."


def scaling(full, book, metric):
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.4))
    points = []
    for ax, run in zip(axes.flat, full):
        for strategy in POLICIES:
            curve(ax, select(run['rows'], strategy), metric, points, strategy, COLORS[strategy],
                  marker=MARKERS[strategy], band=("speedup_ci_low", "speedup_ci_high") if metric == 'speedup' else None)
        if metric == 'speedup': ax.plot([1, 2, 4, 8, 16], [1, 2, 4, 8, 16], 'k--', alpha=.3, label='ideal linear')
        else: ax.axhline(1, color='black', linestyle='--', alpha=.3)
        ax.set(title=run_title(run), xlabel='Threads', ylabel='Speedup vs serial' if metric == 'speedup' else 'Parallel efficiency', xticks=[1, 2, 4, 8, 16])
        ax.grid(alpha=.2)
    axes.flat[-1].axis('off')
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc='center')
    fig.suptitle('ARC strong scaling — fixed scheduling configurations')
    caption(fig, FIXED_NOTE + '\n' + HOST_NOTE)
    book.save(fig, 'comparison/' + metric + '-fixed', points,
              FIXED_NOTE + ' Speedup shading preserves the original bootstrap intervals. ' + HOST_NOTE)


def runtime_bars(full, book):
    fig, ax = plt.subplots(figsize=(11, 5.3))
    points = []
    x = np.arange(len(full)); width = .15
    for j, strategy in enumerate(POLICIES):
        selected = [select(run['rows'], strategy, 1 if strategy == 'serial' else 16)[0] for run in full]
        values = [point(r, 'median_seconds', 1000) for r in selected]; points.extend(values)
        low = [point(r, 'min_seconds', 1000, role='range_low') for r in selected]
        high = [point(r, 'max_seconds', 1000, role='range_high') for r in selected]; points.extend(low + high)
        y = [p['value'] for p in values]
        ax.bar(x+(j-2)*width, y, width, label=strategy, color=COLORS[strategy],
               yerr=[[p['value']-q['value'] for p,q in zip(values,low)],
                     [q['value']-p['value'] for p,q in zip(values,high)]], capsize=2,
               error_kw={'linewidth': .7})
    ax.set(yscale='log', ylabel='Median kernel time (ms, log scale)', xticks=x,
           xticklabels=[run_title(r).replace(' · ', '\n') for r in full], title='Kernel runtime by scheduling strategy — parallel p=16, serial p=1')
    ax.legend(ncol=5); ax.grid(axis='y', alpha=.2)
    caption(fig, FIXED_NOTE + '\nWhiskers: observed min–max; ' + HOST_NOTE)
    book.save(fig, 'comparison/runtime-strategies-16', points, FIXED_NOTE + ' Observed min–max ranges. ' + HOST_NOTE)


def chunk_sensitivity(full, book):
    fig, axes = plt.subplots(5, 3, figsize=(12, 15))
    points = []
    for i, run in enumerate(full):
        for j, strategy in enumerate(['static', 'dynamic', 'guided']):
            ax = axes[i,j]
            rows = sorted(select(run['rows'], strategy, 16, fixed=False), key=lambda r: int(r['chunk']))
            values = [point(r, 'median_seconds', 1000) for r in rows]; points.extend(values)
            lows = [point(r, 'min_seconds', 1000, role='range_low') for r in rows]
            highs = [point(r, 'max_seconds', 1000, role='range_high') for r in rows]; points.extend(lows+highs)
            x = list(range(len(rows)))
            ax.plot(x, [p['value'] for p in values], color=COLORS[strategy], marker=MARKERS[strategy])
            ax.fill_between(x, [p['value'] for p in lows], [p['value'] for p in highs], color=COLORS[strategy], alpha=.15)
            ax.set(yscale='log', xticks=x, xticklabels=[r['chunk'] for r in rows], xlabel='Chunk parameter',
                   ylabel='Kernel time (ms)', title=f"{run_title(run)} / {strategy}")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, position: f'{value:g}'))
            ax.yaxis.set_minor_formatter(FuncFormatter(lambda value, position: f'{value:g}'))
            ax.grid(alpha=.2)
    fig.suptitle('Chunk sensitivity at 16 threads — all measured chunks')
    caption(fig, 'Chunk 0 means static blocks or dynamic/guided default 1. Shading: observed min–max.\n' + HOST_NOTE)
    book.save(fig, 'comparison/chunk-sensitivity-16', points, 'All chunks 0/16/64/256 at p=16; categorical x positions. No per-point tuning.')


def profiling(profile, book):
    for metric, ylabel in [('edge_imbalance', 'Max / mean assigned edges'), ('update_time_imbalance', 'Max / mean update time')]:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6)); points = []
        for ax, graph in zip(axes, sorted({r['graph'] for r in profile['rows']})):
            rows = [r for r in profile['rows'] if r['graph'] == graph]
            for strategy in POLICIES:
                curve(ax, select(rows, strategy), metric, points, strategy, COLORS[strategy], marker=MARKERS[strategy])
            ax.axhline(1, color='black', alpha=.3, linestyle='--')
            ax.set(title=f"{graph_name(graph)} · profiling job 341576 · c11", xlabel='Threads', ylabel=ylabel, xticks=[1,2,4,8,16])
            ax.grid(alpha=.2)
        axes[0].legend(fontsize=8)
        caption(fig, 'Instrumented data only (3 repeats); ratios are medians of cumulative per-thread max/mean.\n' + FIXED_NOTE)
        book.save(fig, 'comparison/profile-' + metric, points, 'Only skewed/hub were profiled. Instrumented times are not mixed with primary timing runs. ' + FIXED_NOTE)


def locality(local, book):
    graphs = sorted({r['graph'] for r in local['rows']}, key=lambda g: graph_name(g))
    assert [graph_name(g) for g in graphs] == ['local', 'local-permuted']
    fig, axes = plt.subplots(2,3,figsize=(12,7.3)); points=[]
    for ax, strategy in zip(axes.flat, POLICIES):
        for graph, color, label in zip(graphs, ['#0072B2','#D55E00'], ['local','local-permuted']):
            curve(ax, select([r for r in local['rows'] if r['graph']==graph], strategy), 'median_seconds', points,
                  label, color, scale=1000, band=('min_seconds','max_seconds'))
        ax.set(yscale='log', title=strategy, xlabel='Threads', ylabel='Median kernel time (ms)', xticks=[1,2,4,8,16])
        ax.grid(alpha=.2)
    axes.flat[-1].axis('off'); axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(),loc='center')
    fig.suptitle('Controlled locality comparison — job 341577, both graphs on c11')
    caption(fig, FIXED_NOTE + '\nShading: observed min–max. Same-node timing does not measure cache misses.')
    book.save(fig,'comparison/locality-runtime',points,'Both graphs use the same node/job, executable and parameters. No cache counters were collected.')
    fig,ax=plt.subplots(figsize=(8.5,4.7));points=[]
    for strategy in POLICIES:
        left=select([r for r in local['rows'] if r['graph']==graphs[0]],strategy)
        right=select([r for r in local['rows'] if r['graph']==graphs[1]],strategy)
        values=[];lower=[];upper=[]
        for a,b in zip(left,right):
            assert a['threads']==b['threads']
            values.append(point(b,'median_seconds',other=a,label=strategy))
            lower.append(point(b,'min_seconds',other=a,other_column='max_seconds',role='range_low'))
            upper.append(point(b,'max_seconds',other=a,other_column='min_seconds',role='range_high'))
        points.extend(values+lower+upper)
        x=[int(r['threads']) for r in left]
        ax.plot(x,[p['value'] for p in values],label=strategy,color=COLORS[strategy],marker=MARKERS[strategy])
        ax.fill_between(x,[p['value'] for p in lower],[p['value'] for p in upper],color=COLORS[strategy],alpha=.1)
    ax.axhline(1,color='black',linestyle='--',alpha=.4)
    ax.set(xlabel='Threads',ylabel='Permuted / local median kernel time',xticks=[1,2,4,8,16],title='Relabeling runtime ratio — same-node job 341577')
    ax.legend(ncol=3,fontsize=8);ax.grid(alpha=.2)
    caption(fig,'Ratio of measured medians; shading is the extreme min/max ratio range, not a confidence interval.\nValues above 1 mean permuted is slower. ' + FIXED_NOTE)
    book.save(fig,'comparison/locality-runtime-ratio',points,'Ratio = permuted median / local median; min/max bounds are not confidence intervals. No claim of cache-miss causality.')


def best_configurations(full, book):
    winners=[max([r for r in run['rows'] if r['threads']=='16'],key=lambda r:float(r['speedup'])) for run in full]
    for metric,ylabel in [('speedup','Highest measured paired speedup at p=16'),('efficiency','Parallel efficiency of speedup winner')]:
        fig,ax=plt.subplots(figsize=(10,5));points=[]
        values=[point(r,metric) for r in winners];points.extend(values)
        y=[p['value'] for p in values];x=np.arange(5)
        ax.bar(x,y,color=[COLORS[r['strategy']] for r in winners])
        if metric=='speedup':
            lo=[point(r,'speedup_ci_low',role='CI_low') for r in winners]
            hi=[point(r,'speedup_ci_high',role='CI_high') for r in winners];points.extend(lo+hi)
            ax.errorbar(x,y,yerr=[[p['value']-q['value'] for p,q in zip(values,lo)],[q['value']-p['value'] for p,q in zip(values,hi)]],fmt='none',color='black',capsize=3)
        for i,r in enumerate(winners):
            top=float(r['speedup_ci_high']) if metric=='speedup' else y[i]
            config='no chunk' if r['strategy']=='edge-balanced' else 'blocks' if r['strategy']=='static' and r['chunk']=='0' else f"c={r['chunk']}"
            ax.annotate(f"{r['strategy']}\n{config}",(i,top),xytext=(0,10),textcoords='offset points',ha='center',fontsize=8)
        ax.set(xticks=x,xticklabels=[run_title(r).replace(' · ','\n') for r in full],ylabel=ylabel,title='Exploratory 16-thread tuning summary')
        ax.set_ylim(0,max(y)*1.35);ax.grid(axis='y',alpha=.2)
        caption(fig,'Selected by highest reported paired speedup using the same samples; optimistic tuning, not held-out validation.\n' + HOST_NOTE)
        book.save(fig,'comparison/best-'+metric+'-16',points,'Post-hoc maximum paired speedup at p=16; runtime ranking may differ because paired speedup is not a ratio of medians.')
    return winners


def additional(full, profile, totals, derived, book):
    # Raw graph properties projected once per graph to an auditable derived CSV.
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.5));points=[]
    for ax,metric,label in zip(axes,['max_edge_fraction','indegree_cv'],['Maximum indegree / edges','Indegree coefficient of variation']):
        vals=[point(r,metric) for r in derived['structure']];points.extend(vals)
        ax.bar(range(5),[p['value'] for p in vals],color='#0072B2')
        ax.set(xticks=range(5),xticklabels=[r['label'] for r in derived['structure']],ylabel=label)
        ax.tick_params(axis='x',rotation=20);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Graph structure — all graphs have 100,000 vertices and 1,000,000 edges')
    caption(fig,'Structural properties from raw records; these bars contain no runtime comparisons.')
    book.save(fig,'comparison/graph-structure',points,'Raw structural statistics; no unmeasured degree distribution is inferred.')
    fig,axes=plt.subplots(2,3,figsize=(12,7.3));points=[]
    for ax,run in zip(axes.flat,full):
        for offset,source,label in [(-.18,run['rows'],'kernel'),(.18,totals[run['name']],'total solve')]:
            chosen=[select(source,s,1 if s=='serial' else 16)[0] for s in POLICIES]
            vals=[point(r,'median_seconds',1000,label=label) for r in chosen];points.extend(vals)
            ax.bar(np.arange(5)+offset,[p['value'] for p in vals],.35,label=label)
        ax.set(yscale='log',title=run_title(run),ylabel='Median time (ms)',xticks=range(5),xticklabels=POLICIES)
        ax.tick_params(axis='x',rotation=25);ax.grid(axis='y',alpha=.2)
    axes.flat[-1].axis('off');axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(),loc='center')
    fig.suptitle('Kernel vs total solve time — setup included only in total; graph IO excluded')
    caption(fig,FIXED_NOTE + '\nTotal-time summaries are derived from existing raw measurements; no benchmarks were rerun.')
    book.save(fig,'comparison/kernel-vs-total-16',points,'Independent medians of kernel and total solve time; total includes setup, but excludes graph IO.')
    fig,ax=plt.subplots(figsize=(12,4.6));points=[]
    configs=[(s,c) for s in ['static','dynamic','guided'] for c in [0,16,64,256]]+[('edge-balanced',0)]
    matrix=[]
    for run in full:
        vals=[]
        for s,c in configs:
            r=next(r for r in run['rows'] if r['strategy']==s and int(r['chunk'])==c and r['threads']=='16')
            p=point(r,'cv');points.append(p);vals.append(p['value'])
        matrix.append(vals)
    image=ax.imshow(matrix,aspect='auto',cmap='magma',vmin=0)
    ax.set(xticks=range(13),xticklabels=[f'{s}\nc={c}' for s,c in configs],yticks=range(5),yticklabels=[r['label'] for r in full],title='Runtime variability at p=16 — all measured configurations')
    ax.tick_params(axis='x',labelsize=8)
    fig.colorbar(image,ax=ax,label='Coefficient of variation (sample SD / mean)')
    caption(fig,'CV is calculated from the seven raw runtimes; no outliers were removed. ' + HOST_NOTE)
    book.save(fig,'comparison/runtime-variability-16',points,'Variability of every p=16 parallel configuration, without filtering high-variance samples.')
    fig,axes=plt.subplots(2,4,figsize=(14,7));points=[]
    for i,label in enumerate(['hub','skewed']):
        for j,strategy in enumerate(POLICIES[1:]):
            ax=axes[i,j]
            rows=[r for r in derived['workers'] if r['label']==label and r['strategy']==strategy]
            for offset,metric,name,color in [(-.2,'row_ratio','rows','#AAAAAA'),(.2,'edge_ratio','edges',COLORS[strategy])]:
                vals=[point(r,metric,label=name) for r in rows];points.extend(vals)
                ax.bar(np.array([int(r['worker']) for r in rows])+offset,[p['value'] for p in vals],.4,label=name,color=color)
            ax.axhline(1,color='black',alpha=.3,linestyle='--')
            ax.set(title=f'{label} / {strategy}',xlabel='Worker index',ylabel='Work / team mean',xticks=[0,4,8,12,15])
            ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Per-worker assignment at p=16 — profiling job 341576, first repeat block (0)')
    caption(fig,'Raw worker counters, fixed chunks; worker indices are not physical CPU IDs.\nA prespecified block illustrates assignment; aggregated imbalance plots use all repeats.')
    book.save(fig,'comparison/profile-worker-work-16',points,'Block 0, p=16, fixed chunks. Ratios normalize raw counters by the team mean; no representative run was cherry-picked.')
