#!/usr/bin/env python3
"""Graph schliessen: jede Notiz in einen Hub einbinden, Roharchive mit Importnotizen und Hubs verknuepfen.
Archivierte Originale (Archiv-Andrew-2026-10-07), Drittanbieter-Dateien (Arduino-Bibliotheken, fixmyprompt, Mod-Server-Archive) werden
NICHT veraendert: sie werden nur von Hubs aus verlinkt. Nur additiv, nichts geloescht."""
import os, re, glob, collections
V = r"C:\Users\andre\Documents\Obsidian Vault"
rel = lambda p: os.path.relpath(p, V).replace("\\", "/")
def abs_(r): return os.path.join(V, *r.split("/"))
def mds(sub):
    out = []
    for root, dirs, files in os.walk(abs_(sub)):
        for f in files:
            if f.lower().endswith(".md"):
                out.append(os.path.join(root, f))
    return sorted(out)
def link(p, label=None):
    r = rel(p)[:-3]
    return f"[[{r}|{label or os.path.basename(r)}]]"
def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(t)
def append_once(p, marker, text):
    s = open(p, encoding="utf-8").read()
    if marker in s: return False
    open(p, "a", encoding="utf-8").write("\n" + text.strip("\n") + "\n"); return True

# ---------- Hubs fuer unverlinkte Gruppen
ard = mds("30 Technik/Arduino/libraries")
write(abs_("30 Technik/Arduino/Arduino.md"),
 "# Arduino\n\nSketches und Bibliotheken (Automaten-Projekt, Pumpensteuerung, Display). Drittanbieter-Dokumentation der Bibliotheken, unverändert. Übergeordnet: [[Technik]]\n\n"
 "## Bibliotheken (README)\n" + "\n".join("- " + link(p, rel(p).split("/")[3]) for p in ard) +
 "\n\n## Verwandt\n- Chat-Notizen zu den Projekten: [[2024-07-04 Arduino System Control and Display]] · [[2025-07-05 Schwimmerschalter Pumpe bleibt an]] · [[2025-06-12 Arduino Pumpe Steuerung]] · [[2025-07 DeepSeek Arduino Pumpe und Blender|DeepSeek Arduino Pumpe und Blender]]\n")
fm = mds("30 Technik/KI-Tools/fixmyprompt")
write(abs_("30 Technik/KI-Tools/fixmyprompt Hub.md"),
 "# fixmyprompt Hub\n\nKopie des Plugins fixmyprompt (Promptverbesserer, Drittanbieter). Aktiv ist das installierte Plugin unter `~/.claude/plugins`, nicht diese Kopie. Übergeordnet: [[Technik]]\n\n## Dateien\n" + "\n".join("- " + link(p) for p in fm) + "\n")
dateien = [p for p in mds("90 Archiv") if "Archiv-Andrew-2026-10-07" in p]
write(abs_("90 Archiv/Archiv-Dateien.md"),
 "# Archiv-Dateien\n\nIndex aller Notizen im Archiv-Paket vom 2026-10-07. Die Dateien bleiben unverändert (Manifest). Übergeordnet: [[Archiv]]\n\n" + "\n".join("- " + link(p) for p in dateien) + "\n")
raw = collections.defaultdict(list)
for src in ("raw", "raw-voll"):
    for p in mds("_Claude-Memory/Import/" + src):
        raw[src].append(p)
rh = ["# Roharchiv\n\nVollständige Chat-Texte (ChatGPT, DeepSeek, Gemini), nach Monat. **Nie komplett laden, nur gezielt suchen.** Datenklasse B, nur lokal. Übergeordnet: [[ChatGPT-Import]] · [[DeepSeek-Import]] · [[Gemini-Index]] · [[Index]]\n"]
for src, title in (("raw", "Nur deine Nachrichten"), ("raw-voll", "Vollständige Dialoge (Du und KI)")):
    rh.append(f"\n## {title}")
    for p in raw[src]:
        rh.append("- " + link(p, rel(p).split("/")[-2] + " " + os.path.basename(p)[:-3]))
write(abs_("_Claude-Memory/Import/Roharchiv.md"), "\n".join(rh) + "\n")

