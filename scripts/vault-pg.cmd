@echo off
rem vault-pg am PC: Abfragen an den Vault-Index in PostgreSQL. Die Datenbank laeuft nur auf dem Server (localhost), das Passwort bleibt dort.
rem Der Aufruf geht per SSH an dasselbe Skript auf dem Server, damit PC und Server dieselben Treffer liefern. Ordner scripts in den PATH legen.
rem Beispiele: vault-pg search "begriffe" -n 5   |   vault-pg stats   |   vault-pg show "Pfad.md"
rem Voraussetzung: andrew ist auf dem Server in der Gruppe ma-web (sudo usermod -aG ma-web andrew).
python "%~dp0vault-pg-pc.py" %*
