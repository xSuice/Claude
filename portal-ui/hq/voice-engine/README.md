# Browser-Sprach-Engine (portal-ui/hq)

Wakeword „Hey Jarvis“ (openWakeWord) + Sprachsegmente (Silero VAD über @ricky0123/vad-web) direkt im Browser, Inferenz mit onnxruntime-web (WASM, 1 Thread).
Kein Audio verlässt das Gerät vor dem Wakeword; danach geht das Segment als 16-kHz-WAV über `/api/voice/stt` an den lokalen Whisper auf dem PC.

Bauen (PC, Node ≥ 20):

    npm ci && bash fetch-models.sh && bash build-voice-engine.sh ..   # schreibt ../js/voice-engine.bundle.js und ../js/vendor/

Tests: `ASSETS=models VADMODEL=node_modules/@ricky0123/vad-web/dist/silero_vad_v5.onnx node test-oww.mjs <wav…>` (Wakeword-Werte + VAD-Segmente), `node test-lag.mjs <wav…>` (Verzögerung Wakeword → Ende der Anrede).
Produktion braucht `script-src 'self' 'wasm-unsafe-eval'` (Caddy-CSP) und Cache-Header für `/staging/js/vendor/` (portal.py, Marker VENDOR-CACHE).
Lizenzen: siehe js/vendor/LICENSES.txt und models/NOTICE.txt.
