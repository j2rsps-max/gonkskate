"""Regress v0.7.0's successful exit after a native physics stop."""
import unittest
from playable_results import failure_message


class HealthTests(unittest.TestCase):
    def test_closed_failed_window_is_failure(self):
        self.assertIn('frame 569', failure_message('ERROR: Native process stopped at frame 569. See session logs.'))

    def test_recovery_does_not_erase_failure(self):
        self.assertIn('stopped', failure_message('', {'failed': True, 'recoveries': 2,
                      'failures': [{'message': 'Native process stopped at frame 20'}]}))

    def test_clean_session_and_benign_stderr_pass(self):
        self.assertIsNone(failure_message('Updating crates.io index\n', {'failed': False}))


if __name__ == '__main__':
    unittest.main()
