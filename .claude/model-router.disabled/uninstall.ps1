$ErrorActionPreference = "Stop"

$RouterDir = "C:\Users\andre\Documents\MA-Server\.claude\model-router"

$Begin = "# BEGIN CLAUDE MODEL ROUTER"
$End   = "# END CLAUDE MODEL ROUTER"

if (Test-Path $PROFILE) {

    $Content = Get-Content $PROFILE -Raw

    $Pattern = "(?s)\r?\n?" +
        [regex]::Escape($Begin) +
        ".*?" +
        [regex]::Escape($End) +
        "\r?\n?"

    $Content = [regex]::Replace(
        $Content,
        $Pattern,
        "`r`n"
    )

    Set-Content `
        -Path $PROFILE `
        -Value $Content `
        -Encoding UTF8
}

$Wrapper = Join-Path $env:USERPROFILE "cr.cmd"

if (Test-Path $Wrapper) {
    Remove-Item $Wrapper -Force
}

if (Test-Path $RouterDir) {
    Remove-Item $RouterDir -Recurse -Force
}

Write-Host ""
Write-Host "Claude Model Router wurde entfernt."
Write-Host ""
