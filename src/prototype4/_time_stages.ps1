$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host ("abc.exe mtime=" + (Get-Item abc.exe).LastWriteTime)
Write-Host ("combined_bytes=" + (Get-Item abc2_combined.abp).Length)

if (Test-Path abc2_combined.asm) { Remove-Item abc2_combined.asm -Force }
Write-Host "=== abc only ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
& .\abc.exe abc2_combined.abp abc2_combined.asm 2>&1 | ForEach-Object { Write-Host $_ }
$sw.Stop()
Write-Host ("ABC_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))
if (Test-Path abc2_combined.asm) {
    Write-Host ("asm_bytes=" + (Get-Item abc2_combined.asm).Length)
    Write-Host ("db0=" + @(Select-String -LiteralPath abc2_combined.asm -Pattern '^\s+db 0\s*$').Count)
    Write-Host ("times=" + @(Select-String -LiteralPath abc2_combined.asm -Pattern '^\s+times\s+').Count)
}

if (Test-Path abc2_combined.obj) { Remove-Item abc2_combined.obj -Force }
Write-Host "=== abassembler only ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
& .\abassembler.exe abc2_combined.asm abc2_combined.obj 2>&1 | ForEach-Object { Write-Host $_ }
$sw.Stop()
Write-Host ("AS_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))
if (Test-Path abc2_combined.obj) {
    Write-Host ("obj_bytes=" + (Get-Item abc2_combined.obj).Length)
}
