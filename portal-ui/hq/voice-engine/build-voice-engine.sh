#!/usr/bin/env bash
# Baut js/voice-engine.bundle.js + js/vendor/ (onnxruntime-web WASM, Silero VAD, openWakeWord-Modelle) fuer portal-ui/hq.
# Aufruf: bash build-voice-engine.sh <hq-verzeichnis>   (braucht npm ci in diesem Ordner; Modelle in ./models)
set -euo pipefail
HQ="$1"; V="$HQ/js/vendor"
npx esbuild voice-engine.js --bundle --minify --format=esm --platform=browser --target=es2022 --conditions=onnxruntime-web-use-extern-wasm --outfile="$HQ/js/voice-engine.bundle.js"
node --check "$HQ/js/voice-engine.bundle.js"
mkdir -p "$V/ort-1.22.0" "$V/vad-0.0.31" "$V/oww-0.5.1"
cp node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.mjs "$V/ort-1.22.0/"
cp node_modules/onnxruntime-web/LICENSE "$V/ort-1.22.0/LICENSE.txt" 2>/dev/null || true
cp node_modules/@ricky0123/vad-web/dist/silero_vad_v5.onnx "$V/vad-0.0.31/"
cp node_modules/@ricky0123/vad-web/LICENSE* "$V/vad-0.0.31/" 2>/dev/null || true
cp models/melspectrogram.onnx models/embedding_model.onnx models/hey_jarvis_v0.1.onnx models/NOTICE.txt "$V/oww-0.5.1/"
sha256sum "$V"/*/* | sed "s#$V/##" > "$V/SHA256SUMS"
