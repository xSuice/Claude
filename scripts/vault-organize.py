#!/usr/bin/env python3
"""Obsidian-Vault aufraeumen: lose Wurzeldateien und Wurzelordner in die Bereichsstruktur sortieren.

Aufruf:  python vault-organize.py plan      (Trockenlauf, schreibt nur den Plan)
         python vault-organize.py run       (fuehrt aus, schreibt Verschiebe-Log)
         python vault-organize.py undo LOG  (macht Verschiebungen aus dem Log rueckgaengig)

Regeln: nichts loeschen, nichts umbenennen (ausser Namenskonflikt -> "Name (2).ext"),
byte-identische Duplikate -> 00 Inbox/Review/Duplikate, Geheimnisse -> ~/.claude/secrets (nicht gelesen),
geschuetzt: .obsidian .smart-connections .smart-env _Claude-Memory "Auto Router" Sessions, Bereichsordner 00..90, Hubs.
"""
import os, re, sys, csv, shutil, hashlib, datetime

V = r"C:\Users\andre\Documents\Obsidian Vault"
SECRETS = os.path.expanduser(r"~\.claude\secrets")
LOGDIR = r"C:\Users\andre\VaultBackup"
STAMP = "20261010"
PROTECT = {".obsidian", ".smart-connections", ".smart-env", "_Claude-Memory", "Auto Router", "Sessions",
           "00 Inbox", "10 Leben", "20 Projekte", "30 Technik", "40 Wissen", "80 Medien", "90 Archiv"}
KEEP_FILES = {"CLAUDE.md", "Übersicht.md", "Wikilinks.md"}
DUP = "00 Inbox/Review/Duplikate"
UNK = "00 Inbox/Review/Unklar"
LEER = "00 Inbox/Review/Leer"
EXPORT_DIR_CHATGPT = "90 Archiv/KI-Exporte/ChatGPT-Export-2026-10-07"
EXPORT_DIR_DEEPSEEK = "90 Archiv/KI-Exporte/DeepSeek-Export-2026-10-10"

# Ordner aus der Wurzel -> Ziel (relativ zum Vault). Wenn Ziel existiert, wird dateiweise zusammengefuehrt.
FOLDER_MAP = {
    "39e6809fcf40fcc864d885ce052e0a6b952536818a6e9056922d9dd9b1662892-2026-10-07-09-30-50-b6eb6d6802284730b8b6d13c5a3d05f4": EXPORT_DIR_CHATGPT,
    "deepseek_data-2026-10-10": EXPORT_DIR_DEEPSEEK,
    "sites": EXPORT_DIR_CHATGPT + "/sites",
    "Arduino": "30 Technik/Arduino",
    "sketch_jul10g": "30 Technik/Arduino/sketch_jul10g",
    "blosm": "30 Technik/Software/Blender GIS/blosm",
    "OSM": "30 Technik/Software/Blender GIS/OSM",
    "NVIDIA_Inspector_v1.9.8.5_Beta": "30 Technik/Software/NVIDIA Inspector",
    "cru-1.5.3": "30 Technik/Software/CRU",
    "Device Cleanup": "30 Technik/Software/Device Cleanup",
    "TestRun": "30 Technik/Software/Unity ProjectX Build",
    "fixmyprompt": "30 Technik/KI-Tools/fixmyprompt",
    "ChatGPT": "30 Technik/MA-Server/ChatGPT-Verlauf",
    "Art Übungen": "20 Projekte/Projekt Schmejd/Artwork/Art Übungen",
    "Eternal Bonds": "20 Projekte/Projekt Schmejd/Eternal Bonds Mod/Dokumente",
    "EternalBonds": "20 Projekte/Projekt Schmejd/Eternal Bonds Mod/Gradle-Projekt EternalBonds",
    "Eternal-Bonds-Mod-1.21.4": "20 Projekte/Projekt Schmejd/Eternal Bonds Mod/Mod 1.21.4",
    "Cz": "20 Projekte/Crimson Zone/Cz Sammlung",
    "Chapters": UNK + "/Chapters",
    "Create Chronicles Bosses and Beyond SERVERv2.5.3": "20 Projekte/Minecraft SMP24/Server-Archiv/Create Chronicles Server",
    "Server": "20 Projekte/Minecraft SMP24/Server-Archiv/Server",
    "Test serv": "20 Projekte/Minecraft SMP24/Server-Archiv/Test serv",
    "New World (42)": "20 Projekte/Minecraft SMP24/Welten/New World (42)",
    "Generated World": "20 Projekte/Minecraft SMP24/Welten/Generated World",
    "SMP": "20 Projekte/Minecraft SMP24/Archive/SMP",
    "ItemsAdder-All+Alpha2.zip": LEER + "/ItemsAdder-All+Alpha2.zip",
    "re-6n7shvg": LEER + "/re-6n7shvg",
    "re-7r3pkg9": LEER + "/re-7r3pkg9",
    "re-l23eeba": LEER + "/re-l23eeba",
    "Desktop": "90 Archiv/Desktop-Altbestand",
    "2016": "90 Archiv/Altbestand 2016",
    "16.7.2019": "90 Archiv/Altbestand 2019",
    "PairDrop_files_20260924_1830": "90 Archiv/PairDrop 2026-09-24",
    "Dropbox": "90 Archiv/Dropbox-Kopie",
    "Ebay": "10 Leben/Finanzen/Dokumente/Ebay",
    "Flaschengarten": "80 Medien/Fotos/Flaschengarten",
    "Profil Bilder& etc": "80 Medien/Bilder/Profilbilder",
    "Unbenannter Export": "80 Medien/Fotografie/Unbenannter Export",
    "tet": "80 Medien/Fotografie/tet Lightroom",
    "Neuer Ordner": "80 Medien/Fotos/Neuer Ordner",
    "Training": "10 Leben/Sport & Training/Training",
    "Schule": "10 Leben/Schule/Schule Altbestand",
    "Praktikum": "10 Leben/Bewerbung/Praktikum",
    "Reflect": UNK + "/Reflect",
}

