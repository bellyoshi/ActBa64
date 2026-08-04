# selfbuild.ps1 - stage0 から stage1 / stage2 を自動ビルド
#
# 前提: bin\stage0\ に abpc / abc / abassembler / ablinker があること（ab420 製）。
#       stage0 の abpc は -o 対応ソースでビルド済みであること。
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
    @{ Name = "abpc";        Pj = "abpc.pj";        Exe = "abpc.exe" }
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
    $failHint = $joined -match "(?i)abc fail|asm fail|link fail|cannot |not found:|error:"

    if ($code -ne 0 -or $failHint -or -not (Test-Path -LiteralPath $outPath)) {
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
    $driver = Join-Path $driverDir "abpc.exe"
    $outDir = Get-StageDir $outStage
    Ensure-Dir $outDir

    if (-not (Test-Path -LiteralPath $driver)) {
        Write-Error "driver not found: $driver"
        exit 1
    }

    Write-Host ""
    Write-Host "=== $driverStage -> $outStage ==="
    Write-Host "driver: $driver"

    # 1) abc を先にビルド（配列 Word ロード等の codegen 修正を取り込み）
    $abcTool = $Tools | Where-Object { $_.Name -eq "abc" } | Select-Object -First 1
    Invoke-OneTool -driverAbpc $driver -pj $abcTool.Pj `
        -relOut ("bin\$outStage\$($abcTool.Exe)") `
        -outPath (Join-Path $outDir $abcTool.Exe)

    # 2) 新 abc + driver の as/link/abpc で残りをビルド
    #    （古い abc で as を組むと Word 配列ロードが壊れ、前方ラベル解決に失敗する）
    $hybrid = Join-Path $Root "bin\hybrid_$outStage"
    Ensure-Dir $hybrid
    Copy-Item -LiteralPath (Join-Path $driverDir "abpc.exe") -Destination $hybrid -Force
    Copy-Item -LiteralPath (Join-Path $driverDir "abassembler.exe") -Destination $hybrid -Force
    Copy-Item -LiteralPath (Join-Path $driverDir "ablinker.exe") -Destination $hybrid -Force
    Copy-Item -LiteralPath (Join-Path $outDir "abc.exe") -Destination $hybrid -Force
    $hybridAbpc = Join-Path $hybrid "abpc.exe"
    Write-Host ""
    Write-Host "hybrid driver: $hybridAbpc (abc from $outStage)"

    $rest = @($Tools | Where-Object { $_.Name -ne "abc" })
    $jobs = @()
    foreach ($t in $rest) {
        $outPath = Join-Path $outDir $t.Exe
        $relOut = "bin\$outStage\$($t.Exe)"
        $pj = $t.Pj
        $name = $t.Name

        $beforeTime = [datetime]::MinValue
        $beforeLen = -1
        if (Test-Path -LiteralPath $outPath) {
            $prev = Get-Item -LiteralPath $outPath
            $beforeTime = $prev.LastWriteTimeUtc
            $beforeLen = $prev.Length
        }

        Write-Host ""
        Write-Host "-- start $($t.Name): $pj -o $relOut"

        $jobs += [pscustomobject]@{
            Name = $name
            OutPath = $outPath
            RelOut = $relOut
            BeforeTime = $beforeTime
            BeforeLen = $beforeLen
            Sw = [Diagnostics.Stopwatch]::StartNew()
            Job = Start-Job -ScriptBlock {
                param($Root, $Driver, $Pj, $RelOut)
                Set-Location $Root
                $log = & $Driver $Pj -o $RelOut 2>&1 | ForEach-Object { "$_" }
                return [pscustomobject]@{
                    Code = $LASTEXITCODE
                    Log = $log
                }
            } -ArgumentList $Root, $hybridAbpc, $pj, $relOut
        }
    }

    $failed = $false
    foreach ($j in $jobs) {
        $result = Receive-Job -Job $j.Job -Wait
        Remove-Job -Job $j.Job -Force
        $j.Sw.Stop()

        $log = @($result.Log)
        foreach ($line in $log) { Write-Host $line }

        $joined = [string]::Join("`n", $log)
        $okLine = $joined -match "(?i)OK:.*->"
        $failHint = $joined -match "(?i)abc fail|asm fail|link fail|cannot |not found:|error:"
        $code = [int]$result.Code

        if ($code -ne 0 -or $failHint -or -not (Test-Path -LiteralPath $j.OutPath)) {
            Write-Host "build failed: $driverStage -> $outStage ($($j.Name)) exit=$code"
            $failed = $true
            continue
        }
        $fi = Get-Item -LiteralPath $j.OutPath
        if ($fi.LastWriteTimeUtc -le $j.BeforeTime -and $fi.Length -eq $j.BeforeLen) {
            Write-Host "output was not updated: $($j.OutPath)"
            $failed = $true
            continue
        }
        if (-not $okLine) {
            Write-Host "warning: no OK line (GUI host may hide stdout); file updated ok"
        }
        Write-Host ("OK: {0} ({1} bytes, {2}s)" -f $j.OutPath, $fi.Length, [math]::Round($j.Sw.Elapsed.TotalSeconds, 2))
    }

    if ($failed) {
        Write-Error "build failed: $driverStage -> $outStage"
        exit 1
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
