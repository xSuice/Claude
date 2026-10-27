# V3 – Referenzsammlung, Ergänzung (Prüfdatum 27.10.2026)

Ergänzt `V3-REFERENZEN.md` um die dort als offen markierten Bereiche. **Methode wie dort:** Lizenz, letzter Push, Archivstatus per GitHub-API abgerufen, Doku-Links per HTTP geprüft. **Nichts davon installiert oder getestet.** Kennzeichnung: *dokumentiert* (Metadaten geprüft) oder *Einschätzung*. Rohdaten: `refs_github2.json`.

## Bereits im System vorhanden (nicht neu bauen)
Laut Statusabfrage laufen auf dem Server als Container: **ntfy, Home Assistant, CouchDB (Obsidian-Sync), Authelia, Filebrowser, Caddy** (alle `running`, 27.10.2026). Für Benachrichtigungen und Smart Home ist damit keine neue Infrastruktur nötig; offen ist nur die **Anbindung an JARVIS** (Vorschlag X-01, N-01).

## Benachrichtigungen, mobile Bedienung
| Referenz | Link | Lizenz / Pflege | Nutzen / Einschätzung | Risiken |
|---|---|---|---|---|
| ntfy | https://github.com/binwiederhier/ntfy , https://docs.ntfy.sh/ | Apache-2.0, aktiv (27.10.2026), 35 k Sterne | **Läuft bereits auf dem Server.** Push aufs Handy per einfachem HTTP-POST; geeignet für „JARVIS meldet Ergebnis/Incident“ (Vorschlag N-01) | Themen/Zugangsdaten über `ma-home credentials`; Nachrichten nie mit Secrets füllen |

## Mission-Control- und Agenten-Oberflächen (Vergleich, keine Übernahme empfohlen)
| Referenz | Link | Lizenz / Pflege | Einschätzung |
|---|---|---|---|
| smolboon/mission-control | https://github.com/smolboon/mission-control | MIT, 7 Sterne, letzter Push 05.03.2026 | Sehr klein und seit Monaten ohne Pflege; nur Ideengeber für Layout, nicht als Abhängigkeit |
| Langfuse | https://github.com/langfuse/langfuse | Lizenz „NOASSERTION“ (Mischlizenz, vorab lesen), aktiv, 36,6 k Sterne | Referenz für Trace-/Kostenansicht von Agentenläufen. Eigener Dienst mit Datenbank — für den 3,2-GB-Server vermutlich zu schwer (Einschätzung) |
| Arize Phoenix | https://github.com/Arize-ai/phoenix | „NOASSERTION“, aktiv, 12 k Sterne | Ähnlich; Vergleichsreferenz für Trace-Darstellung |
| awesome-agent-observability | https://github.com/ianwieds/awesome-agent-observability | CC0-1.0, 1 Stern, aktiv | Linkliste, nur zum Weitersuchen; Qualität der Einträge nicht geprüft |

**Schluss:** Das Portal hat bereits Living HQ und Command Center auf echten Daten. Fremdprojekte liefern Gestaltungsideen (Trace-Zeitleiste, Kostenansicht), aber keinen Grund, ein zweites Dashboard einzuführen (§0/§11 des Auftrags).

## Computersteuerung
| Referenz | Link | Lizenz / Pflege | Nutzen / Einschätzung | Risiken |
|---|---|---|---|---|
| browser-use | https://github.com/browser-use/browser-use | MIT, aktiv, 119 k Sterne | Browser-Automatisierung; die hier benutzte Browser-Kopplung stammt aus diesem Umfeld (Hermes-Harness) — Einschätzung, Herkunft nicht geprüft | Eingabe-/Download-Rechte begrenzen, Prompt-Injection aus Webseiten (OWASP-Raster) |
| trycua/cua | https://github.com/trycua/cua | MIT, aktiv, 31 k Sterne | Desktop-Steuerung mit Sandboxes; Hermes bringt ein eigenes `computer_use`-Werkzeug mit (laut Werkzeugliste) | Windows-Sandbox-Pfad auf diesem PC derzeit blockiert (siehe E-01) |
| microsoft/UFO | https://github.com/microsoft/UFO | MIT, aktiv, 10 k Sterne | Windows-GUI-Agent, Forschungsreferenz | Hoher Rechtebedarf; nur nach E-01 und isoliert zu bewerten |
| Jeomon/Windows-Use | https://github.com/Jeomon/Windows-Use | MIT, 477 Sterne, Push 23.09.2026 | Kleineres Windows-Projekt | Kleine Community, Wartungsrisiko |

