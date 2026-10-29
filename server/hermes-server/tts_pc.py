#!/usr/bin/env python3
"""Hermes-TTS-Command-Provider auf dem Server: tts_pc.py INPUT_TXT OUTPUT_WAV
Die Stimme (Piper Thorsten emotional) läuft lokal auf dem PC; der Server schickt nur den Text durch den eigenen SSH-Tunnel."""
import json
import os
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get('MA_VOICE_URL', 'http://127.0.0.1:18790')
TOKEN_FILE = os.environ.get('MA_VOICE_TOKEN_FILE', str(Path.home() / '.config/ma-jarvis/voice-token'))


def main():
    text = Path(sys.argv[1]).read_text(encoding='utf-8').strip()[:1500]
    if not text:
        raise SystemExit('leerer Text')
    token = Path(TOKEN_FILE).read_text(encoding='utf-8').strip()
    req = urllib.request.Request(URL + '/tts', data=json.dumps({'text': text}).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'X-Voice-Token': token})
    with urllib.request.urlopen(req, timeout=120) as r:
        Path(sys.argv[2]).write_bytes(r.read())


if __name__ == '__main__':
    main()
