# MA-HOME JARVIS — Deepsearch und Architekturabgleich

**Prüfstand: 27.10.2026.** Entscheidungsunterlage zum vollständigen Prüf-, Recherche- und Entwicklungsauftrag. Keine Systemabnahme und kein Bericht über einen fertig implementierten Sprachassistenten.

## 1. Methode und Evidenzgrenzen

Diese Recherche umfasst Primärdokumentation, Referenzimplementierungen, Lizenztexte und separat abgefragte GitHub-Projektmetadaten. Recherchesuchläufe stehen in `DEEPSEARCH-QUERIES.json`; Dokumentauszüge und Metadaten in `deepsearch-evidence/`; Quellenidentitäten in `DEEPSEARCH-SOURCES-LEDGER.json`. Umfang und fehlgeschlagene Abrufe werden zusätzlich im maschinellen Manifest festgehalten. Längere Dokumente liegen teilweise als Kopf-/Endauszüge mit Verweis auf den vollständigen Werkzeug-Cache vor; nicht gelesene Zwischenabschnitte sind keine Evidenz.

**Unterscheidung:**
- **Dokumentiert:** Ein Hersteller/Projekt beschreibt eine Eigenschaft. Das beweist nicht ihre Funktion im MA-HOME-Bestand.
- **Gemessen:** Eigene Tests/Dateiprüfungen mit benanntem Umfang.
- **Empfohlen:** Eigene Architekturentscheidung unter den Ressourcen- und Kostenregeln des Owners.
- **Offen:** Konten, Geräte, Akustik oder Ende-zu-Ende-Ketten fehlen. Das wird nicht durch positive Projektbeschreibungen ersetzt.

Es wurden keine neuen SaaS-Abos abgeschlossen, keine Pay-as-you-go-Dienste aktiviert und keine neuen Frameworks produktiv installiert. Die Recherche ist kein Penetrationstest. Repository-Aktivität ist ein Wartungsindikator, keine Sicherheits- oder Qualitätsgarantie.

## 2. Wichtigste Schlussfolgerungen

1. **Das Sprachproblem ist nicht durch eine freundlichere Promptzeile gelöst.** Im geprüften Portalcode besteht der Wakeword-Pfad aus Browser-Spracherkennung plus Text-RegEx. Ein akustischer Wakeword-Detektor ist dort nicht eingebunden. Nach einer Antwort fehlte ein Anschlussfenster; breite Stichwort-Intents konnten ein Gespräch in eine starre Statusausgabe umleiten. Die Browserstimme bleibt außerdem von der lokalen Piper-Stimme des Hermes-Profils getrennt. Das sind eigene Codebefunde, keine Aussagen aus einer Produktseite.
2. **Die passende Referenz ist eine Pipeline, nicht ein zweiter JARVIS.** Home Assistant trennt Wakeword, Transkription, Gesprächsagent und Sprachausgabe und führt über `conversation_id` ein bestehendes Gespräch fort. Diese Trennung passt zum Auftrag; eine vollständige Umstellung auf Home Assistant ist dafür nicht erforderlich.[1]
3. **„Menschlicher“ braucht funktionierende Sprecherwechsel.** LiveKit und Pipecat behandeln Gesprächsende, Pausen, VAD und Unterbrechungen als eigene Funktionen. Eine Stimme mit anderer Tonhöhe oder eine andere Satzvorlage ersetzt diese Mechanik nicht.[2][13]
4. **Kostenlose Wakeword-Software ist nicht automatisch frei lizenzierte Modellnutzung.** openWakeWord-Code ist Apache-2.0; die mitgelieferten Modelle stehen unter CC BY-NC-SA 4.0. Die dokumentierten Fertigmodelle sind englischsprachig, darunter „hey jarvis“.[3] Ein verlässlich erkanntes deutsches „Jarvis“ auf dem eigenen Mikrofon darf daraus nicht abgeleitet werden.[40]
5. **Der Bestand sollte verbessert, nicht durch Temporal, LangGraph, Open WebUI, mem0 und LiveKit gleichzeitig ersetzt werden.** Deren Mechaniken sind nützliche Vorlagen; zusätzliche Plattformen würden aber Integrations-, Berechtigungs- und Betriebsgrenzen vervielfachen. Diese Empfehlung ist eine eigene Abwägung für den vorhandenen kleinen Master.

## 3. Soll-Ist-Abgleich zum gesamten Auftrag

