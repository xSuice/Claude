"""Register the health blueprint in portal.py (marker HEALTH-BP). Idempotent, backup *.bak-vor-health-20261027."""
import ast, shutil
from pathlib import Path
p = Path('/opt/ma-home/portal.py')
s = p.read_text(encoding='utf-8')
if 'HEALTH-BP' in s:
    print('already patched'); raise SystemExit
anchor = 'app.register_blueprint(telemetry_bp)'
assert s.count(anchor) == 1, 'anchor'
add = anchor + "\nfrom jarvis_health import health_bp  # HEALTH-BP: Dienstestatus aus Uptime Kuma\napp.register_blueprint(health_bp)"
s2 = s.replace(anchor, add)
ast.parse(s2)
b = p.with_name(p.name + '.bak-vor-health-20261027')
if not b.exists():
    shutil.copy2(p, b)
p.write_text(s2, encoding='utf-8')
print('patched')
