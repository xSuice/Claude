# MA-HOME JARVIS – AUTONOMOUS TASK MANAGEMENT, COUNCIL SUPERVISION & SELF-HEALING SYSTEM

## MASTER-AUFTRAG

Erweitere das bestehende MA-HOME-JARVIS-System um eine vollständig integrierte, persistente und weitgehend autonome Auftragsverwaltung mit intelligenter Planung, kontinuierlicher Agentenüberwachung und automatischer Fehlerbehebung.

**Leitprinzip: Auftrag erhalten → Speichern → Planen → Delegieren → Ausführen → Überwachen → Fehler beheben → Verifizieren → Abhaken → Dokumentieren.**

Das Ziel ist kein weiteres isoliertes Tool, sondern eine zentrale Fähigkeit der bestehenden JARVIS-/HERMES-/Council-Architektur.

JARVIS soll möglichst selbstständig dafür sorgen, dass angenommene und autorisierte Aufträge tatsächlich bearbeitet und abgeschlossen werden.

**WICHTIG:** Prüfe zuerst die tatsächliche bestehende Infrastruktur, Datenbanken, Agenten, Dienste, Dateien und Schnittstellen. Nutze vorhandene Funktionen, statt parallele Systeme oder unnötige neue Komponenten aufzubauen.

---

# 1. SYSTEMARCHITEKTUR UND VERANTWORTLICHKEITEN

Implementiere folgende logische Zuständigkeiten:

### JARVIS – Zentrale Benutzeroberfläche

- Nimmt Aufträge über Chat, Sprache und Webportal entgegen.
- Zeigt Fortschritt, Ergebnisse und Probleme.
- Ermöglicht natürliche Kommunikation mit dem Council.
- Ermöglicht Eingriffe, Prioritätsänderungen und Nachfragen.

### Council-Dirigent – Oberste Koordination

Der Dirigent ist der zentrale Planungs- und Koordinationsverantwortliche.

Seine Aufgaben:

- Aufträge erfassen und strukturieren
- Ziele und Erfolgskriterien festlegen
- Umsetzungspläne erstellen
- Aufgaben in Teilaufgaben zerlegen
- Zuständigkeiten vergeben
- Abhängigkeiten verwalten
- Spezialisten koordinieren
- Fortschritt überwachen
- Entscheidungen dokumentieren
- Fehlgeschlagene Aufgaben neu planen
- Ergebnisse zur Prüfung weitergeben
- Offene Aufträge bis zu ihrem Abschluss verfolgen

Der Dirigent soll selbst möglichst wenig operative Arbeit erledigen, sondern Spezialisten sinnvoll einsetzen.

### Council-Spezialisten

Spezialisten führen die ihnen zugewiesenen Aufgaben aus.

Sie müssen:

- Aufträge ausdrücklich übernehmen
- Ihre tatsächliche Ausführung dokumentieren
- Überprüfbare Zwischenergebnisse liefern
- Blockaden melden
- Ergebnisse speichern
- Abschlussnachweise bereitstellen

### JARVIS Watchdog

Der Watchdog ist ein unabhängiger, dauerhaft aktiver Supervisor.

Er überprüft:

- Ob Spezialisten tatsächlich arbeiten
- Ob Fortschritt entsteht
- Ob Aufgaben vergessen werden
- Ob Prozesse hängen
- Ob Agenten in Endlosschleifen geraten
- Ob Fehler auftreten
- Ob Ausführungen unterbrochen wurden
- Ob Aufgaben nach Fehlern wieder aufgenommen werden

### Recovery Manager

Der Recovery Manager übernimmt die technische Wiederherstellung und Fehlerbehebung.

Er soll nicht nur Probleme melden, sondern ihre Ursachen analysieren, sichere Reparaturen durchführen und den Erfolg überprüfen.

### Independent Service Supervisor

Eine unabhängige, ressourcenschonende Systemüberwachung kontrolliert Watchdog, Recovery Manager und die kritischen JARVIS-Dienste.

So darf auch der Ausfall des Councils nicht unbemerkt bleiben.

