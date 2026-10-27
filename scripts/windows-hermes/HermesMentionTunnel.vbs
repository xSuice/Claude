' Hermes Mention-Tunnel Autostart (KIMI SOLO 2026-10-26, selbstheilend seit 2026-10-27)
' Baut den SSH-Reverse-Tunnel ma-server:8484 -> PC:8484 fensterlos auf und baut ihn nach jedem Abbruch
' (Netz weg, ServerAlive-Timeout, Server-Neustart) nach 20 s neu auf. Vorher lief ssh nur einmal pro Login.
' Verifikation (auf ma-server): curl http://127.0.0.1:8484/healthz -> {"ok": true}
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run "ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R 127.0.0.1:8484:127.0.0.1:8484 ma-server", 0, True
  WScript.Sleep 20000
Loop
