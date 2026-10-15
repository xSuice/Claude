#!/usr/bin/env python3
"""Offline comparison of the old (raw keyword Jaccard) and new (normalised) template matcher. No model call, no cost.

Usage: python3 -I e2_matcher_eval.py <brain-runtime dir> <brain.db> [--json out.json]
Part A: leave-one-out on the real job history (read-only). Part B: fixed paraphrase pairs written BEFORE measuring.
It measures retrieval only (does the right template come back?), NOT token savings.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from learning import kw, norm_kw  # noqa: E402

THRESHOLD = 0.35


def old_score(req, tkw):
    a, b = kw(req), set(tkw)
    return len(a & b) / len(a | b) if a and b else 0.0


def new_score(req, tkw):
    a, b = norm_kw(kw(req)), norm_kw(tkw)
    return len(a & b) / len(a | b) if a and b else 0.0


def best(score, req, templates):
    top = None
    for t in templates:
        sc = score(req, t['kw'])
        if sc >= THRESHOLD and (top is None or sc > top[0]):
            top = (sc, t)
    return top


# ---- Part B: fixed before measuring (origin request -> paraphrase, expected match yes/no) ----
PAIRS = [
    ('Schreibe ein Python-Skript, das alle Primzahlen bis n ausgibt, mit Tests und README', 'Ich brauche ein Programm in Python, das die Primzahlen bis n ausgibt, bitte mit Tests und einer README', True),
    ('Erstelle eine CSV-Auswertung: Summe pro Kategorie als Python-Kommandozeilenwerkzeug mit Tests', 'Mach mir ein Python-Tool für die Kommandozeile, das eine CSV einliest und die Summen je Kategorie berechnet, inklusive Tests', True),
    ('Schreibe eine Funktion, die Texte in Kleinbuchstaben mit Bindestrich umwandelt (Slug), mit unittest', 'Bau eine Slug-Funktion: Text zu kleinbuchstaben mit Bindestrichen, bitte mit Unittests', True),
    ('Erstelle ein Word-Dokument mit einem Bericht über unsere Serverkosten und eine kurze Zusammenfassung', 'Schreib mir einen Bericht zu den Serverkosten als Word-Datei mit kurzer Zusammenfassung', True),
    ('Wandle die Markdown-Datei notizen.md in ein DOCX um mit pandoc', 'Konvertiere notizen.md nach Word (docx) mithilfe von pandoc', True),
    ('Schreibe ein Python-Skript, das aus einer JSON-Datei die Bestellungen pro Kunde zählt, mit Tests', 'Zähle in einer JSON-Datei die Bestellungen je Kunde, in Python, mit Tests', True),
    ('Erstelle eine Funktion zum Berechnen der Fibonacci-Folge bis n mit unittest und README', 'Programmiere die Fibonacci-Zahlen bis n als Funktion mit unittest-Tests und README', True),
    ('Schreibe ein Skript, das Wörter in einer Textdatei zählt, mit Tests', 'Erstelle ein Werkzeug, das die Wörter in einer Textdatei zählt, mit Tests', True),
    ('Schreibe ein Python-Skript, das alle Primzahlen bis n ausgibt, mit Tests und README', 'Schreibe ein Gedicht über den Herbst im Wald', False),
    ('Erstelle eine CSV-Auswertung: Summe pro Kategorie als Python-Kommandozeilenwerkzeug mit Tests', 'Erstelle ein Word-Dokument mit einem Brief an die Berufsschule', False),
    ('Wandle die Markdown-Datei notizen.md in ein DOCX um mit pandoc', 'Schreibe ein Python-Skript, das alle Primzahlen bis n ausgibt, mit Tests', False),
    ('Erstelle ein Word-Dokument mit einem Bericht über unsere Serverkosten und eine kurze Zusammenfassung', 'Zähle die Wörter in einer Textdatei mit einem Python-Skript und Tests', False),
    ('Schreibe eine Funktion, die Texte in Kleinbuchstaben mit Bindestrich umwandelt (Slug), mit unittest', 'Erstelle eine Funktion, die römische Zahlen in ganze Zahlen umwandelt, mit unittest', False),
    ('Schreibe ein Skript, das Wörter in einer Textdatei zählt, mit Tests', 'Wie sicher ist mein WLAN-Passwort und wie ändere ich es?', False),
]


def part_a(db):
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    tmpl = [{'id': r['id'], 'type': r['task_type'], 'src': r['source_job'], 'kw': json.loads(r['keywords'])}
            for r in c.execute("SELECT id,task_type,source_job,keywords FROM plan_templates")]
    jobs = [dict(r) for r in c.execute("SELECT id,request,task_type FROM jobs WHERE verdict='done' AND task_type IS NOT NULL "
                                       "AND task_type NOT LIKE 'improve.%' AND task_type<>'jarvis.usage_local'")]
    res = {}
    for name, fn in (('alt', old_score), ('neu', new_score)):
        r = {'jobs': 0, 'solvable': 0, 'right': 0, 'wrong_type': 0, 'none': 0, 'false_match_unsolvable': 0}
        for j in jobs:
            cands = [t for t in tmpl if t['src'] != j['id']]
            solvable = any(t['type'] == j['task_type'] for t in cands)
            top = best(fn, j['request'], cands)
            r['jobs'] += 1
            r['solvable'] += solvable
            if top is None:
                r['none'] += 1
            elif top[1]['type'] == j['task_type']:
                r['right'] += 1
            else:
                r['wrong_type'] += 1
                r['false_match_unsolvable'] += not solvable
        res[name] = r
    return res


def part_b():
    res = {}
    for name, fn in (('alt', old_score), ('neu', new_score)):
        tp = fp = fn_ = tn = 0
        detail = []
        for orig, para, want in PAIRS:
            hit = best(fn, para, [{'kw': sorted(kw(orig)), 'type': orig}]) is not None
            tp += want and hit
            fn_ += want and not hit
            fp += (not want) and hit
            tn += (not want) and not hit
            detail.append((hit, want))
        res[name] = {'positive_recall': f'{tp}/{tp + fn_}', 'false_positives': f'{fp}/{fp + tn}'}
    return res


if __name__ == '__main__':
    out = {'part_a_leave_one_out_real_history': part_a(sys.argv[2]), 'part_b_fixed_paraphrases': part_b(), 'threshold': THRESHOLD}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
