---
name: ma-server-ops
description: Sicheres und token-effizientes Arbeiten am MA-Server über SSH. Für Diagnose, Docker, systemd, Netzwerk, Caddy, Authelia, Dateien und Server-Reparaturen.
---

# MA-Server Ops

Arbeite am Server über:

ssh ma-server

## Grundregeln

- Behandle `ssh ma-server` als den normalen Zugriff auf den echten MA-Server.
- Beginne neue Diagnoseaufträge mit wenigen gezielten, read-only Prüfungen.
- Lade keine kompletten Logs, Repositories oder Verzeichnisbäume ohne Grund.
- Begrenze Logausgaben mit `tail`, `journalctl -n`, `docker logs --tail` oder passenden Filtern.
- Verwende keine Subagenten, außer der Nutzer verlangt sie ausdrücklich.
- Nutze vorhandene Ergebnisse weiter, statt dieselben Prüfungen ständig zu wiederholen.

## Vor Änderungen

1. Ursache soweit möglich belegen.
2. Betroffene Datei oder Dienst eindeutig bestimmen.
3. Bestehende Konfiguration sichern.
4. Konkreten Rollback bestimmen.
5. Nur die kleinste notwendige Änderung durchführen.
6. Nur betroffenen Dienst reloaden/restarten.
7. Ursprünglichen Fehler erneut testen.

## Sicherheit

Nie ohne ausdrücklichen Auftrag:

- `docker system prune`
- Firewall komplett zurücksetzen
- rekursiv `chmod 777`
- Authentifizierung deaktivieren
- TLS-/Zertifikatsprüfung deaktivieren
- Docker-Socket öffentlich freigeben
- neue Ports öffentlich öffnen
- Server rebooten
- produktive Daten löschen

Keine Passwörter, Tokens, Cookies, private Keys oder andere Secrets in:
- Prompts
- Projektdateien
- Logs
- Obsidian
- Git

Secrets in Ausgaben redigieren.

## Serverzustand

Historische Angaben niemals automatisch als aktuellen Zustand behandeln.
Bei wichtigen Entscheidungen live über SSH prüfen.

Bekannter SSH-Endpunkt:
- Alias: `ma-server`
- Hostname: `ma-server`
- Benutzer: `andrew`

Produktive Pfade nur verwenden, wenn sie live bestätigt wurden.

## Webprobleme

Nicht aus `HTTP 200` allein schließen, dass die Anwendung funktioniert.

Bei Webproblemen getrennt prüfen:
1. DNS
2. TCP/Port
3. TLS
4. Reverse Proxy
5. Authentifizierung
6. eigentliche Anwendung
7. Browser/UI

Vorhandenes Chrome-DevTools-MCP kann für Browserprüfungen genutzt werden, wenn nötig.

## Docker

Ein laufender oder "healthy" Container beweist nicht automatisch eine funktionierende Anwendung.

Gezielt prüfen:
- Containerstatus
- relevante begrenzte Logs
- Ports
- Mounts
- Dienstbenutzer/Rechte
- tatsächlichen App-Endpunkt

## Ergebnis

Antworte knapp mit:
- Befund
- tatsächlich ausgeführter Änderung
- Prüfung
- verbleibendem offenen Punkt

Wenn eine Änderung dauerhaft relevant ist, aktualisiere nur die passenden Projekt-/Obsidian-Notizen.

Keine ungeprüften Erfolge behaupten.
