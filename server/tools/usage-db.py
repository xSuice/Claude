#!/usr/bin/env python3
"""usage-db: Verbrauch pro Aufgabe messbar machen (SQLite, nur Standardbibliothek, kein Eingriff in die Bruecke).
Liest die Sitzungsprotokolle der Claude-CLI (~/.claude/projects/*/*.jsonl), speichert NUR Zaehler (Zeit, Sitzung, Modell, Token), nie Text.
Aktualisiert sich selbst (nur geaenderte Dateien). Keine Preise: Kosten werden nicht geschaetzt, nur Token gezaehlt.

  usage-db report [--days 7] [--by day|model|project|session]   Token je Gruppe (Standard: je Tag)
  usage-db top [--days 7] [-n 5]                                  teuerste Sitzungen nach neu verarbeiteten Token
  usage-db windows [--days 7]                                     Verbrauch je 5-Stunden-Fenster (Naeherung) und groesstes Fenster
  usage-db stats                                                  Groesse und Zustand der Datenbank
Umgebung: MA_USAGE_DB (Datenbankdatei), MA_CLAUDE_PROJECTS (Protokollordner)
Spalten: Antw = Antworten, neu = input + Cache geschrieben (wirklich neu verarbeitet), Cache = aus dem Cache gelesen (billig), raus = Ausgabe."""
import argparse
import glob
import json
import os
import sqlite3
import time

JARVIS = '/srv/ma-home/library/.jarvis'
DB = os.environ.get('MA_USAGE_DB') or (os.path.join(JARVIS, 'usage.db') if os.path.isdir(JARVIS) else os.path.expanduser('~/.usage.db'))
PROJ = os.environ.get('MA_CLAUDE_PROJECTS') or os.path.expanduser('~/.claude/projects')


def connect():
    con = sqlite3.connect(DB, timeout=20)
    con.executescript('''
        CREATE TABLE IF NOT EXISTS msgs(id TEXT PRIMARY KEY, ts TEXT, day TEXT, session TEXT, project TEXT, model TEXT,
                                        inp INT, cache_r INT, cache_w INT, out INT, side INT);
        CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INT, mtime REAL);
        CREATE INDEX IF NOT EXISTS msgs_day ON msgs(day);
        CREATE INDEX IF NOT EXISTS msgs_session ON msgs(session);
    ''')
    return con