| Auftragsbereich | Nachgewiesener/berichteter Bestand | Fehlende belastbare Abnahme | Konsequenz |
|---|---|---|---|
| Zielarchitektur und Rollen | Portal, Engine, Hermes und Spezialisten vorhanden; einzelne Verbindungen historisch E2E geprüft | Ein vollständiger repräsentativer Auftrag über alle erforderlichen Stationen, inklusive fachlicher QA und Wissenstransfer | Gesamt-GO bleibt offen |
| Auftragsdauerhaftigkeit | Bestehende SQLite-/Task-Strukturen, Job-IDs, Status und Events | Feldabdeckung von Originalauftrag bis Budget, Kriterien, Run-ID und Checkpoints systematisch gegen Schema prüfen | DR-03 |
| Recovery | Watchdog und vorhandene Recoverylogik; ältere Testbelege | Nachweis je Laufzeitadapter, dass Resume/Start tatsächlich ausgeführt wird, nicht nur eine Nachricht entsteht | DR-03/DR-05 |
| Council-Grenzen | Toolsetbeschränkungen historisch dokumentiert | Vollständige technische Rechteprüfung aller Ein-/Ausgangswege und technisch erzwungenes Debattenbudget | DR-05 |
| Router | Eigener Evidence-Router, Limits und historische Aufrufbelege | Aktuelle Tests unter Ausfall, Budgetende und fehlender Providerquote | DR-06 |
| Memory/Obsidian | Bestehende Speicher und Sync vorgesehen/vorhanden | Provenienz, Konflikte, Ablaufdaten, Löschweitergabe und fachlich richtige Retrievalantworten | DR-07 |
| Capability Registry | Skills/Plugins/MCP vorhanden | Statische Discovery ist keine erfolgreiche Nutzung; viele Konten/Workflows ungeprüft | DR-05/DR-07 |
| Designsystem | Tokens, Shell und Arc-Theme vorhanden | Konsistenz aller Zustände, Dialoge, Freigaben und Fremd-Embeds | DR-04 |
| Mobile | Frühere Emulationsmatrix, einzelne Touch-/Keyboardfixes | APK nicht untersucht, echte Tastatur/Streaming/Uploads/Screenreader nicht vollständig geprüft | APK zurückgestellt; DR-04 bleibt offen |
| Agentenwelt | Bestehende Canvas-Ansicht und Store | Ereigniszuordnung, stale/idle-Semantik und behauptete Aktivität durchgehend prüfen | Keine erfundenen Animationen |
| Wakeword | Textvergleich nach Browser-STT | Akustische Erkennungsrate, Fehlaktivierungen, Gerätestabilität und Echo | DR-01 |
| Gespräch | Bestehender Chatpfad; lokale Statusantworten | Mehrere aufeinander bezogene Sprachzüge und natürliche Unterbrechungen | DR-02 |
| Stimme | Piper-/Edge-Hördateien früher erzeugt; Browser-TTS separat | Einheitliche Portalstimme, drei belastbare Kandidaten, Englisch und echter Hörvergleich | DR-02 |
| Signal | Kontoverknüpfung/Textzustellung bestätigt; Audio und lokales STT technisch getestet | Vollständiger eingehender Text-/Audioturn mit aktiviertem Zusatzadapter | Nicht durch ausgehenden Test ersetzt |
| Worker/Hardware | Scheduler-Prüfungen; Drucker zuletzt unerreichbar | Windows-AppContainer blockiert; kein ungeschützter Ersatz zulässig | Owner-/Geräteblocker bleibt |
| Kreativ/Modding/Smart Home | Nutzungsmöglichkeiten vorhanden bzw. vorgeschlagen | Konkrete autorisierte Endabläufe mit Daten, Lizenzen und Akzeptanztests | DR-08 |
| Supervisorbetrieb | Manuelle Reviews möglich; Dienste übernehmen Überwachung | Getesteter Trigger/Runner, Budget, Umfang und Fehlerverhalten für automatische Reviews | Keine Daueraktivität behaupten |

Die Tabelle ist ein Prüfauftrag und Evidenzabgleich, keine Behauptung, alle genannten Bestandsfunktionen heute neu getestet zu haben.

## 4. Sprache: Vergleich konkreter Referenzansätze

### 4.1 Bestehende Browser-Lösung