---

# 2. DAUERHAFTE PROMPT- UND AUFTRAGSSPEICHERUNG

**Jeder Auftrag muss vor Ausführungsbeginn dauerhaft gespeichert werden.**

Das gilt für:

- Benutzerprompts
- Council-Aufträge
- Spezialisten-Aufträge
- Automatisch erzeugte Teilaufgaben
- Entwicklungsaufträge
- Systemoptimierungen
- Reparaturaufträge
- Langfristige Projektziele
- Hintergrundaufgaben
- Unterbrochene und fehlgeschlagene Arbeiten

Erfasse mindestens:

- Eindeutige Auftrags-ID
- Originalprompt
- Erstellungszeitpunkt
- Ursprung des Auftrags
- Zugehöriges Projekt
- Priorität
- Verantwortlichen Agenten
- Gewähltes Modell
- Ziel und Erfolgskriterien
- Ausführungsplan
- Teilaufgaben
- Abhängigkeiten
- Aktuellen Status
- Fortschritt
- Zeit- und Ressourcenverbrauch
- Tool-Ausführungen
- Fehler und Reparaturversuche
- Prüfergebnisse
- Abschlussnachweise

Originalprompts dürfen nicht überschrieben werden.

Änderungen werden versioniert und nachvollziehbar dokumentiert.

Verwende eine zentrale, zuverlässige Auftragsdatenbank.

---

# 3. AUTOMATISCHE PLANUNG UND CHECKLISTEN

Jeder neue Auftrag erhält einen strukturierten Arbeitsplan.

Beispiel:

**Auftrag: JARVIS Dashboard entwickeln**

- [x] Anforderungen analysieren
- [x] Architektur untersuchen
- [x] Umsetzung planen
- [ ] Frontend entwickeln
- [ ] Backend anbinden
- [ ] Agentenvisualisierung integrieren
- [ ] Mobile Darstellung optimieren
- [ ] Integrationstests ausführen
- [ ] Fehler beheben
- [ ] Produktivsystem testen
- [ ] Abschluss dokumentieren

Checklisten müssen automatisch aktualisiert werden.

Unterstütze:

- Verschachtelte Teilaufgaben
- Prioritäten
- Abhängigkeiten
- Verantwortlichkeiten
- Meilensteine
- Blockaden
- Wiederherstellungspunkte

**Ein Punkt darf ausschließlich nach erfolgreicher Verifikation als abgeschlossen markiert werden.**

Eine Behauptung eines Agenten ist kein ausreichender Erfolgsnachweis.

---

# 4. ZENTRALE AUFTRAGSZUSTÄNDE

Unterstütze folgende Status:

- INBOX – Neu erfasst
- PLANNING – Wird geplant
- READY – Ausführungsbereit
- RUNNING – In Bearbeitung
- WAITING – Wartet auf externe Abhängigkeit
- BLOCKED – Blockiert
- STALLED – Kein erkennbarer Fortschritt
- RECOVERING – Automatische Fehlerbehebung läuft
- REVIEW – Ergebnis wird überprüft
- DONE – Nachweislich abgeschlossen
- FAILED – Fehlgeschlagen
- CANCELLED – Bewusst abgebrochen
- ARCHIVED – Abgeschlossen und archiviert

Statuswechsel müssen nachvollziehbar protokolliert werden.

Fehlgeschlagene Aufträge bleiben erhalten.

---

# 5. AUTONOMER WATCHDOG – DAUERHAFTE AGENTENÜBERWACHUNG

Implementiere einen unabhängigen Watchdog-Dienst auf dem MA-HOME-Server.

Er soll ohne laufende LLM-Sitzung funktionieren.

Verwende möglichst deterministische Prüfungen und normale Systemprozesse.

### Heartbeat-System

Jeder aktive Spezialist meldet regelmäßig:

- Agent-ID
- Task-ID
- Status
- Laufende Operation
- Letzten Arbeitsschritt
- Letzten nachgewiesenen Fortschritt
- Aktuelle Blockaden
- Zeitpunkt der letzten Aktivität

