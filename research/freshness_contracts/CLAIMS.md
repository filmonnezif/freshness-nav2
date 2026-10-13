# Claim boundaries for the v5 paper

| Claim | Evidence | Boundary |
|---|---|---|
| Recorded configurations differ in timely endpoint revocation | V5 raw traces, fixed monitor, complete matrix | Selected scenarios, host and Nav2 1.3.13 only |
| Native smoother is a relevant command-loss baseline | W versus N/P under command interruption | No claim that a new command watchdog is universally necessary |
| Stamp chronology differs from eventual age expiry | Frozen-stamp and future/reordered-stamp treatments | Application requirements are stronger than a source-age timeout alone |
| Recovery must be tested together with stopping | Separate stop and availability judgments | In-epoch F/O recovery is not implemented |
| Healthy controls can expose unnecessary stopping | All control outcomes are retained | No claim that the reference never stops unnecessarily |
| Un-stamped identical streams cannot reveal sender generation history | Identical observable command content and publication patterns | Interface argument, not a new general impossibility theorem |
| Latencies are reproducible finite-trace measurements | Generated per-scenario values and raw timestamps | Includes delivery/scheduling/observation; no hard real-time bound |
| Verdicts are robust to monitor parameters | Offline re-scoring (`sensitivity.py`): stop deadline 150-250 ms, resume allowance 200-500 ms, gap 150-250 ms change no verdict | Monitor parameters only; component timeouts and rates not varied; deadlines >=300 ms not evaluable |
| False stops are rare in availability controls | 60-trial availability campaign + main campaign: F 1/75, all others 0/75 | Bounds only rates of a few percent; short trials; cause of the F stop not identified |
| Evidence has traceable source and result provenance | Frozen snapshots, hashes, input audits, summary recomputation | Tests and hashes do not prove absence of implementation bugs |

## Claims explicitly not made

Formal verification; generic STL implementation; exact minimal guard sets; unique invention of fault injection, command watchdogs, or timestamp validation; CPU-load comparison; real-robot or dynamics-simulator validation; physical braking performance; collision avoidance; universal Nav2 defect; deployment reliability or independent statistical inference from 640 paired evaluations.

