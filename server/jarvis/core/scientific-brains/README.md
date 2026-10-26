# Scientific Brains – Forschungsadapter für Claude Code (V3)

**Status 14.10.2026:** Separates **Forschungslabor** zum vorhandenen Claude-Brain-V2-Paket. Kein dauerhaft laufender Dienst, kein Claude-Hook, kein neuer Router, kein automatischer API-Aufruf. Die reale Claude-Code-Installation und deine Datenbank sind nicht verbunden. Mitgelieferte Tests prüfen Softwareverhalten, **nicht** wissenschaftliche Güte, Claude-Qualität oder Verbrauchsersparnis.

## Was hier tatsächlich von Forschern stammt

| Quelle | Originalmaterial | Anwendung | Status / Grenze |
|---|---|---|---|
| [OpenWorm/CElegansNeuroML](https://github.com/openworm/CElegansNeuroML), [offizielle CSV](https://github.com/openworm/CElegansNeuroML/blob/master/herm_full_edgelist.csv) | Reale gerichtete C.-elegans-Verbindungen (`Source`, `Target`, `Weight`, `Type`); Repositorium verweist für neuronale Mehrskalen-Simulation auf [openworm/c302](https://github.com/openworm/c302) | Mit `openworm_connectome.py` reale Kanten laden und Graphsignal auswerten | Ein kurzes, nachprüfbares **15-Kanten-Originalbeispiel** liegt bei. Vollständiger CSV-Abruf ist ein gesonderter optionaler Schritt. Das Probe-Skript ist **keine** exakte Nervensystemsimulation. |
| [Nengo/nengo-spa](https://github.com/nengo/nengo-spa), [offizielle ActionSelection-Doku](https://www.nengo.ai/nengo-spa/v1.3.0/examples/intro.html) | Biologisch motivierte *Basalganglien-/Thalamus-Handlungsauswahl* als neuronale Simulation | `nengo_action_selection.py` ruft **echte** NengoSPA-Neuronennetze bei optional installierter Abhängigkeit auf | **Nicht lokal ausgeführt**, da diese Bibliotheken hier nicht installiert sind. Sehr wahrscheinlich aufwendiger als triviales Maximum; nicht als Qualitätsgewinn ausgeben. |
| [Eon Systems fly-brain](https://github.com/eonsystemspbc/fly-brain) | LIF-Modell des FlyWire-Fruchtfliegen-Connectoms | Optionales größeres Forschungsexperiment als abgetrennter Prozess | Upstream dokumentiert Linux, NVIDIA/CUDA und hohe Daten-/Rechenanforderungen; **nicht** als Standard-Hook. GPL-2.0-or-later; beachten. |
| [The Virtual Brain](https://github.com/the-virtual-brain/tvb-root) | Makroskopische Simulationsmodelle menschlicher Gehirnnetzwerke | Forschung, nicht praktischer Task-Router | Menschliches Gehirnmodell ≠ künstliches Allgemeinwissen. Nicht standardmäßig installieren. |

**Wichtige Abgrenzung:** Ein Connectom ist ein neuronaler Schaltplan, kein trainiertes Sprachmodell. Ein Schaltplan von Wurm/Fliege hat keine biologisch begründete Zuordnung zu `Claude-Skill`, `Code-Review` oder `MCP-Tool`. Darum werden die neuronalen Versuche **nicht** in den produktiven Entscheidungsweg eingeschaltet, solange sie gegenüber dem einfachen lokalen Algorithmus keine nachweisbaren Vorteile haben.

## A. Sofort offline ausprobieren (nur Python-Standardbibliothek)

Im entpackten Paket:

```powershell
python -m unittest discover -s scientific-brains/tests -v
python scientific-brains/openworm_connectome.py --csv scientific-brains/samples/openworm_verified_excerpt.csv --probe I1L --steps 3
```

Der Ausschnitt enthält **15 echte Verbindungseinträge** aus der oben verlinkten OpenWorm-CSV, nicht das gesamte Nervensystem. Der Graph-Algorithmus selbst ist ein eigenes, bewusst vereinfachtes Rechenbeispiel, **kein** wissenschaftlich validiertes biophysikalisches Modell. Die Knoten können neben Nervenzellen auch andere Zellen/Strukturen umfassen. Ein erfolgreicher Test belegt nur korrekte Umsetzung dieser begrenzten Operation.

## B. Originaldaten freiwillig herunterladen

Einmaliger Netzwerkzugriff auf die veröffentlichte CSV (keine Cloud-KI-Abfrage):

```powershell
python scientific-brains/fetch_openworm.py --output scientific-brains/openworm_full.csv
python scientific-brains/openworm_connectome.py --csv scientific-brains/openworm_full.csv --probe ADFL --steps 3
```

Das Skript lädt nur von der fest eingetragenen GitHub-Raw-URL und gibt den **SHA-256-Hash** aus. Es überschreibt keine bestehende Datei. Für reproduzierbare Studien die geprüfte Quellrevision festhalten und nachfolgende Downloads mit `--sha256 <geprüfter-hash>` prüfen. Eine `master`-URL allein garantiert keine unveränderten Daten. Vor der Weiterverteilung größerer Datenmengen Urheber- und Nutzungsrechte prüfen. Der Voll-Download war im Erstellungssystem wegen fehlendem Netzwerkzugriff **nicht ausführbar**.

## C. NengoSPA-Forschungslauf, optional in isolierter virtueller Umgebung

Nur wenn du diesen Versuch wirklich möchtest – nicht ungefragt im Claude-Projekt installieren:

```powershell
py -3 -m venv .venv-nengo
.\.venv-nengo\Scripts\python.exe -m pip install nengo nengo-spa
.\.venv-nengo\Scripts\python.exe scientific-brains/nengo_action_selection.py --memory 0.8 --tool 0.3 --claude 0.2
```

Linux/macOS: statt `py -3` `python3`, statt `Scripts\python.exe` `bin/python`. Vor dem Installieren aktuelle Kompatibilität, Lizenzen und Paketversionen der offiziellen Veröffentlichungen prüfen und in einem Lockfile festhalten. Das Skript baut einen echten NengoSPA-`ActionSelection`-Versuch mit den drei als Zahlen zugeführten Prioritäten `memory/tool/claude` auf und vergleicht das Ergebnis mit einem **einfachen `max()`**. Es entscheidet **keine** produktive Aufgabe und hat keinen Zugriff auf Berechtigungen, Datenbank oder Router. Neuronale Simulation kann erheblich langsamer sein und keine weiteren Claude-Tokens sparen als `max()`.

## D. Integration nur bei messbarem Vorteil

1. Auf dem echten Gerät zuerst Hardware, Claude Code, bestehenden Router/Hooks und Speicherquellen nachweisen; V5-Baseline festhalten.
2. NengoSPA/Connectome **isoliert** gegen lokale Baseline vergleichen: Genauigkeit bei definierten Aufgaben, falsche Entscheidungen, Laufzeit, CPU/RAM und Zahl der zusätzlichen Modellaufrufe. Datenschutz und Multiuser-Berechtigungen unverändert durch Backend erzwingen.
3. Connectome-Simulation **nicht** als vollständiges Gedächtnis, RAG-System oder Prompt-Interpreter ausgeben. Die Verbindung zu einer echten Aufgabe benötigt eine fachlich begründete Eingabe-/Ausgabecodierung. Ohne solche ist sie nur ein Forschungsobjekt.
4. Wenn eine neuronale Variante schlechter oder gleich gut bei höherem Aufwand ist, nicht in Produktion schalten. Stattdessen vorhandene DB-Volltextsuche/ACL, Code-Hooks und Tests optimieren. Wenn nachweislich besser, eine eng begrenzte **opt-in**-Schnittstelle per CLI prüfen; keine permanente Claude-Modellnutzung.
5. Einen kontrollierten Verbesserungszyklus nutzen. Originaldaten, Version, Lizenz, Benchmark und genaue Rücknahme dokumentieren. Zwei Nutzer strikt getrennt verarbeiten.

## Was getestet wurde

- Lokale Datenvalidierung, 15 echte Beispieleinträge, Knoten-/Kantenzählung, begrenzte Graphdiffusion und Fehlereingaben.
- NengoSPA nur Eingabevalidierung. Eine vollständige Nengo-Simulation und die echte C.-elegans-Gesamtdatei **wurden hier nicht geprüft**.
- Kein auf einem fremden Gerät installierter Dienst; **kein belegter Gewinn bei Claude-Qualität oder Tokenverbrauch**.
