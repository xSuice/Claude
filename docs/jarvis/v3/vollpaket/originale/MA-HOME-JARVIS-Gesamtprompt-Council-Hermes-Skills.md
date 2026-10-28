# MA-HOME JARVIS — ULTIMATE AUTONOMOUS AI HEADQUARTERS
## Gesamtauftrag: Bestehendes Live-System + Specialist Councils + Unified Chat + Hermes + autonome Skills & Agentenverwaltung

**Zielumgebung:** Bereits laufendes MA-HOME-JARVIS-System. **Nicht** parallel neu aufsetzen.
**Prinzip:** JARVIS leitet; Councils diskutieren, entscheiden und delegieren; Hermes koordiniert operative Agenten; Execution Agents arbeiten. **Alles kommuniziert über einen gemeinsamen Chat und einen persistenten Nachrichtenbus.** Sobald diese Grundlage funktionsfähig und nachweislich getestet ist, verwaltet der Council selbstständig Skill-Bedarf, Plugins, MCP-Server, Hooks, Modelle und Spezialistenrollen. Dabei bleiben alle Änderungen in den bestehenden JARVIS-Diensten integriert.

## 1. Gesamtziel

Implementiere innerhalb meines bestehenden MA-HOME JARVIS ein autonomes, serverbasiertes, vernetztes KI-Hauptquartier. Ich möchte primär mit einem einzigen JARVIS-Chat kommunizieren. JARVIS erkennt Ziele, bestimmt die benötigten Fachspezialisten, lässt sie miteinander diskutieren und Aufgaben über Hermes delegieren. Ich kann alle Beratungen, Aufträge und Ergebnisse in meinem bestehenden Webportal live verfolgen, einzelne Councils bzw. Agenten per @Mention ansprechen und in deren Chats mitreden. Autorisierte Hintergrundaufgaben laufen weiter, wenn ich das Portal schließe; Neustarts dürfen sie nicht verlieren.

Das System muss mit echten vorhandenen Diensten und Schnittstellen arbeiten. Keine Schein-Chats, keine erfundenen APIs, keine Erfolgsmeldungen ohne Nachweise. Es ist kein theoretisches Konzept verlangt, sondern nach geprüfter Bestandsaufnahme die tatsächliche, schrittweise Integration.

## 2. Bestand verifizieren

Untersuche vor Änderungen die aktuelle JARVIS- und Hermes-Version, Bot-Profile und Chat-Sitzungen, Task-Engine, Scheduler, bestehende Router-/Modellprovider, Datenbanken und PostgreSQL, Obsidian und Memory, Portal-Frontend und Backend, API/WebSocket/SSE, Authentifizierung und Rollen, Netzwerk, Server, Worker, Plugins, Hooks, Skills, Tests, Deployments sowie die aktiv laufenden Dienste. Verifiziere alle Behauptungen aus historischen Projektinformationen gegen Dateien, Logs, Prozesse und Tests. Erstelle einen belegten Ist-Soll-Abgleich. Nutze Vorhandenes. Sichere kritische Daten und Konfigurationen vor riskanten Änderungen; plane Rollback.

## 3. Rollen und Ebenen

1. **JARVIS Headquarters:** Primärer Ansprechpartner, Gesamtkoordinator, Zielverständnis, Prioritäten, Auswahl von Councils, Konfliktentscheidung, Freigabepolitik, Ergebnisberichte.
2. **Supreme Council Network:** Gemeinsame strategische Beratungs- und Entscheidungsebene, vernetzt über eine dauerhafte Kommunikationsinfrastruktur.
3. **Domain Specialist Councils:** Fachliche Diskussionen, Planung, Beratung, Bewertung, Delegation und Qualitätskontrolle; keine operativen Toolrechte.
4. **Council Communication Bus:** Chat, Direktnachrichten, Threads, Gruppenkommunikation, @Mentions, nachvollziehbarer Entscheidungsverlauf, Aufgabenbezug.
5. **Hermes Execution Orchestrator:** Übernimmt autorisierte strukturierte Arbeitspakete, wählt operative Agenten, verteilt, überwacht, sammelt Nachweise, eskaliert.
6. **Execution Agents / Workers:** Programmieren, führen Terminal-/Server-/Browser-Aktionen aus, testen, recherchieren, deployen oder bearbeiten Dateien **nur mit passenden Rechten**.

## 4. Fach-Councils und Rollen

