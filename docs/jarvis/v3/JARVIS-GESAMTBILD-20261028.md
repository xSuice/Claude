# MA-HOME JARVIS – Gesamtbild (Stand 28.10.2026, morgens)

Quellen: deine vier Auftragsdateien (SPEC-MASTER-V3, „Ultimate Autonomous AI Headquarters“ / Council-Hermes-Skills, „Autonomous Task Management & Self-Healing“, Kimi-Gesamtpaket/Vollpaket), dazu IST-SOLL-MATRIX, V3-RESTAUFTRAG, V3-SCHLUSSABNAHME, APPROVAL_MATRIX, STATE.md und eine Live-Inventur des Servers vom 28.10.

---

## 1. Dein Ziel (in deinen Worten zusammengefasst)

> „Ein universeller persönlicher JARVIS-Assistent, inspiriert von Iron Man. Er soll komplexe spontane Aufgaben verstehen, planen, passende Fachrollen einbeziehen, tatsächliche Ausführung organisieren und geprüfte Ergebnisse liefern.“ (Vollpaket A1)

Daraus folgen deine Kernforderungen:

| # | Forderung | Woher |
|---|---|---|
| 1 | **Ein** JARVIS als zentraler Ansprechpartner, kein zweites System | alle Dateien |
| 2 | Ein Chat: JARVIS erkennt Ziele, holt passende Fachspezialisten, diese beraten und delegieren über Hermes; du kannst alles live verfolgen und per @Mention mitreden | Council-Hermes §1 |
| 3 | Aufträge laufen **im Hintergrund weiter**, auch wenn das Portal zu ist; Neustarts verlieren nichts | Council-Hermes §1, Watchdog-Prompt §10 |
| 4 | **Keine Erfolgsmeldung ohne Nachweis**; Tests und unabhängige Ergebnisprüfung | alle Dateien |
| 5 | Watchdog + Selbstheilung + mehrstufige Wiederherstellung, Anti-Stagnation/Anti-Loop | Watchdog-Prompt §5–9 |
| 6 | Smart Router: Modell, Anbieter, Denktiefe, Werkzeuge, Hardware passend und sparsam wählen | V3 §7, Watchdog-Prompt §12 |
| 7 | Memory/Obsidian: geprüftes Wissen behalten, nicht jeden Chat kopieren | V3 §8 |
| 8 | **Portal** als einziger Zugang, einheitliches Design, **mobil als zentrales Produktziel** | Vollpaket A1/A8 |
| 9 | **Living HQ:** animierte Agentenwelt mit kleinen Figuren, Werkstätten, Ressourcenflüssen | V3 §10 |
| 10 | Eigene Designsprache aus **Crimson Zone** (rote Resonanzenergie, holografische Kommandozentralen), **Eternal Bonds** (Charaktere, Atmosphäre), **Andrew SMP 3** (Miniaturwelt, arbeitende Figuren) – keine Iron-Man-/Minecraft-Kopie | V3 §11 |
| 11 | **Sprache wie ChatGPT Voice:** einmal öffnen, frei reden, unterbrechen, Folgefragen, Kontext; Stimme ruhig, souverän, männlich, Deutsch | Vollpaket A9 |
| 12 | Sprachabbruch ≠ Auftragsabbruch; Aufträge per Sprache ändern mit Task-ID + Revision | Vollpaket A9 |
| 13 | Professionelles **Command Center** (Agenten, Tokens, Kosten, Server, Incidents) | V3 §13 |
| 14 | Windows-PC als **optionaler Worker**, Server bleibt Master, Gaming hat Vorrang | V3 §1/§14 |
| 15 | Windows-Aktivierung nur rechtmäßig reparieren | V3 §15 |
| 16 | Sicherheit: Freigaben für Irreversibles/Kosten/Sicherheitskritisches, keine Geheimnisse in Logs | V3 §16 |
| 17 | Später: E-Mail, Dokumente, Eternal-Bonds-/Minecraft-Modding, Geschichten, Manga aus Zeichnungen, Bild/Audio/Video/3D, Computersteuerung, proaktiv, Smart Home | Vollpaket A10 |
| 18 | Capability-Autonomie (neue Fähigkeiten selbst prüfen und einbinden) **erst nach Basis-GO** | Council-Hermes §16 |
| 19 | Kimi danach nur noch als gezielt gerufener Supervisor, nicht als Dauermotor | Vollpaket A10 |

