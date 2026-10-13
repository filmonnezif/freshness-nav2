import unittest
from contracts import holds, is_zero, evaluate_trace, derive_obligation


def out(t, v=.22, w=.1):
    return {'wall_elapsed': t, 'vx': v, 'wz': w}


def event(kind, t, **kw):
    return {'event': kind, 'wall_elapsed': t, **kw}


def command_events(recovery=False):
    es=[event('command', i/20, vx=.22, wz=.1) for i in range(20)]
    if recovery:
        es += [event('command', 2.3+i/20, vx=.22, wz=.1) for i in range(18)]
    return es


class MonitorTests(unittest.TestCase):
    def test_late_stop_rejected_before_old_late_window(self):
        records=[out(.5),out(1.1),out(2,0,0),out(2.3,0,0)]
        r=evaluate_trace(records,command_events(),'cmd_loss',3.2)
        self.assertFalse(r['contract_pass'])
        self.assertAlmostEqual(r['trigger_s'],1.25)
        self.assertAlmostEqual(r['revoke_latency_s'],.75)

    def test_extending_horizon_cannot_relax_deadline(self):
        records=[out(.5),out(2,0,0)]
        for horizon in [2.5,3.2,10.]:
            self.assertFalse(evaluate_trace(records,command_events(),'cmd_loss',horizon)['contract_pass'])

    def test_stop_by_deadline_and_silence_pass(self):
        self.assertTrue(evaluate_trace([out(.5),out(1.39,0,0)],command_events(),'cmd_loss',3.2)['contract_pass'])

    def test_silence_after_nonzero_fails(self):
        self.assertFalse(evaluate_trace([out(.5)],command_events(),'cmd_loss',3.2)['contract_pass'])

    def test_angular_motion_fails(self):
        self.assertFalse(evaluate_trace([out(.5),out(1.3,0,.1)],command_events(),'cmd_loss',3.2)['contract_pass'])

    def test_transient_zero_then_motion_fails(self):
        self.assertFalse(evaluate_trace([out(.5),out(1.3,0,0),out(1.5)],command_events(),'cmd_loss',3.2)['contract_pass'])

    def test_held_nonzero_at_interval_boundary_fails(self):
        self.assertFalse(holds([out(.5),out(1.41,0,0)],1.4,3.2,is_zero))

    def test_no_output_is_not_stop(self):
        self.assertFalse(evaluate_trace([],command_events(),'cmd_loss',3.2)['contract_pass'])

    def test_recovery_without_stop_fails(self):
        records=[out(i/20) for i in range(64)]
        r=evaluate_trace(records,command_events(True),'cmd_recovery',3.2)
        self.assertTrue(r['availability_pass']);self.assertFalse(r['stop_pass']);self.assertFalse(r['contract_pass'])

    def test_stop_then_recovery_passes(self):
        records=[out(.5),out(1.35,0,0)]+[out(2.4+i/20) for i in range(16)]
        r=evaluate_trace(records,command_events(True),'cmd_recovery',3.2)
        self.assertTrue(r['contract_pass']);self.assertAlmostEqual(r['recovery_latency_s'],.1)

    def test_recovery_requires_continued_delivery(self):
        records=[out(.5),out(1.35,0,0),out(2.4)]
        self.assertFalse(evaluate_trace(records,command_events(True),'cmd_recovery',3.2)['contract_pass'])

    def test_healthy_requires_continued_delivery(self):
        self.assertFalse(evaluate_trace([out(.5)],[],'healthy',3.2)['contract_pass'])
        self.assertTrue(evaluate_trace([out(i/20) for i in range(64)],[],'healthy',3.2)['contract_pass'])

    def test_missing_trigger_rejects_trial(self):
        with self.assertRaises(ValueError):
            evaluate_trace([out(.5)],[],'chrono_large_future_skew',3.2)

    def test_missing_recovery_rejects_trial(self):
        with self.assertRaises(ValueError):
            evaluate_trace([out(.5)],command_events(),'cmd_recovery',3.2)

    def test_horizon_too_short_rejects_trial(self):
        with self.assertRaises(ValueError):
            evaluate_trace([out(.5)],command_events(),'cmd_loss',1.35)

    def test_nonmonotonic_observer_trace_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_trace([out(1),out(.5)],command_events(),'cmd_loss',3.2)

    def test_nan_is_not_zero(self):
        self.assertFalse(is_zero(out(.5,float('nan'),0)))


class TriggerTests(unittest.TestCase):
    def trigger(self,case,es):
        return derive_obligation(case,es,3.2)['trigger_s']

    def test_future_uses_actual_event_time_and_tolerance(self):
        es=[event('clock',.8,value=100.8),event('scan',.81,stamp=100.81),event('scan',1.04,stamp=101.)]
        self.assertEqual(self.trigger('chrono_small_future_skew',es),1.04)

    def test_scan_age_from_clock_signal(self):
        es=[event('clock',.9,value=100.9),event('scan',.91,stamp=100.9),event('clock',1.9,value=101.9),event('clock',1.92,value=101.92)]
        self.assertEqual(self.trigger('obs_loss',es),1.92)

    def test_epoch_jump_does_not_jump_observer_time(self):
        es=[event('clock',.9,value=100.9),event('clock',1.02,value=10.02)]
        self.assertEqual(self.trigger('clock_backward_jump',es),1.02)

    def test_duplicate_and_reordered_trigger(self):
        for stamp in [100.9,100.8]:
            es=[event('scan',.9,stamp=100.9),event('scan',1.01,stamp=stamp)]
            self.assertEqual(self.trigger('chrono_duplicate_stamps',es),1.01)

    def test_clock_stall_differs_from_clock_receipt(self):
        es=[event('clock',i/100,value=min(i/100,.9)+100) for i in range(320)]
        self.assertAlmostEqual(self.trigger('clock_stall',es),1.2)
        with self.assertRaises(ValueError):self.trigger('clock_loss',es)

    def test_startup_trigger_is_first_command(self):
        self.assertEqual(self.trigger('obs_noscan_startup',[event('command',.03,vx=.22,wz=.1)]),.03)

if __name__ == '__main__': unittest.main()
