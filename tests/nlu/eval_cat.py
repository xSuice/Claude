"""Zusatzauftrag §2: misst den ECHTEN /intent-Dienst je Verständnis-Kategorie (holdout4.json).
Feld 3: none = kein Auftrag läuft, run = Auftrag läuft, zuletzt = zuletzt bearbeiteter Auftrag als Kontext.
'multi' (mehrere Anweisungen) kann das heutige Schema nicht ausdrücken -> wird als Lücke gezählt, Ausgabe wird protokolliert."""
import collections, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import importlib.util
spec = importlib.util.spec_from_file_location('ev', pathlib.Path(__file__).parent / 'eval_service.py')
src = (pathlib.Path(__file__).parent / 'eval_service.py').read_text(encoding='utf-8').split('\nfor name in sys.argv')[0]
ns = {'__file__': str(pathlib.Path(__file__).parent / 'eval_service.py')}; exec(compile(src, 'eval_service', 'exec'), ns)
intent = ns['intent']
RUN = 'Build des Crimson-Zone-Plugins mit Java 21'
items = json.loads((pathlib.Path(__file__).parent / sys.argv[1]).read_text(encoding='utf-8'))
cat = collections.defaultdict(lambda: [0, 0]); rows = []
for want, text, ctx, c in items:
    run = None if ctx == 'none' else RUN if ctx == 'run' else 'zuletzt: ' + RUN + ' (DONE)'
    d, s = intent(text, run)
    got = d.get('intent')
    ok = got == want
    cat[c][1] += 1; cat[c][0] += ok
    rows.append({'cat': c, 'want': want, 'got': got, 'ok': ok, 'text': text, 'ctx': ctx, 's': round(s, 2)})
tot = sum(v[0] for k, v in cat.items() if k != 'mehrfach'), sum(v[1] for k, v in cat.items() if k != 'mehrfach')
print('OHNE mehrfach: %d/%d = %d %%' % (tot[0], tot[1], round(100 * tot[0] / tot[1])))
for k, v in sorted(cat.items()):
    print('  %-20s %d/%d' % (k, v[0], v[1]))
for r in rows:
    if not r['ok']:
        print('  MISS [%s] %-8s -> %-8s | %s (%s)' % (r['cat'], r['want'], r['got'], r['text'], r['ctx']))
json.dump(rows, open(pathlib.Path(__file__).parent / ('preds_' + sys.argv[1]), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
