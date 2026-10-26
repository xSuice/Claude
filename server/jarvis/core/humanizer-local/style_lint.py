#!/usr/bin/env python3
"""Read-only, zero-LLM heuristic style hints for German and English prose.

Only heuristics: not an AI-generated-content classifier; never edits text.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

PHRASES = (
    (r"\bes ist wichtig zu beachten\b", "Vermutlich entbehrliche Einleitung"),
    (r"\bzusammenfassend lässt sich sagen\b", "Formelhafter Abschluss"),
    (r"\bin der heutigen schnelllebigen welt\b", "Allgemeine KI-Floskel"),
    (r"\babschließend kann man sagen\b", "Formelhafter Abschluss"),
    (r"\bit is important to note that\b", "Formulaic qualifier"),
    (r"\bin today.s fast.paced world\b", "Generic opening"),
    (r"\bin conclusion,?\b", "Formulaic conclusion"),
    (r"\bdelve into\b", "Possibly inflated wording"),
)


def lint(text: str) -> list[dict]:
    out: list[dict] = []
    in_fence = False
    fence_type = None
    in_frontmatter = False
    for number, line in enumerate(text.splitlines(), 1):
        if number == 1 and line.strip() == '---':
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == '---':
                in_frontmatter = False
            continue
        fence = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            token = fence.group(1)
            if not in_fence:
                in_fence, fence_type = True, token[0]
            elif token[0] == fence_type:
                in_fence, fence_type = False, None
            continue
        if in_fence or line.startswith('    ') or line.lstrip().startswith(('|', '>')):
            continue
        # Skip obvious inline code and URLs to limit accidental technical matches.
        plain = re.sub(r'`[^`]*`|https?://\S+', '', line)
        for pat, reason in PHRASES:
            if re.search(pat, plain, flags=re.I):
                out.append({'line': number, 'kind': 'phrase', 'hint': reason})
        # Advisory only; long technical lines and headings may be legitimate.
        for sentence in re.split(r'(?<=[.!?])\s+', plain):
            if len(sentence.split()) > 42:
                out.append({'line': number, 'kind': 'long_sentence', 'hint': 'Langen Satz auf Lesbarkeit prüfen'})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('file', type=Path)
    ap.add_argument('--json', action='store_true', help='Print machine-readable hints')
    args = ap.parse_args()
    raw = args.file.read_text(encoding='utf-8')
    issues = lint(raw)
    if args.json:
        print(json.dumps({'file': str(args.file), 'hints': issues}, ensure_ascii=False))
    else:
        for issue in issues:
            print(f"{args.file}:{issue['line']}: {issue['hint']}")
        if not issues:
            print('Keine heuristischen Auffälligkeiten gefunden (kein Qualitätsnachweis).')


if __name__ == '__main__':
    main()
