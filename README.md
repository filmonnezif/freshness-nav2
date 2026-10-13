# Freshness Is a Pipeline Property: Testing Temporal Obligations in Nav2 Command Chains

Code, raw data, and paper source for the ITT 2026 paper by Filmon Nezif (Higher Colleges of Technology). The paper links here as its artifact.

The study asks how ROS 2 Navigation2 (Nav2) command chains respond when commands stop arriving, scan timestamps become invalid, or the clock jumps to a new epoch. An executable finite-trace monitor derives each fault trigger from the recorded input events and checks three things: does the chain emit zero by a fixed deadline, does it stay stopped, and does it resume after recovery. Eight configurations combine Nav2's Collision Monitor, its velocity smoother, a periodic relay, and selected reference checks.

Everything in the paper can be recomputed from the raw traces in this repository without ROS. The ROS experiment itself can be re-run in a container.

## Results at a glance

Main campaign: 16 scenarios × 5 repetitions = 80 trials, 640 paired endpoint evaluations (Nav2 1.3.13, ROS 2 Jazzy).

| Configuration | | Passes (of 80) |
|---|---|---:|
| N | native Collision Monitor (CM) | 30 |
| W | native velocity smoother + CM | 40 |
| P | periodic relay + CM | 30 |
| C | P + command-receipt lease | 40 |
| F | P + future-stamp check | 39 |
| O | P + stamp-order check | 40 |
| E | P + clock-epoch invalidation | 40 |
| G | all checks + clock receipt/progress | 80 |

- **Delivery and chronology are different problems.** The smoother's command timeout (W) and the lease (C) handle command loss. Only the timestamp checks catch future, frozen, or reordered stamps before CM's age timeout does.
- **Recovery has to be tested too.** After a clock reset followed by valid new-epoch scans, the stamp-order check (O) keeps driving through the reset, then treats the valid new-epoch scans as out of order, latches, and never resumes (0/5). Epoch invalidation (E) stops and resumes (5/5).
- **Sensitivity.** Re-scoring the traces offline with stop deadlines of 150–250 ms, resume allowances of 200–500 ms, and output-gap limits of 150–250 ms changes no verdict. At 100 ms, W loses 4 of 10 command-loss passes, matching its ~96 ms mean response.
- **False stops.** A separate 60-trial campaign of the availability controls found no false stops. Pooled over 75 availability trials per chain: F stopped falsely once (95% CI 0.03–7.2%), every other chain never (95% upper bound 3.9%).

Per-scenario results: [RESULTS.md](research/freshness_contracts/RESULTS.md). Every endpoint judgment and latency: [measurements.csv](research/freshness_contracts/measurements.csv). What the evidence does and does not support: [CLAIMS.md](research/freshness_contracts/CLAIMS.md).

## Repository layout

```
research/freshness_contracts/   experiment runner, relays/checks, monitor, audit, figures, sensitivity, tests
evidence/freshness-contracts-v5/               main campaign: 80 trials (raw traces, logs, parameters, source snapshot)
evidence/freshness-contracts-v5-availability/  extra campaign: 60 availability-control trials (false-stop estimate)
paper/                          LaTeX source, generated tables and figures, response to reviewers
docker/Containerfile            ROS 2 Jazzy + the two Nav2 components the experiment uses
scripts/run_campaign.sh         build the container and run a new campaign
```

Each trial folder holds `trace.json` (all input events and the output of all eight chains), each node's log, and the `parameters.yaml` it ran with. Each campaign's `results.json` records the shuffled schedule, seed, exact package versions, host, and SHA-256 hashes of the frozen sources. A copy of those sources is kept in `source/`.

## 1. Verify the results (no ROS, about 1 minute)

Requires Python 3 with NumPy and Matplotlib (`pip install -r requirements.txt`).

```sh
make verify        # unit tests + full audit of both campaigns
make sensitivity   # offline re-scoring (paper Table IV)
make assets        # regenerate figures, tables, measurements.csv, RESULTS.md
```

The audit checks the frozen sources against their recorded hashes, validates that each injected fault pattern is present in the inputs, and recomputes all 640 + 480 judgments from the raw traces. It refuses to proceed if anything disagrees.

## 2. Rebuild the paper

Requires pdfLaTeX and BibTeX (the IEEEtran class is included).

```sh
make paper         # writes paper/freshness_contracts.pdf
```

## 3. Re-run the ROS experiment

Requires podman or docker. Nothing else needs to be installed on the host.

```sh
make campaign                                  # 80 trials into evidence/reproduction (about 80 minutes)
make verify-run RUN=reproduction               # or see the audit command printed at the end
```

For other runs, call the script directly. Any `probe.py` option can be passed through:

```sh
scripts/run_campaign.sh availability-rerun --repeats 20 \
  --cases healthy benign_stamp_lag repeated_command --seed 20261013
python3 research/freshness_contracts/build_assets.py --evidence evidence/availability-rerun \
  --audit-only --expected-repeats 20 --cases healthy benign_stamp_lag repeated_command
```

Notes:

- The experiment uses ROS domain 143 and unique per-trial namespaces. No robot is actuated, and no robot base should subscribe to these topics.
- The container installs the *current* Jazzy packages. The paper used `nav2-collision-monitor` and `nav2-velocity-smoother` `1.3.13-1noble.20260903`, as recorded in each `results.json`. If Jazzy has moved on, results may differ. For an exact match, point apt at the ROS snapshot repository for that date.
- Latencies depend on the host. The paper used an Intel Core i7-1355U (12 logical CPUs, 15 GiB RAM) with no artificial load.
- A failed setup aborts the campaign and keeps its files. Nothing is deleted or retried automatically.

## Scope

The outcome measured is a zero command observed at a software endpoint. The study does not measure braking, collisions, or base dynamics. It uses one Nav2 version, one host, synthetic clear scans, and fixed publication rates. The combined configuration G was designed against these requirements: its 80/80 shows that they can be satisfied together, not that G is minimal or safe to deploy. See [PROTOCOL.md](research/freshness_contracts/PROTOCOL.md) and the paper's limitations section.

## Citation

See [CITATION.cff](CITATION.cff).

## License

Code: [Apache-2.0](LICENSE). Data and generated results: [CC BY 4.0](LICENSE-DATA.md). Files in `research/freshness_contracts/upstream/` keep their original Nav2 license headers.
