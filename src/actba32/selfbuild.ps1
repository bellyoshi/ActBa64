# selfbuild.ps1 - stage0 から stage1 / stage2 を自動ビルド
#
# 前提: bin\stage0\ に actba32 / abc / abassembler / ablinker があること
#       （人間が ab420 等でビルド済み）。各ステージは driver のツール一式だけで次を組む。
#
# 使い方:
#   .\selfbuild.ps1
#   .\selfbuild.ps1 -Stage1Only
#   .\selfbuild.ps1 -SkipCompare

param(
    [switch]$Stage1Only,
    [switch]$SkipCompare
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$Tools = @(
    @{ Name = "abc";         Pj = "abc.pj";         Exe = "abc.exe" }
    @{ Name = "abassembler"; Pj = "abassembler.pj"; Exe = "abassembler.exe" }
    @{ Name = "ablinker";    Pj = "ablinker.pj";    Exe = "ablinker.exe" }
    @{ Name = "actba32";     Pj = "actba32.pj";     Exe = "actba32.exe" }
)

function Get-StageDir([string]$stage) {
    return Join-Path $Root "bin\$stage"
}

function Assert-Stage0 {
    $dir = Get-StageDir "stage0"
    if (-not (Test-Path -LiteralPath $dir)) {
        Write-Error "stage0 not found: $dir"
        exit 2
    }
    # 旧名 abpc.exe からの移行
    $legacy = Join-Path $dir "abpc.exe"
    $driver = Join-Path $dir "actba32.exe"
    if ((Test-Path -LiteralPath $legacy) -and -not (Test-Path -LiteralPath $driver)) {
        Write-Host "=== migrate stage0: abpc.exe -> actba32.exe ==="
        Move-Item -LiteralPath $legacy -Destination $driver
    }
    foreach ($t in $Tools) {
        $p = Join-Path $dir $t.Exe
        if (-not (Test-Path -LiteralPath $p)) {
            Write-Error "stage0 missing: $p (build with ab420 first)"
            exit 2
        }
    }
    foreach ($t in $Tools) {
        $pj = Join-Path $Root $t.Pj
        if (-not (Test-Path -LiteralPath $pj)) {
            Write-Error "project not found: $pj"
            exit 2
        }
    }
}

function Ensure-Dir([string]$dir) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

function Sync-StageInclude([string]$stage) {
    $shared = Join-Path $Root "..\Include"
    $stageDir = Get-StageDir $stage
    $incDst = Join-Path $stageDir "Include"
    if (-not (Test-Path -LiteralPath $shared)) {
        Write-Error "shared Include not found: $shared"
        exit 2
    }
    Ensure-Dir $stageDir
    if (Test-Path -LiteralPath $incDst) {
        Remove-Item -LiteralPath $incDst -Recurse -Force
    }
    Write-Host "=== copy src\Include -> bin\$stage\Include ==="
    Copy-Item -LiteralPath $shared -Destination $incDst -Recurse
}

function Invoke-OneTool([string]$driverAbpc, [string]$pj, [string]$relOut, [string]$outPath) {
    $beforeTime = [datetime]::MinValue
    $beforeLen = -1
    if (Test-Path -LiteralPath $outPath) {
        $prev = Get-Item -LiteralPath $outPath
        $beforeTime = $prev.LastWriteTimeUtc
        $beforeLen = $prev.Length
    }

    Write-Host ""
    Write-Host "-- $($pj): -o $relOut"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $driverAbpc $pj -o $relOut 2>&1 | ForEach-Object { "$_" }
    $sw.Stop()
    $code = [int]$LASTEXITCODE

    foreach ($line in $log) { Write-Host $line }

    $joined = [string]::Join("`n", @($log))
    $okLine = $joined -match "(?i)OK:.*->"
    $failHint = $joined -match "(?im)^(?:error:|.*\b(?:abc fail|asm fail|link fail|cannot )).*"

    if ($code -ne 0 -or $failHint -or -not (Test-Path -LiteralPath $outPath)) {
        if ($joined -match "(?i)too many Const \(max 256\)") {
            Write-Host ""
            Write-Host "stage0\abc.exe is too old (Const limit: 256)." -ForegroundColor Yellow
            Write-Host "Open abc.pj with ActiveBasic 4.20 and rebuild bin\stage0\abc.exe,"
            Write-Host "then run selfbuild.ps1 again. Other stage0 tools do not need rebuilding."
        }
        Write-Error "build failed: $pj -> $relOut exit=$code"
        exit 1
    }
    $fi = Get-Item -LiteralPath $outPath
    if ($fi.LastWriteTimeUtc -le $beforeTime -and $fi.Length -eq $beforeLen) {
        Write-Error "output was not updated: $outPath"
        exit 1
    }
    if (-not $okLine) {
        Write-Host "warning: no OK line (GUI host may hide stdout); file updated ok"
    }
    Write-Host ("OK: {0} ({1} bytes, {2}s)" -f $outPath, $fi.Length, [math]::Round($sw.Elapsed.TotalSeconds, 2))
}

function Invoke-StageBuild([string]$driverStage, [string]$outStage) {
    $driverDir = Get-StageDir $driverStage
    $driver = Join-Path $driverDir "actba32.exe"
    $outDir = Get-StageDir $outStage
    Ensure-Dir $outDir
    Sync-StageInclude $driverStage

    if (-not (Test-Path -LiteralPath $driver)) {
        Write-Error "driver not found: $driver"
        exit 1
    }

    Write-Host ""
    Write-Host "=== $driverStage -> $outStage ==="
    Write-Host "driver: $driver"

    foreach ($t in $Tools) {
        Invoke-OneTool -driverAbpc $driver -pj $t.Pj `
            -relOut ("bin\$outStage\$($t.Exe)") `
            -outPath (Join-Path $outDir $t.Exe)
    }
}

function Compare-Stages([string]$a, [string]$b) {
    Write-Host ""
    Write-Host "=== compare $a vs $b ==="
    $allMatch = $true
    foreach ($t in $Tools) {
        $pa = Join-Path (Get-StageDir $a) $t.Exe
        $pb = Join-Path (Get-StageDir $b) $t.Exe
        if (-not (Test-Path -LiteralPath $pa) -or -not (Test-Path -LiteralPath $pb)) {
            Write-Host ("MISS  {0}" -f $t.Exe)
            $allMatch = $false
            continue
        }
        $ha = (Get-FileHash -Algorithm SHA256 -LiteralPath $pa).Hash
        $hb = (Get-FileHash -Algorithm SHA256 -LiteralPath $pb).Hash
        $sa = (Get-Item -LiteralPath $pa).Length
        $sb = (Get-Item -LiteralPath $pb).Length
        if ($ha -eq $hb) {
            Write-Host ("MATCH {0} ({1} bytes)" -f $t.Exe, $sa)
        } else {
            Write-Host ("DIFF  {0} ({1} vs {2} bytes)" -f $t.Exe, $sa, $sb)
            $allMatch = $false
        }
    }
    if ($allMatch) {
        Write-Host "PASS: $a and $b binaries match (SHA256)"
        return 0
    } else {
        Write-Host "NOTE: $a and $b differ (self-host not bit-identical yet)"
        return 1
    }
}

Assert-Stage0
Invoke-StageBuild -driverStage "stage0" -outStage "stage1"

if (-not $Stage1Only) {
    Invoke-StageBuild -driverStage "stage1" -outStage "stage2"
    if (-not $SkipCompare) {
        $diff = Compare-Stages "stage1" "stage2"
        # 不一致でもビルド自体は成功。比較結果だけ伝える。
        if ($diff -ne 0) {
            Write-Host ""
            Write-Host "selfbuild done (binaries differ)."
            exit 0
        }
    }
}

Write-Host ""
Write-Host "selfbuild done."
exit 0
