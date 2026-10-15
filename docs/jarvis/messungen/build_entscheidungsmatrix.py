#!/usr/bin/env python3
"""Builds JARVIS-REFERENZ-ENTSCHEIDUNGSMATRIX.csv: every catalog entry once, with decision and evidence level.
Usage: python3 -I build_entscheidungsmatrix.py <Masterkatalog.md> <Assistenten-Referenzen.md> <meta.json> <out.csv>
Evidence levels: QUELLCODE (files read at the pinned commit) | METADATEN (GitHub API only) | KATALOG (taken from the catalog, not checked).
Rows with KATALOG evidence carry the catalog's own recommendation and are NOT verified by this audit."""
import csv
import json
import re
import sys

COLS = ['Projekt', 'Repo', 'Commit/Datum', 'Lizenz', 'Architekturidee', 'V16 bereits vorhanden?', 'Konkrete V16-Lücke', 'Nachweis',
        'Integrationsform', 'Sicherheitsrisiko', 'CPU/RAM/Storage/Token-Effekt', 'Aufwand', 'Tests', 'Qualität vor/nach', 'Entscheidung', 'Nachweisstufe']

# examined by source reading (QUELLCODE) or API metadata (METADATEN); keys are lower-case GitHub paths
X = {
 'nousresearch/hermes-agent': ('QUELLCODE', 'Begrenztes, eingefrorenes Gedächtnis (MEMORY.md 2.200 Zeichen) + dreistufiges Laden von Skills (Liste ~3k Token, dann Inhalt, dann Referenzdatei) + Quarantäne und Scan mit Inhalts-Hash',
   'Teilweise: learning.py (Vorlagen, Lehren), Drop-ins hash-gepinnt (capabilities.py Z. 298/517); der Planer bekommt aber den ganzen Fähigkeitenkatalog', 'Keine gestufte Fähigkeiten-Offenlegung, kein Größenlimit der Lehren',
   'website/docs/user-guide/features/memory.md, skills.md (Zeilen 172-179, 355-364); SECURITY.md vorhanden', 'einzelne Idee (vorgemerkt, nicht gebaut)', 'niedrig (nur Idee)', 'Token: Katalog-Auszug statt Volltext möglich, nicht gemessen', 'klein', 'keine',
   'nicht gemessen', 'Idee vormerken; nichts installieren'),
 'nearai/ironclaw': ('QUELLCODE', 'Zwei unabhängige Schutzschichten (Redaktion an der Erzeugungsstelle + Typen, die durchgerutschte Geheimnisse verweigern); Marker nur an Wortgrenzen (Lehre: "Secretary" ≠ "secret"); Freigabe ist ein eng begrenzter Grant mit Fingerabdruck der konkreten Aktion',
   'Vorher nein (nur Regex), jetzt ja: secretscan.py, Eingangssperre plus Redaktion, Wortgrenzen-Fehlalarmtests', 'Freigabe nicht an einen Fingerabdruck der Rückfrage gebunden (nur an Auftrag und wartenden Schritt)',
   'crates/contracts/ironclaw_host_api/src/credential_redaction.rs (Z. 1-66), approval.rs (Z. 1-70)', 'einzelne Idee (A9 umgesetzt, Fingerabdruck vorgemerkt)', 'keins durch Übernahme der Idee; Rust-Laufzeit wäre Fremdcode auf dem Master', 'Repo ~1 GB, Rust-Toolchain: nicht installiert',
   'A9 erledigt', 'tests/test_v16_regress_a9_a14.py (A9: 5 Tests)', 'A9: 2 von 11 Sätzen vorher erkannt, nachher 11/11; Fehlalarme vorher und nachher 0/8 (Messung am alten Muster)', 'Ideen übernommen, nicht installiert'),
 'agent0ai/agent-zero': ('QUELLCODE', 'Erweiterungspunkte als Dateien (extensions/python/_functions/...), Projekte, Skills, Subagenten',
   'Ja: capabilities.py (Registry mit Selbsttest, Drop-ins)', 'keine belegte', 'LICENSE (MIT-Text; GitHub meldet NOASSERTION wegen angepasstem Kopf); Dateiliste Erweiterungen', 'nur Referenz', 'hoch bei Installation (Shell-Agent mit eigenem Gedächtnis)', 'zweites Gehirn/Gedächtnis: unerwünscht', 'n/a', 'n/a', 'n/a', 'ablehnen als Installation; Referenz'),
 'openclaw/openclaw': ('QUELLCODE', 'Werkzeug-Richtlinie wird VOR dem Modellaufruf erzwungen: das Modell sieht nur Tools, die Profil, Allow/Deny, Sandbox und Kanalrechte überleben',
   'Ja, gleichwertig: Planer sieht nur getestete Fähigkeiten (catalog_for_planner), Worker-Tools fest (WORKER_TOOLS)', 'keine', 'docs/tools/index.md (Z. 47, 146-149), LICENSE MIT', 'nur Referenz', 'gemeinsame Gateways ≠ Mandantentrennung (laut Auftrag)', 'Repo ~9 GB: nicht installiert', 'n/a', 'n/a', 'n/a', 'ablehnen als Installation; bestätigt V16-Ansatz'),
 'letta-ai/letta-code': ('QUELLCODE', 'Agentengedächtnis als Git-Repository mit Commit-Hooks und Signierung (src/agent/memory-git-*.ts)',
   'Teilweise: Vault ist Git/Obsidian; das Lernen in brain.db hat Rückzug (retract) aber keine Versionshistorie', 'Keine Versionierung der gelernten Vorlagen', 'Nur Dateinamen und LICENSE gelesen (Apache-2.0); Inhalte der memory-git-Dateien NICHT gelesen', 'nur Referenz', 'n/a', 'keine zweite Datenbank (Auftrag)', 'n/a', 'n/a', 'n/a', 'Referenz; keine Übernahme'),
 'khoj-ai/khoj': ('METADATEN', 'Second Brain mit semantischer Suche, Quellen, Agenten', 'Vault + vault-q + FTS5 vorhanden', 'Quellenregister für Aufträge fehlt', 'API: AGPL-3.0, letzter Commit 2026-08-02', 'ablehnen als Code (AGPL), nur Idee Quellenregister', 'Lizenz: Copyleft über Netzwerknutzung', 'zweites Wissenssystem: unerwünscht', 'n/a', 'n/a', 'n/a', 'ablehnen'),
 'kortix-ai/suna': ('METADATEN', 'Isolierte Arbeitssitzungen mit belegten Artefakten', 'Teilweise: Arbeitsordner je Auftrag, Manifest mit sha256', 'keine belegte', 'API: Lizenz NOASSERTION (nicht geprüft), aktiv 2026-10-15', 'nur Referenz', 'Lizenz unklar: keine Codeübernahme', 'Cloud-Computer-Plattform: zu schwer', 'n/a', 'n/a', 'n/a', 'ablehnen'),
 'aaif-goose/goose': ('QUELLCODE', 'Kette von Prüfern vor jedem Tool-Aufruf (Security-, Egress-, Permission-, Adversary-Inspector), jeder liefert erlauben/ablehnen/Freigabe nötig; Rechtestufen je Tool',
   'Teilweise: classify_request (Datenklasse, Wirkungen), plan_approval, Router-Regeln, Ledger-Grenzen', 'Keine einheitliche Prüfer-Kette; Entscheidungen verstreut', 'crates/goose/src/security/egress_inspector.rs, permission/permission_inspector.rs (nur Kopfteile gelesen), LICENSE Apache-2.0', 'einzelne Idee (vorgemerkt)', 'Rust-Laufzeit: nicht installiert', 'n/a', 'mittel', 'n/a', 'nicht gemessen', 'Idee vormerken; nichts installieren'),
 'leon-ai/leon': ('METADATEN', 'Persönlicher Sprachassistent mit Skills', 'nein (Voice ist P3)', 'Voice später', 'API: MIT, aktiv 2026-10-12; Auftrag: 2.0 nur Developer-Preview', 'nur Referenz (P3)', 'Preview-Software', 'n/a', 'n/a', 'n/a', 'n/a', 'später'),
 'openhands/software-agent-sdk': ('QUELLCODE', 'Bestätigungsrichtlinie plus Sicherheitsanalyse je Aktionsbündel als eigenes Ereignis (SecurityAnalysisEvent), Geheimnis-Register mit Redaktion an Exportgrenzen',
   'Teilweise: Ereignisprotokoll (job_events) vorhanden, aber ohne Risikostufe je Aktion', 'Risikostufe je Aktion als Ereignis fehlt', 'openhands-sdk/.../event/security.py (Z. 1-50), openhands-agent-server/.../_secret_redaction.py (Z. 1-60), LICENSE MIT', 'einzelne Idee; Worker-Labor NICHT ausgeführt (AMD-Worker nicht belegt)', 'Container-Workspaces: nur auf isoliertem Worker', 'schwacher Master: nicht installiert', 'n/a', 'n/a', 'n/a', 'Idee vormerken; Worker-Labor nur als Plan'),
 'openinterpreter/open-interpreter': ('METADATEN', 'Computer als Werkzeug (Code-Ausführung)', 'nein', 'keine', 'API: Repo umgezogen nach openinterpreter/openinterpreter, jetzt Rust, Apache-2.0, 2026-10-11', 'ablehnen', 'hoch: Shell-/Dateizugriff ohne belegte Sandbox', 'n/a', 'n/a', 'n/a', 'n/a', 'ablehnen auf dem Master'),
 'restatedev/agent': ('QUELLCODE', 'Freigabe als benanntes Signal mit approvalId und turnId; wird der Wartevorgang unterbrochen, wird die Anfrage zurückgezogen; Entscheidung ist ein Typ',
   'Teilweise: waiting_approval, jetzt mit Antwortpflicht und Urheber', 'Rückzug offener Anfragen bei Abbruch ist über cancel() gelöst (Schritte skipped)', 'packages/libs/core/src/session/approvals.ts (Z. 1-60); im Dateibaum KEINE LICENSE-Datei (API: license None)', 'nur Referenz (keine Lizenz: kein Code kopieren)', 'Lizenz fehlt', 'n/a', 'n/a', 'n/a', 'n/a', 'ablehnen als Code; Idee bestätigt'),
 'langchain-ai/langgraph': ('QUELLCODE', 'interrupt() pausiert, wird nur durch einen Fortsetzungswert aufgelöst (Command(resume=...)), optional mit response_schema; Knoten läuft beim Fortsetzen von vorn (Idempotenz nötig)',
   'Vorher nein: Freigabe war ein Flag ohne Antwortwert; jetzt: Antwort ist der Wert, leer = abgelehnt', 'Typisierte Antwort (response_schema) fehlt', 'libs/langgraph/langgraph/types.py (interrupt, Z. 896-963), LICENSE MIT', 'einzelne Idee (A14 umgesetzt)', 'keins', 'keine zweite Orchestrierung', 'A14 erledigt', 'tests/test_v16_regress_a9_a14.py (A14: 8 Tests)', 'A14: Freigabe ohne Antwort vorher möglich, nachher blockiert', 'Idee übernommen, nicht installiert'),
 'trycua/cua': ('METADATEN', 'Computer-Use-Infrastruktur', 'nein', 'Computersteuerung ist P3', 'API: MIT, aktiv 2026-10-15', 'Worker-Labor nur als Plan', 'hoch ohne Isolation', 'GUI-Sandbox: schwerer als der Laptop trägt', 'n/a', 'n/a', 'n/a', 'später'),
 'mintplex-labs/anything-llm': ('METADATEN', 'Dokumente + Agents + Mehrbenutzer', 'Teilweise', 'keine belegte', 'API: MIT, 2026-10-14', 'nur Referenz', 'n/a', 'zweite Knowledge-App: unerwünscht', 'n/a', 'n/a', 'n/a', 'ablehnen'),
 'danny-avila/librechat': ('METADATEN', 'Multimodell-Chat, MCP, Rollen', 'Portal-Chat vorhanden', 'keine', 'API: Repo leitet nach LibreChat-AI/LibreChat weiter, MIT', 'nur Referenz', 'n/a', 'zweite Oberfläche: unerwünscht', 'n/a', 'n/a', 'n/a', 'ablehnen'),
 'microsoft/agent-framework': ('METADATEN', 'Sessions, Workflows, Multi-Agent', 'Task-Engine vorhanden', 'keine', 'API: MIT, 2026-10-15', 'nur Referenz', 'n/a', 'zweite Runtime: unerwünscht', 'n/a', 'n/a', 'n/a', 'ablehnen'),
 'pydantic/pydantic-ai': ('METADATEN', 'Typisierte Ausgaben und Tool-Aufrufe', 'Ja: validate_plan prüft Pläne streng (Schema, Pfade, Fähigkeiten)', 'keine belegte', 'API: MIT, 2026-10-15', 'nicht nötig', 'neue Abhängigkeit', 'n/a', 'n/a', 'n/a', 'n/a', 'nicht übernehmen'),
 'aider-ai/aider': ('QUELLCODE', 'Repo-Map: Symbole per tree-sitter, Rangfolge per PageRank (networkx), Ausgabe im Token-Budget',
   'Nein', 'Kompakte Code-Übersicht für Claude-Aufträge fehlt', 'aider/repomap.py (tree_sitter-Import Z. 19, pagerank Z. 525, max_map_tokens Z. 70), LICENSE.txt Apache-2.0; letzter Commit 2026-05-22', 'PoC mit Standardbibliothek (ast) gebaut: docs/jarvis/messungen/repomap_poc.py', 'keins', '559.664 → 5.933 Zeichen (1,1 %), nur Größe; Nutzen für Claude nicht gemessen', 'klein', 'PoC läuft, keine Tests im Repo', 'nicht gemessen', 'Idee als PoC; nicht integriert'),
}


