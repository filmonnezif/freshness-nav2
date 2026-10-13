"""Predeclared v5 scenarios. No inferred or hardcoded minimality labels."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ScenarioSpec:
    label: str
    obligation: str
    description: str
    recovery_onset: Optional[float] = None
    fault_onset: float = 1.0

TAXONOMY = {
    'healthy': ScenarioSpec('Healthy', 'availability', 'Clock, fresh scans, and commands continue.'),
    'benign_stamp_lag': ScenarioSpec('Valid stamp lag (50 ms)', 'availability', 'Scans are stamped 50 ms behind the published clock.'),
    'repeated_command': ScenarioSpec('Repeated command control', 'availability', 'Constant un-stamped Twist payload continues to be republished.'),
    'cmd_loss': ScenarioSpec('Command loss', 'command', 'Command publication stops; scans and clock continue.'),
    'cmd_recovery': ScenarioSpec('Command loss + recovery', 'command', 'Commands stop at 1 s and resume at 2.3 s.', 2.3),
    'obs_noscan_startup': ScenarioSpec('No-scan startup', 'startup', 'No scan is ever published.', fault_onset=0.0),
    'obs_loss': ScenarioSpec('Scan loss', 'scan_age', 'Scan publication stops; commands and clock continue.'),
    'obs_recovery': ScenarioSpec('Scan loss + recovery', 'scan_age', 'Scans stop at 1 s and resume at 2.3 s.', 2.3),
    'chrono_small_future_skew': ScenarioSpec('Future stamp (+50 ms)', 'future', 'New scans are stamped 50 ms ahead of the published clock.'),
    'chrono_large_future_skew': ScenarioSpec('Future stamp (+10 s)', 'future', 'New scans are stamped 10 s ahead of the published clock.'),
    'chrono_duplicate_stamps': ScenarioSpec('Frozen scan stamp', 'order', 'Scans repeat the exact last pre-fault stamp.'),
    'chrono_reordered_stamps': ScenarioSpec('Reordered scan stamps', 'order', 'Alternate current and 200 ms backdated stamps.'),
    'clock_backward_jump': ScenarioSpec('Clock reset + scan loss', 'epoch', 'Clock jumps to about 10 s; scans cease.'),
    'clock_epoch_recovery': ScenarioSpec('Clock reset + recovery', 'epoch', 'Clock jumps to about 10 s; scans resume at 2.3 s.', 2.3),
    'clock_loss': ScenarioSpec('Clock delivery + scan loss', 'clock_receipt', 'Clock and scan publications stop; commands continue.'),
    'clock_stall': ScenarioSpec('Clock stall + scan loss', 'clock_progress', 'Clock repeats its last value; scans cease; commands continue.'),
}
ABLATION_MODES = ['native', 'stock_watchdog', 'periodic', 'g_cmd', 'g_future', 'g_order', 'g_epoch', 'guarded']
MODE_GUARDS = {
    'native': [], 'stock_watchdog': [], 'periodic': [],
    'g_cmd': ['cmd'], 'g_future': ['future'], 'g_order': ['order'],
    'g_epoch': ['epoch'], 'guarded': ['cmd', 'future', 'order', 'epoch', 'clock'],
}
MODE_LABELS = ['N', 'W', 'P', 'C', 'F', 'O', 'E', 'G']
TAU_CMD = 0.30
TAU_SCAN = 1.00
TAU_CLOCK = 0.30
EPSILON_SKEW = 0.02
DELTA_REVOKE = 0.15
DELTA_RECOVER = 0.30
DURATION = 3.20
