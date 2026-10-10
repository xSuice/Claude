import json, glob, datetime, os, sys
vault = r"C:\Users\andre\Documents\Obsidian Vault"
out_dir = os.path.join(vault, "_Claude-Memory", "Import")
os.makedirs(out_dir, exist_ok=True)
rows = []
for f in sorted(glob.glob(os.path.join(vault, "90 Archiv", "KI-Exporte", "ChatGPT-Export-2026-10-07", "conversations-*.json"))):
    for c in json.load(open(f, encoding="utf-8")):
        msgs = [m.get("message") for m in c.get("mapping", {}).values() if m.get("message")]
        user = [m for m in msgs if (m.get("author") or {}).get("role") == "user"]
        chars = sum(len(str((m.get("content") or {}).get("parts", ""))) for m in msgs)
        t = c.get("create_time") or 0
        rows.append((t, (c.get("title") or "(ohne Titel)").replace("|", "/").replace("\n", " "),
                     len(user), chars, c.get("id") or c.get("conversation_id") or "", os.path.basename(f)))
rows.sort()
lines = ["---", "typ: import-index", "quelle: ChatGPT-Export 2026-10-07 (conversations-*.json im Vault-Root)",
         f"datum: {datetime.date.today()}", "pruefstatus: ungeprüft (nur Metadaten, keine Inhalte)", "---", "",
         "# ChatGPT-Index", "", f"{len(rows)} Chats. Nur Metadaten. Inhalte bleiben in den Originaldateien.", "",
         "| Datum | Titel | Nutzernachr. | Zeichen | Datei | ID |", "|---|---|---|---|---|---|"]
for t, title, n, ch, i, fn in rows:
    d = datetime.datetime.fromtimestamp(t).date() if t else "?"
    lines.append(f"| {d} | {title} | {n} | {ch} | {fn} | {i} |")
open(os.path.join(out_dir, "ChatGPT-Index.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
# Fortschrittsdatei nur anlegen, wenn sie fehlt (nie ueberschreiben, sonst gehen verarbeitete IDs verloren)
fp = os.path.join(out_dir, "ChatGPT-Fortschritt.json")
if not os.path.exists(fp):
    json.dump({"quelle": "ChatGPT", "gesamt": len(rows), "verarbeitet": [], "stand": str(datetime.date.today())},
              open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(rows), "Zeilen")