Pro nativer Hermes-Bot-Mode-Gruppe den in der installierten Version dokumentierten Maximalwert prüfen; als Zielstruktur **JARVIS + höchstens fünf Fachbots** vorsehen (bei bestätigtem Sechs-Bot-Limit). Gemeinsame logische Rollen dürfen über mehrere Gruppen hinweg wiederverwendet werden. Nur bei Bedarf aktivieren, nicht ständig alle Modelle laufen lassen.

- **DEV Council:** JARVIS, Chief Software Architect, Backend Director, Frontend/UX Director, Development Strategist, QA Director.
- **CLOUD Council:** JARVIS, Cloud Architect, Infrastructure Director, Network Director, Storage Director, Reliability Director.
- **AI Council:** JARVIS, AI Systems Architect, Model Router Director, Multi-Agent Director, Local AI Director, Memory/Evaluation Director.
- **SECURITY Council:** JARVIS, Security Architect, Identity/Access Director, Application Security Director, Privacy Director, Risk Director.
- **OPERATIONS Council:** JARVIS, Operations Director, Monitoring Director, Incident Director, Automation Director, Recovery Director.
- **STRATEGY Council:** JARVIS, Strategy Director, Research Director, Resource/Finance Director, Efficiency Director, Innovation Director.
- **DATA Council:** JARVIS, Data Architect, Knowledge Graph Director, Database Director, Memory Engineer, Governance Director.
- **CREATIVE Council:** JARVIS, Creative Director, Design Director, Writing Director, Media Director, Interactive Experiences Director.

Bei zusätzlichen Anforderungen neue **logische** Fachrollen entwickeln, sofern wirklich nötig; nicht unbegrenzt neue Agentenprozesse starten. Fachbots können ihre Meinungen widersprechen und andere Councils konsultieren. Security kann Richtlinienverletzungen blockieren. Entscheide mit Begründung und dokumentiertem Risiko, nicht nach Mehrheitsgefühl.

## 5. Chat-First: alle miteinander vernetzen

Schaffe ein **JARVIS Unified Chat Network** innerhalb meines existierenden Portals, das wirklich mit den Agenten-Backends verbunden ist:

- Primärer persönlicher **#jarvis**-Chat: Ich gebe JARVIS Aufträge; JARVIS teilt Entscheidungen, wichtige Fortschritte, Blockaden und nachweisbare Abschlüsse mit.
- Eigene persistente Gruppenkanäle: **#headquarters, #dev-council, #cloud-council, #ai-council, #security-council, #operations-council, #strategy-council, #data-council, #creative-council**.
- **#hermes-control** und aufgabenbezogene **Execution-Threads** mit Meldungen von Coding-/Test-/Server-/Research-Agenten.
- **Projekt-Chats** für übergreifende Aufgaben, direkte **Bot-zu-Bot-Chats**, und **Benutzer-zu-Bot-DMs**.
- Cross-Council-Konsultation ohne manuelles Kopieren und Einfügen.
- Ich kann Bots/Councils mit `@Name` oder `@Council` ansprechen, Threads kommentieren, priorisieren, Gespräche öffnen, freigegebene Entscheidungen ändern, Aufgaben pausieren, stoppen oder genehmigen.
- Echte Zeitstempel, eindeutige Sprecher, Status, Referenzen auf Aufgaben/Entscheidungen, Suche, Filter, Ungelesen-Status, Benachrichtigungen, Echtzeitupdates (SSE/WebSocket), Reconnect, mobiloptimierte Darstellung.
- Hauptchat bleibt übersichtlich; ausführliche interne Debatten gehören in ihre Channels, sind aber einsehbar. Zeige begründete Positionen und Entscheidungen, **keine verborgenen privaten Chain-of-Thought-Inhalte**.

Beispiel:
Ich: „JARVIS, verbessere die Portalperformance.“
JARVIS: „@DEV @CLOUD @OPERATIONS: Bitte beraten und notwendige Diagnosen über Hermes anfordern.“
DEV: „Wir brauchen zuerst belastbare Profilingdaten.“
CLOUD: „@Hermes: Erstelle einen lesenden Ressourcenbericht.“
Hermes: „Inspektionsauftrag delegiert: T-204.“
Execution Agent: „Bericht verfügbar: [Artefakt/Logs].“
DEV und CLOUD diskutieren überprüfbare Alternativen.
JARVIS delegiert nach gültiger Freigabe den beschlossenen Plan.
QA überprüft Tests; JARVIS meldet erst danach den tatsächlichen Abschluss.