def catalog_rows(paths):
    seen = {}
    pat = re.compile(r'^\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*\|(.*)\|\s*$')
    for p in paths:
        for line in open(p, encoding='utf-8'):
            m = pat.match(line.strip())
            if not m:
                continue
            name, url, rest = m.group(1), m.group(2), [c.strip() for c in m.group(3).split('|')]
            seen.setdefault(url.rstrip('/'), (name, rest))
    return seen


def default_decision(rest):
    t = ' '.join(rest)
    if 'Später' in t or 'später' in t:
        return 'später (nicht Teil dieses Auftrags)'
    if re.search(r'Referenz|Vorbild|Architektur|Nur Referenz|Konzept', t):
        return 'nur Referenz (nicht installiert)'
    if re.search(r'AMD|Worker|P1', t):
        return 'Worker-Labor-Kandidat; nicht ausgeführt (kein Worker belegt)'
    if re.search(r'Direkt|Vorhandenes|Bestehendes', t):
        return 'vorhandenes bzw. Standardwerkzeug; keine Änderung'
    return 'ungeprüft'


if __name__ == '__main__':
    cat1, cat2, meta_p, out = sys.argv[1:5]
    meta = {k.lower(): v for k, v in json.load(open(meta_p)).items()}
    rows = []
    done = set()
    for key, v in X.items():
        m = meta.get(key, {})
        repo = f"https://github.com/{m.get('full_name', key)}"
        stamp = f"{m.get('sha', '?')} / {str(m.get('commit_date', ''))[:10]}"
        lic = m.get('license') or 'keine/unklar'
        rows.append([key.split('/')[-1], repo, stamp, lic, *v[1:12], v[0]])
        done.add(repo.lower())
        done.add(f'https://github.com/{key}')
    for url, (name, rest) in sorted(catalog_rows([cat1, cat2]).items(), key=lambda kv: kv[1][0].lower()):
        if url.lower() in done:
            continue
        rows.append([name, url, 'nicht gepinnt', 'nicht geprüft', ' | '.join(rest)[:160], 'ungeprüft', 'ungeprüft', 'Katalogangabe', default_decision(rest),
                     'nicht bewertet', 'nicht gemessen', 'nicht bewertet', 'keine', 'nicht gemessen', default_decision(rest), 'KATALOG'])
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for r in rows:
            r = (r + [''] * len(COLS))[:len(COLS)]
            w.writerow(r)
    print(len(rows), 'Zeilen,', sum(1 for r in rows if r[-1] != 'KATALOG'), 'geprüft (QUELLCODE/METADATEN)')
