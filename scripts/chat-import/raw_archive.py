import json, glob, os, re, datetime, collections
base = r"C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Import\raw"
UUID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
LONG = re.compile(r'\b[A-Za-z0-9_\-+/=]{32,}\b')
IBAN = re.compile(r'\b[A-Z]{2}\d{2}(?:\s?[0-9A-Z]{4}){3,7}\b')
KEYV = re.compile(r'(?i)(token|passwort|password|api[_\- ]?key|secret)\s*[:=]\s*\S+')

def red(s):
    s = s.replace('[[', r'\[\[')  # Obsidian: keine Geister-Links aus Bash-Bedingungen
    s = UUID.sub('[ID]', s)
    s = IBAN.sub('[IBAN]', s)
    s = KEYV.sub(lambda m: m.group(1) + ': [GESCHWAERZT]', s)
    s = LONG.sub('[LANG]', s)
    return s

def write(src, chats):
    by = collections.defaultdict(list)
    for dt, title, cid, msgs in chats:
        by[dt[:7]].append((dt, title, cid, msgs))
    os.makedirs(os.path.join(base, src), exist_ok=True)
    for ym, lst in sorted(by.items()):
        lst.sort()
        out = ["---", "typ: roharchiv", "quelle: " + src + "-Export (nur deine Nachrichten, Antworten der KI nicht enthalten)",
               "datum: " + ym, "importiert: 2026-10-10", "pruefstatus: ungeprüft, Rohtext",
               "datenklasse: B (privat, nur lokal, nicht nach außen geben)", "---", "", "# " + src + " " + ym, ""]
        for dt, title, cid, msgs in lst:
            out.append("## " + (title or "(ohne Titel)").replace("\n", " ") + " (" + dt + ", " + str(len(msgs)) + " Nachr.)")
            out.append("")
            for m in msgs:
                m = red(m).strip()
                if m:
                    out.append("> " + m.replace("\n", "\n> "))
                    out.append("")
        open(os.path.join(base, src, ym + ".md"), 'w', encoding='utf-8').write("\n".join(out))
    return len(by)

# ChatGPT
chats = []
gp = r"C:\Users\andre\Documents\Obsidian Vault\90 Archiv\KI-Exporte\ChatGPT-Export-2026-10-07"
for f in sorted(glob.glob(gp + r"\conversations-*.json")):
    for c in json.load(open(f, encoding='utf-8')):
        ms = [v['message'] for v in c['mapping'].values() if v.get('message') and v['message'].get('create_time') and v['message']['author']['role'] == 'user']
        ms.sort(key=lambda m: m['create_time'])
        txt = []
        for m in ms:
            t = " ".join(str(x) for x in m['content'].get('parts', []) if isinstance(x, str)).strip()
            if t:
                txt.append(t)
        dt = datetime.date.fromtimestamp(c.get('create_time') or 0).isoformat()
        chats.append((dt, c.get('title'), c['id'], txt))
n1 = write("ChatGPT", chats)

# DeepSeek
chats = []
for c in json.load(open(r"C:\Users\andre\Documents\Obsidian Vault\90 Archiv\KI-Exporte\DeepSeek-Export-2026-10-10\conversations.json", encoding='utf-8')):
    nodes = [v['message'] for v in c['mapping'].values() if v.get('message')]
    nodes.sort(key=lambda m: m.get('inserted_at', ''))
    txt = []
    for m in nodes:
        for fr in m.get('fragments', []):
            if fr.get('type') == 'REQUEST':
                t = str(fr.get('content', '')).strip()
                if t:
                    txt.append(t)
    chats.append((c['inserted_at'][:10], c.get('title'), c['id'], txt))
n2 = write("DeepSeek", chats)

tot = 0
for f in glob.glob(base + r"\*\*.md"):
    tot += os.path.getsize(f)
print("Monate ChatGPT", n1, "DeepSeek", n2, "Gesamt MB", round(tot / 1e6, 1))
