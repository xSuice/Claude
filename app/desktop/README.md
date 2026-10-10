# MA Home Desktop (Windows)

Eigene App: Chat mit Claude, der auf dem MA-Server läuft, dazu das Portal und Serverstatus.
- Start: Desktop-Verknüpfung "MA Home" oder `dist\MA Home-win32-x64\MA Home.exe`.
- Technik: Electron. Der Chat startet per `ssh ma-server` das Claude Code auf dem Server (`~/.local/bin/claude -p`, Streaming). Kein Schlüssel in der App, keine offene Server-Schnittstelle, nur dein SSH-Zugang.
- Rechte: "Nur lesen" (Lesen, Suchen, harmlose Befehle wie ls, df, journalctl) oder "Notizen bearbeiten" (zusätzlich Edit/Write im gewählten Ordner). Kein sudo, Claude hat kein Root.
- Modelle: Sonnet (Standard), Haiku (sparsam), Opus.
- Erste Einrichtung: einmal `ssh -t ma-server "~/.local/bin/claude"` und anmelden.
- Bauen: `npm install` und `npm run pack`. Chats liegen lokal in `%APPDATA%\ma-home-desktop\chats.json`.
- Läuft nur im Heimnetz oder mit SSH-Zugang von außen (noch nicht eingerichtet).
