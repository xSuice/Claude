import argparse, json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
d = json.load(open(a.src, encoding='utf-8')); n = len(d['abschnitte']) + 1
c = canvas.Canvas(a.out, pagesize=A4); W, H = A4
c.setFont('Helvetica-Bold', 28); c.drawString(60, H - 200, d['titel']); c.setFont('Helvetica', 14); c.drawString(60, H - 230, 'Kurzbericht'); c.showPage()
for i, s in enumerate(d['abschnitte'], start=2):
    c.setFont('Helvetica-Bold', 20); c.drawString(60, H - 80, s['ueberschrift']); c.setFont('Helvetica', 11)
    y = H - 120
    for ln in simpleSplit(s['text'], 'Helvetica', 11, W - 120): c.drawString(60, y, ln); y -= 15
    c.setFont('Helvetica', 9); c.drawString(60, 40, f'Seite {i} von {n}'); c.showPage()
c.save()
