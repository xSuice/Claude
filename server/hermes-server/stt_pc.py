#!/usr/bin/env python3
"""Hermes-STT-Command-Provider auf dem Server: stt_pc.py INPUT_AUDIO OUTPUT_TXT
Die Spracherkennung läuft lokal auf dem PC (Whisper); der Server schickt das Audio nur durch den eigenen SSH-Tunnel."""
import os
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get('MA_VOICE_URL', 'http://127.0.0.1:18790')
TOKEN_FILE = os.environ.get('MA_VOICE_TOKEN_FILE', str(Path.home() / '.config/ma-jarvis/voice-token'))
TYPES = {'.webm': 'audio/webm', '.ogg': 'audio/ogg', '.oga': 'audio/ogg', '.opus': 'audio/ogg', '.wav': 'audio/wav',
         '.m4a': 'audio/mp4', '.mp4': 'audio/mp4', '.mp3': 'audio/mpeg', '.aac': 'audio/aac'}


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    ctype = TYPES.get(src.suffix.lower())
    if not ctype:
        raise SystemExit('Audioformat nicht unterstützt: ' + src.suffix)
    token = Path(TOKEN_FILE).read_text(encoding='utf-8').strip()
    req = urllib.request.Request(URL + '/stt', data=src.read_bytes(), method='POST',
                                 headers={'Content-Type': ctype, 'X-Voice-Token': token})
    import json
    with urllib.request.urlopen(req, timeout=120) as r:
        text = str(json.load(r).get('text') or '').strip()
    if not text:
        raise SystemExit('No speech detected')
    dst.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
