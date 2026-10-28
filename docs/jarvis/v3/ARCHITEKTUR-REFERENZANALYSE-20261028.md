# MA‑HOME JARVIS – Architektur‑ und Referenzanalyse zum Stand vom 28. Oktober 2026

## Quellenlage und Gesamturteil

**Prüfgrenze dieser Analyse:** Für die projektspezifische IST-Seite verwende ich dein oben geliefertes konsolidiertes Gesamtbild aus SPEC‑MASTER‑V3, Council‑Hermes‑Skills, Autonomous Task Management & Self‑Healing, Kimi‑Vollpaket, IST‑SOLL‑MATRIX, V3‑RESTAUFTRAG, V3‑SCHLUSSABNAHME, APPROVAL_MATRIX, STATE.md und deiner Serverinventur vom Morgen des 28.10.2026. Die zugrunde liegenden Dateien und der Server selbst waren mir in dieser Sitzung nicht als direkt lesbare Ressourcen zugänglich. Zahlen wie **55 erledigt / 13 fehlgeschlagen**, **18/18 Spezialistentests**, die Portbelegung oder die Mobiltests behandle ich deshalb als deinen belegten Projektstand, nicht als von mir erneut ausgeführte Abnahme.

Die öffentliche Recherche ergibt trotzdem ein recht klares Bild:

> **MA‑HOME JARVIS braucht keinen Plattform-Neubau.** Deine Grundarchitektur ist bereits näher an einem brauchbaren persönlichen Agentenbetriebssystem als an einem Prototyp. Der größte Hebel liegt jetzt in der **Härtung und Vereinheitlichung der Kontrollschicht**: revisionsfähige Aufträge, formal definierte Councils, ein echter Policy-/Model-Router, ein Capability- und Approval-Broker, systematische Evidenz und gezielte Wissensextraktion.

Ich würde deshalb **Flask-Portal, V16, PostgreSQL-Chatbus, Watchdog, Windows-Worker und deine JARVIS-Identität nicht durch LangGraph, CrewAI, OpenHands oder Hermes ersetzen**. Diese Projekte sind wertvoll als Vorlagen für einzelne Mechanismen. LangGraph etwa ist explizit auf langlebige, zustandsbehaftete Abläufe mit Durable Execution und Human-in-the-loop ausgerichtet; CrewAI trennt rollenbasierte Crews von ereignisgesteuerten Flows. Das sind genau die Muster, die V16 und dein Council-Modell vervollständigen können, ohne dass du dein bestehendes System wegwirfst. citeturn13search0turn14view0

Ebenso wichtig: **Microsoft AutoGen würde ich 2026 nicht mehr als Basis einer neuen JARVIS-Schicht wählen.** Das bekannte AutoGen-Repository ist inzwischen archiviert bzw. nicht mehr die strategische Microsoft-Linie; die Konzepte sind weiterhin interessant, nicht aber ein Neuaufbau darauf. citeturn14view1

Die Zielarchitektur sollte deshalb so aussehen:

```text
Du
 │
 ▼
JARVIS HQ ───────────────────────────────────────────────┐
 │                                                      │
 ├─ Chat / Voice / Signal                               │
 ├─ Living HQ / Command Center                          │
 │                                                      │
 ▼                                                      │
JARVIS Control Plane                                    │
 ├─ Task Engine V16 + immutable Revisions               │
 ├─ Council Manager                                     │
 ├─ Policy / Approval Engine                            │
 ├─ Smart Router                                        │
 ├─ Capability Broker                                   │
 ├─ Evidence + Audit                                    │
 └─ Memory Distiller                                    │
 │                                                      │
 ├─────────────► Council (nur beratend)                  │
 │                    │                                 │
 │              Decision Artifact                       │
 │                    ▼                                 │
 └─────────────► Hermes / Executor Layer                 │
                       │                                 │
        ┌──────────────┼──────────────┐                  │
        ▼              ▼              ▼                  │
   Server-Sandbox  Windows Worker  Browser/Desktop       │
        │              │              │                  │
        └────── Evidence / Artifacts ─┘                  │
                       │                                 │
                 Independent Verifier                   │
                       │                                 │
                 belegter Abschluss                     │
                       │                                 │
                  Memory Distiller                      │
                       │                                 │
                  Obsidian/Vault ◄───────────────────────┘
```

Das Entscheidende an diesem Modell: **„volle Privilegien“ bedeutet, dass JARVIS prinzipiell jede registrierte Fähigkeit anfordern kann – nicht, dass ein LLM permanent als root oder Windows-Administrator läuft.** Genau diese Trennung findet man bei den ausgereifteren Agent-Harnesses wieder. Hermes Agent beschreibt beispielsweise acht Sicherheitsschichten einschließlich Benutzerautorisierung, gefährlichen Befehlsfreigaben, Schreibschutz, Container-Isolation, MCP-Credential-Filtering und Session-Isolation; unbeaufsichtigte Sessions können riskante Befehle standardmäßig verweigern. citeturn19view0


## Referenzlandschaft

Die Star-Zahlen sind Momentaufnahmen vom Recherchezeitpunkt **28.10.2026** und deshalb als Größenordnung zu verstehen. Beim Ressourcenbedarf verwende ich bewusst **niedrig / mittel / hoch** statt erfundener RAM-Werte; der tatsächliche Bedarf hängt von Last, Datenbank und Parallelität ab.

**Router und Gateways**

