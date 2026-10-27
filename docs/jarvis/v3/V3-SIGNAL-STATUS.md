# Signal-Anbindung — verifizierter Stand

Owner-Auftrag: Signal statt ntfy, danach offene Arbeiten weiterführen.

## Erledigt
- Server ist x86_64; nativer signal-cli 0.14.9 scheitert mit `CPU ISA level is lower than required`.
- Alternative installiert, ohne System-Java oder aktive Dienste zu ändern: Temurin JRE 25.0.5+8 und signal-cli 0.14.9 JVM unter `/home/andrew/.local/share/ma-jarvis/signal/`.
- Downloads gegen veröffentlichte SHA256-Werte geprüft. Java: `6fac98f0c8202efc3135a9e9e42aa61963ec42d1c5cbb40caf231e7b14a24ef6`; CLI JVM: `c32b87f587198cbd277c9d71228716ee6047ee2b63e8e88728e8280d9407d65a`.
- `java -version`, `signal-cli --version`, `link --help`, `send --help` und `listAccounts` mit Exit 0 ausgeführt. Noch kein Konto registriert.
- Launcher mit Heaplimit 256 MiB; das ist KEIN Limit für den gesamten Prozessspeicher.
- Ausgangsadapter vorbereitet: feste Selbst-Adresse, `--note-to-self --notify-self --message-from-stdin`, kein Shell-Aufruf, Timeout 90 s, keine Nachrichten im Fehlerprotokoll. Zwei Adaptertests lokal und auf dem Server bestanden; zusammen mit vorhandenen Meldungsplaner-Tests lokal 12 Tests bestanden. Mock-Tests am subprocess-Rand beweisen NICHT Versand/Handy-Push.

## Noch offen — nicht als fertig melden
- Owner muss QR-Verknüpfung in Signal bestätigen. Dadurch erhält der Server einen verknüpften Gerätezugang zum Konto (nicht bloß eine Sendeberechtigung).
- Echte Testnachricht samt Signal-Sendeergebnis und Sichtbarkeit/Push am Handy.
- Erst danach den bestehenden Meldungs-Cron auf Signal umstellen. Bis dahin bleibt ntfy unverändert; keine doppelte Zustellung einrichten.
- Regelmäßiger Empfang für Protokoll-/Gruppenupdates muss vor Regelbetrieb qualifiziert werden; kein Einlesen von Chats in ein Modell und keine Befehlsausführung durch empfangene Nachrichten.
- Die tatsächliche Push-Wirkung von `--notify-self` ist am Handy ungeprüft. Keine garantierte Push-Zustellung allein aus dem CLI-Schalter ableiten.

## Neu überprüfte übrige Punkte
- ma-home-web, ma-claude-bridge, jarvis-watchdog aktiv.
- Drucker 192.168.0.198:631 weiterhin nicht erreichbar (3-s-Probe Exit 124).
- Serverrepo ohne Änderungen zum Zeitpunkt der Prüfung.
- Frühere Vollständigkeitsbehauptungen waren zu weitgehend: Signal, reale Handy-Abnahme, Wakeword, Windows-Sandbox und vollständiger Soll-Ist-Abgleich bleiben offen. Frühere Testzahlen sind historische Nachweise, keine heutige Wiederholungsprüfung.

## Nachtrag — Signal-Dialog vorbereitet, Mikrofonbefund offen
- Owner hat Empfang der Texttestnachricht bestätigt.
- `ma-jarvis-signal.service` installiert/aktiviert: systemd, User andrew, Loopback 18769, Hardening, MemoryMax 512M, keine Chat-Inhalte auf stdout. Health 200.
- `HermesSignalTunnel.vbs` im User-Startup eingerichtet/gestartet. Lokaler Port muss wie am Server **18769** sein: RPC auf umgebogenem Port 28769 lieferte HTTP 421 (Host-Pinning); gleicher Port liefert Health 200 und akzeptiert RPC.
- Aktives Profil kimi-supervisor `.env` vorbereitet: SIGNAL_HTTP_URL, eigenes Account als einzige Allowlist, Gruppen leer, allow-all false, Stories ignorieren. Backup `.env.bak-vor-signal-chat`. Keine anderen Profile geändert.
- Test-WAV mit lokalem Piper erzeugt und per JSON-RPC als data:audio/wav;base64 an sich selbst gesendet (notifySelf/voiceNote). Akzeptierter Timestamp 1793113812877. Owner-Empfang der Audio-Nachricht noch nicht bestätigt.
- Automatischer Dialogempfang im bestehenden Hermes-Gateway ist **noch nicht aktiviert/verifiziert**. Laufender Gateway benötigt Einlesen der neuen Plattformkonfiguration; Gateway-Selbstneustart aus diesem Agentenkontext gesperrt, nicht umgehen.
- Mediengrenze: installierter Hermes-Adapter sendet lokale Dateipfade als Signal-Anhänge. Da Hermes auf Windows und signal-cli auf Linux läuft, funktionieren diese Pfade nicht direkt. Der manuelle Audio-Test nutzt Data-URI; automatische Medienroute braucht eine sauber getestete Umsetzung, bevor sie als fertig gilt.
- Mikrofon mobil: öffentliche HEAD-Abfrage auf `/` liefert 302 zur Anmeldung mit `microphone=()`. Interner authentifizierter Portal-GET liefert 200 ohne Permissions-Policy. Die Header-Sperre ist bisher nur für Login bewiesen, **keine nachgewiesene Ursache für das eingeloggte Portal**. Kein Header auf Verdacht geändert. Handytyp/Browser/exakter Fehler fehlen noch.

