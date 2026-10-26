# Testergebnisse JARVIS V16 Referenz-Audit (2026-10-15)

| Lauf | Ergebnis | Dauer |
|---|---|---|
| Baseline vor Änderung | 323 Tests OK (4 skip) | 2:39 min |
| Neue Tests vor Fix (Rot-Lauf) | 9 von 17 rot | – |
| Nach Fix | 340 Tests OK (4 skip) | 2:43 min |
| Tests im Release (Installer) | grün (`tests-ok`) | – |

Neue Testdatei: `tests/test_v16_regress_a9_a14.py` (17 Tests).
Befehl: `cd brain-runtime && python3 -m unittest discover -s tests -q`.

Messungen: siehe Audit-Bericht (A9 11/11, Fehlalarme 0/8; E2 Leave-one-out 25/35, Fehltreffer 0). Rohdaten: `~/tmp/jref/` (`baseline-tests.txt`, `red-run.txt`, `after-tests.txt`, `e2-eval.json`), Skript `messungen/e2_matcher_eval.py`.
`doctor`: ok.
