# JARVIS V16 – Stand, Architektur, Sicherheit (2026-10-14)

Basis: Cognitive Brain V11.1 (`server/jarvis/core/`, unverändert in Originalstruktur, dazu bwrap-Sandbox). V16-Erweiterungen liegen in `server/jarvis/core/brain-runtime/`. Frühere Doku: `docs/jarvis/v11.1/`. Messungen: `docs/jarvis/messungen/`. Benchmark-Gerüst: `BENCHMARK-V16.md`.

## Was V16 ist

Ein Auftrag vom PC (`/jarvis` oder `scripts/jarvis/jarvis.py submit "..."`) geht an den MA-Server. Dort nimmt ein Cron-Takt (jede Minute, `flock`, `nice`/`ionice`) den Auftrag auf und führt ihn selbstständig aus:

1. **Planung** (`taskengine.py`): Aufgabentyp erkennen, Schritte festlegen. Bei bekanntem Typ mit bewährter Vorlage entfällt die Planung (`template:N:exact`).
2. **Router** (`scripts/router/router_core.py`, Regeln 8/12): schlägt Anbieter vor. Datenklasse C geht nie nach außen. Fable bleibt gesperrt.
3. **Worker** (`workers.py`): Claude-CLI nur mit `--tools` und `--strict-mcp-config` (Grundkontext 9,2k statt 32,3k Token, n=1); lokale Schritte über Fähigkeiten in der Sandbox; PC-Schritte (java.build, blender, ollama) holt der PC-Worker ab.
4. **Fähigkeiten** (`capabilities.py`): eingebaute Werkzeuge und Drop-ins unter `~/.local/share/ma-jarvis/tools/`. Jede Fähigkeit besteht zuerst einen Selbsttest in der Sandbox (Status `tested`); Drop-ins dürfen keine Rechte anfordern.
5. **Abnahme** (`acceptance.py`, `inspect_file.py`): unabhängige Prüfung jeder Ergebnisdatei, bevor ein Auftrag „erledigt“ heißt.
6. **Lernen** (`learning.py`): erfolgreiche Aufträge werden zu Vorlagen. Wiederholung kostet weniger.
7. **Ledger** (`ledger.py`): Aufrufe und Token je 24 h; Grenzen 40 Claude-Aufrufe/Tag, 1,5 Mio Token/Tag, 30 je Identität, 1 gleichzeitig. Plan-Guard über den Bridge-Socket (`{"op":"jobs"}`): Warnung ab 70 %, Stopp ab 85 % der Plan-Auslastung.

## Sicherheit

- Ausführung nur in der **bwrap-Sandbox** (`--unshare-user`, `--disable-userns`, ohne Netz außer ausdrücklich erlaubt). `unshare` scheitert am Server an AppArmor, deshalb bwrap.
- Läuft als `andrew`, **ohne sudo**, ohne Docker. Kein eigenes OS-Konto (Kontentrennung braucht sudo, offen).
- Not-Aus: Datei `/srv/ma-home/library/.jarvis/v16/KILL` (`rollback-v16.sh --stop` setzt sie und entfernt den Cron).
- Takt läuft aus einer **Release-Kopie** (`~/.local/share/ma-jarvis/current`), nicht aus `~/MA-Server`, weil der Abgleich das Repo jederzeit ändert.
- Lesen von `~/.ssh` und `~/.claude/secrets` ist gesperrt. Datenklasse C nie in Prompts, Git oder Vault.
- Externe Helfer: aus (`calls_per_day 0`, shadow). Kein Schlüssel geprüft, kein Budget freigegeben.
- PC-Worker läuft **ohne Sandbox, mit Netz**. Deshalb nur Fähigkeiten aus `~/.claude/state/jarvis-pc.json` (`{"allowed": [...]}`). Datei existiert noch nicht, also läuft nichts am PC.

## Installation und Rückweg (am Server, ohne sudo)

