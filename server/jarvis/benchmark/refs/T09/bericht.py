import argparse, json
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
d = json.load(open(a.src, encoding='utf-8'))
o = ['# Wortstatistik', '', f'Wörter gesamt: {d["woerter"]}', f'Verschiedene Wörter: {d["verschieden"]}', '', '| Rang | Wort | Anzahl |', '|---|---|---|']
o += [f'| {i} | {w} | {n} |' for i, (w, n) in enumerate(d['haeufigste'], start=1)]
open(a.out, 'w', encoding='utf-8').write('\n'.join(o) + '\n')
