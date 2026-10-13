#!/usr/bin/env python3
"""vault-q: schnelle, sparsame Abfragen an den Obsidian-Vault (SQLite + FTS5, nur Standardbibliothek). Gleich am PC und auf dem Server.
Zweck: Claude liest nicht viele ganze Notizen, sondern fragt gezielt (Treffer mit Ausschnitt, Links, Nachbarn, Zeilenbereiche) und spart Tokens.
Der Index entsteht und aktualisiert sich selbst (nur geaenderte Dateien); der Vault wird nie veraendert.

  vault-q search "begriffe" [-n 8] [--archiv] [--zone vault|projekt|bib|alle | --alles]   Volltext (BM25), Treffer mit Ausschnitt
        Zonen: vault (Standard), projekt (Doku, Skripte, Code in MA-Server), bib (Texte/PDF der Bibliothek). Schluessel "projekt::Pfad" gilt auch fuer show.
  vault-q links "Notiz"                        ausgehende Links und Rueckverweise
  vault-q near "Notiz" [-d 2]                  Nachbarn im Link-Graphen bis zur Tiefe d
  vault-q tags [tag]                           Tags (Anzahl) oder Notizen mit einem Tag
  vault-q show "Pfad/Notiz.md" [--lines 10-40] [--head 30]   Teil einer Notiz mit Zeilennummern
  vault-q recent [-n 10]                       zuletzt geaenderte Notizen
  vault-q export-neo4j [Ordner]                CSV + Cypher-Skript fuer Neo4j (Graph aus Notizen, Links, Tags)
  vault-q stats                                Groesse und Zustand des Index
"Notiz" = Dateiname ohne .md oder Pfad. Umgebung: MA_VAULT (Vault-Ordner), MA_VAULT_DB (Index-Datei)."""
import argparse
import os
import re
import sqlite3
import sys
import time

CANDIDATES = [os.environ.get('MA_VAULT'), '/srv/ma-home/library/vault-notizen', r'C:\Users\andre\Documents\Obsidian Vault']
VAULT = next((p for p in CANDIDATES if p and os.path.isdir(p)), None)
JARVIS = '/srv/ma-home/library/.jarvis'
DB = os.environ.get('MA_VAULT_DB') or (os.path.join(JARVIS, 'vault-index.db') if os.path.isdir(JARVIS) else os.path.expanduser('~/.vault-index.db'))
ARCHIV = ('_Claude-Memory/Import',)                       # Roharchiv der Chats: nur mit --archiv durchsuchbar
# Weitere Wissensquellen (Zonen): Projektordner MA-Server (Doku, Skripte, Code) und Texte/PDFs der Bibliothek. Schluessel: "projekt::Pfad", "bib::Pfad".
PROJEKT = next((p for p in (os.environ.get('MA_PROJEKT'), '/home/andrew/MA-Server', r'C:\Users\andre\Documents\MA-Server') if p and os.path.isdir(p)), None)
BIB = next((p for p in (os.environ.get('MA_BIB'), '/srv/ma-home/library/documents') if p and os.path.isdir(p)), None)
ZONES = {'vault': VAULT, 'projekt': PROJEKT, 'bib': BIB}
CODE_EXT = ('.md', '.txt', '.py', '.sh', '.js', '.mjs', '.css', '.html', '.ps1', '.bat', '.java', '.xml', '.yml', '.yaml', '.toml', '.cmd')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'out', 'build', 'dist', 'signing', 'installer', 'setup', 'worktrees', '.router', 'server-konflikte'}
SECRET_HINT = ('token', 'passwort', 'password', 'apikey', 'api-key', 'secret', '.key', '.env', '.pass', 'credentials')
ZONE_MAX = 400_000                                        # Groesse je Datei in Projekt/Bibliothek
WIKI = re.compile(r'\[\[([^\]\n|#]+)(?:#[^\]\n|]*)?(?:\|[^\]\n]*)?\]\]')
HASHTAG = re.compile(r'(?:^|[\s(])#([^\W\d][\w/-]{1,40})')
MAX_BYTES = 2_000_000


