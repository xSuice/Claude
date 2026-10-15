"""Herkunftskennzeichnung (Jarvis / Claude / Jarvis + Claude), nur aus Nachweisen der Job-Daten.

Eine reine Funktion ohne eigene Datenhaltung: sie liest, was die Task-Engine ohnehin protokolliert (Schritte, Modellaufrufe in
job_calls, Ereignisse). Weiterleiten, Anzeigen oder Empfangen zählt nicht als Beitrag. Fehlt ein Nachweis oder widersprechen
sich die Daten, lautet das Ergebnis "Ausführung nicht verifiziert" statt einer geratenen Kennzeichnung.
"""
from __future__ import annotations

NOT_VERIFIED = 'Ausführung nicht verifiziert'
FINAL = {'done': 'abgeschlossen', 'partial': 'teilweise', 'failed': 'fehlgeschlagen', 'cancelled': 'fehlgeschlagen'}
OPEN = {'queued': 'wartet', 'planning': 'läuft', 'running': 'läuft', 'waiting_approval': 'wartet auf Freigabe',
        'waiting_pc': 'wartet auf den PC'}


def _out(label, status, jarvis, claude, ref, reason=''):
    contrib = {'Jarvis': f'Jarvis: {jarvis}', 'Claude': f'Claude: {claude}',
               'Jarvis + Claude': f'Jarvis + Claude: Jarvis – {jarvis}; Claude – {claude}'}.get(label)
    tail = f' · Status: {status}' + (f' · Nachweis: {ref}' if ref else '')
    line = f'{contrib}{tail}' if contrib else f'{NOT_VERIFIED}{tail}' + (f' · Grund: {reason}' if reason else '')
    return {'label': label, 'status': status, 'line': line, 'jarvis': jarvis, 'claude': claude, 'reason': reason, 'ref': ref}


def attribute_job(st: dict, events: list[dict] | None = None) -> dict:
    """st = TaskEngine.status(job). events = TaskEngine.events(job) (empfohlen: prüft die Aufrufe gegen das Ereignisprotokoll)."""
    ref = st.get('id', '')
    state = st.get('state', '')
    if state in OPEN:
        return _out(None, OPEN[state], '', '', ref, 'Auftrag noch nicht abgeschlossen')
    verdict = st.get('verdict') or state
    status = FINAL.get(verdict)
    if status is None:
        return _out(None, 'nicht verifiziert', '', '', ref, f'unbekannter Zustand {state!r}')
    steps = st.get('steps') or []
    calls = st.get('calls') or []
    ok_calls = [c for c in calls if c.get('ok')]
    done = {s['sid'] for s in steps if s.get('state') == 'done'}
    plan_ok = any(c.get('sid') == 'plan' for c in ok_calls)
    claude_steps = [c for c in ok_calls if c.get('sid') in done]
    local = [s for s in steps if s.get('kind') in ('local', 'pc') and s.get('state') == 'done']
    template = str(st.get('plan_source') or '').startswith('template:')
    helper = int(st.get('helper_calls') or 0)
    accepted = 'Ergebnisdateien bestanden die unabhängige Abnahme' in str(st.get('summary') or '') and verdict in ('done', 'partial', 'failed')

    # Konsistenz: jeder gezählte Claude-Aufruf braucht ein Ereignis, sonst keine Behauptung.
    if events is not None:
        n_ev = sum(1 for e in events if e.get('kind') == 'claude_done')
        if n_ev != len(calls):
            return _out(None, 'nicht verifiziert', '', '', ref, f'{len(calls)} Modellaufrufe, aber {n_ev} Ereignisse')
    if int(st.get('claude_calls') or 0) != len(calls):
        return _out(None, 'nicht verifiziert', '', '', ref, f'Zähler claude_calls={st.get("claude_calls")} ≠ {len(calls)} Aufrufe')
    if verdict == 'done' and not (claude_steps or local or template):
        return _out(None, 'nicht verifiziert', '', '', ref, 'abgeschlossen ohne belegten ausgeführten Schritt')

    claude_bits = []
    if claude_steps:
        models = sorted({c['model'] for c in claude_steps if c.get('model')})
        claude_bits.append(f'{len(claude_steps)} Inhaltsschritt(e) erzeugt ({", ".join(models) or "Modell unbekannt"})')
    if plan_ok:
        claude_bits.append('Plan erstellt')
    jarvis_bits = []
    if local:
        jarvis_bits.append(f'{len(local)} lokale(r) Werkzeugschritt(e) ausgeführt')
    if template:
        jarvis_bits.append('Plan aus bewährter Vorlage')
    if helper:
        jarvis_bits.append(f'{helper} Helferaufruf(e)')
    if accepted:
        jarvis_bits.append('unabhängige Abnahme der Ergebnisdateien')
    jarvis_content = bool(local or template or helper)
    claude_contrib = bool(claude_steps or plan_ok)
    unproven = status if verdict != 'done' else 'nicht verifiziert'   # ein Misserfolg bleibt als solcher sichtbar, "abgeschlossen" nur mit Beleg
    if not claude_contrib and not jarvis_content:
        return _out(None, unproven, '', '', ref, 'weder Claude- noch JARVIS-Inhaltsbeitrag belegt')
    if claude_contrib and not jarvis_bits:
        return _out(None, unproven, '', '', ref, 'nur Weiterleitung an Claude belegt, kein eigener JARVIS-Beitrag (keine Abnahme)')
    jarvis, claude = '; '.join(jarvis_bits), '; '.join(claude_bits)
    label = 'Jarvis + Claude' if claude_contrib else 'Jarvis'
    return _out(label, status, jarvis, claude, ref)


def attribute_direct_claude(rec: dict) -> dict:
    """Claude ohne JARVIS (z. B. Claude-Code-Chat). rec: {'id', 'model', 'ok', 'tokens_new', 'jarvis_job': None}.
    Zählt nur mit Nachweis (Bridge-/Usage-Eintrag mit Modell und Verbrauch); eine zu einem JARVIS-Auftrag gehörende Antwort nicht."""
    ref = str(rec.get('id') or '')
    if rec.get('jarvis_job'):
        return _out(None, 'nicht verifiziert', '', '', ref, 'gehört zu einem JARVIS-Auftrag, bitte attribute_job verwenden')
    if not ref or not rec.get('model') or rec.get('tokens_new') is None:
        return _out(None, 'nicht verifiziert', '', '', ref, 'kein Bridge-/Usage-Nachweis (Modell oder Verbrauch fehlt)')
    status = 'abgeschlossen' if rec.get('ok') else 'fehlgeschlagen'
    return _out('Claude', status, '', f'Antwort erzeugt ({rec["model"]}, {rec["tokens_new"]} neue Token)', ref)