MDN kennzeichnet `SpeechRecognition` als eingeschränkt verfügbar; bei einigen Browsern, etwa Chrome, erfolgt die Erkennung über einen Serverdienst und funktioniert dann nicht offline.[4] Daher ist die bloße JavaScript-Existenzprüfung kein Beleg für zuverlässigen Zugriff in Brave, Android-WebViews oder der nicht untersuchten APK. Android-Appberechtigung, WebView-Freigabe, Aufnahme und Erkennungsdienst sind getrennte Grenzen.

**Eigener Codebefund:** Das bestehende Portal behandelt `service-not-allowed` und `not-allowed` identisch als verweigerten Mikrofonzugriff. Eine Diagnose muss diese Fälle auseinanderhalten. Eine Änderung der allgemeinen Sicherheitsheader ohne Befund für die eingeloggte Seite wäre nicht gerechtfertigt.

**Entscheidung:** Browser-STT als begrenzte vorhandene Option behalten, aber nicht als universell verfügbares Wakeword-System verkaufen. Sichtbar anzeigen, ob nur der Browserdienst oder ein getesteter lokaler Audiopfad verfügbar ist.

### 4.2 openWakeWord

**Übertragbar:** Audio-basierte Erkennung, VAD-Unterstützung, an der Umgebung gemessene Schwellwerte, optional ein nutzerspezifischer Verifier. Die README beschreibt 16-kHz-/16-bit-Audio und Frames als Vielfache von 80 ms sowie ein Browser→WebSocket→Python-Beispiel; ein fertiger vollständiger JavaScript-Browserport wird dort ausdrücklich nicht angeboten.[40]

**Grenzen:** Fertigmodelle englisch; „hey jarvis“ ist nicht gleich „Jarvis“. Modelllizenz nichtkommerziell. Herstellerbeispiele für Fehlaktivierungs-/Fehlablehnungsraten sind keine eigenen Akustikmessungen. Das Repository ist nicht archiviert; der abgefragte letzte Push lag am 30.12.2025, also deutlich vor mehreren anderen geprüften Projekten.[25]

**Kosten/Ressourcen:** Keine Anbieter-API für lokale Inferenz erforderlich. Eigenes CPU-, Audio-Transport- und Wartungsbudget; auf diesem Celeron ist noch keine Dauerlastmessung erfolgt. Kein kostenloses Genauigkeitsversprechen.

### 4.3 Home Assistant Assist

**Übertragbar:** Die vier Pipeline-Stufen, explizite Zustandsereignisse, Gesprächs-ID, Trennung von Satellit und Agent, Audioverbesserungen sowie geräteseitige VAD statt wahllosem Dauerstreaming.[1]

**Eignung:** Sehr gute Architekturvorlage, weil Home Assistant bereits zum Bestand gehört. Nicht automatisch eine Freigabe zum Steuern des Hauses. Sprachdialog muss weiterhin dieselben Autorisierungen wie Texteingaben verwenden.

### 4.4 LiveKit vs. Pipecat

LiveKit dokumentiert mehrere Strategien zum Sprecherwechsel, Endpointing und Unterbrechungen.[2]

Pipecat beschreibt den Audioeingang und dessen Zusammenspiel mit Transkription und Turn-Erkennung.[13]

Die Framework-Repositories sind im Prüfstand nicht archiviert und zeigen aktuelle Pushes; Lizenzen Apache-2.0 beziehungsweise BSD-2-Clause.[28][29]

| Entscheidungskriterium | LiveKit | Pipecat | Empfehlung für MA-HOME |
|---|---|---|---|
| Primärer Nutzen | Echtzeit-Sitzungen/Transport plus Agentenabläufe | Zusammensetzbare Audio-Pipeline/Turn-Mechanik | Zuerst Konzepte übernehmen |
| Neue Infrastruktur | Zusätzliche Integration und Betriebsfläche | Zusätzlicher Audio-Prozess und Integrationen | Noch nicht beide installieren |
| Kosten | Open-Source-Kern ist nicht gleich kostenloser Cloud-/Modellbetrieb | Gleiches gilt für verwendete Anbieter | Keine Cloudkosten ohne Freigabe |
| Master-Ressourcen | Eigener Messbedarf | Eigener Messbedarf | Lastprobe vor Produktiventscheidung |
| Abnahmerisiko | Frameworkdemo beweist nicht Browser/APK | Frameworkdemo beweist nicht Browser/APK | Echte Zielgeräte bleiben nötig |

