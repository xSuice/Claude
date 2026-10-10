#!/usr/bin/python3
"""PreToolUse-Hook (Server): sperrt Senden, Loeschen, Veroeffentlichen, Kaufen usw. ueber MCP-Verbindungen,
ausser der Chat laeuft im Modus "Voll + Senden" (Umgebung MA_ALLOW_SEND=1, gilt nur fuer diese eine Nachricht)."""
import json
import os
import re
import sys

RISKY = re.compile(r'send|reply|forward|delete|trash|publish|share|deploy|respond_to_event|buy|purchase|pay|transfer|order|'
                   r'cancel|merge|rollback|promote|revoke|kill|firewall|domain|record|invite|accept|approve|spam|remove|'
                   r'settings_|filters|execute_sql(?!_readonly)|move|archive|update_message_labels|threads_modify|unpause|pause', re.I)
SAFE = re.compile(r'(^|__)(get|list|search|read|fetch|query|describe|count|aggregate)', re.I)

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
name = str(data.get('tool_name', ''))
if not name.startswith('mcp__') or os.environ.get('MA_ALLOW_SEND') == '1':
    sys.exit(0)
action = name.split('__')[-1]
if RISKY.search(action) and not SAFE.search(action):
    print(f'Gesperrt: "{name}" sendet, loescht, veroeffentlicht oder kauft etwas. Das braucht Philipps ausdrueckliches Ja. '
          'Bereite alles vor (z. B. Entwurf), beschreibe genau was passieren wuerde, und bitte ihn, die Nachricht im Modus '
          '"Voll + Senden" zu wiederholen.', file=sys.stderr)
    sys.exit(2)
sys.exit(0)