## 6. Hermes-Bot-Mode-Grenzen korrekt behandeln

Sieh die aktuelle offizielle Dokumentation und die lokal installierte Hermes-Version ein: https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode . Prüfe native Gruppengröße, Diskussionsrunden, Nachrichtenlimits, Bot-Profile, permanente Bot-Chats, Headless-Funktionen, `message_agent`, Gateway, Bot-Peers und APIs. **Gehe nicht davon aus, dass `message_agent` innerhalb einer Gruppenmitglied-Sitzung verfügbar ist**; verwende gegebenenfalls kanonische Bot-Chats und eine eigene serverseitige Vermittlung. Nutze native Gruppenchats, wenn kompatibel; andernfalls bilden persistente **logische Council-Chats** im JARVIS-Backend die verbindliche Orchestrierungsebene. Der Hauptserver muss auch ohne gestartete Hermes-Desktop-App und ohne Windows-PC arbeitsfähig bleiben.

Diskussionen benötigen Ziel, Teilnehmer, Budget, Runden-/Nachrichtenobergrenze, Abbruchkriterien und Beschluss. Mehrstufige Beratungen durch gespeicherte Zusammenfassungen und separat geplante nächste Phasen ermöglichen, niemals unkontrollierte Endlosschleifen auslösen.

## 7. Nachrichtenbus und Persistenz

Bestehende PostgreSQL-/Queue-Infrastruktur nutzen, sofern geeignet. Nachrichten strukturiert speichern mit `message_id`, `conversation_id`, `thread_id`, `task_id`, `sender_id`, `recipient_id/room_id`, `timestamp`, `message_type`, `priority`, `correlation_id`, `delivery_status` und Berechtigungskontext. Unterstütze Authentifizierung, Autorisierung, Idempotenz, Deduplizierung, transaktionale Zustandsübergänge/Outbox (wo erforderlich), Leasing, Retries, Dead Letters, Sichtbarkeit des Zustellstatus und Ereignis-Audit. Abstürze dürfen weder Unterhaltungen verlieren noch unerlaubt ausführende Aktionen duplizieren.

## 8. Council ist ausschließlich strategisch

**Council darf nur:** lesen über geeignete freigegebene Berichte/Research-Agents, besprechen, planen, entscheiden, andere Councils konsultieren, Aufgaben über Hermes delegieren, Nachweise anfordern und Ergebnisse beurteilen.
**Council darf nicht:** Shellbefehle ausführen, Code schreiben, Produktivkonfigurationen ändern, Dateien operativ editieren, Deployments ausführen oder direkten Schreibzugriff auf Worker erhalten. Erzwinge dies mit **echten Tool-Berechtigungen und Rollen**, nicht nur Prompttext. Eingeschränkte Koordinationsdaten/Chatnachrichten dürfen über den autorisierten Nachrichtenservice gespeichert werden.

## 9. Vollständige autonome Delegationskette

`Benutzer → JARVIS → passende Councils → Entscheidung → Policy-/Freigabecheck → Hermes → Execution Agents → Tests/Evidence → Council-Review → JARVIS → Benutzer`.

Jedes Arbeitspaket enthält Task-ID, Ziel, Abhängigkeiten, zuständige Rolle, Priorität, Akzeptanzkriterien, Rechte, Werkzeuge, Zeit-/Kostenbudget, Retry- und Rollbackplan, benötigte Nachweise. Hermes wählt vorhandene passende Ausführungsagenten; vermeidet unnötige Neuinstanzen. Bei Fehlern Council erneut konsultieren; innerhalb definierter Retry-/Budgetgrenzen sicher korrigieren. Keine Erfolgsmeldung allein aufgrund eines Agenten-Claims.

## 10. Persistenter Serverbetrieb

Bestehende Task-Engine erweitern: `BACKLOG → DISCUSSION → PLANNED → APPROVED → DELEGATED → RUNNING → VALIDATION → REVIEW → COMPLETED`; weitere Zustände `BLOCKED`, `FAILED`, `RETRY_PENDING`, `WAITING_APPROVAL`, `CANCELLED`.