## Weiterer Nachtrag — qualifizierter Signal-Adapter
- Laufender Gateway hat die Signal-Verbindung inzwischen ohne Prozessneustart hergestellt: Log `Signal: connected to http://127.0.0.1:18769`. Frühere Aussage, dass dazu zwingend ein Neustart nötig sei, war falsch; Verbindungs-Reconciliation nahm die korrigierte Profilkonfiguration auf.
- Profil-Plugin `plugins/ma-signal-self` erstellt und enabled, Plugin Doctor erfolgreich: wiederverwendet den eingebauten SignalAdapter, begrenzt Intake zusätzlich auf eigene syncMessage/Notiz-an-mich ohne Gruppen und wandelt lokale Anhänge vor RPC in Data-URIs um (10 MiB Gesamtlimit, Fehler bei fehlender Datei). Drei Policytests grün.
- Echter Test des neuen Adapter-Codes ohne parallelen Empfänger: lokale WAV-Datei über Adapter._rpc an entfernten Signal-Daemon geschickt, Versand akzeptiert, Timestamp 1793115144555. Kein bloßer Mock für den Medientransport.
- Einschränkung: `plugins enable` re-wired Handler, ersetzt laut `gateway/run_plugin_rewire.py` aber keine bereits vorhandene Adapterinstanz. Damit ist die neue Klasse nicht als live angenommen. Ein externer Gateway-Neustart lädt die neue Factory; danach echte eingehende Notiz und Echo-/Audio-Test erforderlich. Keine Selbstneustart-Sperre umgehen. Bereits laufender nativer Adapter hat Owner-Allowlist und Gruppen aus, aber noch nicht die zusätzliche Filter-/Media-Klasse.

## Signal-Meldungen und lokale Transkription — umgesetzt
- Bestehender `/opt/jarvis/council/jarvis_notify.py`-Cron sendet jetzt über neuen `signal_push.py` an das eigene Konto statt ntfy. Planner, Zeitplan und Zustandsdatei bleiben gleich. Vorher/nachher SHA der Zustandsdatei beim Wechsel identisch: `862d182e98199770df00a51aa30bdc01d162659aad616e07da42758a7d6ac378`.
- Servertests: 12 Tests OK; Dry-run keine ausstehenden Meldungen; echter Testversand über diesen Wrapper akzeptiert (1793115611944). Spätere Cron-Ausführung am aktualisierten Dateizeitstempel belegt. Rollback: `jarvis_notify.py.bak-vor-signal-push` zurückkopieren, kein Service-Neustart erforderlich. ntfy selbst und seine Konten noch nicht entfernt.
- Statusmeldungen tragen `[JARVIS-MELDUNG]`; Zusatzadapter ignoriert diese als Aufträge (regressionstest erst rot, dann grün, insgesamt vier Policytests). Die neue Adapterklasse ist weiter nicht als laufende Instanz belegt.
- faster-whisper 1.2.1 in isolierter Voice-venv, Modell base multilingual, CPU int8, zwei Threads/ein Worker. Datenverarbeitung lokal, kein Cloud-STT-Konto eingerichtet.
- PyAV 19.0.2 ist inkompatibel mit faster-whisper 1.2.1 (`metadata_errors` entfernt); av==16.1.0 löst den reproduzierten Fehler. Lockdatei aktualisiert.
- `whisper_transcribe.py INPUT OUTPUT` unter dauerhaftem Voice-Verzeichnis. Synthetischer Piper-Audiotest bestanden. Zusätzlich echter Hermes-Aufruf `tools.transcription_tools.transcribe_audio`: success=True, provider=jarvis-local, erwartete Wörter erkannt. Kein Test mit echter Handyaufnahme.
- Profilkonfiguration per `hermes config set stt` aktualisiert, Backup `config.yaml.bak-vor-local-stt`; Timeout 120s. Nur ein Standardwert wurde neu gesetzt, bestehende stt-Konfiguration war nicht gesetzt. Audio-/Transkriptpersistenz entspricht weiterhin Hermes; keine automatische Löschung zugesagt.

## Rückbau
Dialogempfang ist noch nicht aktiviert, aber ein eigener Daemon und User-Startup-Tunnel sind aktiv. Rückbau: `sudo systemctl disable --now ma-jarvis-signal.service`, Startup-Datei `HermesSignalTunnel.vbs` entfernen und nur ihren Tunnelprozess beenden, Signal-Konfiguration im Profil aus Backup zurücknehmen. In der Signal-App das Gerät `MA-HOME JARVIS` entfernen. Anschließend das isolierte Signal-Verzeichnis nach Bedarf löschen. Bestehender Benachrichtigungs-Cron und Portal bleiben unberührt.
