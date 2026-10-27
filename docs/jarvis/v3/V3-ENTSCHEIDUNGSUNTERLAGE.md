# V3 – Entscheidungsunterlage (Stand 27.10.2026)

Alles unten ist **Vorschlag, nichts davon ist umgesetzt**, außer wo „Status“ etwas anderes sagt. Genehmigen, ändern, zurückstellen oder ablehnen per ID. Aufwand ist grobe Schätzung, nicht gemessen. Kosten: kein Pay-as-you-go; alle Vorschläge nutzen vorhandene Abos/Hardware, sofern nicht anders vermerkt.

## Gesamtbewertung autonomer Betrieb
**GO unter Auflagen für den bisherigen Funktionsumfang** (Gate 24/0/0, Spezialisten 18/18, Rollback real geprüft, Router/Status/Ledger/Telemetrie live belegt, Gateway-Fix aktiv). **NICHT BEURTEILBAR** für: Windows-Worker-Ausführung (Sandbox lässt sich nicht anlegen), akustisches Wakeword, physischen Druck. Belege: `V3-ABSCHLUSS-GATES.md`, `V3-RESTAUFTRAG.md`, `A7-ABNAHME-20261027.md`.

## Empfohlenes Gesamtpaket
Zuerst alle **P0/P1**, danach U-01 und U-02; P3 nur einzeln und nach Basisabnahme.

---

## P0 – Sicherheit, Datenverlust, gefährliche Doppelaktionen

### S-01 Schutz der Portal→Host-Agent-Freigabe gegen Neuprovisionierung
- **STATUS: UMGESETZT 27.10. (Owner „ja mache alles“), belegt in `V3-ABSCHLUSS-GATES.md`.**
- **Problem:** `ma-home printer-detect` (und Standard-Provisionierung) schreibt `host.json` neu und entfernt `extra_uids/extra_gid`; danach `/api/status`, Preview und Jobs wieder HTTP 500.
- **Lösung:** `host_config()` in `manage.py` so ändern, dass vorhandene `extra_*`-Felder übernommen werden, plus Test und Abbruch bei Verlust.
- **Nutzen:** Verhindert stillen Rückfall eines produktiven Fixes. **Umfang:** 1 Datei, 1 Test. **Aufwand:** ~1 h. **Risiken:** Berührt Provisionierungscode; Agent-Neustart nötig. **Abhängigkeiten:** keine. **Abnahme:** Provisionierung im Trockenlauf behält die Felder; Drei-Wege-Probe (andrew/ma-web erlaubt, nobody verweigert). **Rollback:** Backup `manage.py.bak-…`.

### S-02 Rotation des nexum-Schlüssels
- **Status:** früher als Empfehlung festgehalten, hier **nicht neu geprüft**. **Problem:** Schlüssel war im Arbeitskontext sichtbar. **Lösung:** Neuen Schlüssel beim Anbieter erzeugen, in `~/.config/ma-jarvis/keys/` ersetzen, alten widerrufen. **Aufwand:** ~30 min, **braucht dich** (Anbieterkonto). **Risiko:** kurzzeitiger Ausfall des Fallbacks. **Abnahme:** Fallback-Job läuft mit neuem Schlüssel; alter wird abgewiesen. **Rollback:** alter Schlüssel nur bis zum Widerruf.

---

## P1 – Echte Ausführung, Persistenz, Delegation, Recovery

### E-01 Windows-Worker-Sandbox lauffähig machen
- **Problem:** `CreateAppContainerProfile` → `0x80070005` auf dem PC (normaler Benutzer, mittlere Integrität, kein Job-Objekt; MDM-/Appx-Richtlinie vorhanden).
- **Lösung (Optionen):** (a) Admin-Diagnose mit Process Monitor / Richtlinienprüfung; (b) falls Richtlinie die Ursache ist, gezielte Ausnahme; (c) falls nicht lösbar: Worker bleibt aus, Aufgaben laufen auf Server/Cloud. **Aufwand:** 1–3 h. **Risiken:** Richtlinienänderung betrifft Systemsicherheit — **deine Entscheidung**. **Abnahme:** `probe.py` (5 Prüfungen: Low-Integrity, Schreiben nur im Arbeitsordner, Lesen/Schreiben außerhalb verweigert, Netz verweigert, Timeout) 5/5. **Rollback:** Richtlinie zurücksetzen.

