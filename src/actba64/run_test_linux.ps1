# run_test_linux.ps1 - test\linux\*.abp を -linux でコンパイルし、WSL で実行する
#
#   .\run_test_linux.ps1            # bin\stage1\actba64.exe（既定）
#   .\run_test_linux.ps1 stage2
#   .\run_test_linux.ps1 -KeepArtifacts
#
# 前提: WSL（wsl.exe）に Linux ディストリビューションがあること。無ければ SKIP で終了コード 0。
# メタ（run_test_meta.ps1 と同じ）:
#   ' Target: actba64  … 対象（必須）
#   ' Expect: N        … 終了コード（省略時 0）
#   ' Stdin: text      … 標準入力の 1 行（LF で渡す。複数行可）
#   ' Option: -x       … 追加のコンパイラオプション
#   ' Args: a "b c"   … 実行時の引数（sh にそのまま渡す）
#   ' Warn: N        … コンパイラの「has no Linux version」警告の数（省略時 0）
#   ' WarnAt: text   … その警告の場所（コンパイラの出力にこの文字列があること）
#   ' MaxSize: N     … 出力 ELF の上限バイト数（呼ばれない関数を消せているか）
# 期待する出力（あれば一致を見る。バイト単位、LF のまま）:
#   test\linux\<base>.out.txt     … 標準出力
#   test\linux\<base>.stderr.txt  … 標準エラー

param(
    [Parameter(Position = 0)]
    [ValidateSet("stage1", "stage2")]
    [string]$Stage = "stage1",
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$TestDir = Join-Path $Root "test\linux"
$OutDir = Join-Path $Root "bin\test_linux"
$Compiler = Join-Path $Root "bin\$Stage\actba64.exe"
. (Join-Path $Root "run_test_meta.ps1")

if (-not (Test-Path -LiteralPath $Compiler)) {
    Write-Error "compiler not found: $Compiler (run .\build.ps1 first)"
    exit 2
}
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "SKIP: wsl.exe not found"
    exit 0
}
if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$stats = @{ pass = 0; fail = 0 }

function Add-Result([string]$name, [string]$status, [string]$detail) {
    $color = "Green"
    if ($status -ne "PASS") { $color = "Red" }
    Write-Host ("[{0}] {1}  {2}" -f $status, $name, $detail) -ForegroundColor $color
}

function Get-WslPath([string]$winPath) {
    $p = (& wsl.exe -e wslpath -a ($winPath -replace '\\', '/')) | Select-Object -First 1
    return $p.Trim()
}

function Compare-Bytes([string]$expectPath, [string]$actualPath) {
    if (-not (Test-Path -LiteralPath $expectPath)) { return $true }
    $e = [System.IO.File]::ReadAllBytes($expectPath)
    $a = [byte[]]@()
    if (Test-Path -LiteralPath $actualPath) { $a = [System.IO.File]::ReadAllBytes($actualPath) }
    if ($e.Length -ne $a.Length) { return $false }
    for ($i = 0; $i -lt $e.Length; $i++) {
        if ($e[$i] -ne $a[$i]) { return $false }
    }
    return $true
}

function Write-Stdin([string]$path, [string[]]$lines) {
    $text = ""
    foreach ($line in $lines) { $text += $line + "`n" }
    [System.IO.File]::WriteAllBytes($path, [System.Text.Encoding]::UTF8.GetBytes($text))
}

function Invoke-Wsl([string]$base, [bool]$hasStdin, [string]$runArgs) {
    $dir = Get-WslPath $OutDir
    $in = "/dev/null"
    if ($hasStdin) { $in = "./$base.stdin" }
    # 引数の " を Windows PowerShell が崩さないよう、コマンドはファイルに書いて sh で読む
    $run = "timeout 5 ./$base $runArgs < $in > $base.stdout 2> $base.stderr; echo `$?`n"
    [System.IO.File]::WriteAllBytes((Join-Path $OutDir "$base.run"), [System.Text.Encoding]::UTF8.GetBytes($run))
    $code = (& wsl.exe -e sh -c "cd '$dir' && sh ./$base.run") | Select-Object -Last 1
    return [int]$code
}

