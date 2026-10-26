"""T03 generator: Markdown document with code blocks that contain '#' lines, duplicate headings and punctuation."""
import random
import re
from pathlib import Path

WORDS = ['Einleitung', 'Aufbau', 'Installation', 'Nutzung', 'Fehler', 'Übersicht', 'Größe', 'Ausblick', 'Daten', 'Tests', 'C# Beispiele', 'Fragen?', 'Hinweis: Rechte', 'Ä-Test']


def make(out: Path, seed: int, name: str = 'dokument.md') -> Path:
    rnd = random.Random(seed)
    lines = ['# Handbuch', '', '<!-- toc -->', '', '## Inhalt', '']
    for _ in range(rnd.randrange(8, 14)):
        lvl = rnd.choice([1, 2, 2, 3, 3, 4])
        lines += ['#' * lvl + ' ' + rnd.choice(WORDS), '', 'Text ohne Bedeutung.', '']
        if rnd.random() < 0.4:
            lines += ['```bash', '# Kommentar im Codeblock', '## auch das ist keine Überschrift', '```', '']
        if rnd.random() < 0.2:
            lines += ['#kein-leerzeichen', '#####  fünf Rauten', '']
    p = out / name
    out.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return p


def anchor(text: str) -> str:
    return re.sub(r'[^\w\- ]', '', text.lower()).replace(' ', '-')


def expected(path: Path) -> str:
    lines, fence, heads = path.read_text(encoding='utf-8').split('\n'), False, []
    for ln in lines:
        if ln.startswith('```'):
            fence = not fence
        m = None if fence else re.match(r'^(#{1,4}) (.+)$', ln)
        if m and m.group(2).strip() != 'Inhalt':
            heads.append((len(m.group(1)), m.group(2).strip()))
    seen, toc = {}, []
    for lvl, text in heads:
        a = anchor(text)
        n = seen.get(a, 0)
        seen[a] = n + 1
        toc.append('  ' * (lvl - 1) + f'- [{text}](#{a if n == 0 else f"{a}-{n}"})')
    out = []
    for ln in lines:
        out += toc if ln == '<!-- toc -->' else [ln]
    return '\n'.join(out)


def visible(out: Path):
    make(out, 1)
