$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Time-Abc([string]$src, [string]$asm) {
    if (-not (Test-Path $src)) {
        Write-Host "MISSING $src"
        return
    }
    if (Test-Path $asm) { Remove-Item $asm -Force }
    Write-Host "=== abc $src ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $out = & .\abc.exe $src $asm 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()
    $out | ForEach-Object { Write-Host $_ }
    $asmBytes = 0
    if (Test-Path $asm) { $asmBytes = (Get-Item $asm).Length }
    Write-Host ("SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2) + " exit=" + $code + " asm_bytes=" + $asmBytes)
    Write-Host ""
}

function Time-As([string]$asm, [string]$obj) {
    if (-not (Test-Path $asm)) {
        Write-Host "MISSING $asm"
        return
    }
    if (Test-Path $obj) { Remove-Item $obj -Force }
    Write-Host "=== abassembler $asm ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $out = & .\abassembler.exe $asm $obj 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()
    $out | ForEach-Object { Write-Host $_ }
    $objBytes = 0
    if (Test-Path $obj) { $objBytes = (Get-Item $obj).Length }
    Write-Host ("SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 2) + " exit=" + $code + " obj_bytes=" + $objBytes)
    Write-Host ""
}

Write-Host ("abc.exe mtime=" + (Get-Item abc.exe).LastWriteTime)
Write-Host ("abassembler.exe mtime=" + (Get-Item abassembler.exe).LastWriteTime)
Write-Host ""

# 1) self-host attempt already known to fail; still show
Time-Abc "abc2_combined.abp" "abc2_combined.asm"

# 2) large inputs that should parse
Time-Abc "abc_combined.abp" "_time_abc_combined.asm"
if (Test-Path "_time_abc_combined.asm") { Time-As "_time_abc_combined.asm" "_time_abc_combined.obj" }

Time-Abc "t7_combined.abp" "_time_t7.asm"
if (Test-Path "_time_t7.asm") { Time-As "_time_t7.asm" "_time_t7.obj" }
