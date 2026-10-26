"""One place that decides what looks like a secret (input gate, logs, events, prompts, helper egress).

Two layers use the same rules: `has_secret()` refuses a request before anything is stored or sent, `redact()` blanks the
value wherever text is persisted or handed on. Natural sentences ("mein api key ist ...") are covered, not only `key: value`.
Rules are deliberately conservative about plain words: a value must look like a credential (letters plus digits/symbols,
a known provider prefix, a JWT/Bearer token, a private key block) unless it is written as an explicit `key: value`
assignment. A free word after "Passwort ist" without digit or symbol is NOT detected: regex cannot know it. That limit is
documented in docs/jarvis/JARVIS-REFERENZ-AUDIT-2026-10-15.md; the structural defences are the stored-redacted request and
the egress gate.
"""
from __future__ import annotations

import re

MASK = '[REDACTED]'
_KEY = (r'(?<![A-Za-z0-9])(?:api[\s_-]?key|apikey|access[\s_-]?key|secret(?:[\s_-]?key)?|(?:auth[\s_-]?)?token|'
        r'passw(?:or)?t|password|passphrase|kennwort|pwd|pw|authorization)')
# explicit assignment: key: value / key=value  (the historic rule; any value counts)
_EXPLICIT = re.compile(_KEY + r'\s*[:=]\s*["\'“„]?(?P<v>[^\s"\',;”]+)', re.I)
# sentence form: "... ist / is / lautet / war <value>"
_SENTENCE = re.compile(_KEY + r'\s+(?:ist|is|lautet|war|=)\s+["\'“„]?(?P<v>[^\s"\',;”]{6,})', re.I)
# bare form: "kennwort 7Gh!k2Lm9" (strictest value test)
_BARE = re.compile(_KEY + r'\s+["\'“„]?(?P<v>[^\s"\',;”]{8,})', re.I)
_BEARER = re.compile(r'\bbearer\s+(?P<v>[A-Za-z0-9._~+/=-]{16,})', re.I)
_PREFIX = re.compile(
    r'(?<![A-Za-z0-9])(?:sk-ant-[A-Za-z0-9_-]{10,}|sk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9_-]{20,}'
    r'|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}'
    r'|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*)'
    r'|-----BEGIN [A-Z ]*PRIVATE KEY-----(?:[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)?')
# long opaque token (only for the input gate: file paths or hashes in logs must stay readable)
_OPAQUE = re.compile(r'\b(?=[A-Za-z0-9_\-+/]*\d)(?=[A-Za-z0-9_\-+/]*[A-Za-z])[A-Za-z0-9_\-+/]{40,}\b')
_SYMBOL = re.compile(r'[!@#$%^&*+=?|~<>]')


def _credential_like(v: str, strict: bool) -> bool:
    if not re.search(r'[A-Za-z]', v) or '://' in v:
        return False
    has_digit = bool(re.search(r'\d', v))
    has_sym = bool(_SYMBOL.search(v))
    if not (has_digit or has_sym):
        return False
    if strict:  # bare "kennwort <value>": digit AND (symbol or mixed case)
        return has_digit and (has_sym or (re.search(r'[a-z]', v) and re.search(r'[A-Z]', v)))
    return True


def spans(text: str, min_explicit: int = 1) -> list[tuple[int, int]]:
    """Character ranges of secret values. `min_explicit`: shortest value that counts in `key: value` form
    (1 for redaction as before, 6 for refusing a request)."""
    out: list[tuple[int, int]] = []
    for m in _EXPLICIT.finditer(text):
        v = m.group('v')
        if len(v) >= min_explicit and not v.lower().startswith('bearer'):
            out.append(m.span('v'))
    for m in _SENTENCE.finditer(text):
        if _credential_like(m.group('v'), False):
            out.append(m.span('v'))
    for m in _BARE.finditer(text):
        if _credential_like(m.group('v'), True):
            out.append(m.span('v'))
    for m in _BEARER.finditer(text):
        if re.search(r'\d', m.group('v')):
            out.append(m.span('v'))
    out.extend(m.span() for m in _PREFIX.finditer(text))
    out.sort()
    merged: list[tuple[int, int]] = []
    for s, e in out:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return merged


def has_secret(text: str) -> bool:
    """Input gate: refuse before anything is stored, logged or sent."""
    return bool(spans(text, 6)) or bool(_OPAQUE.search(text))


def redact(text: str) -> str:
    """Blank every secret value; text without secrets is returned unchanged."""
    sp = spans(text)
    if not sp:
        return text
    parts, last = [], 0
    for s, e in sp:
        parts += [text[last:s], MASK]
        last = e
    parts.append(text[last:])
    return ''.join(parts)
