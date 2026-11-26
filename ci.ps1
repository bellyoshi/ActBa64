# ci.ps1 - CI（GitHub Actions）と同じ手順を回す
#
#   .\ci.ps1 -Bootstrap <actba64.exe>   # ブートストラップのコンパイラを bin\stage0 に置いてから
#   .\ci.ps1                            # bin\stage0 の actba64.exe をそのまま使う
#
# 手順:
#   1. stage0 -> stage1 -> stage2（build.ps1 -SkipCompare）
#   2. stage2 で自分をビルドした stage3 が stage2 とバイト単位で一致すること（自己ホストの固定点）
#      CI の stage0 はリリースの actba64.exe で、ソースより古いことがあるため、stage1 と stage2 は比べない
#   3. stage2 で rc.exe と ProjectEditor を作り release\ に揃える（release_build.ps1 -SkipSelfHost。
#      ProjectEditor を起動するテストがある）
#   4. ユニットテスト（stage2）
#   5. 統合テスト（stage2、64bit と -actba32。CI の機械は遅いので 1 本 20 秒まで）
#
# -linux の出力の実行（WSL）は CI では行わない。手元で .\check.ps1 integration を使う。

param(
    [string]$Bootstrap = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Cc = Join-Path $Root "src\actba64"
$Bin = Join-Path $Cc "bin"

function Invoke-Step([string]$name, [scriptblock]$body) {
    Write-Host ""
    Write-Host "##### $name #####"
    & $body
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $name (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

if ($Bootstrap -ne "") {
    $stage0 = Join-Path $Bin "stage0"
    New-Item -ItemType Directory -Force -Path $stage0 | Out-Null
    Copy-Item -LiteralPath $Bootstrap -Destination (Join-Path $stage0 "actba64.exe") -Force
}

Invoke-Step "build stage0 -> stage1 -> stage2" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Cc "build.ps1") -SkipCompare
}

Invoke-Step "fixed point: stage2 -> stage3" {
    $stage2 = Join-Path $Bin "stage2"
    $stage3 = Join-Path $Bin "stage3"
    New-Item -ItemType Directory -Force -Path $stage3 | Out-Null
    $inc3 = Join-Path $stage3 "Include"
    if (Test-Path -LiteralPath $inc3) { Remove-Item -LiteralPath $inc3 -Recurse -Force }
    Copy-Item -LiteralPath (Join-Path $stage2 "Include") -Destination $inc3 -Recurse
    Push-Location $Cc
    & (Join-Path $stage2 "actba64.exe") "actba64.pj" -o (Join-Path $stage3 "actba64.exe")
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { $global:LASTEXITCODE = $code; return }
    $h2 = (Get-FileHash (Join-Path $stage2 "actba64.exe")).Hash
    $h3 = (Get-FileHash (Join-Path $stage3 "actba64.exe")).Hash
    Write-Host "stage2: $h2"
    Write-Host "stage3: $h3"
    if ($h2 -ne $h3) {
        Write-Host "stage2 and stage3 differ"
        $global:LASTEXITCODE = 1
        return
    }
    Write-Host "MATCH"
    $global:LASTEXITCODE = 0
}

Invoke-Step "release set (rc.exe, ProjectEditor) with stage2" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "release_build.ps1") -SkipSelfHost
}

Invoke-Step "unit tests" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "src\unittest\rununittest.ps1")
}

Invoke-Step "integration tests (64bit)" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Cc "run_test2.ps1") stage2 -TimeoutSec 20
}

Invoke-Step "integration tests (-actba32)" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Cc "run_test2.ps1") stage2 -Actba32 -TimeoutSec 20
}

Invoke-Step "debugger tests (abdbg)" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "src\abdbg\run_test.ps1")
}

Invoke-Step "debugger tests (abdbg, -actba32)" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "src\abdbg\run_test.ps1") -Actba32
}

Write-Host ""
Write-Host "CI OK"
exit 0
