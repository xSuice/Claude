# V3 – Referenzsammlung (Prüfdatum 27.10.2026)

**Methode:** Metadaten (Lizenz, letzter Push, Archivstatus, Sterne) am 27.10.2026 per GitHub-API abgerufen; Dokumentations-Links per HTTP-Abruf auf Erreichbarkeit geprüft (alle 200). **Keine dieser Referenzen wurde in diesem System installiert oder getestet.** Kennzeichnung daher durchgehend: *dokumentiert* (Metadaten/Seite geprüft) bzw. *Einschätzung* (meine Bewertung). Keine Leistungsangaben aus Herstellerwerbung übernommen. Rohdaten: `refs_github.json`.

## Zu konkreten Lücken dieses Systems

| Lücke | Referenz | Link | Lizenz / Pflege (geprüft) | Nutzen für JARVIS (Einschätzung) | Risiken / Grenzen |
|---|---|---|---|---|---|
| Wakeword nicht zuverlässig, Audio geht an Browseranbieter | openWakeWord | https://github.com/dscripka/openWakeWord | Apache-2.0, letzter Push 30.12.2025, 2,9 k Sterne | Lokale Wakeword-Erkennung ohne Cloud; passt zu Datenschutz-Einwilligungsregel | Pflege verlangsamt; eigenes Wort „Jarvis“ braucht ggf. Training; läuft auf dem PC, nicht auf dem Celeron-Server (nicht gemessen) |
| Lokale Spracherkennung (Phase B) | faster-whisper | https://github.com/SYSTRAN/faster-whisper | MIT, aktiv (Push 25.10.2026), 26 k Sterne | GPU-Erkennung auf der RTX 2060 statt Browser-Cloud | VRAM-Konkurrenz mit Spielen (Gaming-Vorrang); Modellgröße vs. 6 GB VRAM nicht gemessen |
| Alternative STT | whisper.cpp | https://github.com/ggml-org/whisper.cpp | MIT, aktiv (19.10.2026) | CPU-fähig, kleinere Abhängigkeiten | Langsamer ohne GPU (Einschätzung) |
| Lokale Sprachausgabe | piper1-gpl (Nachfolger) / piper (archiviert) | https://github.com/OHF-Voice/piper1-gpl , https://github.com/rhasspy/piper | **piper: MIT, aber archiviert (26.08.2025); piper1-gpl: GPL-3.0**, aktiv | Natürliche lokale deutsche Stimme | GPL-3.0 beachten, wenn Code eingebunden statt nur aufgerufen wird; Archiv-Repo nicht verwenden |
| Sprach-/Satelliten-Protokoll | Wyoming | https://github.com/OHF-Voice/wyoming | MIT, Push 29.09.2026 | Standardprotokoll für STT/TTS/Wakeword-Bausteine (Home-Assistant-Ökosystem) | Nur sinnvoll, falls Home Assistant ohnehin genutzt wird |
| Smart Home (später) | Home Assistant Core | https://github.com/home-assistant/core | Apache-2.0, aktiv (27.10.2026), 92 k Sterne | Auf dem Server existiert bereits der Hostname `ha.ma-server.duckdns.org` (siehe Hosts-Eintrag im Layout); Integration via bestehende Instanz statt Neubau | Ob die Instanz aktuell läuft, wurde hier **nicht** geprüft |
| Dauerhafte Aufgaben/Recovery | Temporal | https://github.com/temporalio/temporal | MIT, aktiv | Referenz für Idempotenz, Retries, Resume-Muster | Eigener Server-Dienst; für 3,2 GB RAM-Server ungeeignet (Einschätzung) → nur als Musterquelle |
| Dauerhafte Workflows, leichtgewichtig | DBOS Transact (Python) | https://github.com/dbos-inc/dbos-transact-py | MIT, aktiv (26.10.2026) | Bibliothek auf Postgres-Basis; Postgres existiert bereits (Council-DB) | Würde die vorhandene Task-Engine duplizieren; nur bei konkretem Lückenbefund erwägen |
| Agent-Checkpointing | LangGraph | https://github.com/langchain-ai/langgraph | MIT, aktiv | Referenz für Checkpoints/Resume in Agenten-Graphen | Neues Framework = „zweite Plattform“, widerspricht §0; nur Mustervorlage |
| Memory-Schicht | mem0 | https://github.com/mem0ai/mem0 | Apache-2.0, aktiv | Vergleichsreferenz | Bestehendes brain.db/Memory deckt Bedarf; Neuaufbau nicht begründet |
| Hermes-Funktionen | Hermes Agent Doku / Repo | https://hermes-agent.nousresearch.com/docs/ , https://github.com/NousResearch/hermes-agent | MIT, aktiv (27.10.2026) | Maßgebliche Quelle für Cron, MCP, Delegation, Bot-Mode | – |
| MCP-Spezifikation | Model Context Protocol | https://modelcontextprotocol.io/specification/ , https://github.com/modelcontextprotocol/modelcontextprotocol | Lizenz im Repo „NOASSERTION“ (Mischlizenz, vor Nutzung lesen) | Maßstab für Berechtigungs-/Auth-Modell von MCP-Servern | – |
| Browser-Steuerung via MCP | playwright-mcp | https://github.com/microsoft/playwright-mcp | Apache-2.0, Push 22.10.2026 | Mögliche Alternative zur vorhandenen Browserkopplung | Rechte-/Isolationsfrage; nicht evaluiert |
| Prompt-Injection / Agentenrisiken | OWASP Top 10 for LLM Applications | https://genai.owasp.org/llm-top-10/ , https://github.com/OWASP/www-project-top-10-for-large-language-model-applications | Lizenz „NOASSERTION“; Repo-Push 05.08.2026 | Prüfraster für §7 (Prompt-Injection, Excessive Agency) | Allgemeines Raster, kein Werkzeug |
| Prozess-Überwachung | systemd `WatchdogSec`/`Restart=` | https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html | Dokumentation, Seite erreichbar | Basis für Selbstüberwachung von Diensten ohne Modellaufrufe | Gilt nur für systemd-Dienste auf dem Server, nicht für Windows-Prozesse |
| Isolation unter Windows | AppContainer-Dokumentation | https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation | Microsoft-Doku, erreichbar | Maßgeblich für den derzeit scheiternden Sandbox-Pfad (0x80070005) | Ursache auf diesem Gerät nicht erklärt (siehe V3-ABSCHLUSS-GATES.md) |
| Isolation unter Linux | gVisor | https://github.com/google/gvisor | Apache-2.0, aktiv | Referenz für starke Container-Isolation | Für Celeron-Server vermutlich zu schwer (Einschätzung); nicht Windows |
| Barrierearme Bedienung | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | W3C-Standard | Prüfmaßstab für Kontrast, Fokus, reduzierte Bewegung im Portal | Das Portal wurde **nicht** formal gegen WCAG auditiert |
| Wissensbasis | Obsidian | https://github.com/obsidianmd/obsidian-releases | Repo enthält Plugin-/Themelisten, keine Programmlizenz im Repo | Bereits als Vault im System genutzt | Kein Neuaufbau nötig |

## Eigene Beobachtungen aus der Praxis (getestet, nicht aus Fremdquellen)
- Browser-SpeechRecognition: Einzelmodus erkannte „Wie spät ist es?“ real (Konfidenz 0,91), Dauermodus unzuverlässig → Begründung für lokale Wakeword-Erkennung (Vorschlag U-01).
- Claude-CLI-Grundkontext ≈ 31 000 Token je Aufruf; Cache wirkt (Haiku warm 0,00032 USD, Sonnet warm 0,00318 USD, Sonnet kalt 0,0858 USD, Listenpreisäquivalent).

## Nicht oder nur teilweise untersucht (ehrlich offen)
Mission-Control-Oberflächen anderer Projekte, Kreativ-Toolchains (Manga/3D/Video), Computersteuerung, Eternal-Bonds-/Minecraft-Modding-Werkzeuge, Benachrichtigungsdienste. Dafür liegt keine geprüfte Referenz vor; sie werden nicht erfunden.
