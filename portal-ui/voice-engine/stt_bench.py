"""VOICE-005 Messung: Whisper base vs small, mit/ohne Fachwort-Prompt, auf Piper-Saetzen (16 kHz wie im Portal). Gibt WER-artige Trefferquote und Zeit aus."""
import json, os, pathlib, re, sys, time, urllib.request, wave, io
import numpy as np
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
ROOT = pathlib.Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'voice'
T = (ROOT / 'voice-token.txt').read_text().strip()
OUT = pathlib.Path(__file__).with_name('stt-bench'); OUT.mkdir(exist_ok=True)
SENT = ['Erzähle mir in drei Sätzen etwas über Minecraft Modding.', 'Brich den Auftrag ab.', 'Neuer Auftrag: Fasse die Serverlogs von heute zusammen.',
        'Wie weit ist mein Auftrag?', 'Was macht Jarvis Router gerade?', 'Welche Dienste sind ausgefallen?', 'Öffne das Command Center.',
        'Erkläre mir den Unterschied zwischen Fabric und Forge.']
PROMPT = 'Jarvis, Auftrag, Aufträge, Minecraft, Modding, Fabric, Forge, Serverlogs, Command Center, Router, Signal, Portal, Uptime Kuma.'


def tts16(text, path):
    if path.exists():
        return
    r = urllib.request.Request('http://127.0.0.1:18790/tts', data=json.dumps({'text': text}).encode(), headers={'Content-Type': 'application/json', 'X-Voice-Token': T})
    raw = urllib.request.urlopen(r, timeout=90).read()
    with wave.open(io.BytesIO(raw)) as w:
        sr, ch, frames = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    x = np.frombuffer(frames, '<i2').astype(np.float32)
    if ch == 2:
        x = x.reshape(-1, 2).mean(1)
    n = int(len(x) * 16000 / sr)
    y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype('<i2')   # wie Portal: 16 kHz mono
    with wave.open(str(path), 'wb') as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000); o.writeframes(y.tobytes())


norm = lambda s: re.sub(r'[^a-zäöüß ]', '', s.lower()).split()


def score(ref, hyp):
    r, h = norm(ref), set(norm(hyp))
    return sum(w in h for w in r) / len(r)


files = []
for i, s in enumerate(SENT):
    p = OUT / ('s%d.wav' % i); tts16(s, p); files.append((s, p))
from faster_whisper import WhisperModel
res = {}
for size in sys.argv[1:] or ['base', 'small']:
    m = WhisperModel(size, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1, download_root=str(ROOT / 'models/whisper'))
    for label, kw in (('ohne', {'hotwords': 'Jarvis'}), ('prompt', {'initial_prompt': PROMPT, 'hotwords': 'Jarvis'})):
        tot, sc, ex = 0, 0, []
        for s, p in files:
            t0 = time.perf_counter()
            seg, _ = m.transcribe(str(p), language='de', beam_size=3, vad_filter=True, **kw)
            txt = ' '.join(x.text.strip() for x in seg).strip()
            tot += time.perf_counter() - t0; sc += score(s, txt); ex.append(txt)
        res[size + '/' + label] = {'treffer': round(sc / len(files), 3), 's_pro_satz': round(tot / len(files), 2), 'beispiele': ex[:3]}
        print(size, label, res[size + '/' + label]['treffer'], res[size + '/' + label]['s_pro_satz'], ex[:3], flush=True)
json.dump(res, open(OUT / 'result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
