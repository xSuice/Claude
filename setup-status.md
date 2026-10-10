# Setup-Status KI-Arbeitsplatz

Auftrag: `C:\Users\andre\Downloads\Claude-Code-Gesamtprompt-v2.md` (einmalig, nicht dauerhaft laden).
Stand: 2026-10-09

## Phase 1: Bestand und Interview, abgeschlossen (nur lesend)

Ergebnis:
- Claude Code 2.1.294. Keine globale CLAUDE.md, keine Rules. Projekt-CLAUDE.md 31 Zeilen.
- 7 Plugins: ecc (293 Skills, 68 Agenten), superpowers, caveman, ctx, fixmyprompt, security-guidance, session-report.
- Router: ma-auto-router V7 (`~/.claude/mods`, allowFable=false) und älterer `.claude/model-router` im Projekt.
- MCP: gmx (global), context7 (Projekt). Viele claude.ai-Konnektoren verbunden.
- Auto-Memory per Junction im Vault `_Claude-Memory/Auto-Memory`.
- Geprüft wurde nur "installiert/konfiguriert". "Aktiv" und "getestet" sind nicht belegt.

Offene Befunde für Phase 2:
1. Mehrere Gedächtnis-Schreiber (Auto-Memory, ECC-Sessiondaten, ctx, Librarian).
2. ECC-GateGuard blockiert den ersten Bash- und Write-Aufruf (Reibung).
3. Zwei Router (Mod und Projekt), dazu registrierte, nicht aktive Router-Marktplätze.
4. `refine` doppelt (`~/.claude/skills/refine` und `fixmyprompt:refine`).
5. Keine Schutz-Permissions außer GMX, kein fallbackModel.
6. Vault-Wurzel mit vielen losen Dateien, keine Vault-CLAUDE.md. Ordner `ChatGPT/` leer.
7. Nicht geprüft: `scripts/`, geplante Tasks, DeepSeek-Exporte, ChatGPT-Erinnerungsdatei.

Profil: `Obsidian Vault/_Claude-Memory/Profil.md`

## Phase 2: Überschneidungen, angewendet (2026-10-09)

Zuständigkeiten (Soll):
- Modellwahl und Effort: ma-auto-router V7.
- Langzeitgedächtnis: Obsidian-Vault über Auto-Memory und Librarian. ECC-Sessiondaten und ctx-Snapshots schreiben noch mit (offen).
- Promptverbesserung: fixmyprompt.
- Harte Sperren: Permissions (Phase 3).

Änderungen (Backup: `~/.claude/settings.json.bak-20261009-phase2`):
- `settings.json`: `env.ECC_DISABLED_HOOKS` = `pre:bash:gateguard-fact-force,pre:edit-write:gateguard-fact-force`.
- `settings.json`: Marktplätze `modelrouter` und `claude-router-marketplace` entfernt.
- `settings.json`: `caveman@caveman` auf `false`.
- `~/.claude/skills/refine` -> `refine.disabled` (Datei `SKILL.md.disabled`).
- `.claude/model-router` -> `model-router.disabled`.

Rücknahme: Backup zurückkopieren, beide Ordner zurückbenennen, `SKILL.md.disabled` zurück zu `SKILL.md`.

Status: Dateien geprüft. **Wirkung ungetestet.** Test in neuer Sitzung: erster Bash- und Write-Aufruf ohne GateGuard-Sperre, Caveman-Stil weg.

## Phase 3: Absicherung, angewendet (2026-10-09)

Backup: `~/.claude/settings.json.bak-20261009-phase3`.
- `permissions.deny` +6: Read auf `duckdns-token.txt`, `.env*`, `~/.ssh/**`, `~/.claude/secrets/**` (Skripte `zima-extra-*` und `ma-home-zusatz.py` wieder lesbar, Lernstoff); Bash `rm -rf *`, `git push --force*`.
- `permissions.ask` +12: Gmail send/reply/forward, Multi Mail send/reply/forward/drafts_send, Dropbox delete, Supabase execute_sql/apply_migration/delete_branch, Vercel buy_domain.
- `fallbackModel`: `["haiku"]`. CLI kennt `--fallback-model`, das Settings-Feld ist ungeprüft.
- Neue globale `~/.claude/CLAUDE.md` (10 Zeilen Grundregeln).
- `duckdns-token.txt` aus der Vault-Wurzel nach `~/.claude/secrets/` verschoben (Wert nicht gelesen). **Token bei DuckDNS erneuern** (lag im Vault).

Befunde ohne Änderung: wahrscheinliche Zugangsdaten in `zima-extra-*.sh`, `ma-home-zusatz.py`, Minecraft-Plugin-Configs (DiscordSRV, playit-gg). `conversations-*.json` in der Vault-Wurzel = vermutlich ChatGPT-Export (Phase 4b). Kein `.git` im Projekt.

Status: **ungetestet.** Test in neuer Sitzung: deny-Zugriff scheitert, ask-Zugriff fragt, normaler Zugriff klappt, GateGuard bleibt aus.

