# check.ps1 - コミット前は unit、プッシュ前は integration
#
#   .\check.ps1              # unit（src\unittest\rununittest.ps1）
#   .\check.ps1 unit
#   .\check.ps1 integration  # src\actba64\run_test2.ps1（既定 stage1・64bit）+ run_test_linux.ps1（WSL）

param(
    [Parameter(Position = 0)]
    [ValidateSet("unit", "integration")]
    [string]$Kind = "unit"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

if ($Kind -eq "unit") {
    $script = Join-Path $Root "src\unittest\rununittest.ps1"
} else {
    $script = Join-Path $Root "src\actba64\run_test2.ps1"
}

if (-not (Test-Path -LiteralPath $script)) {
    Write-Error "not found: $script"
    exit 2
}

Write-Host "=== check $Kind ==="
& powershell -NoProfile -ExecutionPolicy Bypass -File $script
if ($LASTEXITCODE -ne 0 -or $Kind -ne "integration") {
    exit $LASTEXITCODE
}

# -linux の出力を WSL で実行（WSL が無ければ SKIP で 0）
$linux = Join-Path $Root "src\actba64\run_test_linux.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $linux
exit $LASTEXITCODE
