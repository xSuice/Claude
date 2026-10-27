"""Waitress transport limit 128 KiB -> 2 MiB; Flask MAX_CONTENT_LENGTH (128 KiB) stays the per-route guard for every route
except /api/voice/stt (request.max_content_length = STT_BODY_LIMIT). Idempotent, backup *.bak-vor-sttlimit-20261027."""
import ast, shutil
from pathlib import Path
p = Path('/opt/ma-home/portal.py')
s = p.read_text(encoding='utf-8')
old = 'max_request_body_size=128*1024, '
new = 'max_request_body_size=2*1024*1024, '   # STT-LIMIT: Flask MAX_CONTENT_LENGTH bleibt 128 KiB je Route
if new in s:
    print('already patched')
else:
    assert s.count(old) == 1, 'anchor'
    assert "app.config['MAX_CONTENT_LENGTH'] = 128 * 1024" in s, 'flask guard missing'
    s2 = s.replace(old, new)
    ast.parse(s2)
    b = p.with_name(p.name + '.bak-vor-sttlimit-20261027')
    if not b.exists():
        shutil.copy2(p, b)
    p.write_text(s2, encoding='utf-8')
    print('patched')
