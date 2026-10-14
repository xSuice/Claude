#!/usr/bin/env python3
"""vault-pg: Vault-Index in PostgreSQL (Volltext tsvector/GIN deutsch, Vektorspalte pgvector). Parallelbetrieb zu vault-q (SQLite), gleiche Zonen und Schluessel.
Mehrere Nutzer/Sitzungen gleichzeitig: Lesen blockiert nie, der Abgleich laeuft unter einem Advisory-Lock (zweiter Aufruf ueberspringt ihn).

  vault-pg sync [--voll]                      Index abgleichen (nur geaenderte Dateien)
  vault-pg search "begriffe" [-n 8] [--zone vault|projekt|bib|alle] [--archiv]   Volltext mit Ausschnitt
  vault-pg show "Pfad.md" [--lines 10-40]     wie vault-q show
  vault-pg links "Notiz"                      ausgehende Links und Rueckverweise
  vault-pg stats                              Anzahl je Zone, Vektoren
Zugang: Datenbank vault, Benutzer vaultq, Passwort aus /etc/ma-home/vaultq.pgpass (nie ausgeben). Umgebung: MA_PG_PASSFILE, MA_PG_HOST."""
import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('vq', os.path.join(HERE, 'vault-q.py'))
vq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vq)                          # Wiederverwendung: Zonen, Scan, Parser, Stopwoerter

PASSFILE = os.environ.get('MA_PG_PASSFILE', '/etc/ma-home/vaultq.pgpass')
LOCK_ID = 727301

# Gewicht nach Bereich wie in vault-q (RANK): Archiv und Chat-Importe nach hinten, Gedaechtnis und Technik nach vorn
WEIGHTS = (('90 Archiv/', 0.35), ('_Claude-Memory/Import/', 0.5), ('20 Projekte/Projekt Schmejd/', 0.4), ('20 Projekte/Crimson Zone/', 0.4),
           ('30 Technik/Arduino/', 0.4), ('_Claude-Memory/Archiv/', 0.5), ('_Claude-Memory/', 1.3), ('30 Technik/', 1.3))


def weight(path):
    return next((w for pre, w in WEIGHTS if path.startswith(pre)), 1.0)


def connect():
    try:
        import psycopg
    except ImportError:
        sys.exit('python3-psycopg fehlt.')
    try:
        pw = open(PASSFILE).read().strip()
    except OSError as e:
        sys.exit('Passwortdatei nicht lesbar (%s). Gruppe ma-web? Skript server/postgres/pgpass-gruppe.sh.' % e.strerror)
    con = psycopg.connect(host=os.environ.get('MA_PG_HOST', 'localhost'), dbname='vault', user='vaultq', password=pw, autocommit=True, connect_timeout=5)
    con.execute("""
        CREATE TABLE IF NOT EXISTS notes(path text PRIMARY KEY, title text, mtime bigint, size bigint, archiv boolean, zone text, art text DEFAULT '', status text DEFAULT '',
                                         body text, tsv tsvector, emb vector(768));
        CREATE INDEX IF NOT EXISTS notes_tsv ON notes USING gin(tsv);
        CREATE INDEX IF NOT EXISTS notes_zone ON notes(zone);
        CREATE TABLE IF NOT EXISTS links(src text, name text);
        CREATE INDEX IF NOT EXISTS links_name ON links(name);
        CREATE INDEX IF NOT EXISTS links_src ON links(src);
        CREATE TABLE IF NOT EXISTS replaces(src text, name text);
        CREATE INDEX IF NOT EXISTS replaces_name ON replaces(name);
        CREATE TABLE IF NOT EXISTS tags(path text, tag text);
        CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
        CREATE TABLE IF NOT EXISTS qlog(ts bigint, query text, zone text, hits int, top text, ms int);
    """)
    return con


