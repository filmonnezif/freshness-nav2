"""Independent evidence completeness, treatment and summary checks for v5."""
import hashlib
import json
import math
from pathlib import Path
from taxonomy import TAXONOMY, ABLATION_MODES, DURATION
from oracle import evaluate


def validate_treatment(t):
    case=t['case'];spec=TAXONOMY[case];es=t['input_events']
    assert t['cpu_load'] is False
    assert t['horizon_s']==DURATION
    for kind in ('clock','command'):
        assert any(e['event']==kind and e['wall_elapsed']<.5 for e in es), (case,'missing warmup input',kind)
    transitions=[e['wall_elapsed'] for e in es if e['event']=='scheduled_transition']
    assert len(transitions)==1 and transitions[0]>=spec.fault_onset
    transition=transitions[0]
    # The scheduler transition is logged explicitly. A publication started in
    # the previous loop can complete just after the nominal 1.0 s schedule.
    # Use the actual transition, not an invented exact scheduling boundary.
    fault=[e for e in es if transition <= e['wall_elapsed'] < (spec.recovery_onset or DURATION)]
    scans=[e for e in es if e['event']=='scan']
    commands=[e for e in es if e['event']=='command']
    assert all(e['vx']==.22 and e['wz']==.10 for e in commands)
    if case in ('cmd_loss','cmd_recovery'):
        assert not any(e['event']=='command' for e in fault), (case,'unexpected command')
    if case in ('obs_loss','obs_recovery','clock_backward_jump','clock_epoch_recovery','clock_loss','clock_stall'):
        assert not any(e['event']=='scan' for e in fault), (case,'unexpected scan')
    if case=='obs_noscan_startup':
        assert not scans
    if case=='clock_loss':
        assert not any(e['event']=='clock' for e in fault)
    if case=='clock_stall':
        vals=[e['value'] for e in fault if e['event']=='clock']
        assert len(vals)>10 and len(set(vals))==1
    clock=None;stamps=[]
    for e in es:
        if e['event']=='clock':clock=e['value']
        if e['event']=='scan':
            assert clock is not None
            if case in ('healthy','repeated_command'):
                assert abs(e['stamp']-clock)<1e-7
            if case=='benign_stamp_lag':
                assert abs(clock-e['stamp']-.05)<1e-7
            if e['wall_elapsed']>=transition:
                stamps.append(e['stamp'])
                if case=='chrono_small_future_skew':assert abs(e['stamp']-clock-.05)<1e-7
                if case=='chrono_large_future_skew':assert abs(e['stamp']-clock-10)<1e-7
    if case=='chrono_duplicate_stamps':
        before=[e['stamp'] for e in scans if e['wall_elapsed']<transition]
        assert len(stamps)>5 and set(stamps)=={before[-1]}
    if case=='chrono_reordered_stamps':
        assert any(b<a for a,b in zip(stamps,stamps[1:]))
        assert any(b>a for a,b in zip(stamps,stamps[1:]))
    if spec.recovery_onset is not None:
        kind='command' if spec.obligation=='command' else 'scan'
        assert any(e['event']==kind and e['wall_elapsed']>=spec.recovery_onset for e in es)
    for mode,rs in t['records'].items():
        assert all(math.isfinite(r[k]) for r in rs for k in ('wall_elapsed','vx','wz'))
        if case!='obs_noscan_startup':
            assert any(.3<=r['wall_elapsed']<1 and abs(r['vx']-.22)<1e-4 and abs(r['wz']-.1)<1e-4 for r in rs),(case,mode,'warmup')


def audit_campaign(path, expected_repeats=5, cases=None):
    cases=list(TAXONOMY) if cases is None else cases
    path=Path(path);data=json.loads((path/'results.json').read_text())
    assert data['version']==5 and data['complete']
    assert data['repeats']==expected_repeats
    assert data['cases']==cases
    assert data['ablation_modes']==ABLATION_MODES
    for name,digest in data['source_hashes'].items():
        assert hashlib.sha256((path/'source'/name).read_bytes()).hexdigest()==digest,(name,'snapshot mismatch')
        assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest,(name,'current source mismatch')
    expected={(case,rep) for case in cases for rep in range(expected_repeats)}
    actual=[(t['case'],t['repeat']) for t in data['results']]
    assert len(actual)==len(expected) and set(actual)==expected
    assert [list(x) for x in actual]==data['schedule']
    for t in data['results']:
        raw=json.loads((path/f"{t['case']}_r{t['repeat']:02d}"/'trace.json').read_text())
        assert set(raw['records'])==set(ABLATION_MODES)
        assert raw['summary']==t['summary']
        validate_treatment(raw)
        for mode,records in raw['records'].items():
            r=evaluate(records,raw['input_events'],raw['case'],raw['horizon_s'])
            assert r==t['summary'][mode],(t['case'],t['repeat'],mode,'summary differs')
    return data
