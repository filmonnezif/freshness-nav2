#!/usr/bin/env python3
"""Isolated v5 finite-trace command-pipeline experiment."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import platform
import random
import time
from typing import Dict, List, Any

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Clock
from lifecycle_msgs.srv import ChangeState
from lifecycle_msgs.msg import Transition

# Project imports
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/freshness_contracts'))
sys.path.insert(0, str(ROOT / 'scripts'))

from taxonomy import TAXONOMY, ABLATION_MODES, MODE_GUARDS, DURATION
from oracle import evaluate
class ProbeDriver(Node):
    def __init__(self, prefix: str, modes: List[str]):
        super().__init__('probe_driver')
        self.prefix = prefix
        self.modes = modes
        self.clock_pub = self.create_publisher(Clock, f'{prefix}/clock', qos_profile_sensor_data)
        self.scan_pub = self.create_publisher(LaserScan, f'{prefix}/scan', qos_profile_sensor_data)
        self.cmd_pub = self.create_publisher(Twist, f'{prefix}/command', 10)
        
        self.records: Dict[str, List[Dict[str, Any]]] = {m: [] for m in modes}
        self.events: List[Dict[str, Any]] = []
        self.preflight_seen = set()
        self.start_wall: Optional[float] = None
        self.sim_time = 100.0

        for mode in modes:
            self.create_subscription(
                Twist, 
                f'{prefix}/{mode}/out',
                lambda msg, m=mode: self.capture_out(m, msg), 
                10
            )

        self.lifecycle_clients = {
            mode: self.create_client(ChangeState, f'{prefix}/{mode}_cm/change_state') 
            for mode in modes
        }
        self.lifecycle_clients['stock_smoother'] = self.create_client(
            ChangeState, f'{prefix}/stock_smoother/change_state'
        )

    def capture_out(self, mode: str, msg: Twist):
        if abs(msg.linear.x) < 1e-6 and abs(msg.angular.z) < 1e-6:
            self.preflight_seen.add(mode)
        if self.start_wall is not None:
            now_wall = time.monotonic()
            self.records[mode].append({
                'wall_elapsed': now_wall - self.start_wall,
                'sim_time': self.sim_time,
                'vx': msg.linear.x,
                'wz': msg.angular.z
            })

    @staticmethod
    def set_stamp(target_stamp, seconds: float):
        ns = round(seconds * 1e9)
        target_stamp.sec, target_stamp.nanosec = divmod(ns, 10**9)

    def publish_clock(self, value: float):
        self.sim_time = value
        msg = Clock()
        self.set_stamp(msg.clock, value)
        self.clock_pub.publish(msg)
        if self.start_wall is not None:
            self.events.append({
                'event': 'clock',
                'wall_elapsed': time.monotonic() - self.start_wall,
                'value': value
            })

    def publish_scan(self, stamp_value: float):
        msg = LaserScan()
        self.set_stamp(msg.header.stamp, stamp_value)
        msg.header.frame_id = 'probe_base'
        msg.angle_min = -math.pi
        msg.angle_max = math.pi
        msg.angle_increment = 2 * math.pi / 359
        msg.range_min = 0.05
        msg.range_max = 10.0
        msg.ranges = [5.0] * 360
        self.scan_pub.publish(msg)
        if self.start_wall is not None:
            self.events.append({
                'event': 'scan',
                'wall_elapsed': time.monotonic() - self.start_wall,
                'stamp': stamp_value
            })

    def publish_cmd(self, vx: float = 0.22, wz: float = 0.10):
        msg = Twist()
        msg.linear.x = vx
        msg.angular.z = wz
        self.cmd_pub.publish(msg)
        if self.start_wall is not None:
            self.events.append({
                'event': 'command',
                'wall_elapsed': time.monotonic() - self.start_wall,
                'vx': vx,
                'wz': wz
            })

def pump(executor, seconds: float):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=0.002)

def run_trial(scenario_name: str, repeat: int, outdir: Path) -> Dict[str, Any]:
    spec = TAXONOMY[scenario_name]
    prefix = f'/freshness_probe/v5_{os.getpid()}/{scenario_name}_r{repeat:02d}'
    modes = list(ABLATION_MODES)
    
    driver = ProbeDriver(prefix, modes)
    executor = SingleThreadedExecutor()
    executor.add_node(driver)

    procs = []
    logs = []

    trial_dir = outdir / f'{scenario_name}_r{repeat:02d}'
    trial_dir.mkdir(parents=True, exist_ok=False)
    
    # Common Nav2 parameter file
    cfg = trial_dir / 'parameters.yaml'
    cfg.write_text(f'''/**:
  ros__parameters:
    use_sim_time: true
    smoothing_frequency: 50.0
    feedback: OPEN_LOOP
    scale_velocities: false
    max_velocity: [0.22, 0.0, 1.0]
    min_velocity: [-0.22, 0.0, -1.0]
    max_accel: [2.5, 0.0, 3.2]
    max_decel: [-2.5, 0.0, -3.2]
    deadband_velocity: [0.0, 0.0, 0.0]
    velocity_timeout: 0.30
    enable_stamped_cmd_vel: false
    base_frame_id: probe_base
    odom_frame_id: probe_base
    base_shift_correction: false
    source_timeout: 1.0
    stop_pub_timeout: 10.0
    transform_tolerance: 0.1
    polygons: [Stop]
    Stop:
      type: polygon
      points: "[[0.3, 0.3], [0.3, -0.3], [-0.3, -0.3], [-0.3, 0.3]]"
      action_type: stop
      min_points: 1
      visualize: false
      enabled: true
    observation_sources: [scan]
    scan:
      type: scan
      topic: {prefix}/scan
      enabled: true
''')

    try:
        # Launch independent Collision Monitor processes for all 8 modes
        for mode in modes:
            log = (trial_dir / f'{mode}_cm.log').open('w')
            logs.append(log)
            upstream = prefix + ('/command' if mode == 'native' else f'/{mode}/in')
            cmd = [
                '/opt/ros/jazzy/lib/nav2_collision_monitor/collision_monitor',
                '--ros-args',
                '--params-file', str(cfg),
                '-r', f'__ns:={prefix}',
                '-r', f'__node:={mode}_cm',
                '-r', f'/clock:={prefix}/clock',
                '-p', f'cmd_vel_in_topic:={upstream}',
                '-p', f'cmd_vel_out_topic:={prefix}/{mode}/out'
            ]
            procs.append(subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT))

        # Launch native velocity smoother for stock_watchdog
        smoother_log = (trial_dir / 'stock_smoother.log').open('w')
        logs.append(smoother_log)
        smoother_cmd = [
            '/opt/ros/jazzy/lib/nav2_velocity_smoother/velocity_smoother',
            '--ros-args',
            '--params-file', str(cfg),
            '-r', f'__ns:={prefix}',
            '-r', '__node:=stock_smoother',
            '-r', f'/clock:={prefix}/clock',
            '-r', f'cmd_vel:={prefix}/command',
            '-r', f'cmd_vel_smoothed:={prefix}/stock_watchdog/in'
        ]
        procs.append(subprocess.Popen(smoother_cmd, stdout=smoother_log, stderr=subprocess.STDOUT))

        # Launch ISOLATED process for each custom guard configuration
        for mode in modes:
            if mode in ('native', 'stock_watchdog'):
                continue
            guard_log = (trial_dir / f'{mode}_filter.log').open('w')
            logs.append(guard_log)
            guard_cmd = [
                sys.executable, str(ROOT / 'research/freshness_contracts/guard_node.py'),
                '--prefix', prefix,
                '--mode', mode,
                '--guards'
            ] + MODE_GUARDS[mode]
            procs.append(subprocess.Popen(guard_cmd, stdout=guard_log, stderr=subprocess.STDOUT))

        # Wait for lifecycle service readiness
        deadline = time.monotonic() + 20.0
        for client in driver.lifecycle_clients.values():
            while not client.service_is_ready():
                if time.monotonic() > deadline:
                    raise RuntimeError('Lifecycle discovery timed out')
                driver.publish_clock(100.0)
                pump(executor, 0.05)

        # Transition lifecycle nodes to active
        for transition in (Transition.TRANSITION_CONFIGURE, Transition.TRANSITION_ACTIVATE):
            futures = []
            for client in driver.lifecycle_clients.values():
                req = ChangeState.Request()
                req.transition.id = transition
                futures.append(client.call_async(req))
            deadline = time.monotonic() + 15.0
            while not all(f.done() for f in futures):
                if time.monotonic() > deadline:
                    raise RuntimeError('Lifecycle transition timed out')
                driver.publish_clock(100.0)
                pump(executor, 0.02)
            if not all(f.result().success for f in futures):
                raise RuntimeError('Lifecycle transition failed')

        # Wait for active subscriber connections
        deadline = time.monotonic() + 20.0
        while (driver.cmd_pub.get_subscription_count() < 8 or
               driver.scan_pub.get_subscription_count() < 8 or
               driver.clock_pub.get_subscription_count() < 10):
            if time.monotonic() > deadline:
                raise RuntimeError('Subscription discovery timed out')
            driver.publish_clock(100.0)
            pump(executor, 0.05)

        # Preflight delivery check: verify zero command propagation across all chains
        deadline = time.monotonic() + 20.0
        while driver.preflight_seen != set(modes):
            if time.monotonic() > deadline:
                raise RuntimeError('Preflight zero delivery failed')
            driver.publish_clock(100.0)
            driver.publish_cmd(0.0, 0.0)
            pump(executor, 0.05)

        # Warmup pacing before trial start
        for _ in range(10):
            driver.publish_clock(100.0)
            pump(executor, 0.02)

        driver.start_wall = time.monotonic()
        last_scan_wall = -1.0
        last_cmd_wall = -1.0
        last_clock_wall = -1.0

        last_scan_stamp = None
        frozen_stamp = None
        frozen_clock = None
        scan_index = 0
        fault_logged = False
        while True:
            elapsed = time.monotonic() - driver.start_wall
            if elapsed >= DURATION:
                break
            faulty = elapsed >= spec.fault_onset
            if faulty and not fault_logged:
                driver.events.append({'event': 'scheduled_transition', 'wall_elapsed': elapsed})
                fault_logged = True
                frozen_stamp = last_scan_stamp
                frozen_clock = driver.sim_time
            recovering = spec.recovery_onset is not None and elapsed >= spec.recovery_onset
            sim = 100.0 + elapsed
            if scenario_name in ('clock_backward_jump', 'clock_epoch_recovery') and faulty:
                sim = 10.0 + elapsed - spec.fault_onset
            if scenario_name in ('clock_loss', 'clock_stall') and faulty:
                sim = frozen_clock
            if elapsed - last_clock_wall >= .01:
                if not (scenario_name == 'clock_loss' and faulty):
                    driver.publish_clock(sim)
                last_clock_wall = elapsed
            if elapsed - last_scan_wall >= .10:
                publish_scan = scenario_name != 'obs_noscan_startup'
                if faulty and scenario_name in ('obs_loss', 'clock_backward_jump', 'clock_loss', 'clock_stall'):
                    publish_scan = False
                if faulty and not recovering and scenario_name in ('obs_recovery', 'clock_epoch_recovery'):
                    publish_scan = False
                # Anchor stamps to the last actually published clock, not a future local calculation.
                stamp_val = driver.sim_time
                if scenario_name == 'benign_stamp_lag':
                    stamp_val -= .05
                if faulty and scenario_name == 'chrono_small_future_skew':
                    stamp_val += .05
                elif faulty and scenario_name == 'chrono_large_future_skew':
                    stamp_val += 10.
                elif faulty and scenario_name == 'chrono_duplicate_stamps':
                    stamp_val = frozen_stamp
                elif faulty and scenario_name == 'chrono_reordered_stamps':
                    stamp_val -= .20 if scan_index % 2 == 0 else 0.
                if publish_scan:
                    driver.publish_scan(stamp_val)
                    last_scan_stamp = stamp_val
                scan_index += 1
                last_scan_wall = elapsed
            if elapsed - last_cmd_wall >= .05:
                publish_cmd = not (faulty and scenario_name == 'cmd_loss')
                if faulty and not recovering and scenario_name == 'cmd_recovery':
                    publish_cmd = False
                # The repeated-command control intentionally has identical observable
                # input to a legitimate constant command: Twist has no generation stamp.
                if publish_cmd:
                    driver.publish_cmd(.22, .10)
                last_cmd_wall = elapsed
            executor.spin_once(timeout_sec=.002)
        # Record observation horizon before cleanup. Extra callbacks are not evidence.
        horizon = DURATION

        # Warmup validation: each chain must exhibit commanded motion before fault onset
        if scenario_name != 'obs_noscan_startup':
            for mode, records in driver.records.items():
                if not any(0.3 <= r['wall_elapsed'] < 1.0 and abs(r['vx'] - 0.22) < 1e-4 for r in records):
                    (trial_dir / 'invalid_trace.json').write_text(json.dumps(driver.records, indent=2))
                    raise RuntimeError(f'Warmup failed for {mode}; trial is invalid')

        # Triggers are derived from actual logged publications, not the schedule.
        summary = {mode: evaluate(records, driver.events, scenario_name, horizon)
                   for mode, records in driver.records.items()}

        trial_data = {
            'case': scenario_name,
            'obligation': spec.obligation,
            'repeat': repeat,
            'cpu_load': False,
            'horizon_s': horizon,
            'trial_start_monotonic': driver.start_wall,
            'summary': summary,
            'records': driver.records,
            'input_events': driver.events
        }
        (trial_dir / 'trace.json').write_text(json.dumps(trial_data, indent=2))
        print(f'[{spec.obligation}] {scenario_name} r{repeat:02d} -> ' +
              ' '.join(f'{m}:{s["contract_pass"]}' for m, s in summary.items()), flush=True)

        return {k: v for k, v in trial_data.items() if k not in ('records', 'input_events')}

    finally:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        for log in logs:
            log.close()
        executor.shutdown()
        driver.destroy_node()

def source_hashes():
    names = ['probe.py', 'guards.py', 'guard_node.py', 'contracts.py', 'oracle.py', 'taxonomy.py', 'PROTOCOL.md']
    return {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in names}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--cases', nargs='+', choices=list(TAXONOMY), default=list(TAXONOMY))
    parser.add_argument('--seed', type=int, default=20260919)
    args = parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID') != '143':
        raise RuntimeError('Requires isolated ROS_DOMAIN_ID=143')
    if args.repeats < 1 or len(args.cases) != len(set(args.cases)):
        raise ValueError('Positive repetitions and distinct scenarios required')
    args.out.mkdir(parents=True, exist_ok=False)
    hashes = source_hashes()
    snapshot = args.out/'source'
    snapshot.mkdir()
    for name in hashes:
        (snapshot/name).write_bytes((Path(__file__).parent/name).read_bytes())
    schedule = [(case, rep) for rep in range(args.repeats) for case in args.cases]
    random.Random(args.seed).shuffle(schedule)
    metadata = {
        'version': 5, 'ros_domain_id': 143, 'ablation_modes': ABLATION_MODES,
        'mode_guards': MODE_GUARDS, 'source_hashes': hashes, 'seed': args.seed,
        'schedule': schedule, 'repeats': args.repeats, 'cases': args.cases,
        'platform': platform.platform(), 'cpu_count': os.cpu_count(),
        'packages': subprocess.check_output(['dpkg-query', '-W', 'ros-jazzy-nav2-collision-monitor',
                    'ros-jazzy-nav2-velocity-smoother'], text=True).strip(),
        'scope': 'Finite-trace endpoint contracts, nominal host conditions, no robot base',
        'complete': False, 'results': [],
    }
    rclpy.init()
    try:
        for case, rep in schedule:
            # Failed setups are retained; no automatic deletion or replacement.
            res = run_trial(case, rep, args.out)
            metadata['results'].append(res)
            (args.out/'results.json').write_text(json.dumps(metadata, indent=2))
        if hashes != source_hashes():
            raise RuntimeError('Experimental source changed during campaign')
        metadata['complete'] = True
    finally:
        (args.out/'results.json').write_text(json.dumps(metadata, indent=2))
        rclpy.shutdown()

if __name__ == '__main__':
    main()