function Get-LinuxMeta([string]$path) {
    $m = @{ Warn = 0; MaxSize = 0; WarnAt = "" }
    foreach ($line in (Get-Content -LiteralPath $path -Encoding UTF8)) {
        if ($line -match '^\s*''\s*Warn\s*:\s*(\d+)\s*$') { $m.Warn = [int]$Matches[1] }
        if ($line -match '^\s*''\s*MaxSize\s*:\s*(\d+)\s*$') { $m.MaxSize = [int]$Matches[1] }
        if ($line -match '^\s*''\s*WarnAt\s*:\s*(\S+)\s*$') { $m.WarnAt = $Matches[1] }
    }
    return $m
}

# 警告の数と ELF の大きさ。合わなければ理由、合えば空
function Test-Build([hashtable]$lm, $log, [string]$exe) {
    $warns = @($log | Where-Object { "$_" -match 'has no Linux version' }).Count
    if ($warns -ne $lm.Warn) { return "warnings=$warns expect=$($lm.Warn)" }
    if ($lm.WarnAt -and -not ("$log".Contains($lm.WarnAt))) { return "no warning at $($lm.WarnAt)" }
    $size = (Get-Item -LiteralPath $exe).Length
    if ($lm.MaxSize -gt 0 -and $size -gt $lm.MaxSize) { return "size=$size max=$($lm.MaxSize)" }
    return ""
}

function Invoke-OneTest([System.IO.FileInfo]$file) {
    $name = $file.Name
    $meta = Get-Meta $file.FullName
    if (-not $meta.Target) { return }
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $exe = Join-Path $OutDir $base
    Remove-Item -LiteralPath $exe -Force -ErrorAction SilentlyContinue
    $ccArgs = @($file.FullName, "-linux") + $meta.Options + @("-o", $exe)
    $log = & $Compiler @ccArgs 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exe)) {
        $stats.fail++
        Add-Result $name "FAIL" ((($log | Select-Object -Last 3) -join " / "))
        return
    }
    $why = Test-Build (Get-LinuxMeta $file.FullName) $log $exe
    if ($why) {
        $stats.fail++
        Add-Result $name "FAIL" $why
        return
    }
    $hasStdin = $meta.Stdin.Count -gt 0
    if ($hasStdin) { Write-Stdin (Join-Path $OutDir "$base.stdin") $meta.Stdin }
    $actual = Invoke-Wsl $base $hasStdin $meta.Args
    Test-Outcome $name $base $meta $actual
    if (-not $KeepArtifacts) {
        Get-ChildItem -LiteralPath $OutDir -Filter "$base*" | Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

function Test-Outcome([string]$name, [string]$base, [hashtable]$meta, [int]$actual) {
    $outOk = Compare-Bytes (Join-Path $TestDir "$base.out.txt") (Join-Path $OutDir "$base.stdout")
    $errOk = Compare-Bytes (Join-Path $TestDir "$base.stderr.txt") (Join-Path $OutDir "$base.stderr")
    if ($actual -ne $meta.Expect) {
        $stats.fail++
        Add-Result $name "FAIL" "exit=$actual expect=$($meta.Expect)"
    } elseif (-not $outOk) {
        $stats.fail++
        Add-Result $name "FAIL" "stdout differs from $base.out.txt"
    } elseif (-not $errOk) {
        $stats.fail++
        Add-Result $name "FAIL" "stderr differs from $base.stderr.txt"
    } else {
        $stats.pass++
        Add-Result $name "PASS" "exit=$actual"
    }
}

Write-Host "=== actba64 $Stage -linux (WSL) ==="
Get-ChildItem -LiteralPath $TestDir -Filter "*.abp" -File | Sort-Object Name | ForEach-Object {
    Invoke-OneTest $_
}
Write-Host ("Summary: {0} passed, {1} failed" -f $stats.pass, $stats.fail)
if ($stats.fail -gt 0) { exit 1 }
exit 0
