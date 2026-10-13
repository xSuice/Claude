#!/usr/bin/env python3
"""Vault pruefen: Verschiebe-Log (alles am Ziel?), kaputte Wikilinks/Embeds, verwaiste Notizen. Nur lesend."""
import os, re, csv, sys, collections
V = r"C:\Users\andre\Documents\Obsidian Vault"
LOG = r"C:\Users\andre\VaultBackup\organize-20261010-moves.csv"
SKIP_DIRS = {".obsidian", ".smart-connections", ".smart-env"}

# 1. Log pruefen
rows = list(csv.reader(open(LOG, encoding="utf-8")))[1:]
missing = [r for r in rows if r[0] != "secret" and not os.path.exists(r[2])]
print("Log:", len(rows), "Zeilen, fehlende Ziele:", len(missing))
for r in missing[:5]:
    print("  fehlt:", r[2])

# 2. Index aller Dateien
by_name = collections.defaultdict(list)   # basename ohne .md -> pfade (md) ; mit Ext fuer andere
allfiles = {}
md = []
for root, dirs, files in os.walk(V):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for f in files:
        p = os.path.join(root, f)
        if f.lower().endswith(".md"):
            by_name[f[:-3].lower()].append(p); md.append(p)
        by_name[f.lower()].append(p)
print("Markdown-Dateien:", len(md))

LINK = re.compile(r"(!?)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
broken = collections.defaultdict(list)
inbound = collections.Counter()
scan = [p for p in md if "\\_Claude-Memory\\Import\\raw" not in p]
for p in scan:
    try:
        t = open(p, encoding="utf-8").read()
    except Exception:
        continue
    for m in LINK.finditer(t):
        target = m.group(2).strip().replace("\\", "/").split("/")[-1].lower()
        if target in by_name:
            for q in by_name[target]:
                inbound[q] += 1
        elif target + ".md" in by_name or target[:-3] in by_name:
            pass
        else:
            broken[target].append(os.path.relpath(p, V))
print("Kaputte Links (verschiedene Ziele):", len(broken))
for k, v in sorted(broken.items(), key=lambda x: -len(x[1]))[:25]:
    print(f"  [[{k}]] x{len(v)}  z. B. {v[0]}")
orph = [p for p in scan if inbound[p] == 0 and "\\_Claude-Memory\\" not in p and not p.endswith("CLAUDE.md")]
print("Verwaiste Notizen (kein eingehender Link), ohne _Claude-Memory:", len(orph))
bydir = collections.Counter(os.path.relpath(os.path.dirname(p), V).split("\\")[0] for p in orph)
print(dict(bydir))
open(os.path.join(os.environ.get("TEMP", "."), "vault-orphans.txt"), "w", encoding="utf-8").write("\n".join(os.path.relpath(p, V) for p in orph))
