"""Capability-Broker (Capability-Vertrag, 28.10.2026): Agent fordert Fähigkeit an, Policy entscheidet, Sandbox führt aus.

Prüfreihenfolge je Werkzeugschritt (deterministisch, kein Modell): Not-Aus-Stufe -> Auftrag aktiv und Revision aktuell ->
Fähigkeit registriert/getestet -> Risiko-Policy (auto | conditional | approval | deny) -> Budget -> Freigabe (an Auftrag,
Revision, Schritt und Parameter gebunden, einmalig) -> Secret-Scope -> Worker-Gesundheit. Jede Entscheidung wird
auditiert (Parameter vorher redigiert). Freigaben werden außerhalb des Prompts technisch erzwungen."""
from __future__ import annotations

import hashlib
import json

# Ziel-Katalog aus der Referenzanalyse. registered=False heißt: es gibt (noch) keinen Executor - der Broker lehnt ab,
# statt etwas zu versprechen. Phase C schaltet einzelne Einträge frei (je Fähigkeit: Threat Model, Sandbox, Tests, Kill).
CATALOG = {
    # heute registriert (V16)
    'llm.worker':             {'registered': True, 'risk': 'reversible', 'approval': 'auto', 'sandbox': 'Arbeitsordner, keine Befehle',
                               'note': 'Claude-Worker schreibt nur im Auftrags-Arbeitsordner; Budget je Auftrag'},
    'web.read':               {'registered': True, 'risk': 'external_read', 'approval': 'conditional', 'sandbox': 'Claude WebSearch/WebFetch',
                               'note': 'nur bei Datenklasse public automatisch'},
    'sandbox.exec':           {'registered': True, 'risk': 'reversible', 'approval': 'auto', 'sandbox': 'bwrap, ohne Netz, Limits'},
    'sandbox.exec_networked': {'registered': True, 'risk': 'external_read', 'approval': 'conditional', 'sandbox': 'bwrap mit Netz',
                               'note': 'public automatisch, interne/private Daten nur nach Freigabe'},
    'pc.exec':                {'registered': True, 'risk': 'reversible', 'approval': 'auto', 'sandbox': 'Windows AppContainer, ohne Netz'},
    'improve.trial':          {'registered': True, 'risk': 'reversible', 'approval': 'auto', 'sandbox': 'Probelauf gegen unveränderte Tests',
                               'note': 'Einspielen selbst immer nur nach Ja'},
    # Ziel (Phase C), noch ohne Executor
    'filesystem.read': {'registered': False, 'risk': 'read', 'approval': 'auto'},
    'filesystem.write': {'registered': False, 'risk': 'reversible', 'approval': 'conditional'},
    'shell.readonly': {'registered': False, 'risk': 'read', 'approval': 'auto'},
    'shell.exec': {'registered': False, 'risk': 'privileged', 'approval': 'approval'},
    'git.status': {'registered': False, 'risk': 'read', 'approval': 'auto'},
    'git.commit': {'registered': False, 'risk': 'reversible', 'approval': 'auto'},
    'git.push': {'registered': False, 'risk': 'external_write', 'approval': 'conditional'},
    'github.read': {'registered': False, 'risk': 'external_read', 'approval': 'auto'},
    'github.issue.write': {'registered': False, 'risk': 'external_write', 'approval': 'approval'},
    'github.pr.write': {'registered': False, 'risk': 'external_write', 'approval': 'approval'},
    'browser.read': {'registered': False, 'risk': 'external_read', 'approval': 'conditional'},
    'browser.interact': {'registered': False, 'risk': 'external_write', 'approval': 'approval'},
    'browser.download': {'registered': False, 'risk': 'external_read', 'approval': 'conditional'},
    'computer.observe': {'registered': False, 'risk': 'read', 'approval': 'conditional'},
    'computer.input': {'registered': False, 'risk': 'privileged', 'approval': 'approval'},
    'mcp.call': {'registered': False, 'risk': 'external_write', 'approval': 'conditional'},
    'skill.run': {'registered': False, 'risk': 'reversible', 'approval': 'conditional'},
    'subagent.spawn': {'registered': False, 'risk': 'reversible', 'approval': 'conditional'},
    'schedule.create': {'registered': False, 'risk': 'reversible', 'approval': 'approval'},
    'schedule.modify': {'registered': False, 'risk': 'reversible', 'approval': 'approval'},
    'memory.read': {'registered': False, 'risk': 'read', 'approval': 'auto'},
    'memory.propose_write': {'registered': True, 'risk': 'reversible', 'approval': 'approval',
                             'note': 'Memory-Distiller: Kandidaten frei, Vault-Schreiben nur nach Freigabe'},
    'service.status': {'registered': False, 'risk': 'read', 'approval': 'auto'},
    'service.restart': {'registered': False, 'risk': 'privileged', 'approval': 'approval'},
    'secrets.use': {'registered': False, 'risk': 'privileged', 'approval': 'conditional', 'note': 'nur secret_ref, nie der Wert im Prompt'},
    'mail.send': {'registered': False, 'risk': 'external_write', 'approval': 'approval'},
    'payment': {'registered': False, 'risk': 'money', 'approval': 'approval'},
}
KILL_LEVELS = ('soft', 'exec', 'hard')


