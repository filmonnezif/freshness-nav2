# V5 audited finite-trace results

80 trials, 5 repetitions per scenario, 640 paired endpoint evaluations. Nominal host conditions. No physical base.

| Scenario | N | W | P | C | F | O | E | G |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Healthy | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 |
| Valid stamp lag (50 ms) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Repeated command control | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Command loss | 0/5 | 5/5 | 0/5 | 5/5 | 0/5 | 0/5 | 0/5 | 5/5 |
| Command loss + recovery | 0/5 | 5/5 | 0/5 | 5/5 | 0/5 | 0/5 | 0/5 | 5/5 |
| No-scan startup | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Scan loss | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Scan loss + recovery | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Future stamp (+50 ms) | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 0/5 | 0/5 | 5/5 |
| Future stamp (+10 s) | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 0/5 | 0/5 | 5/5 |
| Frozen scan stamp | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 0/5 | 5/5 |
| Reordered scan stamps | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 0/5 | 5/5 |
| Clock reset + scan loss | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 5/5 |
| Clock reset + recovery | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | 5/5 |
| Clock delivery + scan loss | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 |
| Clock stall + scan loss | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 |

N=native CM; W=native smoother + CM; P=periodic relay + CM; C/F/O/E=P plus command/future/order/epoch check; G=combined checks plus clock receipt/progress check.

A recovery cell passes only when both the stop and resumed-delivery obligations pass. Deadlines are derived from actual input events. Failures are retained. See `PROTOCOL.md` for exact finite-horizon semantics.
