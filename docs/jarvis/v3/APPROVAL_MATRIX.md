# APPROVAL_MATRIX – MA-HOME JARVIS (Stand 28.10.2026, 04:15 – Owner: „mach alles fertig los“ = empfohlenes Paket freigegeben)

Grundlage: `MA-HOME_JARVIS_KIMI_VOLLPaket.zip` mit Abschnitt 0–0.6, Teil A–D und den beiden Originalanhängen. Die Einträge folgen dem Schema aus 0.2.
Status: `VORSCHLAG | GENEHMIGT | ABGELEHNT | UMGESETZT | VERIFIZIERT`. Prüftiefe: *Doku geprüft · lokal getestet · synthetisch E2E · Zielgerät offen*.
Antwort per ID genügt („VOICE-004 ja“, „HQ-001 zurückstellen“). **Empfohlenes Gesamtpaket:** SEC-001, VOICE-004, VOICE-007, OPS-003, CORE-003, UX-001. Alles andere ist optional.

Bestands- und Evidenzdokumente, auf die verwiesen wird: `IST-SOLL-MATRIX.md`, `V3-ENTSCHEIDUNGSUNTERLAGE.md`, `DEEPSEARCH-GESAMTAUFTRAG.md` (41 Quellen), `REFERENZKATALOG-20261027.md` (24 Bausteine, Lizenzen per GitHub-API), `V3-SPRACHE-WAKEWORD-ENGINE-20261027.md`, `V3-SPRACHE-SIGNAL-WORKER-20261027.md`, `PORTAL-REDESIGN-KONZEPT-20261027.md`, `design-varianten.html`, `stimmen/`, `STATE.md`.

---

## P0 – Sicherheit

```yaml
proposal_id: SEC-001
bereich: "Portal-Proxy-Schlüssel (X-MA-Key) rotieren"
quelle: "eigener Befund 27.10. – der Schlüssel stand beim Lesen der Caddyfile einmal im Klartext in meiner lokalen Hermes-Sitzung"
bestand: "/etc/ma-home/Caddyfile (header_up X-MA-Key), /etc/ma-home/portal.json proxy_key, Test-Proxy liest ihn per ssh"
option: "neu erzeugen (secrets.token_hex(32)), Caddyfile + portal.json + manage.py-Vorlage gleichzeitig, caddy validate, Neustart Caddy + Portal"
benutzererlebnis: "keins (ca. 5 s Unterbrechung)"
begründung: "Wer den Schlüssel hat und 127.0.0.1:18765 erreicht, kann jeden Benutzer spielen. Lokal und nicht öffentlich, aber ein Leak bleibt ein Leak."
risiken: ["falsche Reihenfolge = 401 für alle bis zur Korrektur (Rollback: Backups)"]
ressourcen: "keine"
kosten: "keine"
auswirkungen: "Auth-Kette; Rollback *.bak-vor-keyrotation"
abnahme: ["alter Schlüssel → 401", "neuer Schlüssel nur in den 2 Dateien", "Portal + Statusmonitor grün"]
status: VERIFIZIERT 28.10. – neuer Schlüssel (Fingerprint 6b90462a) in portal.json, Caddyfile, state.json; alter Schlüssel → 401, neuer → 200, öffentlich 302 (Login), Kuma 8/8 grün; Backups *.bak-vor-keyrotation-20261027. Alte Kopien in root-only Backups sind wertlos, weil der alte Schlüssel abgewiesen wird.
```

```yaml
proposal_id: SEC-002
bereich: "Windows-Profil C:\\Users\\andre erbt Laufwerks-ACL („Authentifizierte Benutzer: Ändern“)"
bestand: "icacls-Befund während der Worker-Reparatur; %LOCALAPPDATA%\\Packages bereits korrigiert (Backup packages-acl-backup-20261027.txt)"
option: "Profil-ACL auf Windows-Standard (SYSTEM, Administratoren, andre) mit Backup; per UAC"
risiken: ["falsch gesetzte ACL kann Anmeldung/Apps stören – nur mit Backup und /restore-Weg"]
kosten: "keine"
abnahme: ["andere lokale Konten können das Profil nicht mehr lesen", "Hermes, Steam/Spiele, PC-Worker laufen weiter"]
status: VORSCHLAG (Owner-Entscheidung, betrifft das ganze Windows-Profil)
```

