## Was ändert sich?
<!-- Ein bis drei Sätze. Bezug: Paket/Auftrag (z.B. PRIO2 N1). -->

## Nachweis
- [ ] Tests lokal/auf dem Server ausgeführt — Befehl + Ergebnis (z.B. `Ran 494 tests … OK`):
- [ ] Neue Logik hat einen Test, der vorher rot war
- [ ] Bei Live-Änderung: Read-back vom Ziel (Endpunkt, Journal nach Neustartgrenze, Release-Status)

## Sicherheit
- [ ] Keine Zugangsdaten/Token im Diff (pre-commit-Hook aktiv, nicht mit `--no-verify` umgangen)
- [ ] Keine Lockerung von Freigaben, Sandbox, Not-Aus oder Router-Fail-closed
- [ ] Persistierte Nutzertexte laufen durch `secretscan.redact`

## Betrieb
- [ ] Auslieferung nur über `install-v16.sh` (kein In-place-Edit im Live-Release)
- [ ] Rückweg benannt (`rollback-v16.sh` / `.bak-vor-<änderung>`)
- [ ] Dienst-Neustarts: Owner-Freigabe eingeholt
- [ ] `STATE.md` / Roadmap aktualisiert
