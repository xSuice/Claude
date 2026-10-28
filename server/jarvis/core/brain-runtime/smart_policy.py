"""Smart-Router-Policy (Router-Vertrag, 28.10.2026): JARVIS entscheidet deterministisch, ein Provider fuehrt nur aus.

Ablauf: harte Filter (nicht konfiguriert, Datenschutzklasse, Werkzeugbedarf, Wirkungen, Kontextlaenge, Provider-Gesundheit,
Budget/Quote) -> Kandidatenmenge -> gewichteter Score -> Alias + Begruendung + alle Teilwerte (nachvollziehbar).
Kein LLM entscheidet, ob es selbst ein teureres LLM braucht. Fehlende Messwerte werden NICHT erfunden: sie gehen mit
neutralem Wert und confidence='estimated' ein und werden so ausgewiesen.
Wird von evidence_router.EvidenceRouter.decide() aufgerufen (evidence_router bleibt alleinige Entscheidungsinstanz)."""
from __future__ import annotations

import hashlib

WEIGHTS = {'quality': 0.35, 'reliability': 0.20, 'privacy': 0.15, 'latency': 0.10, 'cost': 0.10, 'quota': 0.05, 'cache': 0.05}
DATA_RANK = {'public': 0, 'internal': 1, 'private': 2}
TRUST_PRIVACY = {'local': 1.0, 'trusted': 0.8, 'untrusted': 0.3}
RISKY_EFFECTS = ('privileged', 'money', 'delete', 'send', 'publish')
NEED = {'routine': 0.55, 'strategic': 0.80, 'critical': 0.90}

# Alias-Katalog: Workflows kennen nur Aliase, nie Provider-Modellnamen. 'model' None = nicht konfiguriert -> ausgeschlossen.
# quality/latency sind Startannahmen (confidence 'estimated'), bis Messwerte aus job_calls vorliegen.
DEFAULT_ALIASES = {
    'claude-opus':   {'provider': 'anthropic-plan', 'model': 'opus', 'executor': 'claude', 'trust': 'trusted', 'max_data': 'private',
                      'tools': True, 'context': 200_000, 'quality': 0.95, 'latency': 0.35, 'price_rel': 5},
    'claude-sonnet': {'provider': 'anthropic-plan', 'model': 'sonnet', 'executor': 'claude', 'trust': 'trusted', 'max_data': 'private',
                      'tools': True, 'context': 200_000, 'quality': 0.85, 'latency': 0.60, 'price_rel': 3},
    'claude-haiku':  {'provider': 'anthropic-plan', 'model': 'haiku', 'executor': 'claude', 'trust': 'trusted', 'max_data': 'private',
                      'tools': True, 'context': 200_000, 'quality': 0.65, 'latency': 0.90, 'price_rel': 1},
    'kimi-main':          {'provider': 'moonshot', 'model': None, 'executor': 'openai-compat', 'trust': 'trusted', 'max_data': 'internal',
                           'tools': False, 'context': 1_000_000, 'quality': 0.93, 'latency': 0.45, 'price_rel': 2},
    'kimi-interactive':   {'provider': 'moonshot', 'model': None, 'executor': 'openai-compat', 'trust': 'trusted', 'max_data': 'internal',
                           'tools': False, 'context': 1_000_000, 'quality': 0.85, 'latency': 0.80, 'price_rel': 2},
    'kimi-open-fallback': {'provider': 'moonshot', 'model': None, 'executor': 'openai-compat', 'trust': 'trusted', 'max_data': 'internal',
                           'tools': False, 'context': 1_000_000, 'quality': 0.80, 'latency': 0.60, 'price_rel': 1},
    'local-fast':         {'provider': 'pc-ollama', 'model': None, 'executor': 'ollama', 'trust': 'local', 'max_data': 'private',
                           'tools': False, 'context': 32_000, 'quality': 0.55, 'latency': 0.85, 'price_rel': 0},
    'bulk-cheap-untrusted': {'provider': 'nexum', 'model': None, 'executor': 'cloud', 'trust': 'untrusted', 'max_data': 'public',
                             'tools': True, 'context': 32_768, 'quality': 0.75, 'latency': 0.40, 'price_rel': 0.5},
    'fallback-diverse':   {'provider': 'openrouter', 'model': None, 'executor': 'openai-compat', 'trust': 'untrusted', 'max_data': 'public',
                           'tools': False, 'context': 128_000, 'quality': 0.80, 'latency': 0.55, 'price_rel': 2},
}


