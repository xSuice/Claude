# V3 – Lokale Sprache, Signal-Dialog und Windows-Worker (27.10.2026, Abend)

Belegter Stand nach Owner-Rückmeldung „1. ja 2. geht nicht, 3. Spracherkennung: network, 4. thorsten emotional, windows worker freigeben, schlüssel habe ich doch schon“.

## 1. Signal-Dialog – Ursache gefunden und behoben (Text)

**Befund (Gateway-Log):** Die Nachricht „Hallo Jarvis antworte mir“ kam an (`inbound message: platform=signal`). Jeder Lauf scheiterte jedoch mit `HTTP 400: kimi-for-coding is not a valid model ID`: Das Profil `kimi-supervisor` hatte `model: kimi-for-coding` ohne Provider, deshalb nutzte das Gateway OpenRouter. Auf dem Handy kam nur die Fehlermeldung „Your request was not processed…“ an.

**Fix:** In `config.yaml` steht jetzt `model: {default: kimi-for-coding, provider: kimi}` (Backup `config.yaml.bak-vor-signal-model-20261027`). Prüfung: direkter Provider-Aufruf HTTP 200, `hermes -p kimi-supervisor chat -q …` antwortet „Signal-Modelltest OK“. Das Gateway hat die Profiländerung neu eingelesen (`Re-scanned profile 'kimi-supervisor'`).

**Push-Hinweis:** Antworten an das eigene Konto setzen jetzt `notifySelf` (Plugin `ma-signal-self`, Policytest 4/4 grün). So soll das Handy benachrichtigen statt die Antwort still einzusortieren. Diese Plugin-Änderung wird erst nach dem nächsten Gateway-Neustart geladen.

**Offen:** Echte neue Nachricht vom Handy nach dem Fix. Ich habe keine Nachricht im Namen des Handys eingespeist.

## 2. Wakeword/Spracherkennung – „Spracherkennung: network“

**Ursache:** Brave hat keinen Zugang zum Google-Spracherkennungsdienst. Die Web-Speech-API meldet dort `network`. Das passt zu MDN, wonach die Erkennung in einigen Browsern serverbasiert ist (siehe Deepsearch).

**Lösung: eigene, lokale Sprachstrecke (umgesetzt, live im Portal)**
- PC-Dienst `ma_voice_service.py` (127.0.0.1:18790, Token-Pflicht, ein Auftrag gleichzeitig, Priorität BELOW_NORMAL, keine Audio-/Textinhalte im Log). STT: faster-whisper `base` int8 mit `hotwords='Jarvis'`. TTS: Piper **Thorsten emotional (medium), Sprecher 0**; der Datensatz ist laut Model Card CC0. Autostart über `HermesVoiceService.vbs` und den Reverse-Tunnel `HermesVoiceTunnel.vbs` (ma-server 127.0.0.1:18790).
- Portal-API `/api/voice/{health,stt,tts}` (Blueprint `jarvis_voice.py`, nur Admin, gleiche Authelia-/CSRF-Regeln). Das Audio wird als JSON/Base64 übertragen, weil `portal.py` nur JSON-POSTs zulässt. Die globale Grenze von 128 KiB bleibt unverändert. Ist der PC aus, antwortet die API mit 503 und das Portal fällt auf den Browser zurück.
- Portal `js/localvoice.js`: Mikrofonpegel in dBFS, Sprachsegmentierung mit Kalibrierung auf das Raumrauschen, Sprechende relativ zur eigenen Lautstärke und angehobener Schwelle bei Dauergeräuschen. Der Recorder läuft vor dem Sprechbeginn mit, damit der Anfang nicht abgeschnitten wird. Opus 24 kbit/s. Die Wiedergabe läuft über Web Audio, der nächste Satz wird bereits vorab erzeugt. Der Browserdienst ist nur noch Fallback; bei `network` wechselt das Portal automatisch auf die lokale Strecke.
- Einwilligungstext für den lokalen Betrieb angepasst: Audio geht nur an den eigenen PC.

**Tests:** Node 18/18 (Segmenter, dB-Pegel, Dialogfenster, Satzausgabe), Server-Proxy 5/5, PC-Dienst 4/4 (inkl. echter TTS→STT-Strecke).
Browser-E2E mit **synthetischem Mikrofon** (Piper-Audio und Rauschen in einen MediaStream; keine echte Person, kein echtes Mikrofon):
- „Hey Jarvis, wie spät ist es?“ → erkannt, lokale Antwort nach ca. 4,5 s gesprochen.
- Folgefrage ohne Wakeword „Welche Aufgaben sind offen?“ → beantwortet, ca. 4 s.
- Nach Ablauf des 12-s-Fensters wurde ein Satz ohne Wakeword ignoriert.
- „Hey Jarvis, erzähl mir … Minecraft“ → Modellantwort (haiku) in natürlicher Sprache, mit lokaler Stimme vorgelesen. Rund 9,6 s davon entfallen auf den Modellaufruf.