| Projekt | Aktivität / Popularität | Lizenz | Ressourcen | Einschätzung für JARVIS |
|---|---:|---|---|---|
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | ≈5,6k Stars; etabliertes Forschungsprojekt | Apache‑2.0 | niedrig beim Routing, hoch beim Training | Sehr gute Vorlage für Quality-vs-Cost-Routing, aber **kein kompletter Gateway-Ersatz**. Die Autoren demonstrieren Routing zwischen starken/schwachen Modellen und berichten in ihren Benchmarks erhebliche Kosteneinsparungen. citeturn6search0 |
| [LiteLLM](https://github.com/BerriAI/litellm) | sehr aktiv; Größenordnung >60k Stars im aktuellen Abruf | Lizenzmodell im aktuellen Repo differenziert; vor Produktion konkret prüfen | niedrig–mittel | **Stärkster Kandidat als Provider-Gateway unter deinem eigenen `evidence_router`**: vereinheitlichte Provider-APIs, Kosten, Load Balancing, Fallbacks und Logging. Nicht den Router ersetzen lassen, sondern ihn als ausführende Provider-Schicht verwenden. citeturn7view0turn28search4 |
| [Portkey AI Gateway](https://github.com/Portkey-AI/gateway) | ≈13k Stars | MIT | niedrig–mittel | Sehr gute Referenz für Guardrails, Fallbacks und Gateway-Policies. Für dein kleines System bringt LiteLLM wahrscheinlich weniger Zusatzkomplexität. citeturn7view1 |
| [Semantic Router](https://github.com/aurelio-labs/semantic-router) | ≈4k Stars | MIT | **niedrig** | Für JARVIS besonders interessant: semantische Vorauswahl ohne großen LLM-Aufruf. Gute **Stufe 0/1** vor Kimi. citeturn7view2 |
| [claude-code-router](https://github.com/musistudio/claude-code-router) | **37,9k Stars**, 989 Commits | MIT | niedrig–mittel | Hervorragender Claude-Code-spezifischer Adapter für verschiedene Modelle. Nicht parallel zu einem zweiten Smart Router entscheiden lassen; als **Claude-Code-Adapter unter JARVIS** sinnvoll. citeturn19view3 |
| Martian Router / RouterBench | öffentliches Router-Repo sehr klein, ≈1 Star/1 Commit im untersuchten Repo | MIT | extern bzw. niedrig | Interessant für Routingforschung/Benchmarks, **nicht als JARVIS-Laufzeitbasis**. citeturn10search0 |
| NotDiamond | kommerzieller Routing-Dienst; keine sinnvolle OSS-Starzahl | proprietär/SaaS | extern | Lernender Modellselektor mit Quality/Cost/Latency-Optimierung. Für dich unnötige zusätzliche Abhängigkeit, weil dein `evidence_router` genau diese strategische Aufgabe selbst besitzen soll. citeturn10search1 |

RouteLLM ist vor allem als **Methodik** interessant. Dein Router muss viel mehr als „schwaches oder starkes Modell?“ entscheiden: Provider, Modell, Reasoning-Budget, Toolfähigkeit, Datenschutzklasse, Hardware, Health, Quoten, Cache-Eignung und Risiko. LiteLLM bzw. claude-code-router sollten deshalb **Transport/Gateway**, nicht Gehirn des Routers sein. citeturn6search0turn19view3

**Agenten, Councils und persistente Arbeit**

| Projekt | Aktivität / Popularität | Lizenz | Ressourcen | Für JARVIS |
|---|---:|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | ≈44k Stars | MIT | mittel | **Muster übernehmen:** Checkpoints, Durable Execution, Unterbrechung/Wiederaufnahme, Subgraphs. V16 nicht ersetzen. citeturn13search0 |
| [CrewAI](https://github.com/crewAIInc/crewAI) | ≈60k Stars | MIT | mittel | Gute Vorlage für Rollen/Crews und klar definierte Tasks. Für deine acht Councils **ergänzen/inspirieren**, nicht übernehmen. citeturn14view0 |
| AutoGen | ≈61k historische Stars, inzwischen archivierte alte Linie | MIT/CC-Komponenten | mittel | **Für neuen Produktivkern ignorieren**; Dialogmuster allenfalls übernehmen. citeturn14view1 |
| [OpenHands](https://github.com/OpenHands/OpenHands) | **92k Stars** | MIT | **hoch** | Sehr wertvolle Executor-/Sandbox-/Always-on-Referenz; vollständiger Einsatz auf dem N2840 dagegen ungeeignet. Agent Canvas unterstützt lokale, Docker-, VM- und Remote-Backends sowie persistente Automationen. citeturn26search0 |
| Agent Squad | Größenordnung ≈6–7k Stars | Apache‑2.0 | mittel | Supervisor, Spezialisten und Routing passen gut zum Council-Konzept; Muster übernehmen. citeturn15search1turn20search0 |
| MetaGPT | aktives, großes Multi-Agent-Projekt; exakte 28.10.-Starzahl im Rechercheabruf nicht belastbar bestimmt | Open-Source-Projekt; Lizenz vor Übernahme konkret prüfen | mittel–hoch | Organisation nach Software-Rollen interessant; für deine beratenden Councils jedoch zu stark auf eigene Prozesswelt zugeschnitten. citeturn15search2 |
| Claude Code Subagents / Skills / Hooks | offizielles, aktiv gepflegtes Produkt | kein eigenständiges OSS-Framework | niedrig | **Sehr hohe Relevanz**, weil dein Bridge bereits Claude Code nutzt: Subagents isolieren Kontext, Skills laden Wissen bedarfsgesteuert, Hooks erzwingen deterministische Lifecycle-Regeln. citeturn16search1 |
| [Hermes Agent, NousResearch](https://github.com/NousResearch/hermes-agent) | im aktuellen Abruf extrem großes und aktives Projekt, ≈258k Stars | MIT | mittel, je Backend variabel | Hervorragende Referenz für Skills, Memory, Cron, Subagents, Terminal-Backends und Security. **Nicht automatisch mit deinem lokalen „Hermes Desktop“ gleichzusetzen**; ich kann nicht belegen, dass es dieselbe Distribution/Fork ist. citeturn18search0turn19view0 |

Gerade Claude Code zeigt eine für dich wichtige Architekturregel: Skills, Tool-Schemas und Spezialkontexte müssen nicht permanent im Hauptkontext stehen. Subagents können isolierte Kontexte führen und nur ihre Ergebnisse zurückgeben; Hooks können deterministische Aktionen übernehmen, ohne dafür jedes Mal LLM-Kontext zu verbrauchen. citeturn16search1

**Observability, Watchdog und Gedächtnis**

| Projekt | Aktivität / Popularität | Lizenz | Ressourcen | Urteil |
|---|---:|---|---|---|
| [Langfuse](https://github.com/langfuse/langfuse) | **36,6k Stars**, >10k Commits | MIT außer Enterprise-Bereichen | **hoch self-hosted** | Inhaltlich ausgezeichnet für Traces, Evals, Scores und Datensätze. Die aktuelle Self-hosted-Architektur nutzt u. a. ClickHouse; **nicht auf deinen 3,2-GB-Master quetschen**. Cloud oder separates System. citeturn20search0 |
| [Helicone](https://github.com/Helicone/helicone) | **6,2k Stars**, >5k Commits | Apache‑2.0 | mittel–hoch self-hosted | Gute Kosten-/Latenz-/Routing-Telemetrie; hat auch eine große öffentliche Model-Cost-Datenbasis. Für JARVIS eher Datenquelle/Referenz als zusätzliche Plattform. citeturn23view2turn23view3 |
| [OpenTelemetry Collector](https://github.com/open-telemetry/opentelemetry-collector) | sehr etablierte Observability-Infrastruktur | Apache‑2.0 | niedrig–mittel | **Empfehlenswertes neutrales Telemetrieformat** für Tasks, Tools, Router und Voice. Kein LLM-spezifischer Lock-in. citeturn20search2 |
| [Mem0](https://github.com/mem0ai/mem0) | **67,9k Stars**, 2.675 Commits | Apache‑2.0 | mittel | Sehr gute Vorlage für selektives Agenten-Memory. Die aktuellen Autorenbenchmarks werben mit stark reduziertem Kontextbedarf; diese Zahlen sind **Herstellerbenchmarks**, nicht unabhängige Garantie. citeturn23view0turn23view1 |
| [Letta](https://github.com/letta-ai) | aktuelles `letta-code` ≈3,7k Stars, zuletzt 26.10.2026 aktualisiert | Apache‑2.0 | mittel | Interessant für langfristig zustandsbehaftete Agenten. Für JARVIS wäre ein kompletter Letta-Layer aber redundant zu V16/Vault. citeturn21search2 |
| [Graphiti](https://github.com/getzep/graphiti) | ≈32k Stars; aktualisiert 23.10.2026 | Apache‑2.0 | **hoch** | Sehr attraktiv für **spätere** zeitabhängige Wissensgraphen mit Provenienz. Benötigt jedoch Graph-Backend und LLM/Embeddings; nicht als erste Lösung auf dem Master. citeturn21search0turn21search6turn21search8 |
| Zep | managed Context-Graph-Plattform | kommerziell / SDKs OSS | extern | Für größere Produktivsysteme bequem, aber für dein privates Vault unnötiger Cloud-Layer. Graphiti-Muster reichen zunächst. citeturn21search0turn21search6 |

Für dein Ziel „**geprüftes Wissen behalten, nicht Chats kopieren**“ ist die beste Lösung deshalb zunächst **nicht ein neues Memory-Produkt**, sondern eine Mem0-/Graphiti-inspirierte Extraktionsstufe über deinem vorhandenen Vault. Graphiti ist besonders interessant, weil es Fakten mit zeitlicher Gültigkeit und Provenienz modelliert; sein Referenz-MCP-Server warnt jedoch selbst ausdrücklich, dass die Beispielserver keine Authentifizierung/Autorisierung oder Prompt-Injection-Abwehr besitzen. citeturn21search0

**Sprache und Living HQ**

| Projekt | Aktivität / Popularität | Lizenz | Ressourcen | Für dein Ziel |
|---|---:|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | ≈25,6k Stars; zuletzt 25.10.2026 aktualisiert | MIT | GPU/CPU mittel | **Übernehmen/testen.** CTranslate2, INT8 und geringer Speicherverbrauch passen sehr gut zur RTX 2060. Die Entwickler berichten bis zu 4× Geschwindigkeit gegenüber Referenz-Whisper in bestimmten Benchmarks. citeturn22search4turn22search6turn22search8 |
| Piper, alter `rhasspy/piper` | archiviert seit 06.10.2025 | MIT | niedrig | Nicht weiter darauf standardisieren. Entwicklung wurde verschoben. citeturn22search0turn22search1 |
| [OHF Piper](https://github.com/OHF-Voice/piper1-gpl) | ≈6k Stars, aktualisiert 25.10.2026 | **GPL‑3.0** | niedrig | Aktuelle Piper-Linie; separate Prozessintegration testen. Deine Thorsten-Stimme kann bleiben, sofern Modell/Lizenz passen. citeturn25search2turn25search3turn25search10 |
| [Silero VAD](https://github.com/snakers4/silero-vad) | ≈10,2k Stars | MIT | sehr niedrig mit ONNX | Sehr passend für Streaming-Endpunkt-Erkennung. Das Modell ist klein und bietet ONNX-/Browser-Varianten. citeturn25search1turn25search4 |
| [openWakeWord](https://github.com/dscripka/openWakeWord) | aktives Wakeword-Projekt; Star-/Lizenzwert im abgerufenen Ausschnitt nicht zuverlässig erfasst | vor Integration erneut prüfen | niedrig | Gute lokale Wakeword-Referenz; dein browserseitiger Wakeword-Pfad muss dafür nicht zwingend ersetzt werden. citeturn24search3 |
| [Pipecat](https://github.com/pipecat-ai/pipecat) | **16,9k Stars**, >14k Commits | BSD‑2-Clause | mittel, modular | **Beste Referenz für deine <4-s-Optimierung**: Streaming-STT → LLM → TTS, Barge-in, VAD, Ollama/Piper/Silero und verteilte Agents bereits als Bausteine. citeturn24search0 |
| [LiveKit Agents](https://github.com/livekit/agents) | **15k Stars**, >4k Commits | Apache‑2.0; eigene Lizenz für Turn-Modelle | mittel–hoch | Sehr ausgereift für WebRTC, Voice Jobs, Turn Detection, Tests und MCP. Für dein Heimnetz wahrscheinlich mehr Plattform als nötig; Pipecat ist zunächst leichter. citeturn24search1 |
| Home Assistant Assist / Wyoming | aktiv weiterentwickeltes HA-Ökosystem | je Komponente OSS | niedrig–mittel | Gute Protokoll-/Pipeline-Referenz. Die HA-Architektur arbeitet explizit an cancellable, gestreamten Voice-Pipelines mit Whisper/Piper und Wyoming. citeturn25search8 |
| [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents) | **9,9k Stars**, 225 Commits | MIT | Browser niedrig, Node mittel | **Sehr hoher Nutzwert als Living-HQ-Muster.** Hooks werden auf normalisierte AgentEvents abgebildet; Canvas 2D, Pathfinding und Charakterzustände visualisieren echte Agentenarbeit. Designassets aber nicht kopieren. citeturn27search3 |

Pixel Agents trifft dein Living-HQ-Ziel bemerkenswert genau: echte Agents werden als Figuren visualisiert, Aktionen wie Lesen, Schreiben oder Warten verändern ihren Zustand; Subagents erscheinen separat, und die Browser-Version funktioniert sogar mobil. Wichtig ist, **deren Ereignismodell zu übernehmen, nicht deren Pixel-Art-Stil**. Dein eigenes Crimson-Zone/Eternal-Bonds/Andrew-SMP-Konzept sollte auf denselben technischen Prinzipien aufgebaut werden. citeturn27search3

**Phase C und PC-Harnesses**

| Projekt | Aktivität / Popularität | Lizenz | Ressourcen | Einsatz |
|---|---:|---|---|---|
| [Home Assistant Core](https://github.com/home-assistant/core) | **91,8k Stars**, >122k Commits | Apache‑2.0 | bereits vorhanden | Smart Home vollständig über HA-Aktionen kapseln; JARVIS sollte Geräte nicht parallel direkt implementieren. citeturn27search1 |
| [Open Interpreter](https://github.com/openinterpreter/openinterpreter) | **68,7k Stars**, >10k Commits | Apache‑2.0 | mittel | Sehr relevante Referenz für Shell, Skills, MCP, Sandbox, Computer Use und Kimi. Die aktuelle Rust-Linie beschreibt sich ausdrücklich als Harness für günstige/open Modelle einschließlich Kimi K3. citeturn26search1 |
| [Browser Use](https://github.com/browser-use/browser-use) | **119,3k Stars**, >10k Commits | MIT | **hoch auf Worker** wegen Browser | Kandidat für Phase-C-Browserautomation; auf Windows-Worker oder separatem Browser-Executor, nicht auf N2840. citeturn29view1 |
| [MCP Servers](https://github.com/modelcontextprotocol/servers) | **91,6k Stars**, 4.826 Commits | jeweilige Komponenten/Repo-Lizenz vor Einbindung prüfen | sehr variabel | MCP als **Capability-Schnittstelle** übernehmen, aber Server nur einzeln nach Audit freigeben. citeturn29view0 |
| [Goose](https://github.com/aaif-goose/goose) | **55,8k Stars**, 5.897 Commits | Apache‑2.0 | mittel | Gute offene Referenz für extensiblen Agent + MCP + Ausführung; kein Grund, JARVIS darauf umzubauen. citeturn29view2 |
| [Aider](https://github.com/Aider-AI/aider) | **49,8k Stars**, >13k Commits | Apache‑2.0 | niedrig–mittel | Sehr gute Coding-/Git-Referenz, aber bewusst enger als dein universeller Executor. citeturn29view3 |

Das Gesamtmuster dieser Projekte ist ziemlich konsistent: **Agenten-Harnesses werden leistungsfähig, indem sie Fähigkeiten modularisieren und Ausführung isolieren – nicht indem sie dem Modell einen unkontrollierten Root-Shell-Prompt geben.** OpenHands warnt beispielsweise ausdrücklich davor, dass der Betrieb ohne Sandbox dem Agenten vollen Dateisystemzugriff gibt, und bietet stattdessen per-Konversation-Docker-Sandboxes mit persistierenden Workspaces an. citeturn26search0


## Architekturvergleich und Zielbild

Die wichtigste Vergleichstabelle für dein tatsächliches System ist aus meiner Sicht diese:

| Bereich | Dein IST | Beste Referenz | Empfehlung | Zielzustand |
|---|---|---|---|---|
| Zentraler JARVIS | Portal + Bridge vorhanden | – | **beibehalten** | Portal bleibt einziges Frontend |
| Persistente Tasks | V16/brain.db funktioniert | LangGraph | **ergänzen** | Revisionen, Leases, Checkpoints, Idempotenz |
| Councils | Chatbus + 18 Einzelprofile | CrewAI, Agent Squad, Claude Subagents | **ergänzen** | 8 echte Council-Gruppen, beratend, messbare Decision Artifacts |
| Multi-Agent-Ausführung | Hermes/Worker vorhanden | OpenHands, Hermes Agent | **ergänzen** | ein Capability Broker vor allen Executor-Backends |
| Ergebnisprüfung | V16 bereits mit Abnahme | LangGraph + eigene Tests | **vertiefen** | deterministische Tests zuerst, unabhängiger Verifier danach |
| Router | `evidence_router` shadow | Semantic Router + LiteLLM + RouteLLM | **ergänzen** | JARVIS entscheidet; Gateway führt aus |
| Provider-Gateway | Claude Bridge / einzelne Provider | LiteLLM, CCR | **ergänzen** | eine API-Schicht, keine Router-Konkurrenz |
| Watchdog | Kuma + Deepcheck + Incidents | OTel, Hermes Security | **ergänzen** | Recovery-Leiter + Circuit Breaker + Anti-Loop |
| Observability | Command Center partiell | OTel + Langfuse | **ergänzen** | OTel-Schema lokal; schwere Analyse extern |
| Memory | Vault + Sync | Mem0, Graphiti | **ergänzen** | geprüfte Fakten/Entscheidungen mit Provenienz |
| Voice | eigener Browser/Worker-Stack | Pipecat + faster-whisper + Silero | **gezielt übernehmen** | vollständiges Streaming statt sequenzieller Requests |
| TTS | Piper/Thorsten | aktueller OHF Piper | **bestehende Stimme behalten, Runtime prüfen** | warm gestartete Streaming-TTS |
| Living HQ | Canvas + Live-Daten | Pixel Agents | **Eventmodell übernehmen** | echte Task-/AgentEvents treiben Originalfiguren |
| Browser | fehlt | Browser Use | **Phase C ergänzen** | isolierter Browser-Worker |
| Computer Use | fehlt | Open Interpreter | **Phase C ergänzen** | eigener Desktop-Executor |
| Smart Home | HA existiert | Home Assistant | **HA als einzige Geräteebene** | JARVIS → genehmigte HA-Services |
| Vollprivilegien | Server teilweise; Worker `java.build` | Hermes/Claude/OpenHands | **Capability Broker bauen** | gleiche Capability-API, unterschiedliche Sandboxes |

Ein Punkt verdient besondere Aufmerksamkeit: **V16/brain.db und PostgreSQL dürfen nicht zu zwei konkurrierenden Wahrheiten über einen Auftrag werden.** Bis zu einer eventuellen späteren Migration sollte V16 die autoritative Task-State-Machine bleiben und PostgreSQL Council, Nachrichten, Evidenz und Projektionen halten. Übergänge sollten über ein **Transactional-Outbox-/Event-Muster** gespiegelt werden. Eine Dual-Write-Logik „SQLite ändern und danach hoffentlich PostgreSQL ändern“ erzeugt genau die inkonsistenten Zustände, die ein autonomes System später schwer reparieren kann.

Für die erste offene Lücke würde ich V16 folgendermaßen erweitern:

```text
task
  task_id
  current_revision
  lifecycle_state

task_revision
  task_id
  revision
  parent_revision
  user_intent
  normalized_spec
  risk_class
  budget
  created_at
  created_by

task_lease
  task_id
  revision
  worker
  lease_until

task_event
  event_id
  task_id
  revision
  event_type
  evidence_ref
  created_at
```

**Eine Auftragsänderung überschreibt niemals den alten Auftrag.** Beispiel:

```text
T-0042 rev 3   "Baue X mit Java 21"
        │
        └── Sprache: "JARVIS, ändere Auftrag T-0042:
                      nimm Java 25 und führe danach die Tests erneut aus."
                         │
                         ▼
T-0042 rev 4   parent=3
```

Ein Executor besitzt immer eine Lease für **`(task_id, revision)`**. Vor jedem externen Seiteneffekt prüft er, ob seine Revision noch aktuell ist. Wird rev 4 erzeugt, darf rev 3 keinen neuen irreversiblen Schritt mehr starten. Bereits valide, revisionsunabhängige Artefakte können weiterverwendet werden; betroffene Schritte werden invalidiert. Damit lösen sich gleichzeitig mehrere deiner Anforderungen: Sprachänderung, Neustartsicherheit, Auditierbarkeit, Anti-Race-Conditions und das Prinzip **„Sprachabbruch ≠ Auftragsabbruch“**.

Für die Councils würde ich **keine frei chattende 40-Agenten-Simulation** bauen. Das kostet Tokens und produziert viel soziale Textmenge ohne proportional bessere Entscheidungen. Stattdessen:

| Council | typische Rollen |
|---|---|
| DEV | Architect, Backend, Frontend, QA/Test, DevOps |
| CLOUD | Infra, Network, Containers, Reliability, Cost |
| AI | Model/Router, Agent Architecture, RAG/Memory, Evaluation, Local AI |
| SECURITY | Threat Modeling, IAM/Secrets, Application Security, Privacy, Reviewer |
| OPERATIONS | SRE, Monitoring, Incident, Backup/Restore, Capacity |
| STRATEGY | Systems Architect, Product, Cost/Value, Risk, Long-term |
| DATA | Database, ETL, Search/RAG, Data Quality, Governance |
| CREATIVE | Art Direction, UX, Narrative, Media, Technical Art |

JARVIS stellt jedem ausgewählten Spezialisten ein **kurzes identisches Task-Briefing** bereit. Jeder liefert strukturierte Einwände/Empfehlungen. Danach entsteht **ein** maschinenlesbares Decision Artifact:

```json
{
  "task_id": "T-0042",
  "revision": 4,
  "council": "DEV",
  "recommendation": "...",
  "constraints": ["..."],
  "dissent": ["..."],
  "evidence": ["E-123", "E-124"],
  "confidence": 0.88,
  "approved_for_execution": true
}
```

Die Spezialisten erhalten **keine operative Shell-/Desktop-Berechtigung**. Das trennt Denken von Handeln exakt so, wie deine Spezifikation es verlangt. Claude Codes isolierte Subagent-Kontexte und CrewAIs Rollenmodell sind gute technische Vorbilder dafür. citeturn16search1turn14view0

Gemessen werden sollten mindestens Council-Dauer, Rollenanzahl, Input-/Output-Tokens, Dissens, Entscheidungskonfidenz, spätere Verifier-Fehlerquote und ob JARVIS die Empfehlung übernommen hat. So lässt sich später empirisch feststellen, **wann ein Council tatsächlich Wert erzeugt** und wann eine einfache Aufgabe direkt zu Hermes gehen sollte.


## Router, Kimi und Nexum

### Kimi ist weiterhin sinnvoll – aber das aktuelle Modell muss korrigiert werden

Nach der aktuellen offiziellen Moonshot-Dokumentation ist **Kimi K3.1 Pro** am 28.10.2026 die stärkste aktuelle API-Flagship-Linie, daneben gibt es **K3.1 Pro Highspeed** und K3. Die K3-Familie bietet einen Kontext von bis zu rund einer Million Tokens. citeturn12search3turn12search2

Das ist wichtig, weil eine Architektur, die „Kimi = K2/K2.5/K2.6“ fest verdrahtet, bereits veraltet wäre. Moonshots aktuelle Pricing-Dokumentation kündigt für die K2-Familie zudem Einschränkungen für Neunutzer ab **31. Oktober 2026** und eine geplante vollständige Einstellung zum Jahresende 2026 an. Alte K2-Aliase sollten deshalb jetzt aus deinem Router entkoppelt werden. citeturn12search2

Meine Alias-Schicht wäre:

```text
kimi-main
    -> Moonshot K3.1 Pro

kimi-interactive
    -> K3.1 Pro Highspeed

kimi-open-fallback
    -> K3

local-fast
    -> Qwen3 8B / Ollama

bulk-cheap-untrusted
    -> Nexum eligible model

fallback-diverse
    -> OpenRouter eligible provider/model
```

Damit muss künftig kein Workflow wissen, wie Moonshot ein Modell benennt.

Für deinen Smart Router würde ich **Kimi-main nicht bei jedem Prompt aufrufen**. Der Ablauf sollte sein:

```text
Task
 │
 ├─ Risk / Privacy / Tool policy        deterministisch
 │
 ├─ Capability requirements             deterministisch
 │
 ├─ Simple semantic classification      lokal / Semantic Router
 │
 ▼
Candidate Set
 │
 ├─ Qualität
 ├─ Latenz
 ├─ Preis
 ├─ Cache-Wahrscheinlichkeit
 ├─ Context length
 ├─ Provider health
 ├─ Quota / Budget
 ├─ Datenschutzklasse
 ├─ benötigte Tools
 └─ Hardware availability
 │
 ▼
weighted policy score
 │
 ▼
Provider + Model + Reasoning + Hardware + Tools
```

**Kein LLM sollte entscheiden dürfen, ob es selbst ein teureres LLM braucht.** Risk-Gates, Budgets, Capability-Constraints und Provider-Ausfälle gehören in normalen deterministischen Code. Semantic Router eignet sich gerade deshalb als frühe, leichte Entscheidungsschicht. citeturn7view2

RouteLLM kann später die Quality-vs-Cost-Komponente verbessern, sobald du genügend eigene Daten gesammelt hast. Die öffentlich dokumentierten Einsparungen des Projekts sind Benchmark-Ergebnisse des Projekts selbst und nicht als Garantie für deinen Workload zu verstehen. citeturn6search0

### Nexum Router: existent, aber nicht als Vertrauensanker geeignet

Das von dir genannte **Nexum Router** existiert tatsächlich und wird von einer Seite namens **Dialagram** angeboten. Die aktuelle Angebotsseite nennt ungefähr **5,50 US-Dollar pro Woche** beziehungsweise rund 22 Dollar pro vier Wochen und listet etwa 20 Modelle aus Familien wie Qwen, DeepSeek, Xiaomi und Meta. Es werden sowohl eine OpenAI-kompatible Router-Schnittstelle als auch eine Anthropic-/Claude-Code-kompatible Schnittstelle dokumentiert. Wichtig: Nexum stellt laut eigener Beschreibung **keinen Claude- oder GPT-Modellzugang** bereit; „Claude Code“ bezeichnet hier den kompatiblen Client-/Protokollweg. citeturn0search0turn1search9

Die Aussage „nahezu unbegrenzt“ muss ebenfalls präzisiert werden. Der Anbieter wirbt für mehrere Modellfamilien mit fehlenden starren Stunden-/Wochenlimits, nennt aber **Account-Pacing**, und für bestimmte DeepSeek-Nutzung ist ein tägliches Budget angegeben. Es handelt sich damit **nicht um technisch grenzenlose Nutzung**. citeturn4search0

Positiv ist, dass es eine relativ aktuelle Privacy Policy vom **20. Oktober 2026** gibt. Negativ ist deren Inhalt aus JARVIS-Sicht: Bei der Nutzung werden unter anderem Account-/Billing-Metadaten, Routingdaten, Modell/Provider, Fehler, Latenz, Token-/Volumendaten sowie IP-/Clientinformationen verarbeitet; Prompts und Outputs müssen zur Diensterbringung verarbeitet werden. Die Policy weist außerdem auf Drittanbieter für Hosting, Bezahlung, E-Mail und AI-Modelle hin. citeturn3view0

Ich konnte bei meiner gezielten Suche **keine ähnlich klar sichtbare öffentliche ToS/AUP-Seite mit detaillierten Suspendierungsregeln, garantierten Nutzungslimits oder einem belastbaren Unternehmens-/Impressumsprofil finden**. Das ist ausdrücklich **kein Beweis, dass solche Dokumente nirgendwo existieren**, wohl aber ein Beschaffungs- und Betriebsrisiko. Die About-Seite beschreibt Dialagram und Kontaktmöglichkeiten, liefert aber wesentlich weniger Unternehmens-/Compliance-Transparenz als etablierte Enterprise-Anbieter. citeturn2view1

Auch die öffentliche Statusseite ist derzeit nur eingeschränkt aussagekräftig: Sie zeigt zwar „Operational“, gleichzeitig fehlen in dem von mir abgerufenen Stand belastbare „last checked“-/24h-Metriken. citeturn3view1

Unabhängige Reputation ist dünn. In meinen Reddit/HN- und Websuchen fand ich keinen belastbaren größeren Erfahrungsbestand. Ein kleiner externer Aggregator hatte in einem früheren Snapshot schwache bzw. fehlende Verfügbarkeitsdaten; dessen Aussagekraft ist jedoch zu gering, um Nexum damit als unseriös zu bezeichnen. citeturn1search10

Meine Einstufung:

| Kriterium | Nexum |
|---|---|
| Existenz | **bestätigt** |
| dokumentierte API-Kompatibilität | **gut** |
| Preisattraktivität | **sehr hoch** |
| wirtschaftliche Transparenz | **niedrig–mittel** |
| unabhängiger Track Record | **niedrig / wenig Daten** |
| Datenschutztransparenz | **mittel** |
| Prompt-Vertrauenskette | **zusätzlicher Vermittler + Upstreams** |
| Kontosperr-/Limitrisiko | **unklar bis erhöht** |
| als einziger JARVIS-Provider | **nein** |
| als billiger Bulk-Fallback | **ja, mit Einschränkungen** |
| Geheimnisse / Security-Aufgaben | **nein** |
| irreversible Aktionen direkt nach Nexum-Ausgabe | **nein** |

**Ich würde Nexum also nicht als Scam bezeichnen. Ich würde es aber auch keinesfalls zum Fundament von JARVIS machen.**

Die richtige Position ist:

```text
                 JARVIS SMART ROUTER
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
     Moonshot         Nexum            OpenRouter
     DIRECT            cheap             fallback
   trusted-main      best-effort         breadth
        │                │                 │
       Kimi         Qwen/DeepSeek/...     diverse
        │
   quality path
```

Der direkte Moonshot-Zugang hat zudem einen wichtigen technischen Vorteil für deine Kostenarchitektur: Kimi unterstützt **automatisches Context Caching**. Die aktuelle Dokumentation beschreibt kurzlebige Cache-TTLs und für K3 eine Input-Cache-Hit-Preisrelation von ungefähr **1:10 gegenüber einem normalen Input-Miss**; stabile System-/Tool-/Referenzprefixe sollten deshalb vor dynamische Task-Daten gestellt werden. citeturn12search4

OpenRouter ist dagegen als breiter Fallback sinnvoll, aber nicht datenschutzneutral: Seine aktuelle Privacy Policy weist ausdrücklich darauf hin, dass Inputs personenbezogene Daten enthalten können und dass OpenRouter das Verhalten der jeweils nachgelagerten LLM-Anbieter hinsichtlich Input/Output-Verarbeitung nicht kontrolliert; deren Bedingungen müssen separat berücksichtigt werden. citeturn19view4

**Empfohlener Provider-Stack:**

1. **Moonshot direkt** für Kimi-main und sensible/hochwertige Aufgaben.
2. **Lokales Qwen3** für Klassifikation, Intent, einfache Offline-Aufgaben und privacy-first Fälle.
3. **Nexum** nur für preisgünstige, nicht sensible, wiederholbare Bulk-Aufgaben.
4. **OpenRouter** als Provider-/Modell-Diversitätsfallback.
5. **LiteLLM** lokal als einheitlicher Gateway/Accounting/Fallback-Layer.
6. **`evidence_router` bleibt alleinige Entscheidungsinstanz.**
7. **claude-code-router nur dort, wo Claude-Code-Protokollanpassung gebraucht wird**, nicht als zweites Routinghirn. citeturn19view3turn28search4

Für die derzeit fehlende „echte Quotenquelle“ gilt: **Wenn ein Anbieter keine verlässliche Remaining-Quota-API anbietet, darf der Command Center keine erfundene Restquote anzeigen.** Dann sollte JARVIS lokale Werte führen:

```text
provider_budget
  hard_limit
  soft_limit
  spent_today
  requests_minute
  tokens_minute
  provider_reported_remaining = null | number
  confidence = measured | provider_api | estimated
```

Damit kann der Router auch mit unvollständigen Anbieterdaten sicher entscheiden.


## Vollprivilegien mit Sicherheitsgrenzen

Die größte konzeptionelle Lücke zwischen deinem heutigen System und dem Ziel ist nicht „fehlende Shell“. Sie ist:

> **Es fehlt eine einheitliche, policy-gesteuerte Capability-Schicht, über die Server und Windows-Worker dieselben abstrakten Fähigkeiten anbieten.**

Dein heutiger Zustand laut Inventur:

| Fähigkeit | Server/Bridge `voll` | Windows Worker | Ziel |
|---|---|---|---|
| Shell | teilweise/Claude CLI | stark eingeschränkt | ✅ |
| Dateisystem | vorhanden/abhängig vom Bridge-Modus | Sandbox | ✅ |
| Git | wahrscheinlich über CLI | `java.build`-Umgebung | ✅ |
| GitHub | nicht als einheitliche Capability belegt | ❌ | ✅ |
| Browser | nicht vollständig belegt | ❌ | ✅ |
| Computersteuerung | ❌/nicht belegt | ❌ | ✅ |
| MCP | teilweise Claude-Seite denkbar, nicht systemweit | ❌ | ✅ |
| Subagenten | Claude/Hermes-spezifisch | Spezialisten | ✅ einheitlich |
| Scheduler | V16/systemseitig | kein einheitlicher Agent-Scheduler | ✅ |
| Skills | fragmentiert | Hermes-Spezialisten | ✅ |
| Memory | Vault/Sync | nicht identisch | ✅ |
| Secrets | systemseitig, aber kein zentraler Agent-Broker belegt | eingeschränkt | ✅ |
| Approval | Teilmechanismen | kein einheitliches Modell | ✅ |

Claude Code hat mittlerweile ein recht feingranulares Berechtigungssystem. Lesezugriffe können innerhalb freigegebener Arbeitsverzeichnisse ohne Nachfrage erfolgen, während Shell, Schreibzugriffe und Webzugriffe abhängig vom Modus und von Regeln genehmigungspflichtig sind; Regeln lassen sich nach Werkzeug und Eingabe parametrisieren und über Hooks erweitern. citeturn19view1turn19view2

Hermes geht ähnlich vor, aber mit zusätzlichen Sicherheitsgrenzen: gefährliche Shell-Kommandos werden erkannt, es gibt `smart`, `manual` und `off` als Approval-Modi, und unbeaufsichtigte/cronbasierte Ausführung kann riskante Aktionen standardmäßig **deny** statt automatisch freigeben. citeturn19view0

OpenHands bestätigt dasselbe Muster auf einer anderen Ebene: Für ernsthaften autonomen Betrieb sind pro-Konversation-Sandboxes möglich; ein Betrieb ohne Sandbox wird ausdrücklich als voller Dateisystemzugriff gekennzeichnet. Persistente Workspace-Daten können trotzdem Container-Neustarts überleben. citeturn26search0

Open Interpreter ist ebenfalls besonders relevant für dein Ziel, weil seine aktuelle Linie Shell-Ausführung mit nativen Sandboxes, Skills, MCP, Hooks, Permissions und Computer Use kombiniert. citeturn26search1

**Konkreter Umsetzungsweg: `jarvis-capability-broker`.**

Jeder Executor registriert Fähigkeiten, nicht rohe Maschinenrechte:

```text
filesystem.read
filesystem.write

shell.readonly
shell.exec

git.status
git.commit
git.push

github.read
github.issue.write
github.pr.write

browser.read
browser.interact
browser.download

computer.observe
computer.input

mcp.call

skill.run
subagent.spawn

schedule.create
schedule.modify

memory.read
memory.propose_write

service.status
service.restart

secrets.use
```

Ein Capability-Manifest könnte beispielsweise lauten:

```json
{
  "capability": "git.push",
  "host": "windows-worker",
  "sandbox": "dev-worktree",
  "network": ["github.com"],
  "risk": "external_write",
  "approval": "conditional",
  "supports_rollback": true
}
```

**Der JARVIS-Modus `voll` bedeutet dann: „Darf alle Capabilities anfragen.“** Er bedeutet nicht: „jede Anfrage wird automatisch genehmigt.“

Meine Freigabematrix wäre:

| Aktion | Automatisch? | Zusatzregel |
|---|---|---|
| Dateien lesen im Task-Workspace | ja | Audit |
| Grep/Search/Tests | ja | Ressourcenlimit |
| temporäre Dateien / Build-Artefakte | ja | Sandbox |
| Dateiänderung im isolierten Worktree | ja | Snapshot/Diff |
| Git Commit lokal | ja | Task-ID im Audit |
| Git Push auf Arbeitsbranch | abhängig von Projekt | kein protected branch |
| Merge auf `main` | **Freigabe** | unabhängige Tests vorher |
| öffentliche Websuche/read-only Browser | ja | Egress-Regeln |
| Login in private Accounts | **Freigabe/Policy** | Secrets nie im Prompt |
| E-Mail/Signal an Dritte senden | **Freigabe** | Empfänger+Inhalt anzeigen |
| dein eigener Signal-Self-Chat | auto möglich | Policy-Allowlist |
| Kauf / bezahltes API-Abo | **immer Freigabe** | Betrag anzeigen |
| Providerkosten innerhalb Tagesbudget | auto | Hard Limit |
| Budget erhöhen | **immer Freigabe** | – |
| Dateien löschen, wenn recycle/snapshotfähig | conditional | Restore-Point |
| `rm -rf`, Formatieren, Registry/Systemeingriff | **immer Freigabe** | kein unattended bypass |
| Dienste neu starten | Low-risk Services auto; kritische Freigabe | Healthcheck danach |
| Paketinstallation | conditional | Quelle/Package protokollieren |
| Secrets aus Vault verwenden | conditional | Secret nur an Tool, nicht LLM |
| Secret anzeigen/exportieren | **immer Freigabe** | normalerweise verweigern |
| Firewall/Router/Authelia/Caddy ändern | **Freigabe** | Backup + rollback |
| Home-Assistant Licht/Musik | auto | Allowlist |
| Türschlösser, Alarm, Heizung sicherheitskritisch | **Freigabe** | je Gerät |
| Windows-Aktivierung | nur legitimer Lizenzweg | bestehende Vorgabe |
| Desktop Maus/Tastatur | abhängig von App | sensible Bereiche geblockt |
| Fähigkeit installieren | bis Basis-GO **Freigabe** | danach Capability-Gate |

Freigaben müssen **außerhalb des Prompts technisch erzwungen werden**. Ein Prompt wie „frage vorher“ ist kein Sicherheitsmechanismus.

Der Ausführungspfad wird:

```text
LLM / Agent
    │
    │ Tool request
    ▼
Capability Broker
    │
    ├─ Task-ID + Revision gültig?
    ├─ Capability existiert?
    ├─ Risk policy?
    ├─ Budget?
    ├─ Approval?
    ├─ Secret scope?
    └─ Worker health?
    │
    ▼
Sandbox Executor
    │
    ▼
Evidence Collector
    │
    ▼
Verifier
```

**Server:** Der N2840 sollte primär Control Plane bleiben. Normale Codeausführung kann in bereits vorhandenen Containern/Workspaces stattfinden. Wirklich hostkritische Aktionen gehen an einen kleinen privilegierten `jarvis-host-agent`, der nur definierte Verben anbietet, statt dem LLM eine Root-Shell zu geben.

**Windows:** Aus deiner heutigen `java.build`-AppContainer-Sandbox sollten mehrere Profiles entstehen:

```text
build-netless
    Files + Compiler
    kein Netz

dev-networked
    Files + Git + freigegebene Dev-Domains

browser
    Chromium/Browser Use
    Netzwerk
    isoliertes Browserprofil

desktop
    UI Automation
    normale Benutzerrechte

maintenance-admin
    Windows Admin
    nur interaktiv freigegeben
```

Damit behältst du den Funktionsumfang eines Desktop-Agenten, ohne jeden Task in dieselbe Sicherheitszone zu werfen.

**Secrets:** Das Modell bekommt `secret_ref="github/jarvis-bot"`, niemals den Tokenwert. Erst der Capability Broker injiziert das Secret kurzlebig in den konkreten Child Process oder MCP-Server. Hermes’ Credential-Isolation für MCP-Prozesse ist dafür eine sehr passende Referenz. citeturn19view0

**Audit:** Für jeden Toolschritt:

```text
timestamp
task_id
revision
agent
model
provider
capability
normalized_parameters
approval_id
sandbox
exit/result
evidence_id
duration
cost
secret_refs_used
```

Secretwerte werden vor Persistenz redigiert.

**Kill-Schalter:** Drei Stufen sind sinnvoll:

```text
SOFT STOP
keine neuen Task-Leases

EXECUTION STOP
aktive Executor stoppen,
keine neuen Seiteneffekte

HARD ISOLATE
Provider-/Worker-Sessiontokens widerrufen,
Egress blockieren,
Executor beenden
```

Der Kill-Schalter darf keinen LLM-Aufruf benötigen.

**Recovery-Leiter:** Deine derzeitige Watchdog-Schicht sollte formal auf mindestens diese fünf Stufen gebracht werden:

```text
L1  transient retry + backoff/jitter
L2  Tool/Session neu initialisieren
L3  Executor/Bridge/Worker neu starten
L4  Provider/Modell/Hardware wechseln
L5  Rollback / Quarantäne / Benutzer eskalieren
```

Dazu gehören ein Fehler-Signatur-Hash, maximales Attempt-Budget, Deadline, Circuit Breaker und eine Regel wie **„identische erfolglose Aktion nicht beliebig wiederholen“**. Das ist die fehlende Anti-Stagnation-Schicht zwischen deinem heutigen Watchdog und dem Soll.

Der unabhängige Verifier sollte außerdem **nicht dieselbe Agenteninstanz sein, die das Ergebnis erzeugt hat**. Noch besser:

```text
deterministische Tests
        ↓
statische Checks
        ↓
Artifact/Evidence Check
        ↓
separater Verifier-Agent
        ↓
bei Hochrisiko ggf. anderer Provider
```

So muss nicht jeder triviale Build einen zweiten großen LLM-Call bezahlen.


## Effizienz, Stimme und schwacher Master

### Token- und Kostensparen ohne Qualitätsverlust

Die Reihenfolge ist wichtig. Ich würde **nicht zuerst billigere Modelle** einsetzen, sondern zuerst unnötigen Kontext eliminieren.

| Maßnahme | realistischer Effekt | Qualitätsrisiko | Priorität |
|---|---|---|---|
| Kimi Prompt/Context Caching | sehr hoch bei wiederkehrenden Prefixen | praktisch keines bei korrekter Struktur | **sehr hoch** |
| Progressive Skills | hoch | niedrig | **sehr hoch** |
| Tool-Schemas nur bei Bedarf | mittel–hoch | niedrig | **sehr hoch** |
| Council nur bei komplexen Tasks | sehr hoch | niedrig bei guter Klassifikation | **sehr hoch** |
| lokaler Intent-/Route-Classifier | mittel | niedrig | hoch |
| Memory-Retrieval statt Chat-Historie | hoch | mittel bei schlechtem Retrieval | hoch |
| Task-Summaries + Artifact-Pointer | hoch | niedrig | hoch |
| deterministische Tests vor LLM-Verifier | mittel–hoch | keines | hoch |
| lokales Qwen für einfache Aufgaben | mittel | mittel | selektiv |
| Nexum für Bulk | Kosten hoch reduzierbar | Provider-/Qualitätsrisiko | selektiv |
| Batch-API | hoch bei Offline-Massenjobs | nicht für interaktive Tasks | später |

Kimis eigener Cache ist hier besonders attraktiv. Stabile Bestandteile sollten vorne liegen:

```text
[ JARVIS core identity ]
[ tool contracts ]
[ safety policy ]
[ project architecture ]
[ stable task context ]
------------------------------ cacheable
[ current task revision ]
[ latest tool results ]
[ latest user message ]
```

und **nicht**:

```text
timestamp
dynamic counters
random UUID
current user message
...
giant stable system prompt
```

weil schon früh wechselnder Inhalt die Wiederverwendung eines langen Prefixes zerstört. Moonshots aktuelle Dokumentation beschreibt genau diese Prefix-basierte Cache-Logik und einen starken Preisabschlag bei Cache Hits. citeturn12search4

Claude Codes aktuelle Skills-/Subagent-Architektur weist in dieselbe Richtung: kurze Skill-Beschreibungen können verfügbar sein, während die eigentlichen Anweisungen erst bei Verwendung geladen werden; isolierte Subagenten verhindern, dass jeder Spezialist den Hauptkontext dauerhaft aufbläht. citeturn16search1

Für JARVIS bedeutet das beispielsweise:

```text
FALSCH:
Jeder Task erhält:
- alle 18 Spezialistenprompts
- alle MCP-Schemas
- kompletten Vault
- kompletten Chat
- alle Serverinformationen

RICHTIG:
Task erhält:
- JARVIS Core ~ kompakt
- Task Revision
- relevante 1–3 Skills
- relevante Tools
- 3–8 Memory-Chunks
- bei Bedarf 1 Council
```

Die Einsparpotenziale dürfen nicht addiert werden. Als **Planungsannahme**, nicht als Benchmark-Garantie, halte ich bei deinem Workload nach Bereinigung der Prompts und Einführung von Cache/Skills/Retrieval **ungefähr 30–55 % weniger wiederkehrenden externen Input-Kosten** für plausibel, wenn viele Tasks dieselben JARVIS-, Tool- und Projektprefixe verwenden. Bei einmaligen Aufgaben kann der Effekt deutlich kleiner sein.

Für Memory würde ich nach jedem erfolgreich abgenommenen Auftrag nicht den Chat kopieren, sondern eine Extraktionspipeline starten:

```text
fertiger Task
    │
    ▼
Knowledge Candidate Extractor
    │
    ├─ dauerhafte Tatsache?
    ├─ Architekturentscheidung?
    ├─ wiederverwendbares Verfahren?
    ├─ gelöster Fehler?
    └─ Benutzerpräferenz?
    │
    ▼
Provenance + Confidence + Evidence
    │
    ▼
Dedupe / contradiction check
    │
    ├─ hohe Sicherheit ──► Vault
    └─ unsicher ─────────► Review Queue
```

Ein Eintrag sollte etwa enthalten:

```yaml
type: architecture_decision
project: MA-HOME
fact: "V16 ist autoritative Task-State-Machine"
valid_from: 2026-10-28
source_task: T-0042
source_revision: 4
evidence:
  - E-1234
confidence: 0.97
```

Das verbindet dein Obsidian-Ziel mit den starken Ideen hinter Mem0 und Graphiti, ohne deren gesamte Infrastruktur zu übernehmen. Mem0 fokussiert selektives Langzeitgedächtnis; Graphiti ergänzt zeitliche Gültigkeit und Provenienz. citeturn23view1turn21search0

### Sprachlatenz: von 5–6 Sekunden auf unter 4 Sekunden

Deine 5–6 Sekunden sind nicht weit vom Ziel entfernt. Ich würde **keinen kompletten Sprachstack neu bauen**.

Der wahrscheinlich wichtigste Umbau ist von einer seriellen zu einer überlappenden Pipeline:

```text
Heute sinngemäß:
Sprache fertig
    ↓
Whisper komplett
    ↓
LLM komplett/weitgehend
    ↓
Piper
    ↓
Audio

Ziel:
Audio ────────► streaming STT ────────┐
       VAD ────────────────────────────┤
                                      ▼
                               Intent/Router
                                      │
                             LLM stream tokens
                                      │
                    erste sprechbare Phrase
                                      ▼
                               TTS stream
                                      │
                                      ▼
                                erster Ton
```

faster-whisper ist dafür auf deinem RTX-2060-Worker besonders plausibel, weil das Projekt CTranslate2 und INT8 unterstützt und in seinen Benchmarks deutlich niedrigere Inferenzzeiten bzw. Speicherlast als einige Whisper-Alternativen zeigt. citeturn22search4turn22search6

Silero kann das Ende eines Turns kontinuierlich und sehr leichtgewichtig bestimmen, einschließlich ONNX-Betrieb; Pipecat kombiniert bereits VAD, Whisper, Ollama, Piper und streamingfähige Voice-Pipelines. citeturn25search1turn24search0

Mein Zielbudget wäre als **Engineering-Zielwert**, nicht als bereits gemessene Leistungszusage:

| Abschnitt | Ziel |
|---|---:|
| VAD / End-of-turn | 0,2–0,5 s |
| finale/partielle STT | 0,4–1,0 s |
| Routing | <0,1 s |
| LLM first useful tokens | 0,3–1,0 s |
| erster TTS-Chunk | 0,15–0,5 s |
| Netzwerk/Puffer | 0,1–0,4 s |
| **Ziel erster Ton** | **ca. 1,5–3,5 s** |

Auf deiner Hardware würde ich **Kimi K3.1 Pro Highspeed oder lokales Qwen für die interaktive erste Antwort** testen und komplexe Hintergrundarbeit danach an Kimi-main übergeben. Der Gesprächspartner hört dann beispielsweise früh „Verstanden. Ich prüfe zuerst …“, während der persistente Auftrag unabhängig davon weiterläuft.

Der alte `rhasspy/piper`-Runtime sollte mittelfristig zumindest gegen die neue Open-Home-Foundation-Linie getestet werden, weil das alte Repository archiviert wurde. Die neue Linie steht allerdings unter GPL‑3.0; für Distribution/Integration sollte die konkrete Lizenzwirkung deiner Einbindungsform geprüft werden. citeturn22search0turn25search2

### Living HQ ohne Serverlast

Hier würde ich Pixel Agents fast **architektonisch abschauen**:

```text
V16 / Council / Worker
         │
         ▼
normalized AgentEvent
         │
         ├─ task.assigned
         ├─ agent.thinking
         ├─ tool.read
         ├─ tool.write
         ├─ tool.execute
         ├─ council.meeting
         ├─ approval.waiting
         ├─ test.running
         ├─ verifier.running
         ├─ task.failed
         └─ task.completed
         │
         ▼
WebSocket/SSE
         │
         ▼
Browser Canvas
```

Pixel Agents selbst setzt Agent-Events, Canvas 2D, Pathfinding und Charakter-State-Machines ein. Diese Architektur passt ideal, weil die **grafische Arbeit im Handy-/PC-Browser statt auf dem Celeron** stattfindet. citeturn27search3

Deine Figuren könnten dadurch echte Bedeutung bekommen:

- DEV-Agent läuft zur Werkbank → Build läuft.
- SECURITY-Figur geht ins holografische Prüfzentrum → Security Review.
- Council versammelt sich um einen Tisch → aktive Beratung.
- rote Resonanzleitung pulsiert zwischen Worker und Server → Artefakttransfer.
- Figur bleibt mit Warnsymbol stehen → Approval/Incident.
- Werkstück wechselt in grüne Prüfkammer → unabhängige Abnahme.

Damit wird Living HQ nicht bloß Dekoration, sondern eine alternative Darstellung deines echten Event Logs.

### Der N2840 ist Control Plane, nicht AI-Host

Auf deinem laut Inventur mit **3,2 GB RAM** ausgestatteten Master würde ich ausdrücklich **nicht zusätzlich** betreiben:

- Langfuse + ClickHouse self-hosted,
- Neo4j/FalkorDB für Graphiti,
- OpenHands Agent Canvas mit mehreren lokalen Sandboxes,
- Chromium-Browserautomation,
- Embedding-/Reranker-Modelle,
- weitere lokale LLMs,
- schwere Voice-Inferenz.

Langfuse bestätigt selbst, dass seine heutige Self-hosted-Plattform ClickHouse verwendet; Graphiti verlangt ein Graph-Backend wie Neo4j/FalkorDB/Neptune sowie LLM-/Embedding-Komponenten. Diese beiden Systeme wären auf deinem Master deshalb aus meiner Sicht unverhältnismäßig. citeturn20search0turn21search0

Der Master sollte hauptsächlich betreiben:

```text
Caddy / Authelia
Portal
V16
PostgreSQL
Router Policy
Capability Broker coordinator
Watchdog
Signal
kleine OTel-Metriken
Vault/Sync
Home Assistant
```

und schwere Arbeit an den Ryzen/RTX-Worker delegieren.

Auch Observability sollte sparsam sein: **100 % Incidents, Security-Events, Approvals und Fehlversuche aufzeichnen; normale erfolgreiche Detailtraces samplen oder nach kurzer Retention verdichten.** OTel eignet sich als neutrales gemeinsames Schema, ohne dass du deshalb die komplette Langfuse-Plattform lokal installieren musst. citeturn20search0turn20search2


## Priorisierte Roadmap und Abnahmekriterien

Ich würde deine vorhandene Prioritätenliste fast vollständig beibehalten. Eine einzige Abhängigkeit muss technisch angepasst werden: **Der Sicherheitskern aus „volle Privilegien“ muss vor den gefährlichen Teilen von Phase C existieren**, weil Browser-, Mail-, Desktop- und Smart-Home-Autonomie ohne Capability-/Approval-Broker nicht sicher freigeschaltet werden sollte. Das heißt nicht, dass Vollprivilegien als Feature vorgezogen werden; nur die Sicherheitsbasis wird früher angelegt.

| Reihenfolge | Arbeitspaket | Aufwandsschätzung | Nutzen | GO-Kriterium |
|---|---|---:|---|---|
| **Auftrag ändern** | immutable Task-ID + Revision, Leases, Supersede, Voice-Update | ca. 2–4 Personentage | **sehr hoch** | Neustart-, Race-, Voice- und Side-effect-Tests grün |
| **Fach-Councils** | acht Council-Gruppen, Rollen, Decision Artifact, Metriken | ca. 4–8 PT | **sehr hoch** | beratende Rechte technisch erzwungen; Entscheidung reproduzierbar |
| **Smart Router aktivieren** | Policy scoring, LiteLLM/Provider adapters, Quotenledger, Canary | ca. 6–12 PT plus Messdaten | **sehr hoch** | Shadow-Eval bestanden, kein Risk-Policy-Verstoß |
| **Living HQ** | Eventmodell + Figuren/Animation/Originaldesign | ca. 3–7 PT | mittel/hoher UX-Wert | jede Figur wird von realem Eventzustand getrieben |
| **Memory Transfer** | Candidate Extractor, Provenienz, Dedupe, Vault Writer | ca. 3–6 PT | **hoch** | kein ungeprüftes Chat-Dumping; Rückverfolgung zu Evidence |
| **Voice <4 s** | Streaming STT/LLM/TTS, warm models, VAD, fast route | ca. 3–7 PT | hoch | echtes Handy p50 <4 s; Barge-in funktioniert |
| **Basis-GO** | Recovery, Security, mobile/voice, Restore-Endtest | eigener Gate statt Feature | **kritisch** | definierte Schlussabnahme vollständig |
| **Capability-Security-Kern** | Broker, Approval, Audit, Secrets, Kill | ca. 5–10 PT | **kritisch für Phase C** | keine Capability umgeht Policy |
| **Phase C** | Mail, Browser, Modding, Medien, Smart Home usw. | jeweils eigenes Modul | sehr hoch | Capability-by-Capability-Abnahme |
| **Vollständige PC-Parität** | Browser/Desktop/MCP/Schedules/Skills/Memory auf allen Workern | ca. 10–20+ PT | sehr hoch | Capability Matrix vollständig |

Die Aufwandsschätzungen sind **Planungsgrößen**, keine Aussagen darüber, wie lange deine konkrete Implementierung tatsächlich dauern wird; insbesondere Browser-/Desktopautomation und fremde APIs können stark variieren.

**Das erste Paket – Revisionen – würde ich nicht überspringen.** Ohne Revisionen kann eine Sprachänderung während eines laufenden Auftrags zu einem gefährlichen Mischzustand führen. Das Abnahme-Set sollte mindestens enthalten:

```text
Task T rev1 läuft
→ rev2 während Planung
→ rev1 stoppt sauber

Task T rev1 schreibt Datei
→ rev2 kommt an
→ bereits erledigte sichere Arbeit wird korrekt bewertet

Task T rev1 steht vor externem Seiteneffekt
→ rev2 kommt an
→ rev1 darf Seiteneffekt nicht mehr starten

Server-Neustart bei rev3
→ current_revision bleibt rev3
→ kein rev2-Executor startet erneut

Voice:
"stopp" während JARVIS spricht
→ Audio stoppt
→ Task läuft weiter

Voice:
"ändere Auftrag T-42 ..."
→ neue Revision
→ Task bleibt dieselbe Task-ID
```

**Council-GO:** Nicht „Agenten konnten miteinander chatten“, sondern beispielsweise:

```text
Council DEV angefordert
→ nur DEV-Rollen aktiviert
→ max. fünf Fachrollen
→ kein Council-Agent besitzt operative Shell
→ Decision Artifact gespeichert
→ Dissens sichtbar
→ Token-/Zeitkosten gemessen
→ Hermes erhält genau die beschlossene Revision
```

**Router-GO:** Ich würde nicht direkt von Shadow auf 100 % wechseln. Erst eine repräsentative Menge historischer und neuer Tasks rückwirkend durch den neuen Router bewerten, dann Entscheidungen mit deinem bisherigen Weg vergleichen. Danach ein kleiner Canary-Anteil, anschließend hochskalieren. Kritische Tasks sollten zunächst weiterhin direct-Moonshot bzw. bewährte Provider verwenden. RouteLLM zeigt, warum datengetriebene Routing-Evaluation wichtig ist; LiteLLM und ähnliche Gateways können danach die gewählte Route technisch ausführen. citeturn6search0turn28search4

Für den Router würde ich folgende Score-Funktion beginnen lassen:

```text
score =
    quality_prediction   * 0.35
  + reliability          * 0.20
  + privacy_fit          * 0.15
  + latency_fit          * 0.10
  + cost_efficiency      * 0.10
  + quota_health         * 0.05
  + cache_fit            * 0.05
```

Diese Gewichte sind **Startparameter**, keine Wahrheit. Security/Capability sind ohnehin harte Filter und gehören nicht in einen weichen Score.

Beispiel:

```text
Task: "Analysiere dieses private Serverlog auf Sicherheitsprobleme."

Nexum:
privacy policy → nicht ausreichend für sensitive class
=> ausgeschlossen

Local Qwen:
privacy excellent, quality maybe medium
=> Candidate

Kimi direct:
privacy/provider policy acceptable, quality high
=> Candidate

Router:
Kimi direct für Analyse
Local Qwen ggf. Vorfilter
```

Dagegen:

```text
Task: "Fasse 80 öffentliche README-Dateien grob thematisch zusammen."

Nexum:
eligible
cheap
no secrets
reproducible
=> sehr guter Candidate
```

**Memory-GO:** Ein sauberer Task-Abschluss sollte zukünftig ungefähr so aussehen:

```text
EXECUTION DONE
      ↓
Tests
      ↓
Independent verification
      ↓
Evidence complete
      ↓
Task CLOSED
      ↓
Knowledge candidates
      ↓
dedupe / contradiction
      ↓
Vault
```

Nicht:

```text
Task CLOSED
→ kompletten Chat nach Obsidian kopieren
```

**Voice-GO** muss zwingend auf dem echten Handy stattfinden. Desktop-Simulation oder künstliche Audioeinspeisung reicht für dein Produktziel nicht. Dazu gehören reale WLAN-Latenz, Mikrofonberechtigungen, Screen-off/PWA-Verhalten, Unterbrechen, Wakeword, Folgefragen und „Audio stoppen, Auftrag weiterlaufen lassen“.

**Living-HQ-GO:** Jede Animation muss einen technischen Ursprung besitzen. Ein Agent darf nicht „arbeiten“, nur weil ein Zufallstimer die Figur tippen lässt. Pixel Agents zeigt ein gutes Muster: Hooks beziehungsweise Runtime-Ereignisse werden normalisiert und treiben den sichtbaren Zustand. citeturn27search3

**Basis-GO vor Capability-Autonomie:** Ich würde es erst geben, wenn mindestens folgende Eigenschaften gemeinsam erfüllt sind:

- Tasks überleben Portal-, Bridge- und Serverprozessneustarts.
- Revisionen funktionieren atomar.
- Council-Rechte sind technisch nur beratend.
- keine Erfolgsmeldung ohne Evidence.
- Watchdog-L1–L5 und Anti-Loop sind real getestet.
- Router kann auf einen defekten Provider automatisch ausweichen.
- Kosten-/Providerwerte werden nicht erfunden, wenn eine Quelle fehlt.
- Kill-Schalter stoppt Ausführung ohne LLM.
- Restore aus Backup ist einmal praktisch durchgespielt.
- echtes Handy/PWA und reale Stimme wurden von dir geprüft.
- Geheimnisse tauchen nicht in LLM-/Audit-/Signal-Logs auf.

Erst danach sollte JARVIS selbstständig neue Fähigkeiten evaluieren und registrieren.

**Phase C sollte dann nicht als riesiges Paket gebaut werden, sondern als Capability-Folge:**

```text
C1  browser.read
C2  browser.interact
C3  mail.read
C4  mail.draft
C5  mail.send
C6  computer.observe
C7  computer.input
C8  homeassistant.read
C9  homeassistant.safe_action
...
```

Jede Capability bekommt Threat Model, Sandbox, Approval-Regel, Tests, Evidence-Schema und Kill-Verhalten. Browser Use bietet dafür eine sehr leistungsfähige Browserbasis; Open Interpreter zeigt eine moderne Kombination aus Sandbox, Computer Use, MCP und Skills; Home Assistant sollte für Smart Home die einzige Hardware-Abstraktionsschicht bleiben. citeturn29view1turn26search1turn27search1

**Mein Endurteil zum Gesamtprojekt lautet daher:**

Dein System hat nach dem von dir gelieferten Stand **kein grundlegendes Architekturproblem und braucht keinen dritten Neustart unter einem neuen Frameworknamen**. Die vorhandenen Komponenten bilden bereits die richtigen Ebenen. Was fehlt, sind verbindliche Verträge zwischen ihnen.

Die fünf wichtigsten davon sind:

**Task Contract:** `Task-ID + immutable Revision + Lease + Evidence`.

**Council Contract:** beraten, dokumentieren, nie direkt ausführen.

**Capability Contract:** Agent fordert Fähigkeit an; Policy entscheidet; Sandbox führt aus.

**Router Contract:** JARVIS entscheidet anhand von Qualität, Risiko, Providerzustand und Kosten; Provider-Gateway führt nur aus.

**Knowledge Contract:** Nur belegte, wiederverwendbare Information gelangt ins Langzeitgedächtnis.

Mit diesen Verträgen kann dein bestehendes MA‑HOME tatsächlich in Richtung des gewünschten „JARVIS“ wachsen, ohne dass du LangGraph, CrewAI, OpenHands, Hermes, LiteLLM, Pipecat oder irgendeinen anderen Fremdstack zum neuen Zentrum machst. Diese Projekte sollten **Bauteilkatalog und Referenzarchitektur** sein. **JARVIS HQ bleibt das System.**