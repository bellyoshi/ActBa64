$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$sources = @(
    "Utils.abp",
    "Common.abp",
    "FileIO.abp",
    "StringBuffer.abp",
    "abcGlobals.abp",
    "abcLexer.abp",
    "abcParser.abp",
    "abcEmit.abp",
    "abc.abp"
)

function Strip-Includes([string]$text) {
    $out = New-Object System.Text.StringBuilder
    foreach ($line in ($text -split "`r?`n", -1)) {
        if ($line -notmatch '^\s*#include\b') {
            [void]$out.AppendLine($line)
        }
    }
    return $out.ToString()
}

$all = New-Object System.Text.StringBuilder
foreach ($s in $sources) {
    if (-not (Test-Path $s)) { throw "missing $s" }
    [void]$all.AppendLine("' ---- $s ----")
    $raw = [System.IO.File]::ReadAllText((Resolve-Path $s).Path)
    [void]$all.Append((Strip-Includes $raw))
}
[System.IO.File]::WriteAllText("$PWD\abc2_combined.abp", $all.ToString())
Write-Host ("abc.exe mtime=" + (Get-Item abc.exe).LastWriteTime)
Write-Host ("combined_bytes=" + (Get-Item abc2_combined.abp).Length)

if (Test-Path abc2_combined.asm) { Remove-Item abc2_combined.asm -Force }
if (Test-Path abc2_combined.obj) { Remove-Item abc2_combined.obj -Force }
if (Test-Path abc2.exe) { Remove-Item abc2.exe -Force }

Write-Host "=== abc ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
& .\abc.exe abc2_combined.abp abc2_combined.asm 2>&1 | ForEach-Object { Write-Host $_ }
Write-Host ("ABC_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))
if (-not (Test-Path abc2_combined.asm)) { throw "no asm" }
Write-Host ("asm_bytes=" + (Get-Item abc2_combined.asm).Length)

$bad = @(Select-String -LiteralPath abc2_combined.asm -Pattern 'call _gVarIsStr|call _gConstVal|call _gVarCount|call _gVarSize|call _Right\$')
if ($bad.Count -gt 0) {
    Write-Host "BAD_REFS:"
    $bad | Select-Object -First 15 | ForEach-Object { Write-Host ($_.LineNumber.ToString() + ": " + $_.Line) }
    throw "still has fake calls"
}
Write-Host "no fake array/Right calls"

Write-Host "=== abassembler ==="
$sw.Restart()
& .\abassembler.exe abc2_combined.asm abc2_combined.obj 2>&1 | ForEach-Object { Write-Host $_ }
Write-Host ("AS_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))
if (-not (Test-Path abc2_combined.obj)) { throw "no obj" }

Write-Host "=== ablinker ==="
$sw.Restart()
& .\ablinker.exe abc2_combined.obj abc2.exe 2>&1 | ForEach-Object { Write-Host $_ }
Write-Host ("LINK_SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))
if (Test-Path abc2.exe) {
    Write-Host ("OK abc2.exe bytes=" + (Get-Item abc2.exe).Length + " mtime=" + (Get-Item abc2.exe).LastWriteTime)
} else {
    throw "link failed: no abc2.exe"
}
