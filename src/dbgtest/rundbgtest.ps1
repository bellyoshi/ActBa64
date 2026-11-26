# rundbgtest.ps1 - デバッガーのユニットテスト（src\dbgtest）をコンパイルして実行する
#
#   .\rundbgtest.ps1
#
# abdbg（src\abdbg）の .abdbg の読み方・条件・値の種類と、ProjectEditor のデバッグの部分のうち窓を
# 使わないところ（ブレークポイントの一覧とずらし方、abdbg の答えの分け方、変数のツリーの問いと答え）を試す。
# 窓・パイプ・プロセスの代わりは DbgStubs.sbp。abdbg を動かして試すのは src\abdbg\run_test.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Compiler = Join-Path $Root "..\actba64\bin\stage2\actba64.exe"
$Pj = Join-Path $Root "dbgtest.pj"
$Exe = Join-Path $Root "dbgtest.exe"

if (-not (Test-Path -LiteralPath $Compiler)) {
    Write-Error "compiler not found: $Compiler"
    exit 2
}

Write-Host "=== compile ==="
& $Compiler $Pj -o $Exe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "=== run ==="
Push-Location $Root
try {
    & $Exe
    $code = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath (Join-Path $Root "dbgtest_tmp.abdbg") -ErrorAction SilentlyContinue
    Pop-Location
}
exit $code
