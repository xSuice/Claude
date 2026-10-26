#!/usr/bin/env python3
"""V16.1 Cloud-Fallback-Brain: OpenAI-kompatibler Executor. NUR aktiv wenn Claude nicht verfügbar
ist (Kontingent erschöpft) oder die Routing-Schicht explizit einen Cloud-Provider wählt.

Vertrag identisch zu ClaudeWorker.run (gleiche Rückgabe-Keys). Das Modell führt NIEMALS Befehle
aus: Datei-Schreibungen werden von JARVIS selbst innerhalb des Job-Arbeitsordners emuliert
(Workspace-Jail); Tests/Builds laufen danach wie gehabt lokal in der Sandbox.

Fail-closed: https + Host-Fixierung via base_url, kein Redirect (Authorization-Header würde
weitergetragen werden), Key-Datei 0600 + Eigentümerprüfung, Antwortgrößen-Limit, JSON-Validierung,
Timeout, ein Retry bei transienten Fehlern.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

MAX_FILES = 40
MAX_TOTAL_BYTES = 2_000_000
MAX_PATH_LEN = 240


class CloudError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _first_json(text: str):
    """Erstes balanciertes {...}- oder [...]-JSON im Text (string-aware: Klammern in
    String-Literalen und Escapes werden korrekt übersprungen)."""
    s = str(text or '')
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        if ch in '"\'':
            i += 1
            while i < n:
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == ch:
                    break
                i += 1
        elif ch in '{[':
            start, open_ch, depth = i, ch, 0
            close_ch = '}' if ch == '{' else ']'
            j = i
            while j < n:
                cj = s[j]
                if cj in '"\'':
                    q = cj
                    j += 1
                    while j < n:
                        if s[j] == '\\':
                            j += 2
                            continue
                        if s[j] == q:
                            break
                        j += 1
                elif cj == open_ch:
                    depth += 1
                elif cj == close_ch:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(s[start:j + 1])
                        except ValueError:
                            break
                j += 1
            i = max(i + 1, j)  # hinter dem Fund (oder dem Abbruch) weitersuchen
            continue
        i += 1
    return None


def _safe_rel(path: str) -> str:
    p = str(path or '').replace('\\', '/').lstrip('/')
    parts = [x for x in p.split('/') if x not in ('', '.')]
    if not parts or any(x == '..' for x in parts) or len(p) > MAX_PATH_LEN or ':' in p or '\x00' in p:
        raise CloudError(f'unzulässiger Pfad: {path!r}')
    return '/'.join(parts)


def write_files_emulation(workspace: Path, files: list) -> tuple[list[str], str | None]:
    """Schreibt die vom Modell gelieferten Dateien in den Arbeitsordner (Jail: nur relative Pfade,
    keine Symlink-Eskalation). Das Modell selbst berührt nie die Platte."""
    written: list[str] = []
    total = 0
    if not isinstance(files, list) or len(files) > MAX_FILES:
        return written, f'Dateiliste ungültig oder zu groß ({len(files) if isinstance(files, list) else "?" } > {MAX_FILES})'
    w = Path(workspace).resolve()
    for f in files:
        try:
            if not isinstance(f, dict):
                return written, 'Dateieintrag ist kein Objekt'
            rel = _safe_rel(f.get('path'))
            content = f.get('content')
            if not isinstance(content, str):
                return written, f'Datei {rel}: content fehlt oder kein Text'
            total += len(content.encode('utf-8'))
            if total > MAX_TOTAL_BYTES:
                return written, f'Gesamtgröße überschritten (>{MAX_TOTAL_BYTES} B)'
            dest = (w / rel).resolve()
            if os.path.commonpath([str(w), str(dest)]) != str(w):
                return written, f'Pfad {rel} verlässt den Arbeitsordner'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding='utf-8')
            written.append(rel)
        except CloudError as e:
            return written, str(e)
    return written, None


class CloudWorker:
    """OpenAI-kompatibler Executor für den JARVIS Cloud-Fallback (z. B. nexum-Router)."""

    def __init__(self, cfg: dict):
        self.cfg = dict(cfg or {})
        self.base_url = str(self.cfg.get('base_url') or '').rstrip('/')
        self.model = str(self.cfg.get('model') or '')
        self.key_file = Path(os.path.expanduser(str(self.cfg.get('key_file') or '')))
        self.timeout_s = int(self.cfg.get('timeout_s') or 300)
        self.max_output_tokens = int(self.cfg.get('max_output_tokens') or 4000)
        self.max_response_bytes = int(self.cfg.get('max_response_bytes') or 400_000)
        self.price_in = float(self.cfg.get('price_in_per_mtok') or 0)
        self.price_out = float(self.cfg.get('price_out_per_mtok') or 0)

    # ------------------------------------------------------------------ setup checks
    def available(self) -> bool:
        try:
            self._validate_setup()
            return True
        except (CloudError, OSError):
            return False

    def _validate_setup(self) -> None:
        if not self.base_url.startswith('https://'):
            raise CloudError('cloud_fallback.base_url muss https:// sein')
        if not self.model:
            raise CloudError('cloud_fallback.model fehlt')
        st = self.key_file.stat()
        if st.st_mode & 0o077:
            raise CloudError(f'Key-Datei {self.key_file}: Rechte müssen 0600 sein')
        if st.st_uid != os.getuid():
            raise CloudError(f'Key-Datei {self.key_file} gehört nicht diesem Benutzer')

    def _key(self) -> str:
        return self.key_file.read_text(encoding='utf-8').strip()

    # ------------------------------------------------------------------ http
    def _post(self, payload: dict) -> dict:
        self._validate_setup()
        req = urllib.request.Request(
            self.base_url + '/chat/completions', data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self._key(), 'Content-Type': 'application/json'},
            method='POST')
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=self.timeout_s) as resp:
                raw = resp.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as e:
            body = e.read(2000).decode('utf-8', 'replace')
            raise CloudError(f'HTTP {e.code}: {body[:300]}') from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CloudError(f'Verbindung: {type(e).__name__}: {e}') from None
        if len(raw) > self.max_response_bytes:
            raise CloudError('Antwort überschreitet max_response_bytes')
        try:
            d = json.loads(raw)
        except ValueError as e:
            raise CloudError(f'Antwort ist kein JSON: {e}') from None
        if not isinstance(d, dict) or not d.get('choices'):
            raise CloudError('Antwort ohne choices')
        return d

    def _post_with_retry(self, payload: dict) -> dict:
        try:
            return self._post(payload)
        except CloudError as e:
            msg = str(e)
            transient = any(s in msg for s in ('HTTP 429', 'HTTP 5', 'Verbindung:', 'Timeout'))
            if not transient:
                raise
            time.sleep(3)
            return self._post(payload)

    @staticmethod
    def _extract(d: dict) -> tuple[str, dict]:
        msg = (d.get('choices') or [{}])[0].get('message') or {}
        text = str(msg.get('content') or '')
        u = d.get('usage') or {}
        tin, tout = int(u.get('prompt_tokens') or 0), int(u.get('completion_tokens') or 0)
        usage = {'in': tin, 'cache_write': 0, 'cache_read': 0, 'out': tout,
                 'new': tin + tout, 'known': bool(u)}
        return text, usage

    def _list_usd(self, usage: dict) -> float:
        return round((usage['in'] * self.price_in + usage['out'] * self.price_out) / 1_000_000, 6)

    def _fail(self, t0: float, err: str, usage: dict | None = None) -> dict:
        return {'ok': False, 'exit': 1, 'ms': int((time.monotonic() - t0) * 1000), 'model': self.model,
                'text': '', 'structured': None, 'subtype': 'cloud_error', 'turns': 1,
                'usage': usage or {'in': 0, 'cache_write': 0, 'cache_read': 0, 'out': 0, 'new': 0, 'known': True},
                'list_usd': 0.0, 'error': err[:400]}

    # ------------------------------------------------------------------ ClaudeWorker-compatible call (planner)
    def run(self, *, prompt: str, system: str, json_schema: dict | None = None, timeout_s: int | None = None,
            workspace: Path | None = None, model: str = '', tools: list | None = None,
            write: bool = True, max_turns: int | None = None) -> dict:
        t0 = time.monotonic()
        payload = {'model': self.model, 'max_tokens': self.max_output_tokens,
                   'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]}
        if json_schema is not None:
            payload['response_format'] = {'type': 'json_object'}
        try:
            text, usage = self._extract(self._post_with_retry(payload))
        except CloudError as e:
            return self._fail(t0, str(e))
        structured = _first_json(text) if '{' in text else None
        return {'ok': True, 'exit': 0, 'ms': int((time.monotonic() - t0) * 1000), 'model': self.model,
                'text': text[:20000], 'structured': structured if isinstance(structured, dict) else None,
                'subtype': 'success', 'turns': 1, 'usage': usage, 'list_usd': self._list_usd(usage), 'error': None}

    # ------------------------------------------------------------------ execution-style call (files emulation)
    def run_files(self, *, prompt: str, system: str, workspace: Path, timeout_s: int | None = None) -> dict:
        """Arbeiter-Aufruf: Das Modell liefert {"files":[...], "notes":...}; JARVIS schreibt."""
        t0 = time.monotonic()
        sys_p = system + (
            '\n\nZUSATZ (Cloud-Fallback): Du kannst KEINE Werkzeuge ausführen und keine Dateien selbst anlegen. '
            'Antworte AUSSCHLIESSLICH mit einem JSON-Objekt der Form '
            '{"files": [{"path": "<relativer Pfad>", "content": "<vollständiger Dateiinhalt>"}], '
            '"notes": "<max. 5 Zeilen: erstellte/geänderte Dateien, was offen ist>"}. '
            'Pfade nur relativ, ohne "..". Liefere echte, vollständige Inhalte - keine Platzhalter, kein "TODO".')
        payload = {'model': self.model, 'max_tokens': self.max_output_tokens,
                   'response_format': {'type': 'json_object'},
                   'messages': [{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': prompt}]}
        try:
            text, usage = self._extract(self._post_with_retry(payload))
        except CloudError as e:
            return self._fail(t0, str(e))
        data = _first_json(text)
        if not isinstance(data, dict):
            return self._fail(t0, 'Antwort ist kein gültiges JSON-Objekt', usage)
        written, err = write_files_emulation(workspace, data.get('files'))
        if err:
            r = self._fail(t0, f'Datei-Schreibung: {err}', usage)
            r['written'] = written
            return r
        notes = str(data.get('notes') or '')[:2000]
        return {'ok': True, 'exit': 0, 'ms': int((time.monotonic() - t0) * 1000), 'model': self.model,
                'text': notes, 'written': written, 'structured': None, 'subtype': 'success', 'turns': 1,
                'usage': usage, 'list_usd': self._list_usd(usage), 'error': None}


def quota_exhausted(error_text: str) -> bool:
    """Erkennt Claude-Kontingent-Erschöpfung (der Auslöser für den Cloud-Fallback)."""
    e = str(error_text or '').lower()
    return any(s in e for s in ('usage_limit_reached', 'weekly limit', 'hit your usage limit',
                                'billing hard limit', 'credit balance is too low'))
