# Stimmvergleich und mobile Prüfung (Ursprungsauftrag §10, §12, §13) – 27.10.2026

## A. Mobile Prüfung (Browser-Emulation, KEIN reales Android/iOS-Gerät)
Prüfpunkte 320/360/390/430/768/1280 px × 14 Ansichten, Staging-Portal über Testproxy. Messung per DOM (Überlauf, Zielgröße, Überdeckung via elementFromPoint), axe-core.

Vorher (390 px): 28 Menüeinträge als horizontale Leiste 37 px hoch, Palette-Knopf mehrzeilig gequetscht, Menü dauerhaft sichtbar, Touchziele überwiegend < 44 px (~324 pro 14 Ansichten).
Umgesetzt (live auf Staging/Produktiv `/`):
- Untere Tab-Leiste (Zentrale, Chat, Aufgaben, Agenten, Mehr) ≤ 720 px, 56 px hoch, Safe-Area, `aria-current`.
- „Mehr“ öffnet das vollständige Menü (20 Einträge, je ≥ 48 px) als Vollbild-Blatt; schließt bei Auswahl und mit Escape.
- Bildschirmtastatur: Leiste wird bei fokussiertem Eingabefeld ausgeblendet; Leiste verschwindet (belegt), aber das Eingabefeld selbst bleibt in der Simulation NICHT sicher sichtbar – siehe offener Befund.
- Palette-Knopf als 44×44-Icon, Eingabefelder ≥ 44 px und 16 px Schrift (verhindert iOS-Auto-Zoom), Checkboxen 24 px.
Nachher: kein horizontaler Überlauf in allen 6 Breiten × 14 Ansichten; ≤ 12 kleine Ziele je Breite (vorher ~324; Reste: Eingaben cdep/csudo/vspk/mseek, ein paar Links/Buttons in Musik/Voice/Dashboard); axe WCAG 2.x A/AA: 0 Verstöße in Slate und Arc (8 Ansichten, 390 px).
Ebenfalls geprüft: Textgröße 200 % ohne Überlauf (4 Ansichten), Querformat 844×390, viewport-fit=cover, Safe-Area- und dvh-Regeln vorhanden.
**Offen/Grenzen – DEFEKT M-01:** Tastatur-Simulation (Fensterhöhe 420 px): Die Messung zeigte die Feld-Unterkante bei 455 px bei 420 px Fensterhöhe, d. h. der Chat-Eingabeblock (Ordner/Rechte/Modell, zwei Checkboxen, Feld, ca. 290 px) ist höher als der Restbereich und das Feld liegt unterhalb des sichtbaren Bereichs (identisch schon vor meiner Änderung). Fix-Vorschlag: Optionen auf Mobil einklappen; echtes Tastaturverhalten (VisualViewport) ist NICHT verifiziert. 3 Elemente (voice-Auswahl, Musik-Knöpfe) liegen im Startzustand unter der Leiste; Erreichbarkeit per Scrollen nicht gesondert geprüft. Kein Real-Gerät, kein Streaming-Scrolltest, kein Upload-/Mikrofontest am Handy, keine Wiederverbindungsprüfung.

## B. Stimmvergleich (identische 5 Testsätze + 1 Langtext)
Hörproben: `stimmen/` (WAV/MP3). Messwerte: `stimmen/messwerte.json`. Gemessen auf dem PC (Ryzen 5 3600, CPU). **Natürlichkeit und Aussprache habe ich nicht beurteilt – ich kann nicht hören; das ist Owner-Urteil.**

| Kandidat | Art | Lizenz | Erzeugung kurzer Satz (Ø) | Langtext (≈13 s Audio) | Datenschutz | Kosten |
|---|---|---|---|---|---|---|
| Piper Thorsten **high** | lokal, ONNX 114 MB | Datensatz CC0 | 0,57 s (Echtzeitfaktor ≈ 0,2) | 2,5 s | vollständig lokal | 0 |
| Piper Thorsten_emotional **medium** | lokal, 77 MB | laut Model Card prüfen (nicht verifiziert) | 0,11 s (RTF ≈ 0,04) | 0,56 s | lokal | 0 |
| Edge TTS de-DE-ConradNeural | Cloud (Microsoft, inoffizieller Zugang) | Dienstbedingungen, kein Produktvertrag | 1,67 s | 4,1 s | Text geht an Microsoft | 0, aber Rechtsstatus unklar |
| Edge TTS de-DE-KillianNeural | wie oben | wie oben | 1,54 s | 6,0 s | wie oben | wie oben |
| ElevenLabs | Cloud, kostenpflichtig | Voice-Library je Stimme | NICHT GETESTET (kein Schlüssel, keine Käufe) | – | Cloud | Abo |

Nicht vorgelegt: Karlsson (16 kHz, low) und Pavoque (CC BY-NC-SA, nicht kommerziell) – Qualität/Lizenz ungeeignet. Erste Piper-Messung (7 s) war Kaltstart.
Integration: Hermes kennt Edge, ElevenLabs, OpenAI, NeuTTS; Piper kann laut Tool-Schema als „command“-Provider (`tts.providers.<name>`) angebunden werden – Konfiguration nicht ausgeführt (Profiländerung). Keine Schauspielerstimme nachgebildet.
Empfehlung (Hypothese bis Hörtest): Piper Thorsten high als lokale Standardstimme (CC0, offline, schnell genug), Edge als optionale Cloudvariante, ElevenLabs nur nach Hörprobe und Budgetfreigabe.

## C. Spracharchitektur (Vorschlag, nichts installiert)
Mikrofon (Push-to-talk, Browser) → Browser-STT (Einwilligung vorhanden) oder lokales faster-whisper → Textauftrag im bestehenden Chat/HQ → gespeicherter Auftrag → Rückmeldung per TTS (Piper-Command). Wakeword optional und bisher nur im Einzelmodus belegt. Kein LiveKit/Pipecat: kein nachgewiesener Zusatzbedarf. Kritische Aktionen nur mit Bestätigung; Sprach-Freitext bleibt lesend.

## Nachtrag: M-01 behoben (27.10.)
Chat-Optionen (Ordner/Rechte/Modell + Admin-Schalter) sind auf Mobil und bei Fensterhöhe ≤ 500 px in ein Einklapp-Element „Optionen“ (44 px) gefasst, bei offener Tastatur ausgeblendet; auf Desktop offen wie bisher. Gemessen (Emulation): Fensterhöhe 420 → Eingabefeld 317–381 sichtbar, 320 → 192–256, Querformat mit Fokus (Höhe 200) → 118–180; Desktop unverändert; axe 0 Verstöße (zu/offen). Grenze: Querformat 844×390 ohne Fokus liegt das Feld weiter unter dem Rand (Seite scrollbar); reale Bildschirmtastatur (VisualViewport) weiter nicht an echtem Gerät geprüft. Backups `*.bak-vor-m01`.
