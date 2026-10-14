"""V16 capability registry: what JARVIS can actually do, where, with which risk - and proof that it works.

A plan (written by a model) can only *name* a capability and pass typed parameters. It can never
supply a command line: argv comes from this file (builtin catalog) or from an operator-owned
drop-in manifest. Every parameter is validated (relative paths stay inside the job workspace,
no option injection, enums/regex for strings). Everything runs in the sandbox (no network,
read-only system, only the workspace writable, secrets hidden); without a sandbox: fail closed.

Status lifecycle:  missing -> available (binary found) -> tested (self-test passed in the sandbox)
                   failed (self-test failed) | disabled (operator). Only `tested` is usable.
Discovery never grants rights: drop-in tools are always risk 'read', never network, never
privileged, and only become usable after their own self-test passed inside the sandbox.
PC capabilities (Java, Blender, GPU models) are reported by the PC client and run only there.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import runner
import sandbox

NAME = re.compile(r'^[a-z][a-z0-9_-]{1,20}\.[a-z0-9_-]{2,40}$')
SAFE_STR = re.compile(r'^[^\x00-\x1f\x7f]{0,300}$')
SCHEMA = '''
CREATE TABLE IF NOT EXISTS capabilities(
    name TEXT NOT NULL, host TEXT NOT NULL, definition TEXT NOT NULL, source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('missing','available','tested','failed','disabled')),
    version TEXT, tested_at INTEGER, test_detail TEXT, uses INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0, updated INTEGER NOT NULL,
    PRIMARY KEY(name, host));
'''
ENV_BASE = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8',
            'PYTHONDONTWRITEBYTECODE': '1', 'MPLBACKEND': 'Agg'}
IMG = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff', '.ppm', '.pgm']
IM_FLAGS = re.compile(r'^-(resize|thumbnail|rotate|quality|colorspace|crop|gravity|extent|strip|flip|flop|negate|'
                      r'blur|sharpen|border|bordercolor|background|flatten|trim|density|alpha)$')
IM_VALUE = re.compile(r'^[0-9A-Za-z%x+#.!<>^-]{1,40}$')
FF_FLAGS = re.compile(r'^-(t|ss|to|vf|af|c:v|c:a|b:v|b:a|r|s|an|vn|ar|ac|f|preset|crf|pix_fmt|frames:v|q:v|ab)$')
FF_VALUE = re.compile(r'^[0-9A-Za-z_.:=,x/*+-]{1,80}$')
# 44-byte WAV header + 8 samples silence, for the ffmpeg self-test
_WAV = base64.b64encode(b'RIFF4\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00\x01\x00\x08\x00'
                        b'data\x08\x00\x00\x00' + b'\x80' * 8).decode()

BUILTIN: dict[str, dict] = {
    'python.run': {
        'title': 'Python-Skript im Arbeitsordner ausführen (Sandbox, ohne Netz; numpy/matplotlib/PIL/docx/openpyxl/reportlab verfügbar)',
        'host': 'server', 'argv': ['python3', '-I', '{script}', '*{args}'],
        'params': {'script': {'type': 'relpath', 'ext': ['.py']}, 'args': {'type': 'list', 'max': 20, 'optional': True}},
        'risk': 'reversible', 'timeout': 600, 'mem_mb': 1024,
        'selftest': {'files': {'t.py': 'open("o.txt","w").write(str(6*7))'}, 'args': {'script': 't.py'},
                     'expect': {'exit': 0, 'file': 'o.txt', 'contains': '42'}}},
    'python.unittest': {
        'title': 'Python-Tests (unittest) im Arbeitsordner ausführen',
        'host': 'server', 'argv': ['python3', '-I', '-m', 'unittest', 'discover', '-s', '{dir}', '-p', '{pattern}', '-v'],
        'params': {'dir': {'type': 'relpath', 'kind': 'dir', 'default': '.'},
                   'pattern': {'type': 'str', 'regex': r'^[A-Za-z0-9_*.\-]{1,40}$', 'default': 'test*.py'}},
        'risk': 'reversible', 'timeout': 600, 'mem_mb': 1024,
        'selftest': {'files': {'test_a.py': 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(1+1, 2)\n'},
                     'args': {}, 'expect': {'exit': 0, 'stdout': 'OK'}}},
    'python.compile': {
        'title': 'Python-Dateien auf Syntaxfehler prüfen',
        'host': 'server', 'argv': ['python3', '-I', '-m', 'py_compile', '*{files}'],
        'params': {'files': {'type': 'list', 'item': 'relpath', 'ext': ['.py'], 'max': 50}},
        'risk': 'read', 'timeout': 120, 'mem_mb': 512,
        'selftest': {'files': {'a.py': 'x = 1\n'}, 'args': {'files': ['a.py']}, 'expect': {'exit': 0}}},
    'doc.pandoc': {
        'title': 'Dokumente umwandeln (Markdown/HTML/DOCX/ODT -> DOCX/ODT/HTML/EPUB/Markdown), pandoc --sandbox',
        'host': 'server', 'argv': ['pandoc', '--sandbox', '{input}', '-o', '{output}'],
        'params': {'input': {'type': 'relpath', 'ext': ['.md', '.markdown', '.html', '.txt', '.rst', '.docx', '.odt']},
                   'output': {'type': 'relpath_out', 'ext': ['.docx', '.odt', '.html', '.epub', '.md', '.txt']}},
        'risk': 'reversible', 'timeout': 180, 'mem_mb': 1024,
        'selftest': {'files': {'a.md': '# Titel\n\nText.\n'}, 'args': {'input': 'a.md', 'output': 'a.docx'},
                     'expect': {'exit': 0, 'file': 'a.docx', 'magic': 'zip'}}},
    'doc.office_pdf': {
        'title': 'Office-Dokument (DOCX/ODT/XLSX/PPTX/TXT) mit LibreOffice in PDF umwandeln (schwer: viel RAM)',
        'host': 'server', 'argv': ['soffice', '--headless', '--norestore', '--nolockcheck', '--convert-to', 'pdf', '--outdir', '{outdir}', '{input}'],
        'params': {'input': {'type': 'relpath', 'ext': ['.docx', '.odt', '.xlsx', '.ods', '.pptx', '.odp', '.txt', '.rtf']},
                   'outdir': {'type': 'relpath', 'kind': 'dir', 'default': '.'}},
        'risk': 'reversible', 'timeout': 300, 'mem_mb': 4096, 'heavy': True,
        'selftest': {'files': {'a.txt': 'Hallo PDF\n'}, 'args': {'input': 'a.txt'},
                     'expect': {'exit': 0, 'file': 'a.pdf', 'magic': 'pdf'}}},
    'image.convert': {
        'title': 'Bilder umwandeln/skalieren/zuschneiden (ImageMagick, nur erlaubte Optionen)',
        'host': 'server', 'argv': ['convert', '{input}', '*{ops}', '{output}'],
        'params': {'input': {'type': 'relpath', 'ext': IMG}, 'output': {'type': 'relpath_out', 'ext': IMG},
                   'ops': {'type': 'list', 'max': 24, 'optional': True, 'flags': 'im'}},
        'risk': 'reversible', 'timeout': 180, 'mem_mb': 1024,
        'selftest': {'files': {'a.ppm': 'P3\n2 1\n255\n255 0 0  0 0 255\n'}, 'args': {'input': 'a.ppm', 'output': 'a.png', 'ops': ['-resize', '4x2']},
                     'expect': {'exit': 0, 'file': 'a.png', 'magic': 'png'}}},
    'media.ffmpeg': {
        'title': 'Audio/Video umwandeln oder schneiden (ffmpeg, nur erlaubte Optionen; schwer bei Video)',
        'host': 'server', 'argv': ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-i', '{input}', '*{opts}', '{output}'],
        'params': {'input': {'type': 'relpath', 'ext': ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.mp4', '.mkv', '.webm', '.mov', '.png', '.jpg']},
                   'output': {'type': 'relpath_out', 'ext': ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.mp4', '.mkv', '.webm', '.gif', '.png', '.jpg']},
                   'opts': {'type': 'list', 'max': 24, 'optional': True, 'flags': 'ff'}},
        'risk': 'reversible', 'timeout': 900, 'mem_mb': 1536, 'heavy': True,
        'selftest': {'files_b64': {'a.wav': _WAV}, 'args': {'input': 'a.wav', 'output': 'b.wav'},
                     'expect': {'exit': 0, 'file': 'b.wav', 'magic': 'wav'}}},
    'pdf.to_png': {
        'title': 'PDF-Seiten als PNG ausgeben (Vorschau/Prüfung)',
        'host': 'server', 'argv': ['pdftoppm', '-png', '-r', '{dpi}', '-f', '{first}', '-l', '{last}', '{input}', '{outprefix}'],
        'params': {'input': {'type': 'relpath', 'ext': ['.pdf']}, 'outprefix': {'type': 'relpath_out', 'ext': ['']},
                   'dpi': {'type': 'int', 'min': 30, 'max': 200, 'default': 72}, 'first': {'type': 'int', 'min': 1, 'max': 9999, 'default': 1},
                   'last': {'type': 'int', 'min': 1, 'max': 9999, 'default': 3}},
        'risk': 'reversible', 'timeout': 180, 'mem_mb': 1024, 'selftest': None},
    'data.jq': {
        'title': 'JSON filtern/umformen (jq); Ausgabe in eine Datei',
        'host': 'server', 'argv': ['jq', '{filter}', '{input}'], 'stdout_param': 'output',
        'params': {'filter': {'type': 'str', 'regex': r'^[^\x00-\x1f\x7f]{1,300}$'}, 'input': {'type': 'relpath', 'ext': ['.json']},
                   'output': {'type': 'relpath_out', 'ext': ['.json', '.txt']}},
        'risk': 'reversible', 'timeout': 120, 'mem_mb': 512,
        'selftest': {'files': {'a.json': '{"a": [1, 2, 3]}'}, 'args': {'filter': '.a | add', 'input': 'a.json', 'output': 'o.txt'},
                     'expect': {'exit': 0, 'file': 'o.txt', 'contains': '6'}}},
    'archive.zip': {
        'title': 'Dateien/Ordner des Arbeitsordners zu einem ZIP packen',
        'host': 'server', 'argv': ['python3', '-I', '-m', 'zipfile', '-c', '{output}', '*{files}'],
        'params': {'output': {'type': 'relpath_out', 'ext': ['.zip']}, 'files': {'type': 'list', 'item': 'relpath', 'kind': 'any', 'max': 50}},
        'risk': 'reversible', 'timeout': 300, 'mem_mb': 512,
        'selftest': {'files': {'a.txt': 'x'}, 'args': {'output': 'o.zip', 'files': ['a.txt']}, 'expect': {'exit': 0, 'file': 'o.zip', 'magic': 'zip'}}},
    # ---- PC (Windows) capabilities: executed only by the PC worker after the operator allowed them there ----
    'java.build': {'title': 'Java/Gradle-Projekt bauen (Minecraft-Mods); nur am PC (Java 21), braucht Netz für Abhängigkeiten',
                   'host': 'pc', 'argv': ['<pc>'], 'params': {'dir': {'type': 'relpath', 'kind': 'dir', 'default': '.'}},
                   'risk': 'reversible', 'network': True, 'timeout': 1800, 'mem_mb': 4096, 'selftest': None},
    'blender.render': {'title': 'Blender-Szene rendern/exportieren; nur am PC (GPU)', 'host': 'pc', 'argv': ['<pc>'],
                       'params': {'blend': {'type': 'relpath', 'ext': ['.blend', '.py']}}, 'risk': 'reversible', 'timeout': 3600,
                       'mem_mb': 8192, 'selftest': None},
    'ollama.ask': {'title': 'Lokales Sprachmodell (gemma3:4b) am PC, auch für private Daten (Klasse B)', 'host': 'pc', 'argv': ['<pc>'],
                   'params': {'input': {'type': 'relpath', 'ext': ['.txt', '.md']}, 'output': {'type': 'relpath_out', 'ext': ['.txt', '.md']}},
                   'risk': 'read', 'timeout': 600, 'mem_mb': 8192, 'selftest': None},
}
MAGIC = {'zip': b'PK\x03\x04', 'pdf': b'%PDF', 'png': b'\x89PNG', 'jpeg': b'\xff\xd8\xff', 'gif': b'GIF8', 'wav': b'RIFF'}


class CapError(ValueError):
    pass


def _owner_only(p: Path) -> bool:
    if os.name != 'posix':
        return True
    st = p.lstat()
    return not stat.S_ISLNK(st.st_mode) and st.st_uid == os.getuid() and not st.st_mode & 0o022


def check_rel(work: Path, value, *, must_exist=True, kind='file', ext=None) -> str:
    """Relative path inside work -> absolute path string. Refuses escapes, links out, option injection."""
    if not isinstance(value, str) or not value or len(value) > 200 or '\x00' in value or '\\' in value:
        raise CapError('path must be a short relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or value.startswith('-') or value.startswith('~'):
        raise CapError(f'path not allowed: {value!r}')
    base = Path(work).resolve()
    full = (base / value).resolve()
    if full != base and base not in full.parents:
        raise CapError(f'path escapes the workspace: {value!r}')
    if ext is not None and ext != [''] and full.suffix.lower() not in ext:
        raise CapError(f'file type {full.suffix or "(none)"} not allowed here (allowed: {", ".join(ext)})')
    if must_exist:
        if kind == 'dir' and not full.is_dir():
            raise CapError(f'directory not found: {value!r}')
        if kind == 'file' and not full.is_file():
            raise CapError(f'file not found: {value!r}')
        if kind == 'any' and not full.exists():
            raise CapError(f'not found: {value!r}')
    else:
        full.parent.mkdir(parents=True, exist_ok=True)
    return str(full)


def _flags_ok(items, which):
    """Each token is an allowed flag, a plain value, or a (negative) number. Nothing else."""
    flags, values = (IM_FLAGS, IM_VALUE) if which == 'im' else (FF_FLAGS, FF_VALUE)
    for t in items:
        ok = isinstance(t, str) and (bool(flags.match(t)) or bool(re.match(r'^-?\d+(\.\d+)?$', t))
                                     or (bool(values.match(t)) and not t.startswith('-')))
        if not ok:
            raise CapError(f'option not allowed: {t!r}')


def render(defn: dict, args: dict, work: Path) -> list[str]:
    """Validated argv for a capability. Unknown args are refused (the model cannot add any)."""
    params = defn.get('params', {})
    args = dict(args or {})
    unknown = set(args) - set(params)
    if unknown:
        raise CapError(f'unknown parameters: {sorted(unknown)}')
    vals: dict = {}
    for name, spec in params.items():
        v = args.get(name, spec.get('default'))
        t = spec['type']
        if v is None:
            if spec.get('optional'):
                vals[name] = [] if t == 'list' else None
                continue
            raise CapError(f'missing parameter {name}')
        if t == 'relpath':
            vals[name] = check_rel(work, v, kind=spec.get('kind', 'file'), ext=spec.get('ext'))
        elif t == 'relpath_out':
            vals[name] = check_rel(work, v, must_exist=False, ext=spec.get('ext'))
        elif t == 'int':
            if type(v) is not int or not spec.get('min', -10**9) <= v <= spec.get('max', 10**9):
                raise CapError(f'{name} must be an integer in range')
            vals[name] = str(v)
        elif t == 'str':
            if not isinstance(v, str) or not re.match(spec.get('regex', SAFE_STR.pattern), v) or v.startswith('-'):
                raise CapError(f'{name} has an invalid value')
            vals[name] = v
        elif t == 'list':
            if not isinstance(v, list) or len(v) > spec.get('max', 20):
                raise CapError(f'{name} must be a list (max {spec.get("max", 20)})')
            if spec.get('item') == 'relpath':
                vals[name] = [check_rel(work, x, kind=spec.get('kind', 'file'), ext=spec.get('ext')) for x in v]
            elif spec.get('flags'):
                _flags_ok(v, spec['flags'])
                vals[name] = list(v)
            else:
                if not all(isinstance(x, str) and SAFE_STR.match(x) and len(x) <= 200 for x in v):
                    raise CapError(f'{name}: list of short strings required')
                vals[name] = list(v)
        else:
            raise CapError(f'bad parameter type {t}')
    argv = []
    for tok in defn['argv']:
        if tok.startswith('*{') and tok.endswith('}'):
            argv.extend(vals.get(tok[2:-1]) or [])
        elif tok.startswith('{') and tok.endswith('}'):
            v = vals.get(tok[1:-1])
            if v is None:
                raise CapError(f'missing value for {tok}')
            argv.append(v)
        else:
            argv.append(tok)
    return argv


def validate_manifest(m: dict, tool_dir: Path) -> dict:
    """Drop-in tool manifest -> capability definition. No privilege can be requested."""
    if not isinstance(m, dict):
        raise CapError('manifest must be an object')
    allowed = {'name', 'title', 'version', 'entry', 'interpreter', 'params', 'argv', 'risk', 'network', 'timeout', 'mem_mb', 'selftest'}
    if set(m) - allowed:
        raise CapError(f'unknown manifest keys: {sorted(set(m) - allowed)}')
    name = m.get('name')
    if not isinstance(name, str) or not name.startswith('tool.') or not NAME.match(name):
        raise CapError('drop-in names must look like tool.<name>')
    if m.get('risk', 'read') != 'read':
        raise CapError('drop-in tools are read-only (risk "read"); they cannot request more')
    if m.get('network'):
        raise CapError('drop-in tools never get network access')
    if m.get('interpreter', 'python3') != 'python3':
        raise CapError('only python3 is allowed as interpreter (no shells)')
    entry = m.get('entry')
    if not isinstance(entry, str) or '/' in entry or entry.startswith('.') or not entry.endswith('.py'):
        raise CapError('entry must be a .py file directly in the tool folder')
    ep = tool_dir / entry
    if not ep.is_file() or not _owner_only(ep) or not _owner_only(tool_dir) or ep.stat().st_size > 512_000:
        raise CapError('entry missing, too large, a link, or writable by others')
    argv = m.get('argv')
    if not isinstance(argv, list) or not all(isinstance(t, str) for t in argv) or len(argv) > 30:
        raise CapError('argv must be a list of strings')
    if any(not re.match(r'^(\*?\{[a-z_]{1,20}\}|-{0,2}[A-Za-z0-9_=.,-]{1,40})$', t) for t in argv):
        raise CapError('argv tokens must be placeholders or simple literal options')
    params = m.get('params') or {}
    if not isinstance(params, dict) or len(params) > 12:
        raise CapError('params must be an object (max 12)')
    for p, spec in params.items():
        if not isinstance(spec, dict) or spec.get('type') not in ('relpath', 'relpath_out', 'int', 'str', 'list'):
            raise CapError(f'param {p}: unsupported type')
        if spec.get('flags'):
            raise CapError(f'param {p}: flags lists are reserved for builtins')
    t, mem = m.get('timeout', 120), m.get('mem_mb', 512)
    if type(t) is not int or not 1 <= t <= 900 or type(mem) is not int or not 64 <= mem <= 2048:
        raise CapError('timeout 1..900 s, mem_mb 64..2048')
    if not isinstance(m.get('selftest'), dict):
        raise CapError('a drop-in tool needs a selftest')
    return {'title': str(m.get('title') or name)[:160], 'host': 'server', 'argv': ['python3', '-I', '{__entry__}', *argv],
            'params': params, 'risk': 'read', 'timeout': t, 'mem_mb': mem, 'selftest': m['selftest'],
            'dropin': {'dir': str(tool_dir), 'entry': entry,
                       'sha256': hashlib.sha256(ep.read_bytes()).hexdigest(), 'version': str(m.get('version') or '0')[:20]}}


class Registry:
    def __init__(self, db: Path, host: str = 'server', tools_dir: Path | None = None, hide: list[str] | None = None,
                 clock=time.time):
        self.db, self.host, self.clock = Path(db), host, clock
        self.tools_dir = Path(tools_dir) if tools_dir else None
        self.hide = list(hide or [])
        with self._conn(True) as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self, write=False):
        c = sqlite3.connect(str(self.db), timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout = 30000')
        try:
            if write:
                c.execute('BEGIN IMMEDIATE')
            yield c
            if write:
                c.commit()
        except Exception:
            if write:
                c.rollback()
            raise
        finally:
            c.close()

    # ---------- registry ----------
    def _save(self, name, host, defn, source, status, version=None, detail=None, tested=False):
        now = int(self.clock())
        with self._conn(True) as c:
            old = c.execute('SELECT definition,status FROM capabilities WHERE name=? AND host=?', (name, host)).fetchone()
            same = old and old['definition'] == json.dumps(defn, sort_keys=True)
            if old and old['status'] == 'disabled':
                status = 'disabled'  # operator decision survives rediscovery
            elif same and old['status'] == 'tested' and status == 'available' and not tested:
                status = 'tested'   # unchanged definition keeps its proof
            c.execute('INSERT INTO capabilities(name,host,definition,source,status,version,tested_at,test_detail,updated) '
                      'VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(name,host) DO UPDATE SET definition=excluded.definition,'
                      'source=excluded.source,status=excluded.status,version=COALESCE(excluded.version,version),'
                      'tested_at=CASE WHEN ? THEN excluded.tested_at ELSE tested_at END,'
                      'test_detail=CASE WHEN ? THEN excluded.test_detail ELSE test_detail END,updated=excluded.updated',
                      (name, host, json.dumps(defn, sort_keys=True), source, status, version, now if tested else None,
                       detail, now, tested, tested))
        return status

    def get(self, name: str, host: str | None = None) -> dict | None:
        with self._conn() as c:
            r = c.execute('SELECT * FROM capabilities WHERE name=? AND host=?', (name, host or self.host)).fetchone()
        if not r:
            return None
        d = dict(r)
        d['definition'] = json.loads(d['definition'])
        return d

    def listing(self, host: str | None = None) -> list[dict]:
        with self._conn() as c:
            rows = c.execute('SELECT name,host,status,version,source,tested_at,test_detail,uses,successes,failures,definition '
                             'FROM capabilities ' + ('WHERE host=? ' if host else '') + 'ORDER BY host,name',
                             (host,) if host else ()).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            defn = json.loads(d.pop('definition'))
            d['title'] = defn.get('title')
            d['risk'] = defn.get('risk')
            d['heavy'] = bool(defn.get('heavy'))
            d['params'] = {k: {kk: vv for kk, vv in v.items() if kk in ('type', 'ext', 'kind', 'default', 'optional', 'max')}
                           for k, v in defn.get('params', {}).items()}
            out.append(d)
        return out

    def usable(self, name: str, host: str | None = None) -> bool:
        c = self.get(name, host)
        return bool(c and c['status'] == 'tested')

    def catalog_for_planner(self) -> list[dict]:
        """Compact list of usable capabilities (both hosts) for the planner prompt."""
        return [{'name': c['name'], 'host': c['host'], 'title': c['title'], 'params': c['params'], 'heavy': c['heavy']}
                for c in self.listing() if c['status'] == 'tested']

    def set_status(self, name: str, status: str, host: str | None = None) -> None:
        if status not in ('disabled', 'available'):
            raise ValueError('operator can only disable or re-enable (re-enable needs a new self-test)')
        with self._conn(True) as c:
            c.execute('UPDATE capabilities SET status=?,updated=? WHERE name=? AND host=?',
                      (status, int(self.clock()), name, host or self.host))

    def record_use(self, name: str, ok: bool, host: str | None = None) -> None:
        with self._conn(True) as c:
            c.execute('UPDATE capabilities SET uses=uses+1, successes=successes+?, failures=failures+? WHERE name=? AND host=?',
                      (1 if ok else 0, 0 if ok else 1, name, host or self.host))

    def report_pc(self, caps: dict) -> list[str]:
        """The PC client reports which PC capabilities it found and tested there (status only, no new rights)."""
        done = []
        for name, info in (caps or {}).items():
            if name not in BUILTIN or BUILTIN[name]['host'] != 'pc' or not isinstance(info, dict):
                continue
            st = info.get('status') if info.get('status') in ('missing', 'available', 'tested', 'failed') else 'failed'
            self._save(name, 'pc', BUILTIN[name], 'pc-report', st, str(info.get('version') or '')[:40] or None,
                       str(info.get('detail') or '')[:300], tested=st in ('tested', 'failed'))
            done.append(name)
        return done

    # ---------- discovery ----------
    def discover(self, selftest: bool = True, only: set[str] | None = None) -> dict:
        """Find builtin tools on this host and operator drop-ins; self-test new or changed ones.
        `only` limits the builtin part to these names (tests, targeted re-checks)."""
        found = {'builtin': {}, 'dropin': {}, 'rejected': {}}
        for name, defn in BUILTIN.items():
            if only is not None and name not in only:
                continue
            if defn['host'] != self.host:
                if not self.get(name, defn['host']):
                    self._save(name, defn['host'], defn, 'builtin', 'missing')
                continue
            exe = shutil.which(defn['argv'][0])
            if not exe:
                found['builtin'][name] = self._save(name, self.host, defn, 'builtin', 'missing')
                continue
            st = self._save(name, self.host, defn, 'builtin', 'available', self._version(exe))
            if selftest and st == 'available':
                st = self.selftest(name)
            found['builtin'][name] = st
        if self.tools_dir and self.tools_dir.is_dir():
            for d in sorted(self.tools_dir.iterdir()):
                mf = d / 'tool.json'
                if not d.is_dir() or not mf.is_file():
                    continue
                try:
                    if not _owner_only(mf):
                        raise CapError('manifest is a link or writable by others')
                    m = json.loads(mf.read_text(encoding='utf-8'))
                    defn = validate_manifest(m, d)
                except (CapError, ValueError, OSError) as e:
                    found['rejected'][d.name] = str(e)[:200]
                    continue
                st = self._save(m['name'], self.host, defn, 'dropin', 'available', defn['dropin']['version'])
                if selftest and st == 'available':
                    st = self.selftest(m['name'])
                found['dropin'][m['name']] = st
        return found

    @staticmethod
    def _version(exe: str) -> str | None:
        for flag in ('--version', '-version'):
            try:
                p = subprocess.run([exe, flag], capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL)
                line = (p.stdout or p.stderr).strip().splitlines()
                if line:
                    return line[0][:80]
            except (OSError, subprocess.TimeoutExpired):
                pass
        return None

    def selftest(self, name: str) -> str:
        cap = self.get(name)
        if not cap:
            raise CapError('unknown capability')
        defn = cap['definition']
        st = defn.get('selftest')
        if not st:
            self._save(name, self.host, defn, cap['source'], 'available', detail='no self-test defined', tested=True)
            return 'available'
        work = Path(tempfile.mkdtemp(prefix='jarvis-selftest-'))
        try:
            for fn, text in (st.get('files') or {}).items():
                check_rel(work, fn, must_exist=False)
                (work / fn).write_text(text, encoding='utf-8')
            for fn, b64 in (st.get('files_b64') or {}).items():
                check_rel(work, fn, must_exist=False)
                (work / fn).write_bytes(base64.b64decode(b64))
            res = self.execute(name, st.get('args') or {}, work, require_tested=False)
            exp, why = st.get('expect') or {}, None
            if res['exit'] != exp.get('exit', 0):
                why = f'exit {res["exit"]}: {res["tail"][-200:]}'
            elif exp.get('stdout') and exp['stdout'] not in res['tail']:
                why = 'expected output missing'
            elif exp.get('file'):
                f = work / exp['file']
                if not f.is_file():
                    why = f'expected file {exp["file"]} missing'
                elif exp.get('contains') and exp['contains'] not in f.read_text(encoding='utf-8', errors='replace'):
                    why = 'expected content missing'
                elif exp.get('magic') and not f.read_bytes()[:8].startswith(MAGIC[exp['magic']]):
                    why = f'output is not {exp["magic"]}'
            status = 'failed' if why else 'tested'
            self._save(name, self.host, defn, cap['source'], status, detail=(why or f'ok in {res["ms"]} ms, sandbox={res["sandboxed"]}')[:300],
                       tested=True)
            return status
        except CapError as e:
            self._save(name, self.host, defn, cap['source'], 'failed', detail=str(e)[:300], tested=True)
            return 'failed'
        finally:
            shutil.rmtree(work, ignore_errors=True)

    # ---------- execution ----------
    def execute(self, name: str, args: dict, work: Path, *, require_tested=True, timeout: int | None = None) -> dict:
        """Run one capability inside the sandbox. Never raises for tool failures; refuses invalid input."""
        cap = self.get(name)
        if not cap or cap['host'] != self.host:
            raise CapError(f'capability {name} is not available on {self.host}')
        if require_tested and cap['status'] != 'tested':
            raise CapError(f'capability {name} is {cap["status"]}, not tested')
        defn = cap['definition']
        work = Path(work).resolve()
        args = dict(args or {})
        out_param = defn.get('stdout_param')
        out_file = None
        if out_param:
            out_file = check_rel(work, args.pop(out_param, None), must_exist=False, ext=defn['params'][out_param].get('ext'))
            params = {k: v for k, v in defn['params'].items() if k != out_param}
            defn = {**defn, 'params': params}
        if defn.get('dropin'):
            src = Path(defn['dropin']['dir']) / defn['dropin']['entry']
            if hashlib.sha256(src.read_bytes()).hexdigest() != defn['dropin']['sha256']:
                raise CapError('drop-in tool changed since its self-test; run discovery again')
            dst = work / '.jarvis-tools' / name
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / defn['dropin']['entry'])
            defn = {**defn, 'argv': [str(dst / defn['dropin']['entry']) if t == '{__entry__}' else t for t in defn['argv']]}
        argv = render(defn, args, work)
        env = {**ENV_BASE, 'HOME': str(work)}
        if not sandbox.available():
            return {'exit': 126, 'ok': False, 'ms': 0, 'tail': 'no sandbox available: refused (fail closed)', 'sandboxed': False,
                    'cpu_ms': 0}
        exe = shutil.which(argv[0]) or argv[0]
        wrapped = sandbox.wrap([exe, *argv[1:]], work, work, env, self.hide)
        t = min(timeout or defn.get('timeout', 300), defn.get('timeout', 300))
        start = time.monotonic()
        before = _child_cpu()
        out_fh = open(out_file, 'wb') if out_file else None
        try:
            p = subprocess.Popen(wrapped, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out_fh or subprocess.PIPE, stderr=subprocess.PIPE if out_fh else subprocess.STDOUT,
                                 preexec_fn=runner._limits(defn.get('mem_mb', 1024), t))
            try:
                out, err = p.communicate(timeout=t)
                code = p.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, 9)
                except OSError:
                    p.kill()
                out, err = p.communicate()
                code = 124
            text = ((out or b'') if not out_fh else (err or b'')).decode('utf-8', 'replace')
            if code == 124:
                text += '\n[timeout]'
        except FileNotFoundError:
            code, text = 127, 'program not found'
        finally:
            if out_fh:
                out_fh.close()
        return {'exit': code, 'ok': code == 0, 'ms': int((time.monotonic() - start) * 1000), 'tail': runner.redact(text[-1500:]),
                'sandboxed': True, 'cpu_ms': _child_cpu() - before, 'argv0': Path(argv[0]).name}


def _child_cpu() -> int:
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        return int((r.ru_utime + r.ru_stime) * 1000)
    except (ImportError, OSError):
        return 0
