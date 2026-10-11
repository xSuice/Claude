# Netzwerk- und Geräte-Inventar (Stand 2026-10-11)

Vault-Notiz: `30 Technik/MA-Server/Server-Claude Variante 2.md` · Prompt-Aufgabe 6a (nur lesen, passiv, kein Port-Scan fremder Geräte).
Keine Passwörter, Tokens oder MAC-Adressen in dieser Datei (Klasse B/C).

## Server (Laptop, Ubuntu)
| Bereich | Befund | Erreichbar über |
|---|---|---|
| LAN | `enp4s0` up, feste Adresse 192.168.0.111, Router 192.168.0.1 | SSH (Port 22), Portal über Caddy (80/443) |
| WLAN | `wlp2s0f0` vorhanden, aus | n/a |
| Bluetooth | Hardware vorhanden (Ralink RT3290, PCI-Funktion 02:00.1). Dienst `bluetooth` inaktiv, `bluez` (bluetoothctl, rfkill) **nicht installiert**. Ob Linux den RT3290-Bluetoothteil ohne Zusatztreiber ansteuert, ist **ungeprüft** (diese Chips gelten als schwierig). | erst nach `server/tools/install-bluetooth.sh`, dann prüfen, ob ein Adapter erscheint |
| Kamera | HP-Webcam (`/dev/video0`, `video1`) | Standard: gesperrt (Datenschutz), nur auf ausdrückliche Anweisung |
| USB | SATA-Bridge (Backup-Platte), USB-Hub | restic-Backup 04:15 |
| Drucker | CUPS läuft (Port 631, nur lokal), kein Drucker eingerichtet | `lpstat`, `lp` |
| Heimnetz | etwa 11 weitere Geräte in der ARP-Tabelle, nicht benannt | Zuordnung braucht Philipp oder die Router-Liste |

## Dienste auf dem Server (lauschend)
Portal (18765) und Brücke (Socket), Terminal (7681), Home Assistant (8123, nur lokal), CouchDB (15984), FileBrowser, ntfy, Authelia, Caddy (80/443/8080/8443), DNS (Blocky, Port 53 im LAN), Docker-Netz 172.18.0.0/16. Docker und `/etc/ma-home` sind ohne Sudo nicht lesbar.

## Berechtigungsstufen (Vorschlag, von Philipp freigegeben: Claude darf alles ansteuern)
1. **nur lesen**: Status, Listen, Logs. Immer erlaubt.
2. **steuern (reversibel)**: Gerät ein/aus, Dienst neu starten, Benachrichtigung senden, Bluetooth verbinden. Erlaubt, Ergebnis wird gemeldet.
3. **ändern (nur mit Bestätigung)**: Router, Firewall, DNS-Filter, `/etc`, Docker, Systemdienste, Löschen, Geldausgaben, Senden an Dritte. Nur als Sudo-Skript für Philipp mit Rückgängig-Anleitung.
Zugänge (Tokens, Router-Login) legt Philipp selbst in einer Datei an (`chmod 600`, nicht im Git, nicht im Chat). Statt offener Shell ins Netz gilt eine Zulassungsliste (Allowlist) von Hosts und Befehlen.

## Nächste Schritte
- Geräteliste mit Namen: Philipp liefert die Geräteliste aus dem Router (192.168.0.1) oder benennt sie, dann ordne ich IPs zu.
- `server/tools/install-bluetooth.sh` ausführen (Sudo), danach Bluetooth-Geräte erfassen.
- Home Assistant (Port 8123) als zentrale Steuerung nutzen, sobald ein Token angelegt ist (`HA_TOKEN` in der Zugangsdatei).