### E-02 Server→PC-Auftrag Ende-zu-Ende mit Gaming-Vorrang
- **Abhängig von E-01.** Harmloser Testauftrag, Abbruch bei Spielstart, Offline-Verhalten. **Aufwand:** 2 h. **Abnahme:** Auftrag läuft, wird bei Spiel abgebrochen/pausiert, Ergebnis im Portal.

### E-03 Debattenbudget technisch durchsetzen
- **Problem:** Budget „3 Runden“ steht nur in SOUL.md. Messung: seit 26.10. noch 2 von 43 Ketten > 6 DMs, längste 17 (vorher 77).
- **Lösung:** Zähler im Chatnetz/`message_agent`-Pfad pro Agentenpaar+Thema, bei Überschreitung Eskalation an JARVIS statt weiterer DM. **Aufwand:** 3–5 h. **Risiken:** Fehlalarme bei legitimen langen Arbeiten. **Abnahme:** Testkette bricht bei Schwellwert kontrolliert ab. **Rollback:** Schalter aus.

### E-04 `kimi-supervisor` im Chat-Bus-Roster
- **STATUS: UMGESETZT 27.10., Mention bis Receiver zugestellt (`delivered target=kimi-supervisor`).**
- **Problem:** Mentions an `@kimi-supervisor` werden nicht extrahiert (`mentions: []`). **Lösung:** Eintrag im Roster in `chat_bus_backend.py`. **Aufwand:** 30 min + Portal-Neustart. **Abnahme:** Mention erzeugt Zustellung (Voraussetzung für D-02).

---

## P2 – Effizienz, Bedienung, Design

### U-01 Lokales Wakeword + lokale Spracherkennung (Phase B)
- **Problem:** Browser-Spracherkennung sendet Audio an den Anbieter; Dauermodus unzuverlässig. **Lösung:** openWakeWord + faster-whisper (+ Piper-Nachfolger für Ausgabe) auf dem PC, Anbindung an das vorhandene Voice-Modul. **Referenzen:** `V3-REFERENZEN.md`. **Aufwand:** 1–2 Tage. **Ressourcen:** GPU-VRAM (Gaming-Vorrang beachten). **Risiken:** GPL-3.0 bei Piper-Nachfolger; Modellgröße vs. 6 GB; Genauigkeit für „Jarvis“ unbekannt. **Abnahme:** akustischer Test mit echter Stimme, ≥ 9/10 Erkennungen, 0 Cloud-Audio. **Rollback:** Browser-Modus bleibt.

### U-02 Router-Restquoten im Command Center
- **STATUS: NICHT UMGESETZT.** Ein Probe-Zugriff auf `council_decisions` (PG, über `db_adapter`) lief in den Timeout; Datenquelle nicht bestätigt, daher keine Anbindung.
- **Problem:** keine Datenquelle. **Lösung:** Evidence-Router-Ledger (liegt auf dem Server) per lesendem Endpunkt anbinden, analog zur Telemetrie. **Aufwand:** 2–3 h. **Risiko:** Portal-Neustart. **Abnahme:** Anzeige gegen Rohdaten verglichen.

### U-03 Funktionstests für die übrigen Skills
- **Status:** 4 Dokument-Skills + maps getestet, ca. 54 nur statisch. **Lösung:** pro Skill ein kleiner harmloser Test (Konten/Daten von dir nötig bei Mail, Kalender, Notion, Airtable, Google). **Aufwand:** 0,5 Tage + deine Zugänge.

### U-04 Pakete für Dokument-Skills in der Hermes-Umgebung
- **STATUS: UMGESETZT, abweichend:** Hermes-Umgebung hat kein pip und blieb unverändert; eigene Umgebung `%LOCALAPPDATA%\hermes\skill-env`, 82 Tests grün.
- **Problem:** `docx/openpyxl/pptx/pypdf/reportlab/pdfplumber` fehlen dort; Skills enden mit Exit 2. **Lösung:** Installation in der Hermes-Umgebung (oder eigene Skill-Umgebung). **Risiko:** Änderung der Hermes-Umgebung — daher deine Freigabe. **Abnahme:** die vier Skill-Testläufe (82 Tests) laufen dort grün.

