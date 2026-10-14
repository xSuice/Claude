#!/usr/bin/env python3
"""Fixed retrieval comparison: V7 keyword recall vs V7.1 compound recall vs V8 vault FTS5.

Usage: python3 retrieval_compare.py [--v7-core PATH/brain_core.py]
Deterministic, offline, no model calls. Uses evals/retrieval-v8/fixture.json unchanged.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RT = HERE.parent
sys.path.insert(0, str(RT))
from knowledge_index import VaultIndex, _frontmatter, _excluded  # noqa: E402
import datetime as dt  # noqa: E402

FIXTURE = HERE / 'retrieval-v8' / 'fixture.json'


def load_core(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def score(results: list[list[str]], queries) -> dict:
    h1 = h3 = mrr = 0.0
    for got, q in zip(results, queries):
        exp = set(q['expect'])
        ranks = [i for i, s in enumerate(got, 1) if s in exp]
        if ranks:
            h1 += ranks[0] == 1; h3 += ranks[0] <= 3; mrr += 1 / ranks[0]
    n = len(queries)
    return {'hit@1': round(h1 / n, 3), 'hit@3': round(h3 / n, 3), 'mrr': round(mrr / n, 3)}


def run_brain(core, notes, queries, tmp):
    b = core.Brain(Path(tmp) / f'{core.__name__}.db', 'person-a', {'ma-home'})
    ids = {}
    for path, text in notes.items():
        meta, body = _frontmatter(text)
        if _excluded(meta, dt.date(2026, 10, 14)):
            continue  # fair baseline: same exclusions as V8
        r = b.propose('ma-home', Path(path).stem[:120], body.strip()[:4000], path)
        b.confirm(r['id']); ids[r['id']] = path
    out, chars, t = [], 0, time.perf_counter()
    for q in queries:
        res = b.recall('ma-home', q['q'], max_chars=1500, limit=4)
        out.append([ids[i['id']] for i in res['items']]); chars += res['chars']
    return out, chars, time.perf_counter() - t


def run_vault(notes, queries, tmp):
    vault = Path(tmp) / f'vault'
    for p, text in notes.items():
        f = vault / p; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, encoding='utf-8')
    vi = VaultIndex(Path(tmp) / f'idx.db', vault)
    vi.build(today=dt.date(2026, 10, 14))
    out, chars, t = [], 0, time.perf_counter()
    for q in queries:
        res = vi.search(q['q'], k=4, max_chars=1500)
        seen = []
        for i in res['items']:
            if i['source'] not in seen: seen.append(i['source'])
        out.append(seen); chars += res['chars']
    return out, chars, time.perf_counter() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--v7-core', type=Path, help='brain_core.py of the unchanged V7 package')
    ap.add_argument('--fixture', type=Path, default=FIXTURE)
    a = ap.parse_args()
    raw = a.fixture.read_bytes()
    fx = json.loads(raw)
    notes, queries, forbidden = fx['notes'], fx['queries'], set(fx['forbidden_everywhere'])
    report = {'fixture_sha256': hashlib.sha256(raw).hexdigest(), 'queries': len(queries), 'variants': {}}
    with tempfile.TemporaryDirectory() as tmp:
        variants = []
        if a.v7_core:
            variants.append(('V7 Stichwort', lambda: run_brain(load_core(a.v7_core, 'core_v7'), notes, queries, tmp)))
        variants.append(('V7.1 Stichwort+Komposita', lambda: run_brain(load_core(RT / 'brain_core.py', 'core_v71'), notes, queries, tmp)))
        variants.append(('V8 Vault-FTS5', lambda: run_vault(notes, queries, tmp)))
        for name, fn in variants:
            got, chars, secs = fn()
            m = score(got, queries)
            m.update({'kontext_zeichen_gesamt': chars, 'leere_antworten': sum(1 for g in got if not g),
                      'verbotene_treffer': sum(1 for g in got for s in g if s in forbidden),
                      'ms_gesamt': round(secs * 1000, 1)})
            report['variants'][name] = m
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