# ---------- bestehende Hubs ergaenzen
H = lambda r: abs_(r)
srv = mds("30 Technik/MA-Server/ChatGPT-Verlauf")
append_once(H("30 Technik/MA-Server/MA-Server.md"), "## Server-Chats (Notizen)", "## Server-Chats (Notizen)\n" + "\n".join("- " + link(p) for p in srv))
sa = mds("20 Projekte/Minecraft SMP24/Server-Archiv")
append_once(H("20 Projekte/Minecraft SMP24/Minecraft SMP24.md"), "## Server-Archiv (Dokumente)", "## Server-Archiv (Dokumente)\n" + "\n".join("- " + link(p) for p in sa))
bg = mds("30 Technik/Software")
append_once(H("30 Technik/Technik.md"), "## Weitere Hubs", "## Weitere Hubs\n[[Arduino]] · [[fixmyprompt Hub]] · [[MA-Server]]" + ("\nSoftware-Dokumentation: " + " · ".join(link(p) for p in bg) if bg else ""))
append_once(H("90 Archiv/Archiv.md"), "[[Archiv-Dateien]]", "Index aller Archiv-Notizen: [[Archiv-Dateien]]")
rv = mds("00 Inbox/Review/Leer") + mds("00 Inbox/Review/Duplikate")
append_once(H("00 Inbox/Review/Review.md"), "## Weitere Review-Notizen", "## Weitere Review-Notizen\n" + "\n".join("- " + link(p) for p in rv))
append_once(H("Übersicht.md"), "## Zentrale Dateien",
 "## Zentrale Dateien\n[[_Claude-Memory/Index|Claude-Memory Index]] · [[_Claude-Memory/Decisions|Entscheidungen]] · [[_Claude-Memory/Lessons-Learned|Lessons Learned]] · [[_Claude-Memory/Current-Projects|Aktuelle Projekte]] · [[Roharchiv]] · [[Wikilinks]] · [[Arduino]] · [[fixmyprompt Hub]] · [[Archiv-Dateien]]")
for moc in ("ChatGPT-Import", "DeepSeek-Import"):
    append_once(H(f"_Claude-Memory/Import/{moc}.md"), "[[Roharchiv]]", "Rohtext nach Monat: [[Roharchiv]]")
prof = H("_Claude-Memory/Profil.md")
append_once(prof, "## Verwandt", "## Verwandt\n[[Übersicht]] · [[Fristen-Uebersicht]] · [[Leben overview]] · [[Crimson Zone]] · [[Projekt Schmejd]] · [[MA-Server]] · [[Index]]")
append_once(H("CLAUDE.md"), "[[Übersicht]]", "Start: [[Übersicht]] · Gedächtnis: [[_Claude-Memory/Index|Index]] · [[_Claude-Memory/Profil|Profil]]")

# ---------- Roharchiv <-> Importnotizen (gleicher Monat)
imp = collections.defaultdict(list)
for src in ("ChatGPT", "DeepSeek"):
    for p in mds("_Claude-Memory/Import/" + src):
        imp[(src, os.path.basename(p)[:7])].append(p)
for src in ("raw", "raw-voll"):
    for p in raw[src]:
        who = rel(p).split("/")[-2]; ym = os.path.basename(p)[:-3]
        notes = imp.get((who, ym), [])
        txt = "## Verwandt\nÜbergeordnet: [[Roharchiv]] · " + f"[[{who}-Import]]" + (" · Notizen aus diesem Monat: " + " · ".join(f"[[{os.path.basename(n)[:-3]}]]" for n in notes) if notes else "")
        append_once(p, "## Verwandt", txt)
n_lnk = 0
for (who, ym), lst in imp.items():
    for p in lst:
        rr = f"_Claude-Memory/Import/raw/{who}/{ym}"
        rv_ = f"_Claude-Memory/Import/raw-voll/{who}/{ym}"
        if os.path.exists(abs_(rr + ".md")):
            if append_once(p, "Rohtext:", f"Rohtext: [[{rr}|nur deine Nachrichten {ym}]] · [[{rv_}|vollständig {ym}]]"): n_lnk += 1
print("Importnotizen mit Rohtext verlinkt:", n_lnk)

# ---------- ausgehende Links: Notizen ohne Link bekommen Elternhub (ausser archivierte/Drittanbieter-Dateien)
EXC = ("Archiv-Andrew-2026-10-07", "Arduino/libraries", "KI-Tools/fixmyprompt", "Server-Archiv", "Blender GIS", "ChatGPT-Verlauf", "node_modules", "/Import/raw")
PARENT = [("20 Projekte/Crimson Zone", "Crimson Zone"), ("20 Projekte/Projekt Schmejd", "Projekt Schmejd"), ("20 Projekte/Minecraft", "Minecraft SMP24"),
          ("20 Projekte", "Projekte"), ("10 Leben", "Leben overview"), ("40 Wissen", "Wissen"), ("80 Medien", "Medien"),
          ("30 Technik/MA-Server", "MA-Server"), ("30 Technik", "Technik"), ("00 Inbox/Review", "Review"), ("90 Archiv", "Archiv")]
LINK = re.compile(r"\[\[[^\]]+\]\]")
n_out = 0
for root, dirs, files in os.walk(V):
    dirs[:] = [d for d in dirs if d not in (".obsidian", ".smart-connections", ".smart-env", "_Claude-Memory")]
    for f in files:
        if not f.lower().endswith(".md"): continue
        p = os.path.join(root, f); r = rel(p)
        if any(x in r for x in EXC): continue
        try: t = open(p, encoding="utf-8").read()
        except Exception: continue
        if LINK.search(t): continue
        hub = next((h for pre, h in PARENT if r.startswith(pre)), None)
        if hub and os.path.basename(p)[:-3] != hub:
            open(p, "a", encoding="utf-8").write(f"\n\n## Verwandt\nÜbergeordnet: [[{hub}]]\n"); n_out += 1
print("Notizen mit Elternhub-Link ergänzt:", n_out)
print("fertig")
