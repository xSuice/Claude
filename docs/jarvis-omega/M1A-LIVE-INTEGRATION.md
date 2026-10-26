# M1a – Live-Basis und Integrationsgrenzen

Stand: 2026-10-18, Europe/Berlin. **WIP vor Freeze; kein vollständiges M1a-PASS.** Diese Datei aktualisiert die älteren M1A-IST/ADR/RESULTS-Snapshots.

## Basis

- Branch: `dev/hermes-m1a-live-20261018`.
- Basis: GitHub `server-live`, Commit `70a6fd0242c349bb798c4545ff58e5c4f2843ce3`.
- Aktives Release: `20261015-140650-f57d32f`, vom vorhandenen `current` referenziert.
- 104 zugeordnete Codedateien dieses Releases stimmen bytegenau mit dieser Basis überein. Gegen die frühere main-Basis unterschieden sich 8 davon. Keine Aussage über nicht verglichene Dateien.
- Der Server-Checkout hat 7 vorhandene getrackte Änderungen. Weder diese noch main/server-live oder das aktive Release wurden geändert.
- Öffentliche M1a-Dateien stammen aus dem lokalen Checkpoint `e632b0aa6e78065c3742ad0a7253c3d9470ba0d6`. Alle 130 Referenzdateien sind byteidentisch übernommen.

## Neue lokale Korrektur

Der Hostadapter verwirft boolesche, negative oder sonst nicht echt ganzzahlige Beobachtungsschritte. RED wurde vor der Implementierung für sechs fehlerhafte Werte beobachtet, danach GREEN. Nur `tests/m1/host_adapter.py` und der zugehörige Test ändern Verhalten. Die Referenzimplementierung bleibt unangetastet.

## Tatsächliche Prüfungen

- 5 öffentliche Adaptertests und 31 ausgewählte Referenztests auf Windows grün.
- 20 ausgewählte bestehende V16-Tests gegen den gepinnten Release-Code unter Linux in einem kurzlebigen, netzisolierten RAM-Dateisystem grün; 0 übersprungen. Nur synthetische Modellantworten, kein produktiver DB-Zugriff.
- Separater öffentlicher Minimal-Bubblewrap-Probe: 13/13 Bedingungen erfüllt. Dieser kleine Probe ist keine vollständige V16-/M1-Sandbox-Zertifizierung.
- Erster Linux-Testversuch scheiterte an Thread-/Speicherfehlern unter künstlicher Adressraumbegrenzung; Bericht erhalten. Nur `MALLOC_ARENA_MAX=1` im Testprozess ergänzt, nicht die 384-MiB-Grenze oder Tests geändert. Endlauf 20/20, stderr leer.
- 4 Freeze-/HMAC-Referenztests bewusst ausgeschlossen. Die früheren 500 Dummy-Audits sind historische, öffentliche Fixture-Evidenz, keine neu ausgeführten Modell- oder Produktionsprüfungen.

Laufbelege und reproduzierbare Diagnoseprogramme liegen im separaten Workspace `Hermes-Engineering-2026-10-17` unter `reports/` und `tools/`. Gesamtbericht: `reports/JARVIS-INTEGRATION-2026-10-18.md`.

## Reviews und nicht erledigte Arbeit

Ein frischer Review-Kontext hat ausschließlich den kleinen öffentlichen Adapter-Diff statisch geprüft: PASS ohne Sicherheits- oder Logikbefunde; drei nicht blockierende Vorschläge zu ergänzender Testabdeckung sind im externen `PUBLIC_DIFF_REVIEW.json` erhalten. Der Reviewer führte selbst keine Tests aus. Der Auftrag verlangte das geerbte Elternmodell/-provider; die konkrete Modellkennung wurde im Ergebnis nicht ausgewiesen. Dies ist ausdrücklich keine unabhängige andere Modellfamilienprüfung. Die Different-Family-M1a-Abnahme bleibt offen.

Nicht abgeschlossen: vollständige faire reale D-Baseline, D-Recheck-/V16-Laufzeitintegration, vollständige Prozess-/Recovery-Prüfung, unabhängiger anderer Modellfamilien-Review. Die Modell-/Toolworker sind durch diesen Serverzugang nicht automatisch qualifiziert.

**Kein Freeze, private Evaluierung, M1b, Multi-Worker/E1–E5, Git-Push oder Deployment.** Kein neuer produktiver Controller, keine zusätzlichen bezahlten Provider. Budget EUR 0 bleibt bestehen.