def refresh(con):
    """Liest nur neue oder geaenderte Protokolldateien. Eine Antwort kann mehrfach im Protokoll stehen (Streaming): die mit den meisten Ausgabetoken gilt."""
    known = {p: (s, m) for p, s, m in con.execute('SELECT path, size, mtime FROM files')}
    n_files = n_msgs = 0
    for f in glob.glob(os.path.join(PROJ, '*', '*.jsonl')):
        st = os.stat(f)
        if known.get(f) == (st.st_size, st.st_mtime):
            continue
        proj = os.path.basename(os.path.dirname(f))
        rows = {}
        with open(f, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = d.get('message')
                if d.get('type') != 'assistant' or not isinstance(m, dict) or not isinstance(m.get('usage'), dict) or not m.get('id'):
                    continue
                if m.get('model') == '<synthetic>':          # Platzhalter der CLI ohne echte Anfrage
                    continue
                u, ts = m['usage'], str(d.get('timestamp') or '')
                row = (m['id'], ts, ts[:10], str(d.get('sessionId') or os.path.basename(f)[:-6]), proj, str(m.get('model') or '?'),
                       int(u.get('input_tokens') or 0), int(u.get('cache_read_input_tokens') or 0),
                       int(u.get('cache_creation_input_tokens') or 0), int(u.get('output_tokens') or 0), 1 if d.get('isSidechain') else 0)
                if m['id'] not in rows or row[9] >= rows[m['id']][9]:
                    rows[m['id']] = row
        con.executemany('INSERT INTO msgs VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                        'out=MAX(out, excluded.out), inp=excluded.inp, cache_r=excluded.cache_r, cache_w=excluded.cache_w', rows.values())
        con.execute('INSERT OR REPLACE INTO files VALUES(?,?,?)', (f, st.st_size, st.st_mtime))
        n_files += 1
        n_msgs += len(rows)
    con.commit()
    return n_files, n_msgs


def fmt(n):
    n = int(n or 0)
    return '%.1f Mio' % (n / 1e6) if n >= 1e6 else ('%dk' % round(n / 1000) if n >= 1000 else str(n))


def since(days):
    return time.strftime('%Y-%m-%d', time.gmtime(time.time() - 86400 * max(days - 1, 0)))


def table(rows, head):
    w = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    for r in [head] + rows:
        print('  '.join(str(c).ljust(w[i]) if i == 0 else str(c).rjust(w[i]) for i, c in enumerate(r)))


def cmd_report(con, a):
    col = {'day': 'day', 'model': 'model', 'project': 'project', 'session': 'substr(session,1,8)'}[a.by]
    q = ('SELECT %s g, COUNT(*), SUM(inp+cache_w), SUM(cache_r), SUM(out) FROM msgs WHERE day >= ? GROUP BY g ORDER BY %s'
         % (col, 'g DESC' if a.by == 'day' else 'SUM(inp+cache_w+out) DESC'))
    rows = [(g, n, fmt(i), fmt(c), fmt(o)) for g, n, i, c, o in con.execute(q, (since(a.days),))]
    if not rows:
        print('Keine Daten im Zeitraum.')
        return
    t = con.execute('SELECT COUNT(*), SUM(inp+cache_w), SUM(cache_r), SUM(out) FROM msgs WHERE day >= ?', (since(a.days),)).fetchone()
    rows.append(('SUMME', t[0], fmt(t[1]), fmt(t[2]), fmt(t[3])))
    table(rows, (a.by, 'Antw', 'neu', 'Cache', 'raus'))


def cmd_top(con, a):
    q = ('SELECT substr(session,1,8), MIN(day), MAX(day), COUNT(*), SUM(inp+cache_w), SUM(cache_r), SUM(out), project FROM msgs '
         'WHERE day >= ? GROUP BY session ORDER BY SUM(inp+cache_w+out) DESC LIMIT ?')
    rows = [(s, d1 if d1 == d2 else d1 + '..' + d2[5:], n, fmt(i), fmt(c), fmt(o), p[-28:]) for s, d1, d2, n, i, c, o, p in con.execute(q, (since(a.days), a.n))]
    table(rows, ('Sitzung', 'Tag', 'Antw', 'neu', 'Cache', 'raus', 'Projekt')) if rows else print('Keine Daten im Zeitraum.')


def cmd_windows(con, a):
    """5-Stunden-Fenster: ein Fenster beginnt mit der ersten Antwort nach Ablauf des vorigen (Naeherung; die echte Zaehlung des Anbieters kennt dieses Werkzeug nicht)."""
    rows = con.execute('SELECT ts, model, inp+cache_w, cache_r, out FROM msgs WHERE day >= ? ORDER BY ts', (since(a.days),)).fetchall()
    wins, start = [], None
    for ts, model, n, c, o in rows:
        t = time.mktime(time.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S'))
        if start is None or t - start >= 5 * 3600:
            start = t
            wins.append([ts[:16].replace('T', ' '), 0, 0, 0, 0, 0])
        w = wins[-1]
        w[1] += 1; w[2] += n; w[3] += c; w[4] += o
        if 'opus' in model:
            w[5] += n + o
    if not wins:
        print('Keine Daten im Zeitraum.')
        return
    table([(w[0], w[1], fmt(w[2]), fmt(w[3]), fmt(w[4]), '%d%%' % (100 * w[5] / max(w[2] + w[4], 1))) for w in wins], ('Start (UTC)', 'Antw', 'neu', 'Cache', 'raus', 'Opus'))
    best = max(wins, key=lambda w: w[2] + w[4])
    print('Groesstes Fenster: %s mit %s neu + %s raus (%d Antworten)' % (best[0], fmt(best[2]), fmt(best[4]), best[1]))


def cmd_stats(con, a):
    n, d1, d2 = con.execute('SELECT COUNT(*), MIN(day), MAX(day) FROM msgs').fetchone()
    s = con.execute('SELECT COUNT(DISTINCT session) FROM msgs').fetchone()[0]
    print('Datenbank: %s (%.1f MB)\nAntworten: %d in %d Sitzungen, %s bis %s\nProtokolle: %s' % (DB, os.path.getsize(DB) / 1e6, n, s, d1, d2, PROJ))


def main():
    ap = argparse.ArgumentParser(prog='usage-db', description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('report'); s.add_argument('--days', type=int, default=7); s.add_argument('--by', choices=['day', 'model', 'project', 'session'], default='day'); s.set_defaults(f=cmd_report)
    s = sp.add_parser('top'); s.add_argument('--days', type=int, default=7); s.add_argument('-n', type=int, default=5); s.set_defaults(f=cmd_top)
    s = sp.add_parser('windows'); s.add_argument('--days', type=int, default=7); s.set_defaults(f=cmd_windows)
    s = sp.add_parser('stats'); s.set_defaults(f=cmd_stats)
    a = ap.parse_args()
    con = connect()
    nf, nm = refresh(con)
    if nf:
        print('(Index aktualisiert: %d Dateien, %d Antworten)' % (nf, nm))
    a.f(con, a)


if __name__ == '__main__':
    main()
