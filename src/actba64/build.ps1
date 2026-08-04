# build.ps1 - actba64 ブートストラップ
#
#   stage0: actba32\bin\stage2 をコピー（32bit actba32 等）
#   stage0 -> stage1: actba32 で actba64.exe をビルド
#   stage1 -> stage2: stage1 の actba64 で自己コンパイル
#   stage2 -> stage3: stage2 の actba64 で再コンパイル
#   stage2 vs stage3: バイナリ一致を確認（自己ホスト固定点）
#
# 使い方:
#   .\build.ps1
#   .\build.ps1 -SkipCopy
#   .\build.ps1 -Stage1Only
#   .\build.ps1 -SkipStage1   # 既存 stage1 を使い stage2/stage3 のみ
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

$SrcStage2 = Join-Path $Root "..\actba32\bin\stage2"
$Stage0 = Join-Path $Root "bin\stage0"
$Pj = "actba64.pj"
$ExeName = "actba64.exe"
$BootTools = @("actba32.exe", "abc.exe", "abassembler.exe", "ablinker.exe")
$BootDriver = "actba32.exe"

function Get-StageDir([string]$stage) {
    return Join-Path $Root "bin\$stage"
}

function Ensure-Dir([string]$dir) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

function Invoke-BootBuild([string]$driverExe, [string]$outStage) {
    $outDir = Get-StageDir $outStage
    $relOut = "bin\$outStage\$ExeName"
    $outPath = Join-Path $outDir $ExeName
    Ensure-Dir $outDir

    $beforeTime = [datetime]::MinValue
    $beforeLen = -1
    if (Test-Path -LiteralPath $outPath) {
        $prev = Get-Item -LiteralPath $outPath
        $beforeTime = $prev.LastWriteTimeUtc
        $beforeLen = $prev.Length
    }

    Write-Host ""
    Write-Host "=== stage0 actba32 -> $outStage ==="
    Write-Host "driver: $driverExe"
    Write-Host "-- ${Pj}: -o $relOut"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $driverExe $Pj -o $relOut 2>&1 | ForEach-Object { "$_" }
    $sw.Stop()
    $code = [int]$LASTEXITCODE

    foreach ($line in $log) { Write-Host $line }

    $joined = [string]::Join("`n", @($log))
    $failHint = $joined -match "(?i)abc fail|asm fail|link fail|cannot |not found:|error:"

    if ($code -ne 0 -or $failHint -or -not (Test-Path -LiteralPath $outPath)) {
        Write-Error "build failed: $Pj -> $relOut exit=$code"
        exit 1
    }
    $fi = Get-Item -LiteralPath $outPath
    if ($fi.LastWriteTimeUtc -le $beforeTime -and $fi.Length -eq $beforeLen) {
        Write-Error "output was not updated: $outPath"
        exit 1
    }

    Write-Host ("OK: {0} ({1} bytes, {2}s)" -f $outPath, $fi.Length, [math]::Round($sw.Elapsed.TotalSeconds, 2))
}

function Invoke-Actba64Build([string]$driverStage, [string]$outStage) {
    $driver = Join-Path (Get-StageDir $driverStage) $ExeName
    $outDir = Get-StageDir $outStage
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
    Write-Host "-- $ExeName $Pj -o $outPath"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $driver $pjPath -o $outPath 2>&1 | ForEach-Object { "$_" }
    $sw.Stop()
    $code = [int]$LASTEXITCODE

    foreach ($line in $log) { Write-Host $line }

    if ($code -ne 0 -or -not (Test-Path -LiteralPath $outPath)) {
        Write-Error "build failed: $driverStage -> $outStage exit=$code"
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

# --- stage0 -> stage1 ---
if ($SkipStage1) {
    $stage1Exe = Join-Path (Get-StageDir "stage1") $ExeName
    if (-not (Test-Path -LiteralPath $stage1Exe)) {
        Write-Error "stage1 not found: $stage1Exe (build without -SkipStage1 first)"
        exit 2
    }
    Write-Host "=== skip stage1 (reuse $stage1Exe) ==="
} else {
    # stage0: copy actba32 toolchain
    if (-not $SkipCopy) {
        if (-not (Test-Path -LiteralPath $SrcStage2)) {
            Write-Error "source not found: $SrcStage2"
            exit 2
        }
        Ensure-Dir (Split-Path $Stage0 -Parent)
        if (Test-Path -LiteralPath $Stage0) {
            Remove-Item -LiteralPath $Stage0 -Recurse -Force
        }
        Write-Host "=== copy actba32\bin\stage2 -> bin\stage0 ==="
        Copy-Item -LiteralPath $SrcStage2 -Destination $Stage0 -Recurse
    }

    $Driver = Join-Path $Stage0 $BootDriver
    if (-not (Test-Path -LiteralPath $Driver)) {
        Write-Error "actba32 not found: $Driver"
        exit 2
    }
    foreach ($t in $BootTools) {
        $p = Join-Path $Stage0 $t
        if (-not (Test-Path -LiteralPath $p)) {
            Write-Error "stage0 missing: $p"
            exit 2
        }
    }

    Invoke-BootBuild -driverExe $Driver -outStage "stage1"
}

if ($Stage1Only) {
    Write-Host ""
    Write-Host "build done (stage1 only)."
    exit 0
}

# --- stage1 -> stage2 ---
Invoke-Actba64Build -driverStage "stage1" -outStage "stage2"

# --- stage2 -> stage3 ---
Invoke-Actba64Build -driverStage "stage2" -outStage "stage3"

if (-not $SkipCompare) {
    Compare-StageExes "stage2" "stage3"
}

Write-Host ""
Write-Host "build done."
exit 0
