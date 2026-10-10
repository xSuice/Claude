import json, glob, os, re, datetime, collections
base = r"C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Import\raw-voll"
UUID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
LONG = re.compile(r'\b[A-Za-z0-9_\-+/=]{40,}\b')
IBAN = re.compile(r'\b[A-Z]{2}\d{2}(?:\s?[0-9A-Z]{4}){3,7}\b')
KEYV = re.compile(r'(?i)(token|passwort|password|api[_\- ]?key|secret)\s*[:=]\s*\S+')
CITE = re.compile(r'cite(?:turn\d+(?:search|view|news|image|product)\d+)+')
PRIV = re.compile(r'[\ue000-\uf8ff]')

def red(s):
    s = s.replace('[[', r'\[\[')  # Obsidian: keine Geister-Links aus Bash-Bedingungen
    s = PRIV.sub('', s)
    s = CITE.sub('', s)
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
    total = 0
    for ym, lst in sorted(by.items()):
        lst.sort()
        out = ["---", "typ: roharchiv-voll", "quelle: " + src + "-Export (vollständige Dialoge, Du und KI)",
               "datum: " + ym, "importiert: 2026-10-10", "pruefstatus: ungeprüft, Rohtext, Antworten der KI nicht verifiziert",
               "datenklasse: B (privat, nur lokal)", "---", "", "# " + src + " vollständig " + ym, ""]
        for dt, title, cid, msgs in lst:
            out.append("## " + (title or "(ohne Titel)").replace("\n", " ") + " (" + dt + ", " + str(len(msgs)) + " Nachr.)")
            out.append("")
            for role, m in msgs:
                m = red(m).strip()
                if m:
                    out.append(("**Du:** " if role == 'u' else "**KI:** ") + m)
                    out.append("")
        s = "\n".join(out)
        total += len(s)
        open(os.path.join(base, src, ym + ".md"), 'w', encoding='utf-8').write(s)
    return len(by), total

def tx(parts):
    return " ".join(str(x) for x in parts if isinstance(x, str)).strip()

chats = []
gp = r"C:\Users\andre\Documents\Obsidian Vault\90 Archiv\KI-Exporte\ChatGPT-Export-2026-10-07"
for f in sorted(glob.glob(gp + r"\conversations-*.json")):
    for c in json.load(open(f, encoding='utf-8')):
        ms = [v['message'] for v in c['mapping'].values() if v.get('message') and v['message'].get('create_time') and v['message']['author']['role'] in ('user', 'assistant')]
        ms.sort(key=lambda m: m['create_time'])
        msgs = []
        for m in ms:
            t = tx(m['content'].get('parts', []))
            if t:
                msgs.append(('u' if m['author']['role'] == 'user' else 'a', t))
        dt = datetime.date.fromtimestamp(c.get('create_time') or 0).isoformat()
        chats.append((dt, c.get('title'), c['id'], msgs))
r1 = write("ChatGPT", chats)

chats = []
for c in json.load(open(r"C:\Users\andre\Documents\Obsidian Vault\90 Archiv\KI-Exporte\DeepSeek-Export-2026-10-10\conversations.json", encoding='utf-8')):
    nodes = [v['message'] for v in c['mapping'].values() if v.get('message')]
    nodes.sort(key=lambda m: m.get('inserted_at', ''))
    msgs = []
    for m in nodes:
        for fr in m.get('fragments', []):
            t = str(fr.get('content', '')).strip()
            if not t:
                continue
            if fr.get('type') == 'REQUEST':
                msgs.append(('u', t))
            elif fr.get('type') == 'RESPONSE':
                msgs.append(('a', t))
    chats.append((c['inserted_at'][:10], c.get('title'), c['id'], msgs))
r2 = write("DeepSeek", chats)
print("ChatGPT Monate/Zeichen", r1, "DeepSeek", r2)
