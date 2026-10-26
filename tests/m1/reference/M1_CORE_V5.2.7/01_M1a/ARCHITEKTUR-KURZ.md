# M1 — Architekturvertrag (kurz, maßgeblich für diesen Lauf)

## Ziel und Hypothese

JARVIS soll langfristig ein vielseitiger, selbstständig planender, lernender und proaktiv arbeitender **lokal gesteuerter** Assistent werden. Die lokalen Sprachmodelle sollen **für nachgewiesen geeignete Aufgabenklassen** primäre kognitive Arbeit leisten: verstehen, gezielte Beobachtungen anfordern, Hypothesen bilden/revidieren, Abstinenz/Eskalation vorschlagen, Ergebnisse auf Evidenz beziehen.

Dass ein kleines Modell der regelbasierten Alternative überlegen ist, ist **keine A-priori-Tatsache**. M1 darf mit `NO_GO` enden. In diesem Fall bleiben Controller und lokale Taskzustände sinnvoll; für die konkrete Aufgabenklasse wird der bessere deterministische Pfad genutzt, während die lokale KI in Shadow bleibt.

## Autorität

- **Nutzer/Policy:** Legitimes Ziel und genehmigte Grenzen. Keine selbstständige Ausweitung.
- **Lokaler V16-Controller:** Einziger Owner für Task-ID, Ziel, Revision, Budgets, AuthZ, Datenfreigabe, Ausführung, Effect Ledger, Zustand, Offline-Recovery, abschließenden Status.
- **Lokales LLM:** Liefert interpretierbare, strukturiert überprüfbare kognitive **Vorschläge**. Kein direkter Zugriff auf Host-Docker/Secrets/Produktiv-Tools.
- **Cloud/Claude:** Austauschbare anspruchsvolle Hilfsintelligenz bei erlaubter Nutzung; niemals Task Owner.
- **Verifier/Oracle:** Bewertet beobachteten Zustand unabhängig vom Modelltext und benennt ausdrücklich, welche Behauptung verifiziert ist.

## Ein Taskvertrag

Originalanfrage (unveränderlich) + klassifiziertes Ziel + Nichtziele + Scope + Datenklassifikation + Nutzer/Rechte + Budgets + Tool-Allowlist + erwartete Evidenz + Checkpoints + Taskstatus. Modelle dürfen eine Änderung vorschlagen, aber nicht selbst den ursprünglichen Nutzerauftrag umdeuten oder Berechtigungen verändern.

## Minimaler Ausführungspfad

`User → TaskContract → lokale Beobachtungen/Memory-Retrieval → lokaler kognitiver Vorschlag → Policy+Tool-Allowlist → isolierte read-only Tool-Aktion → Observation-ID → Hypothesenrevision → Verifier/Oracle → Status+Trace`.

Klar trennen: *Dienst erreichbar* / *Ursache bestätigt* / *Hypothese plausibel* / *noch unklar*. Strukturierte JSON-Ausgabe ist nicht semantische Qualität. Der Controller muss ohne Modellstart funktionsfähig und nach Neustart fortsetzbar bleiben.

## Einfache Regeln gegen Doppelarbeit

Vorhandenen MA Auto Router, Cognitive Brain, Tasklogik, Portal und Tests verwenden, sofern passend. Keine zweite Router-/Memory-/Agentenplattform. M1a braucht keinen großen Wissensgraphen, keine neue GUI, keine Sprachsteuerung, keine 3D-Funktion und keine autonomen Skill-Downloads.

## Safety/Vertrauen

M1 nutzt nur isolierte Testdaten und echte Betriebssystem-/Prozessisolation für behauptete read-only Tools. Logs/Configs/MCP-Output sind untrusted. Kein Produktions-Docker-Socket, keine Cloud mit lokalen Secrets, keine Modellentscheidung ersetzt eine Toolberechtigung. Langfristige Rechteprofile pro Nutzer getrennt.