Standardmäßiges Heartbeat-Prüfintervall: 30 Sekunden, konfigurierbar.

### Fortschrittskontrolle

Ein Heartbeat bedeutet nicht automatisch, dass gearbeitet wird.

Der Watchdog muss konkrete Arbeitsnachweise überprüfen.

Beispiele:

- Änderungen an Projektdateien
- Git-Diffs
- Neue Testergebnisse
- Datenbankänderungen
- Erzeugte Artefakte
- Erfolgreiche API-Aufrufe
- Abgeschlossene Teilaufgaben
- Neue Rechercheergebnisse
- Dokumentierte Architekturentscheidungen

Berücksichtige legitime lang laufende Operationen.

Ein Agent darf nicht wegen fehlender Dateiänderungen als inaktiv eingestuft werden, wenn er nachweislich eine Recherche oder Berechnung ausführt.

---

# 6. AUTOMATISCHE FEHLERERKENNUNG

Der Watchdog muss insbesondere erkennen:

1. Agent startet trotz angenommenem Auftrag nicht.
2. Agent hört mitten in der Arbeit auf.
3. Agent reagiert nicht mehr.
4. Agent produziert keinen sinnvollen Fortschritt.
5. Agent wiederholt identische Schritte.
6. Agent gerät in eine Endlosschleife.
7. Zwei Agenten delegieren Aufgaben ständig gegenseitig.
8. API-Limit oder Tokenbudget ist erreicht.
9. Modell antwortet nicht oder liefert wiederholt Fehler.
10. Benötigtes Tool funktioniert nicht.
11. Worker ist nicht erreichbar.
12. Serverdienst ist abgestürzt.
13. Datenbankverbindung ist verloren gegangen.
14. Datei- oder Berechtigungsproblem verhindert die Arbeit.
15. Agent verwendet einen ungeeigneten Lösungsweg.
16. Council-Dirigent reagiert nicht.
17. Aufgabe wurde nach einem Neustart vergessen.
18. Task-Abhängigkeiten bilden einen Deadlock.
19. Agent behauptet einen Erfolg ohne Nachweis.
20. Spezialist arbeitet an einer anderen als der zugewiesenen Aufgabe.

Jede erkannte Störung erzeugt einen persistenten Incident mit eindeutiger ID.

---

# 7. AUTONOMOUS SELF-HEALING – FEHLER SELBSTSTÄNDIG BEHEBEN

**Das Erkennen und Melden eines Problems reicht nicht aus.**

JARVIS soll erkannte Probleme innerhalb seiner Berechtigungen aktiv beheben.

Implementiere folgenden Recovery-Prozess:

### Phase 1 – Problem erkennen

Der Watchdog registriert die Störung.

Er speichert:

- Betroffenen Agenten
- Zugehörigen Auftrag
- Fehlerzustand
- Zeitpunkt
- Technische Hinweise
- Aktuellen Fortschritt

### Phase 2 – Ursachenanalyse

Der Recovery Manager untersucht:

- Prozesszustand
- Service-Logs
- Fehlermeldungen
- API-Antworten
- Modellverfügbarkeit
- Netzwerkverbindung
- Ressourcen
- Berechtigungen
- Abhängigkeiten
- Tool-Konfiguration
- Letzte erfolgreiche Operation

Er bestimmt die wahrscheinlichste Ursache und überprüft sie möglichst anhand technischer Nachweise.

### Phase 3 – Reparaturplan

Erstelle einen möglichst kleinen und sicheren Reparaturplan.

Bevorzuge gezielte Änderungen gegenüber vollständigen Neuinstallationen.

Berücksichtige Auswirkungen, Risiken und vorhandene Rollback-Möglichkeiten.

### Phase 4 – Automatische Reparatur

Führe geeignete autorisierte Maßnahmen selbstständig aus.

Beispiele:

