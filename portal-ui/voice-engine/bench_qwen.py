import json, os, time, urllib.request
SYS = 'Du bist JARVIS, der persönliche Assistent von Andre. Sprich natürliches, freundliches Deutsch wie im Gespräch, höchstens drei kurze Sätze, kein Markdown, keine Listen, keine Emojis.'
QS = ['Erzähle mir in zwei Sätzen etwas über Minecraft Modding.', 'Und welcher Mod Loader ist für Anfänger besser?', 'Wie kann ich heute Abend gut abschalten?']


def stream(url, body, headers):
    t0 = time.time(); first = None; txt = ''
    r = urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers), timeout=120)
    for line in r:
        line = line.decode('utf-8', 'replace').strip()
        if not line: continue
        if line.startswith('data:'):
            line = line[5:].strip()
            if line == '[DONE]': break
        try: d = json.loads(line)
        except ValueError: continue
        piece = (d.get('message') or {}).get('content') or ''
        if not piece and d.get('choices'):
            piece = (d['choices'][0].get('delta') or {}).get('content') or ''
        if piece:
            if first is None: first = time.time() - t0
            txt += piece
    return first, time.time() - t0, txt


def run(name, fn):
    hist = [{'role': 'system', 'content': SYS}]
    for q in QS:
        hist.append({'role': 'user', 'content': q})
        try:
            f, tot, txt = fn(hist)
        except Exception as e:
            print(name, 'FEHLER', type(e).__name__, str(e)[:120]); return
        hist.append({'role': 'assistant', 'content': txt})
        print('%-28s erstes_wort=%5.1fs gesamt=%5.1fs | %s' % (name, f or -1, tot, ' '.join(txt.split())[:170]), flush=True)


for m in ('qwen3:4b-tools-nothink', 'qwen3:8b'):
    run('lokal ' + m, lambda h, m=m: stream('http://127.0.0.1:11434/api/chat', {'model': m, 'messages': h, 'stream': True, 'think': False, 'keep_alive': '10m', 'options': {'num_ctx': 4096}}, {'Content-Type': 'application/json'}))

key = None
for line in open(os.path.expanduser('~/AppData/Local/hermes/profiles/kimi-supervisor/config.yaml'), encoding='utf-8'):
    if 'key_env' in line and key is None:
        env = line.split(':', 1)[1].strip().strip('"\'')
        key = os.environ.get(env)
        if not key:
            try:
                for l in open(os.path.expanduser('~/AppData/Local/hermes/profiles/kimi-supervisor/.env'), encoding='utf-8'):
                    if l.startswith(env + '='): key = l.split('=', 1)[1].strip().strip('"\'')
            except OSError: pass
if key:
    run('cloud qwen-3.8-omni-flash', lambda h: stream('https://dialagram.me/router/v1/chat/completions', {'model': 'qwen-3.8-omni-flash', 'messages': h, 'stream': True, 'max_tokens': 300},
                                               {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}))
else:
    print('cloud: kein Schlüssel gefunden')
