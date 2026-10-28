"""VOICE-004: Qwen 8B (teilweise CPU, weil VRAM geteilt) gegen Qwen3 4B (passt ganz in die GPU): Zeit bis erstes Wort / erster
Satzteil / gesamt und die Antworten selbst (Qualität sichtbar). Neue Prompts je Lauf (kein KV-Cache-Vorteil). Direkt an Ollama."""
import json, re, time, urllib.request
SYS = ('Du bist JARVIS, der persönliche Assistent von Andre im MA-HOME. Sprich natürliches, freundliches Deutsch wie in einem echten Gespräch: '
       'höchstens drei kurze Sätze, kein Markdown, keine Listen, keine Emojis, keine Links. Bleib bei Fakten ehrlich: wenn du unsicher bist, sag es. '
       'Du hast keinen Zugriff auf Dateien, Notizen oder Aufträge und behauptest nie, etwas nachgesehen oder erledigt zu haben.')
QS = ['Wie spät ist es in Tokio, wenn es hier neun Uhr morgens ist?', 'Was ist ein Mod Loader bei Minecraft?',
      'Was kann ich heute Abend schnell kochen?', 'Erklär mir kurz den Unterschied zwischen RAM und Festplatte.']


def ask(model, q, salt):
    body = {'model': model, 'messages': [{'role': 'system', 'content': SYS + f' (Sitzung {salt})'}, {'role': 'user', 'content': q}],
            'stream': True, 'think': False, 'keep_alive': '15m', 'options': {'num_ctx': 4096, 'temperature': 0.6, 'num_predict': 220}}
    t0 = time.time(); first = clause = None; txt = ''
    r = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/chat', data=json.dumps(body).encode(),
                                                      headers={'Content-Type': 'application/json'}), timeout=120)
    for line in r:
        d = json.loads(line)
        p = (d.get('message') or {}).get('content') or ''
        if p:
            first = first or time.time() - t0
            txt += p
            if clause is None and len(txt) >= 28 and re.search(r'[.!?…,;:](\s|$)', txt[20:]):
                clause = time.time() - t0
        if d.get('done'):
            break
    return first, clause, time.time() - t0, ' '.join(txt.split())


for model in ('qwen3:4b', 'qwen3:8b'):
    ask(model, 'Hallo', 'warm')   # laden
    for i, q in enumerate(QS):
        f, c, tot, txt = ask(model, q, f'{model}-{i}-{time.time()}')
        print(f'{model:10s} erstes {f:4.2f}s satzteil {c or -1:4.2f}s gesamt {tot:4.1f}s | {txt[:150]}', flush=True)
