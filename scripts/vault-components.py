#!/usr/bin/env python3
"""Zusammenhangskomponenten des Vault-Graphen (alle .md, Wikilinks ungerichtet). Nur lesend.
Aufruf: python vault-components.py [fix]   (fix = Inseln per Hub-Link an das Hauptnetz anbinden)"""
import os, re, sys, collections
V = r"C:\Users\andre\Documents\Obsidian Vault"
SKIP = {".obsidian", ".smart-connections", ".smart-env"}
md = []
for root, dirs, files in os.walk(V):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if f.lower().endswith(".md"):
            md.append(os.path.join(root, f))
rel = lambda p: os.path.relpath(p, V).replace("\\", "/")
by_base = collections.defaultdict(list); by_path = {}
for p in md:
    by_base[os.path.basename(p)[:-3].lower()].append(p); by_path[rel(p)[:-3].lower()] = p
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
adj = collections.defaultdict(set)
for p in md:
    try: t = open(p, encoding="utf-8").read()
    except Exception: continue
    for m in LINK.finditer(t):
        k = m.group(1).strip().replace("\\", "/").lower()
        tg = by_path.get(k) or (by_base.get(k.split("/")[-1]) or [None])[0]
        if tg and tg != p:
            adj[p].add(tg); adj[tg].add(p)
seen = {}; comps = []
for p in md:
    if p in seen: continue
    stack = [p]; comp = []; seen[p] = len(comps)
    while stack:
        x = stack.pop(); comp.append(x)
        for y in adj[x]:
            if y not in seen: seen[y] = len(comps); stack.append(y)
    comps.append(comp)
comps.sort(key=len, reverse=True)
print("Notizen:", len(md), "| Gruppen:", len(comps), "| größte:", len(comps[0]))
small = comps[1:]
for c in small:
    top = max(c, key=lambda x: len(adj[x]))
    print(f"  Gruppe {len(c):3d} Notizen, Hub: {rel(top)}")
if len(sys.argv) > 1 and sys.argv[1] == "fix":
    main = set(comps[0])
    # Elternhub nach Ordner (liegt im Hauptnetz)
    PARENT = [("_Claude-Memory/Import/raw", "Roharchiv"), ("_Claude-Memory", "Index"), ("20 Projekte/Crimson Zone", "Crimson Zone"), ("20 Projekte/Projekt Schmejd", "Projekt Schmejd"),
              ("20 Projekte/Minecraft", "Minecraft SMP24"), ("20 Projekte", "Projekte"), ("10 Leben", "Leben overview"), ("40 Wissen", "Wissen"), ("80 Medien", "Medien"),
              ("30 Technik/MA-Server", "MA-Server"), ("30 Technik/Arduino", "Arduino"), ("30 Technik", "Technik"), ("00 Inbox", "Review"), ("90 Archiv", "Archiv-Dateien")]
    n = 0
    for c in small:
        top = max(c, key=lambda x: len(adj[x])); r = rel(top)
        hub = next((h for pre, h in PARENT if r.startswith(pre)), "Übersicht")
        hubp = by_base.get(hub.lower(), [None])[0]
        if hubp and hubp in main:
            line = f"\n- Weitere Gruppe: [[{r[:-3]}|{os.path.basename(r)[:-3]}]]"
            marker = "## Weitere Gruppen"
            t = open(hubp, encoding="utf-8").read()
            if marker not in t:
                open(hubp, "a", encoding="utf-8").write("\n\n## Weitere Gruppen" + line + "\n"); n += 1
            else:
                open(hubp, "a", encoding="utf-8").write(line.lstrip("\n") + "\n"); n += 1
    print("Inseln angebunden:", n)
