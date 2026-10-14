# Conservative migration installer: no changes unless -Apply. Never overwrites existing MCP.
[CmdletBinding()]
param(
  [string]$Config = "",
  [switch]$Apply,
  [switch]$Demo,
  [switch]$InstallSkill
)
$ErrorActionPreference = 'Stop'
$runtime = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = (Resolve-Path (Join-Path $runtime '..')).Path
if ($Demo -and $Config) { throw 'Choose either -Demo or -Config, not both' }
if (-not $Config) {
  if (-not $Demo) { throw 'Provide a trusted -Config or explicitly use -Demo' }
  $Config = Join-Path $runtime 'config.v5.demo.json'
}
$cfgPath = (Resolve-Path -LiteralPath $Config).Path
$cfg = Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json
if (-not $cfg.identity -or -not $cfg.allowed_projects -or -not $cfg.state_db) {
  throw 'Config must include identity, allowed_projects, state_db'
}
if ($cfg.source -and $cfg.source -match 'fixtures' -and -not $Demo) {
  throw 'Synthetic fixture data only allowed with -Demo'
}
$python = (Get-Command python -ErrorAction Stop).Source
$claude = (Get-Command claude -ErrorAction Stop).Source
& $python -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if ($LASTEXITCODE -ne 0) {throw 'Python 3.10+ required'}
& $python -m unittest discover -s (Join-Path $runtime 'tests') -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Nothing changed.' }
$listing = (& $claude mcp list 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect existing MCP registrations' }
$name='claude-local-brain'
if ($listing -match '(?mi)^\s*claude-local-brain\s*:') {
  throw 'An existing Claude Brain is registered. Do NOT run V4 and V5 simultaneously. Inspect, back up, then consciously migrate.'
}
$server=Join-Path $runtime 'mcp_server_v5.py'
Write-Host "Python: $python"
Write-Host "Server: $server"
Write-Host "Config: $cfgPath"
Write-Host 'Existing MCP registrations will NOT be changed.'
if (-not $Apply) {
  Write-Host 'DRY-RUN: add -Apply to register. Optional -InstallSkill adds a project-local skill.'
  exit 0
}
& $claude mcp add --scope local --transport stdio $name -- $python -u $server --config $cfgPath
if ($LASTEXITCODE -ne 0) {throw 'MCP registration failed'}
if ($InstallSkill) {
  $sourceSkill = Join-Path $root '.claude\skills\cognitive-brain\SKILL.md'
  $destSkill = Join-Path (Get-Location).Path '.claude\skills\cognitive-brain\SKILL.md'
  if (Test-Path -LiteralPath $destSkill) {
    Write-Warning 'Skill already exists, not overwriting. MCP server was registered.'
  } else {
    New-Item -ItemType Directory -Force -Path (Split-Path $destSkill) | Out-Null
    Copy-Item -LiteralPath $sourceSkill -Destination $destSkill
    Write-Host "Installed project skill: $destSkill"
  }
}
Write-Host "Added MCP. Verify with: claude mcp get $name  (then /mcp inside Claude)"
Write-Host "Rollback registration: claude mcp remove $name"