Tasks unabhängig von UI-Sitzungen ausführen; nach Neustarts kontrolliert fortsetzen. Scheduler, Queue, Worker-Heartbeat, Timeout, Backoff, Dead Letter, Kill-Switch, Events, Nachweisspeicherung und verlässliche Statusrückmeldung integrieren. Keine blind wiederholten externen Aktionen. Proaktiv auf tatsächliche Events wie Dienst-Ausfall, Testfehler, neue Task-Ergebnisse, Ressourcenprobleme oder autorisierte regelmäßige Wartung reagieren. Keine sinnlosen Dauer-Diskussionen.

## 11. Smart Router & Kosten

Bestehenden Router nutzen. Vorläufige Präferenz: JARVIS-Koordination GPT-6.1 Sol mit niedrigem Reasoning **falls tatsächlich verfügbar und kompatibel**; Council-Modelle intelligent nach Fachgebiet/Komplexität/Kosten; Execution Agents bevorzugt über **vorhandenen Nexum Router**; lokale KI für passende günstige Aufgaben; andere verifizierte Cloudmodelle als zulässige Fallbacks. Jede Provider-Verfügbarkeit, API-Berechtigung, Planrestriktion und Kostenregel verifizieren.

Optimiere Tokenverbrauch, Caching, Kontextkomprimierung, Parallelität, Modellstärke, Warteschlangen und Durchsatz. Agenten nur bei Bedarf aufrufen. Budgetgrenzen pro Projekt, Rolle, Task und Provider. Keine unbeaufsichtigten Käufe, keine implizite Nutzung ungeeigneter interaktiver Abos als Produktions-API.

## 12. Memory und Obsidian

Chatprotokolle in autorisiertem Chat-Store halten; relevante Architekturentscheidungen, Lessons Learned, Ergebnisse, offene Aufgaben und langfristiges Projektwissen in vorhandene Memory-/Obsidian-/PostgreSQL-Komponenten über autorisierte Schreibdienste überführen. Kein blindes Schreiben aller Chatnachrichten als Notizen. Versionierung, Quellenbezug und Dublettenkontrolle.

## 13. Server, Cloud, Worker

Linux-Server ist Master und primäre Entwicklungs-/Ausführungsumgebung. Windows-PC und GPU-Rechner sind optionale Worker, nicht notwendige Voraussetzung. Zugriffe ausschließlich authentifiziert und nach minimalen Rechten über bestehende sichere Netzwerke/VPN. Keine unnötig öffentlichen Verwaltungs- oder Agentenports. Bei Offline-Workern auf geeignete verfügbare Alternativen ausweichen oder Task eindeutig blockieren.

## 14. Sicherheit und Freigaben

Routineabläufe möglichst autonom innerhalb explizit delegierter Befugnisse. Gesonderte Genehmigung für irreversible Löschungen, kritische Zugangskontrolländerungen, unerwartete Käufe/Kosten, Veröffentlichung sensibler Dienste und Aktionen außerhalb der vereinbarten Rechte. Technische Least-Privilege-Grenzen, Secret-Handling, Prompt-Injection-Schutz, isolierte Ausführung, Audit-Trails, sichere Backups, Rollbacks und manueller Not-Stopp. Sicherheits- und QA-Prüfungen niemals zugunsten der Tokensparsamkeit umgehen.

## 15. Webportal

Das bestehende Portal bleibt einzige primäre UI, kein neuer Browser-Tab im regulären Workflow. Zeige Chat-Hauptansicht, Council-Channels, Direktnachrichten, Threads, Hermes-Jobs, Aufgabenhierarchie, Agentenstatus, aktuelle Ausführungen, Entscheidungen, Budget/Tokenverbrauch, Server-/Workerstatus und dokumentierte Ergebnisse. Mobile-first für Smartphone, Tablet, Desktop. Bestehende Authentifizierung und Berechtigungssystem verwenden. Keine Fake-Status; Live-Daten aus Backend und Logs anzeigen.

## 16. Autonomes Capability- und Specialist-Management — erst nach erfolgreichem Council-Aufbau

**Verbindliche Freischaltbedingung:** Zuerst das Headquarters, alle erforderlichen Councils, den gemeinsamen Chat, die Hermes-Delegation, Persistenz, Berechtigungstrennung und das Portal wirklich integrieren und Ende-zu-Ende prüfen. **Erst danach** die autonome Capability-Verwaltung aktivieren. Bis dahin sind Inventarisierung, Analysen und Vorschläge erlaubt, aber keine selbstständige Skill-Neuinstallation oder Rollenänderung aufgrund dieser Zusatzfunktion.

