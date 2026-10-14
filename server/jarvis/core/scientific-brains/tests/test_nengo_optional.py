import importlib.util
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nengoprobe', ROOT / 'nengo_action_selection.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NengoTests(unittest.TestCase):
    def test_bad_utility_rejected_before_optional_import(self):
        with self.assertRaises(ValueError):
            module.pick_with_nengo({'memory': 1.5, 'tool': 0.2, 'claude': 0.3})

    def test_missing_utility_rejected(self):
        with self.assertRaises(ValueError):
            module.pick_with_nengo({'memory': 0.5, 'tool': 0.4})

if __name__ == '__main__':
    unittest.main()
