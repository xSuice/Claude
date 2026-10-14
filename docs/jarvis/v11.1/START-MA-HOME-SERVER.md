# Claude Cognitive Brain V5 — MA-Home Server Edition (Linux)

**Zweck:** Das Gehirn liegt dauerhaft auf dem selbst betriebenen MA-Home-Linux-Server. Claude Code (Windows/Linux) ist Client. Claude-/API-Nutzung bleibt davon getrennt. Dieses Paket startet **keinen öffentlich zugänglichen Port**, verändert keinen Router, keine Docker-Container und keine produktiven Dienste. Die lokale Gedächtnisverwaltung und Routineprüfung laufen ohne zusätzliche Claude-Modellaufrufe.

## 0. Voraussetzungen / Einschränkung

- Ubuntu 24.04 LTS oder vergleichbares Linux mit Python **3.10+**, `ssh`/`sshd` für Remote-Clients, optional `systemd --user`.
- Linux-Benutzerkonto mit **eigenem Home-Verzeichnis**, ohne Rootrechte für den laufenden Brain-Dienst; administrative SSH-Key-Einrichtung bleibt bewusst separat.
- Diese Edition nutzt die bereits programmierte V5-**SQLite-Datenbank**, nicht automatisch die eventuell bestehende PostgreSQL-/Second-Brain-Datenbank. Kein Import ohne vorherige Prüfung von Schema, Zugriffsrechten und Sicherung.
- Nur der Supervisor kann ohne Claude-Modellaufrufe lokal weiterlaufen. Eigenständige KI-Entscheidungen und Code-Änderungen erfordern Claude Code/Agenten oder eine separate, autorisierte Orchestrierung.
- Forschungsmodelle OpenWorm/Nengo sind enthalten, aber **standardmäßig ausgeschaltet**. Keine wissenschaftliche Simulation wird als Qualitätsverbesserung behauptet.

## 1. Installation **auf dem Server**

Entpacke das ZIP auf dem Linux-Server. Unter diesem Ordner:

```bash
python3 server/install_linux.py                # Vorschau ohne Änderungen
python3 server/install_linux.py --apply       # User-lokale Dateien anlegen
python3 server/probe_mcp.py --config ~/.config/ma-home-brain/person-a.json \
  --runtime ~/.local/share/ma-home-brain/brain-runtime
python3 -m unittest discover -s brain-runtime/tests -v
python3 -m unittest discover -s tests -v
```

Standardpfade: Code `~/.local/share/ma-home-brain`, Daten `~/.local/state/ma-home-brain/brain.sqlite3`, Konfiguration `~/.config/ma-home-brain/`. Es werden **keine Demo-Wissensdaten** importiert.

Aktualisieren nach Sicherung:

```bash
python3 server/backup_sqlite.py --config ~/.config/ma-home-brain/person-a.json \
  --out-dir ~/ma-home-brain-backups
python3 server/install_linux.py --apply --update
```

Die alte Programmversion wird unter einem datierten `.backup-...`-Ordner abgelegt. Die Datenbank und Zugangsprofile liegen außerhalb des Programmpfads und bleiben erhalten. Vor DB-Schema-Upgrades zusätzlich eine geprüfte Migration vorsehen.

## 2. Dauerbetrieb (ohne Cloud-Modellaufrufe)

```bash
python3 server/write_service.py --apply
systemctl --user daemon-reload
systemctl --user enable --now ma-home-brain@person-a.service
systemctl --user status ma-home-brain@person-a.service
```

Für die zweite Person bei tatsächlichem Bedarf separat `ma-home-brain@person-b.service` aktivieren. Mit `systemctl --user` kann der Prozess beim Abmelden enden; wenn Dauerbetrieb gewünscht ist, kann ein Administrator gezielt `loginctl enable-linger <serverkonto>` verwenden. Die Unit hat CPU-/RAM-Grenzen und führt keine Claude-Aktionen aus.

Alternativ für erste Tests:

```bash
python3 ~/.local/share/ma-home-brain/brain-runtime/supervisor.py \
  --config ~/.config/ma-home-brain/person-a.json --once
```

## 3. Claude Code auf Windows über SSH anbinden

Für jede Person einen **eigenen SSH-Schlüssel** generieren und dessen öffentlichen Schlüssel von einem Administrator auf dem Server in `~/.ssh/authorized_keys` des dedizierten Brain-SSH-Kontos eintragen. **Nicht** normalen uneingeschränkten SSH-Zugang und dieselben Anmeldedaten für beide Personen verwenden.

Beispiel für eine geprüfte, schlüsselgebundene Regel (Pfad anpassen):