Nach erfolgreichem Basis-Test soll das Council-Netzwerk selbstständig und nachvollziehbar beantworten:

- Welche Skills, Plugins, MCP-Server, Hooks, Modelle und Werkzeuge benötigen JARVIS, Hermes, bestimmte Councils und einzelne ausführende Agenten wirklich?
- Welche Fähigkeiten sind bereits vorhanden, wo liegen Lücken oder redundante Funktionen?
- Welche Fähigkeiten gehören zu strategischen **Council-Rollen** und welche nur zu operativen **Execution Agents**?
- Reicht eine vorhandene Fähigkeit, Skill-Erweiterung oder temporäre Rolle aus, oder ist ein neuer Spezialist beziehungsweise ein neuer Ausführungsagent tatsächlich notwendig?
- Welche Modelle und Ressourcen sind je Rolle die wirtschaftlichste **nachweislich ausreichende** Wahl?
- Welche Fähigkeiten müssen temporär, eingeschränkt oder nach Auftragsende wieder entzogen werden?

### 16.1 Capability Director als logische Council-Funktion

Weise dem vorhandenen AI Council die Verantwortung **Capability Director** zu (optional gemeinsam mit STRATEGY/SECURITY/DEV). Er muss kein zusätzlicher sechster Fachbot oder dauerhaft laufender Modellprozess sein: nutze eine vorhandene geeignete Rolle und aktiviere sie nur bei Bedarf. Der Capability Director organisiert die Beratung, erhält Diagnosen ausschließlich über lesende Inspection/Research Agents und stellt begründete Skill-/Agenten-/Tool-Empfehlungen zur Council-Entscheidung bereit.

Ablauf:
1. Aus Auftrag, Störung, Qualitätsmangel oder periodischem Review einen konkreten Fähigkeitsbedarf erkennen.
2. Vorhandene Capability Registry und installierte Komponenten abfragen.
3. Wiederverwendung vor Erweiterung, Erweiterung vor Neuinstallation, Neuinstallation vor zusätzlichem dauerhaftem Spezialisten priorisieren – sofern qualitativ sinnvoll.
4. Mit fachlich zuständigem Council, Efficiency und bei Bedarf Security konkrete Alternativen diskutieren.
5. Herkunft, Version, Wartungsstatus, Lizenz, Kompatibilität, Testbarkeit, Berechtigungen, Risiken, Nutzen und Kosten abgleichen.
6. Entscheidung und Berechtigungsvorschlag mit Akzeptanzkriterien speichern.
7. Nach Policy- und gegebenenfalls Benutzerfreigabe eine Umsetzung **über Hermes** an einen berechtigten Execution Agent delegieren.
8. Zuerst in isolierter Testumgebung prüfen; erst nach bestandener Validierung kontrolliert aktivieren.
9. Registry, Agentenprofil, Memory und Webportal konsistent aktualisieren.
10. Optional zeitlich befristete Rechte/Fähigkeiten nach Auftragsende automatisch entziehen lassen.

### 16.2 Zentrale Capability Registry – eine maßgebliche Datenquelle

Inventarisiere **alle laufenden und vorhandenen Systeme**: Hermes-Profile, Skills, MCP-Server, Hooks, Plugins, Modellprovider, lokale Modelle, bestehende Tools, Agenten, Subagenten, Council-Rollen, Portaldienste und Worker-Fähigkeiten.

Speichere je Capability unter anderem:

- `capability_id`, Name, Typ, Beschreibung, Version, Herkunft und Integritätsnachweis.
- Installations-/Aktivierungsstatus, Host/Runtime, Kompatibilität und Abhängigkeiten.
- Zugeordnete Council-Fachgebiete, Spezialisten, Execution-Agenten und Task-Typen.
- Erforderliche Berechtigungen, Sicherheitsstufe und zuständige Freigaberichtlinie.
- Kosten-/Tokenprofil, Performance, Zuverlässigkeit, Nutzungsstatistiken.
- Testnachweise, bekannte Einschränkungen, letzter Prüfzeitpunkt, Verantwortliche.
- Nutzbare Alternativen, empfohlene Ablösung, Deaktivierungs-/Rollback-Verfahren.

Bevorzuge vorhandene PostgreSQL-/Konfigurations- und Agentenregister-Komponenten, statt eine zweite unabhängige Wahrheitsquelle zu schaffen. Obsidian erhält relevante Entscheidungen und Dokumentation, nicht unkontrollierte Rohdaten. Zugangsdaten niemals als Klartext in Chats/Registry speichern.