## Einführungsstufen

`OFF → MOCK/FIXTURE → SHADOW (echtes lokales Modell) → ASSIST (je Klasse nach Freigabe) → LEAD (nur getestete Klasse, innerhalb Policy)`.

M1a endet vor echter Modellinferenz. M1b ist getrennt freizugeben. M1b-Ergebnis kann `GO`, `LIMITED_GO`, `NO_GO` oder `INCONCLUSIVE` sein; Fehler dürfen nicht durch neue Architekturvorgaben versteckt werden.

## Quellen/Rückverfolgbarkeit

Jeder Befund nennt Code-Version/Pfad, Laufdatum, tatsächlichen Laufmodus (`MOCK`, `REAL_LOCAL_MODEL`, `REAL_CLOUD`), Modelle/Runtime/Quantisierung, Seed-/Fixture-Fingerprint und Beobachtungs-IDs. Erkenntnisse ohne passenden Messlauf bleiben Hypothesen. Das große V5.1 bleibt Referenz, ist nicht auszuführen.


## V5.2.5 – H-Evidenzgrenze
H darf nur einen hostautorisierten Lesezugriff (Tool + Parameter aus dem Host-Katalog, innerhalb des für D und H gleichen Lesebudgets) vorschlagen. Die lokale KI darf passende Faktenreferenzen liefern (Grounding), aber keine finale Kausalität bestätigen. Finaler Ursachenstatus braucht einen erneuten unabhängigen D-Recheck, dessen Beleg die durch B enthüllte neue Beobachtung enthält. Das Fixture muss selektionssensitiv sein, sonst kann H nichts zeigen. Siehe `FIXTURES-ORACLE-HOLDOUT.md` und `04_TOOLS/hybrid_evidence_gate.py`.

## V5.2.6 – Vorab-Branching statt D-Restbudget

Der lokale D-Preflight bewertet **nur initial sichtbare Evidenz** und löst ohne Zusatzreads entweder `D_CLEAR`, `D_ABSTAIN` oder `D_OBSERVATION_CONFLICT` aus. Im Evaluator starten D und H **aus demselben eingefrorenen Anfangssnapshot** mit **eigenen** vollständigen Read-Budgets. Bei D_CLEAR wird B nie aufgerufen und das Ergebnis H=D. Bei Triggern kann B für H einen zulässigen zusätzlichen Read vorschlagen, auch wenn D seinen parallelen Vergleichs-Read bereits aufgebraucht hat. Damit ist der Vergleich weder durch Vorverbrauch von D verzerrt noch durch Zusatzbudget für H manipuliert. Laufzeit-Evidence-Gate und Oracle bleiben strikt getrennt; `required_proof_sets` werden nur vom unabhängigen Evaluator ausgewertet.

### V5.2.7 – Prüfbarkeit der Belege und Erreichbarkeit von Beobachtungen

Evaluatorseitig ist `required_proof_sets` eine Liste **exakt zulässiger**
Belegmengen. Zum Bestehen müssen die gemeldeten IDs genau eine der
Alternativen bilden (Mengenvergleich; Reihenfolge beliebig). Gültige,
aber für dieses Proof-Set nicht erforderliche zusätzliche IDs werden
als Padding abgelehnt. Ein vollständiges Proof-Set ist eine Bedingung des
synthetischen Oracles, keine allgemeine kausale Garantie; D-Recheck und
Policy-Grenzen bleiben getrennt und dürfen den Oracle nie einsehen.

Schema v1.3: Beobachtungen ohne `reveal_on` sind **immer initial**
(`available_at_step=0`). Eine spätere Beobachtung braucht explizites
`reveal_on` mit genehmigtem Tool und Parametern; andernfalls ist sie
unerreichbar und das Fixture unzulässig. `FixtureReadBranch` setzt
`user_context` vor seiner ersten öffentlichen Zustandsausgabe.
