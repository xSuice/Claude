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


## Nachtrag: Gateway-Transportfix aktiv
Gateway-Prozess seit 27.10. 12:31 (PID 32052), jünger als `run_notifications.py` (05:32). Gegenprobe mit einzeiligem 3,6-kB-JSON: Abschlussmeldung enthielt den Tail inkl. Endmarke statt „showing last 0 chars“. Das Gate „Transportfix aktiv“ gilt damit als erfüllt.


## Nachtrag: Skill-Funktionsprüfung (isolierte Test-Umgebung, 27.10.)
Neue venv unter dem Scratch-Ordner (Hermes-Umgebung unverändert); installiert: python-docx, openpyxl, python-pptx, pypdf, reportlab, pdfplumber, pypdfium2, pytest. Die in den Skills mitgelieferten End-to-End-Tests wurden ausgeführt:

| Skill | Ergebnis |
|---|---|
| docx | 29 bestanden |
| xlsx | 11 bestanden, 1 übersprungen (Grund nicht untersucht) |
| powerpoint | 21 bestanden |
| pdf | 21 bestanden (erster Lauf 1 Fehler: `pdfplumber` fehlte, Exit 2 = fehlende Abhängigkeit; nach Installation grün) |
| maps | Live-Abruf: Geocoding „Brandenburger Tor, Berlin“ und Reverse-Geocoding liefern plausible OSM-Daten |

Nur diese vier Skills haben mitgelieferte Tests; die übrigen rund 54 aktiven Skills sind weiterhin nur per Metadaten/Syntax geprüft. Die vier Dokument-Skills brauchen in der produktiven Hermes-Umgebung die genannten Pakete, sonst schlagen sie mit Exit 2 fehl.

Ein Diagnoseversuch zur AppContainer-Anlage (0x80070005) blieb ohne Freigabe-Antwort im Genehmigungs-Timeout und wurde nicht ausgeführt und nicht umgangen.


## Nachtrag: AppContainer-Diagnose (Worker-Sandbox)
Direkter Aufruf `CreateAppContainerProfile` mit frischem Namen (Testprofil, bei Erfolg sofort gelöscht): **HRESULT 0x80070005 (Zugriff verweigert) reproduziert**, unabhängig vom Sandbox-Code. Kontext: normaler Benutzer (nicht Administrator), mittlere Integrität (S-1-16-8192), Prozess nicht in einem Job-Objekt, `%LOCALAPPDATA%\Packages` vorhanden, Dienst AppIDSvc läuft, AppXSvc gestoppt (bedarfsgesteuert), auf dem Gerät besteht eine MDM-/Appx-Richtlinie (Registrierungsschlüssel `Policies\Microsoft\Windows\Appx` vorhanden). Eine Ursache ist damit **nicht bewiesen**; die Anlage wird auf dieser Maschine verweigert. Weitere Diagnose (z. B. Process Monitor, Richtlinien ändern) bräuchte Administratorrechte bzw. ändert Systemrichtlinien und wurde nicht versucht. Folge: kein Worker-Start, keine unsandboxed Alternative.


## Nachtrag: Router-Ende-zu-Ende und Modellkosten (27.10., Sessionlimit des Anbieters wieder aufgehoben)
Echte Aufrufe über `POST /api/claude` (Modus lesen, Ordner notizen, Prompt „Antworte nur mit OK.“), je Aufruf `bridge_model` und `result` aus dem Stream gelesen. Skript: `scripts/verification-v3/router_probe.py`.

| Aufruf | bridge_model | Antwort | Kosten (Listenpreis-Äquivalent, laut CLI) | Cache |
|---|---|---|---|---|
| ohne Modellangabe (Router) | haiku | OK | 0,00032 USD | read 32.168, create 0 |
| haiku erzwungen | haiku | OK | 0,00032 USD | read 32.168, create 0 |
| sonnet erzwungen, kalter Cache | sonnet | OK | 0,0858 USD | create 21.175, read 10.170 |
| sonnet erzwungen, warmer Cache | sonnet | OK | 0,00318 USD | read 31.345, create 0 |

