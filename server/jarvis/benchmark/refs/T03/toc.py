import argparse, re, sys
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
lines = open(a.src, encoding='utf-8').read().split('\n')
if '<!-- toc -->' not in lines:
    sys.exit(3)
fence, heads = False, []
for ln in lines:
    if ln.startswith('```'): fence = not fence
    m = None if fence else re.match(r'^(#{1,4}) (.+)$', ln)
    if m and m.group(2).strip() != 'Inhalt': heads.append((len(m.group(1)), m.group(2).strip()))
seen, toc = {}, []
for lvl, t in heads:
    an = re.sub(r'[^\w\- ]', '', t.lower()).replace(' ', '-')
    n = seen.get(an, 0); seen[an] = n + 1
    toc.append('  ' * (lvl - 1) + f'- [{t}](#{an if n == 0 else f"{an}-{n}"})')
out = []
for ln in lines: out += toc if ln == '<!-- toc -->' else [ln]
open(a.out, 'w', encoding='utf-8').write('\n'.join(out))
