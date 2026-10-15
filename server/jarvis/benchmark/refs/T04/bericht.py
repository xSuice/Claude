import argparse
from decimal import Decimal, ROUND_HALF_UP
from docx import Document
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
q = lambda d: str(d.quantize(Decimal('0.01'), ROUND_HALF_UP)).replace('.', ',')
d = Document(); d.add_heading('Umsatzbericht', 1)
rows, tot, qty = [], Decimal(0), 0
for ln in open(a.src, encoding='utf-8').read().splitlines()[1:]:
    n, m, p = ln.split(';'); p = Decimal(p.replace(',', '.')); s = p * int(m); tot += s; qty += int(m); rows.append([n, m, q(p), q(s)])
t = d.add_table(rows=1, cols=4)
for c, h in zip(t.rows[0].cells, ['Artikel', 'Menge', 'Einzelpreis (EUR)', 'Summe (EUR)']): c.text = h
for r in rows + [['Gesamt', str(qty), '', q(tot)]]:
    for c, v in zip(t.add_row().cells, r): c.text = v
d.save(a.out)
