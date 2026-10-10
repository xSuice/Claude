#!/usr/bin/env python3
"""Vault-Autopflege (laeuft ohne Modell, als geplante Windows-Aufgabe).
Verschiebt NUR lose Dateien aus der Vault-Wurzel nach festen Regeln (siehe vault-organize.py), meldet alles andere.
Nie: loeschen, ueberschreiben, Ordner verschieben, Dateien juenger als 10 Minuten anfassen, geschuetzte Bereiche aendern.
Aufruf: python vault-autopflege.py [--dry-run]
Log (Rollback): C:/Users/andre/VaultBackup/autopflege-moves.csv   Bericht: _Claude-Memory/Pflege/Pflegebericht.md
Abschalten: schtasks /Delete /TN VaultAutopflege /F"""
import os, sys, csv, time, shutil, datetime, importlib.util, collections, re, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vo", os.path.join(HERE, "vault-organize.py"))
vo = importlib.util.module_from_spec(spec); spec.loader.exec_module(vo)
V = vo.V
LOG = r"C:\Users\andre\VaultBackup\autopflege-moves.csv"
REPORT = os.path.join(V, "_Claude-Memory", "Pflege", "Pflegebericht.md")
MAX_MOVES = 40
MIN_AGE = 600  # Sekunden
DRY = "--dry-run" in sys.argv
t0 = time.time()
moves, skipped, errors, folders = [], [], [], []

rel0 = lambda p: os.path.relpath(p, V).replace("\\", "/")

def target_for(name, path):
    if re.match(r"(?i)^(Backup-codes|.*RecoveryKey|.*recovery_codes)", name):
        return "SECRET"
    if name.lower().endswith(".md"):
        try:
            if os.path.getsize(path) < 5:
                return vo.LEER
        except OSError:
            pass
        return "00 Inbox"
    return vo.classify(name, path)

# ---- Hubs: Schluesselwoerter -> Zielordner, Hub-Notiz (regelbasiert, ohne Modell)
HUBS = {
    "Crimson Zone": ("20 Projekte/Crimson Zone", "20 Projekte/Crimson Zone/Crimson Zone.md", ["crimson", "kaiju", "resonanz", "resonance", "marisport", "aurelion", "ize ", "aegis", "phil "]),
    "Projekt Schmejd": ("20 Projekte/Projekt Schmejd", "20 Projekte/Projekt Schmejd/Projekt Schmejd.md", ["eternal bonds", "schmejd", "daniel", "arcane", "umbralis", "transcendental", "gebot"]),
    "Minecraft SMP24": ("20 Projekte/Minecraft SMP24", "20 Projekte/Minecraft SMP24/Minecraft SMP24.md", ["minecraft", "smp", "plugin", "modpack", "papermc", "towny", "factions", "dynmap", "datapack"]),
    "MA-Server": ("30 Technik/MA-Server", "30 Technik/MA-Server/MA-Server.md", ["ma-server", "zimaos", "docker", "caddy", "ssh", "homeserver", "heimserver", "authelia", "dashboard", "ubuntu server"]),
    "Technik": ("30 Technik", "30 Technik/Technik.md", ["python", "arduino", "claude code", "codex", "obsidian", "api", "skript", "script", "github", "linux", "powershell"]),
    "Leben overview": ("10 Leben", "10 Leben/Leben overview.md", ["bewerbung", "lebenslauf", "ausbildung", "berufsschule", "training", "führerschein", "fahrschule", "kindergeld", "finanz", "schule", "fsj", "plan für"]),
    "Wissen": ("40 Wissen", "40 Wissen/Wissen.md", ["rhetorik", "buch", "philosophie", "zitat", "gedanke"]),
    "Medien": ("80 Medien", "80 Medien/Medien.md", ["foto", "lightroom", "audio", "mikrofon", "video"]),
}

def pick_hub(path):
    try:
        t = (os.path.basename(path)[:-3] + " " + open(path, encoding="utf-8", errors="ignore").read()[:6000]).lower()
    except OSError:
        return None
    sc = {h: sum(t.count(k) for k in kw) for h, (_, _, kw) in HUBS.items()}
    ranked = sorted(sc.items(), key=lambda x: -x[1])
    if ranked[0][1] >= 3 and ranked[0][1] >= ranked[1][1] + 2:
        return ranked[0][0]
    return None

