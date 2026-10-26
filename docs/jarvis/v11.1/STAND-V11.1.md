# MA-Home Cognitive Brain V11.1: Audit-Korrekturen und Laptop-JARVIS – Bericht

**Stand:** 14.10.2026 · Basis: V11 (`STAND-V11.md`) · Auftrag: `MA-Home-V11-Audit-und-V11.1-Auftrag.md`
**Umgebung:** isolierter Linux-Container (2 CPU, 8 GB, Python 3.13), **nicht dein Laptop**.
**Zugang zu Laptop/Server, MA Auto Router, Vault, API-Schlüsseln:** weiterhin keiner (Ordnerfreigabe
abgelehnt, keine Schlüssel). Nichts davon wurde umgangen. Keine Konten angelegt, keine echten
Cloud-Anfragen, keine Kosten.

Legende: **getestet** = hier praktisch geprüft · **gemessen** = mit Zahlen · **simuliert** = lokaler
Fake-Anbieter statt echtem Dienst · **blockiert** = fehlt Zugang/Freigabe

## 1. Audit-Befunde: alle vier bestätigt und behoben (Tests zuerst rot, dann grün)

Die Regressionstests (`tests/test_v111_regressions.py`) liefen zuerst gegen den unveränderten V11-Code:
**16 rote Fälle in allen vier Familien** (11 Fehlschläge + 5 Fehler; Protokoll `evals/v111_red.log`), danach grün.

| # | Befund | Ursache | Korrektur | Datei |
|---|---|---|---|---|
| P0-1 | Schattenmodus rief Helfer auf, wenn der Router `helper:*` nannte | Zuverlässigkeitsprüfung nur in `active` | Schattenmodus führt **immer** den V10.1-Status-quo aus und protokolliert die Router-Wahl nur. Geprüft für public/internal/private, mit und ohne Router | `route_policy.py` |
| P0-2 | Injizierte, leere, erfundene oder unbelegte Antworten wurden als „verified“ gezählt | Die Paket-Prüfung (`packet-ok`) wurde als Qualitätsbeweis benutzt | Strikte Trennung: Prüfaktion = nur **Vorbedingung** (läuft jetzt *vor* dem Aufruf: scheitert sie, wird kein Token ausgegeben). Die **Antwort** prüft das neue `helper_verify.py` deterministisch: JSON mit Ursache + wörtlichen Zitaten, die im Material vorkommen müssen. Verdächtig/leer/unbelegt/erfunden → abgelehnt, zählt **gegen** den Helfer, nächster Helfer oder Claude-Queue. Verdächtige Antworten können auch per direktem Aufruf nie als Erfolg markiert werden. Altdaten: falsch gezählte Erfolge werden beim Start auf 0 gesetzt und in `helper_audit` protokolliert. Eine Diagnose schließt nie eine Störung, das tut nur der Sensor (Test) | `executive.py`, `helper_verify.py`, `provider_adapter.py` |
| P1-3 | `daily_token_budget` deklariert, aber nicht durchgesetzt; Budgets bei Parallelität überschreitbar | fehlende Prüfung; Prüfen und Senden nicht atomar | Token-Budget je **Identität + Projekt** und optional `global_daily_token_budget`. Vor dem Senden wird konservativ reserviert (⌈Zeichen/3⌉ + 32 + `max_tokens`), in **einer** `BEGIN IMMEDIATE`-Transaktion mit allen Limits (prozess- und threadsicher). Nach der Antwort wird auf die echte Nutzung korrigiert; unbekannte Nutzung (Timeout, keine `usage`) bleibt mit der Reservierung gezählt. Tag = gleitende 24 h (zeitzonenunabhängig). Überlebt Neustarts (liegt in der DB) | `provider_adapter.py` |
| P1-4 | Ohne Schattenaufrufe entsteht nie Vertrauen | – | Neues `canary.py` + `daemon.py … canary`: nur bei `canary.enabled=true`, nur öffentliche Fälle (Klassifizierung erzwingt `public`, Personendaten/Secrets werden nie gesendet), Obergrenze je Lauf (Standard 3, max. 20), alle normalen Budgets. Ergebnisse mit `origin='canary'`. Mitgeliefert: **10 öffentliche Standard-Störungen** (`canary-suite.example.json`), bei denen die Antwort zitieren **und** die richtige Ursache nennen muss | `canary.py`, `helper_verify.py` |