def connect():
    if not VAULT:
        sys.exit('Vault nicht gefunden (MA_VAULT setzen).')
    os.makedirs(os.path.dirname(DB) or '.', exist_ok=True)
    con = sqlite3.connect(DB, timeout=20)
    con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS notes(path TEXT PRIMARY KEY, title TEXT, mtime INTEGER, size INTEGER, archiv INTEGER, zone TEXT DEFAULT 'vault');
        CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS links(src TEXT, name TEXT);
        CREATE TABLE IF NOT EXISTS tags(path TEXT, tag TEXT);
        CREATE INDEX IF NOT EXISTS links_name ON links(name);
        CREATE INDEX IF NOT EXISTS links_src ON links(src);
        CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
    """)
    if 'zone' not in [r[1] for r in con.execute('PRAGMA table_info(notes)')]:      # aeltere Indexdatei erweitern
        con.execute("ALTER TABLE notes ADD COLUMN zone TEXT DEFAULT 'vault'")
    return con


def strip_code(t):
    return re.sub(r'`[^`\n]*`', ' ', re.sub(r'```.*?```', ' ', t, flags=re.S))


def parse(text):
    fm = re.match(r'---\n(.*?)\n---\n', text, re.S)
    body = text[fm.end():] if fm else text
    plain = strip_code(body)
    links = {m.group(1).strip().lower() for m in WIKI.finditer(plain)}
    tags = {m.group(1) for m in HASHTAG.finditer(plain)}
    if fm:
        m = re.search(r'^tags:\s*(.*)$', fm.group(1), re.M)
        if m:
            tags |= {t.strip(' "\'#') for t in re.split(r'[,\[\]]', m.group(1)) if t.strip(' "\'#')}
    h1 = re.search(r'^#\s+(.+)$', body, re.M)
    return (h1.group(1).strip() if h1 else ''), links, tags


def key_of(zone, rel):
    return rel if zone == 'vault' else zone + '::' + rel


def split_key(key):
    z, sep, rel = key.partition('::')
    return (z, rel) if sep and z in ZONES else ('vault', key)


def scan_zone(zone, root):
    """Dateien einer Zone: {Schluessel: (mtime, size)}. Vault nur .md; Projekt Doku/Skripte/Code; Bibliothek Text und PDF."""
    exts = ('.md',) if zone == 'vault' else (CODE_EXT if zone == 'projekt' else ('.md', '.txt', '.pdf'))
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and (zone == 'vault' or d not in SKIP_DIRS)]
        for f in files:
            low = f.lower()
            if f.startswith('.') or not low.endswith(exts) or (zone != 'vault' and any(h in low for h in SECRET_HINT)):
                continue
            full = os.path.join(base, f)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if zone != 'vault' and st.st_size > (ZONE_MAX * 10 if low.endswith('.pdf') else ZONE_MAX):
                continue
            out[key_of(zone, os.path.relpath(full, root).replace(os.sep, '/'))] = (int(st.st_mtime_ns // 1000), st.st_size)
    return out


def read_key(key):
    """Text einer indizierten Datei (PDF ueber pdftotext, sonst UTF-8)."""
    zone, rel = split_key(key)
    full = os.path.join(ZONES[zone], *rel.split('/'))
    if full.lower().endswith('.pdf'):
        import subprocess
        try:
            return subprocess.run(['pdftotext', '-l', '40', '-layout', full, '-'], capture_output=True, timeout=60).stdout.decode('utf-8', 'replace')
        except (OSError, subprocess.SubprocessError):
            return ''
    with open(full, encoding='utf-8', errors='replace') as fh:
        return fh.read(MAX_BYTES)


def refresh(con):
    """Aktualisiert den Index inkrementell ueber alle Zonen; gibt (neu_oder_geaendert, entfernt) zurueck."""
    n_changed = n_gone = 0
    for zone, root in ZONES.items():
        if not root:
            continue
        on_disk = scan_zone(zone, root)
        known = {p: (m, s) for p, m, s in con.execute('SELECT path, mtime, size FROM notes WHERE zone=?', (zone,))}
        changed = [p for p, v in on_disk.items() if known.get(p) != v]
        gone = [p for p in known if p not in on_disk]
        for p in gone + changed:
            con.execute('DELETE FROM notes WHERE path=?', (p,))
            con.execute('DELETE FROM fts WHERE path=?', (p,))
            con.execute('DELETE FROM links WHERE src=?', (p,))
            con.execute('DELETE FROM tags WHERE path=?', (p,))
        for p in changed:
            m, s = on_disk[p]
            try:
                text = read_key(p)
            except OSError:
                continue
            rel = split_key(p)[1]
            name = os.path.splitext(os.path.basename(rel))[0]
            if zone == 'vault' or rel.lower().endswith('.md'):
                title, links, tags = parse(text)
            else:
                title, links, tags = '', set(), set()
            con.execute('INSERT INTO notes VALUES(?,?,?,?,?,?)', (p, title or name, m, s, int(zone == 'vault' and p.startswith(ARCHIV)), zone))
            con.execute('INSERT INTO fts(path, title, body) VALUES(?,?,?)', (p, name + ' ' + title, text))
            if zone == 'vault':                         # Links und Tags nur aus dem Vault (Graph), nicht aus Projektdoku
                con.executemany('INSERT INTO links VALUES(?,?)', [(p, l) for l in links])
                con.executemany('INSERT INTO tags VALUES(?,?)', [(p, t) for t in tags])
        n_changed += len(changed)
        n_gone += len(gone)
    con.commit()
    return n_changed, n_gone


def resolve(con, ref):
    """Notiz-Name oder Pfad -> Pfad (bei mehreren der kuerzeste)."""
    ref = ref.strip().replace('\\', '/')
    if ref.endswith('.md'):
        ref = ref[:-3]
    rows = [r[0] for r in con.execute("SELECT path FROM notes WHERE zone='vault' AND (lower(path)=lower(?) OR lower(path) LIKE lower(?))", (ref + '.md', '%/' + ref + '.md'))]
    return min(rows, key=len) if rows else None


def fts_query(q):
    words = re.findall(r'[\w-]{2,}', q, re.U)
    return ' '.join('"%s"*' % w.replace('"', '') for w in words) if words else ''


def cmd_search(con, a):
    qq = fts_query(a.query)
    if not qq:
        return print('Keine Suchbegriffe.')
    zone = 'alle' if a.alles else a.zone
    rows = con.execute("SELECT f.path, n.title, snippet(fts, 2, '[', ']', ' ... ', 18) FROM fts f JOIN notes n ON n.path=f.path "
                       "WHERE fts MATCH ? " + ('' if a.archiv else 'AND n.archiv=0 ') + ('' if zone == 'alle' else "AND n.zone='%s' " % zone.replace("'", '')) +
                       "ORDER BY bm25(fts, 0, 6.0, 1.0) LIMIT ?", (qq, a.n)).fetchall()
    if not rows:
        return print('Nichts gefunden' + ('' if a.archiv else ' (Roharchiv der Chats mit --archiv durchsuchen).') + ('' if zone != 'vault' else ' Nur im Vault gesucht; --alles durchsucht auch Projekt (MA-Server) und Bibliothek.'))
    for p, t, snip in rows:
        print('%s | %s | %s' % (p, t[:60], ' '.join(snip.split())[:200]))


def cmd_links(con, a):
    p = resolve(con, a.note)
    if not p:
        return print('Notiz nicht gefunden:', a.note)
    base = os.path.basename(p)[:-3].lower()
    out = [r[0] for r in con.execute('SELECT DISTINCT name FROM links WHERE src=? ORDER BY name', (p,))]
    back = [r[0] for r in con.execute('SELECT DISTINCT src FROM links WHERE (name=? OR name=?) AND src<>? ORDER BY src', (base, p[:-3].lower(), p))]
    print('Notiz:', p)
    print('Ausgehend (%d): %s' % (len(out), ', '.join(out[:40]) or '-'))
    print('Rueckverweise (%d): %s' % (len(back), ', '.join(back[:40]) or '-'))


def cmd_near(con, a):
    p = resolve(con, a.note)
    if not p:
        return print('Notiz nicht gefunden:', a.note)
    names = {}
    for path, in con.execute("SELECT path FROM notes WHERE zone='vault'"):
        names.setdefault(os.path.basename(path)[:-3].lower(), []).append(path)
    seen, frontier = {p: 0}, [p]
    for depth in range(1, a.d + 1):
        nxt = []
        for cur in frontier:
            base = os.path.basename(cur)[:-3].lower()
            targets = [min(names[n], key=len) for (n,) in con.execute('SELECT DISTINCT name FROM links WHERE src=?', (cur,)) if n.rsplit('/', 1)[-1] in names for n in [n.rsplit('/', 1)[-1]]]
            sources = [s for (s,) in con.execute('SELECT DISTINCT src FROM links WHERE name=? OR name=?', (base, cur[:-3].lower()))]
            for q in targets + sources:
                if q not in seen:
                    seen[q] = depth
                    nxt.append(q)
        frontier = nxt
    for q, d in sorted(seen.items(), key=lambda kv: (kv[1], kv[0])):
        if d:
            print('%d | %s' % (d, q))
    if len(seen) == 1:
        print('Keine verlinkten Nachbarn.')


def cmd_tags(con, a):
    if a.tag:
        for (p,) in con.execute('SELECT DISTINCT path FROM tags WHERE tag=? COLLATE NOCASE ORDER BY path LIMIT 100', (a.tag.lstrip('#'),)):
            print(p)
    else:
        for t, n in con.execute('SELECT tag, COUNT(DISTINCT path) c FROM tags GROUP BY tag ORDER BY c DESC LIMIT 60'):
            print('%s (%d)' % (t, n))


def cmd_show(con, a):
    ref = a.path.strip().replace('\\', '/')
    if '::' in ref and split_key(ref)[0] != 'vault':          # Projekt-/Bibliotheksdatei: Schluessel wie in der Suche ("projekt::CHANGELOG.md")
        p = ref if con.execute('SELECT 1 FROM notes WHERE path=?', (ref,)).fetchone() else None
    else:
        p = resolve(con, ref)
    if not p:
        return print('Datei nicht gefunden:', a.path)
    lines = read_key(p).splitlines()
    lo, hi = 1, len(lines)
    if a.lines:
        m = re.fullmatch(r'(\d+)-(\d+)', a.lines)
        if not m:
            return print('--lines erwartet von-bis, z. B. 10-40')
        lo, hi = max(1, int(m.group(1))), min(len(lines), int(m.group(2)))
    elif a.head:
        hi = min(len(lines), a.head)
    else:
        hi = min(len(lines), 80)
    print('%s (Zeilen %d-%d von %d)' % (p, lo, hi, len(lines)))
    for i in range(lo, hi + 1):
        print('%4d  %s' % (i, lines[i - 1][:300]))


def cmd_recent(con, a):
    for p, m in con.execute("SELECT path, mtime FROM notes WHERE archiv=0 AND zone='vault' ORDER BY mtime DESC LIMIT ?", (a.n,)):
        print('%s | %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(m / 1e6)), p))


def cmd_stats(con, a):
    n, = con.execute('SELECT COUNT(*) FROM notes').fetchone()
    l, = con.execute('SELECT COUNT(*) FROM links').fetchone()
    t, = con.execute('SELECT COUNT(DISTINCT tag) FROM tags').fetchone()
    z = ', '.join('%s %d' % (k, c) for k, c in con.execute('SELECT zone, COUNT(*) FROM notes GROUP BY zone ORDER BY zone'))
    print('Vault: %s\nProjekt: %s\nBibliothek: %s\nIndex: %s (%.1f MB)\nDateien: %d (%s) | Links: %d | Tags: %d' % (VAULT, PROJEKT, BIB, DB, os.path.getsize(DB) / 1e6, n, z, l, t))


def cmd_neo4j(con, a):
    """Schreibt notes.csv, links.csv, tags.csv und import.cypher; in den import-Ordner von Neo4j legen und das Skript ausfuehren."""
    import csv
    os.makedirs(a.dir, exist_ok=True)
    notes = {p: (t, m) for p, t, m in con.execute("SELECT path, title, mtime FROM notes WHERE archiv=0 AND zone='vault'")}
    names = {}
    for p in notes:
        names.setdefault(os.path.basename(p)[:-3].lower(), []).append(p)
    def out(name, header, rows):
        with open(os.path.join(a.dir, name), 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh); w.writerow(header); n = 0
            for r in rows:
                w.writerow(r); n += 1
        return n
    nn = out('notes.csv', ['path', 'title', 'mtime'], ((p, t, m // 1000000) for p, (t, m) in sorted(notes.items())))
    seen = set()
    def link_rows():
        for src, name in con.execute('SELECT src, name FROM links'):
            dst = names.get(name.rsplit('/', 1)[-1])
            if src in notes and dst:
                pair = (src, min(dst, key=len))
                if pair[0] != pair[1] and pair not in seen:
                    seen.add(pair); yield pair
    nl = out('links.csv', ['src', 'dst'], link_rows())
    nt = out('tags.csv', ['path', 'tag'], ((p, t) for p, t in con.execute('SELECT path, tag FROM tags') if p in notes))
    with open(os.path.join(a.dir, 'import.cypher'), 'w', encoding='utf-8') as fh:
        fh.write("CREATE CONSTRAINT note_path IF NOT EXISTS FOR (n:Note) REQUIRE n.path IS UNIQUE;\n"
                 "LOAD CSV WITH HEADERS FROM 'file:///notes.csv' AS r MERGE (n:Note {path: r.path}) SET n.title = r.title, n.mtime = toInteger(r.mtime);\n"
                 "LOAD CSV WITH HEADERS FROM 'file:///links.csv' AS r MATCH (a:Note {path: r.src}), (b:Note {path: r.dst}) MERGE (a)-[:LINKS_TO]->(b);\n"
                 "LOAD CSV WITH HEADERS FROM 'file:///tags.csv' AS r MATCH (n:Note {path: r.path}) MERGE (t:Tag {name: r.tag}) MERGE (n)-[:HAS_TAG]->(t);\n")
    print('Geschrieben in %s: %d Notizen, %d Links, %d Tag-Zuordnungen (+ import.cypher).' % (a.dir, nn, nl, nt))


def main():
    ap = argparse.ArgumentParser(prog='vault-q', description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('search'); s.add_argument('query'); s.add_argument('-n', type=int, default=8); s.add_argument('--archiv', action='store_true')
    s.add_argument('--zone', choices=['vault', 'projekt', 'bib', 'alle'], default='vault'); s.add_argument('--alles', action='store_true', help='Vault, Projekt und Bibliothek'); s.set_defaults(f=cmd_search)
    s = sp.add_parser('links'); s.add_argument('note'); s.set_defaults(f=cmd_links)
    s = sp.add_parser('near'); s.add_argument('note'); s.add_argument('-d', type=int, default=2); s.set_defaults(f=cmd_near)
    s = sp.add_parser('tags'); s.add_argument('tag', nargs='?'); s.set_defaults(f=cmd_tags)
    s = sp.add_parser('show'); s.add_argument('path'); s.add_argument('--lines'); s.add_argument('--head', type=int); s.set_defaults(f=cmd_show)
    s = sp.add_parser('recent'); s.add_argument('-n', type=int, default=10); s.set_defaults(f=cmd_recent)
    s = sp.add_parser('export-neo4j'); s.add_argument('dir', nargs='?', default='neo4j-export'); s.set_defaults(f=cmd_neo4j)
    s = sp.add_parser('stats'); s.set_defaults(f=cmd_stats)
    a = ap.parse_args()
    con = connect()
    refresh(con)
    a.f(con, a)


if __name__ == '__main__':
    main()