```
install-v16.sh --src <Staging>     Sicherung (Crontab, DBs, Integritätsprüfung) → Release → Tests VOR dem Umschalten → Konfiguration → Fähigkeiten testen → Symlink current → Cron → doctor
rollback-v16.sh --stop | --start | --to <Release>
```

Belegt am 2026-10-14: erster Lauf brach bei roten Tests ab und ließ den alten Zustand stehen (Gate funktioniert). Nach Korrektur 294 Tests grün (4 übersprungen, brauchen root), `--stop` entfernt Cron und setzt KILL, `--start` stellt beides wieder her.

## Ehrliche Übersicht

**Funktioniert und belegt (live am Server, 2026-10-14)**
- Installation, Rollback-Schalter, Cron-Takt (journalctl: jede Minute, `tick.err` leer).
- 294 Tests am Server grün (243 V11.1 + 51 V16), 4 übersprungen.
- Zwei echte Aufträge vom PC (Primzahlen-Skript mit Tests und README): beide „erledigt“, 3/3 Ergebnisdateien abgenommen; Ergebnis am PC unabhängig geprüft (Ausgabe bis 30 korrekt, 11 Tests grün).
- Lernen (Gate D live): Wiederholung über `template:1:exact`, 1 statt 3 Claude-Aufrufe, 11 779 statt 30 442 neue Token (−61 %), 0,065 statt 0,166 USD Listenpreis-Äquivalent (keine Rechnung). **n=1.**
- Fähigkeiten: 9 tested (python.run/unittest/compile, doc.pandoc, image.convert, media.ffmpeg, data.jq, archive.zip, Drop-in tool.wortstatistik).
- PC: `pc-report` meldet `java.build` tested (OpenJDK 21).
- Last im Leerlauf (244 s, alle 5 s) vor/nach: CPU-Median 5,8 % / 5,3 %, MemAvailable 1979 / 1987 MB, HA-Latenz Median 7,2 / 9,4 ms (p95 7,9 / 10,4). Einzelmessung, Streuung unbekannt.

**Nur im Test (Container/Fakes), nicht live**
- Gate B (Fehlerpfade, Korrekturrunden, Wartephasen) und Plan-Guard-Schwellen laufen gegen Fakes.
- Router-Regeln (49 Tests), Drop-in-Ablehnungen (Gate C, Tests).

**Live blockiert (braucht Entscheidung oder Rechte von Philipp)**
- PC-Builds: `~/.claude/state/jarvis-pc.json` anlegen.
- Helfer/Canary: Schlüssel am Server und Budget.
- User-Dienst statt Cron: `sudo loginctl enable-linger andrew`. Eigenes OS-Konto: sudo.

**Bekannt kaputt oder schwach**
- `doc.office_pdf` (LibreOffice) scheitert in der Sandbox: „no valid pipe path found“. Als `heavy` markiert, nicht genutzt.
- `pdf.to_png` nur `available` (kein Selbsttest, Versionsabfrage liefert Fehlertext).
- `doc.pandoc` schlug einmal mit „Cannot allocate memory“ fehl (285 MB frei, 3,2 GB Server). Der Test wiederholt jetzt einmal. Echte Aufträge brauchen ggf. eine Wiederholung bei Speicherdruck.
- Während des Messlaufs im Leerlauf wurde kein Auftrag gemessen. Last **während eines Jobs** fehlt noch.
- `ollama.ask` und `blender.render` am PC: kein Adapter bzw. nicht installiert.
- Sonde auf Port 80 unbrauchbar (https-Umleitung).

## Fallen

- Dienste nie aus `~/MA-Server` starten, sondern aus `current`.
- `bwrap` braucht `--unshare-user` zusammen mit `--disable-userns`; `/var/run` ist Link auf `/run`.
- `pandoc --sandbox` kann unter Ubuntu kein DOCX schreiben. `/tmp` ist tmpfs.
- Tests am Server sind Linux-only; am PC fehlen WSL und Docker.
- `rollback-v16.sh --start` legt jedes Mal einen neuen Release an (alte bleiben unter `releases/`).
