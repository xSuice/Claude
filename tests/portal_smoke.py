#!/usr/bin/env python3
"""Browser-Rauchtest der Portal-Oberflaeche in Handy-Groesse (Playwright/Chromium). Ohne echtes Backend: alle /api/-Aufrufe werden mit
Platzhalter-Antworten beantwortet, die Dateien kommen aus portal-ui/web. Prueft: keine JavaScript-Fehler, Startseite, Claude-Tab
(Senden, Live-Antwort, Werkzeugzeile, Token-Anzeige, Anhang, Aufgaben-Panel), Dateien-Suche, Terminal-Tab, kein Querscrollen.
Einrichtung (ohne Root):  python3 -m venv ~/.ma-browsertest && ~/.ma-browsertest/bin/pip install playwright && ~/.ma-browsertest/bin/playwright install chromium
Aufruf:  ~/.ma-browsertest/bin/python tests/portal_smoke.py        Exit-Code 0 = alles bestanden."""
import json
import mimetypes
import os
import sys

from playwright.sync_api import sync_playwright

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'portal-ui', 'web')
BASE = 'http://localhost:8123'
NDJSON = '\n'.join(json.dumps(x) for x in [
    {'type': 'bridge_model', 'model': 'haiku'}, {'type': 'bridge_job', 'id': 'job123'},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hallo '}}},
    {'type': 'assistant', 'message': {'usage': {'input_tokens': 1200, 'cache_read_input_tokens': 3000}, 'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'df -h'}}]}},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Welt\n\n```\ndf -h\n```\n\n```html\n<b>Vorschau-Test</b>\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |'}}},
    {'type': 'result', 'result': 'Hallo Welt', 'usage': {'input_tokens': 1200, 'cache_read_input_tokens': 3000, 'output_tokens': 40}, 'total_cost_usd': 0.01, 'duration_ms': 8200},
    {'type': 'bridge_end', 'code': 0}]) + '\n'
DENY = '\n'.join(json.dumps(x) for x in [
    {'type': 'bridge_model', 'model': 'haiku'}, {'type': 'bridge_job', 'id': 'job123'},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Ich darf hier nicht schreiben.'}}},
    {'type': 'result', 'result': 'Ich darf hier nicht schreiben.', 'permission_denials': [{'tool_name': 'Write', 'tool_input': {'file_path': '/home/andrew/MA-Server/CHANGELOG.md'}}]},
    {'type': 'bridge_end', 'code': 0}]) + '\n'
OKESK = '\n'.join(json.dumps(x) for x in [
    {'type': 'bridge_model', 'model': 'haiku'}, {'type': 'bridge_job', 'id': 'job123'},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Erledigt-ESK'}}},
    {'type': 'result', 'result': 'Erledigt-ESK'}, {'type': 'bridge_end', 'code': 0}]) + '\n'
