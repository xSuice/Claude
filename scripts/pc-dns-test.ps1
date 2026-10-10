# MA Home: DNS-Test an EINEM Windows-Client (Adapter "Ethernet"). Router/DHCP bleiben unveraendert.
# Als Administrator ausfuehren (PowerShell "Als Administrator"):
#   .\pc-dns-test.ps1            -> setzt DNS 192.168.0.111, testet, stellt bei Fehler selbst zurueck
#   .\pc-dns-test.ps1 -Restore   -> stellt den gesicherten Zustand wieder her
# Sicherung: ..\server-snapshot\pc-dns-backup.json (enthaelt keine Geheimnisse)
param([switch]$Restore)
$ErrorActionPreference = 'Stop'
$Alias   = 'Ethernet'
$Blocky  = '192.168.0.111'
$Domain  = 'ma-server.duckdns.org'
$Backup  = Join-Path $PSScriptRoot '..\server-snapshot\pc-dns-backup.json'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Bitte PowerShell als Administrator starten.'
}
if (-not (Test-Path $Backup)) { throw "Sicherung fehlt: $Backup" }
$saved = Get-Content $Backup -Raw | ConvertFrom-Json

function Get-Servers {
    (@(Get-DnsClientServerAddress -InterfaceAlias $Alias -AddressFamily IPv4 | ForEach-Object ServerAddresses) -join ',')
}

function Restore-Dns {
    if ($saved.mode -eq 'manual') {
        Set-DnsClientServerAddress -InterfaceAlias $Alias -ServerAddresses @($saved.dns_v4)
    } else {
        Set-DnsClientServerAddress -InterfaceAlias $Alias -ResetServerAddresses
    }
    ipconfig /flushdns | Out-Null
    $now = Get-Servers
    $want = ($saved.dns_v4 -join ',')
    if ($saved.mode -eq 'manual' -and $now -ne $want) { throw "Wiederherstellung weicht ab: ist '$now', soll '$want'" }
    Write-Host "DNS wiederhergestellt: $now (Modus: $($saved.mode))"
}

if ($Restore) { Restore-Dns; return }

Write-Host "Ist-Zustand: $(Get-Servers) | gesichert: $($saved.dns_v4 -join ',') ($($saved.mode))"
if ((Get-Servers) -ne ($saved.dns_v4 -join ',') -and (Get-Servers) -ne $Blocky) {
    throw 'Aktuelle DNS-Einstellung weicht von der Sicherung ab. Nichts geaendert; Sicherung pruefen.'
}

# Vorbedingung: Blocky antwortet richtig, sonst nichts aendern.
$r = Resolve-DnsName $Domain -Server $Blocky -Type A -DnsOnly
if ($r.IPAddress -notcontains $Blocky) { throw "Blocky liefert fuer $Domain nicht $Blocky - Abbruch, nichts geaendert." }
Write-Host "Blocky-Vorpruefung OK ($Domain -> $($r.IPAddress -join ','))"

$ok = $false
try {
    Set-DnsClientServerAddress -InterfaceAlias $Alias -ServerAddresses $Blocky
    ipconfig /flushdns | Out-Null
    Start-Sleep -Seconds 2
    # Systemresolver (ohne -Server): so loest auch der Browser auf
    $sys = Resolve-DnsName $Domain -Type A
    if ($sys.IPAddress -notcontains $Blocky) { throw "Systemresolver liefert $($sys.IPAddress -join ',')" }
    Resolve-DnsName 'example.com' -Type A | Out-Null
    Write-Host 'Systemresolver: Domain intern + externer Name OK'
    # HTTPS ohne --resolve und ohne -k (Zertifikat wird geprueft)
    foreach ($h in $Domain, "ha.$Domain") {
        $out = & curl.exe -s -m 10 -o NUL -w '%{http_code} %{ssl_verify_result} %{redirect_url}' "https://$h/"
        Write-Host "https://$h/ -> $out"
        if ($out -notmatch ('^302 0 https://' + [regex]::Escape($Domain) + '/auth/')) { throw "Unerwartete Antwort fuer $h" }
    }
    $ok = $true
} catch {
    Write-Host "TEST FEHLGESCHLAGEN: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if (-not $ok) { Restore-Dns }
}
if ($ok) {
    Write-Host "ERFOLG. DNS bleibt vorerst auf $Blocky (fuer den Login-Test im Browser)." -ForegroundColor Green
    Write-Host 'Zurueck: .\pc-dns-test.ps1 -Restore'
}
