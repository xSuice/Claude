import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
TZ = ZoneInfo('Europe/Berlin')
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a.add_argument('--anomalien', required=True); a = a.parse_args()
rows = set()
for ln in open(a.src, encoding='utf-8').read().splitlines()[1:]:
    if ln.strip():
        z, s = ln.split(';'); rows.add((z, float(s.replace(',', '.'))))
last, anom, first, lastd = None, [], {}, {}
for z, s in sorted(rows, key=lambda r: datetime.fromisoformat(r[0])):
    if last is not None and s < last: anom.append(z); continue
    last = s; d = datetime.fromisoformat(z).astimezone(TZ).date().isoformat(); first.setdefault(d, s); lastd[d] = s
days = sorted(lastd)
open(a.out, 'w', encoding='utf-8').write('datum;kwh\n' + ''.join(f'{d};{lastd[d] - (lastd[days[i - 1]] if i else first[d]):.3f}\n' for i, d in enumerate(days)))
open(a.anomalien, 'w', encoding='utf-8').write(''.join(x + '\n' for x in anom))
