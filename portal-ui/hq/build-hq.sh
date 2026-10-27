#!/usr/bin/env bash
# Run from the hq source directory (portal-ui/hq/ in the repository).
set -euo pipefail
for f in js/*.js; do node --check "$f"; done
npm exec --yes --package=esbuild@0.25.12 -- esbuild js/app.js --bundle --minify --format=esm --target=es2022 --outfile=js/app.bundle.js --metafile=bundle-meta.json
node --check js/app.bundle.js
