$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Time-Cmd([string]$title, [scriptblock]$block) {
    Write-Host "=== $title ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $block
    $sw.Stop()
    $sec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    Write-Host ("SEC=" + $sec)
    Write-Host ""
    return $sec
}

Write-Host ("abc.exe mtime=" + (Get-Item abc.exe).LastWriteTime)
Write-Host ("abassembler.exe mtime=" + (Get-Item abassembler.exe).LastWriteTime)
Write-Host ""

# 1) pointer-to-Type smoke
Time-Cmd "abc t_ptrfield.abp" {
    if (Test-Path _t_ptrfield.asm) { Remove-Item _t_ptrfield.asm -Force }
    & .\abc.exe t_ptrfield.abp _t_ptrfield.asm 2>&1 | ForEach-Object { Write-Host $_ }
    if (Test-Path _t_ptrfield.asm) {
        Write-Host ("asm_bytes=" + (Get-Item _t_ptrfield.asm).Length)
        & .\abassembler.exe _t_ptrfield.asm _t_ptrfield.obj 2>&1 | ForEach-Object { Write-Host $_ }
    }
}

# 2) full self-compile via abpc
Time-Cmd "abpc abc2.pj (full self-compile)" {
    & .\abpc.exe abc2.pj 2>&1 | Tee-Object -FilePath abc2_rebuild_timing.log | ForEach-Object { Write-Host $_ }
}

if (Test-Path abc2_combined.abp) {
    Write-Host ("combined_bytes=" + (Get-Item abc2_combined.abp).Length)
}
if (Test-Path abc2_combined.asm) {
    $asm = Get-Item abc2_combined.asm
    Write-Host ("asm_bytes=" + $asm.Length + " mtime=" + $asm.LastWriteTime)
    $db0 = @(Select-String -LiteralPath abc2_combined.asm -Pattern "^\s+db 0\s*$").Count
    $times = @(Select-String -LiteralPath abc2_combined.asm -Pattern "^\s+times\s+").Count
    Write-Host ("db0_lines=" + $db0 + " times_lines=" + $times)
}
if (Test-Path abc2_combined.obj) {
    Write-Host ("obj_bytes=" + (Get-Item abc2_combined.obj).Length)
}
if (Test-Path abc2.exe) {
    Write-Host ("abc2.exe bytes=" + (Get-Item abc2.exe).Length + " mtime=" + (Get-Item abc2.exe).LastWriteTime)
}
