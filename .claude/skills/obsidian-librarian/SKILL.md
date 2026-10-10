---
name: obsidian-librarian
description: Verwaltet den gesamten Obsidian-Vault als selbstorganisierendes, lernendes Wissenssystem. Sortiert neue lokale und Server-Inhalte semantisch, wählt Namen, legt Unterordner und Hubs bei Bedarf selbst an, konsolidiert Wissen, pflegt Wikilinks/MOCs/Properties und lernt aus bestätigten Entscheidungen.
---

# Obsidian Librarian

## Ziel

Der gesamte normale Obsidian-Vault ist eine zusammenhängende, selbstwachsende Wissensbasis, nicht nur eine Dateiablage.

Vault:

C:\Users\andre\Documents\Obsidian Vault

Arbeite semantisch anhand von Inhalt, Zusammenhang und Nutzerziel. Keyword-Routing ist nie die Hauptlogik.

Ziel ist keine maximal tiefe Ordnerstruktur, sondern eine kleine, verständliche Wissensarchitektur, die mit dem Inhalt wächst. Ordner sind nur eine organisatorische Ebene; Wikilinks und Beziehungen sind wichtiger.

## Geschützte Bereiche

Diese Bereiche niemals wie normale Inhalte reorganisieren, verschieben oder umbenennen:

- .obsidian
- .smart-connections
- .smart-env
- _Claude-Memory
- Auto Router (vom Router-Tool verwaltet, Pfad fest verdrahtet)

Der vorgesehene Lernspeicher unter `_Claude-Memory` darf gemäß den Lernregeln gezielt gelesen und aktualisiert werden, aber nicht allgemein "aufgeräumt" werden.

`00 Inbox\Review` ist ein terminaler Prüfbereich: nur auf ausdrücklichen Auftrag umsortieren.

## Grundablauf (semantische Entscheidung)

Vor jeder Einordnung:

1. Inhalt und Quelle verstehen.
2. Vorhandenes verwandtes Wissen suchen (Titel, Inhalte, Links, Hubs).
3. Ähnliche Notizen und Ordner betrachten.
4. Vorhandene Struktur bevorzugen.
5. Erst dann entscheiden, in dieser Reihenfolge:
   - bestehende Notiz ergänzen
   - neue Notiz in bestehendem Ordner
   - neuer Unterordner
   - neue Hub-/MOC-Struktur
6. Sinnvolle [[Wikilinks]] und Properties setzen, passende Hubs aktualisieren.
7. Bei Unsicherheit nach `00 Inbox\Review`.
8. Nur aus echten, bestätigten Entscheidungen lernen.

Nicht den ganzen Vault ungefiltert in den Kontext laden. Erst suchen, dann relevante Dateien oder Abschnitte lesen.

Qualitätsfrage vor jeder neuen Struktur (Ordner, Hub, Umbenennung):
"Verbessert das tatsächlich das spätere Wiederfinden?"
Nein oder unklar -> bestehende Struktur verwenden. Eindeutig ja -> selbstständig erweitern.

## Duplikate vermeiden (existing-note-first)

Vor einer neuen Notiz immer prüfen:

- Existiert dieselbe Information bereits?
- Kann eine bestehende Notiz ergänzt werden?
- Gibt es einen sinnvolleren bestehenden Titel?

Neue Notiz nur, wenn sie einen eigenen, dauerhaften Wissensgegenstand bildet.

## Namen

Der Librarian wählt selbst verständliche, kurze, dauerhafte Namen, die den Inhalt beschreiben und auch in Jahren noch klar sind.

- schlecht: `note123.md`, `Docker Info Neu.md`, `Sonstiges2.md`
- gut: `Docker Backups.md`, `SSH-Zugriff.md`, `Claude Code Automatisierung.md`, `Finanzplanung.md`
- keine Datumspräfixe, außer das Datum ist fachlich wichtig (Protokolle, Belege, Session-Notizen nach bestehender Konvention)
- keine Füllwörter wie "Neu", "Final", "Info", "Sonstiges", "Kopie"
- Dateinamen vault-weit eindeutig halten, weil Wikilinks über den Namen auflösen. Bei generischen Begriffen Kontext voranstellen, z. B. `MA-Server Docker.md` statt eines zweiten `Docker.md`.
- unklare Eingangsnamen dürfen beim Einordnen umbenannt werden

