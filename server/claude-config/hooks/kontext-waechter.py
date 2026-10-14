#!/usr/bin/env python3
"""UserPromptSubmit-Hook: meldet große Sitzungen (Kontext-Wächter, Server-Gegenstück zum PC).
Liest die Token-Zahl der letzten Antwort aus dem Ende des Transcripts. Ab 250 000 Warnung, ab 300 000 Auftrag zur Übergabe.
Jede Stufe wird pro Sitzung nur einmal gemeldet (erneut erst nach +50 000 Token), damit der Hinweis nicht jede Nachricht Kontext kostet.
Abschalten pro Nachricht mit "ohne waechter"."""
import json
import os
import re
import sys
import time

LOG = os.path.expanduser("~/.claude/waechter.log")
ZUSTAND = os.path.expanduser("~/.claude/state")


def protokoll(zeile):
    # nur Zeit und Zahlen, nie Text (Datenklasse B); Datei bleibt unter ca. 100 KB
    try:
        if os.path.getsize(LOG) > 100_000:
            with open(LOG, encoding="utf-8") as f:
                rest = f.readlines()[-200:]
            with open(LOG, "w", encoding="utf-8") as f:
                f.writelines(rest)
    except OSError:
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " " + zeile + "\n")
    except Exception:
        pass


WARN, UEBERGABE, NACHMELDEN = 250_000, 300_000, 50_000
try:
    d = json.load(sys.stdin)
    p, pfad = d.get("prompt", ""), d.get("transcript_path", "")
except Exception:
    sys.exit(0)
if re.search(r"ohne w(ä|ae)chter", p, re.I) or p.lstrip().startswith("/uebergabe"):
    sys.exit(0)

tok = 0
if not pfad:
    protokoll("kein transcript_path")
    sys.exit(0)
try:
    with open(pfad, "rb") as f:  # nur das Ende lesen; die letzte Antwort der Hauptkette steht dort
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 3_000_000))
        text = f.read().decode("utf-8", "replace")
    for z in text.splitlines():
        try:
            e = json.loads(z)
        except Exception:
            continue
        if e.get("isSidechain"):
            continue
        u = (e.get("message") or {}).get("usage")
        if isinstance(u, dict):
            tok = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
except Exception:
    sys.exit(0)

protokoll("tok=%d" % tok)
stufe = 2 if tok >= UEBERGABE else 1 if tok >= WARN else 0
if not stufe:
    sys.exit(0)

sid = re.sub(r"[^A-Za-z0-9_-]", "", str(d.get("session_id", "")))[:64] or "unbekannt"
datei = os.path.join(ZUSTAND, "waechter-%s.json" % sid)
try:
    with open(datei, encoding="utf-8") as f:
        alt = json.load(f)
except Exception:
    alt = {}
if alt.get("stufe", 0) >= stufe and tok < alt.get("tok", 0) + NACHMELDEN:
    sys.exit(0)
try:
    os.makedirs(ZUSTAND, exist_ok=True)
    tmp = datei + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"stufe": stufe, "tok": tok}, f)
    os.replace(tmp, datei)  # atomar, falls zwei Sitzungen gleichzeitig schreiben
    for n in os.listdir(ZUSTAND):  # Zustandsdateien alter Sitzungen nach 7 Tagen entfernen
        pf = os.path.join(ZUSTAND, n)
        if n.startswith("waechter-") and time.time() - os.path.getmtime(pf) > 7 * 86400:
            os.remove(pf)
except OSError:
    pass

if stufe == 2:
    t = ("Kontext-Wächter: Die Sitzung hat ca. %dk Token. Führe am Ende dieser Antwort `/uebergabe` aus, "
         "damit Philipp in einer frischen Sitzung günstiger weitermacht." % (tok // 1000))
else:
    t = "Kontext-Wächter: Die Sitzung hat ca. %dk Token. Erwähne kurz, dass bald eine neue Sitzung (`/uebergabe`) sinnvoll ist." % (tok // 1000)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": t}}))
