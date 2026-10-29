#!/usr/bin/env python3
"""MA-HOME Chat-Weiche: beantwortet einen Portal-Chat-Auftrag über eine Hermes-Fachrolle (Mention-Receiver /api/bot/ask)
und gibt die Antwort im Claude-stream-json-Format aus - Abbrechen, Zeitlimit, Anzeige und Zählung der Brücke bleiben gleich.
Scheitert die Rolle (PC aus, Zeitlimit, Fehler), übernimmt im SELBEN Auftrag Claude mit den ursprünglichen Argumenten.

Aufruf (von der Brücke): ma-route-ask.py <profil> <anzeigename>; Text auf stdin.
Umgebung: MA_ROUTE_CLAUDE_ARGS (JSON-Liste, Rückfall), MA_ROUTE_CTX (letzter Austausch, nur Kontext)."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

RECEIVER = os.environ.get('MA_ROUTE_RECEIVER', 'http://127.0.0.1:8484')
TOKEN_FILE = os.environ.get('MA_ROUTE_TOKEN_FILE', '/home/andrew/.config/ma-jarvis/route-ask-token')
TIMEOUT = float(os.environ.get('MA_ROUTE_TIMEOUT', '200'))


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def text(t):
    emit({'type': 'stream_event', 'event': {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': t}}})


def ask(target, prompt, ctx):
    with open(TOKEN_FILE, encoding='utf-8') as f:
        tok = f.read().strip()
    req = urllib.request.Request(RECEIVER + '/api/bot/ask', method='POST',
                                 data=json.dumps({'target': target, 'message': prompt, 'context': ctx}).encode(),
                                 headers={'Content-Type': 'application/json', 'X-Ask-Token': tok})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def fallback(prompt, why, label):
    args = json.loads(os.environ.get('MA_ROUTE_CLAUDE_ARGS') or '[]')
    text('_(%s nicht verfügbar: %s – Claude übernimmt.)_\n\n' % (label, why))
    if not args:
        emit({'type': 'result', 'is_error': True, 'result': 'Fachrolle nicht verfügbar und kein Rückfall eingerichtet.'})
        return 1
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
    p.stdin.write(prompt.encode()); p.stdin.close()
    return p.wait()


def main():
    target, label = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    prompt = sys.stdin.read()
    ctx = os.environ.get('MA_ROUTE_CTX', '')[:2000]
    # sichtbar im Chat wie ein Werkzeugschritt: wer gerade gefragt wird
    emit({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Weiterleitung', 'input': {'command': label}}]}})
    try:
        d = ask(target, prompt, ctx)
    except urllib.error.HTTPError as e:
        return fallback(prompt, {504: 'Zeitlimit', 503: 'belegt', 401: 'Schlüssel', 403: 'Rolle nicht erlaubt'}.get(e.code, 'Fehler %d' % e.code), label)
    except (OSError, ValueError) as e:
        return fallback(prompt, 'nicht erreichbar' if isinstance(e, OSError) else 'ungültige Antwort', label)
    answer = str(d.get('answer') or '').strip()
    if not answer:
        return fallback(prompt, 'leere Antwort', label)
    text(answer)
    emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': answer, 'total_cost_usd': 0,
          'usage': {'input_tokens': 0, 'output_tokens': 0}, 'ma_route': {'target': target, 's': d.get('s')}})
    return 0


if __name__ == '__main__':
    sys.exit(main())
