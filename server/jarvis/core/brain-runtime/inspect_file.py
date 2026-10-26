"""V16 file inspector. Runs INSIDE the sandbox (copied into the job workspace), never in the engine
process: image, office and PDF parsers process untrusted files. Prints one JSON object per file.
Usage: python3 -I inspect_file.py <relpath>..."""
import json
import os
import sys
import zipfile


def inspect(path):
    info = {'path': path, 'bytes': os.path.getsize(path)}
    low = path.lower()
    try:
        if low.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff')):
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = 80_000_000
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                info.update(kind='image', width=im.width, height=im.height, mode=im.mode,
                            colors=len(im.convert('RGB').getcolors(maxcolors=4096) or []) if im.width * im.height <= 4_000_000 else None)
        elif low.endswith('.docx'):
            import docx
            d = docx.Document(path)
            text = '\n'.join(p.text for p in d.paragraphs)
            info.update(kind='docx', paragraphs=len(d.paragraphs), words=len(text.split()), tables=len(d.tables),
                        headings=sum(1 for p in d.paragraphs if (p.style.name or '').lower().startswith('heading')))
        elif low.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True)
            info.update(kind='xlsx', sheets=wb.sheetnames, rows={ws.title: ws.max_row for ws in wb.worksheets})
            wb.close()
        elif low.endswith('.pptx'):
            with zipfile.ZipFile(path) as z:
                info.update(kind='pptx', slides=sum(1 for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')))
        elif low.endswith('.pdf'):
            import pypdf
            r = pypdf.PdfReader(path)
            text = ''.join((r.pages[i].extract_text() or '') for i in range(min(len(r.pages), 30)))
            info.update(kind='pdf', pages=len(r.pages), words=len(text.split()))
        elif low.endswith(('.zip', '.jar')):
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
                info.update(kind='zip', entries=len(z.namelist()), names=z.namelist()[:200], corrupt=bad)
        elif low.endswith(('.wav',)):
            import wave
            with wave.open(path) as w:
                info.update(kind='wav', seconds=round(w.getnframes() / max(w.getframerate(), 1), 3), channels=w.getnchannels())
        else:
            info.update(kind='other')
        info['ok'] = True
    except Exception as e:  # noqa: BLE001 - report, never crash
        info.update(ok=False, error=f'{type(e).__name__}: {str(e)[:200]}')
    return info


if __name__ == '__main__':
    args = sys.argv[1:]
    out = None
    if len(args) >= 2 and args[0] == '--out':
        out, args = args[1], args[2:]
    lines = [json.dumps(inspect(p), ensure_ascii=False) for p in args]
    if out:
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
    else:
        print('\n'.join(lines))
