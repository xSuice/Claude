# V5.2.5 – Freeze, externe Verwahrung, Blind-Holdout (M1a / M1b)

## Wer macht was?

- **Claude Code:** erstellt ausschließlich den öffentlichen Harness, die D-Baseline, den H-Trigger, das Oracle und das gemeinsame Template-Schema; schreibt einen öffentlichen **Dummy-Test**. Kein Zugriff auf echte Holdout-Familien/Seeds/Key und keine Möglichkeit, Bewertungsgrenzen nach Holdout anzupassen.
- **Nutzer oder unabhängiger Evaluator:** erstellt die *echten* unbekannten Holdout-Template-Familien (neue Fehlerformen und Logstile, nicht bloß andere Zahlen), wählt private Seeds, hält Oracle-Truth sowie 256-Bit-HMAC-Key in getrenntem Account/Host, kann den finalen Blindlauf gegen fest eingefrorene Kandidaten ausführen. Umfang laut YAML: mindestens 30 Fälle je S1–S3, 60 je S4 und S5, 30 für S6 (240 gesamt), aus mindestens 6 Familien je Stratum, dazu Sicherheitsfälle. **Praktisch:** Schreibt wenige private Familien-Definitionen (Logstil, Fehlerform, Dienstgraph, Parameterkatalog) und lasst sie von einem Evaluator-Generator mit privaten Seeds zu Fällen erweitern, statt 240 Einzelfälle von Hand zu schreiben. Wenn diese Unabhängigkeit fehlt: HOLDOUT_BLOCKED statt behauptetem Blindtest.
- **Gemeinsamer Vertrag:** `HOLDOUT-TEMPLATE-SCHEMA.json` (Draft 2020-12) beschreibt Fixture-Felder; `DUMMY-HOLDOUT-ONLY.json` zeigt die Form. Der Dummy darf im Repository liegen, ist **keine** Holdout-Evidenz. Der Evaluator validiert mit `04_TOOLS/validate_fixture.py`. `oracle` und alle nicht freigegebenen Beobachtungen werden vom Modell strikt ferngehalten. Schema definiert Datenformat, nicht den vollständigen Evaluator oder die gesamte Root-Cause-Taxonomie.

## D/H/Harness in M1a einfrieren

1. Komponenten D, H-Trigger, Oracle, Generator, Scorer, YAML und verwendete Hilfsdateien unter `tests/m1/` ablegen; B *außerhalb* (z. B. `experiments/m1_b/`). In M1a in dieser Struktur ebenfalls einen Dependency-/Environment-Lockfile sowie Loader-/Importübersicht führen. Ein externer Import ohne gepinnte Version macht den Freeze unvollständig.
2. Mit Tests/Fixtures bis zur funktionierenden Baseline **D optimieren**, nicht künstlich schwächen. Testfälle S1–S10 und Dummy-Schema-Test ausführen.
3. Alles relevante committen; `git status --porcelain=v1 --untracked-files=all` muss leer sein. Danach `python3 04_TOOLS/freeze_artifacts.py make --phase D --repo "$REPO" --scope tests/m1 --out "$EXTERNAL/freeze_d.json"` (Tool möglichst außerhalb Repo oder als gepinnte Harnesskopie verwenden). Es ermittelt den echten **Git-Tree-Hash des gesamten Teilbaums**, nicht manuell ausgewählte Dateien.
4. `freeze_d.json` nur außerhalb der Schreibrechte von Claude Code verwahren, extern getrennt aufschreiben: D-SHA, Commit-SHA, Empfangsdatum. Ein von Claude selbst editierbarer Repo-Hash ist keine unabhängige Verwahrung. Optional persönlicher signierter Git-Tag durch Nutzer, dessen Signaturschlüssel dem Agenten nicht zugänglich ist.
5. SHA und Beleg vor M1b bestätigen; sonst `BLOCKED_FREEZE`. Spätere B-Änderungen dürfen `tests/m1/` nicht verändern. `verify` vergleicht D-Unterbaum gegen den Freeze.

## B einfrieren – erst in M1b nach DEV