def cmd_sync(con, a):
    got = con.execute('SELECT pg_try_advisory_lock(%s)', (LOCK_ID,)).fetchone()[0]
    if not got:
        print('Abgleich laeuft schon (anderer Aufruf), uebersprungen.')
        return
    try:
        t0, n_ch, n_gone = time.time(), 0, 0
        for zone, root in vq.ZONES.items():
            if not root:
                continue
            disk = vq.scan_zone(zone, root)
            known = {} if a.voll else {p: (m, s) for p, m, s in con.execute('SELECT path, mtime, size FROM notes WHERE zone=%s', (zone,))}
            changed = [p for p, v in disk.items() if known.get(p) != v]
            gone = [p for p in known if p not in disk]
            with con.transaction():
                if a.voll:                              # in derselben Transaktion: parallele Suchen sehen nie eine leere Zone
                    con.execute('DELETE FROM notes WHERE zone=%s', (zone,))
                    con.execute('DELETE FROM links WHERE src = ANY(%s)', ([p for p in disk],))
                    con.execute('DELETE FROM tags WHERE path = ANY(%s)', ([p for p in disk],))
                    con.execute('DELETE FROM replaces WHERE src = ANY(%s)', ([p for p in disk],))
                for p in gone + changed:
                    for t, c in (('notes', 'path'), ('links', 'src'), ('tags', 'path'), ('replaces', 'src')):
                        con.execute('DELETE FROM %s WHERE %s=%%s' % (t, c), (p,))
                for p in changed:
                    m, s = disk[p]
                    try:
                        text = vq.read_key(p)
                    except OSError:
                        continue
                    text = text.replace('\x00', '')
                    rel = vq.split_key(p)[1]
                    name = os.path.splitext(os.path.basename(rel))[0]
                    title, links, tags = vq.parse(text) if (zone == 'vault' or rel.lower().endswith('.md')) else ('', set(), set())
                    art, status = (vq.fm_field(text, 'art'), vq.fm_field(text, 'status')) if zone == 'vault' else ('', '')
                    con.execute("""INSERT INTO notes(path,title,mtime,size,archiv,zone,art,status,body,tsv) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                   setweight(to_tsvector('german', unaccent(%s)),'A') || setweight(to_tsvector('german', unaccent(%s)),'D'))""",
                                (p, title or name, m, s, zone == 'vault' and p.startswith(vq.ARCHIV), zone, art, status, text, name + ' ' + title, text))
                    if zone == 'vault':
                        with con.cursor() as cur:
                            cur.executemany('INSERT INTO links VALUES(%s,%s)', [(p, l) for l in links])
                            cur.executemany('INSERT INTO tags VALUES(%s,%s)', [(p, t) for t in tags])
                        ers = vq.fm_field(text, 'ersetzt').strip('[] ').removesuffix('.md').lower()   # Frontmatter ersetzt: Notizname wertet die Zielnotiz ab
                        if ers:
                            con.execute('INSERT INTO replaces VALUES(%s,%s)', (p, ers))
            n_ch += len(changed)
            n_gone += len(gone)
        print('Abgleich: %d neu/geaendert, %d entfernt, %.1f s' % (n_ch, n_gone, time.time() - t0))
    finally:
        con.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))


def log_query(con, a, zone, rows, t0):
    """Anfrageprotokoll (Tabelle qlog, Klasse B). Aus mit MA_VQ_NOLOG=1; Fehler stoeren die Suche nie."""
    if os.environ.get('MA_VQ_NOLOG'):
        return
    try:
        con.execute('INSERT INTO qlog VALUES(%s,%s,%s,%s,%s,%s)', (int(time.time()), a.query[:300], zone, len(rows), '\n'.join(r[0] for r in rows[:5]), int((time.time() - t0) * 1000)))
    except Exception:
        pass


def cmd_report(con, a):
    n = con.execute('SELECT count(*) FROM qlog').fetchone()[0]
    if not n:
        return print('Noch keine Anfragen protokolliert.')
    first, zero, avg = con.execute('SELECT min(ts), count(*) FILTER (WHERE hits=0), avg(ms) FROM qlog').fetchone()
    print('Anfragen: %d seit %s | ohne Treffer: %d | mittlere Dauer: %d ms' % (n, time.strftime('%Y-%m-%d', time.localtime(first)), zero, avg))
    print('\nOhne oder mit nur einem Treffer (zuletzt):')
    for q, h in con.execute('SELECT query, hits FROM qlog WHERE hits<=1 ORDER BY ts DESC LIMIT %s', (a.n,)):
        print('  %d | %s' % (h, q))


