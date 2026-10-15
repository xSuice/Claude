# Phase E: JARVIS verbessert sich über Claude Code (Entwurf, Stand 2026-10-15)

Status: Entwurf, noch kein Code. Gehört zu BACKLOG B39. Keine Doppelinfrastruktur: Task-Engine, `improve.py`, `install-v16.sh`.

## Ausgangslage (aus dem Code belegt)
- `brain-runtime/improve.py` (V9): `trial` wendet einen Patch im losgelösten Git-Worktree an und führt dieselben erlaubten Prüfungen auf der Basis und auf dem Kandidaten aus. Urteil `improved`, `neutral` oder `rejected`. `promote` (nur mit `allow_promote`), `rollback` per `git revert`. Geschützte Pfade (Tests, Evals, `sandbox.py`, `runner.py`, `improve.py`, `autonomy.py`, `executive.py`, `.claude/settings*.json`) werden abgelehnt. Binär, Symlinks und Submodule werden abgelehnt. Höchstens 3 Trials pro Tag (`max_trials_per_day`).
- `improve.py` ruft Claude nicht auf; der Patch kommt von außen.
- `taskengine.py` kennt Schritt-Arten `claude`, `local`, `pc`, `human`. Claude-Schritte schreiben nur in den Arbeitsordner des Auftrags (`outputs`). Ein Schritt `human` setzt den Auftrag auf `waiting_approval`.
- Fähigkeiten laufen im Sandbox-Jail, nur der Arbeitsordner ist beschreibbar (`capabilities.py`). `improve.py` braucht dagegen das Git-Repo. Eine Fähigkeit `improve.trial` im Jail geht deshalb nicht ohne Weiteres.

## Zielbild
Auftrag-Typ `improve.*` mit fester Kette:
1. **Vorschlag (Claude-Schritt):** Claude bekommt den relevanten Quellausschnitt als Eingabe im Arbeitsordner und liefert `patch.diff` (Unified Diff). Kein Schreibzugriff aufs Live-Repo, kein Netz, nur Haiku/Sonnet.
2. **Gate (außerhalb des Jails, Task-Engine-Seite):** `improve.py trial` mit den unveränderten Prüfungen. Nur `improved` geht weiter; `neutral` nur mit `allow_neutral`; `rejected` beendet den Auftrag mit Begründung.
3. **Freigabe (`human`-Schritt):** Philipp sieht Diff, Dateiliste, Urteil, Testzahlen. Ohne Ja kein Weitergehen.
4. **Einspielen:** nur über `install-v16.sh` (neuer Release-Ordner) und, wo Root nötig ist, per Sudo-Skript von Philipp. `rollback-v16.sh` ist der Rückweg (am 2026-10-15 live getestet). `improve.py promote` bleibt aus (`allow_promote: false`).
5. **Kennzeichnung:** `attribution.py` zeigt `Jarvis + Claude`.

## Grenzen (nicht verhandelbar)
- Keine Rechteausweitung: geschützte Pfade bleiben geschützt; Phase E darf `improve.py`, `sandbox.py`, `runner.py` und die Prüfungen selbst nie ändern.
- Not-Aus (`killed(brain)`) bricht Vorschlag und Gate ab.
- Budget pro Lauf und höchstens ein `improve.*`-Auftrag gleichzeitig.
- Klasse C (Geheimnisse) nie in die Eingabe; Eingabe vorher durch `runner.redact`.
- Wochenauslastung beachten (64 % am 2026-10-15); keine Dauerschleife, nur auf Zuruf.

## Offene Entscheidung
Wie läuft das Gate, da `improve.py` das Git-Repo braucht, die Fähigkeiten aber im Jail laufen?
- **Option A (empfohlen):** eigener Engine-Schritt `kind: 'improve'` in `taskengine.py`, der `Improver.trial` direkt aufruft (wie `_run_local_step`, aber ohne Jail um den Aufruf; `improve.py` jailt den Kandidatencode selbst). Kleiner Eingriff, ein neuer Schritt-Typ im Plan-Validator (`taskengine.py:169-216`).
- Option B: Gate als separater Dienst-Aufruf per Brücke. Mehr Teile, kein Vorteil.

## Umsetzungsreihenfolge
1. Plan-Validator: Schritt-Art `improve` (Schlüssel `patch`, `checks`, `description`), Tests in `tests/test_v16_engine.py`-Stil.
2. Engine: Schritt ausführen, Ergebnis (Urteil, Trial-ID) im Ereignisprotokoll.
3. Vorlage für den Plan (Claude -> improve -> human) und Aufnahme in die Auftragsarten.
4. Test im Staging (`~/tmp/jarvis-stage`, volles Release-Layout), dann Einspielen über `install-v16.sh --no-cron`.
5. Echter Lauf mit kleiner, harmloser Änderung; danach Rollback testen.
