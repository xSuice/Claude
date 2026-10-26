#!/usr/bin/env python3
"""Sync-Wrapper (Luecke 3, 2026-10-20): erzwingt Pull VOR Push.

Sicherheitsluecke 3: laeuft `vault-to-server.py` (Push) bevor
`server-to-vault.py` (Pull) lief, schreibt der Push den lokalen
Bearbeitungsstand in STATE ("als ob gesendet"); der folgende Pull sieht
die lokale Datei dann als "unveraendert" und ERSETZT SIE STILL durch die
Serverfassung (PC-Text bleibt nur als Review-Kopie auf dem Server).

Abhilfe: dieser Wrapper fuehrt IMMER zuerst Pull, dann Push aus -- und
verweigert den Push, wenn der Pull fehlgeschlagen ist (kein Push mit
veraltetem/fehlendem Pull-State).

Aufruf: python sync-wrapper.py [--dry] [--full]
"""

import subprocess
import sys
import time
import os

LOG = os.path.expanduser("~/.claude/state/server-sync.log")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + "[wrapper] " + msg + "\n")


def run_script(name, args):
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, name)] + args
    print(f"[wrapper] starte {name} {' '.join(args)}")
    rc = subprocess.call(cmd)
    print(f"[wrapper] {name} beendet mit rc={rc}")
    return rc


def main():
    dry = "--dry" in sys.argv
    full = "--full" in sys.argv
    pull_args = ["--dry"] if dry else []
    push_args = ["--dry"] if dry else (["--full"] if full else [])

    # SCHRITT 1: PULL (immer zuerst -- Reihenfolgefalle aus Luecke 3 vermeiden).
    rc_pull = run_script("server-to-vault.py", pull_args)
    if rc_pull != 0:
        log(f"Pull fehlgeschlagen (rc={rc_pull}) -- Push wird NICHT ausgefuehrt (kein Push ohne Pull).")
        print("[wrapper] FEHLER: Pull fehlgeschlagen, Push abgebrochen (sonst wuerde der Push den lokalen Stand als 'gesendet' markieren und der naechste Pull wuerde lokale Aenderungen still durch Serverfassungen ersetzen).")
        return 1

    # SCHRITT 2: PUSH (nur nach erfolgreichem Pull).
    rc_push = run_script("vault-to-server.py", push_args)
    if rc_push != 0:
        log(f"Push fehlgeschlagen (rc={rc_push}) nach erfolgreichem Pull.")
        return 1

    log("Sync-Wrappe komplett: Pull OK, Push OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
