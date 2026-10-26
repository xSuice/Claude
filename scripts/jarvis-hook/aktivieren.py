#!/usr/bin/env python3
"""Trägt den JARVIS-Weiterleitungs-Hook in ~/.claude/settings.json ein (mit Sicherung). Rückbau: Argument 'entfernen'."""
import json, os, shutil, sys

P = os.path.expanduser("~/.claude/settings.json")
CMD = "python3 /home/andrew/MA-Server/scripts/jarvis-hook/jarvis-submit-hook.py"
d = json.load(open(P))
liste = d["hooks"]["UserPromptSubmit"][0]["hooks"]
shutil.copy(P, P + ".vor-jarvis-hook")
if len(sys.argv) > 1 and sys.argv[1] == "entfernen":
    liste[:] = [h for h in liste if h.get("command") != CMD]
elif not any(h.get("command") == CMD for h in liste):
    liste.append({"type": "command", "command": CMD, "timeout": 25})
json.dump(d, open(P, "w"), indent=2, ensure_ascii=False)
json.load(open(P))
print("hooks:", [h["command"].split("/")[-1] for h in liste])