def catalog(cfg: dict | None, cloud_model: str | None = None) -> dict:
    """Katalog aus Defaults + jarvis.json router.aliases (nur bekannte Felder). Nexum gilt als konfiguriert, wenn der
    vorhandene Cloud-Fallback aktiv ist (dessen Modell)."""
    out = {k: dict(v) for k, v in DEFAULT_ALIASES.items()}
    if cloud_model:
        out['bulk-cheap-untrusted']['model'] = cloud_model
    for name, over in ((cfg or {}).get('aliases') or {}).items():
        if name in out and isinstance(over, dict):
            out[name].update({k: over[k] for k in ('model', 'quality', 'latency', 'max_data', 'context') if k in over})
    return out


def _quality_pred(q: float, need: float) -> float:
    """Eignung statt Rohqualität: unter Bedarf stark bestraft, Überqualität nur gering belohnt (sonst gewinnt immer das teuerste)."""
    if q >= need:
        return 0.85 + 0.15 * (q - need) / max(1e-6, 1 - need)
    return 0.85 * (q / need) ** 3


def decide(*, text: str, spec: dict, complexity: str, planning: bool, needs_tools: bool, aliases: dict,
           metrics: dict, quota: dict, prev_model: str | None = None) -> dict:
    """metrics[alias] = {'calls','ok','recent_fail_streak','avg_s','avg_usd'} aus job_calls (gemessen; Kontingent-
    Ablehnungen des Anbieters zählen NICHT als Modellfehler, sie gehen über quota ein);
    quota[provider] = {'blocked': bool, 'remaining': float|None, 'confidence': str}."""
    data = spec.get('data_class') or 'internal'
    effects = set(spec.get('effects') or [])
    need = max(NEED.get(complexity, 0.55), 0.80 if planning else 0.0)
    est_tokens = len(text) // 3 + 4000
    excluded, cands = {}, {}
    # einheitliche Kostenskala: gemessene Durchschnittskosten; ungemessene Aliase über die relative Preisklasse an die
    # gemessenen angebunden (als 'estimated' markiert) - nie gemessen gegen geschätzt auf verschiedenen Skalen
    units = [m['avg_usd'] / aliases[k]['price_rel'] for k, m in metrics.items()
             if k in aliases and m.get('avg_usd') and aliases[k].get('price_rel')]
    unit = sum(units) / len(units) if units else None
    def usd_of(name):
        m = metrics.get(name) or {}
        if m.get('avg_usd'):
            return m['avg_usd'], True
        return (unit * aliases[name].get('price_rel', 1), False) if unit is not None else (None, False)
    max_usd = max([u for u in (usd_of(n)[0] for n in aliases if aliases[n].get('model')) if u] or [0]) or None
    for name, a in aliases.items():
        why = None
        if not a.get('model'):
            why = 'nicht konfiguriert'
        elif DATA_RANK.get(data, 2) > DATA_RANK.get(a['max_data'], 0):
            why = f'Datenschutz: {data} nicht erlaubt für {a["trust"]}-Provider (max. {a["max_data"]})'
        elif needs_tools and not a['tools']:
            why = 'Werkzeuge/Dateien nötig, Provider ohne Werkzeugausführung'
        elif effects & set(RISKY_EFFECTS) and a['trust'] == 'untrusted':
            why = 'riskante Wirkung: kein ungeprüfter Vermittler vor Seiteneffekten'
        elif est_tokens > a['context']:
            why = f'Kontext {est_tokens} > {a["context"]}'
        elif (metrics.get(name) or {}).get('recent_fail_streak', 0) >= 3:
            why = 'Provider gestört: letzte 3 Aufrufe fehlgeschlagen (automatisch ausweichen)'
        elif (quota.get(a['provider']) or {}).get('blocked'):
            why = 'Budget/Kontingent erschöpft'
        if why:
            excluded[name] = why
            continue
        m = metrics.get(name) or {}
        est = []
        if m.get('calls', 0) >= 5:
            rel = m['ok'] / m['calls']
        else:
            rel = 0.9
            est.append('reliability')
        lat = (1 - min(1.0, m['avg_s'] / 90)) if m.get('calls', 0) >= 5 and m.get('avg_s') is not None else a['latency']
        if not (m.get('calls', 0) >= 5 and m.get('avg_s') is not None):
            est.append('latency')
        u, measured = usd_of(name)
        if u is not None and max_usd:
            cost = 1 - min(1.0, u / max_usd) * 0.9
        else:   # noch gar nichts gemessen: nur relative Preisklasse
            cost = 1 - 0.9 * a.get('price_rel', 1) / 5
        if not measured:
            est.append('cost')
        q = quota.get(a['provider']) or {}
        if q.get('remaining') is None:
            quo = 0.5
            est.append('quota')
        else:
            quo = max(0.0, min(1.0, q['remaining']))
        parts = {'quality': round(_quality_pred(a['quality'], need), 3), 'reliability': round(rel, 3),
                 'privacy': TRUST_PRIVACY[a['trust']], 'latency': round(lat, 3), 'cost': round(cost, 3), 'quota': round(quo, 3),
                 'cache': 1.0 if prev_model and prev_model == a['model'] else 0.5}
        cands[name] = {'score': round(sum(WEIGHTS[k] * v for k, v in parts.items()), 4), 'parts': parts, 'estimated': est}
    if not cands:
        return {'alias': None, 'model': None, 'executor': None, 'reason': 'kein zulässiger Provider (fail-closed)',
                'complexity': complexity, 'need': need, 'candidates': {}, 'excluded': excluded}
    best = max(cands, key=lambda k: (cands[k]['score'], -len(cands[k]['estimated'])))
    a = aliases[best]
    return {'alias': best, 'model': a['model'], 'executor': a['executor'], 'provider': a['provider'],
            'reason': f'{complexity}, Bedarf {need:.2f}, Datenklasse {data}: {best} Score {cands[best]["score"]}',
            'complexity': complexity, 'need': need, 'candidates': cands, 'excluded': excluded}


def violations(decision: dict, spec: dict, aliases: dict) -> list[str]:
    """Unabhängige Gegenprobe der harten Regeln auf eine getroffene Entscheidung (Shadow-Eval: muss leer sein)."""
    a = aliases.get(decision.get('alias') or '')
    if not a:
        return ['unbekannter Alias']
    v = []
    data = spec.get('data_class') or 'internal'
    if not a.get('model'):
        v.append('nicht konfigurierter Provider gewählt')
    if DATA_RANK.get(data, 2) > DATA_RANK.get(a['max_data'], 0):
        v.append(f'{data}-Daten an {a["trust"]}-Provider')
    if set(spec.get('effects') or []) & set(RISKY_EFFECTS) and a['trust'] == 'untrusted':
        v.append('riskante Wirkung über ungeprüften Vermittler')
    return v


def in_canary(job_id: str, pct: float) -> bool:
    """Deterministische Canary-Zuteilung je Auftrag (gleicher Auftrag -> immer gleiche Gruppe)."""
    if pct <= 0:
        return False
    return int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16) % 10000 < pct * 100