def kill_level(path) -> str | None:
    """KILL-Datei: Inhalt soft|exec|hard. Leere/alte KILL-Datei = exec (bisheriges Verhalten: nichts ausführen)."""
    try:
        if not path.exists():
            return None
        v = path.read_text(encoding='utf-8', errors='replace').strip().lower()
    except OSError:
        return 'exec'
    return v if v in KILL_LEVELS else 'exec'


def classify(kind: str, step_spec: dict, cap_info: dict | None, job_spec: dict) -> tuple[str, dict]:
    """Schritt -> (Broker-Fähigkeit, normalisierte Parameter)."""
    if kind == 'claude':
        web = step_spec.get('web') and job_spec.get('data_class') == 'public' and not job_spec.get('no_web')   # wie die Werkzeugvergabe
        cap = 'web.read' if web else 'llm.worker'
        return cap, {'outputs': sorted(step_spec.get('outputs') or [])[:20], 'model': step_spec.get('model', 'auto')}
    if kind == 'pc':
        return 'pc.exec', {'capability': step_spec.get('capability'), 'args': step_spec.get('args') or {}}
    if step_spec.get('capability') == 'improve.trial':
        return 'improve.trial', {'patch': step_spec.get('patch')}
    net = bool(cap_info and (cap_info.get('definition') or {}).get('network'))
    return ('sandbox.exec_networked' if net else 'sandbox.exec'), {'capability': step_spec.get('capability'),
                                                                     'args': step_spec.get('args') or {}}


def params_hash(job_id: str, revision: int, sid: str, cap: str, params: dict) -> str:
    raw = json.dumps([job_id, revision, sid, cap, params], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def decide(cap: str, *, kill: str | None, job_active: bool, revision_ok: bool, data_class: str, budget_ok: bool,
           approved: bool, secret_refs: list | None = None, worker_ok: bool = True) -> dict:
    c = CATALOG.get(cap)
    if kill in ('exec', 'hard'):
        return {'decision': 'deny', 'reason': f'Not-Aus Stufe {kill}: keine Ausführung'}
    if not job_active:
        return {'decision': 'deny', 'reason': 'Auftrag nicht aktiv'}
    if not revision_ok:
        return {'decision': 'deny', 'reason': 'veraltete Revision'}
    if not c or not c['registered']:
        return {'decision': 'deny', 'reason': f'Fähigkeit {cap} nicht registriert (kein Executor)'}
    if not budget_ok:
        return {'decision': 'deny', 'reason': 'Budget erschöpft'}
    if secret_refs and not set(secret_refs) <= set(c.get('secrets') or []):
        return {'decision': 'deny', 'reason': 'Secret außerhalb des erlaubten Scopes angefordert'}
    if not worker_ok:
        return {'decision': 'deny', 'reason': 'Worker nicht gesund/nicht getestet'}
    rule = c['approval']
    if rule == 'deny':
        return {'decision': 'deny', 'reason': 'Policy: verboten'}
    needs = rule == 'approval' or (rule == 'conditional' and data_class != 'public')
    if cap == 'web.read' and data_class != 'public':
        return {'decision': 'deny', 'reason': 'Webzugriff nur bei öffentlichen Daten'}
    if needs and not approved:
        return {'decision': 'approval', 'reason': f'{cap} bei Datenklasse {data_class} braucht Freigabe'}
    return {'decision': 'allow', 'reason': 'freigegeben' if needs else f'Policy {rule}'}
