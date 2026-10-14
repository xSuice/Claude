#!/usr/bin/env python3
"""V10.1 deterministic log digest: the expensive reading is done locally, not by Claude.

Reads only the tail of each log, keeps error/warning lines, normalises volatile parts
(timestamps, numbers, hex ids, UUIDs, IPs), groups identical messages with counts and
first/last example, ranks by severity then frequency, redacts secrets and stays within a
character budget. Output is Markdown for a diagnosis packet.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import redact  # noqa: E402

LEVELS = [('fatal', re.compile(r'(?i)\b(fatal|panic|emerg|alert|crit(ical)?)\b')),
          ('error', re.compile(r'(?i)\b(error|err|failed|failure|exception|traceback|denied|refused|segfault|oom)\b')),
          ('warn', re.compile(r'(?i)\b(warn(ing)?|timeout|timed out|retry|deprecated|unhealthy)\b'))]
RANK = {'fatal': 0, 'error': 1, 'warn': 2}
NORM = [(re.compile(r'\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:?\d\d)?'), '<ts>'),
        (re.compile(r'\b[A-Z][a-z]{2} +\d{1,2} \d\d:\d\d:\d\d\b'), '<ts>'),
        (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I), '<uuid>'),
        (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b'), '<ip>'),
        (re.compile(r'\b0x[0-9a-f]+\b|\b[0-9a-f]{12,}\b', re.I), '<hex>'),
        (re.compile(r'\b\d+\b'), '<n>')]
TAIL_BYTES = 2_000_000


def _level(line):
    for name, rx in LEVELS:
        if rx.search(line):
            return name
    return None


def _norm(line):
    for rx, rep in NORM:
        line = rx.sub(rep, line)
    return ' '.join(line.split())[:300]


def digest(paths: list[Path], max_chars: int = 4000, top: int = 25) -> dict:
    groups, read, matched, missing = {}, 0, 0, []
    for p in paths:
        p = Path(p)
        try:
            size = p.stat().st_size
            with open(p, 'rb') as fh:
                if size > TAIL_BYTES:
                    fh.seek(size - TAIL_BYTES); fh.readline()
                data = fh.read().decode('utf-8', 'replace')
        except OSError:
            missing.append(str(p)); continue
        for line in data.splitlines():
            read += 1
            lvl = _level(line)
            if not lvl:
                continue
            matched += 1
            key = (lvl, _norm(line))
            g = groups.setdefault(key, {'count': 0, 'first': line.strip()[:300], 'file': p.name})
            g['count'] += 1; g['last'] = line.strip()[:300]
    ranked = sorted(groups.items(), key=lambda kv: (RANK[kv[0][0]], -kv[1]['count']))[:top]
    out, used = [], 0
    for (lvl, _), g in ranked:
        line = f"- **{lvl}** ×{g['count']} ({g['file']}): `{redact(g['last'])}`"
        if used + len(line) > max_chars:
            break
        out.append(line); used += len(line) + 1
    return {'markdown': '\n'.join(out) or '- (keine Fehler- oder Warnzeilen gefunden)', 'lines_read': read,
            'lines_matched': matched, 'groups': len(groups), 'shown': len(out), 'chars': used, 'missing': missing}


TOKEN_RX = [re.compile(r'(?<![\d.])(?:0\.0\.0\.0|127\.0\.0\.1|\[::\])?:(\d{2,5})\b'),     # :8080
            re.compile(r'\bport[ =:]+(\d{2,5})\b', re.I),                                      # port 8080
            re.compile(r'(?<![\w.])(/(?:[\w.-]+/)*[\w.-]+)'),                                  # /DATA/backups/x
            re.compile(r'\b([a-z][\w-]*\.(?:service|socket|timer|lan|local|home))\b', re.I)]   # unit/host names
TEXT_EXT = {'.conf', '.cfg', '.ini', '.toml', '.yaml', '.yml', '.json', '.env.example', '.service', '.md', '.log',
            '.txt', '.properties', ''}


def tokens(lines: list[str], limit=8) -> list[str]:
    """Distinctive identifiers (ports, absolute paths, unit/host names) from error examples."""
    out = []
    for line in lines:
        for rx in TOKEN_RX:
            for m in rx.finditer(line):
                t = m.group(1)
                if t.startswith('/'):
                    t = t.rstrip('.,;:)')
                    parts = t.split('/')
                    if len(parts) > 3:
                        t = '/'.join(parts[:3])  # directory level is what configs mention
                    if t in ('/', '/tmp', '/usr', '/etc', '/var') or len(t) < 4:
                        continue
                if t not in out:
                    out.append(t)
    return out[:limit]


def correlate(toks: list[str], roots: list[Path], skip: set[str] = frozenset(), max_hits=12, max_files=300) -> list[str]:
    """Where else do these identifiers occur? file:line hits in configs and other logs (bounded)."""
    hits, seen, done = [], 0, set()
    for root in roots:
        for f in sorted(Path(root).rglob('*')):
            if seen >= max_files or len(hits) >= max_hits:
                break
            if f.resolve() in done:
                continue
            done.add(f.resolve())
            if not f.is_file() or f.is_symlink() or any(x.startswith('.') for x in f.relative_to(root).parts[:-1]) \
                    or f.suffix.lower() not in TEXT_EXT or str(f) in skip or f.stat().st_size > 1_000_000:
                continue
            seen += 1
            try:
                for n, line in enumerate(f.read_text('utf-8', 'replace').splitlines(), 1):
                    if any(re.search(r'(?<![\w])' + re.escape(t) + r'(?![\w])', line) for t in toks):
                        hits.append(f'{f.relative_to(root)}:{n}: {redact(line.strip())[:160]}')
                        if len(hits) >= max_hits:
                            break
            except OSError:
                continue
    return hits

if __name__ == '__main__':
    r = digest([Path(x) for x in sys.argv[1:]])
    print(r['markdown']); print(f"\n<!-- {r['lines_read']} Zeilen gelesen, {r['groups']} Gruppen -->")
