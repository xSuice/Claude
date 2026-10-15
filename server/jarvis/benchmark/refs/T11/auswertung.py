import argparse, json
from decimal import Decimal, ROUND_HALF_UP
from docx import Document
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--json', required=True); a.add_argument('--docx', required=True); a = a.parse_args()
cols = {'temperatur': [], 'feuchte': []}
for ln in open(a.src, encoding='utf-8').read().splitlines()[1:]:
    _, t, f = ln.split(';')
    if t: cols['temperatur'].append(Decimal(t))
    if f: cols['feuchte'].append(Decimal(f))
r = lambda x: Decimal(x).quantize(Decimal('0.01'), ROUND_HALF_UP)
st = {k: {'anzahl': len(v), 'min': float(r(min(v))), 'max': float(r(max(v))), 'mittel': float(r(sum(v) / len(v)))} for k, v in cols.items()}
json.dump(st, open(a.json, 'w'), indent=1)
d = Document(); d.add_heading('Messbericht', 1)
k = lambda x: f'{x:.2f}'.replace('.', ',')
for n, s in st.items(): d.add_paragraph(f'{n.capitalize()}: Anzahl {s["anzahl"]}, Minimum {k(s["min"])}, Maximum {k(s["max"])}, Mittelwert {k(s["mittel"])}')
d.save(a.docx)