## Phase 4: Gedächtnis, angewendet (2026-10-09)

Backups: `C:\Users\andre\VaultBackup\memory-20261009` (Kopie von `_Claude-Memory`), `~/.claude/settings.json.bak-20261009-phase4`.
- Neu: `Obsidian Vault/CLAUDE.md` (Vault-Karte, Regeln).
- `_Claude-Memory/Index.md`: `[[Profil]]` verlinkt, Regeln 7 bis 9 ergänzt (Metadaten, Hypothesen, ein Langzeitspeicher).
- `ctx@claude-code-ctx` auf `false`. Maßgeblicher Langzeitspeicher = Vault. ECC-Sitzungsdateien (`~/.claude/session-data`) bleiben kurzlebig und speisen nichts ein.
- Vault hat kein Git (Medienmenge). Dauerhafte Sicherung nur als Vorschlag, noch nicht angelegt (Phase 8).

Rücknahme: `Index.md` aus dem Backup zurückkopieren, Vault-`CLAUDE.md` löschen, ctx auf `true`.
Status: ungetestet. Test in neuer Sitzung: Testnotiz anlegen, in neuer Sitzung per Suche finden, danach entfernen.

## Phase 4b: Altbestand, Stufe 1 (2026-10-09, lokal, nur Metadaten)

- ChatGPT-Export: 971 Chats, 2024-05-15 bis 2026-10-07, ca. 4 Mio. Tokens. Originale unverändert im Vault-Root.
- Neu: `_Claude-Memory/Import/ChatGPT-Index.md` (Datum, Titel, Nachrichten, Zeichen, Datei, ID) und `ChatGPT-Fortschritt.json` (verarbeitet: leer). Skript: Scratchpad `chatgpt_index.py` (wiederholbar, überschreibt nur den Index).
- Limit erster Durchlauf: höchstens 50 Chats, danach Rückfrage.
- ChatGPT-Erinnerungsdatei: nicht im Export. Muss von Philipp aus ChatGPT kopiert werden (Einstellungen, Personalisierung, Erinnerungen).
- DeepSeek: nichts auf dem PC. Browser öffnet `chat.deepseek.com/sign_in`. **Anmeldung durch Philipp nötig.** Danach Export-Funktion prüfen, sonst Chats auslesen.

Rücknahme: `_Claude-Memory/Import/` löschen.

### Stand 4b (2026-10-09, später)
- 49 von 971 ChatGPT-Chats verarbeitet (Test + Stapel 1 bis 4), 41 Notizen unter `_Claude-Memory/Import/ChatGPT/`. Limit 50 fast erreicht, danach Rückfrage.
- Übersicht `Import/ChatGPT-Import.md`, verlinkt aus `Index.md`. Hubs von Philipp nicht verändert (Notizen verweisen per Wikilink auf Hubs).
- Ausgelassen (privat/Klasse B): Beziehung, Düfte, Bart, Bildbewertung, Supplements, Auto-Tuning, Kindergeld, Mikrofon.
- Stichprobe von 5 Notizen gegen die Originale durch Philipp: **offen**.
- Im Chat "Docker Dienste einrichten" stand ein DuckDNS-Token im Klartext (nicht übernommen). Token erneuern.
- Angehängte ZIP `39e6809f…zip` im Download-Ordner ist 22 Byte (leer).
- DeepSeek: Browser-Pane des Assistenten ist nicht angemeldet (Philipps Screenshot stammt aus einem anderen Fenster). Offen: im Pane anmelden oder Claude in Chrome nutzen (Zugriff auf Philipps echten Browser, nur nach seiner Zustimmung).
- ChatGPT-Erinnerungsdatei: weiter nicht geliefert.

### Limit aufgehoben (Philipp, 2026-10-09)
- ChatGPT: 90 von 971 Chats verarbeitet (Stapel 1 bis 6, mit Sammelnotizen). Restliche Chats sind überwiegend privat oder kurz und werden nicht übernommen. Übersicht: `Import/ChatGPT-Import.md`.
- Weitere Kandidaten mit Themenbezug gibt es kaum noch (Filter: Server, Programmieren, Minecraft, Schreiben, Ausbildung).

### Stand 2026-10-10
- Philipp hat beide Exporte selbst entpackt: ChatGPT (`Downloads/39e6809f…/`, enthält u. a. user_settings.json, library_files.json, Anhänge) und DeepSeek (`Downloads/deepseek_data-2026-10-10/`, 730 Chats, 27 Mio. Zeichen).
- Stichprobe (automatisch, nur Metadaten): 5 zufällige Notizen gegen die Originale geprüft. IDs, Titel und Datum stimmen. Inhaltlicher Abgleich nicht erfolgt.
- DuckDNS-Token: Philipp verzichtet auf Erneuerung (seine Entscheidung, Risiko bleibt: Token steht im Original-Export und in `~/.claude/secrets/`).
- DeepSeek: `Import/DeepSeek-Index.md` (730 Chats), `DeepSeek-Fortschritt.json`, 4 Sammelnotizen (Heimserver 29 Chats, Claude/Codex 9, Eternal Bonds/SMP 96, Bewerbungen 19), Übersicht `DeepSeek-Import.md`, verlinkt aus `Index.md`. 153 Chats gruppiert; Rest überwiegend privat oder ohne Themenbezug.
- Offen: ChatGPT-Erinnerungstext (nicht im Export), neue Sitzung für Tests, Phase 5.

