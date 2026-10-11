---
name: netz
description: Heimnetz und Geräte vom MA-Server aus prüfen oder steuern (Erreichbarkeit, Nachbarn, Home-Assistant-Schalter) über eine Zulassungsliste. Nutzen bei "Gerät", "Steckdose", "Drucker erreichbar", "Heimnetz", "Home Assistant", "Licht".
---

# Netz und Geräte

Werkzeug: `python3 ~/MA-Server/server/tools/netz.py <befehl>` (nur Standardbibliothek, ohne sudo). Läuft auf dem MA-Server.

Befehle: `liste`, `status [name]`, `nachbarn` (passiv, ARP-Tabelle), `dienste` (lauschende Ports), `ha-zustand [entity]`, `ha-schalten <entity> an|aus`.

Regeln:
1. Nur Geräte und Entities aus `~/.ma-netz.json` (Zulassungsliste). Nicht dort, dann nicht anfassen und Philipp bitten, es einzutragen.
2. Stufe 1 nur lesen. Stufe 2 Schalter ein/aus: erlaubt, das Ergebnis und den Rückweg nennen. Stufe 3 (Router, Firewall, DNS, `/etc`, Docker, Systemdienste, Löschen, Geld, Senden an Dritte): nie selbst, als Anweisung an Philipp mit Rückgängig-Anleitung formulieren.
3. Kein Port-Scan fremder Geräte, keine Passwörter, Tokens oder MAC-Adressen in Antworten oder Notizen (Klasse B/C). Das Home-Assistant-Token liegt in `~/.ma-ha-token` und wird nie ausgegeben.
4. Kamera (`/dev/video0`) bleibt gesperrt, außer Philipp verlangt es ausdrücklich.
