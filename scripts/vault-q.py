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
  vault-q report [-n 15]                       Auswertung des Anfrageprotokolls (Tabelle qlog in der Index-Datei): Anfragen ohne Treffer, haeufige Woerter. Nur Vorschlaege.
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
        CREATE TABLE IF NOT EXISTS replaces(src TEXT, name TEXT);
        CREATE INDEX IF NOT EXISTS replaces_name ON replaces(name);
        CREATE TABLE IF NOT EXISTS qlog(ts INTEGER, query TEXT, zone TEXT, hits INTEGER, top TEXT, ms INTEGER);
        CREATE INDEX IF NOT EXISTS links_name ON links(name);
        CREATE INDEX IF NOT EXISTS links_src ON links(src);
        CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
    """)
    if 'zone' not in [r[1] for r in con.execute('PRAGMA table_info(notes)')]:      # aeltere Indexdatei erweitern
        con.execute("ALTER TABLE notes ADD COLUMN zone TEXT DEFAULT 'vault'")
    if 'art' not in [r[1] for r in con.execute('PRAGMA table_info(notes)')]:       # Schema-Felder: alles einmal neu einlesen
        con.execute("ALTER TABLE notes ADD COLUMN art TEXT DEFAULT ''")
        con.execute("ALTER TABLE notes ADD COLUMN status TEXT DEFAULT ''")
        con.execute('UPDATE notes SET mtime=0')
    return con


def fm_field(text, key):
    """Wert eines Frontmatter-Felds (kleingeschrieben) oder ''."""
    fm = re.match(r'---\n(.*?)\n---\n', text, re.S)
    m = re.search(r'^%s:\s*(.*)$' % key, fm.group(1), re.M) if fm else None
    return m.group(1).strip(' "\'').lower() if m else ''


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
            con.execute('DELETE FROM replaces WHERE src=?', (p,))
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
            art, status = (fm_field(text, 'art'), fm_field(text, 'status')) if zone == 'vault' else ('', '')
            con.execute('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?)', (p, title or name, m, s, int(zone == 'vault' and p.startswith(ARCHIV)), zone, art, status))
            con.execute('INSERT INTO fts(path, title, body) VALUES(?,?,?)', (p, name + ' ' + title, text))
            if zone == 'vault':                         # Links und Tags nur aus dem Vault (Graph), nicht aus Projektdoku
                con.executemany('INSERT INTO links VALUES(?,?)', [(p, l) for l in links])
                con.executemany('INSERT INTO tags VALUES(?,?)', [(p, t) for t in tags])
                ers = fm_field(text, 'ersetzt').strip('[] ').removesuffix('.md')       # Frontmatter ersetzt: Notizname wertet die Zielnotiz ab
                if ers:
                    con.execute('INSERT INTO replaces VALUES(?,?)', (p, ers))
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


STOP = set("""der die das den dem des ein eine einer eines einem einen und oder aber nicht kein keine ich du er sie es wir ihr mein meine meinen meinem meiner dein mich mir dich dir uns was wie wo wann warum wer welche welcher welches wieso ist sind war waren bin bist hat habe haben hatte hast wird werden wurde kann koennen muss soll sollte zu zum zur im in an am auf aus bei mit nach von vor fuer für über ueber um unter zwischen durch gegen ohne als auch noch schon nur so da dann denn dass ob wenn mal bitte gibt geht alles etwas vom hatten haetten hätten hattet wollen wollte sollen sollten koennte könnte können brauche brauchst brauchen wofuer wofür wozu weshalb nochmal eigentlich gesagt gemacht machen mache meinen meiner ihm ihn ihnen
the a an and or not of to in on for with is are was what how when where why who which my me i do does""".split())


def query_words(q):
    words = [w for w in re.findall(r'[\w-]{2,}', q, re.U) if w.lower() not in STOP]
    return words or re.findall(r'[\w-]{2,}', q, re.U)


def fts_query(q, mode='AND'):
    words = query_words(q)
    return (' %s ' % mode).join('"%s"*' % w.replace('"', '') for w in words) if words else ''


# Gewicht nach Bereich: Archiv und Chat-Importe nach hinten (bm25 ist negativ, kleinerer Betrag = schlechterer Rang)
RANK = ("bm25(fts, 0, 6.0, 1.0) * CASE WHEN n.path LIKE '90 Archiv/%' THEN 0.35 WHEN n.path LIKE '_Claude-Memory/Import/%' THEN 0.5 "
        "WHEN n.path LIKE '20 Projekte/Projekt Schmejd/%' OR n.path LIKE '20 Projekte/Crimson Zone/%' OR n.path LIKE '30 Technik/Arduino/%' THEN 0.4 "
        "WHEN n.path LIKE '_Claude-Memory/Archiv/%' THEN 0.5 "
        "WHEN n.path LIKE '_Claude-Memory/%' OR n.path LIKE '30 Technik/%' THEN 1.3 ELSE 1.0 END "
        "* CASE WHEN lower(n.status) IN ('veraltet','ungueltig','zurueckgezogen') "
        "OR lower(replace(replace(n.path, rtrim(n.path, replace(n.path, '/', '')), ''), '.md', '')) IN (SELECT name FROM replaces) THEN 0.3 ELSE 1.0 END")


def log_query(con, a, zone, out, t0):
    """Protokoll der Anfragen (Tabelle qlog, nur lokal in der Index-Datei, Klasse B). Aus mit MA_VQ_NOLOG=1; Fehler stoeren die Suche nie."""
    if os.environ.get('MA_VQ_NOLOG'):
        return
    try:
        con.execute('INSERT INTO qlog VALUES(?,?,?,?,?,?)', (int(time.time()), a.query[:300], zone, len(out), '\n'.join(l.split(' | ')[0] for l in out[:5]), int((time.time() - t0) * 1000)))
        con.commit()
    except sqlite3.Error:
        pass


def cmd_report(con, a):
    """Auswertung des Anfrageprotokolls. Macht nur Vorschlaege; Stoppwoerter und Gewichte aendert nur ein Mensch im Code."""
    n, = con.execute('SELECT COUNT(*) FROM qlog').fetchone()
    if not n:
        return print('Noch keine Anfragen protokolliert.')
    first, = con.execute('SELECT MIN(ts) FROM qlog').fetchone()
    zero, = con.execute('SELECT COUNT(*) FROM qlog WHERE hits=0').fetchone()
    avg, = con.execute('SELECT AVG(ms) FROM qlog').fetchone()
    print('Anfragen: %d seit %s | ohne Treffer: %d | mittlere Dauer: %d ms' % (n, time.strftime('%Y-%m-%d', time.localtime(first)), zero, avg))
    print('\nOhne oder mit nur einem Treffer (zuletzt):')
    for q, h in con.execute('SELECT query, hits FROM qlog WHERE hits<=1 ORDER BY ts DESC LIMIT ?', (a.n,)):
        print('  %d | %s' % (h, q))
    words = {}
    for (q,) in con.execute('SELECT query FROM qlog'):
        for w in {w.lower() for w in re.findall(r'[\w-]{2,}', q, re.U)} - STOP:
            words[w] = words.get(w, 0) + 1
    print('\nHaeufige Woerter in Anfragen (Kandidaten fuer Stoppwoerter, wenn sie nichts Inhaltliches sind):')
    print('  ' + ', '.join('%s (%d)' % kv for kv in sorted(words.items(), key=lambda kv: -kv[1])[:a.n * 2]))


def cmd_search(con, a):
    t0 = time.time()
    if not fts_query(a.query):
        return print('Keine Suchbegriffe.')
    zone = 'alle' if a.alles else a.zone
    where = ('' if a.archiv else 'AND n.archiv=0 ') + ('' if zone == 'alle' else "AND n.zone='%s' " % zone.replace("'", ''))
    params = []
    for col, val in (('art', a.art), ('status', a.status)):
        if val:
            where += 'AND n.%s=? ' % col
            params.append(val.lower())
    sql = ("SELECT f.path, n.title, n.mtime, snippet(fts, 2, '[', ']', ' ... ', 14) FROM fts f JOIN notes n ON n.path=f.path "
           "WHERE fts MATCH ? " + where + "ORDER BY " + RANK + " LIMIT ?")
    rows, seen, out = [], set(), []
    for mode in ('AND', 'OR'):                       # erst alle Begriffe, dann auffuellen mit einzelnen (Fragen in Umgangssprache)
        if len(rows) >= a.n:
            break
        q = fts_query(a.query, mode)
        rows += [r for r in con.execute(sql, (q, *params, a.n * 3)).fetchall() if r[0] not in {x[0] for x in rows}]
    for p, t, m, snip in rows:
        sig = (os.path.basename(p).lower(), t.lower())
        if sig in seen:                              # gleicher Dateiname und Titel (z. B. Archiv-Kopien) nur einmal
            continue
        seen.add(sig)
        out.append('%s | %s | %s | %s' % (p, t[:60], time.strftime('%Y-%m-%d', time.localtime(m / 1e6)), ' '.join(snip.split())[:170]))
        if len(out) >= a.n:
            break
    print('\n'.join(out) if out else 'Nichts gefunden' + ('' if a.archiv else ' (Roharchiv: --archiv).') + (' Nur Vault; --alles fuer Projekt und Bibliothek.' if zone == 'vault' else ''))
    log_query(con, a, zone, out, t0)


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
    s.add_argument('--zone', choices=['vault', 'projekt', 'bib', 'alle'], default='vault'); s.add_argument('--alles', action='store_true', help='Vault, Projekt und Bibliothek')
    s.add_argument('--art', help='Frontmatter art: fakt|entscheidung|aufgabe|annahme'); s.add_argument('--status', help='Frontmatter status, z. B. gueltig|veraltet|offen|erledigt'); s.set_defaults(f=cmd_search)
    s = sp.add_parser('links'); s.add_argument('note'); s.set_defaults(f=cmd_links)
    s = sp.add_parser('near'); s.add_argument('note'); s.add_argument('-d', type=int, default=2); s.set_defaults(f=cmd_near)
    s = sp.add_parser('tags'); s.add_argument('tag', nargs='?'); s.set_defaults(f=cmd_tags)
    s = sp.add_parser('show'); s.add_argument('path'); s.add_argument('--lines'); s.add_argument('--head', type=int); s.set_defaults(f=cmd_show)
    s = sp.add_parser('recent'); s.add_argument('-n', type=int, default=10); s.set_defaults(f=cmd_recent)
    s = sp.add_parser('export-neo4j'); s.add_argument('dir', nargs='?', default='neo4j-export'); s.set_defaults(f=cmd_neo4j)
    s = sp.add_parser('stats'); s.set_defaults(f=cmd_stats)
    s = sp.add_parser('report'); s.add_argument('-n', type=int, default=15); s.set_defaults(f=cmd_report)
    a = ap.parse_args()
    con = connect()
    refresh(con)
    a.f(con, a)


if __name__ == '__main__':
    main()
