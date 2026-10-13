# Experiment code (v5)

This directory holds the experiment, the monitor, and the analysis scripts. Commands to verify and reproduce the results are in the [top-level README](../../README.md). Read [PROTOCOL.md](PROTOCOL.md) for the frozen requirements and scope, [RESULTS.md](RESULTS.md) for the generated judgments, and [CLAIMS.md](CLAIMS.md) for what the evidence does and does not support.

## Files

- `probe.py`: ROS 2 campaign runner. Launches the eight chains per trial, injects the scenario, and records raw input/output traces, node logs, parameters, and a source snapshot.
- `taxonomy.py`: the 16 scenarios, eight configurations, and fixed thresholds.
- `guards.py`, `guard_node.py`: periodic relay and the optional reference checks (C, F, O, E, G).
- `contracts.py`, `oracle.py`: event-derived finite-trace monitor.
- `test_oracle.py`, `test_guards.py`, `test_audit.py`: monitor counterexamples and configuration checks.
- `audit.py`: source-hash, completeness, and input-treatment checks, plus recomputation of every judgment from raw traces.
- `build_assets.py`: audited figures, LaTeX tables, `measurements.csv`, `RESULTS.md`, and `AUDIT.json`.
- `sensitivity.py`: offline re-scoring under alternative monitor deadlines and gap limits (`sensitivity.json`, paper Table IV).
- `upstream/`: the inspected Nav2 1.3.13 sources, with their original license headers.

## Frozen sources

`probe.py`, `guards.py`, `guard_node.py`, `contracts.py`, `oracle.py`, `taxonomy.py`, and `PROTOCOL.md` are hashed into every campaign's `results.json`. The audit refuses to build assets if any of them differ from the recorded hashes. Do not edit them to regenerate old results: change them, bump the version, and rerun the campaign into a new evidence folder.

## Notes on the evidence

- The 80 main-campaign trials contain 640 *paired* endpoint evaluations, not 640 independent runs.
- Three scenarios are availability controls. Two of them (healthy and repeated command) are intentionally indistinguishable constant-command streams.
- Recovery cells require both the stop and the resume obligation.
- Latencies are measured from event-derived triggers, not from the scheduled fault onset. Missing revocations stay missing.
- `evidence/freshness-contracts-v5-availability/` is a separate 60-trial campaign of the three availability controls (seed 20261013, same frozen sources). It is used only for the false-stop estimate and is not merged into the 80-trial results.
