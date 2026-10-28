# APPROVAL_MATRIX – MA-HOME JARVIS (Stand 27.10.2026, 22:40)

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
status: VORSCHLAG (empfohlen, sofort)
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
abnahme: ["künstlich hängender Testauftrag erzeugt Incident", "legitime Wartephase erzeugt keinen", "ausgefallener Tiefencheck → Kuma-Alarm"]
status: VORSCHLAG (empfohlen)
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
option: "/api/jarvis/events (SSE mit Resync über monotone Revision) aus bestehender Engine-Eventtabelle; Living HQ/CC abonnieren statt pollen; Zustände IDLE/RUNNING/WAITING_APPROVAL/BLOCKED/RECOVERING/DONE_VERIFIED nur aus Engine, nie aus LLM-Text"
risiken: ["SSE durch Caddy/Waitress: Thread-Bindung je Verbindung (Waitress 4 Threads) → Long-Polling-Fallback"]
kosten: "keine"
abnahme: ["Statuswechsel erscheint < 3 s in HQ und CC", "Verbindungsabbruch → 'letzter bekannter Stand', danach Resync ohne Duplikat"]
status: VORSCHLAG (empfohlen)
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
status: VORSCHLAG (empfohlen – größter Hebel für 'natürlich')
```

```yaml
proposal_id: VOICE-005
bereich: "Whisper small statt base (bessere Erkennung seltener Wörter, z. B. 'Minecraft' → 'Minikraft')"
ressourcen: "PC (Ryzen 5 3600): grob 2–3× Rechenzeit je Satz – erst messen"
status: VORSCHLAG
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
status: VORSCHLAG (empfohlen)
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
status: VORSCHLAG (empfohlen; Gerätetest durch Owner nötig)
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

Jarvis: Phase B – Gesprächsmodus, Wakeword und Dienste-Wächter live und synthetisch verifiziert – Entscheidung: empfohlenes Paket SEC-001, VOICE-004, VOICE-007, OPS-003, CORE-003, UX-001 freigeben?
