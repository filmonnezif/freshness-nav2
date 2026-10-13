"""Public interface for the v5 finite-trace monitor."""
from contracts import evaluate_trace


def evaluate(records, events, case, horizon):
    return evaluate_trace(records, events, case, horizon)
