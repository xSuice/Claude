# Add a *single*, read-only stdio MCP server to Claude Code's LOCAL scope.
# Default is dry-run. Requires -Apply. Never modifies existing MCP entries.
[CmdletBinding()]
param(
  [string]$Config = "",
  [switch]$Apply,
  [switch]$Demo
)
$ErrorActionPreference = 'Stop'
$runtime = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$package = (Resolve-Path (Join-Path $runtime '..')).Path
if (-not $Config) {
  if (-not $Demo) { throw 'Provide -Config <absolute path to your own trusted config> or -Demo for synthetic data.' }
  $Config = Join-Path $runtime 'config.demo.json'
}
$cfgPath = (Resolve-Path $Config).Path
$settings = Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json
if (-not $settings.identity -or -not $settings.allowed_projects -or -not $settings.source) {
  throw 'Missing identity, allowed_projects, or source'
}
if ($settings.source -like '*fixtures*' -and -not $Demo) {
  throw 'Synthetic fixture requires -Demo; use your authorized knowledge export for real use.'
}
$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $runtime 'mcp_server.py'
$claude = (Get-Command claude -ErrorAction Stop).Source
& $python -m unittest discover -s (Join-Path $runtime 'tests') -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Aborting.' }
$serverName = 'claude-local-brain'
$servers = & $claude mcp list 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect existing MCP servers; no changes performed.' }
if ($servers -match '(?m)^\s*claude-local-brain\s*:') { throw "Existing MCP server '$serverName' found; no overwrite. Inspect with claude mcp get $serverName" }
Write-Host "Project folder: $package"
Write-Host "Read-only MCP command: $python -u $script --config $cfgPath"
if (-not $Apply) { Write-Host 'Dry run only. Add -Apply to register (no admin permissions needed).'; exit 0 }
& $claude mcp add --scope local --transport stdio $serverName -- $python -u $script --config $cfgPath
if ($LASTEXITCODE -ne 0) { throw 'Claude MCP registration failed.' }
Write-Host 'Registered. Check: claude mcp get claude-local-brain; then /mcp in Claude.'