**Eigene Entscheidung:** DR-02 zunächst im vorhandenen Sprachpfad umsetzen. Erst wenn gemessene Transport-/Turn-Probleme das nicht tragen, genau einen vertikalen Test mit einem Framework begründen.

### 4.5 Stimme und Persönlichkeit

Piper bietet lokale TTS; das aktuelle OHF-Projekt steht unter GPL-3.0. Die Lizenz einer einzelnen Stimme muss separat geprüft werden: Engine-Lizenz und Model-Card sind nicht austauschbar.[14][26] faster-whisper ist laut abgefragtem Repository MIT-lizenziert und wurde in der isolierten PC-Umgebung bereits für synthetisches deutsches Audio ausgeführt; das beweist keine Mikrofonqualität.[27]

ElevenLabs bietet einen begrenzten Free-Tarif und kostenpflichtige Stufen. Das ist kein unbegrenzter kostenloser Dauerbetrieb, und Kontingente sowie kommerzielle Rechte unterscheiden sich.[39] Deshalb nicht unbemerkt als neue Standardstimme einschalten.

**Hörvergleich noch unvollständig:** Frühere lokale Piper- und Edge-Dateien sind vorhanden. Zwei Qualitäts-/Emotionsvarianten desselben Thorsten-Sprechers erfüllen nicht automatisch den Wunsch nach drei verschiedenen, tatsächlich gehörten Kandidaten. ElevenLabs wurde nicht mit einem eigenen berechtigten Konto getestet. Gutes Englisch ist ebenfalls nicht durch deutsche Testsätze mit englischen Produktnamen belegt.

**Natürlichkeit:** eigene Abnahme entlang von Wortwahl, Intonation, Eigennamen, Satzenden, Pausen, Antwortlänge und Unterbrechungsverhalten. Keine zufälligen Füllwörter, vorgetäuschten Gefühle oder ständigen „Andrew“-Anreden als Ersatz für echte Gesprächsqualität.

## 5. Dauerhafte Aufträge, Recovery und unabhängige Prüfung

LangGraph dokumentiert Checkpoints anhand von Threads sowie unterbrechbare Abläufe; bei Interrupts wird Ausführungszustand gespeichert und später durch passende Eingaben fortgesetzt.[5][6]

Temporal unterscheidet Workflow-Zustand und externe Activities. Activities können erneut ausgeführt werden; Idempotenz muss ausdrücklich gestaltet werden und folgt nicht allein aus einem persistenten Workflow.[7][8]

**Für den Bestand übernehmen, nicht alles migrieren:**
- Vor Ausführung eine unveränderliche Originalanforderung, Task-/Run-ID und Akzeptanzkriterien speichern.
- Zustandsübergänge mit Herkunft und Zeiten führen; Heartbeat, echter Fortschritt und legitime Wartephase unterscheiden.
- Vor externen Aktionen Idempotenzschlüssel reservieren; unklaren Ausgang nicht blind wiederholen.
- Approval an konkrete Aktion/Parameter/Version binden, nicht nur an eine lose Chatnachricht.
- Nach Unterbrechung vom bestätigten Checkpoint fortsetzen; Retryzahl/Backoff/Budget begrenzen.
- Prüfergebnis mit Artefakt/Hash und fachlichen Kriterien führen. Existenz einer Datei oder ein grüner Prozessstatus allein ist kein fachliches DONE.

systemd dokumentiert Restart- und Watchdogmechaniken. Für WatchdogSec braucht der betreffende Dienst auch das erwartete Watchdog-Protokoll; eine beliebige Unit-Option allein macht einen Prozess nicht selbstüberwacht.[21] Für JARVIS ist die Dienstaufsicht von der inhaltlichen Stagnationsprüfung getrennt zu testen.

**Kosten/Ressourcenentscheidung:** LangGraph MIT und Temporal MIT laut Repository-Metadaten.[30][31] Dennoch kein kostenloser Betriebsaufwand. Auf dem kleinen Master zuerst die existierende Task-/SQLite-Engine prüfen und gezielt ergänzen. Aufwand für Migration, Datenkonversion und Rollback würde weit über den Nutzen einer bloßen Demonstration hinausgehen.

## 6. Design, Chat, mobile Bedienung und Agentenwelt

### Gemeinsame Komponenten statt Fremdportal einbauen

shadcn/ui zeigt semantische CSS-Variablen als gemeinsame Gestaltungsbasis, einschließlich Hintergrund-/Vordergrund-Paaren und Zustandsfarben.[22] Das lässt sich konzeptionell auf die vorhandenen Vanilla-Komponenten übertragen; eine React-/Tailwindmigration ist dafür nicht nötig. Repository-Lizenz MIT.[33]