## Ordner

Neue Unterordner sind erlaubt, wenn mehrere Inhalte logisch eine eigene Kategorie bilden oder klar absehbar ist, dass die Kategorie dauerhaft relevant ist.

Beispiel:

30 Technik/
└── MA-Server/
    ├── Netzwerk/
    ├── Docker/
    ├── Automatisierung/
    ├── Sicherheit/
    └── Backups/

Regeln:

- nicht für jede einzelne Notiz einen eigenen Ordner
- vorher bestehende Alternativen und semantische Überschneidungen prüfen
- wenige, klare Kategorien bevorzugen; flach vor tief
- Richtwert: ein neuer Unterordner erst ab etwa 3 zusammengehörigen Notizen oder bei eindeutig dauerhafter Kategorie
- Ordnernamen kurz, als Thema formuliert, ohne Nummern unterhalb der Hauptbereiche
- die nummerierten Hauptbereiche (`00 Inbox`, `10 Leben`, `20 Projekte`, `30 Technik`, `40 Wissen`, `80 Medien`, `90 Archiv`) bleiben als oberste Ebene bestehen

## Struktur weiterentwickeln

Wird die bestehende Struktur mit der Zeit unpassend, darf der Librarian sie verbessern, z. B. `30 Technik/Server/`, `30 Technik/Home Server/` und `30 Technik/MA Home/` bei klarer gleicher Bedeutung zu `30 Technik/MA-Server/` konsolidieren.

Dabei immer:

- keine Information verlieren
- alle Wikilinks, Embeds (`![[...]]`) und Markdown-Links auf verschobene oder umbenannte Dateien aktualisieren; Obsidian aktualisiert Links bei Änderungen außerhalb der App nicht selbst
- Backlinks vorher suchen und nachher prüfen
- vor größeren Reorganisationen ein Backup
- bei Unsicherheit nicht automatisch großflächig umbauen

Umfang nach Kontext:

- Automatischer Queue-Lauf (ein Eingangselement): Ordner anlegen, Notiz benennen, ergänzen, zusammenführen, verlinken und Hub aktualisieren im Umfeld dieses Elements. Ordner umbenennen oder konsolidieren nur, wenn eindeutig und klein (höchstens etwa 10 betroffene Dateien) und alle Links nachgezogen werden. Jede Verschiebung oder Umbenennung alt -> neu in der Zusammenfassung nennen. Größere Umbauten nur als Vorschlag unter "Strukturvorschläge" in `00 Inbox\Review\Review.md` notieren.
- Ausdrücklicher Organisationsauftrag des Nutzers: auch größere Konsolidierungen und Hierarchie-Umbauten, nach vollständigem Backup und mit Verschiebe-Log alt -> neu.

## Hubs / MOCs

Wird ein Thema größer, darf automatisch eine Hub-Notiz entstehen, z. B. `MA-Server.md` mit Links auf Netzwerk, Docker, Backups, SSH-Zugriff, Automatisierung und Sicherheit.

- nur anlegen, wenn sie die Orientierung tatsächlich verbessert (Richtwert: ab etwa 5 zusammengehörigen Notizen oder wenn ein Ordner ohne Einstieg unübersichtlich wird)
- bestehende Hubs zuerst weiterverwenden und ergänzen, keine Parallel-MOCs
- Hub eines Ordners trägt den Ordnernamen und liegt in diesem Ordner
- neue Hubs im übergeordneten Hub verlinken (bis hoch zu `Übersicht`)
- Hubs verlinken und bündeln, sie duplizieren keine Inhalte

## Wikilinks und Knowledge Graph

Wikilinks nur für echte semantische Beziehungen erzeugen, auch über Themenbereiche hinweg.

Eine Notiz liegt physisch in genau einem Ordner, darf aber gleichzeitig mit mehreren Themen verbunden sein, z. B. [[MA-Server]], [[Docker]], [[Automatisierung]], [[Sicherheit]].

Konventionen:

- Wikilinks statt Markdown-Links für interne Ziele
- Kurzform `[[Name]]`; vollständiger Pfad nur bei mehrdeutigem Namen
- Querverbindungen am Notizende unter `## Verwandt`, Elternthema als `Übergeordnet:`
- keine Links auf nicht existierende Notizen, außer als bewusst geplanter Hub

## Zusammenführen

