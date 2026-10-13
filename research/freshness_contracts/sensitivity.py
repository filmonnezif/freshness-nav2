"""Offline sensitivity of v5 verdicts to monitor parameters.

Re-scores the recorded v5 traces with alternative stop deadlines, resume
allowances and output-gap limits. The campaign monitor source is not modified
(its hash is audited); a patched copy is loaded in memory. No experiment is
re-run, so component timeouts inside the chains stay fixed. Stop deadlines of
0.30 s or more cannot be evaluated: scan-loss recovery starts about 0.3 s
after its trigger.
"""
import argparse
import json
import types
from pathlib import Path

from taxonomy import TAXONOMY, ABLATION_MODES, MODE_LABELS

HERE = Path(__file__).parent
BASE = {'delta_revoke': 0.15, 'delta_recover': 0.30, 'gap_max': 0.15}
SWEEP = [('delta_revoke', (0.10, 0.20, 0.25)),
         ('delta_recover', (0.20, 0.50)),
         ('gap_max', (0.10, 0.25))]
NAMES = {'delta_revoke': r'Stop deadline $\delta_R$',
         'delta_recover': r'Resume allowance $\delta_A$',
         'gap_max': 'Max output gap'}


def load_monitor(delta_revoke, delta_recover, gap_max):
    src = (HERE / 'contracts.py').read_text()
    assert src.count('<= .15') == 1
    mod = types.ModuleType('contracts_sensitivity')
    exec(compile(src.replace('<= .15', '<= GAP_MAX'), 'contracts_sensitivity', 'exec'), mod.__dict__)
    mod.DELTA_REVOKE, mod.DELTA_RECOVER, mod.GAP_MAX = delta_revoke, delta_recover, gap_max
    return mod


def score(traces, **params):
    mon = load_monitor(**params)
    out = {}
    for t in traces:
        for mode in ABLATION_MODES:
            r = mon.evaluate_trace(t['records'][mode], t['input_events'], t['case'], t['horizon_s'])
            out[(t['case'], mode)] = out.get((t['case'], mode), 0) + r['contract_pass']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, default=HERE.parents[1] / 'evidence/freshness-contracts-v5')
    ap.add_argument('--out', type=Path, default=HERE / 'sensitivity.json')
    ap.add_argument('--tex', type=Path, default=HERE.parents[1] / 'paper/freshness_sensitivity_table.tex')
    args = ap.parse_args()
    traces = [json.loads((d / 'trace.json').read_text())
              for d in sorted(args.evidence.iterdir()) if (d / 'trace.json').exists()]

    ref = score(traces, **BASE)
    rows = []
    for key, values in SWEEP:
        for v in values:
            res = score(traces, **{**BASE, key: v})
            changed = [{'case': c, 'mode': MODE_LABELS[ABLATION_MODES.index(m)],
                        'baseline': ref[(c, m)], 'varied': n}
                       for (c, m), n in sorted(res.items()) if n != ref[(c, m)]]
            totals = {MODE_LABELS[i]: sum(res[(c, m)] for c in TAXONOMY) for i, m in enumerate(ABLATION_MODES)}
            rows.append({'parameter': key, 'value_s': v, 'totals': totals, 'changed': changed})
    args.out.write_text(json.dumps({'baseline': BASE, 'rows': rows}, indent=2))

    lines = [r'\begin{tabularx}{\columnwidth}{@{}lrX@{}}', r'\toprule',
             r'Parameter & Value (ms) & Passes changed vs.\ baseline \\', r'\midrule']
    for r in rows:
        detail = '; '.join(f"{TAXONOMY[c['case']].label}/{c['mode']} ({c['baseline']}$\\to${c['varied']}/5)"
                           for c in r['changed']) or 'none'
        lines.append(f"{NAMES[r['parameter']]} & {r['value_s']*1000:.0f} & {detail} \\\\")
    lines += [r'\bottomrule', r'\end{tabularx}']
    args.tex.write_text('\n'.join(lines) + '\n')
    for r in rows:
        print(r['parameter'], r['value_s'], r['totals'], r['changed'])


if __name__ == '__main__':
    main()