Open WebUI ist eine Referenz für Chat-/Sprachabläufe, nicht automatisch ein frei umbenennbares Drop-in-Portal.[18] Das GitHub-Lizenzfeld ist als `NOASSERTION` eingeordnet.[35] Der aktuelle Lizenztext enthält zusätzliche Brandingbedingungen mit bestimmten Ausnahmen; ihn pauschal als MIT/BSD zu bezeichnen wäre falsch.[41] Deshalb keine Assets oder UI-Dateien kopieren und keine zweite produktive JARVIS-Oberfläche installieren.

### Mobile Abnahme

WCAG-Reflow behandelt unter anderem eine Breite von 320 CSS-Pixeln ohne Verlust von Funktion/Information und ohne allgemeine zweidimensionale Scrollpflicht. Zweidimensionale Spezialinhalte sind gesondert zu behandeln.[23] Das Minimum von WCAG 2.5.8 beträgt grundsätzlich 24×24 CSS-Pixel mit Ausnahmen; das Owner-Ziel von ungefähr 44×44 für wichtige Touchziele ist eine strengere Gestaltungsentscheidung, nicht derselbe Normwert.[24]

VisualViewport und VirtualKeyboard API sind relevante Referenzen für Layout bei Bildschirmtastaturen. Vor allem die VirtualKeyboard API hat Verfügbarkeitsgrenzen; keine allein darauf basierende Pflichtimplementierung ohne Fallback.[11][12]

**Abnahme im Bestand:** Chat-Eingabe mit echter Tastatur, Safe Areas, Orientierung, lange deutsche Beschriftungen, Scrollverhalten beim Streaming, Entwurferhalt bei Reconnect, deduplizierte Aufträge und zugängliche Dialoge prüfen. Frühere axe-/Viewportmessungen ersetzen diese Prüfungen nicht. APK-Quellcode ist zurückgestellt und wurde nicht als Browser-PWA umgedeutet.

### Agentenwelt und Diagramme

React Flow beschreibt Optimierungen wie stabile Callbacks und begrenzte unnötige Neuberechnungen; das ist eine nützliche Referenz für performante Graphen, aber keine Empfehlung zur React-Migration.[19] Die geprüfte xyflow-Repositorylizenz ist MIT.[34]

Bestehende Canvas-Welt behalten. Animationen müssen aus belegten Backendereignissen entstehen; dekorative Bewegung als solche kennzeichnen. Eine Linie bedeutet nur dann echte Delegation, wenn ihre Quelle das nachweist. Ein eigenes Diagramm kann alternative Darstellung desselben Stores sein, nicht ein zweiter Wahrheitsbestand.

## 7. Sicherheit, Modelle und Capability-Verwaltung

OWASP Excessive Agency ordnet die Risiken übermäßig mächtiger Agenten ein. Technisch minimale Werkzeuge, enge Rechte und menschliche Freigaben sind Schutzgrenzen, nicht bloß Persönlichkeitstext.[16] Die Hermes-Sicherheitsdokumentation ist zusätzlich gegen die tatsächlich installierte Version und deren Konfiguration zu prüfen, nicht ungeprüft zu übernehmen.[10]

MCP-Autorisierung verlangt unter anderem, dass Tokens für den richtigen Empfänger ausgestellt sind, und behandelt Consent/Confused-Deputy-Risiken. Ein Token für einen anderen Dienst soll nicht blind durchgereicht werden.[37] Das ist besonders wichtig, wenn ein Chatnetz oder Modellrouter Zugriff auf mehrere Apps erhält.

**Bestandsprüfung:** Secretwerte nicht in Chat/Logs ausgeben; bei Rotation Fingerprints vergleichen. Die früher angelegte Handy-App-Gruppe darf nicht stillschweigend mehr Dienste freigeben als gewollt. ntfy als Infrastruktur erst entfernen, wenn andere Nutzer/Abhängigkeiten ausgeschlossen sind. Eine aus dem Netz geladene Datei ist Dateninput, keine Berechtigung zum Ausführen von Anweisungen.

LiteLLM beschreibt Cooldowns, begrenzbare Wiederholungen, Fallbacks und verschiedene Routingstrategien.[38] Übertragbar sind die Mechaniken, nicht automatisch die konkreten Defaults oder ein zweiter Proxy. Der Evidence-Router bleibt Eigentümer der Modellwahl. Lokale Budgetzähler sind keine Kenntnis der Restquote beim Provider; ein Chat-Abo ist kein nachgewiesenes API-Recht.

