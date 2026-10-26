#!/usr/bin/env python3
"""UserPromptSubmit-Hook: reicht einen ausdrücklich markierten Arbeitsauftrag einmal an JARVIS weiter.
Auslöser nur am Anfang der Nachricht: "jarvis:" oder "@jarvis". Normale Gespräche und Statusfragen bleiben unberührt.
Worker (Umgebungsvariable JARVIS_WORKER=1, nur von JARVIS selbst gesetzt) und "direkt:" leiten nie weiter.
Idempotenz: client_id = Hash aus Sitzung und Text; derselbe Auftrag erzeugt keinen zweiten Job (Brücke prüft client_id).
Fail-open: jeder Fehler endet ohne Weiterleitung und ohne Blockade, der Fehler wird als Hinweis gemeldet.
Protokoll: nur Zeit, Job-ID, Status (nie Text, Datenklasse B)."""
import hashlib, json, os, re, socket, sys, time

SOCK = os.environ.get("JARVIS_BRIDGE_SOCK", "/run/ma-claude/bridge.sock")
LOG = os.path.expanduser("~/.claude/jarvis-hook.log")
TRIGGER = re.compile(r"^\s*(@jarvis|jarvis:)\s*", re.I)


def log(z):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " " + z + "\n")
    except OSError:
        pass


def bridge(req):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(20)
    s.connect(SOCK)
    s.sendall(json.dumps(req).encode() + b"\n")
    d = b""
    while not d.endswith(b"\n"):
        b = s.recv(65536)
        if not b:
            break
        d += b
    return json.loads(d.decode())


def hinweis(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))


def main():
    if os.environ.get("JARVIS_WORKER") == "1":
        return
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    p = d.get("prompt", "")
    m = TRIGGER.match(p)
    if not m or re.match(r"^\s*direkt:", p, re.I):
        return
    auftrag = p[m.end():].strip()
    if not auftrag:
        return
    cid = "hook-" + hashlib.sha256((d.get("session_id", "") + "\0" + auftrag).encode()).hexdigest()[:20]
    try:
        r = bridge({"op": "jarvis", "user": os.environ.get("USER", "andrew"), "cmd": "submit", "request": auftrag, "client_id": cid})
    except Exception as e:
        log("fehler brücke " + type(e).__name__)
        hinweis("JARVIS-Weiterleitung: Annahme UNBEKANNT (%s). Nicht erneut senden, ohne zuerst `status` mit client_id %s zu prüfen. "
                "Den Auftrag nicht stillschweigend selbst ausführen; Ausnahmebetrieb benennen oder Philipp 'direkt:' wählen lassen." % (type(e).__name__, cid))
        return
    data = (r.get("data") or {}) if isinstance(r, dict) else {}
    job = data.get("job_id")
    if not job:
        log("abgelehnt " + str(r.get("error", ""))[:80])
        hinweis("JARVIS hat den Auftrag NICHT angenommen: %s. Nicht stillschweigend selbst ausführen; Grund nennen." % str(r.get("error", "unbekannt"))[:200])
        return
    log("job %s client_id %s" % (job, cid))
    hinweis("Der Auftrag wurde an JARVIS übergeben (Auftrags-ID %s). Nicht selbst bearbeiten: nur Status (`status`/`events`) abfragen "
            "und das Ergebnis mit der Kennzeichnung aus dem Ereignis `attribution` wiedergeben." % job)


try:
    main()
except Exception:
    log("hook-fehler")
sys.exit(0)