### Phase 4c Mails und Dienste (2026-10-10, nur lesend, Metadaten)
- Alle Postfächer "of all time" über Betreff/Absender/Datum ausgewertet. GMX 1: 2.258 Mails (Gesendet 156), GMX 2: 8.377 (Gesendet 7), Gmail ca. 200 Threads, Hotmail wenig. Themenabfragen: Bewerbung (42), Ausbildung (22), Fahrschule, Führerschein, Arbeitsagentur.
- Neu im Vault `_Claude-Memory/Dienste/`: `Verbundene-Dienste.md`, `Termine-und-offene-Vorgaenge.md`, `Mail-Zeitleiste.md`. Ohne Namen Dritter, ohne Zahlungs-/Kontodaten.
- Nicht gelesen: Mailinhalte (Fahrschulwechsel, Arbeitsagentur), Drive-/Dropbox-Dokumentinhalte. Offen: Drive/Dropbox-Index, Inhalte nach Freigabe.
- Hinweis: Das Durchsuchen aller 10.600 GMX-Mails einzeln wäre nur Newsletter-Rauschen. Gezielte Themenabfragen reichen. Weitere Themen auf Zuruf.

### Stand 2026-10-10 (später): Mails, Dateien, DeepSeek komplett
- Mails gelesen (mit Freigabe): Fahrschulwechsel-Antwort (nur Telefonnummer, nicht gespeichert), Arbeitsagentur (nur Portalhinweis). Eingetragen in `Dienste/Termine-und-offene-Vorgaenge.md`.
- Neu `Dienste/Dateien-Drive-Dropbox.md` (Index, ohne Inhalte). Drive-Ordner "Songs" (osu!-Beatmaps) ist Ballast.
- DeepSeek: alle 730 Chats Gruppennotizen zugeordnet (`Import/DeepSeek/`, 16 Dateien inkl. Heimserver, Claude/Codex, Eternal Bonds, Crimson Zone, Minecraft, Audio, Training, Geld, Tabak, Stil). Private Bereiche nur auf Themenebene, Gesundheit/Beziehung bewusst nicht zusammengefasst. Browser war nicht nötig, der Export reichte.
- ChatGPT: private Chats (ca. 880 von 971) weiter nur im Index, nicht zusammengefasst. Auf Zuruf nach Thema.

### Roharchiv (2026-10-10)
- Alle eigenen Nachrichten aus beiden Exporten vollständig im Vault: `_Claude-Memory/Import/raw/ChatGPT/` (28 Monate) und `raw/DeepSeek/` (21 Monate), 7,3 MB, nach Monat. IDs, Tokens, Passwörter, IBANs geschwärzt. KI-Antworten nicht enthalten (Originale in den Exportordnern). Skript: Scratchpad `raw_archive.py`, wiederholbar.
- Regel 7 in Vault-`CLAUDE.md`: raw nur gezielt per Suche lesen.
- Mails: bisher nur Betreff/Absender gezielter Themen. Vollständige Auswertung offen (siehe Rückfrage).

### Mail-Indizes (2026-10-10, Hilfsagenten, nur lesend)
- `Dienste/Mail-Index-Gmail-Hotmail-Kalender.md`: Gmail ca. 165 von 201 Threads gesichtet (alle 14 gesendeten), Hotmail ca. 210 Mails (2014 bis 2017 nicht bis zum Ende), Kalender 65 Einträge. Nur Snippets, keine Volltexte.
- `Dienste/Mail-Index-GMX.md`: Gesendet vollständig (gmx 156, gmx2 7). INBOX nur per Themenfilter, **nicht vollständig** (gmx 2.258 und gmx2 8.377 Mails, gmx2 bis auf Stichprobe ungesichtet, Spam/Gelöscht/Entwürfe ungesichtet). Anfang von 8 wichtigen Mails gelesen.
- Offene Prüfpunkte für Philipp: Retoure-Erstattung (Zigarettenstopfmaschine24, Stand 2026-09-14), Konto-Zugriffe Dritter nach der Dienste-Anbindung, ngrok_recovery_codes.txt im Vault-Root (Geheimnis, nicht geöffnet), Frage nach weiteren KI-Diensten.

