#!/usr/bin/env python3
"""UserPromptSubmit-Hook: startet den Council automatisch bei Ideen, Entscheidungen und Plaenen.
Abschalten pro Nachricht mit "ohne council"."""
import json
import re
import sys

AUS = re.compile(r"ohne council|kein council", re.I)
AN = re.compile(
    r"\bcouncil\b|pr(ü|ue)f(e|en)? (meine|diese|die|den|das|mal)|gute idee|lohnt (es )?sich|"
    r"\bsoll(te)? ich\b|was h(ä|ae)ltst du (von|davon)|sinnvoll(er)?[,?]|vor- ?und nachteile|"
    r"\b(entscheidung|projektidee|geschäftsidee|geschaeftsidee)\b|\b(umbau|neu ?aufbau|migration)\b.*\?|"
    r"\b(plan|strategie|konzept|architektur)\b.*\b(bewert|pr(ü|ue)f|passt|taugt|okay|ok)\b|"
    r"\b(entweder|oder)\b.*\?|\bwelche(r|s)? (variante|option|l(ö|oe)sung) ", re.I)
try:
    p = json.load(sys.stdin).get("prompt", "")
except Exception:
    sys.exit(0)
if len(p) < 25 or p.lstrip().startswith(("/", "AI-Council:")) or AUS.search(p) or not AN.search(p):
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
  "Council-Auto: Diese Nachricht ist eine Idee/Entscheidung/ein Plan. Rufe VOR der Antwort den Skill `council` auf (fünf Rollen, zwei Runden, Empfehlung) und sage kurz 'Council automatisch gestartet'. Ausnahme: reine Wissensfrage ohne Entscheidung, dann normal antworten."}}))
