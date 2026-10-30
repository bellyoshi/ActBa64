# rununittest.ps1 - src\unittest をコンパイルして実行する
#
#   .\rununittest.ps1
#   .\rununittest.ps1 -Actba32

param(
    [switch]$Actba32
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Compiler = Join-Path $Root "..\actba64\bin\stage2\actba64.exe"
$Pj = Join-Path $Root "unittest.pj"
$Exe = Join-Path $Root "unittest.exe"

if (-not (Test-Path -LiteralPath $Compiler)) {
    Write-Error "compiler not found: $Compiler"
    exit 2
}
if (-not (Test-Path -LiteralPath $Pj)) {
    Write-Error "project not found: $Pj"
    exit 2
}

$ccArgs = @($Pj)
if ($Actba32) {
    $ccArgs += "-actba32"
}
$ccArgs += @("-o", $Exe)

Write-Host "=== compile ==="
& $Compiler @ccArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "=== run ==="
& $Exe
exit $LASTEXITCODE
