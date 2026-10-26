#!/usr/bin/env python3
"""Hubs ergaenzen, Importnotizen mit Hubs verlinken, kaputte Querverweise reparieren. Nur additiv, nichts geloescht."""
import os, re, glob
V = r"C:\Users\andre\Documents\Obsidian Vault"
M = os.path.join(V, "_Claude-Memory")

def w(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)

def append_once(path, marker, text):
    s = open(path, encoding="utf-8").read()
    if marker in s:
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + text.strip("\n") + "\n")
    return True

def notes(sub):
    return sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(M, "Import", sub, "*.md")))

chat = notes("ChatGPT")
deep = notes("DeepSeek")
def pick(lst, *keys):
    return [n for n in lst if any(k.lower() in n.lower() for k in keys)]

# ---- neue Hubs
smp = pick(chat, "SMP", "Minecraft", "Faction", "Dynmap", "Weltgenerator", "Hosting", "NeoForge", "Avatar", "Modpack", "Wither") + pick(deep, "Minecraft")
w(os.path.join(V, "20 Projekte", "Minecraft SMP24", "Minecraft SMP24.md"),
  "# Minecraft SMP24\n\nMinecraft-Server-Projekte (AndrewSMP, SMP 2.0, Eternal-Bonds-Mod-Ideen). Übergeordnet: [[Projekte]] · [[Übersicht]]\n\n"
  "## Story und Konzept\n- [[Story von AndrewSMP24]]\n\n"
  "## Ordner\n- `Server-Archiv/` Server-Stände (Create Chronicles, Server, Test serv)\n- `Welten/` Welten (New World, Generated World)\n- `Archive/` ZIPs, Modpacks, Server-Dateien\n\n"
  "## Notizen aus Chat-Verläufen (ungeprüft)\n" + "\n".join(f"- [[{n}]]" for n in smp) +
  "\n\n## Verwandt\n- Mod-Entwicklung: [[Projekt Schmejd]] (Eternal Bonds Mod)\n- Übersicht der Importe: [[ChatGPT-Import]] · [[DeepSeek-Import]]\n")

srv = pick(chat, "Docker", "Ubuntu", "FileBrowser", "Serveros", "Installer", "Server Apps", "Serverzugriff", "Crossplattform", "MA Home", "Leichtes Server") + pick(deep, "Heimserver")
w(os.path.join(V, "30 Technik", "MA-Server", "MA-Server.md"),
  "# MA-Server\n\nHeimserver-Projekt (zuletzt ZimaOS). Aktueller Stand: `MA-Server/SERVER-STATUS.md` im Projektordner, nicht diese Notiz. Übergeordnet: [[Technik]] · [[Übersicht]]\n\n"
  "## Betrieb\n- [[MA-Server SSH-Zugriff]] · [[MA-Server Library]] · [[MA-Server-Learned]]\n\n"
  "## Ordner\n- `Skripte/` Einrichtungs- und Prüfskripte (ma-home, zima)\n- `ChatGPT-Verlauf/` frühere Server-Chats als Notizen\n\n"
  "## Verlauf aus Chats (ungeprüft)\n" + "\n".join(f"- [[{n}]]" for n in srv) +
  "\n\n## Verwandt\n- Router und KI-Werkzeuge: [[Technik]]\n- Frist- und Dienstübersicht: [[Fristen-Uebersicht]] · [[Verbundene-Dienste]]\n")

w(os.path.join(V, "10 Leben", "Gesundheit", "Gesundheit.md"),
  "# Gesundheit\n\nPrivate Unterlagen (Datenklasse B, nur lokal, nie nach außen). Inhalte nicht zusammengefasst. Übergeordnet: [[Leben overview]]\n\n"
  "Ordnerinhalt: Check-U-Ergebnis, Infoblätter zur polizeiärztlichen Untersuchung und Sehfähigkeit.\n")

# ---- Hubs ergaenzen
H = lambda *p: os.path.join(V, *p)
append_once(H("Übersicht.md"), "## Gedächtnis und Dienste",
"""## Gedächtnis und Dienste
- Profil und Index: [[Profil]] · [[Index]] · [[Abschlussbericht-Einrichtung-2026-10-10]]
- Fristen und Dienste: [[Fristen-Uebersicht]] · [[Termine-und-offene-Vorgaenge]] · [[Verbundene-Dienste]] · [[Mail-Zeitleiste]] · [[Dateien-Drive-Dropbox]]
- Chat-Importe: [[ChatGPT-Import]] · [[DeepSeek-Import]] · [[Gemini-Index]]
- Weitere Hubs: [[Minecraft SMP24]] · [[MA-Server]] · [[Gesundheit]]""")
append_once(H("10 Leben", "Leben overview.md"), "## Gesundheit", "## Gesundheit\n[[Gesundheit]] (private Unterlagen, nur lokal)\n\n## Bewerbung und Ausbildung (Mails)\n[[Mail-Zeitleiste]] · [[Fristen-Uebersicht]]")
append_once(H("20 Projekte", "Projekte.md"), "[[Minecraft SMP24]]", "## Hub Minecraft\n[[Minecraft SMP24]] sammelt Server, Welten und Konzepte.\n\n## Importe\nChat-Notizen zu den Projekten: [[ChatGPT-Import]] · [[DeepSeek-Import]]")
append_once(H("20 Projekte", "Crimson Zone", "Crimson Zone.md"), "## Neu einsortiert (2026-10-10)",
"""## Neu einsortiert (2026-10-10)
- Ordner `Crimson Zone Chapter/` (Kapitel-PDFs), `Weltaufbau/` (Powersystem, Fähigkeiten, Feldhandbuch, Resonanz-Klassifizierung), `Marisport 3D/` (Blender-Skripte), `Cz Sammlung/` (frühere Sammlung).
- Chat-Notizen: """ + " · ".join(f"[[{n}]]" for n in pick(chat, "Crimson", "Kapitel", "Webtoon", "Charakter") + pick(deep, "Crimson")))
append_once(H("20 Projekte", "Projekt Schmejd", "Projekt Schmejd.md"), "## Eternal Bonds Mod und Importe",
"""## Eternal Bonds Mod und Importe
- Ordner `Eternal Bonds Mod/` (Dokumente, Gradle-Projekt, Mod 1.21.4).
- Chat-Notizen: """ + " · ".join(f"[[{n}]]" for n in pick(chat, "Eternal Bonds", "Powersystem", "Kapitelfeedback", "Plugin vs Mod", "Faction Wars", "Kapitelanalyse", "Charakterdesign", "Zeichnung", "Energiespektrum", "Projekt Hilfe", "Projektzusammenfassung", "Kapitel Beschreibung") + pick(deep, "Eternal"))
 + "\n- Verwandt: [[Minecraft SMP24]]")
