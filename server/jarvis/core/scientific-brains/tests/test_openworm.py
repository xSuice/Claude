"""Small unit tests; not a neuroscientific or Claude quality evaluation."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('worm', ROOT / 'openworm_connectome.py')
worm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worm)

class WormTests(unittest.TestCase):
    def test_published_excerpt_loads(self):
        edges, digest = worm.load_connectome(ROOT / 'samples' / 'openworm_verified_excerpt.csv')
        self.assertEqual(len(edges), 15)
        self.assertEqual(len(digest), 64)
        self.assertIn(('I1L', 'I2L', 10, 'chemical'), edges)

    def test_profile(self):
        edges, digest = worm.load_connectome(ROOT / 'samples' / 'openworm_verified_excerpt.csv')
        info = worm.profile(edges, digest)
        self.assertEqual(info['edges'], 15)
        self.assertGreater(info['nodes'], 7)

    def test_diffusion_is_bounded(self):
        edges, _ = worm.load_connectome(ROOT / 'samples' / 'openworm_verified_excerpt.csv')
        data = worm.probe(edges, 'I1L', 3)
        self.assertTrue(data['top_reached'])
        self.assertLessEqual(sum(item['graph_signal'] for item in data['top_reached']), 1.0)

    def test_no_fake_neurons(self):
        edges, _ = worm.load_connectome(ROOT / 'samples' / 'openworm_verified_excerpt.csv')
        with self.assertRaises(ValueError):
            worm.probe(edges, 'CLAUDE_NEURON', 2)

    def test_invalid_csv_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.csv'
            path.write_text('Source,Target,Weight,Type\nA,B,NOT_NUMBER,chemical\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                worm.load_connectome(path)

if __name__ == '__main__':
    unittest.main()