def cmd_search(con, a):
    t0 = time.time()
    words = vq.query_words(a.query)
    if not words:
        sys.exit('Keine Suchbegriffe.')
    zone = 'alle' if a.alles else a.zone
    where = "tsv @@ to_tsquery('german', unaccent(%s))"
    extra, eargs = '', []
    if zone != 'alle':
        extra += ' AND zone=%s'
        eargs.append(zone)
    if not a.archiv:
        extra += ' AND NOT archiv'
    for col, val in (('art', a.art), ('status', a.status)):
        if val:
            extra += ' AND %s=%%s' % col
            eargs.append(val.lower())
    rows, seen = [], set()
    for op in (' & ', ' | '):                       # erst alle Begriffe (UND), bei zu wenigen Treffern ODER anhaengen (UND-Treffer bleiben)
        q = op.join(w.replace("'", '').replace(':', '') + ':*' for w in words)
        found = con.execute("""SELECT path, title, ts_rank_cd(tsv, to_tsquery('german', unaccent(%%s))) * CASE WHEN lower(status) IN ('veraltet','ungueltig','zurueckgezogen') OR lower(regexp_replace(path, '^.*/|\\.md$', '', 'g')) IN (SELECT name FROM replaces) THEN 0.3 ELSE 1.0 END AS r,
                              ts_headline('german', body, to_tsquery('german', unaccent(%%s)), 'MaxFragments=1,MaxWords=22,MinWords=8') AS snip
                              FROM notes WHERE %s%s ORDER BY r DESC LIMIT %%s""" % (where, extra), [q, q, q] + eargs + [a.n * 3]).fetchall()
        rows += [r for r in found if r[0] not in seen]
        seen.update(r[0] for r in found)
        if len(rows) >= 3 or len(words) == 1:
            break
    rows = sorted(rows, key=lambda r: -r[2] * weight(r[0]))[:a.n]
    log_query(con, a, zone, rows, t0)
    if not rows:
        print('Keine Treffer.')
    for p, title, r, snip in rows:
        print('%s | %s | %.2f | %s' % (p, title, r, ' '.join(snip.split())))


def cmd_show(con, a):
    row = con.execute('SELECT body FROM notes WHERE path=%s OR path LIKE %s ORDER BY length(path) LIMIT 1', (a.path, '%/' + a.path)).fetchone()
    if not row:
        sys.exit('Nicht gefunden: ' + a.path)
    lines = row[0].split('\n')
    lo, hi = 1, len(lines)
    if a.lines:
        lo, _, h = a.lines.partition('-')
        lo, hi = int(lo), int(h or lo)
    for i in range(max(lo, 1), min(hi, len(lines)) + 1):
        print('%4d  %s' % (i, lines[i - 1]))


def cmd_links(con, a):
    ref = a.note.removesuffix('.md').lower()
    row = con.execute("SELECT path FROM notes WHERE zone='vault' AND (lower(path)=%s OR lower(path) LIKE %s) ORDER BY length(path) LIMIT 1", (ref + '.md', '%/' + ref + '.md')).fetchone()
    if not row:
        sys.exit('Nicht gefunden: ' + a.note)
    out = [r[0] for r in con.execute('SELECT name FROM links WHERE src=%s ORDER BY name', (row[0],))]
    back = [r[0] for r in con.execute("SELECT src FROM links WHERE name=%s OR name=%s ORDER BY src", (ref, ref.rsplit('/', 1)[-1]))]
    print(row[0])
    print('-> ' + ', '.join(out) if out else '-> (keine)')
    print('<- ' + ', '.join(back) if back else '<- (keine)')


def cmd_stats(con, a):
    for z, n, v in con.execute('SELECT zone, count(*), count(emb) FROM notes GROUP BY zone ORDER BY zone'):
        print('%-8s %6d Notizen, %d Vektoren' % (z, n, v))
    print('Links: %d, Tags: %d' % (con.execute('SELECT count(*) FROM links').fetchone()[0], con.execute('SELECT count(*) FROM tags').fetchone()[0]))


def main():
    ap = argparse.ArgumentParser(description='Vault-Index in PostgreSQL')
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('sync'); s.add_argument('--voll', action='store_true'); s.set_defaults(f=cmd_sync)
    s = sp.add_parser('search'); s.add_argument('query'); s.add_argument('-n', type=int, default=8); s.add_argument('--archiv', action='store_true')
    s.add_argument('--zone', default='vault', choices=['vault', 'projekt', 'bib', 'alle']); s.add_argument('--alles', action='store_true')
    s.add_argument('--art', help='Frontmatter art: fakt|entscheidung|aufgabe|annahme'); s.add_argument('--status', help='Frontmatter status, z. B. gueltig|veraltet|offen|erledigt'); s.set_defaults(f=cmd_search)
    s = sp.add_parser('show'); s.add_argument('path'); s.add_argument('--lines'); s.set_defaults(f=cmd_show)
    s = sp.add_parser('links'); s.add_argument('note'); s.set_defaults(f=cmd_links)
    s = sp.add_parser('report'); s.add_argument('-n', type=int, default=15); s.set_defaults(f=cmd_report)
    s = sp.add_parser('stats'); s.set_defaults(f=cmd_stats)
    a = ap.parse_args()
    a.f(connect(), a)


if __name__ == '__main__':
    main()