### Phase 5 und Geheimnisse angewendet (2026-10-10)
Backups: `~/.claude/settings.json.bak-20261010-phase5`, `router-config.json.bak-20261010`, `CLAUDE.md.bak-20261010`.
- `router-config.json`: `maxEffort` von `max` auf `xhigh`.
- `settings.json`: `availableModels` = haiku, sonnet, opus (Fable ausgeschlossen). **Wirkung ungetestet**: Laut Doku ist das Feld für Managed-Settings gedacht. Test in neuer Sitzung: `/model fable` muss abgelehnt werden. Wirkt es nicht, kommt ein `PreModelSwitch`-Hook (mit Test).
- Globale `CLAUDE.md`: Zeile 11 (manuelle Modellwahl hat Vorrang, Router schlägt nur vor).
- `ngrok_recovery_codes.txt` aus der Vault-Wurzel nach `~/.claude/secrets/` verschoben (nicht geöffnet), `Read(**/ngrok_recovery_codes.txt)` gesperrt (15 deny-Regeln).
- Phase 6 bis 8 noch offen (Agenten/Skills, externe Helfer = bewusst nichts, Fachbereiche/Automatisierung).

### Phase 6 Agenten und Skills (2026-10-10)
- Belegte Nutzung (ECC-Tracker, 6 Einträge): `ma-server-ops` 4x, `obsidian-librarian` 1x, `computer-use` 1x. Die 293 ECC-Skills und 68 ECC-Agenten wurden nie benutzt.
- Entscheidung nach Erweiterungsstopp: **keine neuen Agenten, keine neuen Skills.** Der allgemeine Hilfsagent hat die Massen-Lesejobs (Mails) erledigt, eine Lücke ist nicht belegt.
- Angewendet: Import-Skripte als wiederholbare Werkzeuge in `MA-Server/scripts/chat-import/` (+ README). Keine Dauerlast im Kontext.
- Entscheidung Philipp: **`ecc@ecc` bleibt aktiv.** Phase 6 abgeschlossen. (Falls Kontext/Hooks später stören: Plugin per Schalter in `settings.json` deaktivieren.)

### Phase 7 externe KI-Helfer (2026-10-10, auf Philipps ausdrücklichen Wunsch)
- Entscheidung Philipp: Gemini, DeepSeek, ChatGPT sollen als externe Tools genutzt werden, um Tokens zu sparen. Umsetzung nur für **Klasse A**, über `MA-Server/scripts/ext-ai/ask.py` (Gemini, DeepSeek; API statt Browser, weil günstiger an Tokens und stabiler).
- Belegt (offizielle Seiten, 2026-10-10): Gemini-API hat kostenloses Kontingent für mehrere Modelle (z. B. `gemini-2.5-flash`), Gratis-Eingaben dürfen von Google zur Produktverbesserung genutzt werden. DeepSeek-API: OpenAI-kompatibel, Modelle `deepseek-flash`, `deepseek-v4-pro`, kostenpflichtig, Preis nicht belegt. Rate-Limits: nicht belegt.
- Schutz im Skript: ohne `--klasse-a` kein Senden, Blockade bei Passwort/Token-Mustern, langen Schlüsseln, E-Mail, IBAN, Telefon, max. 8000 Zeichen, kein Retry/Anbieterwechsel, Log ohne Inhalt. **Getestet** (1 Positiv-, 4 Negativfälle + fehlender Schlüssel).
- Globale `CLAUDE.md` Zeile 8 angepasst (Klasse A selbst, B/C nie). Zusätzliche Sperre `Bash(*.claude/secrets*)` (16 deny-Regeln). Backup `settings.json.bak-20261010-extai`.
- **Gemini echter Aufruf getestet (2026-10-10, ok):** Schlüssel von Philipp angelegt. Standardmodell `gemini-flash-latest`. `gemini-2.5-flash` steht in der Modellliste, liefert aber 404 ("für neue Nutzer nicht mehr verfügbar"). DeepSeek ungetestet (kein Schlüssel). ChatGPT/OpenAI nicht eingerichtet (Abo ≠ API).

### Graph vernetzt (2026-10-10, auf Philipps Wunsch "alles vernetzt")
- Messung `scripts/vault-graph.py`: vorher 202 von 463 Notizen ohne eingehenden Link (Ring aus Einzelpunkten im Graph), danach **0 von 467**. Jede Notiz ist über einen Hub erreichbar.
- Umsetzung `scripts/vault-vernetzen2.py`: neue Hubs `Roharchiv`, `Arduino`, `fixmyprompt Hub`, `Archiv-Dateien`; Index/Übersicht/MOCs/Review ergänzt; 99 Roharchiv-Monate mit Importnotizen und Hubs verbunden; 81 Importnotizen verweisen auf ihren Rohtext (nur deine Nachrichten und vollständig); 72 Notizen bekamen Elternhub-Links.
- Bewusst unverändert: Archiv-Paket vom 2026-10-07 (Manifest), Arduino-Bibliotheken, fixmyprompt-Kopie, Mod-Server-Archive. Sie sind nur von Hubs aus verlinkt (126 Notizen ohne ausgehenden Link, aber alle verbunden).
- Hinweis: Im Obsidian-Graph "Verwaiste Dateien" ausblenden bzw. Anhänge-Filter prüfen; Nicht-Markdown-Dateien (PDF, Bilder) erscheinen nur, wenn "Anhänge" aktiviert ist.

