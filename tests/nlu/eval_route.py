"""Misst classify_route (echtes Qwen über Ollama, gleiche Funktion wie der Dienst) auf route_holdout.json.
Wichtig ist vor allem: 'ausfuehren' darf nie verfehlt werden (sonst bekäme eine Rolle ohne Werkzeuge einen Auftrag)."""
import collections, json, os, pathlib, sys, time
V = pathlib.Path(os.environ['LOCALAPPDATA']) / 'hermes/voice'
sys.path.insert(0, str(V))
os.environ.setdefault('MA_VOICE_TOKEN_FILE', str(V / 'voice-token.txt'))
import ma_voice_service as S
items = json.loads((pathlib.Path(__file__).parent / 'route_holdout.json').read_text(encoding='utf-8'))
S.classify_route('Aufwärmen')
ok, lat, per, miss = 0, [], collections.defaultdict(lambda: [0, 0]), []
for want, text in items:
    t0 = time.perf_counter(); got = S.classify_route(text); lat.append(time.perf_counter() - t0)
    per[want][1] += 1
    if got == want:
        ok += 1; per[want][0] += 1
    else:
        miss.append((want, got, text))
lat.sort()
print('%s: %d/%d = %d %% | median %.2f s, p90 %.2f s' % (S.CHAT_MODEL, ok, len(items), round(100 * ok / len(items)), lat[len(lat) // 2], lat[int(len(lat) * .9)]))
print('  ' + '  '.join('%s %d/%d' % (k, v[0], v[1]) for k, v in per.items()))
aus_miss = [m for m in miss if m[0] == 'ausfuehren']
fals_aus = [m for m in miss if m[1] == 'ausfuehren']
print('  Aufträge verfehlt (kritisch): %d | Fragen fälschlich als Auftrag (harmlos, gehen an Claude): %d' % (len(aus_miss), len(fals_aus)))
for w, g, t in miss:
    print('  MISS %-15s -> %-15s | %s' % (w, g, t))
