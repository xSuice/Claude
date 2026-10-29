"""Rollenprofile zurück auf Nexum. Kimi NUR für kimi-supervisor (Monatskontingent schonen); Rollen ohne Kimi-Ausweich
(bei Nexum-Ausfall übernimmt im Helfer Claude). Idempotent."""
import subprocess
from pathlib import Path

H = str(Path.home() / '.local/bin/hermes')
ROOT = Path.home() / '.hermes/profiles'
names = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p.name.startswith('jarvis-') or p.name == 'kimi-supervisor') and p.name != 'jarvis-server')


def setv(n, k, v):
    r = subprocess.run([H, '-p', n, 'config', 'set', k, v], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (n, k)


for n in names:
    if n == 'kimi-supervisor':
        for k, v in [('model.provider', 'kimi'), ('model.default', 'kimi-for-coding'), ('agent.reasoning_effort', 'medium'),
                     ('fallback_providers', '[]')]:
            setv(n, k, v)
    else:
        for k, v in [('model.provider', 'nexum'), ('model.default', 'qwen-3.8-omni-flash'), ('agent.reasoning_effort', 'low'),
                     ('fallback_providers', '[{provider: nexum, model: qwen-3.7-max-thinking}]'),
                     ('delegation.provider', 'nexum'), ('delegation.model', 'qwen-3.8-omni-flash')]:
            setv(n, k, v)
    print(n, 'ok', flush=True)
print('COUNT', len(names))