```yaml
proposal_id: SEC-003
bereich: "CSP für WebAssembly (Sprach-Engine)"
bestand: "Caddy script-src 'self' → 'self' 'wasm-unsafe-eval' (kein JS-eval); Backups *.bak-vor-voiceengine-20261027"
status: VERIFIZIERT (0 CSP-Verstöße im Browser, Modell lädt in 1–3 s)
```

## P1 – Echter Start, Persistenz, Recovery, Betrieb

```yaml
proposal_id: OPS-001
bereich: "Unabhängiger Dienste-Wächter mit Handy-Alarm"
quelle: "louislam/uptime-kuma 2.x (MIT), Image sha256:20abea8c…; eigene Signal-Brücke"
bestand: "Container ma-uptime-kuma (nur 127.0.0.1:3001, 142 MB RAM, 0,5 CPU), 8 Monitore, Webhook → kuma_signal_bridge.py (127.0.0.1:18772, Token, 10-min-Drossel) → eigener Signal-Self-Chat; Portal /api/jarvis/health + Command-Center-Karte"
benutzererlebnis: "Fällt ein Dienst aus, kommt eine Signal-Nachricht; im Command Center sind alle Dienste mit Antwortzeit sichtbar"
risiken: ["Monitor öffentlich prüft lokal (kein NAT-Hairpin) → beweist Caddy+TLS+Zertifikat, nicht den Weg aus dem Internet"]
abnahme: ["8/8 up", "echter Alarm wurde gesendet (Portal öffentlich: down vor Hairpin-Fix)", "Bridge 5/5 Tests, Health-API 3/3"]
status: VERIFIZIERT
```

```yaml
proposal_id: OPS-002
bereich: "PC-Hilfsdienste starben unbemerkt (Sprachdienst, Tunnel)"
bestand: "Ursache: Neustart aus einer Hermes-Sitzung → Prozess hing im Hermes-Prozessbaum und wurde mit beendet. Jetzt per WMI (Win32_Process.Create) außerhalb gestartet; OPS-001 meldet künftige Ausfälle"
status: UMGESETZT (Dauerbeobachtung über OPS-001)
```

```yaml
proposal_id: OPS-003
bereich: "Watchdog-Takt laut Auftrag: Heartbeat ~30 s, Fortschritt ~60 s, Tiefencheck alle 30 min, ohne LLM"
bestand: "Watchdog mit Evidenzmodell vorhanden (Incidents im Portal); Kuma deckt nur Erreichbarkeit ab, nicht Auftragsfortschritt"
option: "30-min-Tiefencheck als systemd-Timer (jarvis_deepcheck.py): offene Tasks ohne Fortschrittsbeleg > Schwelle, Jobs 'gestartet ohne Run', Ledger-Anomalien → Incident + Kuma-Push-Monitor 'Tiefencheck lebt'"
risiken: ["Fehlalarme bei legitimen Wartephasen → Wartegründe aus Taskstatus respektieren"]
kosten: "keine; < 2 s CPU je Lauf"
abnahme: ["künstlich hängender Testauftrag erzeugt Befund", "legitime Wartephase erzeugt keinen", "ausgefallener Tiefencheck → Kuma-Alarm"]
umsetzung: "jarvis_deepcheck.py (cron 7,37 * * * *), nur lesend auf brain.db; Befund → Kuma-Push 'Tiefencheck (30 min)' down → Signal; bleibt der Lauf aus (35 min) → ebenfalls Alarm. Schreibt KEINE Incidents in die Engine (Core bleibt Eigentümer)."
status: VERIFIZIERT – 7/7 Unit-Tests (hängend, Wartephase < 24 h, Lease, Tick-Fehler, Speicher/Platte), Live-Lauf 'OK', Monitor 9/9 up und mit Signal verknüpft
```

