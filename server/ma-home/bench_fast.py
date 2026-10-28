import json, subprocess, sys, time
C = '/home/andrew/.local/bin/claude'
SYS = 'Du bist JARVIS, ein freundlicher deutscher Sprachassistent. Antworte natürlich, kurz (höchstens 3 Sätze), ohne Markdown, Listen oder Emojis.'
VARIANTS = {
    'default_sys': ['--tools', ''],
    'short_sys': ['--tools', '', '--system-prompt', SYS],
    'short_sys_nosettings': ['--tools', '', '--system-prompt', SYS, '--setting-sources', ''],
}
q = 'Erzähle mir in zwei Sätzen etwas über Minecraft Modding.'
for name, extra in VARIANTS.items():
    for rep in range(2):
        t0 = time.time(); first = None
        p = subprocess.Popen([C, '-p', '--model', 'haiku', '--strict-mcp-config', '--max-turns', '1', '--output-format', 'stream-json', '--verbose', '--include-partial-messages'] + extra,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, cwd='/tmp')
        p.stdin.write(q); p.stdin.close()
        txt = ''
        for line in p.stdout:
            try: d = json.loads(line)
            except ValueError: continue
            ev = d.get('event') or {}
            if d.get('type') == 'stream_event' and ev.get('type') == 'content_block_delta' and (ev.get('delta') or {}).get('type') == 'text_delta':
                if first is None: first = time.time() - t0
                txt += ev['delta']['text']
        p.wait()
        print(name, rep, 'erstes_wort=%.1fs' % (first or -1), 'gesamt=%.1fs' % (time.time() - t0), repr(txt[:80]), flush=True)
