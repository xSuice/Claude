"""Sprachstrecke zerlegt messen (PC-Dienst :18790): STT-Dauer, LLM bis erstes Wort / erster Satz, TTS erster Satz.
Liest das Voice-Token aus der Datei, gibt es nie aus."""
import json, os, re, statistics, time, urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:18790'
TOK = (Path(os.environ['LOCALAPPDATA']) / 'hermes/voice/voice-token.txt').read_text().strip()
H = {'X-Voice-Token': TOK}
WAV = Path(__file__).resolve().parent / 'stt-bench'


def post(path, data, ctype, timeout=120):
    req = urllib.request.Request(BASE + path, data=data, headers={**H, 'Content-Type': ctype})
    return urllib.request.urlopen(req, timeout=timeout)


def stt(p):
    t0 = time.time()
    r = json.loads(post('/stt', p.read_bytes(), 'audio/wav').read())
    return time.time() - t0, r.get('text', '')


def chat(q):
    body = json.dumps({'messages': [{'role': 'user', 'content': q}]}).encode()
    t0 = time.time(); first = sent = None; txt = ''
    with post('/chat', body, 'application/json') as r:
        for line in r:
            line = line.decode('utf-8', 'replace').strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            piece = d.get('t') or ''
            if piece:
                first = first or time.time() - t0
                txt += piece
                if sent is None and re.search(r'[.!?…]\s|[,;:]\s.{0,0}', txt) and len(txt) >= 24:
                    sent = time.time() - t0
            if d.get('done'):
                break
    return first, sent, time.time() - t0, txt


def tts(text):
    t0 = time.time()
    data = post('/tts', json.dumps({'text': text}).encode(), 'application/json').read()
    return time.time() - t0, len(data)


if __name__ == '__main__':
    import sys
    stt_t = []
    for p in sorted(WAV.glob('s*.wav'))[:6]:
        d, txt = stt(p)
        stt_t.append(d)
        print(f'STT {p.name}: {d:.2f}s  {txt[:60]!r}', flush=True)
    post('/warm', b'{}', 'application/json').read()
    llm = []
    for q in ('Wie spät ist es ungefähr in Tokio, wenn es hier neun Uhr morgens ist?', 'Erzähl mir kurz, was ein Mod Loader ist.',
              'Was kann ich heute Abend kochen?'):
        f, s, tot, txt = chat(q)
        llm.append((f, s))
        print(f'LLM erstes Wort {f:.2f}s, erster Satzteil {s or -1:.2f}s, gesamt {tot:.2f}s | {" ".join(txt.split())[:90]}', flush=True)
    tt = []
    for t in ('Klar, das mache ich.', 'In Tokio ist es dann ungefähr vier Uhr nachmittags.'):
        d, n = tts(t)
        tt.append(d)
        print(f'TTS {len(t)} Zeichen: {d:.2f}s ({n} Bytes)', flush=True)
    print(json.dumps({'stt_median': round(statistics.median(stt_t), 2), 'llm_first_word_median': round(statistics.median(x[0] for x in llm), 2),
                      'llm_first_clause_median': round(statistics.median((x[1] or x[0]) for x in llm), 2),
                      'tts_short_median': round(statistics.median(tt), 2)}))
