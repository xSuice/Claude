import py_compile,shutil,sys
P='/opt/ma-home/portal.py'
s=open(P).read()
if 'jarvis_telemetry' in s:
    print('already present');sys.exit(0)
a="app.register_blueprint(jarvis_bp)\n"
assert s.count(a)==1
shutil.copy(P,P+'.bak-vor-telemetry-20261027')
s=s.replace(a,a+"from jarvis_telemetry import telemetry_bp  # TELEMETRY-BP (read-only, admin)\napp.register_blueprint(telemetry_bp)\n")
open(P,'w').write(s)
py_compile.compile(P,doraise=True)
print('patched')
