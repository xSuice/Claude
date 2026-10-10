# Sicherung der Wissensdaten des Obsidian-Vaults (ohne Medien und Exporte).
# Aufruf: powershell -File vault-backup.ps1
# Ziel: C:\Users\andre\VaultBackup\notes-<Datum>. Bestehende Sicherungen werden nie gelöscht.
$src = "C:\Users\andre\Documents\Obsidian Vault"
$dst = "C:\Users\andre\VaultBackup\notes-" + (Get-Date -Format "yyyyMMdd")
New-Item -ItemType Directory -Force -Path $dst | Out-Null
# 1. Gedächtnis komplett (inkl. Archive, raw, Dienste)
robocopy "$src\_Claude-Memory" "$dst\_Claude-Memory" /E /NFL /NDL /NJH /NJS /NP | Out-Null
# 2. Alle Notizen außerhalb davon (nur .md, .canvas, .base) und Obsidian-Einstellungen
robocopy $src "$dst\notes" *.md *.canvas *.base /S /XD "_Claude-Memory" ".git" "node_modules" /NFL /NDL /NJH /NJS /NP | Out-Null
robocopy "$src\.obsidian" "$dst\.obsidian" /E /NFL /NDL /NJH /NJS /NP | Out-Null
$n = (Get-ChildItem $dst -Recurse -File | Measure-Object).Count
$mb = [math]::Round((Get-ChildItem $dst -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Output "Sicherung fertig: $dst, $n Dateien, $mb MB"