Ergebnis: Der Router wählt für die Bestätigung tatsächlich Haiku, und die Antwort kommt an (der frühere Befund „nur Auswahl belegt, Antwort blockiert“ ist damit geschlossen). Bei warmem Cache kostet Sonnet für dieselbe Aufgabe rund das Zehnfache von Haiku (0,00318 gegenüber 0,00032 USD); bei kaltem Cache rund das 265-Fache, weil ca. 21.000 Cache-Schreib-Token anfallen. Auffällig: Jeder Aufruf bringt schon ca. 31.000 Token Grundkontext mit (Hooks/Systemkontext des Claude-CLI), selbst für eine Zwei-Wort-Aufgabe. Das ist der größte Hebel für Kontextkosten, wurde aber nicht verändert. Die USD-Werte sind Listenpreis-Äquivalente der CLI, keine Rechnung. Stichprobe von 4 Aufrufen plus 1 Sonnet-Warmlauf, keine statistische Aussage über reale Aufgabenmischungen.

Ursachenprüfung zum Grundkontext (nur lesend): Die Bridge startet Lesen/Notizen bereits mit `--strict-mcp-config` (`ma-claude-bridge.py`, Kommentar „spart die lange Werkzeugliste“); `~/.claude/CLAUDE.md` hat nur 4,8 kB, das Vault-CLAUDE.md 2,6 kB, `settings.json` definiert zwei Hooks, keine MCP-Server und keine Plugins. Die verbleibenden ca. 31.000 Token sind damit überwiegend der eigene Grundkontext des Claude-CLI. Ein weiterer, bereits genutzter Hebel (Cache-Read statt Cache-Create) wirkt: warme Aufrufe kosten ein Hundertstel der kalten. Kein weiterer sicherer Hebel ohne Eingriff in die Bridge gefunden; keine Änderung vorgenommen.


## Nachtrag: Umsetzung genehmigter Vorschläge S-01, E-04, U-04 (Owner: „ja mache alles“)
- **S-01 erledigt:** `host_config()` in `/opt/ma-home/manage.py` übernimmt jetzt vorhandene `extra_uids`/`extra_gid` aus `host.json` (Marker `KEEP-EXTRA-UIDS`, Backup `manage.py.bak-vor-keepextra-20261027`). Verhalten vor dem Schreiben isoliert getestet: vorhanden → erhalten, Datei fehlt → keine Felder, Datei defekt → keine Felder, fremde Zusatzfelder werden nicht übernommen. Produktive `host.json` unverändert (`extra_uids=[1000]`). `printer-detect` selbst wurde nicht ausgeführt. Nicht abgedeckt: `assets()` (nur bei Erstinstallation) würde `agent.py` aus dem eingebetteten Original überschreiben und meine Agent-Patches (extra_uid, Preview-Gruppe) entfernen — nur relevant bei Neuinstallation.
- **E-04 erledigt und Ende-zu-Ende belegt:** `kimi-supervisor` im `HERMES_ROSTER` (Live-Datei `/opt/ma-home/chat_bus_backend.py` und Kopie im Home, Backups `…bak-vor-kimiroster-20261027`). Portal einmal neu gestartet (vorher busy=False, keine aktiven Jobs), healthz 200. Test-Mention in `#test`: API antwortet `mentions` und `routed_to` = `kimi-supervisor`, Mention-Receiver-Log `delivered target=kimi-supervisor`. Das ist ein Test-Auftrag („nur EMPFANGEN antworten“) an mich selbst.
- **U-04 anders gelöst, weil die Hermes-Umgebung kein pip hat:** Die Hermes-Umgebungen wurden nicht verändert. Stattdessen dauerhafte eigene Umgebung `%LOCALAPPDATA%\hermes\skill-env` (Lock-Datei `requirements-lock.txt`, 23 Pakete). Die vier Skill-Testläufe dort: docx 29, xlsx 11 (+1 übersprungen), powerpoint 21, pdf 21 bestanden. Skill-Skripte müssen mit `skill-env\Scripts\python.exe` gestartet werden, nicht mit dem Terminal-`python`.


