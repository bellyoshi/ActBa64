# run_test2.ps1 - actba64 で test/ をコンパイル & 実行
#
# 使い方:
#   .\run_test2.ps1                 # bin\stage1\actba64.exe（既定）
#   .\run_test2.ps1 stage0          # bin\stage0\actba64.exe（AB4.20 手動ビルド・64bit 出力）
#   .\run_test2.ps1 stage0 -Actba32 # 同上コンパイラで PE32 出力
#   .\run_test2.ps1 stage1
#   .\run_test2.ps1 stage2
#   .\run_test2.ps1 stage3          # 固定点確認用（日常テストは stage1/stage2 で十分）
#   .\run_test2.ps1 -Rebuild        # 先に build.ps1（stage1 は -Stage1Only。stage0 では無効）
#   .\run_test2.ps1 -Quiet
#   .\run_test2.ps1 -KeepArtifacts
#   .\run_test2.ps1 -IncludeGui     # ' Gui: 1 のテストも実行（既定はスキップ）
#   .\run_test2.ps1 -Actba32        # -actba32 で PE32 を出力して実行
#   .\run_test2.ps1 -Linker .\bin\stage1\actba64.exe
#
# stage0 注意: ソース変更のたびに自動更新されない。AB4.20 で actba64.pj を
#   bin\stage0\actba64.exe に手動ビルドすること。ホストは 32bit だが -Actba32 なしなら
#   64bit PE を生成する。失敗時は stage0 が古い可能性 → AB 再ビルド後に stage1 で切り分け。
#
# テスト対象: test\*.abp / test\*.pj のうち ' Target: actba64 があるもの
#   ' Expect: N        … 終了コード期待値（省略時 0）
#   ' Gui: 1           … 対話 UI 想定（MessageBox 等）。既定では SKIP（-IncludeGui で有効）
#   ' Target: actba64  … このランナーの対象（必須）
#   ' Skip32: 1        … -Actba32 時はスキップ（ポインタ幅に依存する SizeOf 等）
# スキップ内訳は Summary 直後に表示。残りはビルド不能（no Target）・pj 包含・GUI・32bit 制限。
# Print はコンソール WriteFile（Gui 自動判定なし）
# .pj の #SOURCE に載る .abp は単独ビルドしない

param(
    [Parameter(Position = 0)]
    [ValidateSet("stage0", "stage1", "stage2", "stage3")]
    [string]$Stage = "stage1",
    [string]$Linker = "",
    [int]$TimeoutSec = 5,
    [int]$GuiWaitMs = 800,
    [switch]$Rebuild,
    [switch]$Quiet,
    [switch]$ShowSkipped,
    [switch]$KeepArtifacts,
    [switch]$IncludeGui,
    [switch]$Actba32
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$TestDir = Join-Path $Root "test"
$OutDir = Join-Path $Root "bin\test_out"
Set-Location $Root

if (-not (Test-Path -LiteralPath $TestDir)) {
    Write-Error "test dir not found: $TestDir"
    exit 2
}

if ($Rebuild) {
    if ($Stage -eq "stage0") {
        Write-Warning "stage0 は AB4.20 で手動ビルドするため -Rebuild は無視します。bin\stage0\actba64.exe を更新してから再実行してください。"
    } else {
        $build = Join-Path $Root "build.ps1"
        if (-not (Test-Path -LiteralPath $build)) {
            Write-Error "build.ps1 not found"
            exit 2
        }
        $buildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $build, "-SkipCopy")
        if ($Stage -eq "stage1") {
            $buildArgs += "-Stage1Only"
        }
        & powershell @buildArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "build.ps1 failed"
            exit 1
        }
    }
}

if ($Linker -eq "") {
    $Linker = Join-Path $Root "bin\$Stage\actba64.exe"
}

if (-not (Test-Path -LiteralPath $Linker)) {
    if ($Stage -eq "stage0") {
        Write-Error "linker not found: $Linker (AB4.20 で actba64.pj を bin\stage0\ にビルドしてください)"
    } else {
        Write-Error "linker not found: $Linker (run .\build.ps1 first)"
    }
    exit 2
}

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