### Graph: Inseln und Geisterknoten (2026-10-10)
- Philipps Graph zeigte noch Inseln. Messung `scripts/vault-components.py`: alle 467 Notizen in einer Gruppe. Ursache der Inseln: **Geisterknoten**. Eingefügte Bash-Skripte in den Roharchiven (`raw-voll/DeepSeek/2026-09.md`: 62) und in einer Arduino-README enthielten `[[ ... ]]`, das Obsidian als Links auf nicht existierende Notizen zeichnet (`hideUnresolved=false`).
- Behoben: `[[` in Roharchiven und `ALog/README.md` zu `\[\[` entschärft (19 Dateien), Generatoren `raw_archive.py`/`raw_voll.py` ebenso. Geisterknoten jetzt 0.
- Philipp: Obsidian neu laden (Strg+R), Graph aktualisieren. Bleiben Inseln, bitte den Namen eines Knotens der Insel nennen (Knoten anklicken).

### Obsidian: Ausschlüsse und lose Knoten (2026-10-10)
- Lose Knoten im Graph: zwei leere `Unbenannt.base` (Review/Leer, Review/Unklar), jetzt im Hub `Review` verlinkt, nicht gelöscht. Obsidian war beim Neu-Indizieren von über 51.900 Dateien eingefroren (nur 467 Notizen).
- Obsidian beendet (ohne Zwang), `.obsidian/app.json` gesichert (`app.json.bak-20261010`), `userIgnoreFilters` mit 11 Ordnern gesetzt: Server-Archiv, Welten, Archive, Mod 1.21.4, Gradle-Projekt, KI-Exporte, Altbestand 2016/2019, Desktop-Altbestand, Dropbox-Kopie, PairDrop. Dateien bleiben erhalten, sie sind nur von Suche/Graph/Index ausgeschlossen. Hub `Minecraft SMP24`: Server-Archiv-Liste durch Hinweis ersetzt. Kaputte Links jetzt 0 (Vorlagentext `[[name]]` entschärft).
- Rückgängig: `app.json.bak-20261010` zurückkopieren.

### Graph verdichtet (2026-10-10, auf Philipps Hinweis auf acht lose Notizen)
- Die acht genannten Notizen (Mail-Index Gmail/Hotmail/Kalender, Einrichtungsauftrag, Termine, ChatGPT-Index, DeepSeek-Index, Librarian-Learned, ChatGPT-Erinnerung, Mail-Index GMX1) hatten nur 1 Verbindung (ein Link vom Index/Übersicht), das wirkt im Graph lose.
- `scripts/vault-vernetzen3.py`: Cluster Dienste/Fristen, Chat-Importe, Gedächtnis-Kern verlinken sich gegenseitig (Abschnitt `## Vernetzt`, 33 Notizen). `scripts/vault-vernetzen4.py`: Roharchive mit Vor-/Folgemonat und Gegenquelle, Geschwister-Ketten (`## Nachbarn`), 244 Notizen.
- Messung Verbindungsgrad (ohne ausgeschlossene Ordner): vorher 99 Notizen mit 1 und 136 mit 2 Verbindungen, jetzt 78 mit 1 und 36 mit 2. Rest = Archiv-Paket, Arduino-Bibliotheken, fixmyprompt-Kopie (bewusst unverändert, nur über Hubs verlinkt).

### Vault-Autopflege (2026-10-10, auf Philipps Auftrag "mach es automatisch, auch verlinken")
- Windows-Aufgabe `VaultAutopflege`: täglich 19:30, nachgeholt wenn der PC aus war, max. 10 Minuten, läuft **ohne Modell** (keine Tokenkosten). Skript `scripts/vault-autopflege.py`.
- Macht: lose Dateien der Vault-Wurzel nach festen Regeln einsortieren (wie `vault-organize.py`); neue Notizen (Wurzel und `00 Inbox`) regelbasiert nach Schlüsselwörtern einem Hub zuordnen, in dessen Ordner legen, `Übergeordnet`-Link setzen und im Hub unter `## Automatisch einsortiert` eintragen; ist der Hub nicht eindeutig, bleibt die Notiz in der Inbox. Bericht `_Claude-Memory/Pflege/Pflegebericht.md` (verlinkt aus Index und Übersicht), Rollback-Log `C:/Users/andre/VaultBackup/autopflege-moves.csv`.
- Macht nie: löschen, überschreiben, Ordner verschieben (neue Ordner in der Wurzel nur melden), Dateien unter 10 Minuten, geschützte Bereiche; max. 40 Verschiebungen pro Lauf; Geheimnisse (Backup-Codes, Recovery Keys) nach `~/.claude/secrets`.
- Getestet: Trockenlauf, echter Lauf mit Dummy-Dateien (Geheimnis, Notiz mit Hub und Link, Installer, Foto, Unbekanntes, zu neue Datei, Ordner), Lauf über den Windows-Planer (Ergebnis 0). Testdateien entfernt.
- Semantisches Einordnen (Inbox leeren nach Inhalt, tiefe Verlinkung) braucht ein Modell und bleibt auf Zuruf an Claude.
- Abschalten: `schtasks /Delete /TN VaultAutopflege /F`. Pausieren: `schtasks /Change /TN VaultAutopflege /DISABLE`.
- Beobachtung: Eine leere `LICENSE.md` in der Wurzel (von Obsidian beim Klick auf einen unaufgelösten Link angelegt) wird beim nächsten Lauf nach `Review/Leer` verschoben.

