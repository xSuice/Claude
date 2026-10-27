import py_compile,shutil,sys,re
for P in ('/opt/ma-home/chat_bus_backend.py','/home/andrew/chat_bus_backend.py'):
    s=open(P).read()
    if "'kimi-supervisor'" in s:
        print(P,'already present');continue
    old="'hermes', 'jarvis-architecture',"
    assert s.count(old)==1,P
    shutil.copy(P,P+'.bak-vor-kimiroster-20261027')
    open(P,'w').write(s.replace(old,"'hermes', 'kimi-supervisor', 'jarvis-architecture',"))
    py_compile.compile(P,doraise=True)
    print(P,'patched')