- Abgestürzten Agenten neu starten
- Fehlgeschlagenen Task sicher wiederholen
- Fehlerhafte Worker-Verbindung wiederherstellen
- Einen abgestürzten Dienst neu starten
- Einen fehlerhaften Tool-Aufruf korrigieren
- Fehlenden Kontext aus der Datenbank wiederherstellen
- Einen geeigneteren Agenten auswählen
- Einen alternativen konfigurierten Modellprovider verwenden
- Abhängigkeiten neu auflösen
- Eine unterbrochene Aufgabe vom letzten Checkpoint fortsetzen
- Sichere und nachvollziehbare Konfigurationsfehler beheben
- Fehlgeschlagene Deployment-Schritte nach Prüfung wiederholen

Verändere keine Berechtigungen, Sicherheitsregeln oder Zugangsdaten, um Schutzmaßnahmen zu umgehen.

### Phase 5 – Reparatur überprüfen

Nach jeder Reparatur:

1. Ursprünglichen Fehler erneut prüfen.
2. Relevante Healthchecks durchführen.
3. Betroffene Tests ausführen.
4. Nachweisbaren Erfolg feststellen.
5. Nebenwirkungen untersuchen.
6. Ergebnis dokumentieren.

### Phase 6 – Arbeit fortsetzen

Bei erfolgreicher Reparatur:

- Incident als behoben markieren.
- Betroffenen Task wieder freigeben.
- Spezialisten erneut einsetzen.
- Am letzten sicheren Checkpoint fortsetzen.
- Doppelte Ausführung verhindern.
- Normale Überwachung wieder aufnehmen.

### Phase 7 – Wenn Reparatur fehlschlägt

Führe keine endlosen Wiederholungen aus.

Stattdessen:

- Reparaturstrategie überdenken
- Andere geeignete Spezialisten hinzuziehen
- Alternativen prüfen
- Fehlversuche begrenzen
- Bei Bedarf auf einen sicheren Zustand zurückrollen
- Ursache und verbleibende Hindernisse dokumentieren

Erst wenn keine sichere, zulässige und erfolgversprechende automatische Maßnahme möglich ist, wird der Auftrag eskaliert.

---

# 8. MEHRSTUFIGES RECOVERY-SYSTEM

Implementiere fünf Eskalationsstufen.

**LEVEL 1 – Automatic Retry**

Kurzzeitige Fehler automatisch behandeln.

Beispielsweise Timeouts, temporäre Verbindungsfehler oder sichere wiederholbare Operationen.

**LEVEL 2 – Agent Recovery**

Agenten kontrolliert neu starten, Kontext wiederherstellen oder Task vom Checkpoint fortsetzen.

**LEVEL 3 – Specialist Replacement**

Wenn der Spezialist wiederholt scheitert, einen anderen geeigneten Spezialisten beauftragen.

Dabei den bisherigen Ausführungsversuch sicher beenden oder isolieren.

**LEVEL 4 – Council Diagnosis**

Der Dirigent aktiviert bei Bedarf mehrere geeignete Spezialisten zur gemeinsamen Ursachenanalyse.

Der Council entscheidet über eine alternative Strategie.

**LEVEL 5 – Safe Escalation**

Falls automatische Reparaturen ausgeschöpft sind:

- Auftrag sichern
- Logs und Ergebnisse erhalten
- Sicheren Zustand herstellen
- Benutzer mit konkretem Problem und Lösungsmöglichkeiten informieren
- Auf notwendige Freigaben warten

Bei Sicherheitsvorfällen, irreversiblen Aktionen oder unklarer Autorisierung nicht erst sämtliche Stufen automatisch durchlaufen.

---

# 9. ANTI-STAGNATION- UND ANTI-LOOP-SYSTEM

Der Watchdog muss auch scheinbare Arbeit erkennen.

Beispiele:

- Agent erklärt ständig, was er machen wird.
- Agent erstellt immer wieder denselben Plan.
- Agent gibt Aufgaben zurück, ohne sie auszuführen.
- Agent wiederholt dieselben Tool-Aufrufe.
- Agent verschwendet Tokens ohne Fortschritt.
- Agent delegiert dieselbe Aufgabe mehrfach.

Implementiere:

- Stagnation Detection
- Deadlock Detection
- Loop Detection
- Retry Limits
- Circuit Breaker
- Exponential Backoff
- Task Timeout Policies
- Progress Verification

Timeouts sollen aufgabenspezifisch sein.

Lange Kompilierungen oder Berechnungen dürfen nicht unnötig abgebrochen werden.

**JARVIS soll tatsächliche Ergebnisse optimieren, nicht künstlich erzeugte Aktivität.**

---

# 10. PERSISTENZ, CHECKPOINTS UND AUTORECOVERY

Das System muss Neustarts überstehen.

Nach einem Neustart:

1. Zentrale Datenbank laden.
2. Gespeicherte Aufträge einlesen.
3. Laufende Prozesse und Agenten prüfen.
4. Unterbrochene Ausführungen identifizieren.
5. Letzte Checkpoints überprüfen.
6. Bereits ausgeführte Aktionen berücksichtigen.
7. Unvollständige Aufträge sicher fortsetzen.
8. Blockierte Aufgaben erneut bewerten.

Nutze:

- Persistente Task-IDs
- Ausführungs-IDs
- Checkpoints
- Transaktionale Statusänderungen
- Task-Leases mit Ablaufzeiten
- Idempotenzschlüssel für wiederholbare Aktionen
- Wiederherstellungsprotokolle

Verhindere, dass Aufgaben nach einem Absturz doppelt ausgeführt werden.

Das gilt besonders für externe Aktionen.

---

# 11. LANGZEITGEDÄCHTNIS UND OBSIDIAN

Integriere die bestehende Speicherarchitektur.

### PostgreSQL

Verbindliche Quelle für:

- Aufträge
- Pläne
- Checklisten
- Status
- Agentenzuweisungen
- Ausführungsverläufe
- Fehler
- Incidents
- Reparaturversuche
- Ergebnisse

### Obsidian

Menschlich lesbares Projektwissen:

- Projektübersichten
- Aufgabenhistorie
- Architekturentscheidungen
- Fehlerursachen
- Reparaturdokumentation
- Erfolgreiche Lösungsverfahren
- Wiederverwendbare Erkenntnisse

### JARVIS Memory

Der Council soll aus dokumentierten Problemen lernen.

Wenn ein ähnlicher Fehler erneut auftritt, soll das System zuerst bereits erfolgreich geprüfte Lösungen berücksichtigen.

Keine unkontrollierten Änderungen am Produktivsystem aufgrund ungeprüfter Erinnerungen.

---

# 12. INTELLIGENTES MODELLROUTING UND TOKENOPTIMIERUNG

Integriere das System vollständig in den bestehenden Smart Router und Hermes.

Der Watchdog soll überwiegend ohne LLM arbeiten.

Nutze lokale, deterministische Prüfungen für:

- Heartbeats
- Statuswechsel
- Healthchecks
- Prozessüberwachung
- Zeitüberschreitungen
- Checkpoints
- Datenbankkontrollen
- Wiederholungsmanagement

Aktiviere LLMs nur bei tatsächlichem Bedarf.

Der Smart Router entscheidet dann über:

- Geeignetes Modell
- Geeigneten Spezialisten
- Benötigte Tools und Skills
- Notwendige Reasoning-Tiefe
- Verfügbaren Kontext
- Kosten und Tokenbudget
- Lokale oder Cloud-Ausführung

Berücksichtige vorhandene Nexum-Router-, Claude- und lokale Modellkonfigurationen, soweit aktuell verfügbar.

Vermeide unnötige Premium-Modellaufrufe.

Komplexe Fehler sollen nicht automatisch zum teuersten Modell führen.

Nutze bevorzugt vorhandene Logs, Datenbankeinträge und kompakte Kontextzusammenfassungen.

---

# 13. INTERAKTIVES COUNCIL- UND WATCHDOG-DASHBOARD

Erweitere das bestehende JARVIS-Webportal um:

**JARVIS → Council → Mission Control**

Das Dashboard soll folgende Bereiche enthalten:

### A. Auftragszentrale