OpenTelemetry trennt Traces, Metriken und Logs.[15] Für MA-HOME genügen zunächst gemeinsame Task-/Run-/Attempt-IDs, Statuswechsel und redigierte Fehlertypen. Keine zweite Telemetriedatenbank nur wegen einer schönen Demo. Modellprompts und private Signalchats gehören nicht automatisch in Observability-Exporte.

AppContainer ist eine Windows-Isolationsgrenze mit eigenem Sicherheitsmodell.[17] Ein vorhandener Fehler 0x80070005 ist kein Anlass, die Ausführung ungeschützt zu starten oder eine zuvor verweigerte Richtlinienänderung zu umgehen. Die offizielle Beschreibung beweist nicht, welche Policy den konkreten PC blockiert.

## 8. Memory, Kreativfunktionen und Erweiterungen

mem0 beschreibt verschiedene Gedächtnisarten.[9] Das ist eine Vorlage zur Trennung von Nutzerfakten, Gesprächen und Aufgabenwissen, nicht ein Beleg, dass bestehendes Retrieval bereits korrekt ist. Das Repository ist Apache-2.0 lizenziert.[32]

**Empfehlung:** Bestehende SQLite-/Obsidian-Strukturen behalten; jede Erinnerung mit Quelle, Gültigkeit, Bestätigungsstatus und Löschweg versehen. Erst Retrievaltests mit erwarteten Antworten und absichtlich widersprüchlichen Daten durchführen. Nicht automatisch private Signalgespräche dauerhaft als Nutzerprofil speichern.

ComfyUI dokumentiert seine Serverkommunikation und Workflow-Schnittstellen.[20] Das ist ein konkreter Anschluss für reproduzierbare Bild-/Kreativjobs; Repository-Metadaten nennen GPL-3.0 und den kanonischen Projektnamen Comfy-Org/ComfyUI.[36] Die Lizenzen von Modellen und Erweiterungen bleiben separate Prüfungen. Auf RTX 2060/6 GB ist die tatsächliche Eignung workflowabhängig; hier wurde kein neuer Workflow gebenchmarkt.

**Keine Fantasiefähigkeiten:** Manga, Video, 3D und Eternal-Bonds-Modding benötigen je einen echten Beispielauftrag, erlaubte Quelldaten, konkrete Tools, Ressourcenobergrenzen und überprüfbare Artefakte. Die bloße Existenz eines Skills reicht nicht. E-Mail-/Cloudkonten und Smart-Home-Aktionen nur im freigegebenen Umfang; autonome Capability-Aktivierung erst nach isoliertem Test und Basisabnahme.

## 9. Priorisierte Arbeitspakete aus der Recherche

Aufwände sind **grobe Engineering-Schätzungen, keine Zusage**; externe Konten, Akustik-/Gerätetests und Owner-Wartezeit sind nicht enthalten. Für alle Pakete gilt: Bestand und vorhandene Authentifizierung erhalten, keine neuen laufenden Kosten ohne Freigabe.

