# V3 – Restauftrag und verifizierter Stand

Grundlage: SPEC-MASTER-V3-20261026.md. Dieser Arbeitsstand ersetzt nicht die SPEC. Alte Aussagen „alles umgesetzt“/„alle 21 Bereiche“ waren zu weitgehend.

## Abgeschlossen und belegt
- A0–A6: GO-Gate mit dokumentierten Einzelbelegen. Spezialistentests 18/18; erneute qa/core-Proben unabhängig geprüft.
- Portal produktiv auf `/`, klassisch auf `/classic/`, Backup/Rollback vorhanden.
- Native Navigation: **20 eindeutige Navigationseinträge einschließlich Design-System**, nicht 21. Design-System liegt als eigener sichtbarer statischer Abschnitt außerhalb `#view`.
- Preview-Rechte repariert: Job 69d753b2-ace7-49bb-94db-eb4dca729f7c, HTTP 200 / JPEG, Testreste entfernt.
- Upload, Vault schreiben/umbenennen/löschen, Musik-Wiedergabe, Dienst-Neustart, UI-Auftrag und Kill-Schalter real geprüft (Details A7/STATE).
- Git-Sync repariert; Portal-Quellen versioniert. Task-Altlasten P1/P3/P5 nach Owner-Entscheid CANCELLED; keine gefälschten DONEs.
- Heartbeats: melden Gateway-Erreichbarkeit, nicht tatsächliche Arbeit. Mention-Kette real geprüft.
- **Portal-Optimierung neu gemessen:** kalter Browsercache, SSH-Tunnel/Header-Proxy, jeweils fünf gewertete Läufe nach Aufwärmlauf. Vorher Median Load 296 ms / DCL 290,8 ms / 24 Ressourcen / 12 JS / 344.194 Ressourcen-Bytes. Nachher Load 95,7 ms / DCL 92,1 ms / 13 Ressourcen / 1 JS / 278.363 Bytes. Nur dieser Testpfad, keine Aussage über Internet-Latenz oder KI-Tokenersparnis.
- Bundle mit esbuild 0.25.12 lokal erstellt; Server benötigt kein npm. Originalmodule bleiben vorhanden. Rollback: `index.html.bak-vor-bundle` wieder als index.html installieren.
- Asynchrone Renderfehler bei schnellem Verlassen von CC und Musik behoben. Browser-Stresstest: 3 Runden CC/Vault/Wissen/Musik/Dashboard im 120-ms-Takt, 0 JS-Fehler nach Fix. Neun zentrale mobile Ansichten ohne horizontalen Overflow.

## Noch nicht abgenommen – konkrete Restarbeit
1. **Akustisches Wakeword:** keine verlässliche Erkennung von „Jarvis“ im echten Test; Einzelmodus erkennt die Zeitfrage. Keine Aufweichung der Wakeword-Pflicht. Sechs Mock-Regressionsgruppen bestanden, aber kein Ersatz für Audio-E2E.
2. **Gateway-Transportfix:** liegt im Code, Aktivierung benötigt Gateway-Neustart. Agent-Wächter blockiert Selbstneustart; diese Sperre nicht umgehen. Danach Langantwort-Rückkanal unabhängig prüfen.
3. **Council-Runden:** `council_decisions=0` ist kein Beleg für null tatsächliche Runden. Messquelle/korrelierte Ausführungen fehlen; Kriterium nicht grün.
4. **Command Center:** Modelle/Router-Quoten, GPU/Worker-Telemetrie und Logs weiter ausdrücklich „nicht angebunden“. Sichere, bestehende Quellen inventarisieren; keine erfundenen Daten.
5. **KI-Effizienz:** Portal-Bundle belegt keine Modell-/Tokenoptimierung. Router-Klassifikationsschwächen sowie Prompt-/Kontextbudgets und Cache-Verbrauch separat messen und verbessern. Keine rückwirkend erfundene Vorher-Baseline.
6. **Skills/MCP-Inventar:** V3-Delta aus Phase 1 noch offen; nicht durch Spezialistentests abgedeckt.
7. **Windows-Execution-Worker:** nicht durch Receiver/Heartbeats ersetzt. Gaming-Vorrang, Sandbox und Ressourcenlimits mit echtem PC-Auftrag nachweisen. Bisheriger Owner-Entscheid: ruhend (Option C); allgemeines „alles“ nicht als Erlaubnis für Rechteaufweitung/fehlende Schutzmechanismen behandeln.
8. **Windows-Neustart/Aktivierung:** Neustart bisher bewusst später, durch Agent hart gesperrt. Aktivierung ohne gültige Lizenz nicht legal automatisierbar; SPEC erlaubt stattdessen dokumentierten Hinderungsgrund. Keine Käufe und keine Lizenzmanipulation.
9. **Drucker:** `printer_ready=false`; Preview funktioniert, physischer Druck nicht eingerichtet/abgenommen. Vor Druckauftrag Papierverbrauch und reales Gerät berücksichtigen.
10. **Rollback-Probe und Schlussabnahme:** vorhandenes Skript allein beweist keinen scharfen Wiederanlauf. Kontrollierte Probe mit Rückkehr zum aktuellen Stand und vollständiger Kriterienzählung steht aus.

## Reproduzierbare Artefakte
- Browser-Rohmessungen: `profiles/kimi-supervisor/cache/browser-use/workspace/local-f9462bd39526705fe9fc29e32b66dfa56eebf769a6337e44241cc225423013c8/bundle-benchmark.json`.
- Browser-Navigationsmessungen: dort `bundle-navigation.json`, `bundle-mobile.json` (historische Zwischenprüfung; finaler Lifecycle-Stresstest in bundle-benchmark.json).
- Quellen lokal: `profiles/kimi-supervisor/cache/scratch/staging/`; Server: `/opt/ma-home/web/staging/`.
- Sprachtests: `test_voice_regression.cjs` (aus hq-Verzeichnis aufrufen).

**Abschlussstatus: nicht vollständig fertig.** Keine neue pauschale Grün-Zählung, solange die Restpunkte nicht einzeln belegt sind.