- Alle offenen Aufträge
- Aktive Arbeiten
- Aufgabenchecklisten
- Projektfortschritt
- Prioritäten
- Abhängigkeiten
- Zuständigkeiten
- Abgeschlossene Arbeiten

### B. Agentenüberwachung

- Alle Council-Spezialisten
- Aktuelle Aufgaben
- Heartbeat-Status
- Letzter tatsächlicher Fortschritt
- Aktuelle Modelle
- Tokenverbrauch
- Ressourcenverbrauch
- Blockaden

### C. Watchdog Monitor

- Erkannte Störungen
- Betroffene Spezialisten
- Eingeleitete Maßnahmen
- Reparaturfortschritt
- Erfolgreiche Wiederherstellungen
- Nicht behobene Probleme

### D. Recovery Center

- Aktive Incidents
- Fehlerursachen
- Reparaturpläne
- Ausgeführte Änderungen
- Tests
- Rollbacks
- Abschlussnachweise

### E. Animierte Agentenvisualisierung

Nutze das geplante interaktive JARVIS-Agenten-Dashboard.

Agenten sollen dort mit ihren tatsächlichen Aufgaben, Zuständen und Beziehungen visualisiert werden.

Die Darstellung kann sich an einer animierten digitalen Kommandozentrale orientieren.

Zeige:

- Welcher Spezialist woran arbeitet
- Wie Aufträge weitergegeben werden
- Welche Spezialisten miteinander kommunizieren
- Wo Störungen entstehen
- Wie der Recovery Manager eingreift
- Wann Arbeiten erfolgreich abgeschlossen werden

Die Animationen müssen durch echte Systemereignisse gesteuert werden.

Keine simulierten Erfolgsmeldungen.

Das Dashboard muss vollständig innerhalb des bestehenden Portals funktionieren, einschließlich Smartphone-Unterstützung.

---

# 14. NATÜRLICHE CHAT- UND SPRACHSTEUERUNG

JARVIS muss folgende Anweisungen verstehen:

- „Zeige alle offenen Aufträge.“
- „Welche Spezialisten arbeiten gerade?“
- „Warum arbeitet der Backend-Agent nicht?“
- „Was macht der Watchdog?“
- „Welche Probleme wurden heute behoben?“
- „Repariere die Störung.“
- „Setze die unterbrochene Aufgabe fort.“
- „Welche Aufträge hängen?“
- „Zeige den Fortschritt des Councils.“
- „Warum wurde dieser Auftrag noch nicht abgeschlossen?“
- „Welche Fehler treten wiederholt auf?“
- „Prüfe alle Agenten.“
- „Zeige die Reparaturhistorie.“

Alle Antworten müssen auf realen Daten beruhen.

---

# 15. AUTOMATISCHE PRIORISIERUNG

Der Dirigent soll regelmäßig die offenen Aufgaben bewerten.

Berücksichtige:

- Dringlichkeit
- Auswirkungen auf andere Aufgaben
- Projektziele
- Abhängigkeiten
- Verfügbare Spezialisten
- Serverressourcen
- Modellkosten
- Fehlerzustände
- Benutzerprioritäten

Blockierende Infrastrukturprobleme können vor weniger dringenden Entwicklungsarbeiten priorisiert werden.

Vermeide, dass dauerhaft neue Aufgaben begonnen werden, während ältere wichtige Aufträge liegen bleiben.

Berücksichtige Prioritätsalterung und begrenze parallele Arbeiten.

---

# 16. FEHLERBEHEBUNG ALS EIGENER AUFTRAG

Jede relevante Störung soll automatisch einen Reparaturauftrag erzeugen.

Dieser Reparaturauftrag bekommt:

- Eigene ID
- Verknüpfung zum ursprünglichen Auftrag
- Fehlerbeschreibung
- Ursachenanalyse
- Zuständigen Spezialisten
- Reparaturplan
- Checkliste
- Testkriterien
- Status
- Reparaturhistorie

Beispiel:

**INCIDENT-0042 – Frontend-Agent reagiert nicht**

