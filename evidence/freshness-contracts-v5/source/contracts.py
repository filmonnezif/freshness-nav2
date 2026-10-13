"""Finite-trace obligations on monotonic observer time; not a general STL engine.

Triggers come from logged publisher events. Outputs use last-received hold.
Transport, scheduling and observation delay are included in measured latency.
"""
import math
from taxonomy import (TAXONOMY, TAU_CMD, TAU_SCAN, TAU_CLOCK,
                      EPSILON_SKEW, DELTA_REVOKE, DELTA_RECOVER)


def is_zero(r):
    return r is not None and all(math.isfinite(r[k]) and abs(r[k]) <= 1e-4 for k in ('vx', 'wz'))


def is_matching(r):
    return r is not None and abs(r['vx'] - .22) <= 1e-3 and abs(r['wz'] - .10) <= 1e-3


def held(records, t):
    before = [r for r in records if r['wall_elapsed'] <= t]
    return before[-1] if before else None


def holds(records, start, end, predicate):
    """Exact check on a piecewise-constant received-output signal, [start,end)."""
    return end > start and predicate(held(records, start)) and all(
        predicate(r) for r in records if start < r['wall_elapsed'] < end)


def first_sustained(records, start, end, predicate):
    candidates = [start] + [r['wall_elapsed'] for r in records if start < r['wall_elapsed'] < end]
    return next((t for t in candidates if holds(records, t, end, predicate)), None)


def first_gap(events, kind, lease, horizon):
    times = [e['wall_elapsed'] for e in events if e['event'] == kind]
    for i, t in enumerate(times):
        nxt = times[i+1] if i+1 < len(times) else horizon
        if nxt > t + lease and t + lease >= .5:
            return t + lease
    return None


def derive_obligation(case, events, horizon):
    spec = TAXONOMY[case]
    if any(b['wall_elapsed'] < a['wall_elapsed'] for a, b in zip(events, events[1:])):
        raise ValueError('Input events must be in monotonic observer order')
    trigger = None
    recovery = None
    clock = stamp = previous_clock = previous_stamp = None
    progress_events = []
    for e in events:
        r = e['wall_elapsed']
        if r > horizon:
            break
        if e['event'] == 'clock':
            clock = e['value']
            if previous_clock is None or clock != previous_clock:
                progress_events.append({'event': 'advance', 'wall_elapsed': r})
            if spec.obligation == 'epoch' and previous_clock is not None and clock < previous_clock - 1e-6 and trigger is None:
                trigger = r
            previous_clock = clock
        elif e['event'] == 'scan':
            stamp = e['stamp']
            if spec.obligation == 'future' and clock is not None and stamp > clock + EPSILON_SKEW and trigger is None:
                trigger = r
            if spec.obligation == 'order' and previous_stamp is not None and stamp <= previous_stamp and trigger is None:
                trigger = r
            previous_stamp = stamp
        if spec.obligation == 'scan_age' and clock is not None and stamp is not None and clock - stamp > TAU_SCAN and trigger is None:
            trigger = r
        if spec.obligation == 'startup' and e['event'] == 'command' and trigger is None:
            trigger = r
        if spec.recovery_onset is not None and r >= spec.recovery_onset and recovery is None:
            if spec.obligation == 'command' and e['event'] == 'command':
                recovery = r
            elif spec.obligation in ('scan_age', 'epoch') and e['event'] == 'scan' and clock is not None and -EPSILON_SKEW <= clock-stamp <= TAU_SCAN:
                recovery = r
    if spec.obligation == 'command':
        trigger = first_gap(events, 'command', TAU_CMD, horizon)
    elif spec.obligation == 'clock_receipt':
        trigger = first_gap(events, 'clock', TAU_CLOCK, horizon)
    elif spec.obligation == 'clock_progress':
        trigger = first_gap(progress_events, 'advance', TAU_CLOCK, horizon)
    if spec.obligation != 'availability' and trigger is None:
        raise ValueError(f'{case}: required fault trigger absent from input trace')
    if spec.recovery_onset is not None and (recovery is None or recovery <= trigger + DELTA_REVOKE):
        raise ValueError(f'{case}: missing recovery or insufficient stop observation interval')
    if trigger is not None and trigger + DELTA_REVOKE >= horizon:
        raise ValueError('Trace is too short to evaluate the revocation deadline')
    return {'trigger_s': trigger, 'recovery_s': recovery, 'obligation': spec.obligation}


def evaluate_trace(records, events, case, horizon):
    if any(b['wall_elapsed'] < a['wall_elapsed'] for a, b in zip(records, records[1:])):
        raise ValueError('Output records must be monotonic')
    obligation = derive_obligation(case, events, horizon)
    trigger, recovery = obligation['trigger_s'], obligation['recovery_s']
    stop_pass = recovery_pass = None
    revoke_latency = recovery_latency = None
    if trigger is not None:
        stop_end = recovery if recovery is not None else horizon
        stop_pass = holds(records, trigger + DELTA_REVOKE, stop_end, is_zero)
        revoked = first_sustained(records, trigger, stop_end, is_zero)
        if revoked is not None:
            revoke_latency = revoked - trigger
    if recovery is not None or trigger is None:
        start = recovery if recovery is not None else .5
        deadline = start + DELTA_RECOVER if recovery is not None else start
        if deadline >= horizon:
            raise ValueError('Trace is too short to evaluate availability')
        recovery_pass = holds(records, deadline, horizon, is_matching)
        arrivals = [r['wall_elapsed'] for r in records if deadline <= r['wall_elapsed'] < horizon]
        # Availability requires continuing output delivery, not just a held value.
        bounds = [deadline] + arrivals + [horizon]
        recovery_pass = recovery_pass and bool(arrivals) and max(b-a for a,b in zip(bounds,bounds[1:])) <= .15
        if recovery is not None:
            resumed = first_sustained(records, recovery, horizon, is_matching)
            if resumed is not None:
                recovery_latency = resumed - recovery
    passed = (stop_pass is not False and recovery_pass is not False)
    return {**obligation, 'contract_pass': bool(passed), 'stop_pass': stop_pass,
            'availability_pass': recovery_pass, 'revoke_latency_s': revoke_latency,
            'recovery_latency_s': recovery_latency, 'deadline_s': DELTA_REVOKE if trigger is not None else None}
