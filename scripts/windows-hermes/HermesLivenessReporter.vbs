' Hermes Liveness-Reporter Autostart (KIMI SOLO 2026-10-27, selbstheilend)
' Meldet Gateway-Liveness der Hermes-Profile als Heartbeats an ma-server (siehe liveness_reporter.py).
' Log: %LOCALAPPDATA%\hermes\heartbeat\liveness.log
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run """C:\Users\andre\AppData\Local\hermes\installs\420129bcb3855271\environments\e4e1010201324985b3656f09c70f6c79\venv\Scripts\pythonw.exe"" ""C:\Users\andre\AppData\Local\hermes\heartbeat\liveness_reporter.py""", 0, True
  WScript.Sleep 30000
Loop
