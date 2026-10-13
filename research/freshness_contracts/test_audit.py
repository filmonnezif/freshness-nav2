"""Independent input-audit checks at a real scheduler boundary."""
import unittest
from audit import validate_treatment
from taxonomy import ABLATION_MODES, DURATION

class InputAuditTests(unittest.TestCase):
    def trial(self):
        return {'case':'cmd_recovery','cpu_load':False,'horizon_s':DURATION,
                'input_events':[
                    {'event':'clock','wall_elapsed':.4,'value':100.4},
                    {'event':'scan','wall_elapsed':.41,'stamp':100.4},
                    {'event':'command','wall_elapsed':.42,'vx':.22,'wz':.1},
                    {'event':'command','wall_elapsed':1.000078,'vx':.22,'wz':.1},
                    {'event':'scheduled_transition','wall_elapsed':1.000734},
                    {'event':'command','wall_elapsed':2.32,'vx':.22,'wz':.1}],
                'records':{m:[{'wall_elapsed':.5,'vx':.22,'wz':.1}] for m in ABLATION_MODES}}
    def test_pre_transition_publication_can_finish_after_nominal_schedule(self):
        validate_treatment(self.trial())
    def test_command_after_actual_stop_transition_is_rejected(self):
        t=self.trial();t['input_events'].insert(-1,{'event':'command','wall_elapsed':1.01,'vx':.22,'wz':.1})
        with self.assertRaises(AssertionError):validate_treatment(t)

if __name__=='__main__':unittest.main()
