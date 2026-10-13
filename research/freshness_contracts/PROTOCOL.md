# V5 finite-trace protocol

Frozen before the final v5 campaign. V1-v4 data and source are historical; they are not pooled with v5. No claim of formal verification, minimal guards, CPU-load comparison, or physical braking is made.

## Question and scope

How do native Nav2 components and explicitly selected reference checks satisfy different software endpoint obligations under command interruption, scan chronology faults, and clock discontinuities? These obligations are requirements chosen for this experiment, not a statement of Nav2's documented safety guarantees.

Eight simultaneous configurations: N = native Collision Monitor (CM); W = native 50 Hz velocity smoother with 0.30 s command timeout, then CM; P = plain 50 Hz steady-timer relay, then CM; C/F/O/E = the same relay plus command lease/future-stamp/order/epoch check, then CM; G = all four plus clock receipt/progress checking, then CM. Each component has its own process; they share the host, network, and publisher. No shared speed scaling is hidden in the relay. Every chain uses native CM scan timeout 1.00 s. Guard masks are in taxonomy.py.

C uses a 0.30 s monotonic command receipt lease. F rejects a scan more than 0.02 s ahead of the latest received clock. O rejects a non-increasing stamp. F/O latch until an epoch invalidation or process restart; normal in-epoch recovery from these faults is not implemented or claimed. E clears retained commands and scan/order/future state on a backward clock change; it blocks until a scan valid in the new epoch arrives. G additionally requires a clock message and a change in clock value in the previous 0.30 wall seconds. Treating a paused simulation clock as a reason to revoke is an application policy, not a ROS requirement.

## Setup

ROS 2 Jazzy installed binaries, package versions and platform recorded. DDS domain 143, unique per-campaign/per-trial topic prefixes, identity base/odometry frame, transform compensation disabled. Synthetic LaserScan: 360 ranges at 5 m, outside a 0.6 m square stop polygon. Commands: Twist with vx=0.22 m/s and wz=0.10 rad/s. Clock 100 Hz, scans 10 Hz, commands 20 Hz. No robot base, simulator dynamics, or artificial CPU stress is attached.

Each trial starts after lifecycle activation and preflight zero delivery to every chain. No scans are sent during preflight. Trial duration is 3.20 wall seconds. Every non-startup trial must exhibit requested motion in each chain between 0.3 and 1.0 s. A failed setup is retained and aborts the campaign; it is not retried invisibly or counted as a policy failure. Scenario order is shuffled with a recorded fixed seed. Five repetitions of 16 scenarios yield 80 trials and 640 paired endpoint evaluations. These are descriptive, finite-trace repetitions, not independent estimates of deployment reliability.

## Scenarios

The full definitions are in taxonomy.py. Three availability controls: healthy, valid 50 ms stamp lag, and repeated constant un-stamped commands. The repeated-command control is deliberately observationally equivalent to a legitimate constant command; it demonstrates the interface's inability to reveal sender generation age. It is not counted as a separately detectable failure.

Thirteen fault/recovery scenarios: command loss; command loss/recovery; no-scan startup; scan loss; scan loss/recovery; +50 ms future stamps; +10 s future stamps; exact repetition of the last pre-fault scan stamp; alternating fresh/200 ms backdated scan stamps; backward clock reset plus scan loss; backward reset plus scan recovery; clock delivery plus scan loss; clock value stall plus scan loss. Clock/scan compound treatments are labeled explicitly. Commands continue in clock/scan fault scenarios. Fault scheduling begins at 1.0 s (startup at zero); recovery is scheduled at 2.3 s. No queued burst, recorded replay, or transport delay is claimed.

## Executable obligations

Observer time r is monotonic wall elapsed time. ROS time is a piecewise-constant signal t(r); output u(r) is the held last command received by the observer. Silence after zero retains zero; silence after nonzero retains nonzero; no observed value is unknown and cannot satisfy an obligation. Both vx and wz are checked.

Trigger q is derived independently from actual logged publisher events: last command publication plus 0.30 s during a gap; first observed clock update making the latest scan older than 1.00 s; first scan exceeding the latest clock by 0.02 s; first non-increasing scan stamp; first backward clock event; last clock publication plus 0.30 s during a gap; or last change of clock value plus 0.30 s during a stall. Startup uses first command publication. Publisher times are not receiver times; the 0.15 s response allowance includes transport, scheduling, filter/smoother response, and observer delivery.

For every triggered case, require u(r)=0 throughout [q+0.15, h), where h is the actual valid recovery publication time or the trial horizon. Revocation latency is first time at/after q from which zero is continuously held to h, minus q. If already zero at q it is zero; no revocation is reported as missing, never replaced by a numerical zero. Late revocation can have a measured latency while still failing the obligation.

For recovery cases, ALSO require matching requested motion continuously from actual recovery publication +0.30 s until the horizon, with new output gaps no greater than 0.15 s. A pipeline that never stopped fails even if it subsequently matches the desired command. Recovery latency is first sustained matching output after recovery minus recovery publication time. Controls require matching output and the same delivery continuity from 0.5 s to the horizon. Missing triggers, missing recovery events, non-monotonic observer traces, and insufficient observation horizons invalidate evaluation.

The checker is a specialized finite-trace monitor, not a general STL engine or a proof over unobserved executions. Unit tests include deadline, boundary-hold, transient stop, angular motion, missing output, input-trigger derivation, and false recovery counterexamples. Scenarios test specific obligations separately, not exhaustive conjunctions of all possible faults.

## Evidence and reporting

Record raw publication and endpoint events, actual horizon, launch logs, parameters, installed package versions, platform, schedule, and SHA-256 snapshots of every experimental source dependency and this protocol. Final asset generation validates all hashes, completeness, unique trial IDs, warmup, input treatments, and recomputed summaries. Preserve failures. Report stop and recovery separately, scenario-specific latencies, all repetitions, and timeouts/failures. No pooled heterogeneous latency distribution or minimality annotation is allowed. No run-dependent threshold tuning is allowed in the final campaign.