### U-05 Portal-Barrierefreiheit gegen WCAG 2.2 prüfen
- **Problem:** nie formal geprüft. **Lösung:** Prüfliste (Kontrast, Tastaturbedienung, Fokus, reduzierte Bewegung) und Korrektur. **Aufwand:** 0,5–1 Tag.

---

## P3 – Neue Fähigkeiten

### X-01 Home-Assistant-Anbindung (lesend zuerst)
Voraussetzung: prüfen, ob die Instanz (`ha.ma-server.duckdns.org`) läuft. Zuerst nur Status lesen, Schalten erst nach separater Freigabe.

### X-02 Kreativ-Toolchains (Manga/Bild/Audio/Video/3D, Modding)
Heute **nicht geprüft**, keine Referenz belegt. Vorschlag: erst Bedarf pro Projekt von dir, dann Recherche und isolierter Test.

### X-03 Autonomes Capability-Management
Erst nach Basisabnahme. Ablauf wie in deinem Auftrag (Bedarf → Prüfung → Council → Freigabe → Hermes → isolierter Test → Registry → Rollback).

---

## Supervisor-Einbindung (Vorschlag D-01 … D-03)

**Geprüfte Möglichkeiten:** (1) Hermes-Mentions: die Kette Server→Tunnel→Receiver→`hermes -p <Profil> chat` funktioniert nachweislich für andere Profile; für `kimi-supervisor` fehlt der Roster-Eintrag (E-04). (2) Das Hermes-Werkzeug `cronjob_manage` ist vorhanden; ein geplanter Lauf wurde **nicht** getestet. (3) Ob dein Anbieter-Abo automatisierte, unbeaufsichtigte Aufrufe zulässt, ist **nicht geprüft** — Nutzungsbedingungen vor Einrichtung klären.

| ID | Vorschlag | Auslöser / Intervall | Datenumfang | Rechte | Budget | Eskalation / Ausfall |
|---|---|---|---|---|---|---|
| D-01 | **Manueller Review (sofort möglich)** | Du sagst „Review“ | STATE.md, Watchdog, Telemetrie, Tests lesend | wie jetzt; keine Produktivänderung ohne Freigabe | nur auf Zuruf | – |
| D-02 | **Ereignisgetrigger** nach E-04 | Watchdog-Incident offen > 2 h oder Debattenbudget gerissen | betroffener Incident + 24-h-Kontext | nur lesen + Bericht | max. 1 Lauf je Ereignis, Haiku/Sonnet je Schwere, Obergrenze z. B. 5 Läufe/Tag | Bei Nichterreichbarkeit: Incident bleibt sichtbar im Portal, Meldung an dich |
| D-03 | **Wöchentlicher Review** per Cron | 1× pro Woche | Statusberichte, Ledger, Council-Ketten, Skill-Tests | nur lesen | 1 Lauf/Woche | Bei Fehlschlag nächster Lauf + Hinweis; **keine** dauerhafte Überwachung behauptet |

Empfehlung: D-01 jetzt, D-02/D-03 erst nach Klärung der Abo-Bedingungen und E-04.

---

## Fehlt noch (Transparenz zu deinem Auftrag)
- Designvarianten: es existiert **ein** umgesetztes Konzept (`PORTAL-REDESIGN-KONZEPT-20261027.md`, live). Der Auftrag sah 2–3 Varianten vor Abnahme vor; das wurde nicht erneut aufgelegt. Wenn du Varianten willst: separater Auftrag (ID U-06).
- Referenzsammlung: `V3-REFERENZEN.md` (nur dokumentiert, nichts getestet; Kreativ-/Mission-Control-/Computersteuerungs-Referenzen offen).

Jarvis: Phase C-Vorbereitung, GO unter Auflagen für den belegten Umfang – wichtigster Befund: Windows-Worker-Sandbox lässt sich auf diesem PC nicht anlegen – Entscheidung nötig: E-01 (Admin-Diagnose/Richtlinie) und S-02 (Schlüsselrotation).
