# MA-HOME Portal-Redesign — Bestandsaufnahme & Konzept
## V3 Phasen 7–10 (Webportal, Living HQ, Sprache, Command Center)
**Stand:** 2026-10-27, erstellt von kimi-supervisor. Quellen: SPEC-MASTER-V3-20261026.md §9–§13, Phasen 7–10, Erfolgskriterien §18; Live-Inventar auf ma-server.

---

## 1. Bestand (verifiziert, Live)

**Architektur:** FastAPI (`/opt/ma-home/portal.py`, 569 Z.) serviert Vanilla-JS-SPA (`web/app.js` 1.858 Z., `style.css` 350 Z., `sw.js` PWA) + Assets unter `/assets/`. Auth: Authelia vor Caddy (extern 302→/auth/), App-Auth `X-MA-Key` (proxy_key aus /etc/ma-home/portal.json) + Remote-User/Origin/X-MA-Request. Jarvis-Bridge (`jarvis_portal_bridge.py`) hängt `/api/jarvis/*` an denselben Port (:18765). Server: Celeron N2840, 3,2 GB RAM → **Server rendert nichts, alles clientseitig.**

**Vorhandene Funktionen (alle zu erhalten):**
- JARVIS-Chat (c*-Elemente, inkl. `cmic`-Button → Mikrofon-Stub existiert bereits), Sessions, Anhänge
- Dateiverwaltung (`/api/files`, `/api/file`, Audio-Playback `/api/audio`)
- Items: Notizen, Aufgaben, Geld, Training (`/api/items/*`)
- Jobs + Claude-Ops (`/api/jobs`, `/api/claude/op`), Deploy-Switch (`/api/deploy/*`)
- Terminal (`/api/term`), Status (`/api/status`), Export (`/api/export`)
- JARVIS-Bridge: Agents, Tasks, Watchdog, Memory, Jobs submit/cancel/result — **E2E-belegt (A6)**
- Karten: „Agenten & Watchdog" mit Echtdaten + Stale-Logik (V2026-10-26-2)

**Bekannte Schwächen:** kein Designsystem/Tokens, 350-Z.-CSS monolithisch, keine Command Palette/Suche/Favoriten, keine Räume/Agentenwelt, Sprachfunktion nur als Stub, Mobile unoptimiert, Views per id-Convention unstrukturiert.

## 2. Anforderungen (aus SPEC, wörtlich verdichtet)

- **§9 Redesign:** eigene Designsprache, futuristische dunkle Kommandozentrale, Holografik, Cyan/Blau + dezente Crimson-Akzente, hochwertige Animationen, eigenes Designsystem mit wiederverwendbaren Komponenten, **alle oben genannten Funktionen erhalten**, Embedded-First (keine neuen Tabs), Sicherheitsrichtlinien nicht umgehen, Architektur prüfen vor Technologiewechsel, neue Navigation (JARVIS-Zugang, Command Palette, Suche, Favoriten, Schnellaktionen, Arbeitsbereiche), **Staging zuerst, Backup+Rollback vor Umschaltung**.
- **§10 Living HQ:** interaktive Welt, Agentenfiguren arbeiten/sitzen/laufen (Räume: Zentrale, Council-Konferenzraum, Entwicklerbüro, Forschung, QA-Lab, Infrastruktur, Serverraum, Kreativstudio), echte protokollierte Ereignisse, **keine vorgetäuschte KI-Aktivität**, **keine zusätzlichen LLM-Tokens**, Clientseitiges Rendering, adaptive Grafikqualität. Kandidaten: Pixel Agents, Hermes Virtual Office, Offivo, React Flow, Three.js (Lizenzen/Integration prüfen).
- **§11 Inspiration:** Crimson Zone (IZE-Kommandozentrale, Aurelion, Holografik, rote Resonanz, Anime/Webtoon), Eternal Bonds (Charakterdesign, Atmosphäre, dynamische Verbindungen), Andrew SMP 3 (lebendige Miniaturwelt, Werkstätten, Ressourcenflüsse). **Eigene Designsprache, keine Kopie.**
- **§12 Sprache:** deutsche SR, natürliche TTS, Kontext, unterbrechbar, optionales Wakeword, Transkripte, Sprachaufträge/-abfragen, animierter Kern, Audio-Visualisierung, Chat+Sprache kombiniert. Lokale Technologien bevorzugen (Whisper/Piper), Mobile-Beschränkungen beachten.
- **§13 Command Center:** Agenten, Verbindungen, Council, Aufgaben, Delegationen, Modelle, Provider, Skills, Tools, Token, Kosten, Server/GPU, Worker, Logs, Fehler, Automatisierungen, Historie. **Dieselben echten Daten wie die animierte Welt — keine parallelen Statussysteme, keine simulierten Live-Daten.**

