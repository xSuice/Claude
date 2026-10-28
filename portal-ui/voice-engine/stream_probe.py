"""Streamt die Portal-Route /api/voice/chat über den Testproxy und misst, wann die Stücke ankommen (prüft Puffern)."""
import json, time, http.client
c = http.client.HTTPConnection('127.0.0.1', 28766, timeout=60)
body = json.dumps({'messages': [{'role': 'user', 'content': 'Erzähl mir in drei Sätzen etwas über Katzen.'}]})
t0 = time.time()
c.request('POST', '/api/voice/chat', body=body, headers={'Content-Type': 'application/json'})
r = c.getresponse()
print('status', r.status, 'headers nach', round(time.time() - t0, 2), 's')
arr = []
while True:
    b = r.read1(4096)
    if not b:
        break
    arr.append((round(time.time() - t0, 2), len(b)))
print('Stücke:', len(arr), 'erstes', arr[:1], 'letztes', arr[-1:], 'Verteilung', [a[0] for a in arr[:: max(1, len(arr) // 10)]])
