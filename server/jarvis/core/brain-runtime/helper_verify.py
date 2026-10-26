#!/usr/bin/env python3
"""V11.1 task-specific, deterministic verification of helper ANSWERS (no model call).

Separates three things V11 mixed up:
  infrastructure check  - e.g. "the diagnosis packet exists" (the step's check action): a precondition,
                          never evidence that an answer is right;
  answer verification   - this module: is the answer well-formed, non-suspicious and GROUNDED in the
                          evidence it was given (every quote must occur verbatim in the input)?
  repair                - only a sensor signal closes an anomaly; a diagnosis never does.

"grounded" is deliberately honest: it proves the helper cited real evidence lines instead of
inventing them; it does not prove the named cause is the true root cause. Verdicts are recorded per
call and are the only input to a helper's trust statistics.
"""
from __future__ import annotations

import json
import re

MIN_QUOTE = 12


def _json(text: str):
    t = text.strip()
    m = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', t, re.S)
    if m:
        t = m.group(1)
    return json.loads(t)


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def grounded(text: str, context: str) -> tuple[bool, str]:
    """{"cause": str (>= 10 chars), "evidence": [{"quote": str}, ...]} with >= 1 quote, each >= 12 chars
    and found verbatim (whitespace-normalised) in a non-heading line of the context."""
    try:
        d = _json(text)
    except (ValueError, TypeError):
        return False, 'not JSON'
    if not isinstance(d, dict) or not isinstance(d.get('cause'), str) or len(d['cause'].strip()) < 10:
        return False, 'no cause'
    ev = d.get('evidence')
    if not isinstance(ev, list) or not ev:
        return False, 'no evidence'
    body = _norm('\n'.join(ln for ln in context.splitlines() if not ln.lstrip().startswith('#')))
    for e in ev[:10]:
        q = e.get('quote') if isinstance(e, dict) else None
        if not isinstance(q, str) or len(q.strip()) < MIN_QUOTE:
            return False, 'quote too short'
        if _norm(q) not in body:
            return False, 'quote not in evidence (fabricated)'
    return True, f'grounded ({len(ev)} quotes)'


def verify(spec: dict | None, text: str, context: str, suspicious: bool) -> tuple[bool, str]:
    if suspicious:
        return False, 'suspicious (injection pattern)'
    if not text or not text.strip():
        return False, 'empty answer'
    spec = spec or {'type': 'grounded'}
    kind = spec.get('type')
    if kind == 'grounded':
        ok, why = grounded(text, context)
        want = [str(x).lower() for x in spec.get('cause_any', [])]
        if ok and want:   # canary cases know the true cause: grounded AND the cause names it
            cause = _json(text)['cause'].lower()
            if not any(w in cause for w in want):
                return False, 'grounded but wrong cause'
            why += ', cause matches'
        return ok, why
    if kind == 'contains':
        need = [str(x).lower() for x in spec.get('all', [])]
        miss = [x for x in need if x not in text.lower()]
        return (not miss and bool(need)), ('contains all' if not miss and need else f'missing {miss[:3]}')
    if kind == 'json_keys':
        try:
            d = _json(text)
        except (ValueError, TypeError):
            return False, 'not JSON'
        ok = isinstance(d, dict) and set(spec.get('keys', [])) <= set(d) and bool(spec.get('keys'))
        return ok, 'keys present' if ok else 'keys missing'
    return False, f'unknown verifier {kind!r}'   # fail closed


# Default verifier per helper task type. A task type without one can never be verified automatically.
DEFAULTS = {'diagnose_hint': {'type': 'grounded'}, 'summarize_log': {'type': 'grounded'}}
PROMPTS = {'grounded': ('Antworte NUR mit JSON {"cause": "<Ursache in einem Satz>", "evidence": '
                        '[{"quote": "<wörtlich kopierte Zeile aus dem Material>"}]}. '
                        'Nur Zeilen zitieren, die im Material wörtlich vorkommen.\n\nMaterial:\n')}
