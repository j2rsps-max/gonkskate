"""Regress v0.7.0's successful exit after a native physics stop."""
import unittest
import tempfile
from pathlib import Path
from playable_results import failure_message, session_files


class HealthTests(unittest.TestCase):
    def test_closed_failed_window_is_failure(self):
        self.assertIn('frame 569', failure_message('ERROR: Native process stopped at frame 569. See session logs.'))

    def test_recovery_does_not_erase_failure(self):
        self.assertIn('stopped', failure_message('', {'failed': True, 'recoveries': 2,
                      'failures': [{'message': 'Native process stopped at frame 20'}]}))

    def test_clean_session_and_benign_stderr_pass(self):
        self.assertIsNone(failure_message('Updating crates.io index\n', {'failed': False}))

    def test_only_this_sessions_declared_segments_are_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['playable-own-segment0.csv', 'playable-own-segment1.csv',
                         'playable-own-segment1.csv.adapters.log', 'playable-unrelated.csv']:
                (root / name).touch()
            text = ''.join('Session trace: '+str(root/name)+'\n' for name in ['playable-own-segment0.csv','playable-own-segment1.csv'])
            files = session_files(text,root)
            self.assertEqual(len(files),3)
            self.assertNotIn(root/'playable-unrelated.csv',files)
            with self.assertRaises(ValueError):
                session_files('Session trace: '+str(root.parent/'playable-escape.csv'),root)


if __name__ == '__main__':
    unittest.main()
