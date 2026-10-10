#!/usr/bin/env python3
"""Externe KI (Gemini, DeepSeek) fuer UNKRITISCHE Aufgaben befragen. Datenklasse A only.

Aufruf:
  python ask.py gemini  --klasse-a "Formuliere diesen Prompt klarer: ..."
  python ask.py deepseek --klasse-a --file prompt.txt

Regeln (im Skript erzwungen):
- Ohne --klasse-a wird nichts gesendet.
- Abbruch, wenn der Text nach Geheimnissen, Mailadressen, IBAN, Telefonnummern, langen Schluesseln aussieht.
- Max. 8000 Zeichen. Ein Versuch, kein stilles Umschalten auf bezahlte Dienste.
- Schluessel liegen in ~/.claude/secrets/<anbieter>.key (nie in Prompts, Git, Vault). Das Skript gibt sie nie aus.
- Log (nur Anbieter, Zeit, Laenge, Ergebnis-Code, KEIN Inhalt): ~/.claude/state/ext-ai.log
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

HOME = os.path.expanduser("~")
KEYDIR = os.path.join(HOME, ".claude", "secrets")
LOG = os.path.join(HOME, ".claude", "state", "ext-ai.log")
MAXLEN = 8000

BLOCK = [
    (re.compile(r'(?i)(token|passwort|password|api[_\- ]?key|secret|private key)\s*[:=]'), "Schluessel/Passwort-Muster"),
    (re.compile(r'\b[A-Za-z0-9_\-+/=]{32,}\b'), "langer Schluessel-String"),
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+'), "E-Mail-Adresse"),
    (re.compile(r'\b[A-Z]{2}\d{2}(?:\s?[0-9A-Z]{4}){3,7}\b'), "IBAN"),
    (re.compile(r'(?<!\d)(?:\+49|0049|0)\s?\d{2,5}[\s/-]?\d{5,10}(?!\d)'), "Telefonnummer"),
]


def check(text):
    for pat, why in BLOCK:
        if pat.search(text):
            return why
    return None


def log(provider, n, status):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + f" {provider} chars={n} status={status}\n")


def key(provider):
    p = os.path.join(KEYDIR, provider + ".key")
    if not os.path.exists(p):
        sys.exit(f"Kein Schluessel: {p} anlegen (nur der Schluessel als Text). Nichts gesendet.")
    return open(p, encoding="utf-8").read().strip()


def post(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={**headers, "Content-Type": "application/json"})
    # lokal: erstes Laden des Modells kann dauern
    with urllib.request.urlopen(req, timeout=240 if url.startswith("http://127.0.0.1") else 60) as r:
        return json.loads(r.read().decode("utf-8"))


def gemini(text, model):
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
             {"x-goog-api-key": key("gemini")},
             {"contents": [{"parts": [{"text": text}]}]})
    return d["candidates"][0]["content"]["parts"][0]["text"]


def deepseek(text, model):
    d = post("https://api.deepseek.com/chat/completions",
             {"Authorization": "Bearer " + key("deepseek")},
             {"model": model, "messages": [{"role": "user", "content": text}], "stream": False})
    return d["choices"][0]["message"]["content"]


def openrouter(text, model):
    # Nur Modelle mit Endung ":free" erlauben, damit nie versehentlich bezahlt wird.
    if not model.endswith(":free") and model != "openrouter/free":
        sys.exit("Abbruch: bei openrouter nur kostenlose Modelle (Endung :free oder openrouter/free).")
    d = post("https://openrouter.ai/api/v1/chat/completions",
             {"Authorization": "Bearer " + key("openrouter")},
             {"model": model, "messages": [{"role": "user", "content": text}]})
    return d["choices"][0]["message"]["content"]


def ollama(text, model):
    # Lokal auf diesem PC (127.0.0.1). Nichts verlaesst den Rechner.
    d = post("http://127.0.0.1:11434/api/chat", {},
             {"model": model, "messages": [{"role": "user", "content": text}], "stream": False})
    return d["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", choices=["gemini", "deepseek", "openrouter", "ollama"])
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--klasse-a", action="store_true", help="bestaetigt: unkritisch, oeffentlich")
    ap.add_argument("--model")
    ap.add_argument("--dry-run", action="store_true", help="nur pruefen, nichts senden")
    a = ap.parse_args()
    text = open(a.file, encoding="utf-8").read() if a.file else (a.prompt or "")
    local = a.provider == "ollama"
    if not local and not a.klasse_a:
        sys.exit("Abbruch: ohne --klasse-a wird nichts gesendet.")
    if not text.strip():
        sys.exit("Abbruch: leerer Text.")
    if len(text) > (30000 if local else MAXLEN):
        sys.exit(f"Abbruch: {len(text)} Zeichen, Maximum {30000 if local else MAXLEN}.")
    # Lokal sind Klasse B (Mail, Telefon) erlaubt, Geheimnisse (Klasse C) nie.
    why = check(text) if not local else (BLOCK[0][1] if BLOCK[0][0].search(text) else None)
    if why:
        log(a.provider, len(text), "blockiert:" + why)
        sys.exit(f"Abbruch: Text enthaelt {why}. Nichts gesendet.")
    if a.dry_run:
        print("OK (dry-run): wuerde an", a.provider, "senden,", len(text), "Zeichen.")
        return
    try:
        if a.provider == "gemini":
            out = gemini(text, a.model or "gemini-flash-latest")
        elif a.provider == "deepseek":
            out = deepseek(text, a.model or "deepseek-flash")
        elif a.provider == "openrouter":
            out = openrouter(text, a.model or "google/gemma-4-31b-it:free")
        else:
            out = ollama(text, a.model or "gemma3:4b")
        log(a.provider, len(text), "ok")
        print(out)
    except urllib.error.HTTPError as e:
        log(a.provider, len(text), f"http{e.code}")
        sys.exit(f"Fehler {e.code} von {a.provider} (Limit/Kontingent/Schluessel?). Kein automatischer Wechsel, kein Retry.")
    except Exception as e:
        log(a.provider, len(text), "fehler")
        sys.exit(f"Fehler: {type(e).__name__}. Nichts weiter versucht.")


if __name__ == "__main__":
    main()
