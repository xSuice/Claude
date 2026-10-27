import io
p = 'build_port.py'
s = io.open(p, encoding='utf-8').read()
marker = 'OUT.write_text(code'
assert s.count(marker) == 1, s.count(marker)
fix = (
    "A = \"  const w = e.target.closest('.wl'); if (!w) return;\\n  try { const g = await loadGraph();\"\n"
    "assert code.count(A) == 1, 'globaler Wikilink-Handler nicht gefunden'\n"
    "code = code.replace(A, \"  const w = e.target.closest('.wl'); if (!w || w.closest('#vread')) return;   // Vault-Leser navigiert selbst\\n  try { const g = await loadGraph();\")\n"
)
s = s.replace(marker, fix + marker)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

a = 'js/app.js'
t = io.open(a, encoding='utf-8').read()
if 'closeViewer' not in t:
    t = t.replace("import * as V from './views.js';", "import { closeViewer } from './viewer.js';\nimport * as V from './views.js';", 1)
    o = "  host.onclick = null;"
    assert t.count(o) == 1
    t = t.replace(o, "  try { closeViewer(); } catch (e) { /* kein Viewer offen */ }\n  host.onclick = null;")
    io.open(a, 'w', encoding='utf-8', newline='\n').write(t)
print('gepatcht')
