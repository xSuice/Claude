# V3 – Abschluss-Gates, Prüfstand 2026-10-27

## Diese Runde tatsächlich erledigt

### 1. Scharfe Portal-Wiederherstellung
Bestehendes `/opt/ma-home/rollback-cutover.sh` ausgeführt, danach aktuelle `portal.py` automatisch im finally-Block wiederhergestellt. Vorher busy=false und keine aktiven Engine-Jobs geprüft.
Alle sechs Prüfungen bestanden: klassische Startseite, klassisches Auth-Gate, HQ wiederhergestellt, HQ-Auth-Gate, Quellbytes identisch, Bundle abrufbar. Dauer aus Rohdaten: started 1793098015.025771, finished 1793098020.9009376. Aktuelle Quell-SHA256 `2c4389007037c6c2463d888eafffd8685a2319fa6e948447e65ece122e397078`. Aktuelle Sicherung `/opt/ma-home/portal.py.bak-vor-rollback-probe`. Rohbeleg `V3-ROLLBACK-PROBE.json`.
**Damit ist der vorher offene echte Portal-Rollback-Test erledigt. Keine Behauptung über Datenbank-Disaster-Recovery.**

### 2. Bestehende Worker-Steuerung
74 Unit-/Policytests in `Hermes-Engineering-2026-10-17/tools/worker_scheduler` bestanden. Reale read-only Admission: allowed=true, reason=steady, vollständiger Prozessscan. Messpunkt CPU 37,7%, RAM 84,9%, GPU 25%, 46°C, VRAM frei 5009/6144 MB. Kein Modell gestartet.
**Echte Sandbox-Qualifikation scheitert vor Ausführung:** bestehendes `MA-Server/scripts/jarvis/winsandbox.py` kann im Agent-Prozesskontext kein AppContainer-Profil anlegen: HRESULT `0x80070005` (Zugriff verweigert). Keine ungeschützte Alternative, keine Rechteaufweitung. Damit Server→PC-E2E weiterhin NICHT abgenommen. Rohbeleg `V3-SANDBOX-QUALIFICATION.json`.

### 3. MCP und Skills
- Aktives Profil: keine MCP-Server eingerichtet.
- Default-Profil: Dropbox und Canva aktiviert, Hugging Face absichtlich deaktiviert; keine Aktivierung vorgenommen.
- Reale `hermes -p default mcp test dropbox`: verbunden, 27 Tools entdeckt; Canva: verbunden, 49 Tools entdeckt. Kein externer Schreibaufruf.
- Alle 59 aktiven SKILL.md-Metadaten erfasst. Alle 46 Python-Skripte in Skill-Unterordnern per AST ohne Syntaxfehler. Fünf nicht lokal auflösbare Pfadnennungen wurden als Kandidaten, nicht als sichere Defekte erfasst (darunter Beispielskripte und Pfade in einer fremden Quellstruktur).
- **Grenze:** Das beweist keine E2E-Funktion aller 59 Fachworkflows. Solche Tests brauchen konkrete Dokumente/Daten, Dienstzugänge und ggf. separate Schreib-/Kostenfreigaben. Rohbelege `V3-INVENTAR.json`, `V3-SKILL-STATIC-CHECK.json`.

### 4. Router-/Quota-Sicherheitsgate und Messquellen
Bestehender Live-Release: `test_ap1_quota.py` 10/10, `test_ap3_evidence_router.py` 10/10 bestanden. Tests beweisen u.a. Kostenakkumulation, Quotenlimit, unbekannte Provider fail-closed, kritische Aufgaben bei leerer Quote fail-closed, Entscheidungslogging. Bestehender Planner bleibt advisory: terminal/file/code_execution/delegation deaktiviert (tools list geprüft).
Read-only aggregierte gespeicherte Sessionzähler von 18 Spezialisten: 521 Sessions, 16713 gespeicherte API-Aufrufe, 1482 deduplizierte message_agent-Abschlussdatensätze; Cache-Read-Zähler 1692993815, Cache-Write 20554942. **Lifetime-Zähler, keine 24-h-Abrechnung, kein Einsparungsnachweis. DM-Abschlussdatensätze sind keine Council-Runden und kein Zustellbeweis.** Keine Inhalte/Toolargumente exportiert. Rohbeleg `V3-COUNCIL-CACHE-BASELINE.json`.

## Tatsächliche externe Blocker

