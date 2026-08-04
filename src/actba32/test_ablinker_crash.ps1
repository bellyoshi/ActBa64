# test_ablinker_crash.ps1
# 回帰: ablinker が headers ok 直後に AV (0xC0000005) して .exe を出さない問題
#
# 再現条件: .text が数十 KB 超の COFF（典型: abc_combined.obj, text≈95KB, PE≈180KB）
# 成功条件: AV せず、headers ok の後に OK 行と .exe ができること
#
# 使い方:
#   .\test_ablinker_crash.ps1
#   .\test_ablinker_crash.ps1 -Stage stage0
#   .\test_ablinker_crash.ps1 -Linker .\bin\stage0\ablinker.exe -Obj abc_combined.obj

param(
    [ValidateSet("stage0", "stage1", "stage2")]
    [string]$Stage = "stage0",
    [string]$Linker = "",
    [string]$Obj = "",
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$AV = -1073741819  # 0xC0000005 STATUS_ACCESS_VIOLATION
$MinTextHint = 50000   # このサイズ未満の .obj では回帰にならない
$MinExeHint = 100000

function Fail([string]$msg) {
    Write-Host "FAIL: $msg"
    exit 1
}

function Pass([string]$msg) {
    Write-Host "PASS: $msg"
}

if ($Linker -eq "") {
    $Linker = Join-Path $Root "bin\$Stage\ablinker.exe"
}
if (-not (Test-Path -LiteralPath $Linker)) {
    Fail "linker not found: $Linker"
}

# --- 大きな obj を用意 ---
if ($Obj -eq "") {
    $Obj = Join-Path $Root "abc_combined.obj"
}
if (-not (Test-Path -LiteralPath $Obj)) {
    $asm = Join-Path $Root "abc_combined.asm"
    $as = Join-Path $Root "bin\$Stage\abassembler.exe"
    if ((Test-Path -LiteralPath $asm) -and (Test-Path -LiteralPath $as)) {
        Write-Host "assemble: $asm -> abc_combined.obj"
        & $as $asm $Obj 2>&1 | ForEach-Object { Write-Host $_ }
        if (-not (Test-Path -LiteralPath $Obj)) {
            Fail "assemble produced no obj"
        }
    } else {
        Fail "large obj missing: $Obj (run selfbuild abc step or provide -Obj)"
    }
}

$objLen = (Get-Item -LiteralPath $Obj).Length
Write-Host "=== ablinker crash regression ==="
Write-Host "linker: $Linker"
Write-Host "obj:    $Obj ($objLen bytes)"
if ($objLen -lt $MinTextHint) {
    Write-Host "WARN: obj is small; may not exercise the large-copy AV path"
}

# COFF .text SizeOfRawData を読む（セクション0想定）
$bytes = [IO.File]::ReadAllBytes((Resolve-Path $Obj))
$nSect = [BitConverter]::ToUInt16($bytes, 2)
$textRaw = 0
for ($i = 0; $i -lt $nSect; $i++) {
    $o = 20 + $i * 40
    $name = [Text.Encoding]::ASCII.GetString($bytes, $o, 8).Trim([char]0)
    if ($name -eq ".text") {
        $textRaw = [BitConverter]::ToUInt32($bytes, $o + 16)
        break
    }
}
Write-Host ("COFF: nSect={0} .text raw={1}" -f $nSect, $textRaw)
if ($textRaw -lt $MinTextHint) {
    Write-Host "WARN: .text raw < $MinTextHint; crash path may not trigger"
}

$outExe = Join-Path $Root ("_crash_test_{0}.exe" -f $Stage)
if (Test-Path -LiteralPath $outExe) {
    Remove-Item -LiteralPath $outExe -Force
}

# --- リンク実行 ---
$log = New-Object System.Collections.Generic.List[string]
$sw = [Diagnostics.Stopwatch]::StartNew()
& $Linker $Obj $outExe 2>&1 | ForEach-Object {
    $line = "$_"
    $log.Add($line)
    Write-Host $line
}
$code = $LASTEXITCODE
$sw.Stop()
$joined = [string]::Join("`n", $log)

Write-Host ("exit={0} elapsed={1}s" -f $code, [math]::Round($sw.Elapsed.TotalSeconds, 2))

# --- 判定 ---
$failed = $false

if ($code -eq $AV -or $code -eq 0xC0000005) {
    Write-Host "FAIL: ACCESS_VIOLATION after link (the original crash)"
    $failed = $true
}
if ($code -lt 0 -and $code -ne 0) {
    # 負の終了コードは異常終了のことが多い（AV 以外も含む）
    if ($code -eq $AV) {
        # already reported
    } elseif (-not (Test-Path -LiteralPath $outExe)) {
        Write-Host ("FAIL: linker aborted with exit={0} and no exe" -f $code)
        $failed = $true
    }
}

if ($joined -notmatch "(?m)headers ok") {
    Write-Host "FAIL: missing 'headers ok' (did not reach PE write stage)"
    $failed = $true
} else {
    Pass "reached headers ok"
}

# 旧バグ: headers ok の直後に落ち、OK 行も exe も無い
if ($joined -match "(?m)headers ok" -and $joined -notmatch "(?m)OK:") {
    Write-Host "FAIL: headers ok without OK line (crash/exit between header build and write)"
    $failed = $true
}

if (-not (Test-Path -LiteralPath $outExe)) {
    Write-Host "FAIL: no output exe (same symptom as selfbuild link failed)"
    $failed = $true
} else {
    $exeLen = (Get-Item -LiteralPath $outExe).Length
    Write-Host ("exe: {0} bytes" -f $exeLen)
    if ($exeLen -lt $MinExeHint -and $textRaw -ge $MinTextHint) {
        Write-Host ("FAIL: exe too small ({0} < {1}) for large .text input" -f $exeLen, $MinExeHint)
        $failed = $true
    } else {
        Pass ("wrote exe ({0} bytes)" -f $exeLen)
    }
}

if ($joined -match "(?m)OK:") {
    Pass "OK line present"
}

if (-not $KeepArtifacts -and (Test-Path -LiteralPath $outExe)) {
    Remove-Item -LiteralPath $outExe -Force
}

if ($failed) {
    Write-Host ""
    Write-Host "RESULT: FAIL (ablinker large-link crash regression)"
    exit 1
}

Write-Host ""
Write-Host "RESULT: PASS (no AV after headers ok; large PE written)"
exit 0