function Get-Meta([string]$path) {
    $expect = 0
    $gui = $null
    $target = $false
    $skip32 = $false
    $stdin = @()
    foreach ($line in (Get-Content -LiteralPath $path -Encoding Default -ErrorAction Stop)) {
        if ($line -match "^\s*'\s*Expect\s*:\s*(-?\d+)\s*$") {
            $expect = [int]$Matches[1]
        }
        if ($line -match "^\s*'\s*Gui\s*:\s*([01])\s*$") {
            $gui = [int]$Matches[1]
        }
        if ($line -match "(?i)^\s*'\s*Target\s*:\s*actba64\s*$") {
            $target = $true
        }
        if ($line -match "(?i)^\s*'\s*Skip32\s*:\s*1\s*$") {
            $skip32 = $true
        }
        if ($line -match "^\s*'\s*Stdin\s*:\s?(.*)$") {
            $stdin += $Matches[1]
        }
    }
    if ($null -eq $gui) {
        $gui = 0
    }
    return @{ Expect = $expect; Gui = $gui; Target = $target; Skip32 = $skip32; Stdin = $stdin }
}

function Get-PjOwnedAbp {
    $owned = @{}
    Get-ChildItem -LiteralPath $TestDir -Filter "*.pj" -File | ForEach-Object {
        $inSource = $false
        foreach ($line in (Get-Content -LiteralPath $_.FullName -Encoding Default)) {
            $t = $line.Trim()
            if ($t -match "^'") { continue }
            if ($t -match "(?i)^#SOURCE\s*$") { $inSource = $true; continue }
            if ($inSource) {
                if ($t -match "^#") { break }
                if ($t -ne "") {
                    $owned[$t.ToLowerInvariant()] = $_.Name
                }
            }
        }
    }
    return $owned
}

$stats = @{ pass = 0; fail = 0; skip = 0; skipNoTarget = 0; skipPj = 0; skipGui = 0; skip32Meta = 0; skipDouble32 = 0 }
$pjOwned = Get-PjOwnedAbp

function Add-Result([string]$name, [string]$status, [string]$detail) {
    if (-not $Quiet) {
        $color = switch ($status) {
            "PASS" { "Green" }
            "FAIL" { "Red" }
            "SKIP" { "Yellow" }
            default { "Gray" }
        }
        Write-Host ("[{0}] {1}  {2}" -f $status, $name, $detail) -ForegroundColor $color
    }
}

