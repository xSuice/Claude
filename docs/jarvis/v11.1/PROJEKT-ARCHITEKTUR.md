# Architektur für MA-Home

```
Claude Code [Windows / Linux] —SSH/forced command/stdio MCP—> MA-Home Server
                                                            |
                         private identity A/B —> Claude Brain V5 SQLite (server-local)
                                                            |
                                    confirmed memory, goals, episodes, suggestions
                                                            |
                                 bounded supervisor (no Claude calls, no shell)

Other MA-Home services (Docker, Caddy, Filebrowser, existing DB, Router)
    remain unchanged; future links require an explicit adapter, ACL test, and evidence.
```

## Designentscheidungen

- Kein öffentlich freigegebener MCP-HTTP-Port. Nutzt vorhandenes SSH.
- Cloud-Claude-Code-Modelle bleiben extern; Gehirn selbst und Daten liegen auf dem eigenen Server.
- Permanente Hintergrundanalyse ohne KI-Aufrufe; komplexe Autonomie nur in autorisierten Claude-Code-Sitzungen.
- Getrennte Profile pro Nutzer; **keine garantierte hart isolierte private Datenhaltung** über ein gemeinsames OS-Konto.
- Keine automatische Konvertierung oder Ersetzung der vorhandenen Second-Brain-Datenbank. Erst Schema/Verbindungen ermitteln.
- Kein wahlloses Starten biologischer Simulationen; Forschungsfunktionen nur experimentell.
- Auf alten Servern mit ca. 4 GB RAM keine lokalen großen Sprachmodelle einplanen.

## Was das nicht ist

Kein biologisches Gehirn, keine allgemeine künstliche Intelligenz, keine Bewusstseins-Simulation. Die lokale Speicherung und regelbasierte Überwachung bedeuten noch keine nachgewiesene Qualitäts- oder Tokenverbesserung im produktiven Claude Code.
