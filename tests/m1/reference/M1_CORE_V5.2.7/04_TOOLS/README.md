# M1a/M1b – kleine überprüfbare Hilfsprogramme

- `freeze_artifacts.py`: **Git-Tree-Hash statt handgepflegte Dateiliste**. Phase D: ganzer sauberer Teilbaum `tests/m1/` (inkl. D, H-Trigger, Oracle, Generator, Scorer, Schwellen, Statistiktool und Abhängigkeiten); Phase B: kompletter sauberer Git-Tree nach maximal vier DEV-Iterationen. Receipt nur **außerhalb** Claude-Schreibzugriff. Git-Hash erkennt Drift, verhindert aber keine Änderungen.
- `holdout_commitment.py`: Key + echtes Holdout-Manifest ausschließlich unter fremden Evaluator-Rechten, öffentlich nur HMAC-Digest. Nicht innerhalb Claude Code starten, solange private Dateien für ihn sichtbar sind.
- `validate_fixture.py`: Schema- (v1.3), Zeitzonen-, Katalog- und Querverweisprüfung; für S4/S5 erzwingt es Selektionsdruck (`SELECTION_TRIVIAL`/`SELECTION_UNSOLVABLE`). Benötigt `jsonschema` in der Evaluator-/Dev-Umgebung (nach bereits vorhandener Installation prüfen; kein automatisches Setup). Die unbekannten echten Templates kommen von unabhängigem Evaluator, nicht von Claude Code.
- `hybrid_evidence_gate.py`: M1a-Referenz für den oraclefreien Hybridpfad: ein Lesevorschlag mit Tool + Parametern aus dem Host-Katalog, Budget- und Duplikatprüfung, Rückgabe `grounded` (kein Relevanz-/Kausalbeweis); Diagnose nur nach unabhängigem D-Recheck, dessen Beleg die neu enthüllte Beobachtung enthält. Keine produktive Sandbox.
- `paired_bootstrap.py`: gepaartes **Cluster**-Bootstrap nach `family_id` (20.000, Seed 20261016) für die Gruppen easy S1–S3, improvement S4–S5, S6; erzwingt ≥30/60/30 Paare, ≥6 Familien je Stratum, keine Familie >35 %, H=D ohne Trigger; gibt Zellen-Konsistenz und ein nur diagnostisches fallbasiertes CI aus. Vor Holdout unter `tests/m1/` versionieren/frieren; Ergebnisse sind nur so gut wie unabhängige Oracle-Scores.
- `selection_sensitivity.py`: Fixture-Gültigkeit ohne LLM: Anteil der S4/S5-Fälle, die unbegrenztes D löst und budgetiertes D nicht (min. 0,30), sonst `FIXTURE_SELECTION_INSENSITIVE` → `INCONCLUSIVE`.
- `g4560_model_smoke.sh`: erst **nach Freigabe M1b** auf echtem G4560 mit echtem Modell; führt echte GPU (`-ngl 99`) und CPU (`-ngl 0`) Inferenz aus, prüft Exitcodes und schreibt Logs. GPU-Offload anhand Log/VRAM **zusätzlich** bestätigen; Meldung `SMOKE_OK` beweist nur Token-Ausgabe beider Aufrufe.
- `test_tools.py`: Offline-Regressionstests (Git-Freeze, HMAC und Dummy-Schema und Bootstrap). Ohne echte Hardware/Modelle.

## Freeze-Aufruf (im bestehenden Git-Repository; externe Receipt-Pfade)

```bash
# alle Pfade ersetzen; VOR Aufruf tests/m1 samt aller Imports+Abhängigkeiten committen.
REPO=/pfad/zum/v16-repo
EXTERNAL=/sicherer/pfad/auserhalb-claude-repo
python3 04_TOOLS/freeze_artifacts.py make --phase D --repo "$REPO" --scope tests/m1 --out "$EXTERNAL/freeze_d.json"
python3 04_TOOLS/freeze_artifacts.py verify --repo "$REPO" --freeze "$EXTERNAL/freeze_d.json"
# Später M1b, nach Kandidatenfreeze: --phase B --scope . --out "$EXTERNAL/freeze_b.json"
```

Der externe Receipt-Pfad darf **nicht** nur außerhalb des Repository-Verzeichnisses liegen, sondern muss dem Claude-Code-Prozess tatsächlich unzugänglich oder gegen dessen Schreibzugriff geschützt sein. Für alle echten Holdout-Artefakte entsprechend eigenes Konto/Host nutzen. SHA/Tags sind keine Zugriffssperren.

### V5.2.6 – zusätzliche Werkzeuge

- `branch_protocol.py`: **nur offline** nutzbare Fixture-Referenz für unabhängige D/H-Zweige mit gleichem Anfangssnapshot und getrennten Read-Budgets. D-Preflight wird vor jedem optionalen Read ausgeführt. `public_state()` versteckt Oracle und noch nicht erhobene Daten; `host_observations()` enthält nur für den Host zusätzlich Read-Provenienz. **Keine echte Tool-Sandbox und keine Produktivautorität.**
- `validate_fixture.py`: Schema **v1.3** und `oracle.required_proof_sets` (ODER über vollständige UND-Mengen), inklusive Prüfung, ob eine vollständige nötige Belegkombination ins Budget passt. `oracle_proof_satisfied(...)` ist **Evaluator-only** und verlangt zusätzlich die Menge der *tatsächlich sichtbaren* Beobachtungs-IDs; die Funktion darf nicht an ein lokales Modell oder den D-Recheck gekoppelt werden.
- `test_tools.py`: Offline-Regressionsfälle für Budget-Isolation, identische Snapshots, lesefreien Preflight, unlösbare Belegkombinationen und evaluatorseitige Vollständigkeitsprüfung.

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
