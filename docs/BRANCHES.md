# Zweige und Archiv

Stand 28.10.2026. Regel: `main` = aktueller Stand, `server-live` = automatischer Server-Abgleich (`ma-git-sync`, alle 15 min, schiebt den ausgecheckten HEAD). Neue Arbeit in `fix/…` oder `feature/…`, Abschluss per Fast-Forward/Merge nach `main`, danach Zweig löschen — das Tag `archive/<zweig>` hält den Endstand fest.

| Archiv-Tag | Inhalt | Status |
|---|---|---|
| `archive/feature/router-phase1-20261026` | Evidence-Router Phase 1 | in `main` |
| `archive/feature/router-phase2-*` (3) | Provider-Registry, Portal-Service, E2E-Tests | in `main` |
| `archive/feature/v16-cloud-fallback` | Cloud-Fallback V16.1 | in `main` |
| `archive/reconcile/v16-phase2` | Zusammenführung Phase 2 | in `main` |
| `archive/release/a51-evidence-router-20261026` | Release-Zweig Evidence-Router | in `main` |
| `archive/p3-watchdog-hardening` | Watchdog-Härtung | in `main` |
| `archive/fix/prio1-knowledge-evidence` | Prio 1 Nachhärtung 1 | in `main` |
| `archive/fix/prio1-pc-stop` | Prio 1 Nachhärtung 2 + HARD ISOLATE | in `main` |
| `dev/hermes-m1a-live-20261018` (nur remote) | m1a guarded_check | in `main` |
| `pre-sync-reconcile-20261027` | Stand vor der Synchronisierung | Sicherungspunkt |

Wiederherstellen eines Zweigs: `git branch <name> archive/<name>`.

Schutz vor Zugangsdaten: `scripts/git-hooks/pre-commit` (Regeln aus `secretscan.py`), aktivieren mit
`ln -sf ../../scripts/git-hooks/pre-commit .git/hooks/pre-commit`.