### 16.3 Intelligente Skill-Zuweisung an Spezialisten

Council-Rollen erhalten **nur beratende Fähigkeiten**, beispielsweise Architektur- und Code-Review auf Basis bereitgestellter Berichte, Bedrohungsmodellierung, Routing-Analyse, Monitoring-Auswertung, Wissensarchitektur und fachliche Planung. **Keine Council-Rolle erhält Shell, Datei-Schreibrechte, Deployment- oder Produktionsadministrationswerkzeuge.** Die Grenze wird auf Dienst-/Tool-/Rollenebene durchgesetzt, nicht durch Textinstruktionen allein.

Hermes und passende Execution Agents erhalten bedarfsgerecht operative Skills, etwa Codebearbeitung, Testausführung, Browserinteraktion, Docker-/Serverwartung, Dokumentations- oder Asset-Erstellung – strikt innerhalb konkret genehmigter Task-Rechte.

Die Zuweisung muss nachvollziehbar und vorzugsweise aufgabenbezogen, zeitlich beschränkt und widerrufbar sein. Verhindere eine pauschale Verteilung aller Plugins und MCP-Zugriffe an alle Agenten.

### 16.4 Neue Spezialisten, zusätzliche Councils und Teamstruktur

Bei wiederholtem Aufgabenbedarf (z. B. Minecraft-Modding, Computer Control, Voice, Research, Creative Studio) prüfen:

1. Kann ein vorhandener Spezialist mit bestehender Fähigkeit aushelfen?
2. Ist ein zusätzlicher Skill für einen bestehenden Spezialisten ausreichend?
3. Reicht ein temporäres Profil/eine zeitlich befristete Fachberatung?
4. Bringt eine dauerhaft neue **logische** Council-Rolle messbar mehr Nutzen als Kosten?
5. Ist eine zusätzliche Hermes-Execution-Agent-Rolle nötig oder genügt das bestehende Agentenregister?
6. Erfordert die Gruppenbegrenzung einen separaten vernetzten Council statt eines überfüllten Chats?

Neue Rollen sind nicht gleich neue dauerhafte Prozesse. Weise nur nach begründeter Entscheidung und zulässiger Freigabe an; dokumentiere Zuständigkeit, Skills, Modellrouting, Berechtigungen, Budget und Abschaltkriterien. Konsolidiere überlappende Rollen.

### 16.5 Hooks, Automationen, Skill-Lifecycle und Selbstoptimierung

Der Council soll ereignisgesteuert Verbesserungsmöglichkeiten erkennen: nach Codeänderung relevante Tests beauftragen, nach Deployment Health Checks anstoßen, wiederholte Agentenfehler eskalieren, nach Projektabschluss Memory/Dokumentation aktualisieren, bei Provider-Limits zulässige Fallbacks erwägen, ineffiziente/ungenutzte Skills zur Deaktivierung vorschlagen.

Jede Änderung an Hooks/Plugins/Skills ist zunächst ein **Vorschlag mit Test und Risikoanalyse**; Implementierung ausschließlich durch Hermes und autorisierte Execution Agents. Keine ungeprüften Downloads, keine eigenmächtige Sicherheitslockerung, keine Selbstmodifikation ohne Rollback, keine unbegrenzte Erzeugung von Agenten. Prüfe Änderungen per Regressionstest, Rollout/Canary wo sinnvoll und Monitoring; bei Qualitätsverlust Rollback.

Optimiere messbar statt behauptet: Erfolgsquote, Testqualität, durchschnittliche Bearbeitungsdauer, Kosten pro erfolgreich abgeschlossener Aufgabe, Tokenverbrauch, unnötige Debatten und Ressourcenbelastung. Ein Review darf auch beschließen, **nichts zu ändern**.

### 16.6 Gemeinsamer Chat für Capability-Entscheidungen

Alle Capability-Entscheidungen laufen durch das bestehende Unified Chat Network und besitzen Task-/Decision-IDs. Beispiel:

> DEV: „Für das neue Feature fehlt uns eine geeignete Testfähigkeit.“  
> Capability Director: „Ein vorhandener Skill kann erweitert werden. Neue MCP-Installation ist nicht notwendig.“  
> SECURITY: „Die Änderung benötigt keine zusätzlichen Produktionsrechte; isolierte Tests sind Pflicht.“  
> JARVIS: „Beschlossen. Hermes erhält einen begrenzten Implementierungsauftrag.“  
> HERMES: „Agent hat Änderung ausgeführt; Prüfartefakte sind hinterlegt.“  
> QA: „Tests bestanden; Aktivierung empfohlen.“

