#!/usr/bin/env python3
"""UserPromptSubmit-Hook: meldet große Sitzungen (Kontext-Wächter, Server-Gegenstück zum PC).
Liest die Token-Zahl der letzten Antwort aus dem Transcript. Ab 250 000 Warnung, ab 300 000 Auftrag zur Übergabe.
Abschalten pro Nachricht mit "ohne waechter"."""
import json
import re
import sys

WARN, UEBERGABE = 250_000, 300_000
try:
    d = json.load(sys.stdin)
    p, pfad = d.get("prompt", ""), d.get("transcript_path", "")
except Exception:
    sys.exit(0)
if re.search(r"ohne w(ä|ae)chter", p, re.I) or p.lstrip().startswith("/uebergabe"):
    sys.exit(0)

tok = 0
try:
    with open(pfad, encoding="utf-8") as f:
        for z in f:
            try:
                u = (json.loads(z).get("message") or {}).get("usage")
            except Exception:
                continue
            if isinstance(u, dict):
                tok = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
except Exception:
    sys.exit(0)

if tok >= UEBERGABE:
    t = ("Kontext-Wächter: Die Sitzung hat ca. %dk Token. Führe am Ende dieser Antwort `/uebergabe` aus, "
         "damit Philipp in einer frischen Sitzung günstiger weitermacht." % (tok // 1000))
elif tok >= WARN:
    t = "Kontext-Wächter: Die Sitzung hat ca. %dk Token. Erwähne kurz, dass bald eine neue Sitzung (`/uebergabe`) sinnvoll ist." % (tok // 1000)
else:
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": t}}))