| Gate | Frischer Befund | Nötiger Schritt |
|---|---|---|
| Gateway-Transportfix aktivieren | Gateway PID 19200 seit 24.10. 09:32; Fix-Datei geändert 27.10. 05:32, also nach Prozessstart | `hermes gateway restart` in einem normalen Terminal außerhalb dieses Agentprozesses; anschließend Langantwort-Gegenprobe. Agent-Selbstneustartsperre nicht umgehen. |
| Akustisches Wakeword | Bisher nicht zuverlässig erkannt; Browser-Diagnose `chrome://version` wird von der Organisation gesperrt | Kein Umgehen der Browserrichtlinie. Realer Mikrofontest auf dem Owner-Browser bzw. genehmigte Testumgebung nötig. Mocktests zählen nicht als Audio-E2E. |
| Execution-Worker | AppContainer-Anlage liefert 0x80070005 vor Prozessstart | Windows-Sandboxfähigkeit/Prozesskontext regulär freigeben bzw. administrativ diagnostizieren; danach denselben Isolationstest wiederholen. Keine unsandboxed Execution. |
| Physischer Druck | CUPS aktiv, keine Queue; konfigurierte IP 192.168.0.198, TCP631 nicht erreichbar | Gerät einschalten/Verbindung prüfen bzw. neue IP bestätigen. Kein Paket-/Treiberwechsel auf Verdacht. |
| Windows aktivieren | Windows Pro, LicenseStatus=5, aktueller Reason 0xC004F034; zuvor 0x803F7001 dokumentiert | Offizielle Aktivierungsproblembehandlung mit eigenem Microsoft-Konto bzw. gültiger Lizenz. Kein Kauf ohne Freigabe, keine Schlüssel hier eingeben. |
| PC-Neustart | Neustart bisher bewusst vertagt, agentseitig hart gesperrt | Owner startet nach Speichern seiner Arbeit selbst neu. Nicht automatisch auslösen. |

Microsoft-Referenz für die rechtmäßigen Aktivierungsoptionen: https://support.microsoft.com/en-US/Windows/activation/get-help-with-windows-activation-errors . Eine fehlende gültige Lizenz ist kein durch Skript legal behebbarer Defekt. Der SPEC-Alternativpfad „Hinderungsgrund dokumentiert“ ist erfüllt, die Maschine ist dadurch NICHT aktiviert.

## Weiterhin offene Entwicklungsarbeit (keine externen Blocker vortäuschen)
- Ein verlässlicher akustischer Wakeword-Pfad in einer geeigneten Testumgebung.
- Council-Rundenzählung mit Themen-/Kausalbezug; die jetzt gefundenen DM-Datensätze sind nur eine Basis.
- Provider-Router-Restquoten, Windows-Telemetrie und secretfreie Logs im Command Center über eng autorisierte bestehende Schnittstellen.
- Kontext-/Caching-Optimierung mit kontrolliertem Vorher/Nachher; aktuelle Lifetime-Baseline ist keine Verbesserung.
- Rollenbezogene Funktionsabnahme der Skills statt bloßer Metadaten-/Syntaxprüfung.
- Server→PC-Auftrag unter qualifizierter Sandbox mit realem Gaming-/Abbruchtest, sobald AppContainer funktioniert.
- Endgültige Gesamtabnahme nach Abschluss dieser Punkte. **Gesamtauftrag noch nicht vollständig fertig.**

## Zusätzlicher Sicherheitsbefund
`ma-home printer-detect` ruft anschließend `host_config(st)` auf. Diese Provisionierung schreibt host.json neu und lässt die später ergänzten `extra_uids`/`extra_gid` weg. Blindes Ausführen würde die funktionierende Portal→Host-Agent-Verbindung wieder beschädigen. Deshalb wurde nur Netzwerk/CUPS gelesen, nicht neu provisioniert. Vor Einrichtung ist die Erhaltung dieser Freigabe zu sichern.


## Nachtrag: Council-Dialogketten (read-only, nur Metadaten)
Quelle: `scripts/verification-v3/council_chains.py` über die persistierten Sessions der 18 Profile; nur Absender, Ziel und Zeitstempel von `message_agent`-Aufrufen, kein Nachrichtentext. Eine Kette = aufeinanderfolgende DMs desselben Agentenpaars mit höchstens 30 min Abstand. Rohdaten: `V3-COUNCIL-CHAINS.json`.

| Zeitraum | Ketten | DMs | längste Kette | Ketten > 6 DMs | > 12 DMs |
|---|---|---|---|---|---|
| bis 25.10. | 227 | 1347 | 77 | 50 | 27 |
| ab 26.10. (A4-1 Toolsperre + A4-2 Debattenbudget) | 43 | 119 | 17 | 2 | 1 |

Gesamt 1466 DM-Aufrufe in 270 Ketten, Median 2. Spitze am 24.10. mit 644 DMs. Das ist eine zeitliche Korrelation, kein Kausalitätsbeweis. Es sind gesendete Aufrufe, kein Zustellbeweis; Themen und Ergebnisqualität sind nicht erfasst. Das Debattenbudget (3 Runden, rund 6 DMs) ist nur per SOUL.md festgelegt, technisch nicht erzwungen: seit 26.10. überschreiten noch 2 Ketten es, die längste hat 17 DMs. Damit ist die Messquelle für Council-Runden vorhanden (r3 teilweise), die Themenzuordnung bleibt offen.