Ich kann alle Diskussionen im Portal sehen, per @Mention hinterfragen, Genehmigungen erteilen und eine Änderung stoppen. Der Capability Director selbst führt keine Shellbefehle aus.

### 16.7 Capability-Management im bestehenden Portal

Erweitere das vorhandene Headquarters um einen **Capability & Specialist Management**-Bereich mit: Councils, Rollen, Fähigkeiten, Skills, Plugins, Hooks, MCP-Servern, Modellen, Berechtigungen, Kosten, Nutzung, Qualitätsnachweisen, Sicherheitsbewertungen, geplanten Änderungen, Freigaben und Rollbacks. Zeige die tatsächlich verwendeten Backend-Daten und ermögliche direkte Sprünge in zugehörige Chats, Tasks und Entscheidungen. Keine zweite Web-App und keine Schein-Statusanzeige.

### 16.8 Zusätzliche Capability-Tests (erst nach bestandenem Basis-Council-Test)

1. Fehlende Fähigkeit anhand einer realistischen Testaufgabe erkennen.
2. Vorhandene Skills/Agenten/Tools vollständig inventarisieren und Alternativen vergleichen.
3. Eine unnötige neue Rolle begründet verwerfen.
4. Eine sinnvolle zusätzliche temporäre Fachrolle mit gültigen Gruppenlimits planen.
5. Eine Capability dem richtigen **operativen** Agenten zuordnen, Council-Rechte unverändert eingeschränkt halten.
6. Herkunft, Berechtigungen, Kosten, Kompatibilität und Security-Freigaben nachweisen.
7. Änderung über Hermes in einer Sandbox delegieren und ausführen lassen.
8. Testresultate unabhängig verifizieren; unsichere Erweiterung blockieren.
9. Capability Registry, Agentenprofil, Memory, Chat und Portal konsistent aktualisieren.
10. Rechte/temporäre Fähigkeiten entziehen, Capability kontrolliert deaktivieren und Rollback testen.
11. Provider-Ausfall, Limit, Neustart und Doppelzustellung ohne unsichere Wiederholungen behandeln.
12. End-to-End: „Bedarf → Council-Diskussion → Entscheidung → Hermes → Execution Agent → Test → Registry → Portal → JARVIS-Abschlussmeldung“.

**Diese Phase gilt erst als fertig, wenn nicht nur vorgeschlagene Zuweisungen, sondern echte autorisierte Änderungen mit reproduzierbaren Nachweisen demonstriert wurden.**

## 17. Implementierungsfolge und Freischaltung in zwei Stufen

**STUFE A – Council-Hauptquartier stabil integrieren (zwingend zuerst):**

A. Ist-Zustand des gesamten Live-Systems verifizieren und Integrationspunkte dokumentieren.
B. Council-Profile, Rollen und technische Berechtigungsgrenzen definieren; vorhandene Hermes-Komponenten verwenden.
C. Persistentem Unified Chat, Nachrichtenbus und eindeutigen Bot-/Room-Identitäten echte Backend-Anbindungen geben.
D. Direktnachrichten, Gruppen-Chats, Cross-Council-Konsultationen, Benutzerchat, @Mentions und Projekt-Chats real testen.
E. Hermes-Delegation, Execution Agents, Task-Engine, Watchdog, Rückmeldungen und sichere Wiederaufnahme integrieren.
F. Bestehendes Smart-Routing, Limits, Kostenkontrolle, Memory, PostgreSQL, Obsidian und optionale Worker anschließen.
G. Portal vollständig mit Backend verbinden; Mobilansicht und tatsächlichen Live-Status prüfen.
H. Sicherheits-, Neustart-, Fehlerrückführungs- und End-to-End-Tests durchführen; Deployment inklusive Rollback.

**GO/NO-GO-GATE:** Council-Chat, Delegation, Berechtigungen, Persistenz und gesamte Testkette müssen mit technischen Belegen funktionieren. Ohne GO bleibt Capability Management in read-only Inventar-/Beratungsmodus. Probleme zuerst durch Hermes mit autorisierten Agents beheben lassen.

