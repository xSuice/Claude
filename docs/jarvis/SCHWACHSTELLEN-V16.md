# JARVIS V16 – Schwachstellen, priorisiert (Phase H, Entwurf, 2026-10-15)

Quelle: `STAND-V16.md`, `BENCHMARK-V16.md`, Übergabe vom 2026-10-15. **Keine neuen Messungen.** Die Reihenfolge ist eine Einschätzung (Wirkung × Risiko), kein Messergebnis. Sobald der Benchmark läuft, mit echten Zahlen neu ordnen.

## Priorität 1: Aussagekraft fehlt

| # | Schwachstelle | Beleg | Nächster Schritt |
|---|---|---|---|
| 1 | Token-Ersparnis nur n=1 (−61 %), B (Claude direkt) fehlt ganz | `STAND-V16.md` Z. 42 | Benchmark T01 bis T12, je A/B/A2, mind. 3 Wiederholungen; Held-out T03, T05, T08, T10 zuletzt |
| 2 | Benchmark blockiert: 5h-Fenster 87 % (Grenze 70 %), 27/40 Aufrufe, 27/30 Identität | `usage` 2026-10-15 | Warten, dann in kleinen Chargen (3 Aufgaben) |
| 3 | Last während eines Jobs nie gemessen (nur Leerlauf) | `STAND-V16.md` Z. 60 | `measure_v16_load.py` bei Charge 1 mitlaufen lassen; Home-Assistant-Latenz prüfen |

## Priorität 2: Sicherheit und Freigabe nur im Test belegt

| # | Schwachstelle | Beleg | Nächster Schritt |
|---|---|---|---|
| 4 | `human`-Schritt und `approve` nur im Unit-Test, nicht live | Übergabe | Einen echten Auftrag mit Freigabe durchspielen (BACKLOG B38) |
| 5 | Gate B (Fehlerpfade, Korrekturrunden) und Plan-Guard nur gegen Fakes | `STAND-V16.md` Z. 48 | Bei Benchmark-Läufen echte Korrekturrunden mitzählen |
| 6 | Vorlage mit schwacher Abnahme kann Fehler als Erfolg lernen | Übergabe „Fallen“ | Nach jedem Abnahmefehler Vorlage prüfen; Idee: nur bei bestandener Qualitätsprüfung lernen (nicht gebaut) |
| 7 | PC-Worker ohne Sandbox, mit Netz; bleibt aus | `STAND-V16.md` Z. 25 | Erst Sandbox (Phase F Rest), dann `jarvis-pc.json` |

## Priorität 3: Fähigkeiten und Betrieb

| # | Schwachstelle | Beleg | Nächster Schritt |
|---|---|---|---|
| 8 | `doc.pandoc` einmal „Cannot allocate memory“ (Server 3,2 GB) | `STAND-V16.md` Z. 59 | Wiederholung bei Speicherdruck im Worker; beobachten |
| 9 | `ollama.ask`, `blender.render` am PC ohne Adapter | `STAND-V16.md` Z. 61 | Nur bauen, wenn Aufgaben es brauchen |
| 10 | Cron statt User-Dienst, kein eigenes OS-Konto | `STAND-V16.md` Z. 54 | Braucht sudo (Philipp): `loginctl enable-linger andrew` |
| 11 | Externe Helfer aus, kein Schlüssel/Budget | `STAND-V16.md` Z. 24 | Entscheidung Philipp |
| 12 | `Claude:`-Kennzeichnung gebaut, Bridge nicht aktualisiert; Leserecht auf `brain-runtime` ungeprüft | Übergabe | `sudo bash ~/MA-Server/server/claude-bridge/update-bridge.sh`, dann Testfrage |

## Bereits behoben (Phase F)
- `doc.office_pdf` lief im Jail nicht (`private_tmp` nur für diese Fähigkeit); `pdf.to_png` hat Selbsttest. Release `20261015-040726-91bb3b8`, doctor ok.

## Offene Entscheidungen für Philipp
1. Probelauf-Gate AN lassen (`max_trials_per_day` 3, `allow_neutral` aus)?
2. T01 als Zähler-Aufgabe statt Primzahlen bestätigen (Abweichung im Bericht nennen).
3. Bridge-Update ausführen (sudo).