### Tägliche Routinen (2026-10-10, auf Philipps Auftrag)
- Aufgaben in der Claude-App (laufen nur bei offener App, sonst beim nächsten Start; verwaltbar unter "Scheduled"): `taegliche-mailpruefung` (19:45, nur lesend: Gmail, Hotmail, GMX 1, GMX 2, Kalender; Bericht `Dienste/Mail-Tagesbericht.md`, Budget 25 Werkzeugaufrufe, kein Senden/Löschen/Markieren) und `taegliche-kalenderfristen` (20:10, liest Mailbericht und Fristen-Übersicht, trägt nur eindeutig datierte, zukünftige Fristen als neue Ereignisse ein, ohne Gäste, ohne Duplikate, ohne Ändern/Löschen, max. 5 pro Lauf; Log `Dienste/Kalender-Eintraege.md`).
- Beide Testläufe erfolgreich (Mail: 5 Quellen ok, 64 Mails, 1 wichtiger Vorgang; Kalender: nichts neu, 3 schon vorhanden erkannt, unklare Daten korrekt nicht eingetragen).
- **Kostenhinweis:** Die Aufgaben-Sitzungen starteten mit Opus (Aufwand mittel), vermutlich durch das Code-Tab-Modell oder die Router-Hochstufung wegen Wörtern wie "Passwörter". Testläufe wurden per `set_session_model` auf Sonnet/low gestellt. Plan Pro: 5-Stunden-Limit zum Zeitpunkt 53 % genutzt, Woche 8 %. Philipp sollte im Code-Tab Sonnet als Standard wählen und nach den ersten Tagen die Nutzung prüfen. Pausieren: in der App unter "Scheduled" ausschalten.

### Testlauf "teste alles" (2026-10-10, später)
- Bestanden: `settings.json` gültig (16 deny, 14 ask, availableModels 3, fallbackModel 1); frische Claude-Instanz (haiku) lädt globale `CLAUDE.md` inkl. Regeln 8 und 12; `ask.py` Schutz (Positiv/E-Mail/bezahltes Modell/ohne Flag blockiert), Echtaufrufe Gemini (Paris) und Ollama (Madrid) ok; DeepSeek ohne Schlüssel erwartungsgemäß abgebrochen; GateGuard aus; Deny auf Schlüsselordner (Read und Bash).
- Auffällig: OpenRouter lieferte beim Gratis-Modell 429 (Limit), nicht dauerhaft kaputt (früherer Test ok). Ollama läuft jetzt (Prozesse `ollama`, `ollama app`), Autostart nicht belegt.
- **Nicht getestet (Absicht):** `/model fable` gegen `availableModels` und `fallbackModel` im Ernstfall. Ein Test über `claude -p --model fable` würde Fable ohne Rückfrage abrechnen. Philipp testet interaktiv in der App (`/model fable`, dort kommt eine Bestätigung vor Abrechnung). Außerdem ask-Regeln (Gmail senden, Dropbox löschen u. a.) nicht ausgelöst.

### Vault-Organisation (2026-10-10, auf Philipps Auftrag)
- Vault-Wurzel hat keine losen Dateien mehr (nur Bereichsordner 00 bis 90, geschützte Ordner, Hubs `Übersicht`, `CLAUDE.md`, `Wikilinks`). 677 Verschiebungen, nichts gelöscht/umbenannt, 0 fehlende Ziele. Log (Rollback): `C:\Users\andre\VaultBackup\organize-20261010-moves.csv`; Rückgängig: `python scripts/vault-organize.py undo <Log>`.
- Skripte: `MA-Server/scripts/vault-organize.py` (plan/run/undo), `vault-linkcheck.py`, `vault-vernetzen.py`.
- Geheimnisse aus dem Vault nach `~/.claude/secrets` (Google-Backup-Codes, Norton-Recovery-Key; nicht gelesen).
- KI-Exporte jetzt unter `90 Archiv/KI-Exporte/`. Import-Skripte angepasst. **Pannen und Reparatur:** Der Indexlauf `chatgpt_index.py` hat mit altem Pfad `ChatGPT-Index.md` leer geschrieben und `ChatGPT-Fortschritt.json` zurückgesetzt. Beides wiederhergestellt (971 Zeilen, 90 IDs aus Notizen), Skript überschreibt Fortschritt nie mehr.
- Vernetzung: neue Hubs `Minecraft SMP24`, `MA-Server`, `Gesundheit`; Hubs `Übersicht`, `Leben overview`, `Projekte`, `Crimson Zone`, `Projekt Schmejd`, `Technik`, `Medien`, `Archiv` ergänzt; 81 Importnotizen mit `## Verwandt` zu Hub und Import-Übersicht; 3 kaputte Querverweise repariert. Rest kaputter Links: nur Bibliotheks-READMEs (Arduino) und Vorlage.
- Offen: `00 Inbox/Review/Unklar` (77 Dateien) und `Review/Duplikate` (322, überwiegend ChatGPT-Export-Wurzelkopie) zum Sichten; 55 verwaiste Notizen (Arduino-READMEs, Archivdokumente, bewusst unverändert).

