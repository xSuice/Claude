#!/usr/bin/env python3
"""Graph-Analyse: Notizen ohne eingehende bzw. ausgehende Wikilinks (alle .md, inkl. _Claude-Memory und raw). Nur lesend."""
import os, re, collections, sys
V = r"C:\Users\andre\Documents\Obsidian Vault"
SKIP = {".obsidian", ".smart-connections", ".smart-env"}
md = []
for root, dirs, files in os.walk(V):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if f.lower().endswith(".md"):
            md.append(os.path.join(root, f))
rel = lambda p: os.path.relpath(p, V).replace("\\", "/")
by_base = collections.defaultdict(list)
by_path = {}
for p in md:
    by_base[os.path.basename(p)[:-3].lower()].append(p)
    by_path[rel(p)[:-3].lower()] = p
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
inb = collections.Counter(); outb = collections.Counter()
for p in md:
    try:
        t = open(p, encoding="utf-8").read()
    except Exception:
        continue
    for m in LINK.finditer(t):
        tg = m.group(1).strip().replace("\\", "/")
        key = tg.lower()
        tgt = by_path.get(key) or (by_base.get(key.split("/")[-1]) or [None])[0]
        if tgt and tgt != p:
            inb[tgt] += 1; outb[p] += 1
no_in = [p for p in md if inb[p] == 0]
no_out = [p for p in md if outb[p] == 0]
def top(lst):
    c = collections.Counter("/".join(rel(p).split("/")[:3]) for p in lst)
    return c.most_common(14)
print("Notizen gesamt:", len(md))
print("ohne eingehenden Link:", len(no_in)); [print("  ", n, k) for k, n in top(no_in)]
print("ohne ausgehenden Link:", len(no_out)); [print("  ", n, k) for k, n in top(no_out)]
if len(sys.argv) > 1:
    open(sys.argv[1], "w", encoding="utf-8").write("\n".join(rel(p) for p in no_in) + "\n---\n" + "\n".join(rel(p) for p in no_out))