- [x] Störung erkannt
- [x] Logs analysiert
- [x] Fehlerursache identifiziert
- [x] Wiederherstellungsplan erstellt
- [ ] Fehler beheben
- [ ] Agent erneut testen
- [ ] Ursprünglichen Auftrag fortsetzen
- [ ] Fortschritt verifizieren
- [ ] Incident abschließen

Reparaturaufträge dürfen nicht verloren gehen oder ohne Nachweis abgehakt werden.

---

# 17. SICHERHEIT UND AUTONOMIE

JARVIS soll Routineprobleme ohne ständige Benutzerinteraktion lösen.

Erlaubte automatische Maßnahmen müssen jedoch klar definiert und begrenzt sein.

Implementiere abgestufte Berechtigungen für:

- Prozessneustarts
- Task-Wiederholungen
- Agentenwechsel
- Änderungen an ungefährlichen Konfigurationen
- Updates
- Deployments
- Systemänderungen

Für potenziell destruktive, irreversible, kostenpflichtige oder sicherheitskritische Aktionen müssen die entsprechenden Freigaben eingehalten werden.

Keine eigenmächtige Umgehung von Schutzmechanismen.

Vor riskanten Reparaturen nach Möglichkeit Backups oder Rollback-Punkte erstellen.

Lege globale Limits für Kosten, parallele Reparaturen und Wiederholungsversuche fest.

Ein Recovery-Mechanismus darf niemals selbst eine unkontrollierte Fehler- oder Kostenspirale verursachen.

---

# 18. WATCHDOG-SELBSTÜBERWACHUNG

Verhindere einen Single Point of Failure.

Überwache insbesondere:

- Watchdog-Prozess
- Recovery Manager
- Council-Dirigent
- Task-Datenbank
- Task-Queue
- Kritische Schnittstellen

Nutze dafür passende Betriebssystemmechanismen wie systemd, sofern kompatibel.

Eine einfache externe oder unabhängige Healthcheck-Komponente soll erkennen, wenn der Watchdog nicht mehr funktioniert.

Bei Ausfall müssen verfügbare sichere Wiederherstellungsmechanismen greifen.

---

# 19. REALITÄTSCHECK UND ABNAHMETESTS

Die Implementierung gilt erst als vollständig, wenn reale Tests bestanden wurden.

Mindestens folgende Szenarien prüfen:

1. Ein neuer Prompt wird dauerhaft gespeichert.
2. Der Dirigent erstellt einen nachvollziehbaren Plan.
3. Ein Spezialist übernimmt einen Auftrag.
4. Der Watchdog erkennt fehlenden Fortschritt.
5. Ein inaktiver Agent wird korrekt diagnostiziert.
6. Eine kontrollierte Wiederherstellung funktioniert.
7. Ein fehlerhafter Spezialist wird sicher ersetzt.
8. Ein abgestürzter Dienst wird wiederhergestellt.
9. API-Limits führen nicht zu Endlosschleifen.
10. Ein unterbrochener Auftrag wird fortgesetzt.
11. Ein Serverneustart verursacht keinen Aufgabenverlust.
12. Eine bereits ausgeführte Aktion wird nicht doppelt ausgeführt.
13. Checklisten werden korrekt aktualisiert.
14. Fehlerbehebungen werden überprüft.
15. Obsidian erhält konsistente Dokumentationen.
16. Das Dashboard zeigt reale Zustände.
17. Der unabhängige Supervisor erkennt den Ausfall des Watchdogs.
18. Das System bleibt innerhalb seiner Ressourcen- und Kostenlimits.
19. Nicht automatisch lösbare Fehler werden korrekt eskaliert.
20. Abgeschlossene Aufträge haben überprüfbare Erfolgskriterien erfüllt.

Dokumentiere Testergebnisse und eventuelle Einschränkungen.

Keine Erfolgsmeldungen ohne Nachweise.

---

# 20. UMSETZUNGSREIHENFOLGE

Arbeite den Auftrag eigenständig in dieser Reihenfolge ab:

**P0 – Bestandsaufnahme**

