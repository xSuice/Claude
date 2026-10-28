"""VOICE-004 Messung: Whisper base mit Prompt - Varianten fuer Latenz (beam, threads, vad, GPU wenn moeglich). Gleiche 8 Saetze wie stt_bench."""
import os, pathlib, re, sys, time
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
ROOT = pathlib.Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'voice'
OUT = pathlib.Path(__file__).with_name('stt-bench')
SENT = ['Erzähle mir in drei Sätzen etwas über Minecraft Modding.', 'Brich den Auftrag ab.', 'Neuer Auftrag: Fasse die Serverlogs von heute zusammen.',
        'Wie weit ist mein Auftrag?', 'Was macht Jarvis Router gerade?', 'Welche Dienste sind ausgefallen?', 'Öffne das Command Center.',
        'Erkläre mir den Unterschied zwischen Fabric und Forge.']
PROMPT = 'Jarvis, Auftrag, Aufträge, Minecraft, Modding, Fabric, Forge, Serverlogs, Command Center, Router, Signal, Portal, Uptime Kuma.'
norm = lambda s: re.sub(r'[^a-zäöüß ]', '', s.lower()).split()
score = lambda ref, hyp: sum(w in set(norm(hyp)) for w in norm(ref)) / len(norm(ref))
from faster_whisper import WhisperModel
files = [(s, OUT / ('s%d.wav' % i)) for i, s in enumerate(SENT)]
variants = [('cpu', 'int8', 2, 3, True), ('cpu', 'int8', 2, 1, True), ('cpu', 'int8', 4, 1, True), ('cpu', 'int8', 4, 1, False), ('cpu', 'int8', 4, 3, True)]
if 'gpu' in sys.argv:
    variants = [('cuda', 'int8_float16', 0, 1, True), ('cuda', 'int8_float16', 0, 3, True)]
for dev, ct, th, beam, vad in variants:
    try:
        kw = dict(device=dev, compute_type=ct, num_workers=1, download_root=str(ROOT / 'models/whisper'))
        if th:
            kw['cpu_threads'] = th
        m = WhisperModel('base', **kw)
        m.transcribe(str(files[0][1]), language='de', beam_size=beam)   # Aufwaermen
        tot, sc = 0, 0
        for s, p in files:
            t0 = time.perf_counter()
            seg, _ = m.transcribe(str(p), language='de', beam_size=beam, vad_filter=vad, initial_prompt=PROMPT, hotwords='Jarvis')
            txt = ' '.join(x.text.strip() for x in seg).strip()
            tot += time.perf_counter() - t0
            sc += score(s, txt)
        print(f'{dev}/{ct} threads={th} beam={beam} vad={vad}: Treffer {sc / len(files):.3f}, {tot / len(files):.2f} s/Satz', flush=True)
    except Exception as e:
        print(f'{dev}/{ct} beam={beam}: FEHLER {type(e).__name__}: {str(e)[:160]}', flush=True)