**Schluss:** Computersteuerung ist ein P3-Thema und hängt an der Sandbox (E-01). Vor E-01 kein Eigenbau und keine Installation.

## Kreativwerkzeuge (Bild, Audio, Video, 3D, Manga)
| Referenz | Link | Lizenz / Pflege | Nutzen für deine Projekte (Einschätzung) | Risiken |
|---|---|---|---|---|
| ComfyUI | https://github.com/Comfy-Org/ComfyUI , https://docs.comfy.org/ | **GPL-3.0**, aktiv (27.10.2026), 143 k Sterne | Knotenbasierte Bild-/Videopipelines mit API; Basis für „Zeichnung → Bild/Manga-Panel“ | 6 GB VRAM der RTX 2060 begrenzen Modellgröße; Gaming-Vorrang; GPL beachten, wenn Code eingebunden wird |
| Blender | https://github.com/blender/blender | Lizenz im Mirror „NOASSERTION“ (Blender ist GPL), aktiv | 3D-Modelle/Renders | – |
| Blender-MCP (ahujasid) | https://github.com/ahujasid/mcp-for-blender (früher `blender-mcp`, umgeleitet) | MIT, aktiv (24.10.2026), 32 k Sterne | LLM steuert Blender per MCP — mögliche Brücke für „3D per Beschreibung“ | Führt Skripte in Blender aus: nur isoliert, nach Freigabe |
| Remotion | https://github.com/remotion-dev/remotion | „NOASSERTION“ (eigene Lizenz, Firmennutzung kann kostenpflichtig sein — vorab lesen) | Videos per React/Code erzeugen | Lizenz/Kosten klären |
| stable-audio-tools | https://github.com/Stability-AI/stable-audio-tools | MIT, aktiv | Audio-Generierung, Forschungs-/Trainingsbasis | Modell-Lizenzen separat; VRAM |

## Minecraft-Modding (Eternal Bonds / SMP)
| Referenz | Link | Lizenz / Pflege | Einschätzung |
|---|---|---|---|
| NeoForge | https://github.com/neoforged/NeoForge | LGPL-2.1, aktiv (26.10.2026) | Moderne Forge-Linie; Wahl hängt von deiner Zielversion ab, **welche Loader/Version deine Projekte nutzen, ist hier nicht bekannt** |
| Fabric API | https://github.com/FabricMC/fabric-api , https://fabricmc.net/ | Apache-2.0, aktiv | Leichtgewichtiger Loader; gleiche Einschränkung |

## Weiterhin ungeprüft
Manga-/Comic-Werkzeuge im engeren Sinn (Panel-Layout, Schrift, Konsistenz von Figuren), Spracherkennung für Sprachbefehle beim Gaming, konkrete Erfahrungsberichte zu Dauerbetrieb von ComfyUI auf 6 GB VRAM. Dafür liegt keine geprüfte Quelle vor.

## Neuer Vorschlag aus der Recherche
### N-01 JARVIS-Ergebnisse und Incidents per ntfy aufs Handy (P2)
- **Problem:** Ergebnisse/Incidents sind nur im Portal sichtbar. **Lösung:** Watchdog-Incident (offen > 2 h) und fertige Aufträge senden eine kurze ntfy-Nachricht (nur Titel/ID, keine Inhalte). **Nutzen:** Du erfährst es, ohne das Portal zu öffnen. **Umfang:** kleines Sendemodul + Thema + Test. **Aufwand:** ~2 h. **Kosten:** keine. **Risiken:** Nachrichten verlassen den Server nicht (eigener ntfy), Zugangsdaten über vorhandenes Verfahren. **Abnahme:** Testnachricht erscheint auf dem Handy, Incident-Simulation im Testthema. **Rollback:** Sender abschalten.