append_once(H("30 Technik", "Technik.md"), "## Neu einsortiert (2026-10-10)",
"""## Neu einsortiert (2026-10-10)
- `Software/` (Installer, Archive, NVIDIA-Profile, Blender GIS, CRU, Unity-Build), `Arduino/` (Sketches, Bibliotheken), `MA-Server/Skripte/`, `KI-Tools/fixmyprompt/`.
- Hub: [[MA-Server]]. KI-Arbeitsplatz: [[Abschlussbericht-Einrichtung-2026-10-10]] · [[DeepSeek Claude Code, Codex und Werkzeug-Fragen]]""")
append_once(H("80 Medien", "Medien.md"), "## Neu einsortiert (2026-10-10)",
"""## Neu einsortiert (2026-10-10)
- `Audio/Mikrofon-Tests/` (Spektrum-Messungen, Test-Aufnahmen), `Videos/`, `Bilder/Grafiken und Screenshots/`, `Bilder/Profilbilder/`, `Fotografie/Presets/` (Lightroom), `Fotografie/RAW/`, `Fotografie/tet Lightroom/`, Fotos je Jahr unter `Fotos/`.
- Chat-Notiz zum Audio-Setup: [[2025-05 DeepSeek Audio, Mikrofon und Rap]]""")
append_once(H("90 Archiv", "Archiv.md"), "## KI-Exporte und Altbestände",
"""## KI-Exporte und Altbestände
- `KI-Exporte/ChatGPT-Export-2026-10-07/` und `KI-Exporte/DeepSeek-Export-2026-10-10/`: Original-Exporte (JSON, Anhänge). Auswertung: [[ChatGPT-Import]] · [[DeepSeek-Import]] · [[Gemini-Index]]. Rohtext: `_Claude-Memory/Import/raw-voll/`.
- Altbestände: `Altbestand 2016/`, `Altbestand 2019/`, `Desktop-Altbestand/`, `Dropbox-Kopie/`, `PairDrop 2026-09-24/`. Nicht mehr bearbeiten.""")

# ---- Importnotizen mit Hubs verlinken
def hub_for(scope):
    s = scope.lower()
    if "minecraft" in s: return "Minecraft SMP24"
    if "crimson" in s: return "Crimson Zone"
    if "eternal" in s or "schmejd" in s: return "Projekt Schmejd"
    if "ma-server" in s: return "MA-Server"
    if "hardware" in s or "schule" in s or "ki-werk" in s or "arduino" in s: return "Technik"
    if "audio" in s: return "Medien"
    return "Leben overview"
n = 0
for src, moc in (("ChatGPT", "ChatGPT-Import"), ("DeepSeek", "DeepSeek-Import")):
    for p in glob.glob(os.path.join(M, "Import", src, "*.md")):
        t = open(p, encoding="utf-8").read()
        if "## Verwandt" in t:
            continue
        sc = re.search(r"geltungsbereich: (.+)", t)
        hub = hub_for(sc.group(1) if sc else "")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"\n## Verwandt\nÜbergeordnet: [[{hub}]] · [[{moc}]]\n")
        n += 1
print("Importnotizen verlinkt:", n)

# ---- kaputte Querverweise in Importnotizen reparieren (Datumspraefix)
fix = {"[[Eternal Bonds Mod Konzept]]": "[[2025-07-25 Eternal Bonds Mod Konzept]]",
       "[[Plugin vs Mod Minecraft]]": "[[2025-07-23 Plugin vs Mod Minecraft]]",
       "[[Faction Wars Plugin Konzept]]": "[[2025-07-25 Faction Wars Plugin Konzept]]"}
for p in glob.glob(os.path.join(M, "Import", "ChatGPT", "*.md")):
    t = open(p, encoding="utf-8").read(); o = t
    for a, b in fix.items():
        t = t.replace(a, b)
    if t != o:
        open(p, "w", encoding="utf-8").write(t)
print("fertig")