**Zusätzlich gefunden und behoben:**
- **Absturz bei leerer Helferantwort (V11):** Der Executor warf `ValueError` beim Speichern, der Daemon-Tick brach ab. Jetzt wird die Antwort als „leer“ abgelehnt.
- **Rennen bei der Datenbank-Migration:** Starten zwei Prozesse gleichzeitig (z. B. Daemon und Canary-CLI), kollidierte das Hinzufügen der neuen Spalten. Der Thread-Test zeigte es in 3 von 8 Läufen; jetzt 15/15 grün. Neue Datenbanken haben die Spalten direkt im Schema.

## 2. Gemessen: V11 vs. V11.1, identische Szenarien (simuliert, `scripts/measure_v111.py`)

| Messgröße | V11 | V11.1 |
|---|---|---|
| Korrekt belegte Antwort → Schritt erledigt | 1/1 | 1/1 |
| **Falsch als erledigt markiert** (unbelegt, erfunden, injiziert) | **3 von 4** | **0 von 4** |
| Falsche Vertrauenspunkte für den Helfer | 3 | 0 |
| Abstürze (leere Antwort) | 1 | 0 |
| Schattenmodus, Router nennt Helfer: führt Helfer aus? | ja | nein (Claude-Queue wie V10.1) |
| 10 parallele Anfragen bei Aufruf-Budget 3: beim Anbieter angekommen | **10** | **3** |
| Token-Budget 0: beim Anbieter angekommen | 1 | 0 |
| Daemon-Eigenverbrauch mit Performance-Messung (Median 5×200 Ticks) | 10,7 ms/Tick | 10,2 ms/Tick (gleich innerhalb Messrauschen) |

Bedeutung für dich: Die 3 falschen „Erledigt“-Meldungen in V11 wären versteckte Nacharbeit gewesen
und hätten einem unzuverlässigen Helfer Vertrauen und damit später echte Aufträge verschafft.
**Ehrliche Grenze:** „belegt“ heißt, die Antwort zitiert echte Zeilen. Dass die genannte Ursache die
wahre ist, prüft nur der Canary mit bekannten Ursachen; im Betrieb bleibt sie eine Hypothese, bis
der Sensor die Behebung zeigt.

## 3. Laptop-JARVIS: was zusätzlich verbessert wurde

| Fähigkeit | Umsetzung | Status |
|---|---|---|
| **Ursachen untersuchen** | Bei CPU- oder RAM-Druck nennt die Performance-Intelligenz die größten Verbraucher (Prozessname, CPU-%, RSS; nie Argumente oder Umgebung). Erfasst **nur unter Druck**: ohne Druck kein Prozess-Scan. Der Scan kostet ≈ 4 ms bei 70 Prozessen. Steht in der Ereignis-Evidenz, `perf` und `causes()` | getestet mit echtem CPU-Fresser |
| **Ergebnis je Verbrauch messen** | `daemon.py … scoreboard`: verifizierte Aufträge/Schritte nach Herkunft (lokal/Helfer/Claude), Wiederholungsfehler (= Nacharbeit), Claude-Jobs + Tokens + Listenpreis, Helfer-Aufrufe + Tokens + Kosten, Brain-Eigen-CPU, Kennzahlen „Schritte je Claude-Job“, „Claude-Tokens je verifiziertem Schritt“, „Anteil ohne Claude“ | getestet |
| **Ressourcen hart begrenzen** | systemd-Unit: `CPUWeight=20`, `IOWeight=20`, `IOSchedulingPriority=7`, `MemoryHigh=384M` (bremst vor dem Abbruch), dazu wie bisher `CPUQuota=50%`, `MemoryMax=512M`, `Nice=10`. Deine Dienste haben Vorrang | getestet (Unit-Text) |
| **Tokens sparen** | Helfer wird nur noch gefragt, wenn die Vorbedingung erfüllt ist. Die Antwort kommt als kurzes JSON statt als Freitext. Abgelehnte Antworten kosten keinen Claude-Lauf, wenn ein zweiter Helfer im Budget ist | getestet |
| Beispielkonfiguration | `actions.example.json` mit `diagnose-hint` (Helfer + Claude-Fallback + Prüfer); `providers.example.json` mit Token-/Global-Budget 0 und Canary aus | validiert |

**Nicht umgesetzt (bewusst):** serverweite Optimierung (Dienste neu starten, Swappiness, Governor
usw.). Laut Audit erst nach Ursachenanalyse auf der echten Hardware, mit eigens erlaubten,
reversiblen Allowlist-Aktionen. Der Autopilot ändert weiter nur die 4 eigenen Brain-Einstellungen.

## 4. Tests

