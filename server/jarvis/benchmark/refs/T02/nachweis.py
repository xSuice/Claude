import argparse, json
from datetime import date
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
es = sorted(json.load(open(a.src, encoding='utf-8'))['eintraege'], key=lambda e: (e['datum'], e['nr']))
weeks = {}
for e in es:
    y, w, _ = date.fromisoformat(e['datum']).isocalendar(); weeks.setdefault((y, w), []).append(e)
h = lambda x: f'{x:.1f}'.replace('.', ',')
out = ['# Ausbildungsnachweis', '']
for (y, w), rows in sorted(weeks.items()):
    out += [f'## KW {w:02d}/{y}', '', '| Datum | Bereich | Tätigkeit | Stunden |', '|---|---|---|---|']
    out += [f"| {date.fromisoformat(e['datum']).strftime('%d.%m.%Y')} | {e['bereich']} | {e['taetigkeit']} | {h(e['stunden'])} |" for e in rows]
    out += ['', f"**Summe: {h(sum(e['stunden'] for e in rows))} Stunden**", '']
open(a.out, 'w', encoding='utf-8').write('\n'.join(out))