## Nachtrag: nexum-Schlüssel – Abgleich PC ↔ Server (Hinweis des Owners, 27.10.)
Nur SHA-256-Fingerabdrücke und Längen, Werte nie ausgegeben (`scripts/verification-v3/nexum_fp.py`, `nexum_scan.py`).
- **PC und Server haben denselben Schlüssel:** `~/.config/ma-jarvis/keys/nexum.key` (59 Zeichen, Fingerabdruck `b2444a7dcd2e`) stimmt mit `NEXUM_API_KEY` in allen **18** Profil-`.env`-Dateien überein (jarvis-*; `kimi-supervisor` und `hermes` haben keine eigene Zeile). Die Annahme „gleich, weil es funktioniert“ ist belegt.
- **Streuung:** Der Schlüssel liegt damit an 19 Stellen (18 PC-Profile + Server). In 806 geprüften Dateien (`.env`, `config.yaml`, Request-Dumps, Logs, Prozessergebnisse) taucht er **nur in den 18 `.env`-Dateien** auf — nicht in Dumps, Logs oder Konfigurationen.
- **Folge für S-02 (Rotation):** Neuer Schlüssel muss in alle 19 Stellen; sinnvoll per Skript mit Fingerabdruck-Gegenprobe. Alte Gültigkeit erst nach erfolgreicher Prüfung widerrufen. Rotation selbst braucht dein Anbieterkonto (nicht durchgeführt).
- **Nebenbefund:** In `profiles/kimi-supervisor/config.yaml` und `profiles/jarvis-cloud-dev/config.yaml` steht je ein **literaler** `api_key` (72 bzw. 6 Zeichen), obwohl Secrets laut Hermes-Regel in `.env` gehören. Es ist nicht der nexum-Schlüssel (kein Treffer in `config.yaml`). Nicht verändert, Zweck nicht untersucht.

## Nachtrag: Barrierefreiheit (U-05, automatisiert mit axe-core 4.10.2, WCAG 2.0/2.1/2.2 A+AA)
Vorher (8 Ansichten): 58 Knoten Kontrastfehler (`--text-faint` #5A636F auf #151920 = 2,89:1, Soll 4,5:1) und 3 scrollbare Bereiche ohne Tastaturzugang (Chatverlauf, 2 Tabellen im Command Center). Behoben: `--text-faint` → #858E9B; `tabindex="0"`, `role`, `aria-label` auf den Bereichen. Nachher (16 Ansichten): **1 verbleibender Knoten** (Ansicht Musik: Schaltfläche `data-r=""` unterschreitet die Mindestzielgröße), 0 sonst. Bundle `a5b260be…8341` deployt, Server = lokal (Hash gleich); Backups `…bak-vor-a11y`. Grenze: axe findet nur den automatisch prüfbaren Teil (typisch ein Drittel der WCAG-Kriterien). Tastaturbedienung im Ganzen, Screenreader und reduzierte Bewegung wurden nicht manuell geprüft.

## Nachtrag: U-02 (Router-Restquoten)
Die vermutete Datenquelle `council_decisions` (PG) ist **leer (0 Zeilen)**. Es werden dort keine Routing-Entscheidungen protokolliert, daher gibt es nichts anzubinden. Das Feld bleibt „nicht angebunden“.


## Nachtrag: E-03 als Warnanzeige (statt Erzwingung) und Restfund Barrierefreiheit
- **Council-Dialoge im Command Center (Warnung, keine Sperre):** Der PC-Reporter zählt alle 10 min (gecached) aus den Sitzungsdatenbanken der jarvis-Profile `message_agent`-Aufrufe der letzten 24 h (nur Absender, Ziel, Zeit; kein Nachrichtentext) und schickt `{dms, chains, longest, over_6}` mit der Telemetrie an den Server (Schema-Erweiterung `council`, TDD: 14 Tests grün, auch auf dem Server). Anzeige im CC: aktuell 34 DMs, 11 Ketten, längste 6, 0 über Budget (> 6). Technische Erzwingung wurde bewusst **nicht** gebaut (Eingriff in den Hermes-`message_agent`-Pfad würde bei Hermes-Updates verloren gehen und ist Kernänderung). Portal einmal neu gestartet (vorher busy=False, keine aktiven Jobs); Reporter ersetzt (gezielt nur die zwei pythonw-Prozesse, Backup `pc_telemetry.py.bak-vor-council-20261027`).
- **Router-Feld:** Text im CC korrigiert: Entscheidungstabelle leer, keine Quelle.
- **Barrierefreiheit:** letzter axe-Knoten (Musik-Breadcrumb unter 24×24 px) per CSS behoben. Nachmessung cc/musik/dashboard/chat: 0 Verstöße, kein horizontaler Überlauf. Bundle `d05672dd…6d44`, Server = lokal, Backups `…bak-vor-council`.