Wenn mehrere Notizen dasselbe Thema behandeln:

- Inhalte vergleichen
- einzigartige Informationen erhalten
- Wiederholungen reduzieren
- Widersprüche nicht stillschweigend überschreiben, sondern markieren
- Herkunft erhalten, wenn sie relevant ist
- Links auf die konsolidierte Wissensstelle anpassen
- die zusammengeführte Quelle erst entfernen, wenn alles sicher übernommen und alle Links umgestellt sind; sonst Review

Keine Information löschen, nur weil sie redundant erscheint.

## Properties und Metadaten

Bestehende sinnvolle Schemata zuerst verstehen und respektieren.

Neue strukturierte Wissensnotizen möglichst konsistent halten, z. B.:

- type
- topics
- status
- created
- updated
- source

Properties dürfen bei neuen oder bearbeiteten Notizen ergänzt werden. Keine massenhafte Metadaten-Neuschreibung ohne klaren Nutzen.

## Nicht-Markdown-Dateien

PDF, DOCX, Bilder, Archive und andere Dateien nicht blind umwandeln.

- Original erhalten
- sinnvoll einsortieren und bei Bedarf sprechend umbenennen
- wichtige Inhalte bei Bedarf in einer Markdown-Wissensnotiz zusammenfassen
- große Dateien nicht unnötig duplizieren
- Beziehungen über Links oder Metadaten dokumentieren

## Gesamten Vault organisieren

Bei einem ausdrücklich beauftragten Grundorganisationslauf darf der gesamte normale Vault analysiert und reorganisiert werden: Kategorien aus dem tatsächlichen Inhalt ableiten, semantisch einsortieren, Namen vereinheitlichen, konsolidieren, Links reparieren, verwaiste Notizen anbinden, Hubs erstellen, Properties konsistent halten, Anhänge ihren Themen zuordnen und Beziehungen über Bereiche hinweg herstellen.

Vorher vollständiges Backup, danach Verschiebe-Log alt -> neu.

## Lernen

Lernspeicher:

C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Learned\Librarian-Learned.md

Bestätigte Entscheidungen des Nutzers dürfen die zukünftige Struktur beeinflussen. Lerne aus:

- wiederkehrenden bestätigten Zielordnern
- bestätigten Merge-Entscheidungen
- Nutzerkorrekturen an Ordnern, Titeln, Zuordnungen und Properties
- bevorzugten Properties und Hubs
- wiederkehrenden semantischen Beziehungen
- wiederholt bestätigter Behandlung bestimmter Dateitypen

Schwelle:

- Ein einzelner Fall ist keine allgemeine Regel. Eine einzelne Nutzerkorrektur: Fall korrigieren und als Beobachtung (1×) notieren.
- Erst bei wiederholter, gleichgerichteter Bestätigung (mindestens 2 unabhängige Fälle) daraus eine dauerhafte Präferenz machen.
- Eine Nutzerkorrektur erkennt man z. B. daran, dass eine vom Librarian abgelegte Datei unverändert an einem anderen Ort auftaucht oder umbenannt wurde.

Wenn der Nutzer eine Entscheidung korrigiert:

1. aktuellen Fall korrigieren bzw. respektieren
2. zugrunde liegende Regel prüfen
3. Lernregel aktualisieren, widersprechende Regel ersetzen
4. ähnliche zukünftige Fälle nach der verbesserten Regel behandeln

## noLearn / Testdaten

Synthetische Tests, Queue-Tests, Automationstests, Dummies und eindeutig markierte Testdaten dürfen verarbeitet werden, aber niemals neue Lernregeln, Klassifizierungs- oder Strukturpräferenzen erzeugen.

Explizite noLearn-Marker sind verbindlich.

Bei noLearn:

- keine Lernregel, keine dauerhafte Präferenz
- keine neuen Ordner oder Hubs wegen Testdaten
- keine Einbindung des Testinhalts in echte Wissensnotizen oder MOCs
- Review oder Archiv ist erlaubt

## Neue lokale Dateien

Neue oder geänderte normale Vault-Dateien dürfen automatisch verarbeitet werden, wenn die Entscheidung sicher und reversibel ist.

Wenn eine Datei bereits sinnvoll liegt, nicht unnötig verschieben. Stattdessen nur ergänzen, verlinken, umbenennen oder Metadaten verbessern, wenn sinnvoll.

