#!/usr/bin/env python3
"""V11.1 Mutationsprobe: python3 brain-runtime/scripts/mutate_v111.py PAKETORDNER"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
SRC = Path(sys.argv[1])
M = [
 ('provider_adapter.py', "if not c.get('cloud_enabled'):\n            return 'cloud disabled'", "if False:\n            return 'cloud disabled'", 'Cloud-Schalter ignoriert'),
 ('provider_adapter.py', "if not p or not p.get('enabled'):", "if not p:", 'Provider-enabled ignoriert'),
 ('provider_adapter.py', "if task_type not in p.get('task_types', []):", "if False:", 'Aufgabentyp ignoriert'),
 ('provider_adapter.py', "if provider not in allowed or data_class not in p.get('data_classes', []):", "if False:", 'Egress-Regel ignoriert'),
 ('provider_adapter.py', "now - 60) >= lim.get('rpm', 0)", "now - 60) >= 10**9", 'Rate-Limit ignoriert'),
 ('provider_adapter.py', ">= cfg.get('daily_call_budget', 0):", ">= 10**9:", 'Tagesbudget Aufrufe ignoriert'),
 ('provider_adapter.py', "        if b and b[0] > now:\n            return 'circuit open", "        if False:\n            return 'circuit open", 'Circuit-Breaker/Retry-After ignoriert'),
 ('provider_adapter.py', "if runner.redact(text) != text:\n        return 'secret'", "if False:\n        return 'secret'", 'Secrets nicht erkannt'),
 ('provider_adapter.py', "if declared == 'private' or PERSONAL.search(text) or", "if declared == 'private' or", 'Personendaten nicht erkannt'),
 ('provider_adapter.py', "if (u.scheme != 'https' and not loop) or u.hostname not in hosts:", "if False:", 'Host-Allowlist/https aus'),
 ('provider_adapter.py', "if os.name == 'posix' and path.stat().st_mode & 0o077:", "if False:", 'Provider-Config ohne 0600'),
 ('provider_adapter.py', "if cls == 'secret' or cls not in CLASSES:", "if cls not in CLASSES:", 'Egress für secret erlaubt'),
 ('provider_adapter.py', "sus = bool(INJECTION.search(text))", "sus = False", 'Injection nicht markiert'),
 ('provider_adapter.py', "if len(raw) > self.cfg.get('max_response_bytes', 200_000):", "if False:", 'Antwortgröße unbegrenzt'),
 ('provider_adapter.py', ", _NoRedirect())", ")", 'Redirect mit Schlüssel gefolgt'),
 ('provider_adapter.py', "content = runner.redact(prompt)[", "content = prompt[", 'Prompt ohne Schwärzung (äquivalent)'),
 ('route_policy.py', "if not self.helpers or self.helpers.eligible(prov, req['task_type'], req['data_class'], project) or not ok:", "if False:", 'Router-Helferwahl ungeprüft'),
 ('route_policy.py', "if n < self.min_samples:", "if False:", 'Vertrauen ohne Mindeststichprobe'),
 ('orders.py', "'helper_used<helper_budget AND cancelled=0'", "'1=1'", 'Helferbudget ignoriert'),
 ('executive.py', "(' SUSPICIOUS' if r['suspicious'] else '')", "''", 'Verdacht nicht vermerkt'),
 ('executive.py', "self.helpers.mark_call(r['call_id'], ok, why)", "self.helpers.mark_call(r['call_id'], True, why)", 'Helfer immer als korrekt gelernt'),
 ('executive.py', "if not ok:\n                    tried.append(f'{prov}: answer rejected ({why})'); continue", "if False:\n                    pass", 'P0-2 ungeprüfte Antwort schließt Schritt ab'),
 ('executive.py', "if not pre['ok']:\n                return", "if False:\n                return", 'Helfer trotz fehlgeschlagener Vorbedingung'),
 ('route_policy.py', "if self.mode == 'shadow' and router['target'].startswith('helper:'):", "if False:", 'P0-1 Schattenmodus ruft Helfer'),
 ('provider_adapter.py', "verified=CASE WHEN suspicious=1 THEN 0 ELSE ? END, error", "verified=?, error", 'Verdächtige Antwort zählt als Erfolg'),
 ('provider_adapter.py', "+ need_tokens > cfg.get('daily_token_budget', 0):", "+ need_tokens > 10**12:", 'P1-3 Token-Budget ignoriert'),
 ('provider_adapter.py', "+ need_tokens > cfg['global_daily_token_budget']:", "+ need_tokens > 10**12:", 'P1-3 globaler Deckel ignoriert'),
 ('provider_adapter.py', "c.execute('BEGIN IMMEDIATE')", "c.execute('BEGIN')", 'P1-3 Reservierung nicht atomar'),
 ('provider_adapter.py', "return -(-len(content) // 3) + 32 + max_tokens", "return 1", 'P1-3 keine Vorab-Reservierung'),
 ('provider_adapter.py', "for cid in bad:", "for cid in []:", 'Altfehler nicht korrigiert'),
 ('helper_verify.py', "if _norm(q) not in body:", "if False:", 'Erfundene Belege akzeptiert'),
 ('helper_verify.py', "if not text or not text.strip():\n        return False, 'empty answer'", "if False:\n        return False, 'empty answer'", 'Leere Antwort akzeptiert'),
 ('helper_verify.py', "if not any(w in cause for w in want):", "if False:", 'Falsche Ursache akzeptiert'),
 ('helper_verify.py', "return False, f'unknown verifier {kind!r}'", "return True, 'ok'", 'Unbekannter Prüfer akzeptiert'),
 ('canary.py', "if not can.get('enabled'):", "if False:", 'P1-4 Canary ohne Freigabe'),
 ('canary.py', "if classify(prompt, 'public') != 'public':", "if False:", 'P1-4 Canary sendet private Daten'),
 ('canary.py', "if len(out['results']) >= cap:", "if False:", 'P1-4 Canary ohne Obergrenze'),
 ('performance_intelligence.py', "if conds['cpu'] or conds['memory']:", "if True:", 'Prozess-Scan ohne Druck (Mehrlast)'),
 ('executive.py', "and spec.get('fallback_template') and self.autonomy and self.autonomy.get('enabled'):", "and spec.get('fallback_template'):", 'Claude-Fallback ohne Autonomie'),
 ('perf_autopilot.py', "if hashlib.sha256(raw).hexdigest() != pinned_sha256:", "if False:", 'Allowlist-Pin ignoriert'),
 ('perf_autopilot.py', "if name not in MEASURES:", "if False:", 'Fremde Maßnahmen erlaubt'),
 ('perf_autopilot.py', "(path.stat().st_mode & 0o022 or path.stat().st_uid != os.getuid())", "False", 'Allowlist-Rechte ignoriert'),
 ('perf_autopilot.py', "if not (self.autorun and m.get('auto')):", "if False:", 'Autorun ohne Freigabe'),
 ('perf_autopilot.py', "ok = gain >= min_gain and not regress", "ok = True", 'Kein Rollback'),
 ('perf_autopilot.py', "if last and now - (last[0] or 0) < self.cooldown:", "if False:", 'Kein Cooldown'),
 ('perf_autopilot.py', "if n_day >= self.max_day:", "if False:", 'Kein Tageslimit'),
 ('performance_intelligence.py', "if not act and st >= enter_n:", "if not act and st >= 1:", 'Keine Hysterese'),
 ('daemon.py', "self.ex.defer_remote = h['mode'] != 'normal' or", "self.ex.defer_remote =", 'Helfer trotz Schonmodus'),
]
TESTS = ['brain-runtime/tests/test_v11_perf.py', 'brain-runtime/tests/test_v11_providers.py',
         'brain-runtime/tests/test_v11_autopilot_chain.py', 'brain-runtime/tests/test_v111_regressions.py',
         'brain-runtime/tests/test_v111_jarvis.py']
caught = 0
for f, a, b, name in M:
    with tempfile.TemporaryDirectory() as t:
        dst = Path(t) / 'pkg'; shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns('__pycache__'))
        p = dst / 'brain-runtime' / f; s = p.read_text()
        if a not in s:
            print(f'{name}: PATTERN MISSING', flush=True); continue
        p.write_text(s.replace(a, b, 1))
        try:
            r = subprocess.run([sys.executable, '-m', 'unittest', *TESTS], cwd=dst, capture_output=True, text=True, timeout=900)
            hit = r.returncode != 0; last = (r.stderr.strip().splitlines() or ['?'])[-1]
        except subprocess.TimeoutExpired:
            hit, last = True, 'TIMEOUT'
        caught += hit
        print(f"{name}: {'erkannt' if hit else 'NICHT ERKANNT'} ({last})", flush=True)
print(f'{caught}/{len(M)} erkannt')
