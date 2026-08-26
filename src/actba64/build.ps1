# build.ps1 - actba64 ブートストラップ
#
#   stage0: ActiveBasic 4.20 で actba64.pj をビルドした 32bit ホスト
#           （bin\stage0\actba64.exe。#PLATFORM=32 は AB4.20 用で、出力ターゲットではない）
#   stage0 -> stage1: stage0 の actba64 で 64bit actba64.exe をビルド（-actba32 なし）
#   stage1 -> stage2: 自己コンパイル
#   stage2 -> stage3: 再コンパイル
#   stage2 vs stage3: バイナリ一致（自己ホスト固定点）
#
# 使い方:
#   .\build.ps1
#   .\build.ps1 -SkipCopy       # Include を stage0 へコピーしない
#   .\build.ps1 -Stage1Only
#   .\build.ps1 -SkipStage1
#   .\build.ps1 -SkipCompare

param(
    [switch]$SkipCopy,
    [switch]$Stage1Only,
    [switch]$SkipStage1,
    [switch]$SkipCompare
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$IncludeSrc = Join-Path $Root "..\Include"
$Stage0 = Join-Path $Root "bin\stage0"
$Pj = "actba64.pj"
$ExeName = "actba64.exe"

function Get-StageDir([string]$stage) {
    return Join-Path $Root "bin\$stage"
}

function Ensure-Dir([string]$dir) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

function Test-Actba64Driver([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        return $false
    }
    $len = (Get-Item -LiteralPath $path).Length
    if ($len -lt 80000) {
        Write-Host ("note: $path is ${len} bytes (too small for a compiler)")
        return $false
    }
    return $true
}

function Invoke-Actba64Build([string]$driverStage, [string]$outStage) {
    $driver = Join-Path (Get-StageDir $driverStage) $ExeName
    $outDir = Get-StageDir $outStage
    $relOut = "bin\$outStage\$ExeName"
    $outPath = Join-Path $outDir $ExeName
    $pjPath = Join-Path $Root $Pj

    if (-not (Test-Path -LiteralPath $driver)) {
        Write-Error "driver not found: $driver"
        exit 1
    }

    Ensure-Dir $outDir
    if (Test-Path -LiteralPath $outPath) {
        Remove-Item -LiteralPath $outPath -Force
    }

    Write-Host ""
    Write-Host "=== $driverStage -> $outStage ==="
    Write-Host "driver: $driver"
    Write-Host "-- $ExeName $Pj -o $relOut"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $driver $pjPath -o $relOut
    $code = [int]$LASTEXITCODE
    $sw.Stop()

    if ($code -ne 0 -or -not (Test-Path -LiteralPath $outPath)) {
        Write-Error "build failed: $driverStage -> $outStage exit=$code (no output at $outPath)"
        exit 1
    }

    $fi = Get-Item -LiteralPath $outPath
    Write-Host ("OK: {0} ({1} bytes, {2}s)" -f $outPath, $fi.Length, [math]::Round($sw.Elapsed.TotalSeconds, 2))
}

function Compare-StageExes([string]$a, [string]$b) {
    Write-Host ""
    Write-Host "=== compare $a vs $b ==="
    $pa = Join-Path (Get-StageDir $a) $ExeName
    $pb = Join-Path (Get-StageDir $b) $ExeName

    if (-not (Test-Path -LiteralPath $pa) -or -not (Test-Path -LiteralPath $pb)) {
        Write-Error "compare missing: $pa / $pb"
        exit 1
    }

    $ha = (Get-FileHash -Algorithm SHA256 -LiteralPath $pa).Hash
    $hb = (Get-FileHash -Algorithm SHA256 -LiteralPath $pb).Hash
    $sa = (Get-Item -LiteralPath $pa).Length
    $sb = (Get-Item -LiteralPath $pb).Length

    if ($ha -eq $hb) {
        Write-Host ("MATCH {0} ({1} bytes)" -f $ExeName, $sa)
        Write-Host "PASS: $a and $b binaries match (SHA256)"
        return 0
    }

    Write-Host ("DIFF  {0} ({1} vs {2} bytes)" -f $ExeName, $sa, $sb)
    Write-Host ("  {0}: {1}" -f $a, $ha)
    Write-Host ("  {0}: {1}" -f $b, $hb)
    Write-Error "FAIL: $a and $b binaries differ"
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $Root $Pj))) {
    Write-Error "project not found: $Pj"
    exit 2
}

if ($SkipStage1) {
    $stage1Exe = Join-Path (Get-StageDir "stage1") $ExeName
    if (-not (Test-Path -LiteralPath $stage1Exe)) {
        Write-Error "stage1 not found: $stage1Exe (build without -SkipStage1 first)"
        exit 2
    }
    Write-Host "=== skip stage1 (reuse $stage1Exe) ==="
} else {
    Ensure-Dir $Stage0
    $Driver = Join-Path $Stage0 $ExeName
    if (-not (Test-Actba64Driver $Driver)) {
        $fallback = $null
        foreach ($cand in @("stage2", "stage3", "stage1")) {
            $p = Join-Path (Get-StageDir $cand) $ExeName
            if (Test-Actba64Driver $p) {
                $fallback = $p
                break
            }
        }
        if ($null -eq $fallback) {
            Write-Error @"
stage0 missing or invalid: $Driver
Rebuild actba64.pj with ActiveBasic 4.20 into bin\stage0\actba64.exe
(#USEWINDOW=0 / CUI). A ~24KB GUI exe is not the compiler.
"@
            exit 2
        }
        Write-Host "=== stage0 actba64.exe is not a usable compiler; using $fallback ==="
        Copy-Item -LiteralPath $fallback -Destination $Driver -Force
    }

    if (-not $SkipCopy) {
        if (-not (Test-Path -LiteralPath $IncludeSrc)) {
            Write-Error "Include not found: $IncludeSrc"
            exit 2
        }
        $incDst = Join-Path $Stage0 "Include"
        if (Test-Path -LiteralPath $incDst) {
            Remove-Item -LiteralPath $incDst -Recurse -Force
        }
        Write-Host "=== copy Include -> bin\stage0\Include ==="
        Copy-Item -LiteralPath $IncludeSrc -Destination $incDst -Recurse
    }

    Invoke-Actba64Build -driverStage "stage0" -outStage "stage1"
}

if ($Stage1Only) {
    Write-Host ""
    Write-Host "build done (stage1 only)."
    exit 0
}

Invoke-Actba64Build -driverStage "stage1" -outStage "stage2"
Invoke-Actba64Build -driverStage "stage2" -outStage "stage3"

if (-not $SkipCompare) {
    Compare-StageExes "stage2" "stage3"
}

Write-Host ""
Write-Host "build done."
exit 0
