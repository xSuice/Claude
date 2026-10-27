# MA-HOME: AppContainer MA.JARVIS.PCWorker darf das Laufwerk C:\ nur auflisten/Attribute lesen (kein Vererben, kein Lesen von Dateien).
# Ersatz fuer die auf diesem Windows-Build nicht verfuegbare Faehigkeit isolatedWin32-volumeRootMinimal.
$sid = 'S-1-15-2-2463243902-2450264064-2423113111-2866411314-72383083-2064497059-1182243265'
$out = "$env:TEMP\ma_volroot_ok.txt"
# Sicherung liegt bereits vor (c-root-acl-vor-pcworker.txt)
icacls C:\ /grant "*${sid}:(S,RD,X,RA)" | Out-File -Encoding utf8 $out
"exit=$LASTEXITCODE" | Out-File -Append -Encoding utf8 $out
