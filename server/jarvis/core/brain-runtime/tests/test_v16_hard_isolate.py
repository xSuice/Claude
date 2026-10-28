"""HARD ISOLATE: Egress-Block via root-Helper, fail-soft, mit Markern und einmaliger Fehlermeldung."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, make_app, tmpdir
import sandbox

STUB = r'''
import sys, pathlib
pathlib.Path(sys.argv[1]).write_text(" ".join(sys.argv[2:]))
'''

@unittest.skipUnless(sys.platform == 'linux' and sandbox.available(), 'Linux sandbox required')
class HardIsolateEgress(unittest.TestCase):
    def make(self):
        eng = make_app(tmpdir(self), FakeClaude({'goal':'g','task_type':'t','match_keywords':['x'],
            'deliverables':[],'steps':[]}, {}))
        stub = Path(eng.brain.db_path.parent) / 'stub.py'
        stub.write_text(STUB)
        self.log = Path(eng.brain.db_path.parent) / 'helper.log'
        eng.hard_isolate_cmd = lambda mode: [sys.executable, str(stub), str(self.log), mode]
        return eng

    def test_hard_engages_helper_and_marks(self):
        eng = self.make()
        (eng.brain.db_path.parent / 'KILL').write_text('hard')
        eng.tick(max_seconds=0)
        self.assertEqual(self.log.read_text(), 'on')            # Helper mit 'on' aufgerufen
        self.assertTrue((eng.brain.db_path.parent / 'HARD_ISOLATED').exists())

    def test_disengage_removes_marker_and_calls_off(self):
        eng = self.make()
        d = eng.brain.db_path.parent
        (d / 'KILL').write_text('hard')
        eng.tick(max_seconds=0)
        self.assertTrue((d / 'HARD_ISOLATED').exists())
        (d / 'KILL').unlink()
        eng.tick(max_seconds=0)
        self.assertFalse((d / 'HARD_ISOLATED').exists())
        self.assertEqual(self.log.read_text(), 'off')

    def test_helper_failure_is_fail_soft_and_reported_once(self):
        eng = self.make()
        d = eng.brain.db_path.parent
        failing = d / 'fail.py'
        failing.write_text('import sys; sys.exit(1)')
        eng.hard_isolate_cmd = lambda mode: [sys.executable, str(failing)]
        (d / 'KILL').write_text('hard')
        eng.tick(max_seconds=0)                                  # kein Crash
        self.assertFalse((d / 'HARD_ISOLATED').exists())
        eng.tick(max_seconds=0)
        # Fehler nur einmal gemeldet bis es klappt
        with eng._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM job_events WHERE kind='hard_isolate_failed'").fetchone()[0]
        self.assertEqual(n, 1)

if __name__ == '__main__':
    unittest.main()