## 3. Leitentscheidungen (Vorschlag)

| Entscheidung | Vorschlag | Begründung |
|---|---|---|
| Framework | **Kein Wechsel: Vanilla-JS-Modul + CSS-Token-System** | SPEC verlangt Architekturprüfung vor Tausch; 1.858-Z.-app.js ist tragbar; Server hat 3,2 GB RAM — Build-Toolchain/Node auf Server meiden; PWA-SW eh vorhanden |
| Designsystem | `tokens.css` (Farben/Typo/Abstände/Glow) + `components.css` (Karten, Buttons, Holografik-Panels), Incremental neben altem CSS | Bestand vor Neubau, risikoarm migrierbar |
| Living HQ | **Canvas-2D-Engine (Eigenbau, ~Pixel-Agents-Stil)**, Räume als Tilemap-Daten, Figuren als Sprite-Prozeduren | SMP3-Ästhetik = 2D-Miniaturwelt passt besser als 3D; Three.js = Overkill für Celeron-Clients; keine Lizenztreue nötig; volle Kontrolle über „echte Ereignisse"-Mapping |
| Ereignis-Quelle | **chat_bus-Postgres + JARVIS-Bridge-APIs** (tasks, heartbeats, council-Sessions, ledger) via bestehendem Polling; neuer schlanker `/api/jarvis/events?since=`-Endpunkt (Cursor-basiert) | Kein Parallel-Statussystem (§13), keine LLM-Tokens (§10), Server-lastarm |
| Sprache | **Phase A: Web Speech API im Browser** (de-DE SR + SpeechSynthesis, unterbrechbar, Transkript-Anzeige, cmic-Stub ersetzen). **Phase B (optional): lokaler Whisper/Piper auf Windows-PC** (RTX 2060) über Worker-Anbindung | SPEC: lokale Tech, Mobile-Limiten beachten; Browser-API = null Serverlast, sofort nutzbar; lokale SR/TTS später nachrüstbar ohne UI-Bruch |
| Command Center | Neuer View im selben SPA, **zweite Darstellung derselben Daten** wie Living HQ (shared Store `state.js`, ein Polling-Core) | §13: gleiche echten Daten, keine parallelen Systeme |
| Staging | Neuer Pfad `/staging/` im selben portal.py (StaticDir), eigene SW-Scope-Unterbindung (sw.js im Staging deaktiviert), Test via staging.ma-server.duckdns.org (Authelia-Regel) | Kein zweiter Service, kein RAM-Mehrbedarf; produktives Portal unberührt |
| Rollout | 4 Meilensteine (siehe §6), jeder mit Backup + einem Commit-Stand auf main (ma-git-sync) + Owner-Gate vor produktiver Umschaltung | SPEC: Staging zuerst, Backup/Rollback |

## 4. Designsprache „MA-HOME HQ" (Entwurf)

- **Basis:** Tiefes Marine/Schwarzblau (`#050a14`), Cyan-Glow (`#22d3ee`), Blau-Verläufe; **Crimson nur als Akzent** (Warnungen, JARVIS-Kern, Resonanz-Energie: `#e11d48`), nie als Fläche.
- **Holografik:** wiederkehrende `holo-panel`-Komponente (Glas, Scanline, feiner Rahmen-Glow, Clip-Pfade), 1px-Grid-Hintergründe, dezente Partikel.
- **Typo:** System-Stack mit `font-feature-settings` für Zahlen (Telemetrie), monospace für Logs/Token.
- **Motion:** 150–300 ms, `prefers-reduced-motion` respektieren (SPEC: hohe Performance); adaptive HQ-Grafik = FPS-Cap + Partikel-Dichte nach `deviceMemory`/Messung.
- **SMP3-Motiv:** Ressourcenflüsse im Living HQ = **echte** Token/Kosten-Ströme als Linienanimation.

## 5. Living HQ — Datenmodell (kein Vortäuschen)

Figur = Agent aus `/api/jarvis/agents` + Heartbeat/Tasks. Zustandsmapping ausschließlich aus echten Feldern:
- `active_task` → Figur sitzt am Rechner im Fachraum, Fortschrittsbalken = echter Task-Status
- Council-Session (chat_bus: council-Topic aktiv) → beteiligte Figuren laufen zum Konferenzraum
- Test-Run (jobs mit Typ test) → QA-Lab-Animation
- Incident/Failure (watchdog) → Warnicon + roter Puls am betroffenen Raum
- Idle > Stale-Schwelle → Figur „schläft"/steht auf Kaffeepause (dekorativ, kenntlich als dekorativ)
- Klick auf Figur → Drawer mit Auftrag/Modell/Skills/Status/Fortschritt/Fehlern/Token/Kommunikationsverlauf (§10)

