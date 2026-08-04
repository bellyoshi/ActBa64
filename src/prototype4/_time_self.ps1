$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "=== abpc abc2.pj (combine + abc + as + link) ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
& .\abpc.exe abc2.pj 2>&1 | Tee-Object -FilePath abc2_rebuild_timing.log
$code = $LASTEXITCODE
$sw.Stop()
Write-Host ("TOTAL_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2) + " exit=" + $code)

if (Test-Path abc2_combined.abp) {
    $sz = (Get-Item abc2_combined.abp).Length
    Write-Host ("combined_bytes=" + $sz)
}
if (Test-Path abc2_combined.asm) {
    $asm = Get-Item abc2_combined.asm
    Write-Host ("asm_bytes=" + $asm.Length + " mtime=" + $asm.LastWriteTime)
}
if (Test-Path abc2_combined.obj) {
    Write-Host ("obj_bytes=" + (Get-Item abc2_combined.obj).Length)
}
if (Test-Path abc2.exe) {
    Write-Host ("abc2_exe_bytes=" + (Get-Item abc2.exe).Length + " mtime=" + (Get-Item abc2.exe).LastWriteTime)
}
