# Änderungen JARVIS V16 Referenz-Audit (2026-10-15)

Repo `server/jarvis/core/brain-runtime/` (Auto-Sync Commit f57d32f):
- `secretscan.py` neu; `runner.redact` und `classify` nutzen es; Auftrag/Ziel nur geschwärzt gespeichert.
- `taskengine.py`: `approve(..., by=)` mit Pflicht-Urheber `cli:|portal:`, Pflicht-Antwort bei Rückfrage; `_finalize` wertet unbeantwortete Rückfrage nie als done; Kostenfrage lokal (`is_usage_question`, `_answer_usage`, plan_source `local:usage`).
- `attribution.py`, `learning.py`: nie aus `local:`/unbeantworteten Jobs lernen; E2 `norm_kw`/`_stem`.
- CLI `--by`; Bridge-Quelle `--by portal:<user>`; Portal `app.js` verlangt Antwort bei Rückfrage.
- Neu: `tests/test_v16_regress_a9_a14.py`, `docs/jarvis/messungen/e2_matcher_eval.py`, `build_entscheidungsmatrix.py`, `repomap_poc.py`, Entscheidungsmatrix CSV.

Deploy: `install-v16.sh`, Sicherung `~/.local/share/ma-jarvis/backups/20261015-140650`, `current` auf `releases/20261015-140650-f57d32f` (vorher `…040726-91bb3b8`). Rückweg: `bash ~/MA-Server/server/jarvis/rollback-v16.sh`.

Offen bei Philipp: `sudo bash ~/MA-Server/server/claude-bridge/update-bridge.sh`, danach `portal-ui/deploy-ui.sh` (sudo).
