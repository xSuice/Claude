"""Wortstatistik: zählt Wörter einer Textdatei und schreibt die häufigsten als JSON.
Aufruf: python3 wortstatistik.py <eingabe.txt|.md> <ausgabe.json> [anzahl]"""
import collections
import json
import re
import sys


def main(src, dst, top=10):
    with open(src, encoding='utf-8', errors='replace') as fh:
        words = re.findall(r'[^\W\d_]{2,}', fh.read().casefold())
    freq = collections.Counter(words)
    with open(dst, 'w', encoding='utf-8') as fh:
        json.dump({'woerter': len(words), 'verschieden': len(freq), 'haeufigste': freq.most_common(int(top))}, fh, ensure_ascii=False)


if __name__ == '__main__':
    main(*sys.argv[1:4])
