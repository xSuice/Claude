"""T10 check (held-out): python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check  # noqa: E402

HIDDEN = r'''
import random, sys, unittest
from collections import deque
sys.path.insert(0, ".")
from ringpuffer import RingPuffer

class H(unittest.TestCase):
    def test_kapazitaet(self):
        for bad in (0, -1, 1.5, "3", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    RingPuffer(bad)
        self.assertEqual(RingPuffer(4).kapazitaet, 4)
    def test_basis(self):
        p = RingPuffer(3)
        self.assertEqual((len(p), p.voll, list(p)), (0, False, []))
        p.extend([1, 2, 3, 4])
        self.assertEqual((len(p), p.voll, list(p), p[0], p[-1], p[-3]), (3, True, [2, 3, 4], 2, 4, 2))
    def test_index(self):
        p = RingPuffer(2); p.extend([5, 6])
        for i in (2, -3, 10):
            with self.assertRaises(IndexError):
                p[i]
        with self.assertRaises(TypeError):
            p[0:1]
    def test_entnehmen(self):
        p = RingPuffer(2)
        with self.assertRaises(IndexError):
            p.entnehmen()
        p.extend([1, 2, 3])
        self.assertEqual((p.entnehmen(), list(p)), (2, [3]))
    def test_repr_gleich(self):
        a, b = RingPuffer(3), RingPuffer(3)
        a.extend([1, 2, 3]); b.extend([0, 1, 2, 3])
        self.assertEqual(repr(a), "RingPuffer(kapazitaet=3, elemente=[1, 2, 3])")
        self.assertEqual(a, b)
        self.assertNotEqual(a, RingPuffer(4))
    def test_kapazitaet_eins(self):
        p = RingPuffer(1); p.extend(["a", "b"])
        self.assertEqual((list(p), p[-1], p.voll), (["b"], "b", True))
    def test_zufall(self):
        for seed in range(40):
            rnd = random.Random(seed); cap = rnd.randrange(1, 8)
            p, d = RingPuffer(cap), deque(maxlen=cap)
            for _ in range(300):
                op = rnd.choice(["append", "append", "extend", "entnehmen", "leeren", "get"])
                if op == "append":
                    x = rnd.randrange(100); p.append(x); d.append(x)
                elif op == "extend":
                    xs = [rnd.randrange(100) for _ in range(rnd.randrange(0, 5))]; p.extend(xs); d.extend(xs)
                elif op == "entnehmen":
                    if d: self.assertEqual(p.entnehmen(), d.popleft())
                    else:
                        with self.assertRaises(IndexError): p.entnehmen()
                elif op == "leeren":
                    p.leeren(); d.clear()
                else:
                    i = rnd.randrange(-cap - 1, cap + 1)
                    try: want = d[i]
                    except IndexError:
                        with self.assertRaises(IndexError): p[i]
                    else: self.assertEqual(p[i], want)
                self.assertEqual((list(p), len(p), p.voll), (list(d), len(d), len(d) == cap))

unittest.main(argv=["x"], verbosity=0)
'''


def main():
    c = Check('T10', sys.argv[1])
    for f in ('ringpuffer.py', 'test_ringpuffer.py', 'README.md'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('ringpuffer.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        (c.work / '_versteckt.py').write_text(HIDDEN, encoding='utf-8')
        code, out = c.run(['python3', '_versteckt.py'], timeout=180)
        for name in ('kapazitaet', 'basis', 'index', 'entnehmen', 'repr_gleich', 'kapazitaet_eins', 'zufall'):
            c.ok(f'verdeckt-{name}', code == 0 or f'test_{name}' not in out, out[-400:] if code else '')
        c.ok('verdeckt-gesamt', code == 0, out[-400:])
    c.ok('readme', c.file('README.md').is_file() and 'RingPuffer' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