```yaml
proposal_id: CORE-001
bereich: "PC-Worker (Windows, Sandbox)"
bestand: "AppContainer, Netz aus, nur java.build; Job j20261027-14c029 2/2 unabhängige Abnahme"
status: VERIFIZIERT
```

```yaml
proposal_id: CORE-003
bereich: "Einheitlicher Ereignisvertrag (Abschnitt 0.4) für Chat, Command Center, Living HQ, Sprache"
bestand: "store.js leitet Ereignisse aus Poll-Differenzen ab; Engine schreibt events je Job (jarvis.py events)"
entscheidung: "KEIN SSE: Waitress hat 4 Threads, jede offene SSE-Verbindung bindet einen dauerhaft → Portal könnte bei 3–4 Tabs hängen. Stattdessen adaptives Polling im bestehenden Store: 2 s solange etwas läuft, 5 s im Leerlauf, sofort bei Tab-Rückkehr."
umsetzung: "store.js pollDelay() + unifiedState() (IDLE/RUNNING/WAITING_APPROVAL/BLOCKED/RECOVERING/DONE_VERIFIED/FAILED/PARTIAL/CANCELLED nur aus Engine-/Task-Status)"
status: UMGESETZT – Unit-Tests 2/2; Statuswechsel spätestens nach 2 s + Abrufzeit sichtbar (nicht separat im Browser gemessen). Echtes SSE erst mit eigenem Event-Dienst (später, Owner-Entscheidung)
```

## Sprache (Produktziel „wie ChatGPT Voice“)

```yaml
proposal_id: VOICE-001
bereich: "Gesprächsmodus: einmal starten, frei sprechen"
quelle: "Silero VAD v5 via @ricky0123/vad-web 0.0.31 (ISC), onnxruntime-web 1.22.0 (MIT); UX-Muster Home-Assistant Voice Satellite (nur Muster)"
bestand: "Portal /#/voice: Knopf 'Gespräch starten' → Zuhören → Du sprichst → Denkt nach → Spricht → Zuhören …; Stumm; Unterbrechen (stoppt nur Ton); Gespräch beenden (lässt Aufträge unberührt)"
abnahme: ["3 Wechsel ohne Knopf/Wakeword, auch nach 14 s Pause", "Stumm → nichts erkannt", "Beenden → Aus"]
status: VERIFIZIERT synthetisch (Piper-Audio als Mikrofon) – echtes Mikrofon/Handy offen
```

```yaml
proposal_id: VOICE-002
bereich: "Wakeword 'Hey Jarvis' im Browser (openWakeWord v0.5.1, Modelle CC BY-NC-SA – privat)"
status: VERIFIZIERT synthetisch (Positiv 0,85–0,998, Negativ ≤ 0,002); echte Stimme offen
```

```yaml
proposal_id: VOICE-003
bereich: "JARVIS ins Wort fallen per Stimme"
bestand: "Option 'Unterbrechen per Stimme (Kopfhörer)'; über Lautsprecher: 'Hey Jarvis' unterbricht (verifiziert)"
status: UMGESETZT (Kopfhörer-Variante nicht real getestet)
```

