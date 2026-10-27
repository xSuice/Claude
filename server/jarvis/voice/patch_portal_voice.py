import ast, shutil, sys
p = '/opt/ma-home/portal.py'
s = open(p, encoding='utf-8').read()
marker = '# VOICE-BP'
if marker in s:
    print('already present'); sys.exit(0)
anchor = 'app.register_blueprint(telemetry_bp)\n'
assert s.count(anchor) == 1, 'anchor count != 1'
shutil.copy2(p, p + '.bak-vor-voice-20261027')
s = s.replace(anchor, anchor + 'from jarvis_voice import voice_bp  ' + marker + ' (admin, proxy to local PC voice service)\napp.register_blueprint(voice_bp)\n', 1)
ast.parse(s)
open(p + '.new', 'w', encoding='utf-8').write(s)
shutil.copymode(p, p + '.new')
import os; os.replace(p + '.new', p)
print('patched')
