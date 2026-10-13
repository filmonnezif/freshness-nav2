# Response to Reviewers

**Paper:** Freshness Is a Pipeline Property: Testing Temporal Obligations in Nav2 Command Chains

We thank the three reviewers for their careful and constructive reviews. The revision adds two new analyses: an offline sensitivity analysis of all 640 recorded evaluations, and an extended campaign of the availability controls that measures false stops. It also expands the related work, adds a parameter table, and gives an anonymized artifact link. Section and table numbers below refer to the revised manuscript.

## Summary of changes

| # | Concern | Reviewer(s) | Change | Location |
|---|---------|-------------|--------|----------|
| 1 | No sensitivity analysis of deadlines, timeouts, or triggers | R3 | Re-scored all 80 traces with different stop deadlines, resume allowances, and gap limits | §V-C, Table IV |
| 2 | Unexplained false stop in one healthy F trial; false-stop rates | R2, R3 | Ran 60 additional availability-control trials (480 evaluations); reported pooled false-stop rates with confidence intervals and the logging needed to diagnose the cause | §V-B, §VI-C |
| 3 | Configuration details missing | R3 | New parameter table covering every component and monitor setting | §IV-A, Table II |
| 4 | Artifact not accessible | R3 | Anonymized artifact link added | §IV-C |
| 5 | Related work: ROS runtime monitoring, command timeouts, safety standards | R3 | New paragraphs on ROSRV, ROSMonitoring, RTAMT, twist_mux, diff_drive_controller, IEC 61508, ISO 13849-1, ISO 3691-4 | §II-A, §II-B |
| 6 | G's perfect score could be over-read | R2 | Results now state explicitly what G's score does and does not show | §V |
| 7 | External validity (one version, one host, synthetic inputs, no physical robot) | R1, R2, R3 | Scope restated as a deliberate boundary | §VI-C |

## Reviewer 1

> It is narrow and software-only, but methodologically solid.

Thank you. The narrow scope is deliberate: it isolates temporal behavior from transforms, obstacle geometry, and base dynamics. §VI-C now states this boundary together with the new false-stop measurements (item 2).

## Reviewer 2

> Limited external validity: one Nav2 version, one host, synthetic clear scans, fixed publication rates, short trials, software endpoints only.

We agree, and §VI-C lists these limits. Physical braking, obstacle interaction, network partitions, CPU load, and DDS policy variation would each need their own experimental design, so we leave them to future work and do not generalize beyond the tested configurations. The revision does add evidence on two points within the current boundary: whether the verdicts depend on the chosen monitor parameters (item 1), and the false-stop rate of each chain under longer healthy runs (item 2).

> One healthy trial also fails for the future-stamp configuration, and the recorded traces are insufficient to determine the exact internal cause.

We ran a separate campaign of the three availability controls (healthy input, valid 50 ms stamp lag, repeated command) with 20 repetitions each: 60 trials and 480 paired evaluations. It used the same frozen sources, packages, and host, with a new shuffle seed, and passed the same audit (source hashes, input treatments, recomputed judgments). Every chain passed every trial. Pooled with the main campaign, F has 1 false stop in 75 availability trials (95% Clopper–Pearson interval 0.03–7.2%), and every other chain has 0 in 75 (one-sided 95% upper bound 3.9%). The failure is rare at these rates but cannot be excluded. We still cannot identify its cause from the traces, and §V-B now names the missing signal: each filter's local clock-receipt state, logged next to its decision. §VI-C also notes that 75 short trials bound only rates of a few percent, and that long-duration healthy operation remains future work.

> The combined guard is designed for the selected requirements, so its perfect score should not be interpreted as proof of minimality or deployment-level safety.

Agreed. Before, this caveat appeared only in the limitations. The Results section now says directly that G's 80/80 shows only that the selected requirements can be satisfied together. G was designed against those requirements, so the score says nothing about minimality, correctness outside the tested scenarios, or deployment-level safety.

## Reviewer 3

> 1. The pass/fail outcomes depend on the selected trigger definitions, timeouts, and response deadline; no sensitivity analysis.

The monitor evaluates recorded traces offline, so we re-scored all 640 evaluations without re-running any experiment. New §V-C and Table IV give the results:

- **Stop deadline.** Values of 150, 200, and 250 ms leave every count unchanged. At 100 ms, W (native smoother) loses 4 of its 10 command-loss and command-recovery passes, consistent with its mean response of about 96 ms.
- **Resume allowance.** Values from 200 to 500 ms change nothing.
- **Output-gap limit.** Values of 150 and 250 ms change nothing. At 100 ms, one healthy E trial fails.
- **Longer deadlines.** Deadlines of 300 ms or more cannot be evaluated, because scan-loss recovery begins about 0.3 s after its trigger.
- **Trigger thresholds.** The command lease (0.30 s) and scan-age limit (1.0 s) are set equal to the configured component timeouts. Varying them offline would test a mismatch between requirement and configuration rather than the chains, so we state this rather than sweep them.

The qualitative findings therefore hold over the range of monitor parameters that can be evaluated.

> 2. Five short repetitions; unexplained false stop; longer healthy runs and false-stop rates.

We ran a separate campaign of the three availability controls (healthy input, valid 50 ms stamp lag, repeated command) with 20 repetitions each: 60 trials and 480 paired evaluations. It used the same frozen sources, packages, and host, with a new shuffle seed, and passed the same audit (source hashes, input treatments, recomputed judgments). Every chain passed every trial. Pooled with the main campaign, F has 1 false stop in 75 availability trials (95% Clopper–Pearson interval 0.03–7.2%), and every other chain has 0 in 75 (one-sided 95% upper bound 3.9%). The failure is rare at these rates but cannot be excluded. We still cannot identify its cause from the traces, and §V-B now names the missing signal: each filter's local clock-receipt state, logged next to its decision. §VI-C also notes that 75 short trials bound only rates of a few percent, and that long-duration healthy operation remains future work.

The sensitivity analysis (item 1) also shows that the main verdicts do not hinge on the particular five repetitions passing narrowly: changing the deadline by +50 or +100 ms changes no verdict.

> 3. Configuration details and artifact access missing; related work on ROS runtime monitoring, command-timeout mechanisms, and safety standards.

- **Configuration.** New Table II lists every component and monitor parameter. The values are taken from the recorded `parameters.yaml`.
- **Artifact.** §IV-C now gives an anonymized link to the traces, source snapshots, monitor, and build scripts.
- **Related work.** §II-B now discusses ROSRV, ROSMonitoring, and RTAMT, and explains that they could host our obligations; our contribution is the trigger derivation and the choice of obligations. §II-A covers receipt timeouts in `twist_mux` and `diff_drive_controller`, which bound delivery gaps but do not check timestamps or clock epochs. §II-B places the work relative to IEC 61508, ISO 13849-1, and ISO 3691-4: the traces can serve as software test evidence within such a process, but they are not a safety-integrity argument.
