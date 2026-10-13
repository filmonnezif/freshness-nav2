#!/usr/bin/env python3
"""Audit frozen v5 evidence, then generate all numerical manuscript assets."""
import argparse
import csv
import json
import os
import statistics
from pathlib import Path
# Fixed PDF timestamps so regenerated figures are byte-identical.
os.environ.setdefault('SOURCE_DATE_EPOCH', '0')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np
from audit import audit_campaign
from taxonomy import TAXONOMY, ABLATION_MODES, MODE_LABELS, DELTA_REVOKE

ROOT=Path(__file__).resolve().parents[2]
PAPER=ROOT/'paper'
FIGURES=PAPER/'figures'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,default=ROOT/'evidence/freshness-contracts-v5')
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--expected-repeats',type=int,default=5)
    parser.add_argument('--cases',nargs='+',choices=list(TAXONOMY),default=None,help='audit a campaign that ran only these scenarios')
    args=parser.parse_args()
    data=audit_campaign(args.evidence,args.expected_repeats,args.cases)
    ts=data['results'];n=data['repeats'];cases=list(TAXONOMY)
    print(f'Audited {len(ts)} raw trials, {len(ts)*len(ABLATION_MODES)} recomputed endpoint judgments.')
    if args.audit_only:return
    FIGURES.mkdir(exist_ok=True)
    counts=np.array([[sum(t['summary'][m]['contract_pass'] for t in ts if t['case']==case) for m in ABLATION_MODES] for case in cases])
    def entries(case,mode):return [t['summary'][mode] for t in ts if t['case']==case]
    def values(case,mode,key):return [r[key] for r in entries(case,mode) if r[key] is not None]
    def count(case,mode,key='contract_pass'):return sum(r[key] is True for r in entries(case,mode))
    plt.rcParams.update({'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})

    # Diagram designed at final column width, not shrunk from a poster layout.
    fig,ax=plt.subplots(figsize=(3.45,1.45));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    boxes=[(.77,'Synthetic clock, scan, and command'),(.54,'Input stage: direct / smoother / relay + checks'),(.31,'Native Collision Monitor'),(.08,'Held-command observer (no robot base)')]
    for y,label in boxes:
        ax.add_patch(FancyBboxPatch((.02,y),.96,.15,boxstyle='round,pad=.015',fc='#edf3f8',ec='#40617e'))
        ax.text(.5,y+.075,label,ha='center',va='center',fontsize=7.5)
    for high,low in zip(boxes,boxes[1:]):
        ax.annotate('',xy=(.5,low[0]+.17),xytext=(.5,high[0]),arrowprops={'arrowstyle':'->','color':'#40617e'})
    fig.tight_layout(pad=.3);fig.savefig(FIGURES/'freshness_architecture.pdf');plt.close(fig)

    # Column width; cells give passes out of n (stated in the caption).
    fig,ax=plt.subplots(figsize=(3.45,3.2),layout='constrained')
    cmap=ListedColormap(['#fae3e0','#fff0c9','#dcefe2'])
    ax.imshow(np.where(counts==0,0,np.where(counts==n,2,1)),cmap=cmap,vmin=0,vmax=2,aspect='auto')
    ax.set_xticks(range(8),MODE_LABELS)
    ax.set_yticks(range(len(cases)),[TAXONOMY[c].label for c in cases])
    for i in range(len(cases)):
        for j in range(8):ax.text(j,i,f'{counts[i,j]}',ha='center',va='center',fontsize=7.5)
    ax.axhline(2.5,color='#777',lw=.8,ls='--')
    ax.tick_params(labelsize=7.5);ax.xaxis.tick_top()
    ax.tick_params(length=0);fig.savefig(FIGURES/'freshness_results.pdf');plt.close(fig)

    selected=['cmd_loss','chrono_large_future_skew','chrono_duplicate_stamps','clock_backward_jump']
    fig,axes=plt.subplots(1,4,figsize=(7,1.85),layout='constrained')
    for ax,case in zip(axes.flat,selected):
        allvals=[1000*v for m in ABLATION_MODES for v in values(case,m,'revoke_latency_s')]
        top=max([220]+allvals)*1.12
        for j,m in enumerate(ABLATION_MODES):
            rs=entries(case,m)
            for i,r in enumerate(rs):
                x=j+(i-(n-1)/2)*.065
                v=r['revoke_latency_s']
                ax.scatter(x,top*.94 if v is None else v*1000,marker='x' if v is None else 'o',s=14,color='#b44832' if not r['stop_pass'] else '#246d50',zorder=3)
        ax.axhline(DELTA_REVOKE*1000,color='#555',ls='--',lw=.8)
        ax.set(xticks=range(8),xticklabels=MODE_LABELS,ylim=(-10,top))
        ax.set_title(TAXONOMY[case].label,fontsize=8);ax.tick_params(labelsize=7);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Trigger-to-zero (ms)')
    fig.savefig(FIGURES/'freshness_latency.pdf');plt.close(fig)

    healthy_failed=[t for t in ts if t['case']=='healthy' and not t['summary']['g_future']['contract_pass']]
    healthy_rep=healthy_failed[0]['repeat'] if healthy_failed else 0
    panels=[('chrono_large_future_skew',0),('clock_epoch_recovery',0),('healthy',healthy_rep)]
    fig,axes=plt.subplots(1,3,figsize=(7,2.2),layout='constrained')
    for ax,(case,rep) in zip(axes,panels):
        t=json.loads((args.evidence/f'{case}_r{rep:02d}/trace.json').read_text())
        middle=('g_future','F','#c57b22','--') if case=='healthy' else ('stock_watchdog','W','#c57b22','--')
        for mode,label,color,ls in [('native','N','#2472ae','-'),middle,('guarded','G','#24764d','-')]:
            rs=t['records'][mode];xx=[r['wall_elapsed'] for r in rs];yy=[r['vx'] for r in rs]
            if xx:xx.append(t['horizon_s']);yy.append(yy[-1])
            ax.step(xx,yy,where='post',label=label,color=color,ls=ls,lw=1.1)
        q=t['summary']['guarded']['trigger_s'];rec=t['summary']['guarded']['recovery_s']
        if q is not None:
            ax.axvline(q,color='#555',ls=':',lw=.8)
            ax.axvline(q+DELTA_REVOKE,color='#a44',ls='--',lw=.8)
        if rec is not None:ax.axvline(rec,color='#777',ls='-.',lw=.8)
        ax.set(xlabel='Observer time (s)',ylabel='Command vx (m/s)',ylim=(-.01,.255))
        title={'chrono_large_future_skew':'Future stamp (+10 s)','clock_epoch_recovery':'Clock reset + recovery','healthy':f'Healthy (repeat {rep})'}[case]
        ax.set_title(title,fontsize=8)
        ax.legend(loc='lower right',ncol=3,frameon=False);ax.grid(alpha=.2)
    fig.savefig(FIGURES/'freshness_traces.pdf');plt.close(fig)
    (PAPER/'freshness_trace_caption.tex').write_text(
        r'\caption{' + f'Fault panels show repetition 0 for N, W, and G; the healthy panel shows repetition {healthy_rep} for N, F, and G. '
        + ('The healthy repetition was selected to show the observed F failure. ' if healthy_failed else '')
        + 'Dotted lines mark triggers, dashed vertical lines mark revocation deadlines, and dash-dot marks recovery publication. Curves are held software commands, not robot velocities; coincident curves may overlap.}\n')

    # Every number in the manuscript results is generated from audited records.
    totals=counts.sum(axis=0)
    summary=(f'We obtained {len(ts)*8} paired endpoint evaluations from {len(ts)} trials. '
             f'Of the {3*n*8} availability-control evaluations, {int(counts[:3].sum())} passed. Across all scenarios, N, W, P, C, F, O, E, and G passed '
             + ', '.join(str(int(x)) for x in totals)+f' of {len(ts)} evaluations, respectively. '
             'These counts summarize the selected tests and do not estimate reliability in deployment.\n\n')
    if healthy_failed:
        bad=healthy_failed[0]
        raw=json.loads((args.evidence/f'healthy_r{bad["repeat"]:02d}/trace.json').read_text())
        zeros=[r for r in raw['records']['g_future'] if r['wall_elapsed']>.5 and abs(r['vx'])<1e-4 and abs(r['wz'])<1e-4]
        if zeros:
            summary+=(f'In healthy repetition {bad["repeat"]}, F first emitted zero after warmup at {zeros[0]["wall_elapsed"]:.3f} s, '
                      'while the published scan timestamps were still valid relative to the published clock. '
                      'We did not record the filter\'s local clock-receipt state, so the trace alone cannot explain the interruption.\n\n')
    summary+=('Under command loss, N and P passed '+f'{count("cmd_loss","native")}/{n} and {count("cmd_loss","periodic")}/{n}, '
              f'while W and C passed {count("cmd_loss","stock_watchdog")}/{n} and {count("cmd_loss","g_cmd")}/{n}. '
              f'With frozen scan timestamps, native CM passed {count("chrono_duplicate_stamps","native")}/{n} under the chronology deadline, '
              f'while O passed {count("chrono_duplicate_stamps","g_order")}/{n}. '
              'The difference is between detecting the duplicate promptly and waiting for the observation to become stale.\n\n')
    control_failures=[]
    for case in cases[:3]:
        for mode in ABLATION_MODES:
            successes=count(case,mode)
            if successes<n:
                control_failures.append(f'{TAXONOMY[case].label} / {MODE_LABELS[ABLATION_MODES.index(mode)]}: {successes}/{n}')
    if control_failures:
        summary+=('The availability controls included failures: '+ '; '.join(control_failures)+'. '
                  'These failures remain in the reported results and show why stopping performance must be considered alongside availability.\n\n')
    recovery_cases=['cmd_recovery','obs_recovery','clock_epoch_recovery']
    summary+=('Across command, scan, and epoch recovery, G passed '+', '.join(f'{count(c,"guarded")}/{n}' for c in recovery_cases)+' combined stop-and-resume tests, respectively. '
              f'In epoch recovery, O passed {count("clock_epoch_recovery","g_order","availability_pass")}/{n} availability checks, '
              f'while E passed {count("clock_epoch_recovery","g_epoch","availability_pass")}/{n}. '
              'The artifact reports the stopping and resumption judgments separately.\n')
    (PAPER/'freshness_summary.tex').write_text(summary)
    lines=['\\begin{tabular}{@{}llrr@{}}','\\toprule','Scenario & Chain & Stop passes & Latency (ms) \\\\','\\midrule']
    for case,mode,label in [('cmd_loss','stock_watchdog','Command loss'),('cmd_loss','g_cmd','Command loss'),('obs_loss','native','Scan loss'),('chrono_large_future_skew','g_future','Future +10 s'),('chrono_duplicate_stamps','g_order','Frozen stamp'),('clock_backward_jump','g_epoch','Clock reset')]:
        vs=values(case,mode,'revoke_latency_s');stat=f'{statistics.mean(vs)*1000:.1f} $\\pm$ {statistics.stdev(vs)*1000:.1f}' if len(vs)>1 else '--'
        lines.append(f'{label} & {MODE_LABELS[ABLATION_MODES.index(mode)]} & {count(case,mode,"stop_pass")}/{n} & {stat} \\\\')
    lines+=['\\bottomrule','\\end{tabular}']
    (PAPER/'freshness_latency_table.tex').write_text('\n'.join(lines)+'\n')
    md=['# V5 audited finite-trace results','',f'{len(ts)} trials, {n} repetitions per scenario, {len(ts)*8} paired endpoint evaluations. Nominal host conditions. No physical base.','', '| Scenario | '+' | '.join(MODE_LABELS)+' |','|---|'+'---:|'*8]
    for i,case in enumerate(cases):md.append('| '+TAXONOMY[case].label+' | '+' | '.join(f'{x}/{n}' for x in counts[i])+' |')
    md+=['','N=native CM; W=native smoother + CM; P=periodic relay + CM; C/F/O/E=P plus command/future/order/epoch check; G=combined checks plus clock receipt/progress check.','', 'A recovery cell passes only when both the stop and resumed-delivery obligations pass. Deadlines are derived from actual input events. Failures are retained. See `PROTOCOL.md` for exact finite-horizon semantics.']
    (ROOT/'research/freshness_contracts/RESULTS.md').write_text('\n'.join(md)+'\n')
    rows=[]
    for t in ts:
        for mode,s in t['summary'].items():rows.append({'case':t['case'],'repeat':t['repeat'],'mode':mode,**s})
    with (ROOT/'research/freshness_contracts/measurements.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    audit_report={'evidence':str(args.evidence.relative_to(ROOT)) if args.evidence.is_relative_to(ROOT) else str(args.evidence),'trials':len(ts),'evaluations':len(rows),'source_hashes':data['source_hashes'],'all_raw_summaries_recomputed':True,'counts':counts.tolist(),'cases':cases,'modes':ABLATION_MODES}
    (ROOT/'research/freshness_contracts/AUDIT.json').write_text(json.dumps(audit_report,indent=2)+'\n')
    print('Generated audited figures, LaTeX summaries, CSV measurements, and results ledger.')

if __name__=='__main__':main()