```yaml
proposal_id: VOICE-004
bereich: "Antwort beginnt sofort: ersten Satz sprechen, während der Rest generiert wird"
bestand: "lokale Antworten 3,5–4 s nach Sprechbeginn; Modellantworten (haiku) 10–13 s still bis zum ersten Ton"
option: "voiceAsk streamt bereits NDJSON → Satzgrenzen erkennen, je Satz Piper anstoßen (Queue vorhanden: speechChunks/playLocal)"
abnahme: ["erster hörbarer Satz < 4 s nach Frageende bei Modellantworten (messen, nicht versprechen)", "Unterbrechen stoppt auch noch nicht gesprochene Sätze"]
kosten: "keine"
messung: "Satzweise Ausgabe ist eingebaut (Ton begann 1 s vor Ende der Antwort). Aber: Ziel < 4 s NICHT erreicht – Modellfrage dauerte 35 s bis zum ersten Ton, weil Claude im Lesemodus erst den Vault durchsucht und den Text erst danach schreibt. Engpass ist der Modellaufruf, nicht die Sprachausgabe."
schnellroute: "28.10. vom Owner freigegeben: Brückenmodus 'gespraech' (keine Werkzeuge, keine Settings/MCP, 1 Zug, Haiku, gleiche Tageslimits; Backup ma-claude-bridge.py.bak-vor-gespraech-20261028). Notizfragen ('in meinen Notizen', 'schau nach', 'Vault' …) gehen weiter über den Lesemodus."
messung_neu: "Brücke direkt: erstes Wort 3,3 s (vorher ~35 s), Init meldet 0 Werkzeuge, Dateilese-Versuch abgelehnt. Browser-E2E: erster Ton 5,3–5,9 s nach erkannter Frage (Modell + erster Piper-Satz), Folgefrage mit Kontext korrekt."
status: VERIFIZIERT synthetisch – Ziel < 4 s bis erstem Ton knapp verfehlt (5–6 s), ca. 6× schneller als vorher
```

```yaml
proposal_id: VOICE-005
bereich: "Whisper small statt base (bessere Erkennung seltener Wörter, z. B. 'Minecraft' → 'Minikraft')"
messung: "28.10., 8 Fachsätze (Piper-Stimme, 16 kHz): base 0,75 Worttreffer/1,07 s · base+Fachwort-Prompt 0,88/1,04 s · small 0,74/3,32 s · small+Prompt 0,80/3,69 s"
entscheidung: "small ABGELEHNT (nicht besser, 3,5× langsamer). base + Fachwort-Prompt live (ma_voice_service.py, Backup *.bak-vor-sttprompt-20261028, 4/4 Tests)"
status: VERIFIZIERT (mit synthetischer Stimme – echte Stimme kann anders ausfallen)
```

```yaml
proposal_id: VOICE-006
bereich: "Smart-Turn (pipecat, BSD-2): Denkpause vs. Satzende per Modell"
bestand: "heute fester VAD-Nachlauf 0,9 s"
status: VORSCHLAG (nach VOICE-004 messen, ob nötig)
```

```yaml
proposal_id: VOICE-007
bereich: "Aufträge per Sprache: anlegen, Fortschritt fragen, korrigieren (Task-ID + Revision), pausieren/abbrechen nur mit Bestätigung"
bestand: "Sprache ist heute absichtlich nur lesend"
option: "Intent → jarvis.py submit/status/cancel über bestehende Portal-API; Rückfrage 'Soll ich den Auftrag … anlegen?' + Bestätigung per Knopf/Ja; Barge-in löst nie cancel_task aus"
risiken: ["Fehlerkennung → falscher Auftrag: deshalb Bestätigungsschritt und Anzeige des Transkripts"]
abnahme: ["Entscheidende Gesamtprobe aus D3 (Auftrag geben, unterbrechen, Anforderung ändern, Fortschritt fragen)"]
umsetzung: "voicetasks.js: 'Neuer Auftrag: …' → JARVIS liest das Verstandene vor und fragt; nur 'Ja' legt an (client_id gegen Doppelanlage), 'Nein' oder anderes Thema verwirft, Rückfrage verfällt nach 30 s. 'Brich den Auftrag ab' → Rückfrage → nur 'Ja' bricht ab. 'Wie weit ist mein Auftrag?' liest den Engine-Zustand."
status: UMGESETZT – 5/5 Unit-Tests, Browser-E2E: Anlegen→Nein (nichts angelegt), Abbrechen ohne laufenden Auftrag, Fortschritt. Ein echtes 'Ja' wurde NICHT getestet (hätte einen echten Auftrag erzeugt). 'Anforderung ändern' fehlt: V16 hat keinen Änderungsbefehl → LÜCKE
```