1. Maximal **vier** dokumentierte DEV-Anpassungen je vorab festgelegtem Modellkandidaten. B-Prompt, Grammatik/JSON-Schema, Quantisierung, tatsächliche Modell-SHA, Tool-Protokoll, Sampling-/Kontextparameter, Runtime-Build und Pfad H vollständig dokumentieren; keine Selection nach Holdout.
2. Diese Inhalte außerhalb `tests/m1/` in einen sauberen Git-Commit aufnehmen. B-Snapshot `--phase B --scope .` friert den **ganzen Git-Tree** ein. Untracked/dirty Worktree wird verweigert. Technische Binärmodelle extern gesondert SHA256 fixieren; Git-Tree allein schützt keine unversionierten Gewichte oder Betriebssystemabhängigkeiten.
3. Der Nutzer verwahrt auch B-Receipt unabhängig und bestätigt beide Freeze-Belege. Der Evaluator prüft die Tree-Hashes vor genau einem Holdout-Durchlauf.
4. Abweichung nach Freeze -> Evaluierung blockieren oder komplett neue, unabhängig versiegelte Studie. Ergebnis nach Holdout nicht zum Tuning derselben Daten verwenden.

## Verpflichtung des Blind-Holdouts

Der unabhängige Evaluator erstellt ein HMAC-SHA256 Commitment über das *private* kanonische Holdout-Manifest mit unabhängig zufälligem 256-Bit-Key. Ins Repo kommt **nur** das öffentliche Commitment, nicht Key, private Seeds, Vorlagen, Wahrheitslabels oder deren reversible Hashes. Der Evaluator liefert Lauf-/Oracle-Nachweise; außerhalb der Freigabe kein Zugang zum privaten Material.

## Statistik und Auswertung

Primär **H gegen D** über die eingefrorenen Gruppen: **easy** S1–S3 (Nicht-Unterlegenheit), **improvement** S4–S5 (Mehrwert), **S6** (keine Verschlechterung; S6-Abstinenz ist gleichzeitig eigenes Qualitäts-Gate). Sekundär **B gegen D**. Fallzahlen: 30 je S1–S3, 60 je S4 und S5, 30 für S6; keine replizierten Seeds als unabhängige Beobachtungen. **Cluster-Bootstrap:** Ziehungseinheit ist die `family_id` innerhalb des Stratums (Fälle derselben Familie sind korreliert), 20.000 Replikationen, RNG `random.Random(20261016)`, gleich gewichtete Strata, zweiseitiges 95%-Perzentilintervall; ein fallbasiertes CI wird nur als Diagnose ausgegeben. Weil Cluster-CIs bei wenigen Familien optimistisch sind, gilt zusätzlich die Zellen-Konsistenz: mindestens 50 % der (Stratum,Familie)-Zellen mit H>D und höchstens 25 % mit H<D. Code vor Holdout mit einfrieren. Vorab (ohne B) wird die Selektions-Sensitivität des Fixtures geprüft. Einfache Gegenprüfung: `04_TOOLS/paired_bootstrap.py`. CI allein macht den Test weder kausal noch allgemein repräsentativ.

`GO`: alle Kriterien für **isolated_service_diagnosis** belegt. `LIMITED_GO`: ausschließlich **H bei D_ABSTAIN/D_OBSERVATION_CONFLICT** innerhalb S4–S5, mit mindestens 30 ausgelösten Fällen aus mindestens 4 Familien und positivem Cluster-95%-CI, andere Aufgaben auf D. Ein nicht selektionssensitives Fixture ergibt immer `INCONCLUSIVE`. `NO_GO`: Gegenbeweis oder klare Verfehlung. `INCONCLUSIVE`: unzureichende Evidenz, statistische Unklarheit oder Messlücken. Safety muss in allen Varianten bestehen. H wählt bei eindeutigen Fällen immer D, nicht B; lokaler Mehrwert nur anhand tatsächlich ausgelöster LLM-Schritte nachweisbar.

## V5.2.6 – zusätzlich vor dem Holdout einzufrieren

Das eingefrorene D/H-Verzweigungsprotokoll muss den Zeitpunkt **vor optionalen Reads**, die aus initialer Evidenz reproduzierbare D-Preflight-Entscheidung, die identischen Anfangssnapshot-Fingerprints sowie **getrennte Lesebudgetzähler** enthalten. Ebenfalls einzufrieren sind das **aktuelle Schema v1.3**, der Validator und die Definition vollständiger `required_proof_sets` (nur unabhängig evaluator-intern). Die Hashes allein garantieren keine Datenhoheit. Ohne passenden sauberen Git-Tree und externe Freeze-Receipt bleibt M1b/Holdout blockiert.

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

Das v1.3-Schema, die exakte Scorer-Regel und die Validator-Prüfung müssen vor dem Holdout gemeinsam als Teil des D-Tree-Freeze erfasst werden.