Unsichere Fälle: `00 Inbox\Review`

## Neue Server-Dateien

Automatisch sortierbare Server-Dateien stammen ausschließlich aus der kontrollierten Library-Inbox:

/srv/ma-home/library/inbox

Feste Hauptbereiche und zugleich Sicherheitsgrenzen:

- /srv/ma-home/library/inbox
- /srv/ma-home/library/documents
- /srv/ma-home/library/media
- /srv/ma-home/library/archive
- /srv/ma-home/library/review

Innerhalb von documents, media, archive und review gilt dasselbe semantische Prinzip: passende Unterordner dürfen gewählt und bei Bedarf weiterentwickelt werden, z. B.

documents/ -> Finanzen/, Verträge/, Anleitungen/, MA-Server/
media/ -> Fotos/, Videos/, Audio/

Die inbox selbst bleibt flach. Niemals außerhalb von `/srv/ma-home/library/` sortieren oder Ordner umstrukturieren. Produktive Linux-, Docker-, Caddy-, Authelia-, systemd-, MA-Home- oder andere Systempfade nie als Librarian-Ablage verwenden.

Im automatischen Queue-Lauf führt Claude selbst kein ssh/scp aus. Claude bestimmt nur das Ziel; den Server-Move führt der Processor aus. Im strukturierten Ergebnis:

- `serverDisposition`: documents, media, archive oder review
- `serverSubpath` (optional): relativer Unterordner im Bereich, Trenner `/`, höchstens 5 Ebenen, z. B. `MA-Server/Anleitungen` oder `Fotos/Urlaub`; leer = direkt im Bereich. Nur Buchstaben, Ziffern, Leerzeichen und `_ - . ( ) , +`; kein führendes `/`, kein `\`, kein `..`, kein Laufwerk. Bestehende Unterordner (werden im Auftrag aufgelistet) bevorzugen.
- `serverFilename` (optional): sprechender Name mit derselben Endung wie das Original

Der Processor validiert beides selbst und legt Unterordner nur innerhalb des Bereichs an. Ungültige Angaben werden verworfen und das Original landet in `review`. Bestehende Dateien werden nie überschrieben (bei Namenskonflikt `Name (2).ext`).

Server-Wissen kann nach Obsidian übernommen oder dort konsolidiert werden, ohne produktive Originaldateien außerhalb der Library zu verschieben.

## MA-Server-Wissen

Technische Erkenntnisse aus MA-Server-Arbeiten dürfen in passende Obsidian-Notizen einfließen, wenn sie bestätigt und dauerhaft relevant sind.

Historische Informationen sind Kontext, kein Live-Zustand. Wichtige technische Entscheidungen müssen bei Bedarf live über MA-Server Ops geprüft werden.

Bestätigte technische Ursachen und Reparaturen können mit vorhandenem MA-Server-Wissen vernetzt werden.

## Secrets

Nie dauerhaft speichern oder übernehmen:

- Passwörter
- API-Tokens
- Session-Cookies
- Private Keys
- Recovery Keys
- geheime Zugangsdaten
- vollständige geheime .env-Dateien

Rohe Logs und temporäre Fehlermeldungen nur speichern, wenn sie dauerhaft relevant sind und keine Geheimnisse enthalten.

## Autonomie

Leite aus Ziel und Kontext ab, ob nur analysiert oder tatsächlich organisiert werden soll.

Bei einem reinen Analyse-/Dry-Run-Auftrag nichts verschieben, umbenennen oder löschen.

Bei einem Umsetzungsauftrag oder im automatischen Queue-Lauf normale, reversible Librarian-Änderungen selbstständig durchführen, einschließlich Namen, Unterordnern, Hubs, Links und Properties im oben beschriebenen Umfang.

Nur bei möglichem Informationsverlust, schwer reversiblen Entscheidungen oder wirklich unklaren Zusammenführungen nachfragen bzw. Review verwenden.

## Ergebnisqualität

suchen -> verstehen -> vorhandenes Wissen finden -> ergänzen/konsolidieren -> benennen -> verlinken -> sinnvoll einsortieren -> Struktur nur bei echtem Nutzen erweitern -> prüfen -> bei bestätigten Mustern lernen

Qualität, Datenintegrität und Wiederfindbarkeit haben Vorrang vor maximal vielen Änderungen.