def link_into_hub(hub, dst):
    """Notiz verlinken: Elternlink in der Notiz, Eintrag im Hub (additiv)."""
    note = os.path.basename(dst)[:-3]
    s = open(dst, encoding="utf-8", errors="ignore").read()
    if "Übergeordnet: [[" + hub + "]]" not in s:
        open(dst, "a", encoding="utf-8").write(f"\n\n## Verwandt\nÜbergeordnet: [[{hub}]]\n")
    hp = os.path.join(V, *HUBS[hub][1].split("/"))
    if os.path.exists(hp):
        h = open(hp, encoding="utf-8", errors="ignore").read()
        if f"[[{note}]]" not in h:
            if "## Automatisch einsortiert" not in h:
                open(hp, "a", encoding="utf-8").write("\n\n## Automatisch einsortiert\n")
            open(hp, "a", encoding="utf-8").write(f"- [[{note}]] ({datetime.date.today()})\n")

def handle_note(p, n):
    """Regelbasiert: eindeutiger Hub -> Zielordner + Links, sonst Inbox."""
    hub = pick_hub(p)
    if not hub or DRY:
        return None, hub
    dd = os.path.join(V, *HUBS[hub][0].split("/")); os.makedirs(dd, exist_ok=True)
    dst = vo.free_name(dd, n)
    shutil.move(p, dst); link_into_hub(hub, dst)
    return dst, hub

def log_move(src, dst):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["zeit", "von", "nach"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), src, dst])

try:
    # neue Notizen im Inbox-Wurzelordner (nicht Review) sortieren
    inbox_dir = os.path.join(V, "00 Inbox")
    for n in sorted(os.listdir(inbox_dir)):
        p = os.path.join(inbox_dir, n)
        if n == "Review" or not os.path.isfile(p) or not n.lower().endswith(".md"): continue
        if time.time() - os.path.getmtime(p) < MIN_AGE or len(moves) >= MAX_MOVES: continue
        try:
            dst, hub = handle_note(p, n)
            if dst: moves.append((n, rel0(dst) + f" (Hub {hub})")); log_move(p, dst)
        except Exception as e:
            errors.append((n, type(e).__name__))
    for n in sorted(os.listdir(V)):
        p = os.path.join(V, n)
        if n in vo.PROTECT or n in vo.KEEP_FILES or n.startswith("."):
            continue
        if os.path.isdir(p):
            folders.append(n)           # Ordner nie verschieben, nur melden
            continue
        if time.time() - os.path.getmtime(p) < MIN_AGE:
            skipped.append((n, "jünger als 10 Minuten")); continue
        if len(moves) >= MAX_MOVES:
            skipped.append((n, "Limit 40 pro Lauf")); continue
        tgt = target_for(n, p)
        if tgt == "00 Inbox" and not DRY:      # neue Notiz in der Wurzel: Hub suchen, verlinken, einsortieren
            try:
                dst, hub = handle_note(p, n)
                if dst:
                    moves.append((n, rel0(dst) + f" (Hub {hub})")); log_move(p, dst); continue
            except Exception as e:
                errors.append((n, type(e).__name__)); continue
        if tgt == "EXPORT":
            tgt = vo.EXPORT_DIR_CHATGPT + "/Wurzel-Reste"
        if DRY:
            moves.append((n, "(Trockenlauf) " + tgt)); continue
        try:
            if tgt == "SECRET":
                os.makedirs(vo.SECRETS, exist_ok=True); dst = vo.free_name(vo.SECRETS, n)
            else:
                dd = os.path.join(V, *tgt.split("/")); os.makedirs(dd, exist_ok=True)
                dst = os.path.join(dd, n)
                if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(p) and vo.sha(dst) == vo.sha(p):
                    d2 = os.path.join(V, *vo.DUP.split("/"), "aus Wurzel"); os.makedirs(d2, exist_ok=True); dst = vo.free_name(d2, n)
                else:
                    dst = vo.free_name(dd, n)
            shutil.move(p, dst)
            moves.append((n, os.path.relpath(dst, V).replace("\\", "/") if tgt != "SECRET" else "~/.claude/secrets"))
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            new = not os.path.exists(LOG)
            with open(LOG, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new: w.writerow(["zeit", "von", "nach"])
                w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), p, dst])
        except Exception as e:
            errors.append((n, type(e).__name__))
        if time.time() - t0 > 540: errors.append(("Lauf", "Zeitlimit")); break
except Exception:
    errors.append(("Lauf", traceback.format_exc().splitlines()[-1]))

# ---- Zustand messen (nur lesen)
SK = {".obsidian", ".smart-connections", ".smart-env"}
EXC = ("Server-Archiv", "Welten", "Archive/", "Mod 1.21.4", "Gradle-Projekt", "KI-Exporte", "Altbestand", "Desktop-Altbestand", "Dropbox-Kopie", "PairDrop")
md = []
for r, d, f in os.walk(V):
    d[:] = [x for x in d if x not in SK]
    md += [os.path.join(r, x) for x in f if x.lower().endswith(".md")]
