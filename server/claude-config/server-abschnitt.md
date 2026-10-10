# Server-Umgebung (Chat im MA-Home-Portal und in der App)
- Du läufst als Benutzer `andrew` auf dem MA-Server (Ubuntu), ohne sudo und ohne Root. Änderungen an Systemdiensten, `/etc`, Docker und Firewall macht Philipp selbst per Sudo-Skript. Schreibe dafür das Skript und sage, wie es gestartet wird.
- Projektordner: `~/MA-Server` (Doku, Skripte, Skills, Portal-Oberfläche, Apps). Notizen-Spiegel des Obsidian-Vaults: `/srv/ma-home/library/vault-notizen` (die Hauptkopie liegt auf Philipps PC; Änderungen hier gleicht `server-to-vault.py` alle 30 Min zurück, bei Konflikt landet die Serverfassung in `00 Inbox/Review`).
- Bibliothek: `/srv/ma-home/library` (inbox, documents, media, archive, review). Backup-Platte: `/mnt/ma-backup` (nur lesen).
- Windows-Pfade aus den Projektdateien (z. B. `C:\Users\andre\...`) gelten nur auf dem PC. Auf dem Server heißen die Entsprechungen wie oben.
- Senden (Mail, Chat), Löschen und Veröffentlichen nur nach ausdrücklichem Ja von Philipp. In diesem Chat sind Sende-Werkzeuge ohnehin gesperrt.
