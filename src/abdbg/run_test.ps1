# run_test.ps1 - abdbg の回帰テスト
#
#   .\run_test.ps1            # abdbg.exe を作り直して test\*.abp を試す
#   .\run_test.ps1 -Update    # 今の出力で test\*.out を書き直す（中身を見て確かめてから）
#   .\run_test.ps1 -Actba32   # -actba32 の 32bit の exe で試す
#
# test\<名前>.abp を actba64 -debug で訳し、test\<名前>.in のコマンドを abdbg に渡す。
# 出力（プログラム自身の出力も混ざる）のパスはファイル名だけにして test\<名前>.out と比べる。
# -Actba32 では test\<名前>.out32 があればそれと比べる（32bit は機械語の並びが違い、ステップで止まる
# 行が変わることがある）。-Update -Actba32 は .out と違うときだけ .out32 を書く（同じなら消す）。
param(
    [string]$Compiler = "",
    [switch]$Update,
    [switch]$Actba32
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if ($Compiler -eq "") { $Compiler = Join-Path $Root "..\actba64\bin\stage2\actba64.exe" }
$Compiler = (Resolve-Path -LiteralPath $Compiler).Path
$Abdbg = Join-Path $Root "abdbg.exe"
$OutDir = Join-Path $Root "test\out"

function Invoke-Compiler([string[]]$cargs) {
    $log = & $Compiler @cargs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw ("compile failed: " + ($cargs -join " ") + "`n" + ($log -join "`n")) }
}

# 標準入力に in を渡して動かし、出力の行を返す（20 秒で打ち切る）
function Invoke-Abdbg([string]$exe, [string]$inText) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Abdbg
    $psi.Arguments = '"' + $exe + '"'
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.WorkingDirectory = $OutDir
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.StandardInput.Write($inText)
    $p.StandardInput.Close()
    $text = $p.StandardOutput.ReadToEndAsync()
    if (-not $p.WaitForExit(20000)) {
        $p.Kill()
        return @("TIMEOUT")
    }
    return ($text.Result -replace "`r", "") -split "`n" | Where-Object { $_ -ne "" }
}

# C:\...\name.abp → name.abp。ポインタの値（&H...）は配置で変わるので &H? にする
function Format-Line([string]$s) {
    $s = $s -replace '[A-Za-z]:\\(?:[^\\\r\n]*\\)*', ''
    return ($s -replace '&H[0-9a-fA-F]+', '&H?')
}

Push-Location $Root
try {
    Invoke-Compiler @("abdbg.pj", "-o", $Abdbg)
} finally {
    Pop-Location
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$pass = 0
$fail = 0
foreach ($src in Get-ChildItem -LiteralPath (Join-Path $Root "test") -Filter *.abp | Sort-Object Name) {
    $name = $src.BaseName
    $inFile = Join-Path $src.DirectoryName "$name.in"
    $outFile = Join-Path $src.DirectoryName "$name.out"
    if (-not (Test-Path -LiteralPath $inFile)) { continue }
    $exe = Join-Path $OutDir "$name.exe"
    $cargs = @($src.FullName, "-debug", "-o", $exe)
    if ($Actba32) {
        $exe = Join-Path $OutDir "${name}_32.exe"
        $cargs = @($src.FullName, "-debug", "-actba32", "-o", $exe)
    }
    Invoke-Compiler $cargs
    $got = @(Invoke-Abdbg $exe ([System.IO.File]::ReadAllText($inFile)) | ForEach-Object { Format-Line $_ })
    $want = @()
    if (Test-Path -LiteralPath $outFile) {
        $want = @([System.IO.File]::ReadAllLines($outFile) | Where-Object { $_ -ne "" })
    }
    $out32 = Join-Path $src.DirectoryName "$name.out32"
    $same = (($got -join "`n") -ceq ($want -join "`n"))
    if ($Update) {
        $text = (($got -join "`r`n") + "`r`n")
        if (-not $Actba32) { [System.IO.File]::WriteAllText($outFile, $text) }
        if ($Actba32 -and -not $same) { [System.IO.File]::WriteAllText($out32, $text) }
        if ($Actba32 -and $same -and (Test-Path -LiteralPath $out32)) { Remove-Item -LiteralPath $out32 }
        Write-Host "[UPDATE] $name"
        continue
    }
    if ($Actba32 -and (Test-Path -LiteralPath $out32)) {
        $want = @([System.IO.File]::ReadAllLines($out32) | Where-Object { $_ -ne "" })
    }
    if (($got -join "`n") -ceq ($want -join "`n")) {
        $pass++
        Write-Host "[PASS] $name"
    } else {
        $fail++
        Write-Host "[FAIL] $name"
        Compare-Object $want $got | ForEach-Object { Write-Host ("    " + $_.SideIndicator + " " + $_.InputObject) }
    }
}
Write-Host ""
Write-Host "Summary: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 }
exit 0
