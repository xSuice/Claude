# MA Home – Architektur und Abhängigkeiten

Stand: 2026-10-05. Quelle: beigefügte AGENTS.md und SERVER-STATUS.md; historische Angaben, keine Live-Inventur. Ports, Images, Mounts, interne Routen und tatsächliche Proxy-Zuordnung sind noch offen.

## Zielbild

Browser → HTTPS über Caddy → geschützte Oberfläche bzw. lokal gehostete Anwendungen. Authelia ist als Anmeldedienst genannt; welche Routen tatsächlich geschützt sind, muss geprüft werden. Keine konkrete Proxy-Konfiguration aus diesem Zielbild ableiten.

| Komponente | Genannte Aufgabe | Abhängigkeit / offene Prüfung |
|---|---|---|
| Caddy | HTTPS und Reverse Proxy | DNS, Zertifikate, aktive Upstreams und Auth-Regeln |
| Authelia | Anmeldung | Geschützte Routen, Sitzungen, Rollen und Weiterleitungen |
| ma-home-web | Oberfläche | Tatsächlicher Dienstbenutzer, Startdatei, statische Dateien, API |
| ma-home-agent | Verwaltungsfunktion | Befugnisse und API-Grenzen unbekannt; nicht pauschal root geben |
| Filebrowser | Dateien | Mounts, Datenrechte und Zugriffsschutz |
| Home Assistant | Smart Home | Aktive Einbindung und Anmeldung |
| ntfy | Benachrichtigungen | Erreichbarkeit und Zugriffsrechte |
| CouchDB | Daten / Synchronisierung | Tatsächliche Nutzung, Volumes und Zugriffsschutz |
| Blocky | DNS-Zusatz | Installation und Client-Nutzung nicht bestätigt |
| Samsung C480/C48x | Druck / Scan | IPP historisch erkannt; konkrete Integration offen |

## Historisch genannte Orte

| Ort | Genannte Bedeutung |
|---|---|
| /opt/ma-home | Quellcode |
| /opt/ma-home/web | Oberfläche |
| /etc/ma-home | Konfiguration; kann Geheimnisse enthalten |
| /srv/ma-home | Nutzdaten |
| /etc/ma-home-dns | Separater DNS-Zusatz |

Vor Änderungen tatsächliche Existenz, Eigentümer, Dienstkonten und Mounts prüfen. Datenpfade sind keine Backupziele. Keine Dateien zwischen diesen Orten verschieben, nur weil die Übersicht sie nennt.

## Inventurvorlage

Pro Dienst ergänzen: Quelle + Datum; Version/Image-Digest; Laufzeit (systemd/Compose); Benutzer; veröffentlichte Ports; interne Netze; Datenpfade; Auth-Grenze; Sicherung; Start-/Reload-Verfahren. Nur benötigte Metadaten, keine Environment-Werte oder Geheimnisse.

Dauerhafte Architekturentscheidungen mit Datum, Grund, Alternativen und Folgen hier festhalten. Aktueller Zustand bleibt in SERVER-STATUS.md, Änderungen bleiben im CHANGELOG.md.
