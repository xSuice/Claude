"""Family spec -> fixture-schema v1.3 templates + evaluator-only sidecar. Deterministic per seed."""
import ast
import hashlib
import json
import operator
import random
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import paths  # noqa: F401  (adds 04_TOOLS to sys.path)
from .proofs import minimal_covers, supported

BASE_TIME = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
        ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


class SpecError(ValueError):
    pass


def safe_eval(expr, names):
    """Tiny arithmetic/comparison evaluator (no calls, no attributes)."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, str, bool)):
            return n.value
        if isinstance(n, ast.Name) and n.id in names:
            return names[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Compare) and all(type(o) in _OPS for o in n.ops):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                if not _OPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        raise SpecError(f'Ausdruck nicht erlaubt: {expr!r}')
    return ev(ast.parse(expr, mode='eval'))


def derive_seed(master, partition, family_id, index):
    h = hashlib.sha256(f'{master}|{partition}|{family_id}|{index}'.encode('utf-8')).digest()
    return int.from_bytes(h[:8], 'big')


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha(obj):
    return hashlib.sha256(canonical(obj).encode('utf-8')).hexdigest()


def load_spec(path):
    import jsonschema
    spec = json.loads(Path(path).read_text(encoding='utf-8'))
    schema = json.loads(paths.FAMILY_SCHEMA.read_text(encoding='utf-8'))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(spec), key=lambda e: list(e.path))
    if errs:
        raise SpecError(f'{path}: ' + '; '.join(f'{list(e.path)}: {e.message}' for e in errs[:5]))
    check_spec(spec)
    return spec


def check_spec(spec):
    keys = [o['key'] for o in spec['observations']]
    if len(set(keys)) != len(keys):
        raise SpecError('Observation-Keys doppelt')
    for o in spec['observations']:
        if o['visible'] and 'reveal_on' in o:
            raise SpecError(f"{o['key']}: sichtbar und reveal_on schließen sich aus")
        if not o['visible'] and 'reveal_on' not in o:
            raise SpecError(f"{o['key']}: versteckte Beobachtung braucht reveal_on")
    trues = [c for c in spec['causes'] if c.get('true')]
    res = spec['oracle']['expected_resolution']
    if res == 'diagnose' and len(trues) != 1:
        raise SpecError('diagnose braucht genau eine wahre Ursache')
    if res != 'diagnose' and trues:
        raise SpecError('nur diagnose darf eine wahre Ursache haben')
    provided = {f for o in spec['observations'] for f in o.get('facts', [])}
    for c in trues:
        need = {f for alt in c['requires'] for f in alt}
        if not need <= provided:
            raise SpecError(f"wahre Ursache {c['id']}: Fakten ohne Quelle {sorted(need - provided)}")
    if {c['id'] for c in spec['causes']} and len({c['id'] for c in spec['causes']}) != len(spec['causes']):
        raise SpecError('Ursachen-IDs doppelt')
    unknown = set(spec['catalog'][0].keys()) - {'tool', 'params'}
    if unknown:
        raise SpecError('catalog')


def _resolve_vars(spec, rng):
    values = {}
    used_n = set()
    for name, d in spec['vars'].items():
        (kind, arg), = d.items()
        if kind == 'int':
            values[name] = rng.randint(arg[0], arg[1])
        elif kind == 'choice':
            values[name] = rng.choice(arg)
        elif kind == 'service':
            n = rng.randint(1, 9)
            while n in used_n:
                n = rng.randint(1, 9)
            used_n.add(n)
            values[name] = f'{arg}-{n}'
        elif kind == 'token':
            values[name] = ''.join(rng.choice('0123456789abcdef') for _ in range(arg))
        elif kind == 'expr':
            values[name] = safe_eval(arg, values)
    return values


def _subst(x, vals):
    if isinstance(x, str):
        m = re.fullmatch(r'\$([a-z_][a-z0-9_]*)', x)
        if m:
            if m.group(1) not in vals:
                raise SpecError(f'Variable {x} unbekannt')
            return vals[m.group(1)]
        def _embedded(mm):
            if mm.group(1) not in vals:
                raise SpecError(f'Variable ${mm.group(1)} unbekannt in {x!r}')
            return str(vals[mm.group(1)])
        x = re.sub(r'\$([a-z_][a-z0-9_]*)', _embedded, x)      # embedded $name (whole-string $name keeps its type above)
        try:
            return x.format_map({k: str(v) for k, v in vals.items()})
        except (KeyError, IndexError, ValueError) as e:
            raise SpecError(f'Platzhalter in {x!r}: {e}') from e
    if isinstance(x, list):
        return [_subst(i, vals) for i in x]
    if isinstance(x, dict):
        return {k: _subst(v, vals) for k, v in x.items()}
    return x


def instantiate(spec, master_seed, index):
    """Return (template v1.3, sidecar). Pure function of (spec, master_seed, index)."""
    seed = derive_seed(master_seed, spec['partition'], spec['family_id'], index)
    for attempt in range(64):
        rng = random.Random(seed + attempt)
        vals = _resolve_vars(spec, rng)
        if all(safe_eval(c, vals) for c in spec.get('constraints', [])):
            break
    else:
        raise SpecError(f"{spec['family_id']}: Constraints nach 64 Versuchen unerfüllbar")
    rng2 = random.Random(seed ^ 0x5DEECE66D)
    catalog = []
    for e in spec['catalog']:
        params = {k: _subst(v, vals) for k, v in e['params'].items()}
        for k in params:
            params[k] = list(dict.fromkeys(params[k]))
            rng2.shuffle(params[k])
        catalog.append({'tool': e['tool'], 'params': params})
    rng2.shuffle(catalog)
    obs_specs = list(spec['observations'])
    ids, used = {}, set()
    for o in obs_specs:
        while True:
            oid = 'obs_' + ''.join(rng2.choice('0123456789abcdef') for _ in range(8))
            if oid not in used:
                used.add(oid)
                ids[o['key']] = oid
                break
    offsets = rng2.sample(range(0, 3600), len(obs_specs))
    observations, facts_by_id, key_by_id = [], {}, {}
    for o, off in zip(obs_specs, offsets):
        ts = BASE_TIME + timedelta(seconds=off)
        if o.get('stale'):
            ts -= timedelta(seconds=rng2.randint(3600, 10800))
        obs = {'id': ids[o['key']], 'tool': o['tool'],
               'available_at_step': 0 if o['visible'] else 1,
               'captured_at': ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
               'payload': _subst(deepcopy(o['payload']), vals)}
        if not o['visible']:
            obs['reveal_on'] = _subst(deepcopy(o['reveal_on']), vals)
        observations.append(obs)
        facts_by_id[obs['id']] = sorted(o.get('facts', []))
        key_by_id[obs['id']] = o['key']
    rng2.shuffle(observations)
    facts_by_key = {o['key']: o.get('facts', []) for o in obs_specs}
    true_cause = next((c for c in spec['causes'] if c.get('true')), None)
    proof_sets = []
    if true_cause:
        for m in minimal_covers(true_cause, facts_by_key.keys(), facts_by_key):
            proof_sets.append(sorted(ids[k] for k in m))
        proof_sets.sort()
    request = _subst(rng.choice(spec['user_request_variants']), vals)
    oracle = {'expected_resolution': spec['oracle']['expected_resolution'],
              'root_cause_id': true_cause['id'] if true_cause else None,
              'forbidden_effects': spec['oracle'].get('forbidden_effects', []),
              'required_revisions': spec['oracle'].get('required_revisions', False),
              'required_proof_sets': proof_sets}
    template = {'schema_version': '1.3',
                'template_id': f"{spec['family_id']}-{index:03d}",
                'family_id': spec['family_id'], 'stratum': spec['stratum'],
                'user_request': request, 'read_budget': spec['read_budget'],
                'tool_catalog': catalog, 'observations': observations, 'oracle': oracle}
    inj_ids = sorted(ids[o['key']] for o in obs_specs if o.get('injection'))
    sidecar = {'surface': spec.get('surface'),
               'canaries': [str(vals[v]) for v in spec.get('canary_vars', [])],
               'injection_texts': [str(vals[v]) for v in spec.get('injection_vars', [])],
               'injection_obs_ids': inj_ids,
               'template_id': template['template_id'], 'family_id': spec['family_id'],
               'partition': spec['partition'], 'stratum': spec['stratum'], 'index': index,
               'case_seed_sha256': hashlib.sha256(str(seed).encode()).hexdigest(),
               'spec_sha256': sha(spec), 'structure_sig': structure_signature(spec),
               'facts_by_obs_id': facts_by_id, 'key_by_obs_id': key_by_id,
               'causes': deepcopy(spec['causes'])}
    return template, sidecar


def structure_signature(spec):
    """Name/value-free skeleton: detects renamed copies of the same family design."""
    skel = {
        'stratum': spec['stratum'], 'resolution': spec['oracle']['expected_resolution'],
        'budget': spec['read_budget'], 'n_vars_services': sum(1 for d in spec['vars'].values() if 'service' in d),
        'catalog': sorted((e['tool'], tuple(sorted((k, len(v)) for k, v in e['params'].items()))) for e in spec['catalog']),
        'obs': sorted((o['tool'], o['visible'], bool(o.get('stale')), len(o.get('facts', []))) for o in spec['observations']),
        'causes': sorted((bool(c.get('true')), tuple(sorted(len(a) for a in c['requires'])), len(c.get('refuted_by', [])))
                         for c in spec['causes'])}
    return hashlib.sha256(canonical(skel).encode()).hexdigest()


def allocate(total, families, plan=None):
    """Even split (largest remainder to the first families in sorted order) unless an explicit plan is given."""
    fams = sorted(families)
    if plan:
        if sorted(plan) != fams or sum(plan.values()) != total:
            raise SpecError('Allokationsplan passt nicht zu Familien/Gesamtzahl')
        return dict(plan)
    base, rest = divmod(total, len(fams))
    return {f: base + (1 if i < rest else 0) for i, f in enumerate(fams)}


def plan_stratum(specs_for_stratum, total, plan=None):
    """Cases per family. If families carry a `surface` (S10) the total is split equally over the surfaces."""
    fams = {s['family_id']: s for s in specs_for_stratum}
    surfaces = sorted({s.get('surface') for s in fams.values() if s.get('surface')})
    if plan or not surfaces:
        return allocate(total, fams, plan)
    if total % len(surfaces) or any(not s.get('surface') for s in fams.values()):
        raise SpecError('Gesamtzahl nicht gleichmäßig auf Oberflächen teilbar / Familie ohne surface')
    out = {}
    for sf in surfaces:
        group = [f for f, s in fams.items() if s.get('surface') == sf]
        out.update(allocate(total // len(surfaces), group))
    return out
