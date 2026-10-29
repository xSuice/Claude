"""Chat-Weiche: Portal reicht den Gesprächskontext 'ctx' an die Bruecke durch (idempotent, Marker CHAT-ROUTE-CTX)."""
import sys
P = sys.argv[1]
s = open(P, encoding='utf-8').read()
if 'CHAT-ROUTE-CTX' in s:
    print('schon gepatcht'); sys.exit(0)
old = "    req = {k: body.get(k) for k in ('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files', 'attach', 'from')}"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "    req = {k: body.get(k) for k in ('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files', 'attach', 'from', 'ctx')}   # CHAT-ROUTE-CTX")
open(P, 'w', encoding='utf-8').write(s)
print('gepatcht')
