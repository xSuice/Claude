"""Shared fakes for the V16 tests: a scripted stand-in for the Claude CLI (same JSON result shape)."""
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain_core import Brain  # noqa: E402
from capabilities import Registry  # noqa: E402
from ledger import Ledger  # noqa: E402
from learning import Learning  # noqa: E402
from taskengine import Engine  # noqa: E402
from workers import ClaudeWorker  # noqa: E402

STEP_RE = re.compile(r'Du bearbeitest Schritt (\d+) von (\d+): (.+)')


def result(text='ok', new=1000, cache=5000, usd=0.01, is_error=False, structured=None):
    d = {'type': 'result', 'subtype': 'success' if not is_error else 'error_during_execution', 'is_error': is_error,
         'result': text, 'num_turns': 2, 'duration_ms': 10, 'total_cost_usd': usd,
         'usage': {'input_tokens': new // 2, 'cache_creation_input_tokens': new // 4, 'cache_read_input_tokens': cache,
                   'output_tokens': new - new // 2 - new // 4}}
    if structured is not None:
        d['structured_output'] = structured
    return json.dumps(d)


class FakeClaude:
    """plan: dict or callable(prompt)->dict|str ; steps: {title: callable(cwd: Path, prompt: str, call_no: int) -> str|None}"""

    def __init__(self, plan=None, steps=None, plan_cost=0.02, step_cost=0.05):
        self.plan, self.steps = plan, steps or {}
        self.calls = []
        self.plan_cost, self.step_cost = plan_cost, step_cost
        self.step_calls = {}

    def __call__(self, args, prompt, cwd, timeout):
        model = args[args.index('--model') + 1]
        tools = args[args.index('--tools') + 1]
        planning = tools == ''
        self.calls.append({'model': model, 'planning': planning, 'tools': tools, 'cwd': str(cwd), 'prompt': prompt})
        if planning:
            p = self.plan(prompt) if callable(self.plan) else self.plan
            text = p if isinstance(p, str) else json.dumps(p)
            return 0, result(text, new=3000, usd=self.plan_cost if model != 'haiku' else self.plan_cost / 3), ''
        m = STEP_RE.search(prompt)
        title = m.group(3).strip() if m else ''
        n = self.step_calls[title] = self.step_calls.get(title, 0) + 1
        fn = self.steps.get(title)
        if fn is None:
            return 0, result('nichts zu tun'), ''
        txt = fn(Path(cwd), prompt, n)
        if txt == 'ERROR':
            return 1, result('Fehler', is_error=True), 'boom'
        return 0, result(txt or 'Dateien geschrieben', new=8000, usd=self.step_cost), ''

    @property
    def planning_calls(self):
        return sum(1 for c in self.calls if c['planning'])


def make_app(tmp: Path, fake: FakeClaude, *, identity='person-a', system_db=None, limits=None, job_defaults=None,
             plan_probe=None, pressure=lambda: {}, caps=('python.run', 'python.unittest', 'python.compile'), registry=None,
             tools_dir=None, clock=None, cfg_extra=None):
    state = tmp / f'state-{identity}'
    cfg = {'identity': identity, 'project': 'jarvis', 'state_dir': str(state), 'results_dir': str(tmp / f'results-{identity}'),
           'system_db': str(system_db or tmp / 'system.db'), 'job_defaults': job_defaults or {}, 'lease_s': 30,
           'resources': {'max_bridge_jobs': 5}, **(cfg_extra or {})}
    state.mkdir(parents=True, exist_ok=True)
    brain = Brain(state / 'brain.db', identity, {'jarvis'})
    ledger = Ledger(Path(cfg['system_db']), limits or {'plan_guard': {'five_hour_max_pct': 70, 'week_max_pct': 85}}, plan_probe=plan_probe)
    reg = registry or Registry(Path(cfg['system_db']), 'server', tools_dir, hide=[str(state)])
    if registry is None and caps:
        reg.discover(selftest=True, only=set(caps))
    claude = ClaudeWorker('/nonexistent/claude', exec_fn=fake)
    learning = Learning(brain, 'jarvis')
    kw = {'clock': clock} if clock else {}
    eng = Engine(brain=brain, project='jarvis', registry=reg, ledger=ledger, claude=claude, learning=learning, cfg=cfg,
                 router=None, pressure=pressure, **kw)
    return eng


def run_until(eng, states=('done', 'partial', 'failed', 'cancelled', 'waiting_approval', 'waiting_pc'), job=None, rounds=40):
    for _ in range(rounds):
        eng.tick(max_seconds=5)
        if job and eng.status(job)['state'] in states:
            return eng.status(job)
    return eng.status(job) if job else None


WC_PLAN = {
    'goal': 'Ein Python-Kommandozeilenwerkzeug, das Wörter zählt, mit Tests',
    'task_type': 'coding.python_cli', 'match_keywords': ['python', 'wörter', 'zählt', 'kommandozeile', 'tests'],
    'deliverables': [
        {'path': 'wc.py', 'description': 'Werkzeug', 'checks': [{'type': 'python_compiles'}, {'type': 'no_placeholders'},
                                                                {'type': 'capability', 'capability': 'python.unittest', 'args': {}}]},
        {'path': 'README.md', 'description': 'Anleitung', 'checks': [{'type': 'words_min', 'value': 5}, {'type': 'contains', 'value': 'wc.py'}]}],
    'steps': [
        {'id': 's1', 'title': 'Code und Tests schreiben', 'kind': 'claude', 'instructions': 'Schreibe wc.py und test_wc.py ...',
         'outputs': ['wc.py', 'test_wc.py'], 'deps': []},
        {'id': 's2', 'title': 'Tests ausführen', 'kind': 'local', 'capability': 'python.unittest', 'args': {}, 'deps': ['s1']},
        {'id': 's3', 'title': 'README schreiben', 'kind': 'claude', 'instructions': 'Schreibe README.md mit Aufruf ...',
         'outputs': ['README.md'], 'deps': ['s2']}]}
WC_GOOD = 'import sys\n\ndef count(text):\n    return len(text.split())\n\nif __name__ == "__main__":\n    print(count(sys.stdin.read()))\n'
WC_BAD = 'import sys\n\ndef count(text):\n    return len(text)\n'
WC_TEST = ('import unittest\nfrom wc import count\n\nclass T(unittest.TestCase):\n    def test_count(self):\n'
           '        self.assertEqual(count("a b  c"), 3)\n')


def wc_steps(bad_first=False):
    def code(cwd, prompt, n):
        (cwd / 'wc.py').write_text(WC_BAD if bad_first and n == 1 else WC_GOOD)
        (cwd / 'test_wc.py').write_text(WC_TEST)
        return 'wc.py und test_wc.py geschrieben'

    def readme(cwd, prompt, n):
        (cwd / 'README.md').write_text('# Wortzähler\n\nAufruf: python3 wc.py < datei.txt gibt die Anzahl der Wörter aus.\n')
        return 'README.md geschrieben'
    return {'Code und Tests schreiben': code, 'README schreiben': readme}


def tmpdir(test):
    t = tempfile.TemporaryDirectory()
    test.addCleanup(t.cleanup)
    return Path(t.name)
