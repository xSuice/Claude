# JARVIS V16 im Portal (Stand 2026-10-15)

JARVIS ist ein Reiter im vorhandenen MA-Home-Portal (`portal-ui/web/app.js`, Reiter "JARVIS"). Es gibt kein zweites Dashboard.

## Weg einer Anfrage

Browser -> `POST /api/jarvis` (Portal, nur Admin) -> Unix-Socket der Claude-Brücke (Op `jarvis`) -> `jarvis_cli.py` aus `~/.local/share/ma-jarvis/current` -> Zustand unter `/srv/ma-home/library/.jarvis/v16`, Ergebnisse unter `/srv/ma-home/library/JARVIS`.

Dieselbe Steuerung wie der PC-Client (`scripts/jarvis/jarvis.py`) und die Kommandozeile am Server. Die Brücke hat eine Zulassungsliste: submit, list, status, events, result, cancel, approve, usage, caps (ohne `--discover`), learned, meta, kill (nur eigener Not-Aus), forget. Nicht erreichbar über das Portal: `tick`, `doctor`, `caps --discover` (brauchen bwrap, den Takt macht Cron), globaler Not-Aus, PC-Worker-Befehle.

## Benutzertrennung

Der Portal-Benutzer wird über `~/.config/ma-jarvis/portal-users.json` auf eine JARVIS-Konfiguration abgebildet (`{"andrew": "jarvis.json"}`, Identität `philipp`). Unbekannte Benutzer bekommen "Kein JARVIS-Konto". Das Portal erlaubt JARVIS nur Admins. Ein weiterer Mensch braucht eine eigene Konfiguration mit eigenem `state_dir` und einen Eintrag in der Zuordnung. Eine Trennung auf Betriebssystem-Ebene gibt es nicht (kein sudo).

## Last und Token

- Der Reiter fragt nur ab, solange er offen und sichtbar ist und ein Auftrag läuft: alle 6 s Status und Verlauf, alle 5. Runde Liste und Verbrauch, sonst alle 30 s. Ein Aufruf kostet etwa 0,35 s CPU (gemessen, ein Python-Prozess).
- Das Portal selbst verbraucht keine Claude-Token. Token verbrauchen nur die Aufträge, begrenzt vom Ledger (40 Aufrufe/Tag, 1,5 Mio Token/Tag, Plan-Guard).

## API (Anmeldung über Authelia-Sitzung, Header `X-MA-Request: 1`)

```
POST /api/jarvis {"cmd":"submit","request":"...","client_id":"<eindeutig>"}   -> data.job_id
POST /api/jarvis {"cmd":"status","job":"j20261014-cfcd71"}
POST /api/jarvis {"cmd":"events","job":"...","since":0}
POST /api/jarvis {"cmd":"approve","job":"...","step":"s1","answer":""}
POST /api/jarvis {"cmd":"cancel","job":"..."}
```

Antwort: `{"type":"jarvis","ok":true|false,"rc":0,"data":{...}}`. Ergebnisdateien öffnet der Reiter über den vorhandenen Betrachter (`Bibliothek/JARVIS/<Auftrag>/<Datei>`).

## Installation (braucht Philipp, sudo)

1. `sudo bash ~/MA-Server/portal-ui/deploy-ui.sh` (installiert die Oberfläche und patcht `portal.py` mit `patch-portal-jarvis.py`, startet das Portal neu).
2. Brücke einspielen: der Auto-Deploy (`ma-deploy`) übernimmt `server/claude-bridge/ma-claude-bridge.py` nach `/usr/local/lib` und startet sie neu, sobald der Deploy-Schalter an ist. Sonst von Hand: `sudo install -m 755 ~/MA-Server/server/claude-bridge/ma-claude-bridge.py /usr/local/lib/ma-claude-bridge.py && sudo systemctl restart ma-claude-bridge`.
3. Reiter "JARVIS" im Portal öffnen (Strg+F5).

Rückweg: `portal.py.bak-<Zeit>` und `web.bak-<Zeit>` zurückkopieren, `/usr/local/lib/ma-claude-bridge.py.bak` zurück, Dienste neu starten.

## Geprüft und nicht geprüft

- Geprüft: `jarvis_api` gegen den echten Kern am Server (list, status, usage, fremder Benutzer, ungültige ID, unbekannter Befehl); Portal-Patch an einer Kopie von `portal.py` (idempotent, kompiliert); Browser-Rauchtest 82/82 mit Platzhalter-Antworten (Reiter, Auftrag senden, Freigabe, Ergebnisdateien, kein Querscrollen).
- Nicht geprüft: echter Lauf durch Portal und Brücke (beides noch nicht neu eingespielt); Freigabe eines echten Auftrags; Bridge-Sandbox (`ProtectSystem=strict`) gegen `jarvis_cli.py submit`.

## Offene Lücken

- Dateien hochladen für Aufträge geht nur über den PC-Client (`--file`), im Portal noch nicht.
- Serverdienste verwalten: bleibt in den Reitern System und Terminal. JARVIS-Aufträge laufen in der Sandbox ohne sudo und können keine Dienste steuern.
- "Dieselben Erinnerungen und Helfer wie Claude Code am PC": JARVIS nutzt eine eigene Wissensbasis (`brain.db`, Lernen, Vorlagen). Der Auto-Memory des Vaults und die Agenten aus `~/.claude/agents` werden von den Claude-Workern nicht eingelesen (`--tools` und Minimal-Kontext sind Absicht wegen der Token). Anbindung wäre eine Entscheidung und ein eigener Schritt.
- Cron-Takt: `doctor` meldete in der Chat-Umgebung `cron_tick: false`, weil `crontab -l` dort gesperrt ist. Am Server selbst prüfen.