**Grenzen:** Ein satzinitiales „Jarvis“ der synthetischen Stimme wurde teils als „Ja, bis“ erkannt; „Hey Jarvis“ bzw. „Okay Jarvis“ zuverlässiger. Mit echter Stimme ist das noch nicht gemessen. Während JARVIS spricht, ist das Mikrofon pausiert (kein Selbstecho); Unterbrechen per „Stopp“-Knopf. Die APK bzw. das Mikrofon in Android-WebViews ist weiterhin zurückgestellt.

## 3. Stimme

Owner-Wahl **Thorsten emotional** ist umgesetzt für Portal (lokal) und Hermes-TTS (`piper_say.py`, Backup `.bak-vor-emotional`).

## 4. Windows-Worker – freigegeben und qualifiziert

**Ursache 0x80070005:** Der Ordner `%LOCALAPPDATA%\Packages` hatte keine geschützte Profil-ACL; er erbte die Laufwerks-ACL, wie das gesamte Benutzerprofil `C:\Users\andre`. Nach geschützter ACL auf `Packages` (Owner, SYSTEM, Administratoren; Sicherung `packages-acl-backup-20261027.txt`) erstellt Windows das AppContainer-Profil.

**Zweiter Fehler (CreateProcess 87):** Dieser Windows-Build (10.0.26300) lehnt die Fähigkeit `isolatedWin32-volumeRootMinimal` ab. `winsandbox.py` erkennt das und läuft ohne sie weiter, also strenger. Für Java (`getNameMax` auf C:\) bekam **nur der Container-SID** auf **C:\ selbst** `(S,RD,X,RA)` ohne Vererbung, per UAC (Sicherung `c-root-acl-vor-pcworker.txt`).

**Qualifizierung 7/7:** Low Integrity, Schreiben nur im Arbeitsordner, Canary außerhalb unlesbar, Schreiben außerhalb verweigert, Loopback **und Internet** blockiert, Zeitlimit greift. Repo-Tests `test_winsandbox`: 13 bestanden, 3 übersprungen, 2 Umgebungsfehler (die Tests suchen `java`/`javac` im System-PATH; das JDK liegt benutzerlokal). `pc-report`: `java.build` = **tested** (Selbsttest-Build im Sandbox).

**Installiert:** Temurin JDK 21.0.12.1 (Checksumme geprüft, benutzerlokal `%LOCALAPPDATA%\ma-jarvis\jdk-21`), Client `%LOCALAPPDATA%\ma-jarvis\client`, Freigabe `~/.claude/state/jarvis-pc.json` = nur `java.build`, **ohne Netz**. Autostart `JarvisPcWorker.vbs` (Log `%LOCALAPPDATA%\ma-jarvis\pc-worker.log`).

**E2E-Nachweis:** Gradle 9.8.2 einmal checksum-verifiziert in `%LOCALAPPDATA%\ma-jarvis\gradle-home` geseedet (`seed_gradle.py`, Offline-Builds im Sandbox). Aufgabe „Hallo.java zu JAR kompilieren“ wurde vollständig durchlaufen: Server plant (haiku), PC-Worker baut **im Sandbox offline** (Spitze 116 MB, 2 Prozesse, <1 s), Server nimmt ab: **2/2 Ergebnisdateien bestanden die unabhängige Abnahme**, Job `j20261027-14c029` = ERLEDIGT (alles geprüft). Abgeholt nach `Documents\JARVIS-Ergebnisse\j20261027-14c029`; die JAR läuft lokal: Ausgabe „Hallo von JARVIS“.

**Lehre für Pläne:** Die Abnahme prüft nur Dateien, die der Plan als `deliverables` nennt. Ein Plan, der die JAR „liefert“ ohne sie als Deliverable zu deklarieren, scheitert mit `0/1 ... unabhängige Abnahme`, obwohl der Build ok war (erster Lauf `j20261027-8351b5`).

**Nebenbefund Sicherheit:** Das Profil `C:\Users\andre` erbt die Laufwerks-ACL („Benutzer: Lesen“, „Authentifizierte Benutzer: Ändern“). Andere lokale Konten können das Profil daher lesen bzw. ändern. Eine Reparatur des ganzen Profils ist eine eigene Owner-Entscheidung und wurde nicht durchgeführt.

**Rückbau:** `icacls C:\ /remove *S-1-15-2-2463243902-2450264064-2423113111-2866411314-72383083-2064497059-1182243265` (Admin), `icacls %LOCALAPPDATA% /restore packages-acl-backup-20261027.txt`, `JarvisPcWorker.vbs` löschen, `jarvis-pc.json` löschen.

## 5. Schlüssel (nexum)

Der vom Owner früher eingefügte Schlüssel hat denselben Fingerabdruck wie der in allen 18 Profilen hinterlegte (`f790b2d10158…`). Der Anbieter nimmt ihn an (`/models` HTTP 200). Damit ist nichts mehr zu tauschen. Hinweis: Der Schlüssel stand im Chat, eine spätere Rotation bleibt empfehlenswert.

Jarvis: Phase B – Signal-Fehlerursache behoben, lokale Sprache + Worker live und getestet (synthetisch) – nächster Schritt: echte Signal-Nachricht und echter Sprachtest mit „Hey Jarvis“ durch den Owner.