NAME_RULES = [  # (regex auf Dateiname, Ziel)
    (r"^(Backup-codes|.*RecoveryKey|.*recovery_codes)", "SECRET"),
    (r"^(CHECK-U|Bundespolizei|Infoblatt-Sehfaehigkeit)", "10 Leben/Gesundheit"),
    (r"^(Kindergeld|kd0020)", "10 Leben/Finanzen/Dokumente"),
    (r"^Finanzplanung", "10 Leben/Finanzen"),
    (r"^Geburtstagliste", "10 Leben/Planung"),
    (r"(?i)anschreiben", "10 Leben/Bewerbung/Anschreiben Sammlung"),
    (r"(?i)^(lebenslauf|Studyflix|Hospitation|Philipp_Andrew_R.*Bewerbung)", "10 Leben/Bewerbung/Dokumenten Sammlung"),
    (r"(?i)^(Chapter|CrimsonZone)", "20 Projekte/Crimson Zone/Crimson Zone Chapter"),
    (r"(?i)(powersyst|^Fähigkeiten|^Feldhandbuch|^Klassifizierung der Resonanz|Konzepten von Crimson)", "20 Projekte/Crimson Zone/Weltaufbau"),
    (r"(?i)(marisport|blender_4_5)", "20 Projekte/Crimson Zone/Marisport 3D"),
    (r"(?i)(eternal.?bonds|^Enderdrache|^package com)", "20 Projekte/Projekt Schmejd/Eternal Bonds Mod/Dokumente"),
    (r"(?i)(^Training|🏋|Tägliche Routine)", "10 Leben/Sport & Training"),
    (r"(?i)(samson|spektrum|xm8500|hyperx|^sound|besseres mic|blue ember)", "80 Medien/Audio/Mikrofon-Tests"),
    (r"(?i)^(ma-home|zima)-.*\.(sh|py)$", "30 Technik/MA-Server/Skripte"),
    (r"(?i)\.xmp$", "80 Medien/Fotografie/Presets"),
    (r"(?i)\.arw$", "80 Medien/Fotografie/RAW"),
    (r"(?i)\.nip$", "30 Technik/Software/NVIDIA-Profile"),
    (r"(?i)\.(exe|msi)$", "30 Technik/Software/Installer"),
    (r"(?i)(smp|world|server|mod|minecraft|towny|sword|plugin|kippe|yippe|resmp).*\.(zip|rar|mrpack)$", "20 Projekte/Minecraft SMP24/Archive"),
    (r"(?i)\.(zip|rar|7z)$", "30 Technik/Software/Archive"),
    (r"(?i)\.(mp4|mov|mkv|avi)$", "80 Medien/Videos"),
    (r"(?i)\.(mp3|wav|flac|sfk)$", "80 Medien/Audio"),
    (r"(?i)\.(png|gif|webp|bmp)$", "80 Medien/Bilder/Grafiken und Screenshots"),
]
EXPORT_NAMES = re.compile(r"^(file[-_].*\.dat|conversations-\d+\.json|ads\.json|conversation_asset_file_names\.json|export_manifest\.json|"
                          r"library_files\.json|sectioned_conversations\.json|shared_conversations\.json|user\.json|user_settings\.json|"
                          r"message\.txt|chat\.html|.*-2026-10-07-.*\.zip|deepseek_data-.*\.zip|Andrew-(Verfuegbare|Addons).*\.zip)$")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def classify(name, path):
    if EXPORT_NAMES.match(name):
        return "EXPORT"
    for pat, tgt in NAME_RULES:
        if re.search(pat, name):
            return tgt
    if re.search(r"(?i)\.(jpg|jpeg|heic)$", name):
        y = datetime.datetime.fromtimestamp(os.path.getmtime(path)).year
        return f"80 Medien/Fotos/{y}"
    return UNK


