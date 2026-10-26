# MA Auto Router ↔ Cognitive Brain – Schnittstelle (V11)

Das Brain baut **keinen zweiten Router**. `route_policy.py` ist nur ein Adapter: Er fragt deinen
bestehenden MA Auto Router und setzt dessen Entscheidung innerhalb der Brain-Grenzen um.

## Vertrag

Aufruf: `router.cmd` aus `daemon.json` (argv-Liste, keine Shell), Zeitlimit 10 s.

stdin (eine JSON-Zeile):

```json
{"task_type": "diagnose_hint", "risk": "read", "data_class": "internal",
 "size_chars": 5321, "has_procedure": false, "fallback": "claude"}
```

stdout (ein JSON-Objekt):

```json
{"target": "local" | "helper:<provider>" | "claude" | "claude:<modell>" | "human", "reason": "kurz"}
```

- Exit-Code ≠ 0, ungültiges JSON, unbekanntes Ziel oder Zeitüberschreitung → **Status quo**
  (genau das V10.1-Verhalten: bekannter Ablauf lokal, Diagnose über die begrenzte Claude-Queue,
  sonst Mensch). Der Router kann also nichts kaputt machen, indem er ausfällt.
- `data_class` hat das Brain schon bestimmt (strengste Klasse gewinnt: secret > private > deklariert).
  Der Router darf sie nicht herabstufen; er bekommt keinen Inhalt, nur Metadaten.

## Modi

| Modus | Wirkung |
|---|---|
| `shadow` (Standard) | **Nie ein Helfer-Aufruf** (V11.1, auch wenn der Router `helper:*` nennt): ausgeführt wird der V10.1-Status-quo, die Router-Wahl wird nur protokolliert. Zusätzlich wird je Auftrag notiert, welcher Helfer zulässig *gewesen wäre* (`route_shadow`). Vergleich: `daemon.py --config … helpers`. |
| `active` | Ein vom Router genannter Helfer wird nur genutzt, wenn: Cloud an, Provider aktiv, Aufgabentyp angeboten, Egress-Regel für Identität+Projekt+Datenklasse, Budget/Rate-Limit frei, Breaker zu **und** gemessene, unabhängig geprüfte Erfolgsquote ≥ `min_success` über ≥ `min_samples` Aufträge. Sonst Status quo. |

## Vertrauen aufbauen: nur per Canary (V11.1)

`active` verlangt ≥ `min_samples` unabhängig geprüfte Antworten. Diese entstehen **nicht** im
Schattenmodus, sondern ausschließlich durch ausdrücklich freigegebene Canary-Läufe auf öffentlichen
Testfällen: `providers.json → "canary": {"enabled": true, "max_calls_per_run": 3}`, dann
`daemon.py --config daemon.json canary --provider groq --suite brain-runtime/canary-suite.example.json`.
Jede Antwort muss eine Zeile wörtlich zitieren **und** die bekannte Ursache nennen; private
Testfälle werden nie gesendet; alle normalen Budgets gelten.

## Was ein Helfer nie kann

Helferantworten sind untrusted Daten: gespeichert nur als unbestätigte `hypothesis` (bei
Injection-Mustern mit `SUSPICIOUS`), nie ausgeführt, keine Werkzeuge, keine Freigaben, keine
Budget- oder Politikänderung. V11.1 trennt strikt: die Prüfaktion des Schritts (z. B. „Paket
existiert“) ist nur **Vorbedingung**; die Antwort selbst prüft `helper_verify.py` (leer, verdächtig,
ohne wörtliche Belege oder mit erfundenen Belegen → abgelehnt, zählt gegen den Helfer). Eine
Diagnose schließt nie eine Störung, das tut nur das Sensorsignal.

## Offen (blockiert)

Das reale Ein-/Ausgabeformat deines MA Auto Routers ist mir nicht zugänglich. Falls es abweicht:
ein 10-Zeilen-Wrapper-Skript als `router.cmd`, das obiges JSON übersetzt. Produktive Umschaltung
auf `active` erst nach Schattenvergleich auf der echten Instanz.
