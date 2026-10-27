import base64,urllib.request,urllib.error,os
user,pw=open(os.path.expanduser('~/.config/ma-jarvis/ntfy-notify.cred')).read().strip().split(':',1)
auth='Basic '+base64.b64encode((user+':'+pw).encode()).decode()
B='http://127.0.0.1:12586'
def call(method,path,data=None,a=True):
    h={'Authorization':auth} if a else {}
    r=urllib.request.Request(B+path,data=data,method=method,headers=h)
    try:
        with urllib.request.urlopen(r,timeout=10) as x:return x.status
    except urllib.error.HTTPError as e:return e.code
print('anonymous publish to andrew-jarvis   :',call('POST','/andrew-jarvis',b'x',a=False),'(expect 401/403)')
print('jarvis-notify publish other topic    :',call('POST','/other-topic',b'x'),'(expect 403)')
print('jarvis-notify publish andrew-secret  :',call('POST','/andrew-secret',b'x'),'(expect 403)')
print('jarvis-notify READ andrew-jarvis     :',call('GET','/andrew-jarvis/json?poll=1'),'(expect 403)')
print('jarvis-notify publish andrew-jarvis  :','(done via --test)')
