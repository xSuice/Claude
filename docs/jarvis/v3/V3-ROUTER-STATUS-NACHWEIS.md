# V3 – Router, Statussemantik und Ledger: Nachweis

## Router
- RED: Test `test_exact_ack_uses_small_model` meldete sonnet statt haiku.
- GREEN: eng begrenztes vollständiges Muster `Antworte nur mit OK|ja|nein|bereit` nur bei lesendem Modus, ohne Bilder; manuelle Modellwahl bleibt vorrangig. Keine Quoten-/Rechteänderung.
- Tests: 49 Bestandsfälle und 5 neue unittest-Fälle bestanden (lokal und Server).
- Aktivierung: `/usr/local/lib/router_core.py`, Backup `.bak-vor-ack-v3`; ma-claude-bridge nach Neustart active. Live-Datei SHA256 `60304029e5af438e445665202a487ee2f0a6238c41f77119683ccb81ece8fc2f`.
- Echte POST-/api/claude-Gegenprobe mit model=auto: bridge_model=haiku, system.model=claude-haiku-5-5. Anbieter antwortete mit Sessionlimit. **Routing nachgewiesen, keine erfolgreiche Modellantwort und keine gemessene Kosteneinsparung behauptet.** Vollständiger Stream auf Server `/tmp/v3-router-ack-e2e.ndjson` (temporäre Evidenz).
- Engine-Release unverändert: dortiger router ist noch die alte Version. Änderung gilt für Portal-Chat-Brücke; nicht als Änderung des Evidence-Routers ausgeben.

## Taskstatus
- RED: CANCELLED wurde von `agentState()` als offen gezählt.
- GREEN: exakte Terminalstatusliste DONE/COMPLETE/COMPLETED/CLOSED/CANCELLED/CANCELED/ARCHIVED/FAILED in Store, HQ, CC und Voice.
- BLOCKED und NOT_DONE bleiben offen; abgebrochen wird nicht in DONE umgeschrieben.
- Regressionstest `test_task_states.cjs` bestanden; sechs bestehende Sprach-Regressionsgruppen weiter grün.
- Live-Gegenprobe API vs Command Center: 13 Tasks, **8 offen**, 0 offene Incidents. Vorheriger Filter hätte die 3 CANCELLED-Tasks fälschlich mitgezählt.

## Command Center
- Vorhandene autorisierte `/api/jarvis`-Operation `cmd=usage` wird lesend genutzt; kein neuer Backend-Endpunkt.
- Neue Ledger-Anzeige: Claude 49/100000 Aufrufe, 16296/1000000000 Token im 24-h-Fenster; Helper-Limits 0 als deaktiviert; Cache-Zähler Jobs 13014. Punktuelle Werte, keine historischen Garantien.
- Explizite Unterscheidung zwischen lokalen Caps, Provider-Restkontingent und nicht abgerechneten Listenpreis-Äquivalenten. Echte Router-/Provider-Quoten, GPU/Worker und Logs bleiben unangebunden.
- TDD-Test für Zahlen/Nullgrenzen/fehlende Werte/HTML-Escaping bestanden.
- Browser: exakte Werte gegen Roh-API geprüft; schneller Wechsel HQ/Voice/CC/Musik/Dashboard ohne JavaScript-Fehler.
- Aktueller Live-Bundle-SHA256: `d55dc5c78956b56f00fd405fd6a3042cc5037b124a74232c7f434ca38c008ca0`.
- Raw browser evidence: `cache/browser-use/workspace/local-f9462bd39526705fe9fc29e32b66dfa56eebf769a6337e44241cc225423013c8/ledger-status-verification.json`.

## Restumfang
`V3-RESTAUFTRAG.md` bleibt maßgeblich. Diese Arbeit schließt weder akustische Wakeword-Zuverlässigkeit noch Gateway-Neustart, Worker-Sandbox, Provider-Telemetrie oder Council-Rundenzählung ab. Nicht alle Kriterien sind grün.