Aktuelle Architektur, Agenten, Speicher, Queues und bestehende Auftragsverwaltung prüfen.

**P1 – Persistente Auftragsverwaltung**

Zentrale Datenbank, Statusmodell, Checklisten und Auftrags-IDs integrieren.

**P2 – Council-Dirigent**

Planung, Delegation, Priorisierung und Statusabfragen anbinden.

**P3 – Watchdog**

Heartbeat-System, Fortschrittsprüfung, Stagnationserkennung und Systemüberwachung implementieren.

**P4 – Recovery Manager**

Automatische Diagnose, sichere Reparatur, Wiederaufnahme, Agentenersatz und Eskalation integrieren.

**P5 – Langzeitgedächtnis**

PostgreSQL, Obsidian und bestehende Memory-Funktionen verknüpfen.

**P6 – Mission Control Dashboard**

Auftragsverwaltung, Agentenstatus, Watchdog und Recovery Center in das Portal integrieren.

**P7 – Effizienzoptimierung**

Deterministische Prüfungen, Smart Routing, geringe Tokenkosten und effiziente Ressourcennutzung sicherstellen.

**P8 – End-to-End-Tests**

Fehlerfälle simulieren, Wiederherstellungsmechanismen testen und reale Fortschrittsnachweise prüfen.

**P9 – Produktivintegration**

Nach bestandenen Tests sicher ausrollen, überwachen und dokumentieren.

Jede Phase muss als persistenter Auftrag mit überprüfbaren Teilaufgaben angelegt werden.

---

# 21. ABSCHLIESSENDE DAUERREGEL

Ab sofort soll das gesamte JARVIS-System nach folgendem Prinzip arbeiten:

**Jeder Auftrag wird gespeichert.**

**Jeder Auftrag bekommt einen Plan.**

**Jeder Plan erhält überprüfbare Teilaufgaben.**

**Jede Teilaufgabe erhält einen verantwortlichen Spezialisten.**

**Jeder aktive Spezialist wird überwacht.**

**Jeder fehlende Fortschritt wird untersucht.**

**Jede erkannte Störung erhält einen Reparaturauftrag.**

**Jede sicher behebbare Störung soll automatisch behoben werden.**

**Jede Reparatur wird anschließend überprüft.**

**Jeder unterbrochene Auftrag soll sicher fortgesetzt werden.**

**Jede erfolgreich abgeschlossene Teilaufgabe wird abgehakt.**

**Jeder offene Auftrag bleibt bis zum nachweislichen Abschluss oder bewussten Abbruch erhalten.**

**Jede wichtige Entscheidung, Änderung und Fehlerbehebung wird dokumentiert.**

Der Dirigent trägt die organisatorische Gesamtverantwortung.

Der Watchdog stellt die kontinuierliche Überwachung sicher.

Der Recovery Manager behebt technische Probleme innerhalb seiner Autorisierung.

Die Spezialisten führen die eigentliche Arbeit aus.

JARVIS stellt sämtliche Informationen zentral bereit.

## LETZTE ANWEISUNG

Setze dieses System so weit wie technisch und sicher möglich autonom in der bestehenden MA-HOME-JARVIS-Architektur um.

**Beende die Arbeit nicht bereits nach der Planung, nach einer Fehlererkennung oder nach einer bloßen Erfolgsmeldung.**

Führe die Umsetzung, erforderliche Reparaturen, Tests und Verifikation tatsächlich durch.

Wenn ein Schritt fehlschlägt, untersuche die Ursache, versuche eine geeignete sichere Fehlerbehebung und setze anschließend die Arbeit fort.

Wenn ein Problem nicht automatisch behoben werden kann, dokumentiere den konkreten Grund, sichere den Zustand und eskaliere gezielt.

Bestehende funktionierende Komponenten sollen erhalten bleiben.

Ziel ist ein dauerhaft stabiles, effizientes, tokensparendes, selbstüberwachendes und möglichst selbstheilendes JARVIS-System, das angenommene Aufgaben zuverlässig bis zum überprüften Ergebnis verfolgt.
