#!/usr/bin/env python3
"""Graph verdichten: zusammengehoerige Notizen verlinken sich gegenseitig (Cluster-Vollvernetzung), jede Notiz hat mehrere Kanten.
Nur additiv (Abschnitt '## Vernetzt'), nichts geloescht."""
import os, glob
V = r"C:\Users\andre\Documents\Obsidian Vault"
M = os.path.join(V, "_Claude-Memory")
def P(*a): return os.path.join(M, *a)
def lk(path):
    r = os.path.relpath(path, V).replace("\\", "/")[:-3]
    return f"[[{r}|{os.path.basename(r)}]]"
def add(path, others, extra=()):
    s = open(path, encoding="utf-8").read()
    if "## Vernetzt" in s:
        return 0
    items = [lk(o) for o in others if os.path.abspath(o) != os.path.abspath(path) and os.path.exists(o)] + list(extra)
    if not items:
        return 0
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\n## Vernetzt\n" + " · ".join(items) + "\n")
    return 1

core = [P("Index.md"), P("Profil.md"), os.path.join(V, "Übersicht.md")]
n = 0
# Cluster 1: Dienste und Fristen
dienste = [P("Dienste", x) for x in ("Verbundene-Dienste.md", "Termine-und-offene-Vorgaenge.md", "Mail-Zeitleiste.md", "Mail-Index-GMX.md",
           "Mail-Index-Gmail-Hotmail-Kalender.md", "Mail-Index-GMX1-INBOX-vollstaendig.md", "Dateien-Drive-Dropbox.md", "Fristen-Uebersicht.md")]
lebens = [os.path.join(V, "10 Leben", "Leben overview.md")]
for p in dienste:
    n += add(p, dienste + core + lebens)
# Jahresdateien GMX1: mit Hauptdatei + Zeitleiste
for p in glob.glob(P("Dienste", "Mail-Index-GMX1-20*.md")):
    n += add(p, [P("Dienste", "Mail-Index-GMX1-INBOX-vollstaendig.md"), P("Dienste", "Mail-Zeitleiste.md"), P("Dienste", "Fristen-Uebersicht.md")])
# Cluster 2: Chat-Importe
imp = [P("Import", x) for x in ("ChatGPT-Import.md", "ChatGPT-Index.md", "ChatGPT-Erinnerung-Vorschlaege.md", "DeepSeek-Import.md", "DeepSeek-Index.md", "Gemini-Index.md", "Roharchiv.md")]
for p in imp:
    n += add(p, imp + core)
# Cluster 3: Gedaechtnis-Kern, Regeln, Einrichtung
kern = [P("Index.md"), P("Profil.md"), P("Decisions.md"), P("Lessons-Learned.md"), P("Current-Projects.md"), P("Learned", "Librarian-Learned.md"), P("Learned", "MA-Server-Learned.md"),
        P("Abschlussbericht-Einrichtung-2026-10-10.md"), P("Archiv", "Einrichtungsauftrag-v2-2026-10-09.md"), os.path.join(V, "Übersicht.md"), os.path.join(V, "Wikilinks.md"), os.path.join(V, "CLAUDE.md")]
for p in kern:
    if os.path.exists(p):
        n += add(p, [k for k in kern if k != p][:8] + [], extra=[])
# Abschlussbericht verbindet alles
ab = P("Abschlussbericht-Einrichtung-2026-10-10.md")
if os.path.exists(ab):
    s = open(ab, encoding="utf-8").read()
    if "## Vernetzt" not in s:
        pass
print("Notizen verdichtet:", n)
