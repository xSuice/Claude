"""Bridge mode 'gespraech' (marker GESPRAECH-MODE): schnelle Sprachantworten OHNE Werkzeuge, ohne Vault, ohne MCP.
Gemessen 28.10.: erstes Wort 3,6 s statt ~35 s (Lesemodus mit Vault-Suche). Idempotent, Backup *.bak-vor-gespraech-20261028."""
import ast, shutil
from pathlib import Path
p = Path('/usr/local/lib/ma-claude-bridge.py')
s = p.read_text(encoding='utf-8')
if 'GESPRAECH-MODE' in s:
    print('already patched'); raise SystemExit
a1 = "    'lesen': ('default', ['Read', 'Grep', 'Glob'] + READ_BASH),\n"
assert s.count(a1) == 1, 'a1'
s = s.replace(a1, a1 + "    # GESPRAECH-MODE: Sprachdialog. KEINE Werkzeuge (--tools ''), keine Settings/MCP, 1 Zug. Liest und aendert nichts.\n    'gespraech': ('default', []),\n")
a2 = "            sid = req.get('session')\n            if isinstance(sid, str) and SESSION.fullmatch(sid):\n                args += ['--resume', sid]\n"
assert s.count(a2) == 1, 'a2'
s = s.replace(a2, """            if req.get('mode') == 'gespraech':   # GESPRAECH-MODE: Argumente komplett ersetzen (nichts aus anderen Modi uebernehmen)
                args = [CLAUDE, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
                        '--model', model if req.get('model') in MODELS else 'haiku', '--tools', '', '--setting-sources', '',
                        '--strict-mcp-config', '--max-turns', '1', '--system-prompt', VOICE_SYS]
            else:
""" + ''.join('    ' + l + '\n' for l in a2.rstrip('\n').split('\n')))
a3 = "MODES = {\n"
assert s.count(a3) == 1
s = s.replace(a3, "VOICE_SYS = ('Du bist JARVIS, der persoenliche Assistent von Andre im MA-HOME. Du sprichst Deutsch, natuerlich und freundlich wie im Gespraech. '\n             'Antworte kurz (hoechstens drei Saetze), ohne Markdown, Listen, Emojis oder Links. Du hast in diesem Modus keinen Zugriff auf Dateien, '\n             'Notizen oder Werkzeuge; behaupte nie, etwas nachgesehen oder erledigt zu haben. Fuer Auftraege sagt Andre \"Neuer Auftrag\".')\n" + a3)
ast.parse(s)
b = p.with_name(p.name + '.bak-vor-gespraech-20261028')
if not b.exists():
    shutil.copy2(p, b)
p.write_text(s, encoding='utf-8')
print('patched')
