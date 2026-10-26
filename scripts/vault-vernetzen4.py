#!/usr/bin/env python3
"""Graph weiter verdichten: Roharchive (Vor-/Folgemonat, Gegenquelle), Geschwister-Ketten fuer duenn vernetzte Notizen. Additiv."""
import os, re, glob, collections
V = r"C:\Users\andre\Documents\Obsidian Vault"
M = os.path.join(V, "_Claude-Memory", "Import")
rel = lambda p: os.path.relpath(p, V).replace("\\", "/")
def lk(p): r = rel(p)[:-3]; return f"[[{r}|{os.path.basename(r)}]]"
def add(p, items, title="## Vernetzt"):
    s = open(p, encoding="utf-8").read()
    if title in s or not items: return 0
    open(p, "a", encoding="utf-8").write(f"\n\n{title}\n" + " · ".join(items) + "\n"); return 1

n = 0
# --- Roharchive: Vor/Folgemonat + Gegenquelle + andere Rohform
raw = {}
for src in ("raw", "raw-voll"):
    for who in ("ChatGPT", "DeepSeek", "Gemini"):
        for p in glob.glob(os.path.join(M, src, who, "*.md")):
            raw[(src, who, os.path.basename(p)[:-3])] = p
for (src, who, ym), p in raw.items():
    months = sorted(k[2] for k in raw if k[0] == src and k[1] == who)
    i = months.index(ym); items = []
    if i > 0: items.append("Vorher " + lk(raw[(src, who, months[i - 1])]))
    if i < len(months) - 1: items.append("Danach " + lk(raw[(src, who, months[i + 1])]))
    other = "raw-voll" if src == "raw" else "raw"
    if (other, who, ym) in raw: items.append("Andere Rohform " + lk(raw[(other, who, ym)]))
    for w2 in ("ChatGPT", "DeepSeek"):
        if w2 != who and (src, w2, ym) in raw: items.append(f"{w2} im selben Monat " + lk(raw[(src, w2, ym)]))
    n += add(p, items)

# --- Geschwister-Ketten in bearbeitbaren Bereichen
EXC = ("Archiv-Andrew-2026-10-07", "Arduino/libraries", "KI-Tools/fixmyprompt", "Server-Archiv", "/Import/raw", "Altbestand", "KI-Exporte", "Mod 1.21.4", "Welten", "Archive/", "Software/")
by_dir = collections.defaultdict(list)
for root, dirs, files in os.walk(V):
    dirs[:] = [d for d in dirs if d not in (".obsidian", ".smart-connections", ".smart-env")]
    for f in files:
        if f.lower().endswith(".md"):
            p = os.path.join(root, f)
            if not any(e in rel(p) for e in EXC) and "/Import/ChatGPT/" not in rel(p) and "/Import/DeepSeek/" not in rel(p):
                by_dir[os.path.dirname(p)].append(p)
for d, lst in by_dir.items():
    lst.sort()
    if len(lst) < 3: continue
    for i, p in enumerate(lst):
        prev, nxt = lst[i - 1], lst[(i + 1) % len(lst)]
        n += add(p, [lk(prev), lk(nxt)] if prev != nxt else [lk(prev)], "## Nachbarn")
print("Notizen verdichtet:", n)
