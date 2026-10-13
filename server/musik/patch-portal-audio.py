#!/usr/bin/python3
"""Fuegt /api/audio in /opt/ma-home/portal.py ein (idempotent, mit Sicherung und Pruefung). Als root ausfuehren.
Die Route liefert Audiodateien aus der Bibliothek zum Abspielen: richtiger Inhaltstyp, inline, mit Range-Unterstuetzung
(Vor-/Zurueckspulen, iPhone verlangt das). Gleiche Pfadpruefung wie /api/file (user_fd), nur Audio-Endungen."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-AUDIO ---'
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
ROUTE = f'''
{MARK}
AUDIO_TYPES = {{'.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.ogg': 'audio/ogg', '.oga': 'audio/ogg', '.opus': 'audio/ogg',
               '.flac': 'audio/flac', '.wav': 'audio/wav', '.webm': 'audio/webm'}}


@app.get('/api/audio')
def audio_get():
    """Audiodatei zum Abspielen (inline, Range). Nur bekannte Audio-Endungen."""
    path = request.args.get('path', '')
    mime = AUDIO_TYPES.get(Path(path).suffix.lower())
    if not mime:
        abort(415, 'Kein Audioformat')
    fd = user_fd(path)
    try:
        size = os.fstat(fd).st_size
        start, end, status = 0, size - 1, 200
        m = re.fullmatch(r'bytes=(\\d*)-(\\d*)', request.headers.get('Range', '').strip())
        if m and (m.group(1) or m.group(2)) and size:
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(size - int(m.group(2)), 0)
            if start > end or start >= size:
                os.close(fd)
                return Response(status=416, headers={{'Content-Range': 'bytes */%d' % size}})
            status = 206
    except Exception:
        os.close(fd)
        raise

    def chunks():
        try:
            pos = start
            while pos <= end:
                block = os.pread(fd, min(262144, end - pos + 1), pos)
                if not block:
                    break
                pos += len(block)
                yield block
        finally:
            os.close(fd)

    headers = {{'Accept-Ranges': 'bytes', 'Content-Length': str(max(end - start + 1, 0)), 'Cache-Control': 'private, max-age=3600'}}
    if status == 206:
        headers['Content-Range'] = 'bytes %d-%d/%d' % (start, end, size)
    return Response(stream_with_context(chunks()), status=status, mimetype=mime, headers=headers)
'''
cut = src.rfind("\nif __name__")
new = src[:cut] + ROUTE + src[cut:] if cut >= 0 else src + ROUTE
open(P, 'w', encoding='utf-8').write(new)
try:
    py_compile.compile(P, doraise=True)
except py_compile.PyCompileError as exc:
    shutil.copy2(backup, P)
    sys.exit(f'Fehler, Sicherung wiederhergestellt: {exc}')
print(f'Eingebaut. Sicherung: {backup}')
