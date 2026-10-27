# Referenzkatalog – fertige Vorlagen und Bausteine für MA-HOME JARVIS (27.10.2026)

Ziel: vorhandene, gepflegte Open-Source-Bausteine nennen, die man **in das bestehende JARVIS / Portal übernehmen** kann. Es geht nicht um einen Neubau.
Die Metadaten (Lizenz, Sterne, letzter Push) stammen am 27.10.2026 aus der GitHub-API, Rohdaten in `deepsearch-evidence/referenzkatalog-repos.json`.
Lizenzbewertung für **privaten Eigenbetrieb**. Bei AGPL/GPL wird nur das Muster übernommen, kein Code, damit das Portal frei lizenzierbar bleibt.

Legende: **Übernehmen** = Code/Paket direkt einbauen · **Muster** = Aufbau/UX nachbauen · **Daneben** = als eigener Dienst neben JARVIS betreiben

## 1. Sprache im Portal (Problembereich: Wakeword/Dialog auf der Website)

| Baustein | Lizenz | Stand | Was wir davon nehmen | Art |
|---|---|---|---|---|
| [@ricky0123/vad-web](https://github.com/ricky0123/vad) (Silero VAD im Browser) | ISC (npm 0.0.31) | aktiv, Push 09/2026, 2,1k★ | **Ersetzt meinen selbstgebauten Pegel-Segmenter.** Neuronale Spracherkennung mit `onSpeechStart`/`onSpeechEnd` und 16-kHz-Audio, robust gegen Lüfter/TV. Das ist die Hauptursache für „funktioniert nicht richtig“. | Übernehmen |
| [openWakeWord](https://github.com/dscripka/openWakeWord) + Browser-Port [openwakeword_wasm](https://github.com/dnavarrom/openwakeword_wasm) | Code Apache-2.0; **Modelle CC BY-NC-SA** (privat ok, nicht kommerziell) | Kern aktiv; WASM-Port klein (8★, keine Lizenzangabe → nur als Muster) | **Fertiges „hey_jarvis“-Modell** läuft lokal im Browser, alle 80 ms ein Score. Das Wakeword wird dann akustisch erkannt statt aus dem Transkript geraten; der PC bekommt erst danach Audio. | Übernehmen (Modell + onnxruntime-web), WASM-Port als Muster |
| [Porcupine Web](https://picovoice.ai/docs/quick-start/porcupine-web/) | proprietär, AccessKey nötig; der Anbieter zählt jeden Browser als Nutzer | – | Alternative mit deutschem Modell, aber Konto und Key nötig. **Nicht empfohlen** (Bindung an den Anbieter) | – |
| [pipecat smart-turn](https://github.com/pipecat-ai/smart-turn) | BSD-2 | 1,6k★ | Modell für das Sprechende: unterscheidet „Pause beim Nachdenken“ von „fertig“. Passt auf den PC-Voice-Dienst, damit JARVIS nicht reinredet. | Übernehmen (PC-Seite) |
| [Voice Satellite Card (Home Assistant)](https://github.com/jxlarrea/voice-satellite-card-integration) | AGPL-3.0 | aktiv, 908★ | Beste **UX-Vorlage** für den Browser als Freisprech-Satellit: Zustände (wartet → hört → denkt → spricht), Diagnose-Panel mit Prüfungen (sicherer Kontext, Mikrofonrecht, TTS) und Button „Bericht kopieren“. | Muster |
| [Home Assistant Assist / Wyoming](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/) | – (Doku) | – | Referenz-Pipeline Wake → STT → Intent → TTS mit lokalem Whisper/Piper; bestätigt unseren PC-Ansatz. `wyoming-satellite` ist **archiviert**, also nicht einbauen. | Muster |
| [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit) / [LiveKit Agents UI](https://github.com/livekit/components-js) | BSD-2 / Apache-2.0 | sehr aktiv | Fertige Komponenten für **Audio-Visualizer, Gesprächsstatus und Transkript**; vorbildliche Sprechanzeige. React-basiert, deshalb als Design-/Logikvorlage für unsere ES-Module. | Muster |
| [micdrop.dev: Wakeword-Vergleich](https://micdrop.dev/blog/wake-word-detection-web-app) | Artikel | 2026 | Entscheidungshilfe: Wakeword-Modell im Browser für Dauerlauschen, sonst Push-to-Talk mit VAD. | Referenz |

## 2. Chat- und Agenten-Oberfläche (Portal-Chat, Aufgaben, Spezialisten)

| Baustein | Lizenz | Stand | Nutzen | Art |
|---|---|---|---|---|
| [assistant-ui](https://github.com/assistant-ui/assistant-ui) | MIT | 12,8k★, täglich gepflegt | Chat-Bausteine: Streaming, Tool-Aufrufe sichtbar, Anhänge, Bearbeiten/Neu generieren | Muster (React) |
| [CopilotKit / AG-UI-Protokoll](https://github.com/CopilotKit/CopilotKit) | MIT | 38k★ | **AG-UI**: Standard-Eventformat Agent → UI (Schritt gestartet, Tool läuft, Zustand). Passt auf unsere Jobs/Events | Muster (Eventformat) |
| [LibreChat](https://github.com/LibreChat-AI/LibreChat) | MIT | 46k★ | Vorlage für Agenten-/MCP-Verwaltung, Modellwahl, Konversationssuche | Muster |
| [LobeHub](https://github.com/lobehub/lobehub) | eigene Lizenz (NOASSERTION) | 83k★ | Sehr ausgereifte TTS-/STT-UX und Agenten-Marktplatz-Optik | Muster (nur ansehen) |

## 3. Portal-Design, Dashboard und Mobile

| Baustein | Lizenz | Nutzen | Art |
|---|---|---|---|
| [shadcn/ui Blocks](https://ui.shadcn.com/blocks) | MIT | Fertige Dashboard-, Sidebar- und Login-Layouts; Tokens passen zu unserem Designsystem | Muster |
| [Tremor](https://github.com/tremorlabs/tremor) | Apache-2.0 | Diagramm- und KPI-Karten für Kosten, Router-Quoten und Worker-Last (letzter Push 10/2025, ruhiger) | Muster |
| [dnd-kit](https://github.com/clauderic/dnd-kit) | MIT | Barrierearmes Drag & Drop für ein Aufgaben-Kanban | Übernehmen (bei Kanban) |
| [Homarr](https://github.com/homarr-labs/homarr) | Apache-2.0 | Homelab-Widgets mit 80+ Integrationen und [Dashboard-Icons](https://github.com/homarr-labs/dashboard-icons) | Muster/Icons |
| [Homepage](https://github.com/gethomepage/homepage) · [Glance](https://github.com/glanceapp/glance) | GPL-3.0 · AGPL-3.0 | Kompakte Service-Kacheln und Feeds; gute Mobile-Dichte | Muster |
| [MDN PWA Best Practices](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Best_practices) / [web.dev Install-Muster](https://web.dev/articles/pwa-install-patterns) | Doku | Portal als installierbare App aufs Handy, statt die zurückgestellte APK | Referenz |

## 4. Betrieb, Beobachtung, Gedächtnis

| Baustein | Lizenz | Nutzen | Art |
|---|---|---|---|
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | MIT | Health-Checks für Portal, Signal, Voice-Dienst und PC-Worker mit Statusseite. Hätte den heutigen Ausfall des Voice-Dienstes sofort gemeldet; Benachrichtigung über Signal ist eingebaut. | **Daneben** (Docker) |
| [Langfuse](https://github.com/langfuse/langfuse) | MIT-Kern + EE-Teile | Traces und Kosten pro Agentenlauf, Evaluierungen; ersetzt Eigenbau-Telemetrie teilweise. Server-RAM (3,2 GB) ist knapp → eher auf dem PC. | Daneben (prüfen) |
| [Letta (MemGPT)](https://github.com/letta-ai/letta) | Apache-2.0 | Referenzmodell für Langzeitgedächtnis (Kern- vs. Archivspeicher) als Vorlage für jarvis-brain | Muster |
| [n8n](https://github.com/n8n-io/n8n) | Fair-Code (Sustainable Use) | Fertige Workflow-Vorlagen (Mail, Kalender, RSS → Agent). Privat erlaubt | Daneben (optional) |

## Empfehlung – Reihenfolge

1. **Website-Sprache neu auf fertigen Bausteinen (behebt das gemeldete Problem):** `vad-web` (Silero) statt Eigenbau-Pegel, `openWakeWord hey_jarvis` im Browser für das Wakeword, Zustände und Diagnose-Panel nach dem Muster der Voice Satellite Card. Das Sprechen bleibt bei „Hey Jarvis“, weil es dafür ein fertiges Modell gibt.
2. **Uptime Kuma** als Wächter für alle Dienste mit Signal-Alarm.
3. **Portal als PWA** (Manifest, Installationshinweis) statt APK.
4. Danach optional: AG-UI-Eventformat für Aufgaben-Fortschritt, Tremor-Karten für Kosten/Quoten, Kanban mit dnd-kit.

Jarvis: Phase B – Referenzkatalog mit 24 geprüften Bausteinen erstellt – Entscheidung: Punkt 1 (Website-Sprache auf vad-web + openWakeWord) jetzt umsetzen?