```yaml
proposal_id: VOICE-008
bereich: "Stimme"
bestand: "Piper Thorsten emotional (Owner-Wahl), lokal auf dem PC"
status: VERIFIZIERT (Owner-Abnahme der Stimme)
```

## Portal / Design / Mobil

```yaml
proposal_id: UX-001
bereich: "Portal als installierbare App (PWA) statt APK"
bestand: "manifest.webmanifest + sw.js vorhanden (classic); neue Shell nutzt sie"
option: "Installationshinweis (beforeinstallprompt, iOS-Hinweis), Offline-Seite 'letzter Stand', Icons/Theme an HQ-Design"
abnahme: ["Installieren auf Android", "Start im Vollbild", "Mikrofon in der installierten App"]
umsetzung: "Knopf '⤓ App' oben (Android/Chrome/Edge: echtes Installationsfenster; iPhone: Hinweis Teilen → Zum Home-Bildschirm; installiert: kein Knopf). Manifest-Name 'MA-HOME JARVIS'/'JARVIS', Farben an HQ (Backup manifest.webmanifest.bak-vor-jarvisname-20261028)"
status: UMGESETZT – 2/2 Unit-Tests; Installation auf deinem Handy offen
```

```yaml
proposal_id: UX-002
bereich: "Designrichtungen"
bestand: "M1 Designsystem, M2 Funktions-Port, M3 Living HQ umgesetzt und live; M4 Command Center + Sprache"
status: UMGESETZT – Abnahme M4 durch Owner ausstehend
```

```yaml
proposal_id: HQ-001
bereich: "Animierte Agentenwelt mit Figuren (Pixel Agents MIT / Star Office UI Code MIT, Assets NICHT frei)"
bestand: "Living HQ (Canvas, echte Daten, keine erfundene Aktivität)"
option: "Figuren/Animationen nach Pixel-Agents-Muster mit eigenen oder Kenney-CC0-Assets, Zustände aus CORE-003"
abhängigkeit: "CORE-003"
status: VORSCHLAG (nach CORE-003)
```

## P3 – Später / Forschung

| ID | Bereich | Status | Empfehlung |
|---|---|---|---|
| ROUTER-001 | Restquoten der Provider | LÜCKE: keine Datenquelle, `council_decisions` leer | erst Messquelle, dann Anzeige |
| SKILL-001 | Capability-Registry und automatische Skill-Zuweisung (Anhang 1 §16) | VORSCHLAG | erst nach Basis-GO |
| KIMI-001 | geplante Kimi-Supervision (z. B. wöchentlicher Review-Cron mit Budget) | VORSCHLAG | nach OPS-003 |
| HW-001 | Echo Dot 3 als Lautsprecher/Mikrofon | NO-GO-Empfehlung (Firmware-Eingriff, Brick-Risiko) | Handy/PC-Headset nutzen |
| DRUCK-001 | Drucker 192.168.0.198:631 | NICHT_PRÜFBAR (Gerät nicht erreichbar) | Owner: Gerät einschalten |
| WIN-001 | Windows-Aktivierung | Owner-Aufgabe, keine Umgehung | – |

## Offene Abnahmefälle (nur mit echter Hardware/Owner)
1. Gesprächsmodus mit echtem Mikrofon am PC (Chrome/Edge) und am Android-Handy.
2. „Hey Jarvis“ mit echter Stimme: ggf. Empfindlichkeit anpassen (Regler, Diagnose → „Bericht kopieren“).
3. Signal-Dialog vom Handy: gemeldet als in Ordnung.

Jarvis: Phase B – empfohlenes Paket plus Schnellroute umgesetzt; Gesprächsantworten 5–6 s statt 35 s bis zum ersten Ton – offen: Tests mit echter Stimme und am Handy durch den Owner.