```text
restrict,command="/home/ma-brain/.local/share/ma-home-brain/bin/mcp-person-a" ssh-ed25519 <ECHTER-PUBLIC-KEY-A>
restrict,command="/home/ma-brain/.local/share/ma-home-brain/bin/mcp-person-b" ssh-ed25519 <ECHTER-PUBLIC-KEY-B>
```

Die `restrict`-Option verhindert unter anderem PTY, Weiterleitungen und Agent-Forwarding für genau diesen SSH-Key. Ein Python-Helfer gibt mit echten öffentlichen Schlüsseln die beiden Zeilen zur Kontrolle aus:

```bash
python3 server/generate_ssh_keys_lines.py \
  --bin-dir ~/.local/share/ma-home-brain/bin \
  --person-a-public-key /pfad/zum/public_key_A.pub \
  --person-b-public-key /pfad/zum/public_key_B.pub
```

Windows PowerShell (**Beispielwerte durch eigene ersetzen**):

```powershell
claude mcp add --scope user --transport stdio ma-home-brain -- ssh -T -o BatchMode=yes -i "$env:USERPROFILE\.ssh\ma-brain-a" ma-brain@DEIN-SERVER
claude mcp get ma-home-brain
```

Der SSH-Prozess wird von Claude als MCP-Transport gestartet und ist kein interaktives Konsolenprogramm. Zur Prüfung `server/probe_mcp.py` serverseitig ausführen und danach Claude Code mit `/mcp` testen. **SSH-Hostschlüssel vor dem ersten Einsatz separat verifizieren**; keine Option verwenden, die Host-Key-Prüfung deaktiviert. Wenn ein normaler SSH-Account verwendet wird, ist die Identitätstrennung nicht automatisch garantiert; `authorized_keys`-Zwangsbefehle müssen tatsächlich durch den SSH-Server erzwungen werden. Eine bereits vorhandene lokale `ma-home-brain`-Registrierung darf nicht blind überschrieben werden.

**Zwei-Nutzer-Grenze:** V5 hat identitätsgefilterte Abfragen und einzelne Freigaben. Beide SSH-Keys laufen im Beispiel aber unter demselben Linux-Benutzer und greifen auf dieselbe Datenbank zu. Das ist **keine harte OS-/Datenbank-Isolation** gegen einen kompromittierten Prozess oder Administrator. Für streng getrennte persönliche Daten sind unabhängige DB-Konten/isolierte Instanzen oder ein authentifizierter Backend-Dienst nötig, bevor echte vertrauliche Daten zweier Personen übernommen werden.

## 4. Betrieb/Weiterentwicklung

- Standard: `research_tools=false`, **keine** OpenWorm-Simulation bei jeder Claude-Anfrage.
- `brain_lookup` sucht nur bestätigte Daten; `brain_propose_memory` legt **nicht bestätigte Vorschläge** an.
- Nur der Server-Administrator bestätigt Erinnerungen explizit per CLI, z. B. `python3 brain-runtime/brain_admin.py --config ... pending ma-home`; danach `confirm ID`.
- `brain_cycle` und Supervisor erzeugen höchstens Vorschläge aus **bestätigten** Fehlern; keine Auto-Rewrites oder KI-Calls.
- Auf dem Server darf kein Docker-Socket ungeschützt an die KI gegeben werden; sichere Aktionen benötigen einzeln autorisierte Werkzeuge.
- Falls der reale MA-Home-Server ZimaOS mit read-only OS statt Ubuntu verwendet, **dieses native Installationsskript nicht blind ausführen**. Dafür ist ein separater Container-/API-Anschluss erforderlich.
- Vorher-nachher-Messung: Aufgabenqualität, Nacharbeit, Dauer, Claude-Pro-Anzeige und API-Tokens separat erfassen. Der Server erhöht Claude-Nutzungslimits nicht.

## 5. Abnahme und Rückbau

1. MCP `initialize`, `tools/list`, `brain_lookup` prüfen.
2. Erinnerung A speichern, manuell bestätigen, in neuer Sitzung abrufen; Korrektur/Widerruf testen.
3. Für Testpersonen private und ausdrücklich freigegebene Einträge prüfen.
4. Server-Neustart/Schreibkonflikte sowie Backup und Restore auf Testkopie prüfen.
5. Mit und ohne Brain mindestens drei vergleichbare reale Aufgaben ausführen. Keine generellen Token-/Qualitätsgewinne ohne Belege behaupten.

Rückbau: `systemctl --user disable --now ma-home-brain@person-a.service` (und ggf. B), Claude-MCP-Registrierung entfernen **nur wenn sie genau dieser Installation gehört**, dann nur die von `install_linux.py` angelegten Programmdateien entfernen. **Datenbank und Backups nicht automatisch löschen.**
