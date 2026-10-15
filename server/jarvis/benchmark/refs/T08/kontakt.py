import argparse, sys
from pathlib import Path
from PIL import Image
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a.add_argument('--thumbs', required=True); a = a.parse_args()
pics = sorted(Path(a.src).glob('*.png'))
if not pics: sys.exit(4)
Path(a.thumbs).mkdir(parents=True, exist_ok=True)
rows = -(-len(pics) // 3); sheet = Image.new('RGB', (640, rows * 200 + (rows + 1) * 10), (255, 255, 255))
for i, p in enumerate(pics):
    im = Image.open(p).convert('RGB'); w, h = im.size; t = im.resize((200, max(1, round(h * 200 / w))))
    t.save(Path(a.thumbs) / p.name); sheet.paste(t, (10 + (i % 3) * 210, 10 + (i // 3) * 210))
sheet.save(a.out)
