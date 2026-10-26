#!/usr/bin/env python3
"""Proof of concept after Aider's repo-map idea, stdlib only (ast): one compact line per top-level symbol instead of the file.
No tree-sitter, no networkx, no model call. Measures size only (characters, 4 chars ~ 1 token is a rough proxy, NOT a token count).
Usage: python3 -I repomap_poc.py <dir> [--budget CHARS] [--focus word,word]"""
import ast
import sys
from pathlib import Path


def symbols(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError):
        return []
    out = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(f'def {n.name}({", ".join(a.arg for a in n.args.args)})')
        elif isinstance(n, ast.ClassDef):
            meths = [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith('__')]
            out.append(f'class {n.name}: ' + ', '.join(meths[:12]) + (' ...' if len(meths) > 12 else ''))
    return out


def build(root: Path, budget: int, focus: set[str]):
    files = sorted(p for p in root.glob('*.py'))
    scored = []
    for p in files:
        syms = symbols(p)
        text = p.name + ' ' + ' '.join(syms)
        score = sum(text.casefold().count(w) for w in focus) if focus else 0
        scored.append((-score, p.name, p, syms))
    scored.sort()
    lines, used = [], 0
    for _, name, p, syms in scored:
        block = f'{name}\n' + '\n'.join('  ' + s for s in syms) + '\n'
        if used + len(block) > budget:
            continue
        lines.append(block)
        used += len(block)
    return ''.join(lines), sum(p.stat().st_size for p in files), len(files)


if __name__ == '__main__':
    root = Path(sys.argv[1])
    budget = int(sys.argv[sys.argv.index('--budget') + 1]) if '--budget' in sys.argv else 6000
    focus = set(sys.argv[sys.argv.index('--focus') + 1].split(',')) if '--focus' in sys.argv else set()
    text, raw, n = build(root, budget, focus)
    sys.stderr.write(f'files={n} raw_chars={raw} map_chars={len(text)} ratio={len(text) / raw:.3f}\n')
    print(text)