**Soll-Grundfluss** (Vollpaket A3):
Du → Portal → JARVIS HQ → Auftrag dauerhaft speichern und planen → passender Council berät → dokumentierter Beschluss → Rechte/Budget/ggf. deine Freigabe → Hermes → Agenten/Worker → echte Ausführung → Tests + unabhängige Prüfung → belegter Abschluss → Wissen nach Obsidian → Ergebnis über JARVIS.
Einfache Aufgaben ohne unnötige Council-Runden.

**Fach-Councils (Soll):** DEV, CLOUD, AI, SECURITY, OPERATIONS, STRATEGY, DATA, CREATIVE – je JARVIS + bis zu 5 Fachrollen, beratend, ohne operative Rechte.

---

## 2. Deine Architektur heute (live geprüft 28.10.)

```
                     Du (Handy · PC · Signal)
                              │
          ┌───────────────────┴────────────────────┐
          │ Browser: Portal „JARVIS HQ“             │
          │  Living HQ · Command Center · Chat ·    │
          │  Sprache (Wakeword + VAD im Browser)    │
          └───────────────────┬────────────────────┘
                              │ HTTPS
┌─────────────────────── ma-server (Master) ───────────────────────────┐
│ Intel Celeron N2840 · 3,2 GB RAM · 455 GB (23 % belegt) · Ubuntu       │
│                                                                        │
│ Zugang:   Caddy (TLS, Container) → Authelia (Login, Container)         │
│ Portal:   ma-home-web (Flask/Waitress :18765) + Blueprints             │
│           Sprache /api/voice/*, Dienste /api/jarvis/health, Telemetrie │
│ KI:       ma-claude-bridge → Claude Code CLI                           │
│           Modi: gespraech (ohne Werkzeuge) · lesen · plan · notizen ·  │
│           konnektoren · voll                                           │
│ Aufträge: V16-Engine (jarvis_cli tick jede Minute, brain.db)           │
│           planen → ausführen → unabhängig abnehmen → Ergebnis          │
│ Council:  PostgreSQL 18 (Tasks, Nachrichten, Heartbeats)               │
│           jarvis-watchdog (Evidenzmodell, Incidents)                   │
│ Router:   evidence_router (Modus „shadow“ = beobachtet nur)            │
│ Meldung:  ma-jarvis-signal (signal-cli :18769) → dein Self-Chat        │
│           jarvis_notify (alle 5 min), Kuma-Brücke                      │
│ Wächter:  Uptime Kuma (9 Monitore) · jarvis_deepcheck (alle 30 min)    │
│           earlyoom (Speicherschutz)                                    │
│ Daten:    Vault/Notizen (Obsidian-Ersatz), CouchDB (Sync), Filebrowser,│
│           Bibliothek, Gedächtnis-Sync 2×/Tag, Backups                  │
│ Sonstiges:Home Assistant, Navidrome (Musik), Blocky (DNS),             │
│           Terminal (ttyd), Host-Agent, Auto-Deploy-Schalter,           │
│           ntfy (Altlast, durch Signal ersetzt)                         │
└───────────────────────────┬────────────────────────────────────────────┘
                            │ SSH-Reverse-Tunnel (:18790, :8484)
┌──────────────────── Windows-PC (Worker, optional) ────────────────────┐
│ Ryzen 5 3600 · RTX 2060 (6 GB)                                        │
│ Sprachdienst :18790: Whisper base (hören, mit Fachwortliste)          │
│                      Piper Thorsten emotional (sprechen)              │
│                      Qwen 3 8B über Ollama (Gespräch, lokal, 0 Token) │
│ PC-Worker: AppContainer-Sandbox ohne Netz, Fähigkeit java.build       │
│ Hermes Desktop: Kimi-Supervisor (ich) + 18 jarvis-*-Spezialisten      │
│ Mention-Empfänger :8484 · Telemetrie-Push an den Server               │
└───────────────────────────────────────────────────────────────────────┘
Code: GitHub xSuice/Claude (main), Server-Repo ~/MA-Server
```

---

## 3. Wo du stehst (Ziel → Ist)