| ID / Klasse | Problem und vorgeschlagener Umfang | Aufwand / Ressourcen / Kosten | Abnahmekriterien | Risiko / Abhängigkeit / Rückbau |
|---|---|---|---|---|
| **DR-01 / Fehler + fehlende Fähigkeit** | Akustisches Wakeword von STT trennen; genau einen passenden Detektor mit Audioformat, VAD, Echo-/Reaktivierungsschutz und Gerätediagnose testen | 2–5 Tage bis Feldtest; laufende CPU/Netzlast erst messen; Modelllizenz beachten | Eigene Positiv-/Negativaufnahmen, verpasste Aktivierungen/Fehlalarme und Latenzen dokumentiert; kein behaupteter Erfolg ohne Akustik | Mikrofon/APK/Android-Hintergrundbetrieb; Featureflag und PTT-Fallback, keine Umgehung von Rechten |
| **DR-02 / Fehler + Verbesserung** | Gesprächszustand: kurze Folgefragephase, explizites Ende, Kontext, engere lokale Intents; anschließend einheitliche TTS-Strecke prüfen | 1–3 Tage für vorhandene Logik, zusätzliche Audiointegration separat; kein neuer Cloudvertrag | Mindestens fünf thematisch verknüpfte Turns; Kontextfragen; Pause; Stopp; kein Selbstecho; echter Hörvergleich | ASR-/TTS-Gerätegrenzen; Quellen/Bundles sichern, Featureflag |
| **DR-03 / Zuverlässigkeit** | Auftragsschema und Side-effect-Ledger prüfen; Checkpoint-/Resume-/Idempotenzlücken gezielt schließen | 2–5 Tage; vorhandene DB; zusätzliche Speicherlast messen | Abbruch nach Effekt und vor Bestätigung, Neustart/Resume ohne doppelte externe Aktion; fachliches QA-DONE | DB-Migration, Fencing, laufende Jobs; Testkopie zuerst, kompatibler Rollback |
| **DR-04 / Verbesserung** | Designsystemaudit aller eigenen Ansichten und Zustände; reale mobile Ablaufprüfung | 2–4 Tage + Gerätezugang; keine Frameworkmigration | 320–1280-Matrix plus echte Tastatur/Upload/Streaming/Offline; keine verdeckten Hauptaktionen | Browser/Embed-Grenzen; vorhandene Token-/Komponentenbackups |
| **DR-05 / Sicherheit** | Rollen-/Toolrechte, MCP-Consent, Councilbudget und Capability-Aktivierung technisch abgrenzen | 2–4 Tage Audit/gezielte Tests; keine pauschalen Adminrechte | Negativtests für unerlaubte Shell/Datei/Deploy/Gruppe; Budget begrenzt statt nur SOUL-Regel | Zugriffsausweitung, bestehende Verbote; fail-closed, per-Profil-Backup |
| **DR-06 / Effizienz** | Router mit Referenzmustern für Deadline/Retry/Cooldown und eindeutigen Budgetlabels prüfen | 1–2 Tage; bestehender Router, keine zweite Modellplattform | Providerfehler, Quote unbekannt, Budgetende, wiederholte Anfrage, zulässiger Fallback; keine PAYG-Aktivierung | API-Rechte/Providerlimits; Router-Konfig sichern |
| **DR-07 / Wissen** | Provenienz, Veralten, Konflikte, Löschung und Retrieval-Suite; Capability-Fachtests nach Kontenfreigabe | 2–4 Tage für einen repräsentativen Schnitt; Speicher/Tokenbedarf messen | Zitierte richtige Antworten, Konfliktfälle, Rücknahme einer Erinnerung, keine Secretpersistenz | Privatdaten und falsche dauerhafte Fakten; versionierte eigene Notizen statt Fremdplattform |
| **DR-08 / Erweiterung** | Ein vertikaler Kreativ-/Moddingpfad und zunächst lesende Smart-Home-Integration statt zahlreicher leerer Agenten | 1–3 Tage je eng begrenztem Pfad, Modell-/Assetkosten vorher prüfen | Reales Artefakt, Test/Preview, Lizenzprotokoll, Gaming-/Offline-Workerverhalten | GPU/VRAM, Plugins, fremde Daten; isolierte Workflows, keine automatische Aktivierung |

### Status der aktuellen Sprachänderungen

Die lokale Arbeitskopie enthält inzwischen Regressionstests für die gefundenen Dialogfehler. Neun Sprach-/Dialogtests sind grün, mit simulierten Recognition-/SpeechSynthesis-Grenzen. Geprüft sind Kontextübergabe, engere Aufgaben-Intents, ein 12-Sekunden-Anschlussfenster bei bereits aktiviertem Wake-Modus und dessen Ablauf über Recognizer-Neustarts. Diese letzte Dialogänderung ist während der Deepsearch **noch nicht deployt** und beweist keine akustische Erkennungsrate. Die zuvor ausgelieferte Satzsegmentierung ist davon zu unterscheiden.

Ein begrenztes Folgefenster ist nicht dasselbe wie echte semantische Turn-Erkennung. Die bisherige Browserstimme wurde dadurch auch nicht in eine neue neuronale Stimme verwandelt. PTT bleibt ohne bestätigten Wake-Modus ein einzelner Aufnahmevorgang; kein stillschweigendes Dauerlauschen.

## 10. Entscheidung und ehrliche Schlussabnahme