## 6. Meilensteine

- **M1 Designsystem + Gerüst:** tokens.css/components.css, neuer App-Shell mit Navigation, Command Palette (clientseitig über vorhandene Views), Staging-Pfad. *(Owner-Gate: Designrichtung)*
- **M2 Funktions-Port:** alle Bestands-Views in neues Gerüst, keine Funktionsverluste, Mobile. *(Owner-Gate: Staging-Abnahme)*
- **M3 Living HQ:** Canvas-Engine + Räume + Event-Endpunkt + Figuren. *(Owner-Gate: „kein Vortäuschen"-Audit)*
- **M4 Sprache + Command Center:** Web-Speech-A + CC-View + Shared Store. *(Owner-Gate: Produktiv-Umschaltung)*

**Risiken/Aufwand:** M1–M2 = Frontend-Fleiß, geringes Risiko. M3 = der kreative Kern, Aufwand hauptsächlich Engine + Event-Mapping. Sprache Phase A überraschend billig (Browser-API), Phase B (lokal Whisper/Piper) eigener Workpackage nach Windows-Worker-Freigabe. Gesamt realistisch in Etappen über mehrere Sessions; jede Etappe produktiv nutzbar.

## 7. Offene Owner-Entscheidungen

1. **Designrichtung M1:** wie oben (Cyan/Holografik/Crimson-Akzent, SMP3-Miniaturwelt) — Freigabe oder Korrekturwunsch?
2. **Eigene Originalmaterialien** (Crimson Zone / Eternal Bonds / SMP3 Assets): wo liegen sie, sollen sie einfließen? (SPEC §11: „soweit zugänglich")
3. **Wakeword** („Jarvis"-Aktivierung): Phase A weglassen (Button-gesteuert) oder früh einplanen?
4. Soll M1 direkt starten?

**Owner-Entscheide 27.10. (~06:45):** Wakeword = **einplanen** (nicht weglassen); Inspirationssuche durch alle zugänglichen Materialien = **ja**; M1 = **starten** („mach einfach alles").

---

## 8. Inspirations-Distillation (Originalmaterial, Server-Vault)

Quellen verifiziert unter `/srv/ma-home/library/vault-notizen|dateien/20 Projekte/`:
- **Crimson Zone**: Vollständiges Worldbuilding (Resonanz-Powersystem, IZE-Klassifikation, Sicherheitsstufen, Uniformen IZE/Aegis), Webtoon-Kapitel (DE/EN), Weltkarte (`ChatGsd.png`, 4 MB), Klimazonen-Karten, `Cz Sammlung/Cover.png` + `Philippe_Braun_KonzeptArt.png` (Charakter-Konzeptart).
- **Eternal Bonds**: Minecraft-Mod (Fabric 1.21.4) + Kapitel-/Charakterdesign-Chat-Notizen (Ordner Projekt Schmejd).
- **Minecraft SMP24**: Welten/Server-Archive + Story-Timeline — Miniaturwelt-Prinzip.

Bildanalyse (lokal gesichert unter `kimi-supervisor/cache/scratch/inspiration/`):

1. **CZ-Cover**: Duochrome-Spannung kühles Schiefer-Blau (`#4A5560`-Richtung) vs. Glut-Crimson (`#FF2E4D`), Türkis-Auge (`#35C4D8`) als Kontrastpol, Underlighting, Vignette, Block-Uppercase-Typo mit Glitch, Partikel/Embers. → UI: Crimson nur für Kritisches/Aktives, Türkis = System/OK, Glow statt Flächen, Underglow als Karten-Signatur.
2. **CZ-Weltkarte**: Pergament-Erdtöne (Greige `#B8A892`, Sand `#D9BFA8`) + ein Signal-Rot für Gefahrenzone + Cyan für interaktive Marker; Hierarchie Titel>Region>Ort; Quadrat=Station, Punkt=Agent, Linie=Route; dioramaartiger Rahmen. → Living HQ: semantische Farbcodierung, Zonen statt Einzelobjekte, 3-Ebenen-Beschriftung, Raster.
3. Ablehnung als Referenz: `chapter1_page1.png` ist nur eine leere Panel-Vorlage — keine Stilaussage (Webtoon-PDFs enthalten das fertige Artwork, bei Bedarf einzeln extrahierbar).

## 9. M1 — Stand (27.10. ~07:20 MESZ)

- **Designsystem** live unter **`https://ma-server.duckdns.org/staging/`** (gleiche Authelia/Key-Auth wie Portal).
- Dateien: `web/staging/{index.html, css/tokens.css, css/components.css, js/app.js}` — Palette/Abstände/Typo/Motion/Glow-Tokens, Holo-Panel, KPI, Status-Dots, Buttons, Chips, Tabelle, Sidebar-Nav, Command Palette (Ctrl+K, Maus + Tastatur), Swatch-Showcase, reduced-motion + Mobile-Breakpoints. Kein Framework, keine Webfonts, keine Cookies.
- **portal.py**: Route `/staging` + `/staging/<path:name>` ergänzt (Backup `portal.py.bak-vor-staging-20261027`); ma-home-web einmal neugestartet.
- **Verifikation (alles 200/404 wie erwartet)**: healthz 200 · / (prod) 200 · /staging/ + css + js 200 · Pfad-Traversal 404 (safe_join) · API watchdog 200 · Auth-Uniformität: /staging ohne Key = 401 (identisch zu /).
- **Nächster Schritt M2**: Bestands-Views (Chat, Dateien, Items, Jobs, Terminal, Status, Deploy) in die Schale portieren, echte Daten via bestehender APIs, danach Owner-Gate Staging-Abnahme.

## 10. M2 — Stand (27.10. ~08:30 MESZ): Funktions-Port, Staging-Abnahme bereit

**Architektur:** ES-Module ohne Build-Schritt (`js/api.js` Basis+mdLite · `viewer.js` Datei-Vorschau · `chat.js` JARVIS-Chat · `views.js` Dashboard/Items/Dateien/System/Terminal/Verbindungen · `app.js` Shell/Router/Palette/Favoriten). Bestands-`style.css` als `css/legacy.css` darunter, Tokens/Komponenten überschreiben. Logik und API-Verträge unverändert aus Bestands-`app.js` portiert (Streaming, Auto-Reconnect, Rechte-Eskalation, Council-Auto, Slash-Befehle, Anhänge, Verläufe, geplante Aufgaben, Übergabe-Mechanik).

**Nativ portiert (10):** Kommandozentrale (neu: echte KPIs), JARVIS-Chat, Aufgaben, Notizen, Geld, Training, Dateien (+Suche, Viewer), Terminal, System, Verbindungen. **Als klassische Einbettung (5, Zwischenstand, alt-Navigation per CSS ausgeblendet):** Neu, Vault, Wissen (Graph), Musik, Einstellungen. **Gesperrt bis M3/M4:** Living HQ, Command Center. Neu: Favoriten (Ctrl+Klick in Palette), Palette mit Chat-Aktionen.

**Verifikation (echter Chromium, ueber SSH-Tunnel + Auth-Proxy; 0 JS-Fehler in allen Durchlaeufen):**
- 10 native Views rendern mit echten Daten; Dashboard-KPIs gegen API-Rohdaten gegengeprueft (Agents 2, davon 1 aktuell / 1 veraltet, 4 Incidents; Watchdog aktiv).
- POST-Pfade (Verbindungen: 40 Eintraege/11 mit Handlungsbedarf, Verlaeufe, geplante Aufgaben inkl. Limits) laufen.
- Chat **E2E mit echter Anfrage** (haiku, nur lesen, „Antworte nur mit dem Wort OK“): Antwort „OK“, Usage-Zeile (26k rein/4 raus, ca. 0,005 USD), Attribution/Nachweis-ID, Plan-Limits (Sitzung 5 h 7 %, Woche 1 %). Slash-Menue (20 Eintraege), /hilfe, /modell funktionieren.
- 5 Legacy-Einbettungen zeigen den richtigen Inhalt (iframe-Hash), Alt-Navigation ausgeblendet.

**Befunde (nicht durch M2 verursacht):**
1. **`/api/status` liefert seit mindestens 26.10. 12:27 HTTP 500 (PermissionError, 19 Treffer vor dem Staging-Restart).** Ursache: ma-home-web laeuft als `User=andrew`, der Host-Agent-Socket `/run/ma-home/agent.sock` gehoert `ma-web` (Modus 0600). Betroffen im Produktivportal: Systemstatus, Dienst-Neustart (`/api/service`), Dokument-Vorschau/Druck (`/api/jobs*`). Nicht eigenmaechtig geaendert (Sicherheitsgrenze Host-Agent). **Owner-Entscheidung:** (a) Socket-Gruppenrecht fuer `andrew` setzen, (b) Portal-Dienst wieder als `ma-web`, oder (c) so lassen. Die neue UI zeigt den Ausfall ehrlich („Statusdienst nicht erreichbar“).
2. Nicht getestet: Datei-Upload-Anhaenge, Spracheingabe (Mikrofon-Berechtigung), Auto-Rechte-Eskalation, Uebergabe-Neustart — 1:1-Port, aber ohne Live-Probe (wuerden Dateien/Rechte/Quota beruehren). Vor Produktivumschaltung einmal manuell im Staging pruefen.
3. Der Test-Chat „Antworte nur mit dem Wort OK.“ erscheint in der Verlaufsliste (harmlos).

**Naechster Schritt:** Owner-Gate Staging-Abnahme (`/staging/` ansehen), danach M3 Living HQ.

### 10a. Befund 1 BEHOBEN (27.10. ~07:00 MESZ, Owner: „mach wie du denkst“)
Die Empfehlung „Socket-Gruppenrecht“ war allein nicht ausreichend: `agent.py` prueft zusaetzlich per `SO_PEERCRED` und liess nur UID 0 und `web_uid` (ma-web, 999) zu. Umgesetzt (eng, fail-closed, rueckrollbar):
- `agent.py`: Peer-Pruefung akzeptiert `(0, web_uid, *extra_uids)`; Socket wird nur dann `0660` mit Gruppe `extra_gid`, wenn `extra_uids` konfiguriert ist — ohne Config-Eintrag exakt das alte Verhalten (0600).
- `/etc/ma-home/host.json`: `extra_uids=[1000]`, `extra_gid=1000` (Modus 0600 root erhalten).
- Backups: `agent.py.bak-vor-extrauid-20261027`, `host.json.bak-vor-extrauid-20261027`. Rollback: beide zurueckkopieren + `sudo systemctl restart ma-home-agent`.
- Begruendung: stellt nur die Faehigkeit des Portals wieder her, die es vor dem Wechsel auf `User=andrew` hatte; Agent-Befugnisse unveraendert; andrew hat ohnehin sudo.
- **Verifikation:** Agent aktiv (0 Restarts nach Start), Socket `ma-web:andrew 0660`; Probe: andrew OK, ma-web OK, **nobody abgewiesen**; `/api/status` 200 mit Containern/Backup/Uptime; `/api/jobs/<unbekannt>` jetzt 400 statt 500; 0 PermissionError im Portal-Journal seit Neustart. Restart-Fenster ~1 s, keine aktiven Jobs.

## 11. M3 — Living HQ (27.10. ~09:00 MESZ): im Staging live, Owner-Gate „Kein-Vortaeuschen-Audit“

**Umfang:** `js/store.js` (gemeinsamer Daten-Store, Poll 5 s, Events nur aus Zustandsdiffs; wird in M4 vom Command Center mitgenutzt), `js/roster.js` (18 Profile + Watchdog auf 8 Raeume), `js/hq.js` (Canvas-2D-Engine), Styles + Mobil-Kopfzeile, Nav-Eintrag „Living HQ“ freigeschaltet. Kein Backend-Umbau (Produktivsystem unberuehrt), keine LLM-Token.

**Datenmodell (nur echte Daten):** Figur-Zustand aus `/api/jarvis/tasks` (assigned_to + Status: ACTIVE→arbeitet / PLANNING|INBOX|pending→Planung / sonst ohne Auftrag), Alarm aus Incidents (Besitzer ueber Task-Zuordnung oder Agent-Subject) und veralteten Heartbeats (>10 Min), Server-Racks/Ressourcenfluss nur bei echtem `engine.active`. Bewegung ausschliesslich bei Diff-Ereignissen (neuer Auftrag/Zuweisung/Statuswechsel → Gang zur Zentrale, Pulsring bei Incident/Job). Drawer je Figur: Rolle, Raum, Heartbeat, Auftraege, Incidents, letzte Ereignisse. **Keine Council-Konferenz-Choreografie:** fuer „wer spricht mit wem“ existiert keine Datenquelle (Council laeuft ueber message_agent, Chat-Bus praktisch leer) — wird nicht erfunden.

**Verifikation (echter Chromium, 0 JS-Fehler):**
- Zustandsabgleich gegen API-Rohdaten: 3 ACTIVE-Tasks = 3 Arbeitende (core, worker, brain); 4 Incidents → 3 Alarm-Besitzer; 18+1 Figuren.
- Ereignislogik mit injizierten Antworten (nur im Browser): Statuswechsel, neuer Task, Incident behoben/wieder offen → korrekte Feed-Eintraege, Chips/Alarmrahmen ziehen nach.
- **Animationspfad:** QA-Figur lief nach neuem Auftrag in die Zentrale, Schreibtisch-Monitor blieb „arbeitet“-cyan; 62 FPS. **Reduced-Motion-Pfad** (Browser meldete reduce): statisch, Updates korrekt. Engine-aktiv-Darstellung (LED-Blinken, Flusslinie, „n Engine-Job(s) aktiv“) mit injiziertem Job geprueft.
- Drawer mit echten Daten (brain: P5 ACTIVE, STALLED_TASK seit 16 Std). Mobil (390 px): kompakte scrollbare Kopfzeile statt Vollbild-Sidebar (Fix eines M1-Mangels), Welt voll sichtbar, kein Overflow.

**Grenzen/Ehrlichkeit:** (1) Ereignisse nur seit Seitenaufruf (sessionStorage, kein serverseitiges Eventlog) — ein Cursor-Endpunkt `/api/jarvis/events` waere der naechste Ausbau. (2) 16 von 18 Profilen haben keine Heartbeat-Telemetrie; ihr Zustand beruht allein auf Tasks. (3) Dekoration (Atmen, LED-Ruhelicht) ist als solche im UI gekennzeichnet. (4) Engine-aktiv und Walk-Pfade wurden mit injizierten, nicht mit echten Live-Ereignissen verifiziert (aktuell laeuft kein Job). **Naechster Schritt:** Owner-Abnahme im Staging → M4 (Command Center auf demselben Store + Sprache inkl. Wakeword).

## 12. M4 — Command Center + Sprache (27.10. ~09:50 MESZ): im Staging live

**Command Center (§13)** `js/cc.js` — nutzt denselben Store wie Living HQ (`store.js`), plus 30-s-Zusatzquellen: Agenten/Council (19 Zeilen), Aufgaben, Incidents, Engine-Jobs (`/api/jarvis/jobs`: Calls, Token, Ergebnis), Token & Kosten (usage-Op: Tageslimits, Plan-Limits 5 h/Woche, Tagesverlauf), Server (CPU/RAM/Disk/Container/Backup), Verbindungen (Konnektor-Status), Automatisierungen (sched_list), Skills & Werkzeuge (Slash-Katalog), Historie (Ereignisse + Chat-Verläufe). **Ausdruecklich „nicht angebunden“ (keine API, nichts simuliert):** Modelle/Router-Quoten (Ledger liegt auf dem Server, kein Endpunkt), GPU/Worker-Telemetrie (Windows-PC), Logs.

**Sprache (§12)** `js/voice.js` + `js/voiceui.js`: deutsche Spracherkennung + Sprachausgabe (Web Speech API), Wakeword „Jarvis“ (Varianten dscharvis/jervis …), Zwei-Schritt-Modus („Jarvis“ → Fenster 8 s → Befehl), unterbrechbar („Jarvis stopp“, Echo-Schutz: nur kurze Äußerungen ≤ 4 Wörter unterbrechen), Transkript, animierter Kern mit **echtem Mikrofonpegel** (AnalyserNode), Stimmauswahl, Chat+Sprache kombiniert (gleiche Verlaufsdaten). Kopfzeilen-Knopf in jedem Bereich (Klick = diktieren, Umschalt+Klick = Wakeword).
- **Lokale Intents ohne Token:** Lage, Alarme/Incidents, Aufgaben, „wer arbeitet“, „was macht <Agent>“, Uhrzeit, Navigation („öffne Living HQ“), Stopp. Vor jeder Antwort wird der Store frisch geladen. Freitext → `voiceAsk` = JARVIS **haiku, Modus „nur lesen“, Ordner Notizen** — per Sprache ist **nichts schreibbar/loeschbar**.
- **Datenschutz:** Chrome/Edge senden Audio zur Erkennung an den Browser-Anbieter (nicht lokal). Wakeword nur nach ausdruecklicher Bestaetigung (einmalig), Wake-Modus verwirft Äußerungen ohne Wakeword ohne Anzeige/Speicherung, Auto-Wiederaufnahme nur bei bereits erteilter Mikrofon-Berechtigung. Lokale Whisper/Piper-Variante = Phase B (Windows-Worker, RTX 2060).

**Verifikation (echter Chromium, 0 JS-Fehler):** CC: alle 12 Panels mit Echtdaten, Zahlen gegen API-Rohdaten (19 Agenten, 11/13 offen, 4 Incidents, Plan-Limits, 6 Container). Sprache mit **injizierter SpeechRecognition-Attrappe** (echte Erkennung/Mikrofon in der Automation nicht pruefbar): Fragmente ohne Wakeword verworfen; „Jarvis wie ist die Lage“ → korrekte Zahlen (3 arbeiten/6 Planung/9 ohne Auftrag); Alarme, wer arbeitet, brain-Status, Aufgaben, Uhrzeit, Navigation → Command Center; Zwei-Schritt-Fenster; Neustart der Erkennung nach onend; Barge-in („Jarvis stopp“ unterbricht, langer Satz mit „Jarvis“ nicht, neuer Befehl waehrend Ausgabe); **echter JARVIS-Fallback** (haiku/nur lesen, 8 s, „Paris“). Mobil 390 px und Desktop: kein Overflow in 8 Ansichten.

**Beim Test gefundene und behobene Fehler:** (1) Sprachantwort auf leerem Store („18 ohne Auftrag, Watchdog nicht aktuell“) → `refresh()` vor jeder Antwort. (2) Wake-Start haette auf den Mikrofon-Dialog gewartet → Pegelanzeige entkoppelt. (3) **Legacy-CSS-Kollision: `.c1`–`.c4` sind im alten Stylesheet Gradient-Hintergruende** → farbige Balken/roter Schimmer in Grid-Layouts (auch in M2-Dashboard); Spaltenklassen jetzt `cols2/3/4` mit `minmax(0,1fr)` (Overflow behoben). (4) Doppelt escapte „&amp;“ in Platzhaltern.

**Nicht verifizierbar hier:** echte Spracherkennung/-ausgabe mit Mikrofon und Stimmen (Headless ohne Audio) — bitte einmal real ausprobieren (Chrome/Edge, Mikrofon erlauben).

### 12a. Plan Produktiv-Umschaltung (noch NICHT ausgefuehrt, Owner-Gate)
Das Staging ist bereits nur fuer authentifizierte Nutzer erreichbar. Umschalten heisst: neue Shell auf `/`, klassisches Portal unter `/classic/`. Zu beachten: (a) `<base href="/staging/">` bzw. eigene Asset-Route fuer die neue Shell; (b) iframes der klassischen Ansichten zeigen auf `/classic/#/…` statt `/#/…` (sonst Rekursion); (c) **Service-Worker/PWA:** bestehende Clients haben den alten SW (Cache) — VERSION in `sw.js` UND `app.js` gemeinsam anheben (Skill-Regel), sonst Update-Schleife oder haengende Alt-Shell; (d) vorher Backup `web/` + `portal.py`, Rollback-Skript (ein Befehl); (e) Neustart `ma-home-web` einmalig (Owner-Freigabe). Alternative ohne Risiko: Staging dauerhaft als „HQ“-Zugang belassen und `/` unveraendert lassen.

## 13. PRODUKTIV-UMSCHALTUNG DURCHGEFUEHRT (27.10. ~10:15 MESZ, Owner: „Jetzt umschalten“)

**Ergebnis:** `/` = neue Shell (HQ), `/classic/` = klassisches Portal (unveraendert, eigenstaendig lauffaehig), `/staging/` = dieselben Dateien wie `/`. Beide hinter derselben Authelia-/Key-Authentifizierung (ohne Auth 401).
- **portal.py:** `index()` liefert `web/staging/index.html` (mit `<base href="/staging/">`), neue Route `classic_index()` fuer `/classic` + `/classic/`. Sonst unveraendert.
- **Neue Shell:** Hash-Routing fuer alte Lesezeichen (`#/claude→chat`, `#/home→dashboard`, `#/jarvis→cc`, `#/system→status`, `#/files?p=…`), Hash wird bei Navigation mitgefuehrt (Reload bleibt in der Ansicht), iframes der 5 klassischen Ansichten zeigen auf `/classic/#/…` (sonst Rekursion), PWA-Manifest/Icons + SW-Registrierung (bestehender network-first-SW unveraendert → **keine Versionsanhebung noetig**, keine Update-Schleife; bestehende Clients laden die neue Shell beim naechsten Oeffnen).
- **Backups:** `/opt/ma-home/portal.py.bak-vor-cutover-20261027`, `/opt/ma-home/web.bak-vor-cutover-20261027/`. **ROLLBACK (ein Befehl, ~3 s): `sudo bash /opt/ma-home/rollback-cutover.sh`** — stellt portal.py wieder her und startet ma-home-web neu; `web/` blieb unveraendert, `/staging/` bleibt erreichbar. Rollback-Skript syntaxgeprueft, noch nicht scharf ausgefuehrt.
- **Dienst-Neustart:** ma-home-web einmal (Owner-Freigabe); danach healthz 200, Journal ohne Fehler.

**Verifikation auf dem Produktivpfad `/` (echter Chromium):** Startseite, 13 native Ansichten ohne Overflow/Leerlauf, Deep-Links (#/claude, #/jarvis, #/hq, #/files) korrekt; 5 Einbettungen laden ueber `/classic/` mit richtigem Inhalt und ohne verschachtelte Navigation; `/classic/` eigenstaendig voll funktionsfaehig (16 Nav-Eintraege, kein Reload-Loop nach 6 s); HQ ohne Resize-Warnung. Server-seitig: `/`, `/classic/`, `/classic`, Assets, sw.js, Manifest, `/staging/*`, `/api/me`, `/api/jarvis/agents` alle 200 mit Auth.
**Nebenkorrekturen:** ResizeObserver-Warnung (HQ), Beschriftungen „Meine Aufgaben offen“ / „Agenten mit Heartbeat“ (vorher missverstaendlich), Versionszeile ohne Umbruch.

**Bewusst nicht migriert / bekannte Aenderungen:** (1) PWA-`share_target` (Teilen-Menue → `/?title=…`) wird von der neuen Shell nicht verarbeitet (klassisch: `/classic/?…`); Nutzung bisher nicht belegt. (2) Native Portierung von Neu, Vault, Wissen (Graph), Musik, Einstellungen steht aus (laufen als Embed). (3) Wake-Word/Spracherkennung real nur mit Mikrofon pruefbar. (4) Android-App-Bruecke (`window.MaApp`) laeuft im klassischen Portal weiter; in der neuen Shell nur ueber `/classic/`.

## 14. M5 — Native Portierung der 5 Embed-Bereiche + Abnahme (27.10. ~10:40 MESZ)
**Neu nativ (kein iframe mehr):** Neu, Vault (Obsidian-Ersatz), Wissen (Graph), Musik, Einstellungen, dazu **JARVIS-Aufträge** (V16-Engine, im Altportal Route `#/jarvis`). Vorgehen: `build_port.py` erzeugt `js/port.js` (746 Z.) **aus dem Bestands-`app.js`** (Logik und API-Verträge 1:1; Schnittgrenzen per Anker-Assertions abgesichert) + dünner Adapter (`view`, `head`, `ico`, `me`). Einziger Eingriff in Logik: Wikilink-Klick im Vault-Leser öffnete im Altportal zusätzlich den globalen Datei-Viewer → jetzt unterdrückt. `LEGACY = {}`; der Embed-Pfad (`/classic/#/…`) bleibt als Fallback im Code.
**Gefunden/behoben:** `.dot` (Statuspunkt) kollidierte mit `.pill.dot` des Alt-CSS (Overflow in JARVIS-Aufträgen); Kopfzeilen mit mehreren Aktionen; Viewer-Layer blieb beim Bereichswechsel offen (`closeViewer()` in `activate`); Deep-Link-Parameter bleiben erhalten (`?p=…`, `?d=…`), jeder Hashwechsel rendert neu.
**Verifiziert (Chromium, 0 JS-Fehler):** Vault (Ordnerliste 17 Zeilen, Notiz per Deep-Link, Wikilink-Navigation, Editor-Umschaltung, Graph, ⋯-Menü, Lesezeichen), Wissen (513 Notizen/1.550 Verbindungen, Canvas gefüllt, Legende, Zoom, Reset), Neu (Server-Statusbericht), JARVIS-Aufträge (15 Jobs, Agenten/Incidents = API), Einstellungen, Musik (Ordner serverseitig leer → korrekte Leeranzeige). Overflow Desktop 1440 und Mobil 390: 0 px in allen 6.
**Nicht getestet (bewusst):** Schreiben/Löschen im echten Vault, Musik-Wiedergabe (keine Dateien), Auftrag starten/Not-Aus (Nebenwirkungen).
**Abnahme gegen SPEC §20:** siehe `A7-ABNAHME-20261027.md` (GO mit dokumentierten Abweichungen).
**Portal-Messung (ehrlich):** neue Shell lädt langsamer als die klassische (Load 169 vs 64 ms, 25 vs 14 Requests; ungebündelte ES-Module). Bündelung/Lazy-Load der großen Module (`port.js` 67 KB) wäre der nächste Hebel; `modulepreload` brachte nichts Messbares.