**STUFE B – Fähigkeiten und Spezialisten autonom organisieren (erst nach GO):**

I. Vorhandene Agenten, Skills, Plugins, MCP-Server, Hooks, Modelle und Rechte in die zentrale Capability Registry übernehmen.
J. Capability Director als logische bestehende Council-Funktion aktivieren.
K. Vorschlags-, Review-, Rechte-/Kostenprüfungs- und Freigabeworkflow integrieren.
L. Sandboxbasierte Skill-/Hook-/Plugin-Lifecycle-Aufträge über Hermes ermöglichen.
M. Temporäre und dauerhafte Spezialistenrollen nach dokumentiertem Nutzen verwalten, unter Einhaltung der Hermes-Gruppenlimits.
N. Capability-Chat, Registry, Security-Review, Tasks und Portal vernetzen.
O. Capability-End-to-End-Tests, Rückbau und Rollback; erst dann als produktiv freigeben.

Arbeite autorisierte Schritte möglichst eigenständig. Unabhängige sichere Prüfungen können parallel erfolgen. Keine Duplikat-Systeme. Nicht bei bloßer Dokumentation stehen bleiben, sofern die reale Umsetzung technisch zugänglich und zulässig ist. Jeder Abschluss braucht belegte Tests; Blockaden und unerfüllte Ziele offen benennen.

## 18. Verbindliche End-to-End-Tests

1. Ich schreibe im JARVIS-Hauptchat; JARVIS öffnet eine passende Fachberatung.
2. Mindestens zwei Council-Bots diskutieren in persistenter Unterhaltung.
3. DEV kontaktiert CLOUD; Nachricht, Antwort und Thread sind dauerhaft gespeichert.
4. Direktnachricht von Spezialist zu Spezialist funktioniert.
5. Ich schreibe in einen Council-Kanal und spreche einen Spezialisten per @Mention an.
6. Ein Council delegiert über JARVIS/Hermes einen ungefährlichen realen Testauftrag.
7. Execution Agent erledigt Aufgabe, berichtet Artefakt/Logs/Tests; Council validiert unabhängig.
8. Ein Fehler führt zu begrenzter Wiederaufnahme oder gekennzeichneter Blockade, nicht zu Endlosschleife.
9. Chat/Tasks überstehen Prozess- und Serverneustarts ohne gefährliche Duplikate.
10. Council kann trotz versuchtem Tool-Aufruf **keine** Shell-/Dateischreibaktion ausführen.
11. Budgetlimit und Provider-Ausfall führen zu regelkonformer Fortsetzung oder Blockade.
12. Funktioniert ohne laufende Desktop-App bzw. optionalen Windows-PC.
13. Im Portal sind tatsächliche Chats, Jobs, Tokenverbrauch, Entscheidungen und Status mobil sichtbar.
14. Benutzer kann stoppen, priorisieren, Freigabe geben/verweigern; alle Rechte werden durchgesetzt.
15. Vollständiger Test von Auftrag bis geprüfter Fertigmeldung ohne Benutzer-Mikromanagement.

## 19. Abschlussanforderungen und Arbeitsweise

Arbeite autorisierte Schritte selbstständig bis zu prüfbaren Erfolgskriterien ab. Führe eine tatsächliche Bestandsaufnahme, Code-/Konfigurationsänderungen, Tests und ein kontrolliertes Deployment durch, sofern zulässiger Zugriff gegeben ist. Blockaden und nicht realisierbare Hermes-Funktionen transparent kennzeichnen; eine kompatible, verifizierte Alternative einsetzen, statt API-Fähigkeiten zu erfinden.

**Endzustand:** Nach bestandener Stufe A und gesondert geprüfter Freischaltung von Stufe B entscheidet der Council zusätzlich selbstständig über notwendige Skills, Plugins, MCP-Server, Hooks, Modelle, Berechtigungszuweisungen und neue Spezialistenrollen; die technische Arbeit bleibt Hermes/Execution Agents vorbehalten. Ich chatte primär mit JARVIS. Ein vernetztes Netz aus Specialist Councils berät, diskutiert und delegiert, Hermes koordiniert die praktische Arbeit, Execution Agents erledigen sie, und alle Unterhaltungen, Entscheidungen, Tests und Ergebnisse sind im bestehenden MA-HOME-Webportal sichtbar. Der Hauptserver arbeitet innerhalb seiner Berechtigungen dauerhaft selbstständig – auch wenn ich offline bin.