function Invoke-OneTest([string]$src, [string]$name, [hashtable]$meta) {
    if ($meta.Gui -eq 1 -and -not $IncludeGui) {
        $stats.skip++
        $stats.skipGui++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "gui (use -IncludeGui)"
        }
        return
    }
    if ($Actba32 -and $meta.Skip32) {
        $stats.skip++
        $stats.skip32Meta++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "skip32"
        }
        return
    }
    if ($Actba32 -and $name -match '(?i)^t_double') {
        $stats.skip++
        $stats.skipDouble32++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "double/sse32"
        }
        return
    }
    $exeName = [System.IO.Path]::GetFileNameWithoutExtension($name) + "_test.exe"
    $exePath = Join-Path $OutDir $exeName
    $stdinPath = $exePath + ".stdin"

    if (Test-Path -LiteralPath $exePath) {
        Remove-Item -LiteralPath $exePath -Force -ErrorAction SilentlyContinue
    }

    $ccArgs = @($src)
    if ($Actba32) {
        $ccArgs += "-actba32"
    }
    $ccArgs += "-o"
    $ccArgs += $exePath
    $log = & $Linker @ccArgs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exePath)) {
        $stats.fail++
        $hint = ($log | Select-Object -Last 3) -join " / "
        if ($hint -eq "") { $hint = "build failed (exit=$LASTEXITCODE)" }
        Add-Result $name "FAIL" $hint
        return
    }

    if ($meta.Gui -eq 1) {
        $proc = Start-Process -FilePath $exePath -WorkingDirectory $Root -PassThru -WindowStyle Hidden
        Start-Sleep -Milliseconds $GuiWaitMs
        if (-not $proc.HasExited) {
            try { Stop-Process -Id $proc.Id -Force } catch {}
            $stats.pass++
            Add-Result $name "PASS" "gui alive (MessageBox)"
        } else {
            $actual = $proc.ExitCode
            if ($actual -eq $meta.Expect) {
                $stats.pass++
                Add-Result $name "PASS" "exit=$actual (gui closed early)"
            } else {
                $stats.fail++
                Add-Result $name "FAIL" "exit=$actual expect=$($meta.Expect)"
            }
        }
    } else {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exePath
        $psi.WorkingDirectory = $Root
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.RedirectStandardInput = ($meta.Stdin.Count -gt 0)
        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $psi
        [void]$p.Start()
        $outTask = $p.StandardOutput.ReadToEndAsync()
        $errTask = $p.StandardError.ReadToEndAsync()
        if ($meta.Stdin.Count -gt 0) {
            foreach ($line in $meta.Stdin) {
                $p.StandardInput.WriteLine($line)
            }
            $p.StandardInput.Close()
        }
        $exited = $p.WaitForExit($TimeoutSec * 1000)
        if ($exited) {
            [void]$outTask.Wait(1000)
            [void]$errTask.Wait(1000)
        }
        if (-not $exited) {
            try { $p.Kill() } catch {}
            $stats.fail++
            Add-Result $name "FAIL" "timeout (${TimeoutSec}s) expect=$($meta.Expect)"
        } else {
            $actual = $p.ExitCode
            if ($actual -eq $meta.Expect) {
                $stats.pass++
                Add-Result $name "PASS" "exit=$actual"
            } else {
                $stats.fail++
                Add-Result $name "FAIL" "exit=$actual expect=$($meta.Expect)"
            }
        }
        $p.Dispose()
    }

    if (-not $KeepArtifacts) {
        Remove-Item -LiteralPath $exePath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stdinPath -Force -ErrorAction SilentlyContinue
    }
}

if (-not $Quiet) {
    Write-Host ""
    Write-Host "=== actba64 $Stage ==="
    Write-Host "linker: $Linker"
    Write-Host "tests:  $TestDir"
}

Get-ChildItem -LiteralPath $TestDir -Filter "*.abp" -File | Sort-Object Name | ForEach-Object {
    $src = $_.FullName
    $name = $_.Name
    $key = $name.ToLowerInvariant()
    if ($pjOwned.ContainsKey($key)) {
        $stats.skip++
        $stats.skipPj++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "covered by $($pjOwned[$key])"
        }
        return
    }
    $meta = Get-Meta $src
    if (-not $meta.Target) {
        $stats.skip++
        $stats.skipNoTarget++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "no Target: actba64"
        }
        return
    }
    Invoke-OneTest $src $name $meta
}

Get-ChildItem -LiteralPath $TestDir -Filter "*.pj" -File | Sort-Object Name | ForEach-Object {
    $src = $_.FullName
    $name = $_.Name
    $meta = Get-Meta $src
    if (-not $meta.Target) {
        $stats.skip++
        $stats.skipNoTarget++
        if ($ShowSkipped) {
            Add-Result $name "SKIP" "no Target: actba64"
        }
        return
    }
    Invoke-OneTest $src $name $meta
}

Write-Host ""
Write-Host ("Summary: {0} passed, {1} failed, {2} skipped (total {3})" -f `
    $stats.pass, $stats.fail, $stats.skip, ($stats.pass + $stats.fail + $stats.skip))
if ($stats.skip -gt 0) {
    $parts = @()
    if ($stats.skipNoTarget -gt 0) { $parts += ("{0} no Target" -f $stats.skipNoTarget) }
    if ($stats.skipPj -gt 0) { $parts += ("{0} pj-covered" -f $stats.skipPj) }
    if ($stats.skipGui -gt 0) { $parts += ("{0} gui (-IncludeGui)" -f $stats.skipGui) }
    if ($stats.skip32Meta -gt 0) { $parts += ("{0} Skip32" -f $stats.skip32Meta) }
    if ($stats.skipDouble32 -gt 0) { $parts += ("{0} double/sse32" -f $stats.skipDouble32) }
    Write-Host ("  skipped: {0}" -f ($parts -join ", "))
}

if ($stats.fail -gt 0) { exit 1 }
exit 0
