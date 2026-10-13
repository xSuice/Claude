import os, subprocess

M = '30 Technik/MA-Server/'
C = M + 'ChatGPT-Verlauf/MA-Server/'
D = '_Claude-Memory/Dienste/'
GOLD = [
    ('wie starte ich den Server neu', [M + 'MA-Server Zentrale.md', C + 'RUNBOOK.md', M + 'MA-Server SSH-Zugriff.md']),
    ('was ist Portainer und wofür brauche ich das', ['30 Technik/KI-Tools/Addons/ADDONS-UND-VERBINDUNGEN.md']),
    ('wie funktioniert der Abgleich zwischen PC und Server', [D + 'Server-Abgleich.md', '_Claude-Memory/Auto-Memory/server-abgleich-pruefen.md', M + 'MA-Server Zentrale.md', D + 'Paritaet.md']),
    ('wie komme ich von außerhalb ins Heimnetz', [C + 'SERVER-STATUS.md', C + 'ARCHITECTURE.md', M + 'MA-Server Zentrale.md', M + 'MA-Server SSH-Zugriff.md']),
    ('wie funktioniert die Anmeldung mit Authelia', [M + 'MA-Server Zentrale.md', C + 'ARCHITECTURE.md', C + 'SERVER-STATUS.md', M + 'MA-Server Library.md']),
    ('was habe ich für ein Backup auf dem Server', [M + 'MA-Server Zentrale.md', C + 'SERVER-STATUS.md', D + 'Status.md', D + 'Server-Abgleich.md']),
    ('welche Docker Container laufen auf dem Server', [D + 'Status.md', C + 'SERVER-STATUS.md', C + 'ARCHITECTURE.md']),
    ('wie funktioniert Caddy bei mir', [C + 'ARCHITECTURE.md', C + 'SERVER-STATUS.md', M + 'MA-Server Library.md']),
    ('was ist mit dem Home Assistant', [C + 'ARCHITECTURE.md', C + 'SERVER-STATUS.md']),
    ('wie funktioniert die Bibliothek mit der Inbox', [M + 'MA-Server Library.md', M + 'MA-Server Zentrale.md']),
    ('wie funktioniert der Obsidian Bibliothekar', ['_Claude-Memory/Learned/Librarian-Learned.md', M + 'MA-Server Zentrale.md', '_Claude-Memory/Auto-Memory/ma-automation-librarian-pipeline.md']),
    ('was ist das Projekt Crimson Zone', ['20 Projekte/Crimson Zone/Crimson Zone.md', '20 Projekte/Projekte.md']),
    ('was ist Eternal Bonds', ['20 Projekte/Crimson Zone/Crimson Zone.md', '20 Projekte/Projekte.md']),
    ('wie bewerbe ich mich bei der Bundespolizei', ['10 Leben/Bewerbung/Bewerbungsunterlagen.md', '10 Leben/Bewerbung/Bundespolizei Einstellungstest.md', '10 Leben/Bewerbung/Bundespolizei Gesundheitsanforderungen.md']),
    ('was muss ich für den Einstellungstest lernen', ['10 Leben/Bewerbung/Bundespolizei Einstellungstest.md']),
    ('wie läuft meine Ausbildung zum Fachinformatiker', ['_Claude-Memory/Profil.md']),
    ('welche Fristen habe ich gerade', [D + 'Fristen-Uebersicht.md']),
    ('wie funktioniert der Kontext Wächter und die Übergabe', [C + 'HANDOFF.md', M + 'MA-Server Zentrale.md', C + 'TASK-POLICY.md']),
    ('wie funktioniert die externe KI ask.py', [D + 'Paritaet.md', M + 'MA-Server Zentrale.md', '_Claude-Memory/Abschlussbericht-Einrichtung-2026-10-10.md']),
    ('welche Hardware hat der Server', [C + 'SERVER-STATUS.md', C + 'ARCHITECTURE.md', C + 'HANDOFF.md']),
]
VER = {'alt': ('/srv/ma-home/library/vault-snapshots/wissen-vor-umbau-20261013-0921/vault-q.py', '/srv/ma-home/library/vault-snapshots/wissen-vor-umbau-20261013-0921/vault-index.db'), 'neu': ('/home/andrew/MA-Server/scripts/vault-q.py', '/srv/ma-home/library/.jarvis/vault-index.db')}
tot = {k: 0 for k in VER}
rr = {k: 0.0 for k in VER}
for q, exp in GOLD:
    row = []
    for k, (script, db) in VER.items():
        env = dict(os.environ, MA_VAULT_DB=db, MA_VQ_NOLOG='1')
        out = subprocess.run(['python3', script, 'search', q, '-n', '5'], capture_output=True, text=True, env=env).stdout
        paths = [l.split(' | ')[0] for l in out.splitlines()]
        rank = next((i + 1 for i, p in enumerate(paths) if p in exp), 0)
        tot[k] += bool(rank)
        rr[k] += 1 / rank if rank else 0
        row.append('%s:%s' % (k, rank or '-'))
    print('%-62s %s' % (q, '  '.join(row)))
n = len(GOLD)
for k in VER:
    print('%s: Treffer@5 %d/%d, MRR %.2f' % (k, tot[k], n, rr[k] / n))
