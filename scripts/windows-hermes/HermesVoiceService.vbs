' MA-HOME lokaler Sprachdienst (STT faster-whisper, TTS Piper Thorsten emotional) auf 127.0.0.1:18790, startet nach Absturz neu
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run """C:\Users\andre\AppData\Local\hermes\voice\venv\Scripts\pythonw.exe"" ""C:\Users\andre\AppData\Local\hermes\voice\ma_voice_service.py""", 0, True
  WScript.Sleep 15000
Loop
