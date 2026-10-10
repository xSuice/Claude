# GMX-Konto fuer den lokalen MCP-Server "mcp-email-server" (Claude Code) einrichten.
# Nur lokal auf dem Windows-PC. Kein Bezug zum Heimserver.
#
# Passwort: wird ausschliesslich von mcp-email-server selbst maskiert abgefragt
# (nie als Argument, nie in Logs). Gespeichert im privaten Managed-Katalog
# %USERPROFILE%\.config\mcp-email-server\managed.sqlite3 (DACL nur Benutzer/SYSTEM/Admins).
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File .\gmx-mcp-setup.ps1

$ErrorActionPreference = 'Stop'
$exe = Join-Path $env:USERPROFILE '.local\bin\mcp-email-server.exe'
if (-not (Test-Path $exe)) { throw "mcp-email-server nicht gefunden: $exe" }

$email = (Read-Host 'GMX-Adresse (z.B. name@gmx.de)').Trim()
if ($email -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') { throw 'Ungueltige E-Mail-Adresse.' }
$fullName = (Read-Host 'Absendername (z.B. Vorname Nachname)').Trim()
if (-not $fullName) { throw 'Absendername fehlt.' }

Write-Host ''
Write-Host 'Gleich fragt mcp-email-server ZWEIMAL verdeckt nach dem Passwort:' -ForegroundColor Cyan
Write-Host '  1. IMAP (Empfang)   2. SMTP (Versand)  -> jeweils dasselbe GMX-(App-)Passwort.' -ForegroundColor Cyan
Write-Host ''

& $exe account add gmx `
    --email $email `
    --full-name $fullName `
    --imap-host imap.gmx.net --imap-port 993 --imap-user $email `
    --smtp-host mail.gmx.net --smtp-port 587 --no-smtp-ssl --smtp-starttls --smtp-user $email
if ($LASTEXITCODE -ne 0) { throw "account add fehlgeschlagen (Exit $LASTEXITCODE)." }

Write-Host ''
Write-Host 'Teste IMAP (nur Ordnerliste, liest keine Mails) ...' -ForegroundColor Cyan
& $exe account test gmx incoming
Write-Host 'Teste SMTP (nur Login + Absenderpruefung, sendet NICHTS) ...' -ForegroundColor Cyan
& $exe account test gmx outgoing

Write-Host ''
& $exe config status
Write-Host ''
Write-Host 'Fertig. Claude Code danach neu starten.' -ForegroundColor Green