ESC = {'on': False}
TERM = '\n'.join(json.dumps(x) for x in [{'type': 'out', 't': 'hallo-terminal\n'}, {'type': 'end', 'code': 0}]) + '\n'
# Verbindungsabbruch: erste Antwort endet ohne bridge_end, danach muss sich das Portal per attach ab Position 3 wieder anhaengen
PART = '\n'.join(json.dumps(x) for x in [
    {'type': 'bridge_model', 'model': 'haiku'}, {'type': 'bridge_job', 'id': 'job123'},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Teil1 '}}}]) + '\n'
REST = '\n'.join(json.dumps(x) for x in [
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Teil2'}}},
    {'type': 'result', 'result': 'Teil1 Teil2'}, {'type': 'bridge_end', 'code': 0}]) + '\n'
CALLS = []
SCHED_SET = []
NOTE_WRITES = []
BOOKMARKS = []
NOTES = {'Plan.md': '# Plan\nSiehe [[Fahrschule]] und #planung\n\n![[bild.png]]\n\n## Teil A\n\n![[Fahrschule]]\n\n## Teil B\n\n> [!warning] Achtung\n> Text\n\n```\n#define X\n```\n', '10 Leben/Fahrschule.md': '# Fahrschule\nZurueck zu [[Plan]]\n', '_Claude-Memory/Index.md': '# Index\n'}
JOBS = []          # laufende Auftraege, die die Platzhalter-Bruecke meldet
FEEDBACK = []
TERM_CALLS = []
JV = {'state': 'waiting_approval'}
JV_CALLS = []


def api(route, request):
    path = request.url[len(BASE):]
    body = request.post_data or ''
    j = (lambda o, s=200: route.fulfill(status=s, content_type='application/json', body=json.dumps(o)))
    if path.startswith('/api/me'):
        return j({'user': 'andrew', 'admin': True, 'domain': BASE, 'modules': {}})
    if path.startswith('/api/items/'):
        return j({'items': []})
    if path.startswith('/api/jarvis'):
        d = json.loads(body or '{}'); c = d.get('cmd'); JV_CALLS.append(d)
        job = {'id': 'j20261014-abc123', 'state': JV['state'], 'request': 'Teste Freigabe', 'summary': '', 'effects': [], 'created': 1790000000, 'claude_calls': 1, 'tokens_new': 2000,
               'steps': [{'sid': 's1', 'title': 'Schreiben', 'kind': 'claude', 'state': 'waiting' if JV['state'] == 'waiting_approval' else 'done', 'capability': None, 'detail': ''}]}
        if c == 'usage':
            return j({'ok': True, 'data': {'ledger': {'claude': {'calls_24h': 5, 'tokens_24h': 53000, 'limits': {'calls_per_day': 40, 'tokens_per_day': 1500000}}, 'plan_block': None}}})
        if c == 'list':
            return j({'ok': True, 'data': {'jobs': [job]}})
        if c == 'status':
            return j({'ok': True, 'data': job})
        if c == 'events':
            return j({'ok': True, 'data': {'events': [{'id': 1, 'ts': 1790000000, 'kind': 'submitted', 'text': 'Datenklasse internal'}]}})
        if c == 'approve':
            JV['state'] = 'done'
            return j({'ok': True, 'data': {'ok': True}})
        if c == 'result':
            return j({'ok': True, 'data': {'files': ['BERICHT.md'], 'state': 'done'}})
        if c == 'submit':
            return j({'ok': True, 'data': {'job_id': 'j20261014-abc123', 'state': 'queued'}})
        if c == 'caps':
            return j({'ok': True, 'data': {'caps': [{'name': 'python.run', 'status': 'tested', 'host': 'server', 'title': 'x'}]}})
        if c == 'learned':
            return j({'ok': True, 'data': {'templates': [], 'lessons': []}})
        return j({'ok': True, 'data': {}})
    if path.startswith('/api/claude/op'):
        op = json.loads(body or '{}').get('op')
        if op == 'suggest':
            vollt = 'Terminal' in str(json.loads(body).get('prompt')) and 'ESKALATION' not in str(json.loads(body).get('prompt'))
            return j({'ok': True, 'mode': 'voll' if vollt else 'lesen', 'dir': 'maserver' if vollt else 'notizen', 'confirm': vollt})
        if op == 'sched_set':
            SCHED_SET.append(json.loads(json.loads(body)['data']))
            return j({'ok': True, 'tasks': [dict(SCHED_SET[-1], id='abcd1234', enabled=True, last='')]})
        if op == 'note':
            d = json.loads(json.loads(body)['data'])
            act, np_ = d.get('act'), d.get('path', '')
            if act == 'index':
                return j({'ok': True, 'items': [{'p': k, 'm': 1790000000, 's': len(v)} for k, v in sorted(NOTES.items())], 'protected': ['_Claude-Memory'], 'att': ['Anhang/bild.png'], 'bookmarks': list(BOOKMARKS)})
            if act == 'read':
                return j({'ok': True, 'path': np_, 'content': NOTES.get(np_, ''), 'etag': 'e1', 'readonly': np_.startswith('_Claude-Memory'), 'backlinks': ['10 Leben/Fahrschule.md'] if np_ == 'Plan.md' else [], 'outgoing': ['10 Leben/Fahrschule.md'] if np_ == 'Plan.md' else []})
            if act == 'write':
                NOTE_WRITES.append(d)
                NOTES[np_] = d['content']
                return j({'ok': True, 'etag': 'e2'})
            if act == 'bookmark':
                BOOKMARKS.append(np_) if np_ not in BOOKMARKS else BOOKMARKS.remove(np_)
                return j({'ok': True, 'bookmarks': list(BOOKMARKS)})
            if act == 'daily':
                return j({'ok': True, 'path': '10 Leben/Tagesnotizen/2026-10-12.md'})
            if act == 'tags':
                return j({'ok': True, 'tags': {'planung': ['Plan.md']}})
            if act == 'create':
                NOTES[np_] = '# neu\n'
                return j({'ok': True, 'path': np_})
            return j({'ok': True})
        if op == 'lern_feedback':
            FEEDBACK.append(json.loads(json.loads(body)['data']))
            return j({'ok': True})
        out = {'jobs': {'jobs': JOBS}, 'usage': {'ok': True, 'today': {'chat': {'jobs': 2, 'in': 1000, 'out': 50}}, 'limits': {'chat': 300, 'council': 25, 'geplant': 40}}, 'sessions': {'sessions': [{'id': 'x', 'title': 'Alter Chat', 'where': 'notizen', 'time': 1, 'dir': 'notizen'}]},
               'sched_list': {'ok': True, 'tasks': []}, 'search': {'ok': True, 'hits': [{'path': 'vault-notizen/a/Notiz.md', 'line': 3, 'text': 'Treffer Text'}]},
               'upload': {'ok': True, 'done': True, 'uid': 'abc123abc123', 'ref': 'abc123abc123/bild.png'}}.get(op, {})
        return j(out)
    if path.startswith('/api/claude'):
        req = json.loads(body or '{}')
        CALLS.append(req)
        if req.get('attach'):
            return route.fulfill(status=200, content_type='application/x-ndjson', body=REST)
        if 'ESKALATION' in str(req.get('prompt')):
            ESC['on'] = True
        if ESC['on']:
            if req.get('mode') == 'voll':
                ESC['on'] = False
                return route.fulfill(status=200, content_type='application/x-ndjson', body=OKESK)
            return route.fulfill(status=200, content_type='application/x-ndjson', body=DENY)
        return route.fulfill(status=200, content_type='application/x-ndjson', body=PART if 'DROP' in str(req.get('prompt')) else NDJSON)
    if path.startswith('/api/term'):
        TERM_CALLS.append(json.loads(body or '{}'))
        return route.fulfill(status=200, content_type='application/x-ndjson', body=TERM)
    if path.startswith('/api/files') and 'media%2Fmusik' in request.url:
        sub = 'Album' in request.url
        ents = [{'name': 'c.mp3', 'directory': False, 'size': 9000}] if sub else [{'name': 'Album', 'directory': True, 'size': 0}, {'name': 'a.wav', 'directory': False, 'size': 9000}, {'name': 'b.wav', 'directory': False, 'size': 9000}, {'name': 'notiz.txt', 'directory': False, 'size': 5}]
        return j({'path': 'x', 'entries': ents})
    if path.startswith('/api/audio'):
        import io, wave
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\0\0' * 8000 * 20)
        return route.fulfill(status=200, content_type='audio/wav', body=buf.getvalue())
    if path.startswith('/api/file') and 'status.json' in path:
        return j({'stand': '2026-10-12 08:28', 'probleme': ['Portal-Oberfläche auf dem Server ist nicht auf dem Stand des Projekts'],
                  'system': {'uptime_h': 187.8, 'ram_frei_mb': 1900, 'platte_belegt_prozent': 16, 'platte_frei_gb': 358, 'wachhund': 'OK', 'wachhund_stand': '08:25', 'akku': '0 %'},
                  'dienste': {'ma-home-web': 'active'}, 'updates': {'anzahl': 5, 'sicherheit': 0, 'neustart_noetig': False, 'beispiele': ['docker-ce']},
                  'version': {'portal_laufend': '2026-10-11-4', 'portal_repo': '2026-10-12-16', 'aktuell': False, 'bruecke_aktuell': False},
                  'neues': [{'titel': '2026-10-12 – Test', 'text': 'etwas Neues'}], 'offen': [{'id': 'B14', 'titel': 'Einspielen', 'status': 'offen'}],
                  'wichtig': {'fristen_woche': ['Abgabe Bericht'], 'fristen_bald': [], 'mails_bericht': ['Rechnung prüfen'], 'mails_bericht_datum': '2026-10-10', 'geplante_ergebnisse': [{'datei': 'Posteingang.md', 'alter_min': 30}]},
                  'eingang': {'anzahl': 0}})
    if path.startswith('/api/file') and 'Lern-Impuls' in path:
        return route.fulfill(status=200, content_type='text/markdown', body='# Lern-Impuls\n\nStand heute · Notiz: [[30 Technik/A/b|b]]\n\n### Frage 1\nWas ist DNS?\n')
    if path.startswith('/api/file') and 'Dienste' in path:
        return route.fulfill(status=200, content_type='text/markdown', body='## Montag\n- Top 1\n- Top 2\n')
    return route.fulfill(status=404, body='nicht gemockt')


def handler(route, request):
    path = request.url[len(BASE):].split('?')[0]
    if path.startswith('/api/'):
        return api(route, request)
    name = {'/': 'index.html', '/sw.js': 'sw.js'}.get(path) or path.replace('/assets/', '', 1).lstrip('/')
    fp = os.path.normpath(os.path.join(WEB, name))
    if not fp.startswith(os.path.normpath(WEB)) or not os.path.isfile(fp):
        return route.fulfill(status=404, body='')
    return route.fulfill(status=200, content_type=mimetypes.guess_type(fp)[0] or 'text/plain', body=open(fp, 'rb').read())


def main():
    results, errors = [], []

    def check(name, ok, info=''):
        results.append((name, bool(ok)))
        print(('PASS ' if ok else 'FAIL ') + name + (' – ' + str(info) if info and not ok else ''))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, accept_downloads=False)
        ctx.grant_permissions([])
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' and 'nicht gemockt' not in m.text and '404' not in m.text else None)
        page.route(BASE + '/**', handler)
        page.goto(BASE + '/')
        page.wait_for_selector('#view .top', timeout=8000)
        check('Startseite lädt, Version im Kopf', 'v2026-' in page.inner_text('.kicker').lower(), page.inner_text('.kicker'))
        check('Jarvis-Karte erscheint', page.wait_for_selector('#jarvis', timeout=4000) is not None)
        page.click('#jarvis summary')
        page.click('#jarvis button[data-fb=again]')
        page.wait_for_timeout(600)
        check('Lern-Rückmeldung „Nochmal“ wird gesendet', FEEDBACK and FEEDBACK[-1] == {'note': '30 Technik/A/b.md', 'result': 'again'}, FEEDBACK)
        check('Link zur Kalenderdatei (.ics)', page.locator('#jarvis a[href*="fristen.ics"]').count() == 1)
        check('kein Querscrollen (Start)', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'))
        page.evaluate("location.hash = '#/neu'")
        page.wait_for_selector('#nb .card', timeout=5000)
        nt = page.inner_text('#nb').lower()
        check('Reiter Neu: Status, Updates, Mails, Offenes', all(x.lower() in nt for x in ('Hinweis', '5 Pakete', 'Rechnung prüfen', 'B14', 'Einspielung offen', 'Abgabe Bericht')), nt[:300])
        check('Reiter Neu: Navigation markiert', page.locator('#nav button[data-t=neu][aria-current=page]').count() == 1)
        check('Reiter Neu: kein Querscrollen', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'))
        page.evaluate("location.hash = '#/musik'")
        page.wait_for_selector('#mlist .row', timeout=5000)
        ml = page.inner_text('#mlist').lower()
        check('Reiter Musik: Ordner und nur Audiodateien sichtbar', 'album' in ml and 'a' in ml and 'notiz' not in ml, ml)
        page.click('#mlist [data-f="0"]')
        page.wait_for_function("document.querySelector('#mplay').textContent.includes('❚')", timeout=5000)
        check('Musik: Titel startet, Warteschlange hat zwei Titel', page.locator('#mqueue .row').count() == 2 and 'a' in page.inner_text('#mnow').lower())
        page.click('#mnext')
        page.wait_for_function("document.querySelector('#mnow').innerText.toLowerCase().startsWith('b')", timeout=5000)
        check('Musik: Weiter springt zum nächsten Titel', True)
        page.evaluate("location.hash = '#/home'"); page.wait_for_selector('#view .top', timeout=4000)
        page.evaluate("location.hash = '#/musik'"); page.wait_for_selector('#mnow b', timeout=4000)
        check('Musik: Stand bleibt beim Reiterwechsel erhalten', page.inner_text('#mnow').lower().startswith('b'))
        page.click('#mcrumb button'); page.click('#mlist [data-d="Album"]')
        page.wait_for_function("document.querySelector('#mlist').innerText.toLowerCase().includes('c')", timeout=4000)
        check('Musik: Unterordner öffnen', 'a.wav' not in page.inner_text('#mlist').lower())
        page.click('#mplay')
        page.evaluate("location.hash = '#/claude'")
        page.wait_for_selector('#cmsgs', timeout=5000)
        page.fill('#cf textarea', 'Wie voll ist die Platte?')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Hallo')", timeout=8000)
        txt = page.inner_text('#cmsgs')
        check('Antwort wird angezeigt', 'Hallo' in txt)
        check('Werkzeugzeile sichtbar', 'Bash: df -h' in txt, txt[:200])
        check('Codeblock mit Kopieren-Knopf', page.locator('.codebox .cpy').count() == 2)
        check('HTML-Codeblock hat Vorschau-Knopf', page.locator('.codebox .pvw').count() == 1)
        page.click('.codebox .pvw')
        check('Vorschau läuft in abgeschottetem Rahmen (sandbox)', page.locator('iframe.pvframe[sandbox="allow-scripts"]').count() == 1)
        check('Tabelle gerendert', page.locator('.tblwrap table').count() == 1)
        cu = page.inner_text('#cmsgs .cuse')
        check('Verbrauch pro Nachricht (Modell, Tokens, Dauer)', 'haiku' in cu.lower() and 'rein' in cu and '40 raus' in cu and '8 s' in cu, cu)
        check('Token-Anzeige', 'Kontext' in page.inner_text('#ctok'), page.inner_text('#ctok'))
        check('Senden-Knopf nach Ende wieder „Senden“', 'senden' in page.inner_text('#csend').lower(), page.inner_text('#csend'))
        check('Vorlesen-Knopf vorhanden', page.locator('.cacts button[data-a=speak]').count() >= 1)
        page.fill('#cf textarea', '/notiz Docker')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Docker')", timeout=8000)
        check('/notiz startet eine Notizsuche im Modus „lesen“', 'Docker' in str(CALLS[-1].get('prompt')) and CALLS[-1].get('mode') == 'lesen', CALLS[-1])
        page.wait_for_function("document.querySelector('#csend').innerText.toLowerCase().includes('senden')", timeout=8000)
        check('Neu erzeugen / Kopieren vorhanden', page.locator('.cacts button[data-a=regen]').count() == 1)
        # Verbindungsabbruch mitten im Auftrag: das Portal haengt sich nach ein paar Sekunden per attach wieder an und holt den Rest
        page.fill('#cf textarea', 'DROP Verbindung testen bitte')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Teil1')", timeout=8000)
        page.evaluate("document.querySelector('#cmsgs').scrollTop = 0")      # Nutzer scrollt während der Antwort nach oben
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Teil1 Teil2')", timeout=15000)
        top = page.evaluate("document.querySelector('#cmsgs').scrollTop")
        ovf = page.evaluate("document.querySelector('#cmsgs').scrollHeight > document.querySelector('#cmsgs').clientHeight + 200")
        check('Chat überläuft (genug Inhalt zum Scrollen)', ovf)
        check('Hochscrollen bleibt erhalten, wenn neue Teile ankommen', top < 150, top)
        check('Knopf „↓ Neueste“ erscheint', page.locator('#cjump').is_visible())
        page.click('#cjump')
        page.wait_for_timeout(700)
        check('„↓ Neueste“ springt ans Ende', page.evaluate("(() => { const b = document.querySelector('#cmsgs'); return b.scrollHeight - b.scrollTop - b.clientHeight < 90; })()"))
        att = [c for c in CALLS if c.get('attach')]
        check('Wiederanhängen nach Abbruch (attach ab Position 3)', att and att[-1].get('attach') == 'job123' and att[-1].get('from') == 3, att)
        # Automatischer Council bei einer Entscheidungsfrage
        page.fill('#cf textarea', 'Soll ich lieber Variante A oder Variante B nehmen, oder ein ganz anderes Konzept?')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Hallo')", timeout=8000)
        check('Council startet automatisch bei Entscheidungsfrage', str(CALLS[-1].get('prompt')).startswith('AI-Council:'), str(CALLS[-1].get('prompt'))[:60])
        page.fill('#cf textarea', 'Soll ich lieber A oder B nehmen? ohne Council')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('ohne Council')", timeout=8000)
        check('„ohne Council“ schaltet ihn ab', not str(CALLS[-1].get('prompt')).startswith('AI-Council:'))
        page.wait_for_function("!document.querySelector('#csend').innerText.toLowerCase().includes('stopp')", timeout=8000)
        page.fill('#cf textarea', 'Im Terminal soll der Ordner automatisch gewählt werden')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Im Terminal soll')", timeout=8000)
        check('Auto wählt „Voll“ im Projekt und sendet sofort (ohne zweiten Druck)', CALLS[-1].get('mode') == 'voll' and CALLS[-1].get('dir') == 'maserver' and 'Terminal' in str(CALLS[-1].get('prompt')), CALLS[-1])
        page.wait_for_function("!document.querySelector('#csend').innerText.toLowerCase().includes('stopp')", timeout=8000)
        n0 = len(CALLS)
        page.fill('#cf textarea', 'ESKALATION: ergänze etwas')
        page.click('#csend')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Erledigt-ESK')", timeout=15000)
        seq = [(c.get('mode'), c.get('dir')) for c in CALLS[n0:]]
        check('Rechte-Eskalation: lesen → notizen → voll, Ordner folgt dem verweigerten Pfad', seq == [('lesen', 'notizen'), ('notizen', 'maserver'), ('voll', 'maserver')], seq)
        check('Rechte-Eskalation: Fortsetzung nennt die Erhöhung und läuft in derselben Sitzung', 'automatisch erhöht' in str(CALLS[-1].get('prompt')) and 'esc' not in CALLS[-1] and 'isEsc' not in CALLS[-1], CALLS[-1])
        page.wait_for_function("!document.querySelector('#csend').innerText.toLowerCase().includes('stopp')", timeout=8000)
        page.set_input_files('#cfile', {'name': 'bild.png', 'mimeType': 'image/png', 'buffer': b'\x89PNG\r\n\x1a\n' + b'0' * 200})
        page.wait_for_function("document.querySelector('#cimgs').innerText.includes('bild.png')", timeout=6000)
        check('Anhang als Chip', 'bild.png' in page.inner_text('#cimgs'))
        page.click('#csch')
        check('Aufgaben-Panel öffnet', page.locator('#schf').is_visible())
        page.wait_for_function("document.querySelector('#cses').innerText.includes('Heute: Chat 2/300')", timeout=4000)
        check('Verbrauch und Tageslimit sichtbar', True)
        page.select_option('#schv', 'eingang')
        check('Vorlage „Eingang“ blendet Uhrzeit und Wochentage aus', page.locator('#schtl').is_hidden() and page.locator('#schdays').is_hidden())
        page.click('#schf button.btn')
        page.wait_for_selector('#schl .csrow', timeout=4000)
        check('Aufgabe wird mit Auslöser „inbox“ gesendet und gelistet', SCHED_SET and SCHED_SET[-1].get('trigger') == 'inbox' and 'Eingang' in page.inner_text('#schl'), SCHED_SET)
        page.select_option('#schv', 'abend')
        check('Vorlage „Abend“ zeigt Uhrzeit wieder', page.locator('#schtl').is_visible() and page.input_value('#schf input[name=time]') == '18:30')
        page.select_option('#schv', 'posteingang')
        check('Vorlage „Posteingang“ setzt Modus Mail und Kalender lesen', page.input_value('#schf select[name=mode]') == 'konnektoren' and page.input_value('#schf input[name=time]') == '07:00')
        page.click('#schclose')
        # Laufenden Auftrag (anderes Gerät, geplanter Lauf) ansehen: Knopf „Ansehen“ hängt sich ab Anfang an
        JOBS.append({'id': 'jobX', 'sec': 5, 'prompt': 'Geplanter Lauf', 'model': 'haiku', 'mode': 'geplant:lesen'})
        page.wait_for_selector('#cstat button[data-view]', timeout=9000)
        page.click('#cstat button[data-view]')
        page.wait_for_function("document.querySelector('#cmsgs').innerText.includes('Teil2')", timeout=8000)
        att2 = [c for c in CALLS if c.get('attach') == 'jobX']
        check('„Ansehen“ hängt sich an laufenden Auftrag an (ab Position 0)', att2 and att2[-1].get('from') == 0, att2)
        JOBS.clear()
        page.click('#cseb')
        check('Verlaufsliste öffnet', page.wait_for_selector('.csrow', timeout=4000) is not None)
        page.go_back()
        check('Zurück-Geste schließt die Verlaufsliste', page.locator('#cses').is_hidden())
        page.evaluate("location.hash = '#/files'")
        page.wait_for_selector('#sf', timeout=5000)
        page.fill('#sf input', 'Notiz')
        page.click('#sf button')
        check('Suche zeigt Treffer', page.wait_for_selector('#sres .row', timeout=5000) is not None)
        # --- Vault (Obsidian-Ersatz) ---
        page.evaluate("location.hash = '#/vault'")
        page.wait_for_selector('#vsf', timeout=5000)
        check('Vault-Reiter zeigt Ordner und Notizen', 'Plan' in page.inner_text('#vlist') and '10 Leben' in page.inner_text('#vlist'), page.inner_text('#vlist')[:80])
        page.fill('#vsf input[name=q]', 'plan')
        check('Schnellwechsler filtert Notizen', page.wait_for_selector('#vres .row', timeout=3000) is not None)
        page.click('#vres .row')
        page.wait_for_selector('#vread', timeout=5000)
        check('Notiz wird gerendert (Callout, Tag, Wikilink)', page.locator('#vread blockquote.callout').count() == 1 and page.locator('#vread .ntag').count() == 1 and page.locator('#vread .wl').count() >= 1, page.inner_html('#vread')[:200])
        check('Bild aus dem Vault wird eingebettet', page.locator('#vread img.vimg2').count() == 1 and 'vault-notizen%2FAnhang%2Fbild.png' in page.get_attribute('#vread img.vimg2', 'src'), page.inner_html('#vread')[:200])
        check('Tag im Codeblock wird nicht als Tag erkannt', '#define' not in [e.inner_text() for e in page.locator('#vread .ntag').all()])
        check('Notiz-Einbettung ![[Notiz]] zeigt den Inhalt', page.wait_for_function("document.querySelector('#vread .embed').innerText.includes('Zurueck')", timeout=4000) is not None)
        check('Gliederung listet die Überschriften', page.locator('#vol button').count() == 3, page.locator('#vol button').count())
        page.click('#vbm')
        page.wait_for_timeout(400)
        check('Lesezeichen setzen (★)', '★' in page.inner_text('#vbm') and BOOKMARKS == ['Plan.md'], BOOKMARKS)
        check('Rückverweise werden angezeigt', 'Rückverweise (1)' in page.inner_text('#vbl'))
        page.click('#vgb')
        check('Lokale Graph-Ansicht zeigt Nachbarn', page.locator('#vgraph .vn').count() == 1)
        page.click('#vgraph .vn')
        page.wait_for_function("document.querySelector('#vread') && document.querySelector('#vread').innerText.includes('Zurueck')", timeout=5000)
        check('Tippen im Graph öffnet die Notiz', True)
        page.evaluate("location.hash = '#/vault?p=Plan.md'")
        page.wait_for_selector('#vread', timeout=5000)
        page.click('#vread .wl')
        page.wait_for_function("document.querySelector('.kicker').innerText.length > 0 && document.querySelector('#vread') && document.querySelector('#vread').innerText.includes('Zurueck')", timeout=5000)
        check('Wikilink öffnet die verlinkte Notiz', True)
        page.evaluate("location.hash = '#/vault?p=Plan.md&e=1'")
        page.wait_for_selector('#ved', timeout=5000)
        page.click('#ved')
        page.keyboard.press('Control+End')
        page.keyboard.type(' ZUSATZ')
        page.wait_for_function("document.querySelector('#vstat').innerText.includes('Gespeichert')", timeout=6000)
        check('Autospeichern schickt die Änderung mit etag', NOTE_WRITES and 'ZUSATZ' in NOTE_WRITES[-1]['content'] and NOTE_WRITES[-1]['etag'] == 'e1', NOTE_WRITES[-1:])
        page.evaluate("(() => { const t = document.querySelector('#ved'); t.value = 'abc [[Pl'; t.setSelectionRange(8, 8); t.dispatchEvent(new Event('input')); })()")
        check('Wikilink-Vorschläge beim Tippen von [[', page.wait_for_selector('#vsug button', timeout=3000) is not None)
        page.click('#vsug button')
        check('Vorschlag wird eingefügt', ']]' in page.input_value('#ved'), page.input_value('#ved'))
        page.wait_for_function("document.querySelector('#vstat').innerText.includes('Gespeichert')", timeout=6000)
        page.evaluate("location.hash = '#/vault?p=' + encodeURIComponent('_Claude-Memory/Index.md')")
        page.wait_for_selector('#vread', timeout=5000)
        check('Geschützter Ordner ist nur lesbar (kein Bearbeiten-Knopf)', page.locator('#vmode').count() == 0)
        page.evaluate("location.hash = '#/vault'")
        page.wait_for_selector('#vdaily', timeout=4000)
        check('Lesezeichen erscheinen in der Vault-Übersicht', page.locator('#vmk .row').count() == 1)
        page.fill('#vsf input[name=q]', 'path:leben')
        check('Suchoperator path: filtert nach Ordner', page.wait_for_selector('#vres .row', timeout=3000) is not None)
        page.fill('#vsf input[name=q]', '')
        page.click('#vdaily')
        page.wait_for_selector('#ved', timeout=5000)
        check('Tagesnotiz öffnet im Editor', 'Tagesnotizen' in page.inner_text('.top .sub'), page.inner_text('.top .sub'))
        page.evaluate("location.hash = '#/term'")
        page.wait_for_selector('#tf', timeout=5000)
        page.fill('#tf input[name=cmd]', 'echo hallo')
        page.click('#trun')
        page.wait_for_function("document.querySelector('#tout').innerText.includes('hallo-terminal')", timeout=6000)
        check('Terminal zeigt Ausgabe', True)
        check('Terminal: Ordner „Automatisch“ ist Standard, df-Befehl nimmt Server-Home und zeigt es an', page.input_value('#tf select[name=dir]') == 'auto' and TERM_CALLS[-1].get('dir') == 'server' and '[Ordner: Server-Home]' in page.inner_text('#tout'), TERM_CALLS[-1:])
        for cmd, want in (('git status', 'maserver'), ('vault-q search dns', 'notizen'), ('ls /srv/ma-home/library/inbox', 'bibliothek')):
            page.fill('#tf input[name=cmd]', cmd)
            page.click('#trun')
            page.wait_for_function("!document.querySelector('#trun').disabled", timeout=6000)
            check('Terminal: „%s“ wählt Ordner %s' % (cmd, want), TERM_CALLS[-1].get('dir') == want, TERM_CALLS[-1:])
        page.select_option('#tf select[name=dir]', 'bibliothek')
        page.fill('#tf input[name=cmd]', 'git status')
        page.click('#trun')
        page.wait_for_function("!document.querySelector('#trun').disabled", timeout=6000)
        check('Terminal: manuell gewählter Ordner bleibt bestehen', TERM_CALLS[-1].get('dir') == 'bibliothek', TERM_CALLS[-1:])
        page.select_option('#tf select[name=dir]', 'auto')
        n = len(TERM_CALLS)
        page.fill('#tf input[name=cmd]', 'sudo systemctl status ssh')
        page.click('#trun')
        page.wait_for_timeout(500)
        check('Terminal: sudo-Befehl wird beim ersten Absenden nicht gesendet', len(TERM_CALLS) == n, TERM_CALLS[-1:])
        page.click('#trun')
        page.wait_for_function("!document.querySelector('#trun').disabled", timeout=6000)
        check('Terminal: sudo-Befehl läuft beim zweiten Absenden', len(TERM_CALLS) == n + 1 and TERM_CALLS[-1].get('cmd', '').startswith('sudo '), TERM_CALLS[-1:])
        n = len(TERM_CALLS)
        page.fill('#tf input[name=cmd]', 'rm -rf /tmp/testordner')
        page.click('#trun')
        page.wait_for_timeout(500)
        check('Riskanter Befehl wird beim ersten Mal nicht gesendet', len(TERM_CALLS) == n, TERM_CALLS[-1:])
        page.click('#trun')
        page.wait_for_timeout(800)
        check('Riskanter Befehl läuft beim zweiten Absenden', len(TERM_CALLS) == n + 1)
        check('kein Querscrollen (Terminal)', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'))
        page.goto(BASE + '/?text=Hallo%20Teilen')
        page.wait_for_selector('#cf textarea', timeout=6000)
        check('Teilen-Menü legt Text als Entwurf in den Chat', page.input_value('#cf textarea') == 'Hallo Teilen', page.input_value('#cf textarea'))
        page.evaluate("location.hash = '#/jarvis'")
        page.wait_for_selector('#jvlist .row', timeout=5000)
        check('JARVIS-Reiter: Navigation markiert, Auftrag gelistet', page.locator('#nav button[data-t=jarvis][aria-current=page]').count() == 1 and 'Teste Freigabe' in page.inner_text('#jvlist'))
        page.fill('#jvf textarea', 'Neuer Auftrag eins')
        page.click('#jvf button')
        page.wait_for_function("document.querySelector('#jvdet').innerText.includes('braucht Freigabe')", timeout=6000)
        sub = [x for x in JV_CALLS if x.get('cmd') == 'submit']
        check('JARVIS: Auftrag wird mit Schlüssel gesendet, Detail zeigt Freigabe', len(sub) == 1 and sub[0].get('request') == 'Neuer Auftrag eins' and len(sub[0].get('client_id', '')) >= 8, sub)
        page.click('#jvok')
        page.wait_for_function("document.querySelector('#jvdet').innerText.includes('BERICHT.md')", timeout=6000)
        ap = [x for x in JV_CALLS if x.get('cmd') == 'approve']
        check('JARVIS: Freigabe sendet Schritt, danach erscheinen Ergebnisdateien', len(ap) == 1 and ap[0].get('step') == 's1', ap)
        check('JARVIS: kein Querscrollen', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'))
        check('keine JavaScript-Fehler', not errors, '; '.join(errors[:3]))
        browser.close()
    failed = [n for n, ok in results if not ok]
    print('\n%d von %d Prüfungen bestanden.' % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
