"""V16 independent acceptance: deterministic checks of real result files.

A deliverable counts as done only when every one of its checks passes here - never because a
model said so. Checks that need a parser for untrusted formats (images, DOCX, XLSX, PDF, ZIP/JAR)
run the inspector inside the sandbox; if the sandbox or inspector is unavailable they fail closed.
`capability` checks run a registered capability (e.g. unit tests) in the sandbox and need exit 0.
Optional model reviews are recorded elsewhere as opinions and never replace these checks.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from capabilities import CapError, check_rel, MAGIC

PLACEHOLDER = re.compile(r'(?i)\b(?:lorem ipsum|platzhalter|placeholder|insert (?:here|text)|hier einfügen)\b'
                         r'|\b(?:todo|fixme|tbd)\s*:|#\s*(?:todo|fixme)\b|\bxxx+\b|\bNotImplementedError\b|^\s*\.\.\.\s*$', re.M)
CHECK_TYPES = {
    'exists': (), 'min_bytes': ('value',), 'max_bytes': ('value',), 'contains': ('value',), 'not_contains': ('value',),
    'regex': ('value',), 'json_valid': (), 'json_keys': ('value',), 'python_compiles': (), 'magic': ('value',),
    'words_min': ('value',), 'lines_min': ('value',), 'no_placeholders': (), 'image_min': ('width', 'height'),
    'docx_min_words': ('value',), 'pdf_min_pages': ('value',), 'xlsx_sheets_min': ('value',), 'zip_contains': ('value',),
    'pptx_min_slides': ('value',), 'capability': ('capability',),
}
INSPECT = {'image_min', 'docx_min_words', 'pdf_min_pages', 'xlsx_sheets_min', 'pptx_min_slides'}
INSPECTOR = Path(__file__).resolve().with_name('inspect_file.py')


def validate_checks(checks, where='deliverable') -> list[dict]:
    """Schema check for planner-written checks (unknown types/keys refused)."""
    if not isinstance(checks, list) or not 1 <= len(checks) <= 12:
        raise ValueError(f'{where}: 1..12 checks required')
    out = []
    for c in checks:
        if not isinstance(c, dict) or c.get('type') not in CHECK_TYPES:
            raise ValueError(f'{where}: unknown check {c!r:.80}')
        allowed = {'type', 'args', *CHECK_TYPES[c['type']]}
        if set(c) - allowed:
            raise ValueError(f'{where}: check {c["type"]} has unknown keys {sorted(set(c) - allowed)}')
        for k in CHECK_TYPES[c['type']]:
            if k not in c:
                raise ValueError(f'{where}: check {c["type"]} needs {k}')
        t = c['type']
        if t in ('min_bytes', 'max_bytes', 'words_min', 'lines_min', 'docx_min_words', 'pdf_min_pages', 'xlsx_sheets_min',
                 'pptx_min_slides') and (type(c['value']) is not int or c['value'] < 0):
            raise ValueError(f'{where}: {t} needs an integer')
        if t == 'image_min' and not all(type(c[k]) is int and c[k] > 0 for k in ('width', 'height')):
            raise ValueError(f'{where}: image_min needs width/height')
        if t in ('contains', 'not_contains', 'regex') and (not isinstance(c['value'], str) or not 1 <= len(c['value']) <= 200):
            raise ValueError(f'{where}: {t} needs a string')
        if t == 'regex':
            try:
                re.compile(c['value'])
            except re.error as e:
                raise ValueError(f'{where}: bad regex: {e}') from e
        if t in ('json_keys', 'zip_contains') and (not isinstance(c['value'], list) or not all(isinstance(x, str) for x in c['value'])):
            raise ValueError(f'{where}: {t} needs a list of strings')
        if t == 'magic' and c['value'] not in MAGIC:
            raise ValueError(f'{where}: magic must be one of {sorted(MAGIC)}')
        if t == 'capability' and (not isinstance(c['capability'], str) or not isinstance(c.get('args', {}), dict)):
            raise ValueError(f'{where}: capability check needs a name and args object')
        out.append(c)
    return out


class Acceptance:
    def __init__(self, registry):
        self.reg = registry

    def _inspect(self, work: Path, rel: str) -> dict:
        if not self.reg.usable('python.run'):
            return {'ok': False, 'error': 'inspector unavailable (python.run not tested): fail closed'}
        tools = work / '.jarvis-tools'
        tools.mkdir(parents=True, exist_ok=True)
        shutil.copy2(INSPECTOR, tools / 'inspect_file.py')
        out = tools / 'inspect-out.json'
        out.unlink(missing_ok=True)
        r = self.reg.execute('python.run', {'script': '.jarvis-tools/inspect_file.py',
                                            'args': ['--out', '.jarvis-tools/inspect-out.json', rel]}, work)
        if not r['ok'] or not out.is_file():
            return {'ok': False, 'error': f'inspector failed: {r["tail"][-200:]}'}
        try:
            return json.loads(out.read_text(encoding='utf-8').splitlines()[0])
        except (ValueError, IndexError):
            return {'ok': False, 'error': 'inspector output unreadable'}

    def check_one(self, work: Path, rel: str, c: dict) -> tuple[bool, str]:
        t = c['type']
        if t == 'capability':
            try:
                r = self.reg.execute(c['capability'], c.get('args') or {}, work)
            except CapError as e:
                return False, f'capability {c["capability"]}: {e}'
            self.reg.record_use(c['capability'], r['ok'])
            return r['ok'], f'{c["capability"]} exit {r["exit"]}: {r["tail"][-300:]}'
        try:
            full = Path(check_rel(work, rel, kind='any'))
        except CapError as e:
            return False, str(e)
        if t == 'exists':
            return True, 'exists'
        if full.is_dir():
            return False, f'{rel} is a directory'
        size = full.stat().st_size
        if t == 'min_bytes':
            return size >= c['value'], f'{size} bytes (min {c["value"]})'
        if t == 'max_bytes':
            return size <= c['value'], f'{size} bytes (max {c["value"]})'
        if t == 'magic':
            return full.read_bytes()[:8].startswith(MAGIC[c['value']]), f'magic {c["value"]}'
        if t == 'zip_contains':
            import zipfile
            try:
                with zipfile.ZipFile(full) as z:
                    names = set(z.namelist())
            except (zipfile.BadZipFile, OSError) as e:
                return False, f'not a valid zip/jar: {e}'
            missing = [n for n in c['value'] if not any(x == n or x.endswith('/' + n) or (n.endswith('/') and x.startswith(n)) for x in names)]
            return not missing, f'missing entries: {missing}' if missing else 'entries present'
        if t in INSPECT:
            info = self._inspect(work, rel)
            if not info.get('ok'):
                return False, info.get('error', 'inspection failed')
            if t == 'image_min':
                ok = info.get('kind') == 'image' and info['width'] >= c['width'] and info['height'] >= c['height']
                return ok, f'image {info.get("width")}x{info.get("height")}'
            key, kind = {'docx_min_words': ('words', 'docx'), 'pdf_min_pages': ('pages', 'pdf'),
                         'xlsx_sheets_min': ('sheets', 'xlsx'), 'pptx_min_slides': ('slides', 'pptx')}[t]
            val = info.get(key)
            val = len(val) if isinstance(val, list) else val
            return info.get('kind') == kind and isinstance(val, int) and val >= c['value'], f'{kind} {key}={val} (min {c["value"]})'
        if size > 20_000_000:
            return False, 'file too large for text checks'
        text = full.read_text(encoding='utf-8', errors='replace')
        if t == 'contains':
            return c['value'].casefold() in text.casefold(), f'contains {c["value"]!r}'
        if t == 'not_contains':
            return c['value'].casefold() not in text.casefold(), f'does not contain {c["value"]!r}'
        if t == 'regex':
            return bool(re.search(c['value'], text, re.M)), f'regex {c["value"]!r}'
        if t in ('json_valid', 'json_keys'):
            try:
                data = json.loads(text)
            except ValueError as e:
                return False, f'invalid JSON: {e}'
            if t == 'json_valid':
                return True, 'valid JSON'
            missing = [k for k in c['value'] if not isinstance(data, dict) or k not in data]
            return not missing, f'missing keys {missing}' if missing else 'keys present'
        if t == 'python_compiles':
            try:
                compile(text, rel, 'exec')  # compiles only, never executes
                return True, 'compiles'
            except SyntaxError as e:
                return False, f'SyntaxError line {e.lineno}: {e.msg}'
        if t == 'words_min':
            n = len(text.split())
            return n >= c['value'], f'{n} words (min {c["value"]})'
        if t == 'lines_min':
            n = len(text.splitlines())
            return n >= c['value'], f'{n} lines (min {c["value"]})'
        if t == 'no_placeholders':
            m = PLACEHOLDER.search(text)
            return not m, f'placeholder found: {m.group(0)!r}' if m else 'no placeholders'
        return False, f'unknown check {t}'

    def run(self, work: Path, deliverables: list[dict]) -> dict:
        """-> {'ok': all passed, 'deliverables': [{path, ok, checks:[{type, ok, detail}]}]}"""
        res = []
        for d in deliverables:
            checks = []
            for c in d['checks']:
                ok, detail = self.check_one(work, d['path'], c)
                checks.append({'type': c['type'], 'ok': bool(ok), 'detail': str(detail)[:400]})
            res.append({'path': d['path'], 'ok': all(x['ok'] for x in checks), 'checks': checks})
        return {'ok': bool(res) and all(r['ok'] for r in res), 'deliverables': res}
