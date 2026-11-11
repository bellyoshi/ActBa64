# run_selfhost_linux.ps1 - Linux 上でのセルフホスト（P6）
#
#   .\run_selfhost_linux.ps1          # bin\stage1\actba64.exe（既定）で Linux 版を作る
#   .\run_selfhost_linux.ps1 stage2
#
# 1. Windows: actba64.pj と ..\rc\rc.pj を -linux で bin\linux\actba64 / rc に（Include も隣へ）
# 2. WSL: その actba64 で、
#      actba64.pj -linux → gen2         … 1 の actba64 とバイト単位で同じ
#      rc.pj -linux      → rc2          … 1 の rc と同じ
#      actba64.pj（PE）  → actba64.exe  … Windows の同じコンパイラが出す PE と同じ
#      #resource のテスト（PE）          … 同上（.rc は隣の rc を起動する）
# 前提: WSL。無ければ SKIP で終了コード 0。

param(
    [Parameter(Position = 0)]
    [ValidateSet("stage1", "stage2")]
    [string]$Stage = "stage1"
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$RcDir = Join-Path $Root "..\rc"
$Out = Join-Path $Root "bin\linux"
$Ref = Join-Path $Out "ref"
$Compiler = Join-Path $Root "bin\$Stage\actba64.exe"
$ResTests = @("t_resource", "t_iconres", "t_bmpres")
$stats = @{ pass = 0; fail = 0 }

if (-not (Test-Path -LiteralPath $Compiler)) {
    Write-Error "compiler not found: $Compiler (run .\build.ps1 first)"
    exit 2
}
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "SKIP: wsl.exe not found"
    exit 0
}

function Get-WslPath([string]$winPath) {
    $p = (& wsl.exe -e wslpath -a ($winPath -replace '\\', '/')) | Select-Object -First 1
    return $p.Trim()
}

function Add-Result([string]$name, [bool]$ok, [string]$detail) {
    if ($ok) {
        $stats.pass++
        Write-Host ("[PASS] {0}  {1}" -f $name, $detail) -ForegroundColor Green
    } else {
        $stats.fail++
        Write-Host ("[FAIL] {0}  {1}" -f $name, $detail) -ForegroundColor Red
    }
}

function Test-SameFile([string]$a, [string]$b) {
    if (-not (Test-Path -LiteralPath $a) -or -not (Test-Path -LiteralPath $b)) { return $false }
    $ha = (Get-FileHash -LiteralPath $a -Algorithm SHA256).Hash
    $hb = (Get-FileHash -LiteralPath $b -Algorithm SHA256).Hash
    return $ha -eq $hb
}

# Windows 側でコンパイル（cwd = $dir）。失敗なら $false
function Invoke-Win([string]$dir, [string[]]$ccArgs) {
    Push-Location $dir
    $log = & $Compiler @ccArgs 2>&1
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { Write-Host (($log | Select-Object -Last 3) -join " / ") }
    return $code -eq 0
}

# WSL 側で Linux 版の actba64 を動かす（cwd = $dir）。引数の " を崩さないようファイル経由
function Invoke-Lx([string]$name, [string]$dir, [string]$cmdArgs) {
    $run = "cd '$(Get-WslPath $dir)' && '$(Get-WslPath $Out)/actba64' $cmdArgs > '$(Get-WslPath $Out)/$name.log' 2>&1; echo `$?`n"
    [System.IO.File]::WriteAllBytes((Join-Path $Out "$name.run"), [System.Text.Encoding]::UTF8.GetBytes($run))
    $code = (& wsl.exe -e sh "$(Get-WslPath $Out)/$name.run") | Select-Object -Last 1
    return [int]$code
}

function Test-Lx([string]$name, [string]$dir, [string]$cmdArgs, [string]$actual, [string]$expect) {
    Remove-Item -LiteralPath $actual -Force -ErrorAction SilentlyContinue
    $code = Invoke-Lx $name $dir $cmdArgs
    $same = ($code -eq 0) -and (Test-SameFile $actual $expect)
    Add-Result $name $same ("exit={0}, same as {1}" -f $code, (Split-Path -Leaf $expect))
}

if (Test-Path -LiteralPath $Out) { Remove-Item -LiteralPath $Out -Recurse -Force }
New-Item -ItemType Directory -Path $Ref -Force | Out-Null

Write-Host "=== Windows ($Stage): Linux 版の actba64 / rc と、比べる PE ==="
$ok = Invoke-Win $Root @("actba64.pj", "-linux", "-o", (Join-Path $Out "actba64"))
$ok = $ok -and (Invoke-Win $RcDir @("rc.pj", "-linux", "-o", (Join-Path $Out "rc")))
$ok = $ok -and (Invoke-Win $Root @("actba64.pj", "-o", (Join-Path $Ref "actba64.exe")))
foreach ($t in $ResTests) {
    $ok = $ok -and (Invoke-Win $Root @("test\$t.abp", "-o", (Join-Path $Ref "$t.exe")))
}
if (-not $ok) {
    Write-Host "FAIL: Windows build" -ForegroundColor Red
    exit 1
}
Copy-Item -LiteralPath (Join-Path $Root "bin\$Stage\Include") -Destination (Join-Path $Out "Include") -Recurse

Write-Host "=== WSL: Linux 版の actba64 ==="
$o = Get-WslPath $Out
Test-Lx "gen2" $Root "actba64.pj -linux -o '$o/gen2'" (Join-Path $Out "gen2") (Join-Path $Out "actba64")
Test-Lx "rc2" $RcDir "rc.pj -linux -o '$o/rc2'" (Join-Path $Out "rc2") (Join-Path $Out "rc")
Test-Lx "actba64.exe" $Root "actba64.pj -o '$o/actba64.exe'" (Join-Path $Out "actba64.exe") (Join-Path $Ref "actba64.exe")
foreach ($t in $ResTests) {
    Test-Lx "$t.exe" $Root "test/$t.abp -o '$o/$t.exe'" (Join-Path $Out "$t.exe") (Join-Path $Ref "$t.exe")
}
Write-Host ("Summary: {0} passed, {1} failed" -f $stats.pass, $stats.fail)
if ($stats.fail -gt 0) { exit 1 }
exit 0
