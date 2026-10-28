import json, socket, sys, time
mode = sys.argv[1] if len(sys.argv) > 1 else 'gespraech'
q = sys.argv[2] if len(sys.argv) > 2 else 'Erzähle mir in zwei Sätzen etwas über Minecraft Modding.'
s = socket.socket(socket.AF_UNIX); s.connect('/run/ma-claude/bridge.sock')
t0 = time.time()
s.sendall(json.dumps({'prompt': q, 'dir': 'notizen', 'mode': mode, 'model': 'haiku'}).encode() + b'\n')
buf, first, txt, tools, init = b'', None, '', [], None
while True:
    b = s.recv(65536)
    if not b: break
    buf += b
    while b'\n' in buf:
        line, buf = buf.split(b'\n', 1)
        try: d = json.loads(line)
        except ValueError: continue
        if d.get('type') == 'system' and d.get('subtype') == 'init': init = d.get('tools')
        if d.get('type') == 'bridge_error': print('ERR', d); sys.exit(1)
        ev = d.get('event') or {}
        if d.get('type') == 'stream_event' and ev.get('type') == 'content_block_delta' and (ev.get('delta') or {}).get('type') == 'text_delta':
            if first is None: first = time.time() - t0
            txt += ev['delta']['text']
        if d.get('type') == 'assistant':
            tools += [c.get('name') for c in d['message'].get('content', []) if c.get('type') == 'tool_use']
print('mode=%s erstes_wort=%.1fs gesamt=%.1fs werkzeuge_verfuegbar=%s benutzt=%s' % (mode, first or -1, time.time() - t0, init, tools))
print(txt[:300])
