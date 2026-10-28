"""PRIO2 N4: Portal-Whitelist /api/jarvis um remember + memories erweitern (Pfad als Argument, idempotent, Marker N4-PORTAL)."""
import sys
P = sys.argv[1]
s = open(P, encoding='utf-8').read()
if 'N4-PORTAL' in s:
    print('schon gepatcht'); sys.exit(0)
old = "'caps', 'learned', 'meta', 'kill', 'forget'):"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "'caps', 'learned', 'meta', 'kill', 'forget', 'remember', 'memories'):   # N4-PORTAL")
open(P, 'w', encoding='utf-8').write(s)
print('gepatcht')