rel = lambda p: os.path.relpath(p, V).replace("\\", "/")
md = [p for p in md if not any(e in rel(p) for e in EXC)]
names = {os.path.basename(p)[:-3].lower() for p in md} | {rel(p)[:-3].lower() for p in md}
allf = set()
for r, d, f in os.walk(V):
    d[:] = [x for x in d if x not in SK]
    allf |= {x.lower() for x in f}
by_base = collections.defaultdict(list); by_path = {}
for p in md:
    by_base[os.path.basename(p)[:-3].lower()].append(rel(p)); by_path[rel(p)[:-3].lower()] = rel(p)
LINK = re.compile(r"(?<!!)\[\[([^\]|#\n]+)(?:#[^\]|\n]*)?(?:\|[^\]\n]*)?\]\]")
inb = collections.Counter(); ghosts = set()
for p in md:
    t = re.sub(r"```.*?```", "", open(p, encoding="utf-8", errors="ignore").read(), flags=re.S)
    for m in LINK.finditer(t):
        k = m.group(1).strip().replace("\\", "/").lower()
        tg = by_path.get(k) or ((sorted(by_base.get(k.split("/")[-1], []), key=lambda x: (x.count("/"), len(x))) or [None])[0])
        if tg and tg != rel(p): inb[tg] += 1
        elif not tg and k.split("/")[-1] not in allf and k.split("/")[-1] + ".md" not in allf: ghosts.add(k)
orph = [rel(p) for p in md if inb[rel(p)] == 0 and not rel(p).endswith("CLAUDE.md")]
inbox = [f for f in os.listdir(os.path.join(V, "00 Inbox")) if f != "Review"]
review = sum(len(f) for _, _, f in os.walk(os.path.join(V, "00 Inbox", "Review")))
rootfiles = [n for n in os.listdir(V) if os.path.isfile(os.path.join(V, n)) and n not in vo.KEEP_FILES and not n.startswith(".")]

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
lines = ["---", "typ: pflegebericht", f"datum: {now}", "quelle: scripts/vault-autopflege.py (ohne Modell)", "---", "", "# Pflegebericht Vault", "",
         f"Letzter Lauf: {now}{' (Trockenlauf)' if DRY else ''}. Dauer {round(time.time() - t0)} s. Übergeordnet: [[Index]] · [[Übersicht]] · [[Abschlussbericht-Einrichtung-2026-10-10]]", "",
         f"## Ergebnis\n- Verschoben: {len(moves)} lose Dateien aus der Wurzel. Übersprungen: {len(skipped)}. Fehler: {len(errors)}.",
         f"- Lose Dateien in der Wurzel jetzt: {len(rootfiles)}. Neue Ordner in der Wurzel (nicht angefasst): {', '.join(folders) if folders else 'keine'}.",
         f"- Zu sortieren: `00 Inbox` {len(inbox)} Einträge. `Review` {review} Dateien.",
         f"- Graph: {len(md)} Notizen, ohne eingehenden Link: {len(orph)}, unaufgelöste Linkziele (Geisterknoten): {len(ghosts)}."]
if moves: lines += ["", "## Verschoben"] + [f"- `{a}` nach `{b}`" for a, b in moves[:40]]
if skipped: lines += ["", "## Übersprungen"] + [f"- `{a}`: {b}" for a, b in skipped[:20]]
if errors: lines += ["", "## Fehler"] + [f"- {a}: {b}" for a, b in errors[:10]]
if orph: lines += ["", "## Notizen ohne eingehenden Link (bitte einordnen lassen)"] + [f"- `{o}`" for o in orph[:25]]
if inbox: lines += ["", "## Inbox (auf Zuruf von Claude nach Inhalt einsortieren)"] + [f"- `{i}`" for i in inbox[:25]]
lines += ["", "Rückgängig: `python scripts/vault-organize.py undo` ist nur für den Großlauf. Für diesen Lauf: Zeilen aus `C:/Users/andre/VaultBackup/autopflege-moves.csv` (von, nach) manuell zurückschieben. Abschalten: `schtasks /Delete /TN VaultAutopflege /F`."]
open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"verschoben {len(moves)}, übersprungen {len(skipped)}, Fehler {len(errors)}, Wurzel lose {len(rootfiles)}, Orphans {len(orph)}, Geister {len(ghosts)}")
sys.exit(1 if errors else 0)
