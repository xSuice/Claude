"""PRIO2 N4: Bruecke remember/memories (Anker-Patch auf eine Datei, Pfad als Argument; idempotent, Marker N4-BRIDGE)."""
import sys
P = sys.argv[1]
s = open(P, encoding='utf-8').read()
if 'N4-BRIDGE' in s:
    print('schon gepatcht'); sys.exit(0)
a1 = "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router', 'audit')  # JARVIS-COUNCILS"
assert s.count(a1) == 1
s = s.replace(a1, "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router', 'audit', 'memories')  # JARVIS-COUNCILS, N4-BRIDGE: memories (lesend)")
a2 = "    elif cmd == 'forget':\n"
assert s.count(a2) == 1
s = s.replace(a2, "    elif cmd == 'remember':                         # N4-BRIDGE: „Merk dir …“, im Portal per Ja bestätigt; Geheimnisprüfung in der Engine\n"
                  "        text = ' '.join(str(req.get('request') or '').split())\n"
                  "        if not 3 <= len(text) <= 500:\n"
                  "            return {'ok': False, 'error': 'Merktext leer oder laenger als 500 Zeichen'}\n"
                  "        who = re.sub(r'[^A-Za-z0-9._-]', '', user)[:40]\n"
                  "        if not who:\n"
                  "            return {'ok': False, 'error': 'Merken ohne bekannten Portal-Benutzer'}\n"
                  "        args = ['remember', '--text', text, '--by', 'portal:' + who]\n" + a2)
open(P, 'w', encoding='utf-8').write(s)
print('gepatcht')
