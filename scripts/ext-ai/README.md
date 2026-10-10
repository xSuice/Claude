# Externe KI-Helfer (ask.py), Stand 2026-10-10

Zweck: Tokens sparen. Claude lässt unkritische Aufgaben (Prompt verbessern, Entwurf, Übersetzung, öffentliche Recherche) von Gemini oder DeepSeek erledigen, ohne Browser und ohne Screenshots.

## Einrichtung (einmalig, durch Philipp)
1. Gemini-Schlüssel: aistudio.google.com/apikey (Google AI Studio). Im Gratis-Tarif werden Eingaben laut Google zur Verbesserung der Produkte genutzt, deshalb nur Klasse A.
2. DeepSeek-Schlüssel: platform.deepseek.com/api_keys. API ist kostenpflichtig (Preis vor Nutzung auf platform.deepseek.com prüfen; nicht belegt).
3. Schlüssel als reine Textdatei ablegen, **nie im Chat posten**:
   - `C:\Users\andre\.claude\secrets\gemini.key`
   - `C:\Users\andre\.claude\secrets\deepseek.key`
4. Test: `python ask.py gemini --klasse-a "Sag kurz Hallo"`

## Regeln (im Skript erzwungen)
- Ohne `--klasse-a` wird nichts gesendet. Max. 8000 Zeichen.
- Abbruch bei Passwort/Token-Mustern, langen Schlüsseln, E-Mail-Adressen, IBAN, Telefonnummern.
- Ein Versuch, kein Retry, kein Wechsel zu anderem Anbieter bei Fehler oder Limit.
- Log ohne Inhalt: `~/.claude/state/ext-ai.log`.
- Claude kann den Schlüsselordner nicht lesen (Permission-Sperre auf Read und Bash).

## OpenRouter (neu, 2026-10-10)
- Schlüssel auf openrouter.ai erstellen und als `openrouter.key` im Ordner `.claude\secrets` ablegen (wie die anderen).
- Nur kostenlose Modelle (Endung `:free` oder `openrouter/free`), andere blockiert das Skript. Standard: `google/gemma-4-31b-it:free`.
- Limits laut offizieller Seite: 20 Anfragen/Minute, 50 pro Tag (1.000 ab 10 Euro gekauftem Guthaben insgesamt). Ob Prompts geloggt oder zum Training genutzt werden: nicht belegt, deshalb nur Klasse A.
- Stand: Schutzlogik und echter Aufruf getestet am 2026-10-10 (Modell `google/gemma-4-31b-it:free`, ok).

## Ollama lokal (neu, 2026-10-10)
- Installiert: Ollama 0.40.2 (Installer von ollama.com geprüft: Größe 1.578.560.904 Byte, Signatur Ollama Inc. gültig), Modell `gemma3:4b` (3,4 GB, läuft zu 100 Prozent auf der RTX 2060).
- Aufruf: `python ask.py ollama "Frage"`. Kein `--klasse-a` nötig, nichts verlässt den PC. Erlaubt auch Klasse B (Mail, Telefon). Geheimnisse (Passwort/Token-Muster) blockiert das Skript trotzdem. Max. 30.000 Zeichen.
- Getestet: deutsche Antwort korrekt, ca. 19 Sekunden (erster Aufruf nach Start länger, Modell lädt). Qualität deutlich unter Claude/Gemini, nur für einfache Aufgaben.
- Der Installer liegt noch in `Downloads\ollama-setup\` (1,5 GB), kann gelöscht werden.

## Nicht eingerichtet
- ChatGPT/OpenAI: Abo ist kein API-Zugang. Erst einrichten, wenn ein API-Konto da ist.
- Nutzung der Websites über den Browser: langsamer, braucht mehr Tokens (Seitentext, Screenshots) und kann gegen die Nutzungsbedingungen verstoßen.

## Status
Schutzlogik getestet (Positiv- und Negativfälle). Echter Aufruf Gemini getestet am 2026-10-10 (Modell `gemini-flash-latest`). `gemini-2.5-flash` ist trotz Liste für neue Nutzer nicht mehr verfügbar (404). DeepSeek ungetestet (kein Schlüssel).
