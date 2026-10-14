# Docker / ZimaOS: zunächst nur der lokale Supervisor

Dieses Compose startet ausschließlich den **deterministischen**, lokal begrenzten Supervisor und **kein Claude-Modell**, keine Gehirnsimulation und keinen Netzwerkport.

1. `mkdir -p local-state && sudo chown 10001:10001 local-state && chmod 700 local-state` (einen lokalen Admin den Pfad prüfen lassen; kein unüberprüftes `sudo`-Skript).
2. Die Datei `local-state/person-a.json` mit Modus 600 anlegen (Eigentümer 10001). Beispiel:
   `{"identity":"person-a","allowed_projects":["ma-home"],"state_db":"/state/brain-person-a.sqlite3","research_tools":false}`.
3. `docker compose -f compose.brain.yml config` und dann `docker compose -f compose.brain.yml up -d --build`.
4. `docker compose -f compose.brain.yml logs --tail 20`; stoppen mit `docker compose -f compose.brain.yml down`.

**Sicherheitsgrenze:** Jeder Container sollte für eine zweite echte Person unter eigener OS-/Container-Identität und mit getrenntem Verzeichnis laufen. Die Compose-Datei enthält absichtlich **nur Nutzer A**. Gemeinsame Quellen werden erst nach expliziten ACL-Tests integriert. Docker bleibt ohne Netzwerk, benötigt keinen Docker-Socket und kann keine externen Aufgaben auslösen.

Für den produktiven **MCP-Zugang über SSH** ist bisher die native Ubuntu/Linux-Variante dokumentiert. Es ist **kein** sicherer Docker-Remote-MCP-Pfad vorgetäuscht; keine Docker-Gruppenmitgliedschaft nur wegen dieses Prototyps vergeben.
