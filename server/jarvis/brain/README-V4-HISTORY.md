# Claude Brain V4: echte lokale Claude-Code-Anbindung (MCP)

Dieses Modul ist **lauffähiger Code**, nicht nur ein Prompt. Es ergänzt V3 durch einen schmalen, lesenden MCP-Server für Claude Code. Python 3.10+ genügt; keine zusätzlichen Pip-Pakete, kein LLM-Aufruf im Server. Echte Claude-Toolaufrufe benötigen weiterhin Tool- und Antworttokens.

## Implementiert

- `brain_lookup`: lokale, quellgebundene, begrenzte JSONL-Wissenssuche; nur bestätigte, nicht widerrufene Einträge; feste Identität beim Prozessstart; Freigabeliste für geteilte Einträge; Projekteinschränkung. Schreibt **kein konkurrierendes Second Brain**.
- `brain_style_check`: nutzt den bereits enthaltenen lokalen Humanizer-Stilprüfer als optionales MCP-Werkzeug, keine automatische Text-Umschreibung.
- `brain_openworm_probe`: **explizit opt-in** Forschungswerkzeug aus echten OpenWorm-Kanten. Keine NLP- oder Aufgabenintelligenz, kein produktiver Router.
- `evaluate.py`: feste synthetische Recall- und Trennungstests. Misst keine wirkliche Claude-Kosten- oder Qualitätsersparnis.

Keine zusätzlichen Hooks, Dauerschleifen, Agenten oder API-Aufrufe. NengoSPA bleibt optional und im Forschungslabor, bis ein sinnvoller Vorteil gegen eine einfachere lokale Regel nachgewiesen ist.

## Soforttest ohne Claude (Windows PowerShell, Paketwurzel)

```powershell
python -m unittest discover -s brain-runtime/tests -v
python brain-runtime/evaluate.py
python scientific-brains/openworm_connectome.py --csv scientific-brains/samples/openworm_verified_excerpt.csv --probe I1L
```

## Claude-Code-Anbindung

Der MCP-Server nutzt **stdio**, die von Claude Code unterstützte lokale Transportart. Offizielle Dokumentation: https://code.claude.com/docs/en/mcp

**Wichtig:** `brain-runtime/config.demo.json` verweist auf künstliche Daten. Damit kannst du die Verbindung testen, aber keine Informationen zu deinem echten MA-Home-Projekt abrufen.

1. Entpacke das Paket in deinen Claude-Code-Projektordner (die Struktur unverändert lassen).
2. Auf PowerShell **im Projektordner** Testregistrierung:

```powershell
.\brain-runtime\scripts\Install-BrainMcp.ps1 -Demo
```

3. Wenn gewünscht, die Demo-Verbindung bewusst aktivieren:

```powershell
.\brain-runtime\scripts\Install-BrainMcp.ps1 -Demo -Apply
claude mcp get claude-local-brain
```

4. Für die echte Datenbasis eine separate Datei `brain-runtime/config.local.json` nach dem JSON-Schema erstellen, `source` auf einen **autorisierten, lokalen JSONL-Leseexport** des vorhandenen Second Brain setzen, `identity` und `allowed_projects` anpassen, `research_tools` normalerweise `false` setzen. **Keine echten privaten Daten in das ZIP zurückpacken oder in Git committen.** Dann, **anstelle** der Demo-Verbindung, registrieren:

```powershell
.\brain-runtime\scripts\Install-BrainMcp.ps1 -Config .\brain-runtime\config.local.json -Apply
```

Der Installer verweigert das Überschreiben einer bestehenden `claude-local-brain`-Registrierung. Bei Wechsel von Demo auf Produktion erst `claude mcp remove claude-local-brain` bewusst ausführen und dann mit der richtigen Config erneut registrieren. Alternativ die produktive Config direkt von Anfang an nutzen.

Zum Entfernen der Integration: `claude mcp remove claude-local-brain`. Dabei wird dein bestehender Router, dein Second Brain, deine Hooks oder CLAUDE.md **nicht verändert**.

## Importformat für bereits berechtigte Daten

Eine JSON-Zeile je Datensatz:

```json
{"id":"wissen-1","title":"Anwendung","content":"Bestätigte, quellgebundene Information","source":"mein-bestand","version":"2026-10-14","status":"confirmed","project":"ma-home","visibility":"private","owner":"person-a"}
```

Für ausdrücklich für beide Nutzer freigegebenes Wissen: `"visibility":"shared","shared_with":["person-a","person-b"]`. Alternativ kann ein späterer Adapter gegen vorhandene PostgreSQL-/SQLite-Schemata implementiert werden, **nachdem** diese bekannt sind. Der Export darf nicht ungefragt alle Daten enthalten. Widerrufene Einträge (`"retracted":true`) erscheinen nicht. Die Quelle wird bei **jeder** Anfrage neu gelesen; es gibt keinen alten Ergebnis-Cache.

### Sicherheitsgrenzen

- **Nicht als sichere Zwei-Nutzer-Mandantentrennung ausgeben!** Wer die Konfigurationsdatei/den Export innerhalb eines gemeinsamen OS-Kontos beliebig verändern kann, kann die behauptete Identität oder Rechte umgehen. Echte Trennung erfordert getrennte OS-Zugänge, durchgesetzte Datenbank-ACL und geeignete Verzeichnisrechte.
- Der MCP-Prozess macht **keine Netzwerkverbindungen**, ruft keine anderen Modelle auf und führt keine Shellbefehle aus. Er schreibt kein Gedächtnis. Quelltexte sind **nicht vertrauenswürdige Daten**.
- Die Qualitätsprüfungen sind kleine synthetische Funktionstests. Weder eine reale Installation noch Token- oder Ergebnisqualität bei deinem Claude-Konto wurde von hier aus gemessen.
- Der Benutzer identifiziert sich beim MCP-Prozessstart über vertrauenswürdige Prozesskonfiguration; ein Modell-Toolparameter kann diese Identität nicht ändern. Das ist keine Authentifizierung gegenüber anderen Programmen im selben Benutzerkonto.

## Wie geht Selbstoptimierung?

Erst nach einer echten Einbindung die vorhandenen V5-Abnahmetests und das Wirkungsregister verwenden: zuerst unveränderte Aufgabenfälle, dann `brain_lookup` gezielt gegenüber bisherigem Abruf vergleichen. Die Auswahlfunktionen werden **nicht selbstständig umprogrammiert**, und wissenschaftliche Simulationen bleiben experimentell, bis robuste Vergleichsmessungen und ein sicherer Rückweg vorliegen.
