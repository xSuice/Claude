# MA Home – Backup und Restore (vorbereitet, NICHT aktiv)

Stand: 2026-10-09, Europe/Berlin. Status: **kein Backupziel gewählt, nichts installiert, nichts ausgeführt.** Skript: `scripts/ma-backup.sh` (nur syntaxgeprüft).

## Grundsatz
Ein Backup zählt erst, wenn (1) es auf einem **anderen physischen Datenträger/Gerät** liegt, (2) verschlüsselt ist und (3) ein Restore-Test belegt ist. Eine Kopie auf der internen HDD (sda) schützt nicht vor deren Ausfall und wird vom Skript abgelehnt. Das aktuelle `/srv/ma-home/backups` liegt auf sda und gilt nicht als Backup.

## Ziel (offen – Entscheidung Andrew)
Der Server hat nur eine interne HDD und ein DVD-Laufwerk. Mögliche Ziele, jeweils extern zum Server:
- USB-Festplatte am Server (einfach, abziehbar; Schutz gegen Brand/Diebstahl nur bei Auslagerung).
- NAS oder anderer Rechner im LAN per SFTP (restic `sftp:`), gleiche Einschränkung.
- Entferntes Ziel (SFTP/S3): gäbe verschlüsselte Daten an einen externen Dienst → nur mit ausdrücklicher Freigabe. Kein Cloudflare.

## Umfang
- `/srv/ma-home` (Portal-SQLite, Authelia, Home Assistant, CouchDB, ntfy, Filebrowser, Dateien, Library), ohne `previews`, `jobs`, `backups`.
- `/etc/ma-home` (enthält Geheimnisse → nur verschlüsselt sichern).
- SQLite-Datenbanken werden vorher per Online-Backup-API konsistent gedumpt. Home Assistant und CouchDB werden live gesichert (absturzkonsistent). Strengere Konsistenz durch kurzen Container-Stopp möglich – offene Entscheidung.
- Nicht enthalten: Betriebssystem, Docker-Images (aus compose.json neu ladbar).

## Einrichtung nach Zielwahl (root)
1. `restic init` mit Passwortdatei `/etc/ma-home/backup.pass` (600). **Passwort zusätzlich getrennt vom Server aufbewahren**, sonst ist das Backup bei Serverausfall wertlos.
2. `/etc/ma-home/backup.env` (600): `RESTIC_REPOSITORY=…` und `RESTIC_PASSWORD_FILE=…`.
3. `sudo scripts/ma-backup.sh run`, danach `sudo scripts/ma-backup.sh restore-test`.
4. Erst nach bestandenem Restore-Test einen systemd-Timer (täglich, nachts) anlegen.

## Restore (Ernstfall)
`restic restore latest --tag ma-home --target /srv/restore` in einen **leeren Zielordner**, Inhalt prüfen, dann dienstweise zurückkopieren (Dienst vorher stoppen). Nie direkt über laufende Produktivdaten restoren.

## Belegstatus
| Punkt | Status |
|---|---|
| restic 0.18.1 auf Server installiert | live bestätigt 2026-10-09 |
| Skript Syntax / Logik | lokal geschrieben; Ausführung offen |
| Externes Ziel | offen |
| Restore-Test | offen |