### ChatGPT-Erinnerung (2026-10-10)
- Text von Philipp eingefügt, abgeglichen (`Import/ChatGPT-Erinnerung-Vorschlaege.md`), auf Bestätigung ("übernehmen wie empfohlen") in `Profil.md` übernommen. Geändert: Ausbildung läuft seit 2026-09-01 (statt "geplant"), Führerschein "in Arbeit" (statt "besitzt"). Training/Technikliste als ungeprüfte Präferenz.

### Nach Abschluss (2026-10-10)
- Einmalige Sicherung der Wissensdaten: `C:\Users\andre\VaultBackup\notes-20261010` (619 Dateien, 96,6 MB; `_Claude-Memory` komplett, alle Notizen, Obsidian-Einstellungen, ohne Medien und Exporte). Wiederholbar mit `MA-Server/scripts/vault-backup.ps1`. Keine geplante Aufgabe angelegt.
- Neu: `Dienste/Fristen-Uebersicht.md` (Fahrschule 12.10., Klarna/Inkasso, Kindergeld, Retoure, Konten prüfen, Klassenarbeit 17.11.).
- GMX 2 (8.377 Mails, fast nur Newsletter, 7 gesendet): bewusst nicht Seite für Seite durchgelesen (ca. 2 Mio. Tokens für fast keinen Nutzen). Auf Zuruf.

### Phase 8 und Abschluss (2026-10-10)
- Phase 8: nichts Dauerhaftes eingerichtet (keine Skills, keine geplante Aktualisierung). Lernregel: zweimal gleiche Korrektur ergibt eine Regel.
- Abschlussbericht: `Obsidian Vault/_Claude-Memory/Abschlussbericht-Einrichtung-2026-10-10.md`. Einrichtungsauftrag archiviert: `_Claude-Memory/Archiv/Einrichtungsauftrag-v2-2026-10-09.md` (Kopie, Original in der Vault-Wurzel unverändert).
- Status insgesamt: Phasen 1 bis 8 durchgeführt. **Offen:** Test in neuer Sitzung, optionale Schlüssel (OpenRouter, DeepSeek), ChatGPT-Erinnerungstext.

### Weitere kostenlose Modelle (2026-10-10)
- OpenRouter in `ask.py` eingebaut (nur `:free`-Modelle, bezahlte blockiert, getestet). Schlüssel angelegt, **echter Aufruf getestet (ok, 2026-10-10)**. 19 kostenlose Modelle gelistet (u. a. Gemma 4, Nemotron).
- Geprüft, nicht eingebaut: Groq (Gratis-Limits nicht belegt), Cerebras (kein dauerhaft kostenloser Tarif, nur 30 Tage Startguthaben mit Zahlungsmethode), Mistral (Seite nicht erreichbar), OpenAI (Abo ≠ API).
- **Lokales Modell installiert (auf Philipps Freigabe, 2026-10-10):** Ollama 0.40.2 (Installer geprüft: Größe stimmt, Signatur Ollama Inc. gültig) und `gemma3:4b` (3,4 GB). `ask.py ollama` getestet: deutsche Antwort ok, ca. 19 s, 100 % GPU (RTX 2060). Lokal auch Klasse B erlaubt, Klasse C blockiert. Globale `CLAUDE.md` Zeile 8 angepasst (Backup `CLAUDE.md.bak-20261010b`). Installer `Downloads\ollama-setup\OllamaSetup.exe` (1,5 GB) kann gelöscht werden. Auf der Ollama-Downloadseite stand ein Block mit Anweisungen an KI-Agenten; ignoriert.

### Vollarchive (2026-10-10, später)
- Philipp hat beide Exportordner (ChatGPT, DeepSeek) und die ZIPs in die **Vault-Wurzel** verschoben. Skripte angepasst, Quellen: `Obsidian Vault/39e6809f…/` und `Obsidian Vault/deepseek_data-2026-10-10/`. Die früheren Pfade unter Downloads gelten nicht mehr.
- Neu `_Claude-Memory/Import/raw-voll/` (35 MB): vollständige Dialoge (Du und KI), ChatGPT 28 Monate (15,7 Mio. Zeichen), DeepSeek 21 Monate (18,7 Mio., ohne internes "Denken"). IDs/Tokens/IBAN geschwärzt, ChatGPT-Zitatmarker entfernt. Skript `raw_voll.py`.
- Gemini: alle 31 Chats im Volltext unter `raw-voll/Gemini/Gemini-Chats.md`. Es sind fast nur Sprachbefehle.
- Hinweis: Roharchive (`raw`, `raw-voll`) nie komplett laden. Obsidian-Plugins (Smart Connections) könnten die großen Dateien indexieren und langsam werden. Falls ja, Ordner in den Plugin-Einstellungen ausschließen.
- GMX 1 INBOX vollständig: alle 23 Seiten (2.258 Mails) geprüft, 335 aufgenommen, 1.923 aussortiert (Kategoriezahlen ±10 %). Dateien: `Dienste/Mail-Index-GMX1-INBOX-vollstaendig.md` plus Jahresdateien `Mail-Index-GMX1-2021…2026.md`. Nur Absender/Betreff, kein Volltext.
- Befunde: ab Mai 2026 mehrere Kredit-/Kreditkartenanträge (teils abgelehnt), Klarna-Mahnung (2026-07-01) und "Letzter Hinweis" (2026-09-10), Inkassomail (coeo) mit Datum 2026-10-10 (Echtheit über Klarna-App prüfen, keine Links anklicken), Betrugsmuster beim Saab-Verkauf (2025-08/09), 7 GMX-App-Passwort-Ereignisse am 2026-10-09 (vermutlich MCP-Einrichtung).

