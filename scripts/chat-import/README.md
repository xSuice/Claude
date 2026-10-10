# Chat-Import (ChatGPT, DeepSeek)

Wiederholbare Skripte, Stand 2026-10-10. Alles lokal, nichts geht nach außen.

Quellen (Pfade oben in jedem Skript anpassen, wenn neue Exporte kommen):
- ChatGPT-Export: `Obsidian Vault\90 Archiv\KI-Exporte\ChatGPT-Export-2026-10-07\conversations-*.json`
- DeepSeek-Export: `Obsidian Vault\90 Archiv\KI-Exporte\DeepSeek-Export-2026-10-10\conversations.json`

Skripte:
- `chatgpt_index.py`: Index (Datum, Titel, Anzahl Nachrichten) nach `_Claude-Memory/Import/ChatGPT-Index.md`.
- `raw_archive.py`: nur deine Nachrichten, nach Monat, nach `Import/raw/`.
- `raw_voll.py`: vollständige Dialoge (Du und KI), nach `Import/raw-voll/` (35 MB).

Geschwärzt werden IDs, lange Schlüssel-Strings, IBANs, Zeilen mit token/passwort/api key/secret.
Erneuter Lauf überschreibt nur die Archivdateien, keine Notizen.
Die handgeschriebenen Themennotizen (`Import/ChatGPT/`, `Import/DeepSeek/`) sind nicht Teil der Skripte.
