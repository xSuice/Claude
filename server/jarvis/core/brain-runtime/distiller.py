"""Memory Distiller (Knowledge-Vertrag, 28.10.2026): nur belegte, wiederverwendbare Information gelangt ins Langzeitgedächtnis.

Ablauf: Ausführung fertig -> unabhängige Abnahme bestanden -> Kandidaten (deterministisch, ohne Modellaufruf, kein Chat-Dump)
-> Dedupe / Widerspruch -> Review-Queue -> erst nach Freigabe durch Philipp: Notiz im Vault (mit Herkunft und Evidenz).
Reine Funktionen; Speicherung und Freigabe macht taskengine.Engine."""
from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path
from secretscan import redact


def _redact_values(value):
    """Sanitize persisted candidate fields without serializing secrets first."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [_redact_values(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_values(v) for k, v in value.items()}
    return value

MAX_BODY = 1800
STOP = set('der die das und oder mit von für fur auf aus ist sind ein eine einer eines den dem des im in zu zur zum als bei nicht nur '
           'the and or of to a an is are for with on in'.split())


def norm_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r'[a-zäöüß0-9_.-]{3,}', text.casefold()) if w not in STOP}


def jaccard(a: str, b: str) -> float:
    x, y = norm_tokens(a), norm_tokens(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def fingerprint(kind: str, topic: str, body: str) -> str:
    return hashlib.sha256(f'{kind}|{topic}|{" ".join(sorted(norm_tokens(body)))}'.encode()).hexdigest()[:32]


def extract(job: dict, plan: dict, acceptance: dict, events: list[dict], council: dict | None) -> list[dict]:
    """Kandidaten aus einem abgenommenen Auftrag. Nie Rohtext aus Chat/Ergebnissen, nur Struktur + belegte Befunde."""
    if job.get('verdict') != 'done' or not acceptance.get('ok'):
        return []
    tt = plan.get('task_type') or job.get('task_type') or 'allgemein'
    rev = int(job.get('revision') or 1)
    ev_ids = [e['id'] for e in events if e['kind'] in ('finished', 'step_done', 'correction', 'step_failed', 'council_done')][:30]
    dl = [d for d in acceptance.get('deliverables') or [] if isinstance(d, dict)]
    evidence = {'job': job['id'], 'revision': rev, 'events': ev_ids,
                'acceptance': {'ok': True, 'passed': sum(1 for d in dl if d.get('ok')), 'total': len(dl)},
                'results_dir': job.get('results') or ''}
    out = []
    steps = [s for s in plan.get('steps') or [] if isinstance(s, dict)]
    if steps:
        lines = [f'- {s.get("title") or s.get("id")}' + (f' ({s.get("capability")})' if s.get('capability') else '') for s in steps[:12]]
        out.append({'kind': 'procedure', 'topic': f'procedure:{tt}', 'title': f'Bewährter Ablauf: {tt}',
                    'body': (f'Aufgabentyp {tt}, unabhängig abgenommen (Auftrag {job["id"]}, Revision {rev}).\nSchritte:\n'
                             + '\n'.join(lines))[:MAX_BODY], 'evidence': evidence})
    first_fail = next((e for e in events if e['kind'] in ('step_failed', 'correction')), None)
    if first_fail and int(job.get('fix_rounds') or 0) > 0:
        reason = re.sub(r'\s+', ' ', first_fail['text'])[:300]
        out.append({'kind': 'lesson', 'topic': f'lesson:{tt}', 'title': f'Erkenntnis: {tt}',
                    'body': f'Erste Fassung scheiterte: {reason}\nBehoben in Korrekturrunde; danach Abnahme bestanden.', 'evidence': evidence})
    if council and council.get('constraints'):
        out.append({'kind': 'decision', 'topic': f'decision:{council.get("council")}:{tt}',
                    'title': f'{council.get("council")}-Council: Randbedingungen für {tt}',
                    'body': ('Beratende Vorgaben; Einhaltung nicht separat verifiziert. Die Dateiabnahme allein belegt ihre Einhaltung nicht:\n'
                             + '\n'.join(f'- {c}' for c in council['constraints'][:8])
                             + (f'\nAbweichende Meinungen: {len(council.get("dissent") or [])}' if council.get('dissent') else ''))[:MAX_BODY],
                    'evidence': {**evidence, 'council_confidence': council.get('confidence')}})
    private = (job.get('spec') or {}).get('data_class') == 'private'
    out = _redact_values(out)
    for c in out:
        c['private'] = private
        c['fingerprint'] = fingerprint(c['kind'], c['topic'], c['body'])
    return out


def classify(cand: dict, existing: list[dict]) -> tuple[str, int | None]:
    """existing: frühere Kandidaten (id, topic, body, fingerprint, state). -> (state, bezug)."""
    for e in existing:
        if e['fingerprint'] == cand['fingerprint']:
            return 'duplicate', e['id']
    same = [e for e in existing if e['topic'] == cand['topic'] and e['state'] in ('proposed', 'approved', 'written')]
    for e in same:
        if jaccard(e['body'], cand['body']) >= 0.85:
            return 'duplicate', e['id']
    for e in same:
        if e['state'] == 'written' and cand['kind'] in ('procedure', 'decision') and jaccard(e['body'], cand['body']) < 0.5:
            return 'conflict', e['id']   # gleiches Thema, deutlich anderer Inhalt: Mensch entscheidet
    return 'proposed', None


def slug(text: str) -> str:
    s = re.sub(r'[^a-z0-9äöüß]+', '-', text.casefold()).strip('-')
    return s[:60] or 'notiz'


def write_note(vault_dir: Path, cand: dict, approved_by: str, clock=time.time) -> Path:
    """Atomar und ohne Überschreiben (O_EXCL). Frontmatter mit Herkunft; private Kandidaten bleiben private: true."""
    # Re-check legacy candidates at the persistence boundary as well.
    cand = _redact_values(cand)
    approved_by = redact(str(approved_by))
    vault_dir.mkdir(parents=True, exist_ok=True)
    day = time.strftime('%Y-%m-%d', time.localtime(clock()))
    path = vault_dir / f'{day}-{slug(cand["title"])}-k{cand["id"]}.md'
    ev = cand['evidence']
    fm = ['---', f'title: "{cand["title"].replace(chr(34), chr(39))}"', 'source: jarvis-v16', f'kind: {cand["kind"]}',
          f'job: {ev.get("job")}', f'revision: {ev.get("revision")}', f'evidence_events: {ev.get("events")}',
          f'acceptance: "{ev.get("acceptance")}"', f'approved_by: {approved_by}', f'created: {day}', 'status: active']
    if cand.get('private'):
        fm.append('private: true')
    text = '\n'.join(fm + ['---', '', f'# {cand["title"]}', '', cand['body'], '',
                           f'Herkunft: JARVIS-Auftrag `{ev.get("job")}` Revision {ev.get("revision")}, unabhängige Abnahme bestanden.', ''])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(text)
    return path