### Gemini (2026-10-10)
- Philipp nutzt ChatGPT, DeepSeek, Gemini (Antwort auf Rückfrage zu weiteren KI-Diensten). Gemini: `Import/Gemini-Index.md` (ca. 30 Chats, ca. 110 Aktivitäten, Titel/Kurzprompts). Vollständige Chats nur auf Zuruf oder per Google Takeout. Hinweis: "Aktivitäten speichern" steht auf An (Training möglich).
- Phase 7 (externe KI-Helfer): nichts eingerichtet, keine API-Schlüssel, Rückfrage bei jedem externen Aufruf. Erweiterungsstopp gilt.

### DeepSeek (2026-10-09, Brave-Browser per Claude-in-Chrome-Erweiterung)
- Export ist bereit (Einstellungen, Daten, "Herunterladen", gültig bis 2026-10-16 22:00). Download wartet auf Philipps Freigabe.
- Der Schalter "Modell für alle verbessern" steht jetzt auf AUS (von Philipp geändert).
- Zugriff klappt über einen eigenen Tab in Philipps Browser (angemeldet, nur lesend). Sidebar zeigt ca. 100 Chats; viele Server-Chats ("Heimserver Setup" u. a.), Claude Code vs Codex, MCP bei Claude, ECC Agents für Codex, Lebenslauf. Viele private Themen (Tabak, Bank, Gesundheit, E-Bike), die nicht ins Gedächtnis kommen.
- Offizielle Exportfunktion vorhanden (Einstellungen, Daten, "Daten exportieren", Download-Link 7 Tage gültig). Export wurde angestoßen, wartet auf Bereitstellung. **Download nur nach Philipps Freigabe** (Dateiname, Quelle, Größe nennen).
- In DeepSeek steht "Modell für alle verbessern" (Training mit Chats) auf AN. Nicht geändert. Philipp entscheidet.

## Nächste Schritte
- Neue Sitzung starten: GateGuard-, Permission- und Wiederfind-Test.
- Philipp: Stichprobe, DuckDNS-Token erneuern, DeepSeek-Anmeldung, Erinnerungstext.
- Danach Phase 5 (Router und Arbeitsweise).
- Offen: ECC- und ctx-Gedächtnisschreiber, Langzeitgedächtnis auf einen Schreiber bringen.
- CLAUDE.md-Kurzfassung (max. 10 Zeilen) liegt als Entwurf im Profil, noch nicht übernommen.

- 2026-10-10: Kalenderaufgabe erweitert (Geburtstage, undatierte Aufgaben als Vorschlagstermine 19:00, max. 10/Lauf). 5 Aufgaben manuell eingetragen, Geburtstage waren schon im Kalender.

### MA-Server Zentrale (2026-10-10)
- Server ist ein Laptop (Akku 0 %, Deckel-Suspend-Standard). Spiegel PC->Server stündlich (Task VaultZuServer), Härtungsskript auf dem Server, noch nicht ausgeführt (Sudo). Details: Vault `30 Technik/MA-Server/MA-Server Zentrale.md`. Abschalten: schtasks /Delete /TN VaultZuServer /F.

### MA-Librarian pausiert (2026-10-10)
- Task MA-Librarian (alle 10 Min, Claude-Aufrufe pro Datei) deaktiviert: Warteschlange wuchs auf ca. 97 000 offene Dateien (Vault-Import und Umbau), Läufe hingen, Gefahr für Nutzungslimit und für die Ordnung. Wieder aktivieren: schtasks /Change /TN MA-Librarian /ENABLE (erst Warteschlange begrenzen). Ersatz ohne Modell: VaultAutopflege (lokal) und server-to-vault.py (Server).

### MA Home Desktop-App (2026-10-10)
- app/desktop (Electron), Claude Code 2.1.296 auf dem Server installiert (~/.local/bin/claude, offizieller Installer), Anmeldung durch Philipp offen. Getestet: Start, Serverstatus, Chat bis zur Meldung "Nicht angemeldet".
