# MA Home – Aufgaben verstehen und sparsam bearbeiten

Stand: 2026-10-05, Europe/Berlin. Ergänzt AGENTS.md; keine Serveränderung.
Diese Regeln verringern vermeidbaren Aufwand. Tokenersparnis, Geschwindigkeit und Fehlerfreiheit sind nicht garantiert. Die Datei schaltet kein Modell um und aktiviert keine Plugins.

## 1. Auftrag aus dem Kontext ableiten

- Ermittle Ziel, gewünschtes Ergebnis, Einschränkungen und Fertig-Kriterium. Nutze dafür die aktuelle Nachricht und den relevanten Projektkontext.
- Interpretiere offensichtliche Tippfehler und kurze Antworten wie „ja, mach“ im Zusammenhang mit dem unmittelbar zuvor angebotenen Arbeitsschritt.
- Bewahre ausdrückliche Nutzerentscheidungen; leite keine zusätzlichen Funktionen oder Servereingriffe aus vagen Formulierungen ab.
- Stelle nur bei einer entscheidenden Informationslücke eine kurze, gebündelte Rückfrage. Unabhängige autorisierte Arbeit weiterführen. Routineentscheidungen selbst treffen; folgenreiche Annahmen knapp benennen.
- Kein ausführliches Umschreiben jedes Prompts. Bei komplexen Aufgaben reicht ein Satz zu Ziel und Umfang.

## 2. Aufwand an die Aufgabe anpassen

| Aufgabe | Vorgehen | Prüfung |
|---|---|---|
| Erklärung oder Zusammenfassung | Direkt mit vorhandenen Belegen beantworten | Aussage gegen relevante Quelle prüfen |
| Kleine reversible Änderung | Betroffene Stelle lesen, gezielt ändern | Passende Syntax- oder Funktionsprüfung |
| Fehler mit unklarer Ursache | Wenige unterscheidende Diagnosen, Hypothese aktualisieren | Ursprünglichen Fehler reproduzieren und erneut prüfen |
| Größere Funktion oder Integration | Kurzer Plan, Abhängigkeiten klären, in Teiländerungen umsetzen | Betroffenen Benutzerablauf und Sicherheitsgrenzen prüfen |
| Rechte, Auth, Firewall oder Datenmigration | Belege, Umfang und Rückweg konkret klären | Risikoangemessene Prüfung; Schutzregeln aus AGENTS.md erhalten |

Kürze keine notwendigen Sicherheits-, Funktions- oder Wiederherstellungsprüfungen allein zum Tokensparen.

## 3. Kontext und Werkzeuge sparsam nutzen

- Pflichtlektüre nach AGENTS.md beachten; übrige Dokumente nur für die konkrete Aufgabe hinzuziehen.
- Bereits gelesene unveränderte Inhalte innerhalb der Sitzung wiederverwenden. Bei neuem Stand oder fehlenden Informationen gezielt nachlesen.
- Erst Dateinamen und relevante Stellen suchen, dann begrenzte Ausschnitte lesen. Keine kompletten Repositories oder ungekürzten Logs in den Kontext laden.
- Unabhängige lesende Abfragen bündeln; begrenzte Ausgaben verwenden und relevante Fehler nicht abschneiden.
- Vorhandene Lösung gezielt ergänzen. Keine komplette Neufassung für einen lokalen Fehler.
- Werkzeuge, Plugins und Skills nach tatsächlichem Bedarf einsetzen. Keine Katalogsuche pro Aufgabe.
- Keine Subagenten ohne ausdrückliche Anforderung gemäß AGENTS.md. Bei autorisierter Delegation nur benötigten Kontext übergeben und Zuständigkeiten trennen.
- Tests nach neuen Änderungen, Fehlern oder offenen Risiken wiederholen; erfolgreiche unveränderte Prüfungen nicht grundlos erneut ausführen.

## 4. Modellwahl nur bei tatsächlicher Unterstützung

- Ohne verfügbare Routing-Funktion im aktuellen Modell arbeiten; keine erfolgte Modellumschaltung behaupten.
- Falls Modellwahl autorisiert und technisch verfügbar ist: das günstigste/schnellste Modell verwenden, das die konkreten Anforderungen nachweislich erfüllt.
- Bei unzureichendem Ergebnis zuerst fehlende Belege oder den Auftrag präzisieren. Für nachgewiesene Komplexität ein stärkeres Modell erwägen und nur den benötigten Kontext übergeben.
- Routing-Konfiguration, zusätzliche Kosten oder externe Datenweitergabe nicht ungefragt einrichten. ECC und llm-routing nicht allein wegen ihrer Erwähnung als aktiv behandeln.
- Tatsächlichen Verbrauch nur mit verfügbaren Messdaten beziffern. Keine erfundenen Einsparprozente oder Credits nennen.

## 5. Ergebnis und Projektwissen knapp halten

- Antworte mit Ergebnis, relevanter Prüfung, Einschränkung und nächstem nötigen Schritt. Keine Wiederholung des gesamten Plans oder Gesprächsverlaufs.
- Tabellen nur für echte Vergleiche; Code vollständig genug zum sicheren Ausführen, mit passender Shell.
- Dokumentiere ausgeführte Änderungen, bereitgestellten Code und offene Hypothesen getrennt nach AGENTS.md.
- Aktualisiere nur betroffene Dokumente und die Übergabe. Fakten an ihrer führenden Stelle halten; an anderen Stellen verweisen.
- Fehlende Serverbelege als offen kennzeichnen. Eine kurze Antwort darf keinen ungeprüften Erfolg suggerieren.

## Einbindung

Als Projektquelle hochladen und im lokalen MA-Home-Projektstamm neben AGENTS.md ablegen. Damit lokale Codex-Sitzungen sie berücksichtigen, diesen Verweis in AGENTS.md aufnehmen:

> Lies ergänzend TASK-POLICY.md und passe Kontextumfang, Werkzeuge und Prüfungen an die konkrete Aufgabe an. Bestehende Sicherheits- und Dokumentationsregeln bleiben verbindlich.

Die neue Datei wird nicht automatisch auf PC oder Server übertragen.
