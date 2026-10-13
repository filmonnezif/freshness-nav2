"""Guard composition invariants; executable guard behavior is exercised by ROS trials."""
import unittest
from taxonomy import ABLATION_MODES, MODE_GUARDS, TAXONOMY

class ConfigurationTests(unittest.TestCase):
    def test_periodic_relay_has_no_optional_guards(self):
        self.assertEqual(MODE_GUARDS['periodic'], [])
    def test_individual_checks_are_single_interventions(self):
        for mode, guard in [('g_cmd','cmd'),('g_future','future'),('g_order','order'),('g_epoch','epoch')]:
            self.assertEqual(MODE_GUARDS[mode],[guard])
    def test_clock_claim_has_corresponding_scenarios(self):
        self.assertIn('clock',MODE_GUARDS['guarded'])
        self.assertIn('clock_loss',TAXONOMY);self.assertIn('clock_stall',TAXONOMY)
    def test_eight_distinct_configurations(self):
        self.assertEqual(len(set(ABLATION_MODES)),8)

if __name__ == '__main__': unittest.main()