**Empfohlenes Gesamtpaket:** DR-01/DR-02 zur vom Owner beanstandeten Sprachfunktion, DR-03/DR-05 als technische Sicherheits- und Zuverlässigkeitsbasis, danach DR-04/DR-06/DR-07 im bestehenden System. DR-08 erst als einzelne, tatsächlich benötigte Fähigkeit. Keine gleichzeitige Installation mehrerer Orchestratoren, Voiceframeworks, Memorydienste oder Dashboards.

**NO-GO für die Behauptung „vollständiger JARVIS mit natürlichem freihändigem Dialog fertig“.** Der Owner meldet das Gegenteil, und die geprüfte Implementierung besitzt dafür noch nicht die erforderlichen Nachweise.

**GO für die Nutzung der recherchierten Muster als Entwicklungsgrundlage**, nicht für ungeprüfte Produktivmigrationen. Bereits freigegebene, begrenzte Reparaturen können weiterbearbeitet werden; neue Dienste, Lizenzbindungen, Rechte und Kosten werden separat behandelt.

**Weiter offen:** Gerätespezifische APK-Audiointegration, akustische Tests in der realen Umgebung, technische Aktivierung/Prüfung des neuen Signaladapters, vollständige Voice-Turn-Kette, Provider-API-Rechte, Sicherheitsblockaden der Windows-Sandbox, Hardwareerreichbarkeit und kontogebundene Fachabläufe. Eine Literaturrecherche kann diese Lücken nicht stellvertretend schließen.

**Supervisorvorschlag:** Manuelle gezielte Reviews plus bestehende Softwareüberwachung beibehalten. Ein automatischer Reviewrunner benötigt Trigger, minimalen redigierten Input, Obergrenzen, Ergebnisablage und getestetes Ausfallverhalten; keine dauerhafte Modellpräsenz behaupten. Das Reviewbudget muss technisch begrenzt sein, nicht nur als freundliche Aufforderung im Prompt stehen.

Jarvis: Phase A-Vertiefung, Deepsearch zum Gesamtauftrag dokumentiert – wichtigster Befund: fehlende Sprachpipeline-/Dialognachweise und mehrere offene Integrationsgates – nächster Schritt: DR-01/DR-02 gegen reale Audio- und Mehrturntests umsetzen; Gesamt-GO erst danach neu bewerten.

## Sources

[1] https://contributors.home-assistant.io/core/internals/assist-pipelines
[2] https://docs.livekit.io/agents/logic/turns
[3] https://github.com/dscripka/openWakeWord
[4] https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
[5] https://docs.langchain.com/oss/python/langgraph/persistence
[6] https://docs.langchain.com/oss/python/langgraph/interrupts
[7] https://docs.temporal.io/activity-execution
[8] https://temporal.io/blog/idempotency-and-durable-execution
[9] https://docs.mem0.ai/core-concepts/how-it-works
[10] https://hermes-agent.nousresearch.com/docs/user-guide/security
[11] https://developer.mozilla.org/en-US/docs/Web/API/VirtualKeyboard_API
[12] https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport
[13] https://docs.pipecat.ai/pipecat/learn/speech-input
[14] https://github.com/OHF-voice/piper1-gpl
[15] https://opentelemetry.io/docs/concepts/signals
[16] https://genai.owasp.org/llmrisk/llm062025-excessive-agency
[17] https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation
[18] https://docs.openwebui.com/features/chat-conversations/chat-features/voice-mode
[19] https://reactflow.dev/learn/advanced-use/performance
[20] https://docs.comfy.org/development/comfyui-server/comms_overview
[21] https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
[22] https://ui.shadcn.com/docs/theming
[23] https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
[24] https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
[25] https://api.github.com/repos/dscripka/openWakeWord
[26] https://api.github.com/repos/OHF-Voice/piper1-gpl
[27] https://api.github.com/repos/SYSTRAN/faster-whisper
[28] https://api.github.com/repos/livekit/agents
[29] https://api.github.com/repos/pipecat-ai/pipecat
[30] https://api.github.com/repos/langchain-ai/langgraph
[31] https://api.github.com/repos/temporalio/temporal
[32] https://api.github.com/repos/mem0ai/mem0
[33] https://api.github.com/repos/shadcn-ui/ui
[34] https://api.github.com/repos/xyflow/xyflow
[35] https://api.github.com/repos/open-webui/open-webui
[36] https://api.github.com/repos/comfyanonymous/ComfyUI
[37] https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
[38] https://docs.litellm.ai/docs/routing
[39] https://elevenlabs.io/pricing
[40] https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md
[41] https://raw.githubusercontent.com/open-webui/open-webui/main/LICENSE
