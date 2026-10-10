# MA Home – Erkenntnisse und Fehlervermeidung

Stand: 2026-10-05. Quelle: aktuelle Projektregeln; keine neuen Live-Belege. Diese Datei enthält Prüfregeln und trennt sie von unbestätigten Ursachen.

## Bereits geltende Prüfregeln

| ID | Erkenntnis | Passende Prüfung | Beleggrenze |
|---|---|---|---|
| L01 | Healthcheck-Erfolg beweist keine funktionierende Oberfläche | Root-Seite, Assets, Benutzeraktion und Auth prüfen | Allgemeine Projektregel, kein aktueller Erfolg |
| L02 | Dateizugriff hängt von Dienstkonto und allen Elternverzeichnissen ab | Zugriff als tatsächlicher Dienstbenutzer prüfen; umask berücksichtigen | 404-Ursache am Server noch offen |
| L03 | DHCP-Reservierung setzt keinen Client-DNS | DNS-Antwort und tatsächlich genutzten Client-DNS getrennt prüfen | Blocky-Nutzung offen |
| L04 | Mobilfunk-Erfolg beweist keinen LAN-Erfolg | Beide Zugangswege getrennt testen | Aktueller Netzwerkzustand offen |
| L05 | Bereitgestellter Code ist keine ausgeführte Änderung | Ausführungsausgabe und ursprünglichen Fehlerfall belegen | Gilt für alle Serverberichte |
| L06 | Geräteerkennung ist kein Druck-/Scan-Test | Beauftragte reale Geräteaktion prüfen | Druck/Scan noch offen |

## Unbestätigte Hypothese

H01: Unzugänglicher Webordner könnte die historische JSON-404 erklären. Laut bestehender Dokumentation lokal simuliert; Ausführung der Rechtekorrektur und Erfolg auf dem Server nicht bestätigt. Nicht als erledigte Reparatur oder bestätigte Ursache führen.

## Vorlage für eine belegte Ursache

- ID / Datum / betroffener Fall:
- Beobachteter Fehler und Quelle:
- Bestätigte Ursache und unterscheidender Beleg:
- Tatsächliche Reparatur und Ergebnis:
- Kurze Vermeidungsregel und passende Prüfung:
- Grenzen / weiterhin offene Punkte:

Überholte Erkenntnisse mit datierter Korrektur versehen. Nur allgemeingültige dauerhafte Regeln zusätzlich in AGENTS.md übernehmen; keine unbestätigten Vermutungen verallgemeinern.

## Bestätigte Erkenntnisse 2026-10-09 (live belegt)

| ID | Erkenntnis | Prüfung |
|---|---|---|
| L07 | Webdateien `root:root 700` → Dienst `ma-web` bekam 404 (JSON-Fehlerhandler). Behoben mit `root:ma-web 750/640`. Belegt durch Vorher/Nachher (404→200). | Zugriff als Dienstkonto und lokaler Portalaufruf mit Proxy-Schlüssel |
| L08 | Ubuntu 26.04 nutzt `sudo-rs`: Ticket je Terminal, Option `tty_tickets` ungültig. Vor jeder sudoers-Änderung `visudo -cf` prüfen. | `sudo --version`, `visudo -cf Datei` |
| L09 | `UMask=0077` im systemd-Dienst maskiert `mkdir(mode=…)`; Verzeichnisse für Container-Benutzer danach explizit `chmod`. | Modus des erzeugten Verzeichnisses prüfen, nicht nur "Container läuft" |
| L10 | Neue Filebrowser-Images lesen Port/baseURL aus `/config/settings.json`, nicht aus der DB; Compose-Portmapping und Datei müssen übereinstimmen. Proxy-Auth legt unbekannte Benutzer an (Standard-Scope `/`) → Standardwerte härten. | `docker logs` ("Listening on"), `GET …/api/login` mit unbekanntem Benutzer |
| L11 | HA ≥ 2026.x: HTTP-Einstellungen aus YAML liegen in `.storage/http` als `stable`/`pending`; unbestätigte `pending` verfallen nach 5 min. Bei Proxy-Aussperrung `.storage/http` bei gestopptem HA anpassen. | `GET` mit `X-Forwarded-For` (400 vs 200), Listener per `ss` |
| L12 | Healthy-Container ≠ funktionierende App: Filebrowser war "healthy", antwortete aber nicht auf dem veröffentlichten Port. | `curl` auf Host-Port |
