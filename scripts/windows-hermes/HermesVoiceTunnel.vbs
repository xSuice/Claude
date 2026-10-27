' Reverse-Tunnel ma-server 127.0.0.1:18790 -> PC 127.0.0.1:18790 fuer den lokalen Sprachdienst, selbstheilend
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run "ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R 127.0.0.1:18790:127.0.0.1:18790 ma-server", 0, True
  WScript.Sleep 20000
Loop
