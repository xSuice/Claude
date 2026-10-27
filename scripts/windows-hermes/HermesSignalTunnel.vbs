Option Explicit
Dim shell, cmd
Set shell = CreateObject("WScript.Shell")
cmd = "ssh.exe -N -L 127.0.0.1:18769:127.0.0.1:18769 -i C:/Users/andre/.ssh/hermes_mahome -o IdentitiesOnly=yes -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 andrew@ma-server"
Do
  shell.Run cmd, 0, True
  WScript.Sleep 20000
Loop