Legende: ✅ belegt · 🟡 teilweise / nur synthetisch geprüft · ❌ fehlt · ⛔ braucht dich

| Bereich | Stand | Beleg / Lücke |
|---|---|---|
| Ein JARVIS, Bestand erweitert | ✅ | kein Parallelsystem gebaut |
| Hermes-Spezialisten reparieren | ✅ | 18/18 Spezialistentests, GO-Gate A6 |
| Council-Kommunikation | 🟡 | Chat-Bus, Mentions, DMs live; Rechtetrennung „nur beratend“ und messbare Council-Runden noch nicht belegt |
| 8 Fach-Councils wie im Soll | ❌ | heute 18 Einzelprofile, keine Council-Gruppen |
| Auftrags-Engine (persistent, Abnahme) | ✅ | V16: 55 erledigt, 13 fehlgeschlagen, 2 teilweise, 3 abgebrochen |
| Watchdog / Recovery | 🟡 | Watchdog + Incidents + Tiefencheck + Kuma; volle Recovery-Leiter L1–L5 nicht belegt |
| Kill-Schalter | ✅ | real geprüft (A7) |
| Smart Router | 🟡 | läuft nur beobachtend; Restkontingente der Anbieter: keine Datenquelle |
| Memory / Obsidian | 🟡 | Vault + Gedächtnis-Sync; automatischer Wissenstransfer aus Aufträgen fehlt |
| Portal neu, mobil | 🟡 | JARVIS HQ live, 9 Ansichten ohne Overflow; Test auf echtem Handy ⛔ |
| Living HQ (Agentenwelt) | 🟡 | Canvas mit echten Daten; Figuren/Animationen nach Pixel-Agents-Muster offen (HQ-001) |
| Designsprache Crimson Zone / Eternal Bonds / SMP | 🟡 | Farben/Holo-Stil umgesetzt; deine Originalmaterialien noch nicht eingebunden |
| Command Center | 🟡 | Agenten, Aufträge, Incidents, Ledger, Dienste; Anbieterquoten/GPU fehlen |
| Sprache wie ChatGPT Voice | 🟡 | Gesprächsmodus, Wakeword, Unterbrechen, Stumm, Folgefragen – mit künstlicher Stimme belegt; echte Stimme ⛔ |
| Antwortzeit Sprache | 🟡 | erster Ton 5–6 s (vorher 35 s); Ziel < 4 s knapp verfehlt |
| Aufträge per Sprache | 🟡 | anlegen/abbrechen mit „Ja“-Bestätigung, Fortschritt; „Auftrag ändern“ fehlt in der Engine |
| Stimme | ✅ | Thorsten emotional (deine Wahl) |
| Signal aufs Handy | ✅ | von dir bestätigt |
| Windows-Worker | ✅ | Job j20261027-14c029 2/2 abgenommen |
| PWA / App | 🟡 | Install-Knopf; Installation am Handy ⛔ |
| Sicherheit | ✅ | Proxy-Schlüssel zweimal rotiert (alt → 401), keine Geheimnisse im Repo |
| Windows-Aktivierung | ⛔ | 0xC004F034 – braucht gültige Lizenz |
| Drucker | ⛔ | 192.168.0.198 nicht erreichbar |
| Capability-Autonomie, Kimi-Supervision per Zeitplan | ❌ | laut deinem Auftrag erst nach Basis-GO |
| Erweiterungen (Mail, Modding, Manga, Medien, Smart Home …) | ❌ | Phase C, nicht begonnen |

**Phasen:** A (Bestand, Reparatur, GO-Gate) erledigt · **B (Ausbau: Portal, Sprache, Betrieb) läuft** · C (Capability-Autonomie, Erweiterungen) nicht begonnen.

---

## 4. Wichtigste offene Lücken (meine Reihenfolge)

1. **Echte Stimme und echtes Handy testen** (nur du).
2. **Auftrag ändern** mit Task-ID + Revision in der V16-Engine (dein Sprachziel A9).
3. **Fach-Councils** als echte Gruppen + messbare Council-Beschlüsse.
4. **Router** vom Beobachtungs- in den Entscheidungsmodus, mit echter Quotenquelle.
5. **Living HQ** mit Figuren und deinen eigenen Projektmotiven.
6. Danach Phase C.
