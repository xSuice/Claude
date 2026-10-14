# Bestandsaufnahme PC vs. Server (Aufgabe 0, Stand 2026-10-11)

Vault-Notiz: `30 Technik/MA-Server/Server-Claude Variante 2.md` · Abgleich: `scripts/server-sync/claude-abgleich.py` · Installation: `server/tools/install-office-tools.sh`, `server/claude-bridge/update-bridge.sh`

Nur gelesen, nichts geändert. Geheimnisse nur als vorhanden/fehlt.

| Bereich | PC | Server | Status |
|---|---|---|---|
| Globale CLAUDE.md | Grundregeln Philipp (13 Regeln) | Server-Fassung (`server/claude-config/CLAUDE.md`), andere Prüfsumme | abweichend (gewollt: Pfade, Server-Abschnitt) |
| Skills | council, uebergabe, learned, refine.disabled; Projekt: ma-server-ops, obsidian-librarian | council (+ Ordner "synced") | fehlt auf dem Server: uebergabe, learned, ma-server-ops, obsidian-librarian |
| Agenten | 8 Agenten | dieselben 8 | gleich |
| settings.json | deny 16, ask 16, Hooks: Kontext-Wächter, Übergabe laden, fixmyprompt | deny 17, Hook ma-guard.py (PreToolUse), keine ask-Liste | abweichend (gewollt, Server strenger) |
| MCP/Verbindungen | gmx, claude.ai-Connectors | keine | fehlt auf dem Server |
| Modell-Router | im Repo `.claude/model-router.disabled/` (deaktiviert), in `settings.json` kein Router-Hook | gleicher Ordner, deaktiviert; Auto-Wahl nur in der Brücke (`pick_model`) | beide ohne aktiven Router; zwei getrennte Logiken |
| ask.py | `scripts/ext-ai/ask.py` | identische Datei (gleiche Prüfsumme) | gleich; Schlüssel in `~/.claude/secrets/<anbieter>.key` auf dem Server nicht gefunden (fehlt) |
| ollama | gemma3:4b lokal | nicht installiert; 3,3 GB RAM, davon ca. 2,2 GB frei, 2 Kerne | fehlt, passt kaum (siehe unten) |
| Auto-Memory / Vault | Junction nach Vault `_Claude-Memory/Auto-Memory` | Spiegel `/srv/ma-home/library/vault-notizen`, server-to-vault alle 30 Min | vorhanden, Rückweg per Skript |
| Übergabe | Hooks laden `Uebergabe.md` automatisch | nur über Text in CLAUDE.md, kein Hook | abweichend |
| Brücke (laufend) | Repo-Stand | `/usr/local/lib/ma-claude-bridge.py` = alter Stand | Repo und Betrieb gleich, aber NEUERE Version nur auf dem Server unter `~/MA-Server` |
| Bildanhänge, Auto-Modell | nicht aktiv | neuer Code liegt bereit, nie installiert | Installation steht aus (`update-bridge.sh`) |
| Portal-Oberfläche | Repo-Stand | betrieben = Repo-Stand von gestern; `~/MA-Server/portal-ui` neuer (Bilder, Council-Auto) | Drift, jetzt ins Repo übernommen |
| Büro-Werkzeuge | n/a | node, pandoc, soffice, ffmpeg, ImageMagick, python-pptx/docx/openpyxl/reportlab/pypdf, matplotlib, Chromium: alle fehlen; nur Pillow vorhanden | fehlt |
| Parallele Aufträge | n/a | 2 (Semaphore in der Brücke), Zeitlimit 900 s | gesetzt |

## Befunde
1. **Drift:** Die Server-Kopie `~/MA-Server` war neuer als Repo und Betrieb (Brücke, Oberfläche). Die neueren Dateien liegen jetzt auch im PC-Repo. Der Server-Ordner ist kein Git-Repo.
2. **Brücke gegengelesen:** `update-bridge.sh` sichert die alte Brücke (`.bak`), installiert die neue, patcht `portal.py` nur an einer Stelle (Feld `images`, idempotent, Sicherung, Syntaxprüfung, Rücksetzen bei Fehler) und startet beide Dienste neu. Bilder: nur jpeg/png/webp/gif, höchstens 3, je unter 5 MB, Ordner 0700, Löschung nach 7 Tagen, `--add-dir` nur für diesen Ordner. Schutzschicht (deny, ma-guard, NoNewPrivileges) wird nicht berührt. Keine Beanstandung. Bildbudget (100 000 Zeichen) liegt unter dem 128-KB-Limit des Portals.
3. **ollama:** gemma3:4b braucht etwa 3 bis 4 GB RAM. Der Server hat 2,2 GB frei, ein lokales Modell würde ihn ausbremsen. Empfehlung: ollama nur am PC.
4. **Router:** Es gibt keinen aktiven Router. Für eine Quelle braucht es ein gemeinsames Modul (Aufgabe 8d), erst nach der Entscheidung Variante 1 oder 2.
5. **Schlüssel:** Gemini/OpenRouter-Schlüssel fehlen auf dem Server. Philipp legt sie selbst an (chmod 600).

## Reihenfolge, in der die Lücken geschlossen werden
1. Brücke und Oberfläche installieren (Sudo, ein Befehl).
2. Büro-Werkzeuge installieren (Sudo, `server/tools/install-office-tools.sh`), danach Skills pptx/docx/xlsx/pdf anlegen.
3. Fehlende Skills (uebergabe, ma-server-ops, learned) auf den Server und Übergabe-Hook.
4. Verlauf, Abbrechen/Status, Auto-Rechte (brauchen Entscheidungen, siehe Abschnitt Entscheidungen).
5. Mobile Oberfläche und Graph-Zoom.
6. Netzwerk-Inventar und Steuerung (erst Inventar).
7. Gemeinsames Router-Modul mit Tests, Paritäts-Check.

## Entscheidungen von Philipp
1. Variante 1 (Server einzige Umgebung) oder Variante 2 (beide gleich halten)?
2. Auto-Rechte: Bestätigen-Knopf vor "Voll" (Empfehlung)?
3. Alte PC-Verläufe auf den Server importieren oder bei null anfangen?
4. Welche Geräte im Netz darf Claude steuern?

## JARVIS V16 (Stand 2026-10-14)

Bewusst nur auf einer Seite: Der Server-Teil (`server/jarvis/`, Cron-Takt, bwrap-Sandbox, bwrap/Linux-Tests) läuft nur am Server; der PC hat den Client `scripts/jarvis/jarvis.py` und den Skill `/jarvis` sowie den PC-Worker (java.build, blender, ollama; ohne Sandbox, nur mit `jarvis-pc.json`). Grund: Aufträge sollen am Server laufen, am PC fehlen WSL und Docker. Der Router (`scripts/router/router_core.py`) liegt auf beiden Seiten. Server-Installation hat noch keine Kopie in `~/MA-Server` (nur Staging `~/jarvis-stage/v16`); Abgleich über `ClaudeAbgleich`/`server-live`.
