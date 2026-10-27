' Hermes Mention-Receiver Autostart (KIMI SOLO 2026-10-26)
' Startet den Portal-Mention-Endpunkt fensterlos beim Anmelden.
' Verifikation: http://127.0.0.1:8484/healthz -> {"ok": true}
Set sh = CreateObject("WScript.Shell")
sh.Run """C:\Users\andre\AppData\Local\hermes\installs\420129bcb3855271\environments\e4e1010201324985b3656f09c70f6c79\venv\Scripts\pythonw.exe"" ""C:\Users\andre\AppData\Local\hermes\mention-receiver\mention_receiver.py""", 0, False
Set sh = Nothing