def free_name(d, name):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return p
    base, ext = os.path.splitext(name)
    i = 2
    while os.path.exists(os.path.join(d, f"{base} ({i}){ext}")):
        i += 1
    return os.path.join(d, f"{base} ({i}){ext}")


def plan():
    items = []  # (src, dst_dir, kind)
    for n in sorted(os.listdir(V)):
        p = os.path.join(V, n)
        if n in PROTECT or n in KEEP_FILES:
            continue
        if os.path.isdir(p):
            if n in FOLDER_MAP:
                items.append((p, FOLDER_MAP[n], "dir"))
            else:
                items.append((p, UNK + "/" + n, "dir"))
        else:
            t = classify(n, p)
            items.append((p, t, "file"))
    return items


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "undo":
        for row in reversed(list(csv.reader(open(sys.argv[2], encoding="utf-8")))[1:]):
            dst, src = row[2], row[1]
            if os.path.exists(dst):
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst, src)
        print("rueckgaengig gemacht")
        return
    items = plan()
    os.makedirs(LOGDIR, exist_ok=True)
    log = os.path.join(LOGDIR, f"organize-{STAMP}-moves.csv")
    rows = [["art", "von", "nach"]]
    counts = {}
    for src, tgt, kind in items:
        key = tgt if tgt not in ("EXPORT",) else EXPORT_DIR_CHATGPT + "/Wurzel-Reste"
        counts[key] = counts.get(key, 0) + 1
    if mode == "plan":
        for k, v in sorted(counts.items()):
            print(f"{v:4d}  {k}")
        print(len(items), "Eintraege")
        return
    export_ref = os.path.join(V, *EXPORT_DIR_CHATGPT.split("/"))
    for src, tgt, kind in items:
        name = os.path.basename(src)
        if tgt == "SECRET":
            os.makedirs(SECRETS, exist_ok=True)
            dst = free_name(SECRETS, name)
            shutil.move(src, dst); rows.append(["secret", src, dst]); continue
        if tgt == "EXPORT":
            ref = os.path.join(export_ref, name)
            if os.path.exists(ref) and os.path.getsize(ref) == os.path.getsize(src) and sha(ref) == sha(src):
                d = os.path.join(V, *DUP.split("/"), "ChatGPT-Export-Wurzelkopie")
            else:
                d = os.path.join(V, *EXPORT_DIR_CHATGPT.split("/"), "Wurzel-Reste")
            os.makedirs(d, exist_ok=True)
            dst = free_name(d, name)
            shutil.move(src, dst); rows.append(["datei", src, dst]); continue
        dd = os.path.join(V, *tgt.split("/"))
        if kind == "file":
            os.makedirs(dd, exist_ok=True)
            dst = os.path.join(dd, name)
            if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src) and sha(dst) == sha(src):
                d2 = os.path.join(V, *DUP.split("/"), "aus Wurzel")
                os.makedirs(d2, exist_ok=True)
                dst = free_name(d2, name)
            else:
                dst = free_name(dd, name)
            shutil.move(src, dst); rows.append(["datei", src, dst]); continue
        # Ordner
        if not os.path.exists(dd):
            os.makedirs(os.path.dirname(dd), exist_ok=True)
            shutil.move(src, dd); rows.append(["ordner", src, dd])
        else:  # zusammenfuehren, dateiweise, nie ueberschreiben
            for root, dirs, files in os.walk(src):
                rel = os.path.relpath(root, src)
                for f in files:
                    s = os.path.join(root, f)
                    td = os.path.join(dd, rel) if rel != "." else dd
                    os.makedirs(td, exist_ok=True)
                    t = os.path.join(td, f)
                    if os.path.exists(t) and os.path.getsize(t) == os.path.getsize(s) and sha(t) == sha(s):
                        d2 = os.path.join(V, *DUP.split("/"), "aus " + name)
                        os.makedirs(d2, exist_ok=True)
                        t = free_name(d2, f)
                    else:
                        t = free_name(td, f)
                    shutil.move(s, t); rows.append(["datei", s, t])
            for root, dirs, files in os.walk(src, topdown=False):  # nur leere Ordner entfernen
                try:
                    os.rmdir(root)
                except OSError:
                    pass
    with open(log, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print("fertig,", len(rows) - 1, "Verschiebungen, Log:", log)


if __name__ == "__main__":
    main()
