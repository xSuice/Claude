# V3 – Website-Sprache auf fertigen Bausteinen (27.10.2026, spät)

Owner-Auftrag: „das mit website muss nochmal überarbeitet werden … schaue nach fertige referenzen“ → Referenzkatalog (`REFERENZKATALOG-20261027.md`) → Owner: „ja mache alles fertig“.

## Was jetzt läuft

| Baustein | Herkunft (Lizenz) | Rolle |
|---|---|---|
| openWakeWord „hey_jarvis“ v0.5.1 | dscripka/openWakeWord (Code Apache-2.0, Modelle CC BY-NC-SA 4.0, privat) | Wakeword direkt im Browser. Bis „Hey Jarvis“ fällt, verlässt kein Ton das Gerät. |
| Silero VAD v5 + FrameProcessor | @ricky0123/vad-web 0.0.31 (ISC), Silero (MIT) | Erkennt Sprechbeginn und Sprechende und ersetzt den eigenen Pegel-Segmentierer. |
| onnxruntime-web 1.22.0 | Microsoft (MIT) | WASM-Inferenz mit 1 Thread (kein COOP/COEP nötig) |
| Zustände + Diagnose-Panel | Muster: Home-Assistant Voice Satellite Card (AGPL, **nur Muster, kein Code**) | Anzeige „Wartet → hört → denkt → spricht“, Live-Balken für den Wakeword-Wert, Regler für die Empfindlichkeit, Diagnose mit „Bericht kopieren“ |
| Whisper + Piper Thorsten emotional | eigener PC (unverändert) | STT/TTS über `/api/voice/*` |

Die Pipeline ist 1:1 wie `openwakeword/utils.py`: 80-ms-Blöcke in int16-Skala, Mel-Spektrum über 1280+480 Samples, x/10+2, Embedding je 8 Mel-Frames über 76 Frames, Klassifikator über 16 Embeddings, die ersten 5 Vorhersagen werden verworfen. Ein früher Fehler im Browser-Port `openwakeword_wasm` ist damit vermieden: Dort fehlt die int16-Skalierung und der Kontext.

## Ablauf
1. **Wake-Modus:** Wakeword und VAD laufen lokal. Segmente ohne „Hey Jarvis“ werden im Browser verworfen und **nicht** gesendet. Vorher ging jedes Segment an Whisper.
2. **„Hey Jarvis …“:** Signalton, dann „Ich höre zu“. Am Ende des Segments wird „Hey Jarvis“ abgeschnitten, gemessen 0,35–0,45 s vor dem Auslösen. Nur der Rest geht als WAV an Whisper.
3. **Nur „Hey Jarvis“ gesagt:** JARVIS wartet 8 s auf die Frage.
4. **Antwort:** Während JARVIS spricht, ist der VAD aus (kein Selbstecho). Das Wakeword bleibt aktiv: „Hey Jarvis“ unterbricht ihn.
5. **Danach 12 s Folgefenster ohne Wakeword.** Danach braucht es wieder „Hey Jarvis“.
6. **Fallbacks:** Lädt die Engine nicht (alter Browser), greift die alte Text-Wake-Strecke. Ist der PC aus, greift die Browser-Erkennung mit Einwilligung.

Gegen Whisper-Halluzinationen bei Stille („Copyright WDR 2020“, „Untertitel …“) gibt es einen Filter. Füllwörter vor Folgefragen („Und welche Aufgaben …“) treffen jetzt die lokale Antwort.

## Server-Änderungen (Backups daneben)
- Caddy-CSP: `script-src 'self' 'wasm-unsafe-eval'` erlaubt **nur** das Kompilieren von WebAssembly, kein JS-`eval`. Geändert in `/etc/ma-home/Caddyfile` und in der Vorlage `/opt/ma-home/manage.py`, Backups `*.bak-vor-voiceengine-20261027`. Container `ma-home-caddy-1` wurde neu gestartet, `caddy validate` war vorher OK.
- `portal.py`: Marker `VENDOR-CACHE` → `/staging/js/vendor/*` = `private, max-age=30 Tage, immutable`. Die Dateien liegen in versionierten Ordnern; die WASM-Datei hat 11 MB und wird nur einmal geladen.
- `portal.py`: Marker `STT-LIMIT` → Waitress-Transportgrenze 128 KiB → 2 MiB. Die Flask-Grenze von 128 KiB gilt weiter für **alle** Routen außer `/api/voice/stt` (1,2 MB Audio ≈ 37 s). Dreifach-Probe: STT 300 KB → erreicht den PC, andere Route 300 KB → 413, STT 1,5 MB → 413.
- `jarvis_voice.py`: Grenze pro Anfrage, Tests 7/7 (inkl. „globale Grenze bleibt“).

## Nachweise
- Node mit echten Modellen und Audio: „Hey Jarvis …“ (Thorsten) 0,85–0,98; Referenzaufnahme 0,998. Fünf Negativsätze ≤ 0,002, darunter „Jarvis ist ein Name aus einem Film“ und „Ja, bis morgen“. CPU ≈ 55 ms je Sekunde Audio (1 Kern); im Browser 2,4–3,1 ms je 32-ms-Rahmen.
- Browser-E2E auf dem ausgelieferten Build mit Produktions-CSP, **synthetischem Mikrofon** (Piper-Audio in einen MediaStream) und null CSP-Verstößen:
  - Satz ohne Wakeword → nichts passiert, nichts gesendet.
  - „Hey Jarvis, wie spät ist es?“ → Transkript „Wie spät ist es?“, lokale Antwort nach 4,1 s.
  - Folgefrage „Und welche Aufgaben sind offen?“ ohne Wakeword → lokal beantwortet („8 offene Aufträge, davon 0 aktiv“).
  - Nach Ablauf des Fensters wird „Wer arbeitet gerade?“ ohne Wakeword ignoriert.
  - Freie Frage → Modellantwort (haiku) mit lokaler Stimme, ca. 13 s davon entfallen auf das Modell.
  - „Hey, Jarvis“ während JARVIS spricht → unterbricht und hört zu.
- Unit-Tests: Portal-Node 33/33 (7 Dateien), Proxy 7/7.

## Grenzen (ehrlich)
- Das Modell ist englisch trainiert; der Satz lautet **„Hey Jarvis“**, ein bloßes „Jarvis“ reicht nicht. Die synthetische deutsche Stimme erreicht bei „Hey Jarvis.“ allein nur 0,47–0,59. Deshalb liegt die Standard-Schwelle bei 0,40 statt 0,50, einstellbar über den Regler. Mit einer echten Stimme ist das **noch nicht gemessen**: Die Referenzaufnahme eines Menschen erreicht 0,998.
- Whisper `base` verhört seltene Wörter („Minecraft“ → „Minikraft“).
- Echtes Mikrofon, Handy-Browser und Bildschirmsperre sind nicht getestet. Der Test lief mit synthetischem Audio.
- Modelle CC BY-NC-SA: nur nicht-kommerziell.

## Rückbau
`sudo cp /etc/ma-home/Caddyfile.bak-vor-voiceengine-20261027 /etc/ma-home/Caddyfile && sudo docker restart ma-home-caddy-1`; `sudo cp /opt/ma-home/portal.py.bak-vor-voiceengine-20261027 /opt/ma-home/portal.py && sudo systemctl restart ma-home-web` (setzt beide Portal-Marker zurück); Staging-JS: `*.bak-vor-voiceengine` in `/opt/ma-home/web/staging/js/`.
