# run_test.ps1 - abdbg の回帰テスト
#
#   .\run_test.ps1            # abdbg.exe を作り直して test\*.abp を試す
#   .\run_test.ps1 -Update    # 今の出力で test\*.out を書き直す（中身を見て確かめてから）
#
# test\<名前>.abp を actba64 -debug で訳し、test\<名前>.in のコマンドを abdbg に渡す。
# 出力（プログラム自身の出力も混ざる）のパスはファイル名だけにして test\<名前>.out と比べる。
param(
    [string]$Compiler = "",
    [switch]$Update
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
    Invoke-Compiler @($src.FullName, "-debug", "-o", $exe)
    $got = @(Invoke-Abdbg $exe ([System.IO.File]::ReadAllText($inFile)) | ForEach-Object { Format-Line $_ })
    if ($Update) {
        [System.IO.File]::WriteAllText($outFile, (($got -join "`r`n") + "`r`n"))
        Write-Host "[UPDATE] $name"
        continue
    }
    $want = @()
    if (Test-Path -LiteralPath $outFile) {
        $want = @([System.IO.File]::ReadAllLines($outFile) | Where-Object { $_ -ne "" })
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