| Suite | Tests | Ergebnis |
|---|---|---|
| `brain-runtime/tests` (180 V10.1 + 39 V11 + 24 V11.1) | 243 | OK, `-X dev`, ResourceWarnings als Fehler, **0 übersprungen** |
| `tests` · `scientific-brains/tests` · `humanizer-local` | 9 · 7 · 6 | OK |
| Mutationsprobe V11+V11.1 (`scripts/mutate_v111.py`, 48 eingebaute Sicherheitsfehler) | 48 | **47 erkannt**. Der eine nicht erkannte („Prompt ohne Schwärzung“) ist äquivalent: Secrets werden vorher als `secret` klassifiziert und nie gesendet. Die Probe deckte zwei Testlücken auf, beide geschlossen: Canary mit erlaubtem privatem Egress, leere Antwort bei jedem Prüfertyp |

**Geänderte V11-Testerwartungen** (weil sie den Fehler festschrieben): Die zwei Tests, die eine
unbelegte Freitext-Antwort als Erfolg erwarteten, verlangen jetzt eine belegte Antwort. Der Injection-Test
erwartet Ablehnung statt Abschluss. Der Lern-Test prüft jetzt, dass bei gescheiterter Vorbedingung kein
Aufruf erfolgt. Die Budget-Meldung heißt genauer `daily call budget exhausted`.

**Übersprungene Tests:** hier 0. Auf Systemen ohne PSI (`/proc/pressure` fehlt, z. B. Kernel mit
`psi=0`) werden 2 PSI-Tests übersprungen, so wie im Audit beobachtet.

## 5. Abnahmekriterien V11.1

| # | Kriterium | Status |
|---|---|---|
| 1 | Vier Fehlerfamilien zuerst rot, dann grün | **erfüllt** (16 rot → grün) |
| 2 | Schattenmodus: null Helferaufrufe, auch bei `helper:*` | **erfüllt** (Test + Messung) |
| 3 | Verdächtige/leere/falsche Antworten: kein verifizierter Gewinn | **erfüllt** |
| 4 | Budgets bei Parallelität und Neustart | **erfüllt** (Threads; mehrere Prozesse über SQLite-Sperre; Neustart-Test) |
| 5 | Alle Tests grün, Übersprungene ausgewiesen | **erfüllt** |
| 6 | Keine private/geheime Weitergabe ohne Egress-Regel | **erfüllt** (unverändert + Canary nur public) |
| 7 | Produktionsintegration nur mit Zugang | **blockiert** (kein Zugang) |
| 8 | Echte A/B-Zahlen mit Qualität, Latenz, Nacharbeit, Verbrauch auf ≥ 10 Aufgaben | **blockiert**. Werkzeuge bereit: 10-Fall-Canary-Suite, `scoreboard`, `measure_v111.py`. Alle Zahlen oben sind simuliert |

## 6. Reihenfolge auf deinem Laptop (nur durch dich)

1. Entpacken, `python3 -m unittest discover -s brain-runtime/tests`, `python3 server/inventory.py > inventory.json`.
2. Daemon mit Beispielkonfiguration (Cloud aus, Router `shadow`) 24 h laufen lassen → `perf`, `scoreboard`.
3. Router: `router.cmd` auf deinen MA Auto Router (Vertrag: `ROUTER-INTERFACE.md`). Im Schattenmodus entstehen null Helferkosten.
4. Falls du Helfer willst: Konto **selbst** anlegen, Schlüssel 0600, `providers.json` mit `cloud_enabled`, Egress nur `public`, kleinen Budgets (z. B. 20 Aufrufe / 20 000 Tokens pro Tag), `canary.enabled: true` → `daemon.py … canary --provider groq --suite brain-runtime/canary-suite.example.json` (3 Aufrufe je Lauf). Erst bei ≥ 10 geprüften Fällen mit ≥ 80 % Erfolg kommt `router.mode: active` infrage, dann Diagnose-Aktion `diagnose-hint`.
5. Nach 2 Wochen `scoreboard` mit dem Stand vorher vergleichen. Das ist die echte A/B-Zahl.

## 7. Rollback

Ohne `providers`/`router`/`autopilot` in `daemon.json` verhält sich V11.1 wie V10.1. Die Helfer-DB wird
beim ersten Start automatisch erweitert (2 Spalten, 1 Tabelle). V11 kann sie weiter lesen. Komplett
zurück: V11- oder V10.1-Paket entpacken. Nichts wird automatisch gelöscht.

## 8. Blockiert

| Punkt | Was ich brauche |
|---|---|
| Laptop-Inventur, Sicherung, echte Messung | Zugang oder die Ausgaben von `inventory.py`, `perf`, `scoreboard` als Datei |
| Echter MA Auto Router | sein Aufruf / Ein- und Ausgabeformat |
| Echte Helfer, Canary, A/B | dein Entschluss, selbst einen Free-Key anzulegen, und ein Kostenlimit |
| Zwei echte OS-Konten auf dem Server | Serverzugang |
