# run_test2.ps1 - test/ 全ソースを abpc でコンパイル & 実行
# 使い方:
#   .\run_test2.ps1                      # bin\stage0\abpc.exe（既定）
#   .\run_test2.ps1 stage0
#   .\run_test2.ps1 stage1
#   .\run_test2.ps1 stage2
#   .\run_test2.ps1 stage0 stage1 stage2 # 複数ステージを順に実行
#   .\run_test2.ps1 stage1 -Quiet
#   .\run_test2.ps1 -Abpc .\bin\stage2\abpc.exe
#   .\run_test2.ps1 -KeepArtifacts
#
# t_ 付きでなくても .abp / .pj はすべてテスト対象。
# ' Expect: N があれば終了コードを比較。無ければ 0 を期待。

param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [ValidateSet("stage0", "stage1", "stage2")]
    [string[]]$Stage = @("stage0"),
    [string]$Abpc = "",
    [int]$TimeoutSec = 5,
    [switch]$Quiet,
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$TestDir = Join-Path $Root "test"
Set-Location $Root

if (-not (Test-Path -LiteralPath $TestDir)) {
    Write-Error "test dir not found: $TestDir"
    exit 2
}

function Get-Expect([string]$path) {
    foreach ($line in (Get-Content -LiteralPath $path -Encoding Default -ErrorAction Stop)) {
        if ($line -match "^\s*'\s*Expect\s*:\s*(-?\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    return 0
}

# .pj の #SOURCE に載る .abp は単独ビルドしない（.pj 側でまとめて実行）
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

function Invoke-StageTests {
    param(
        [string]$AbpcPath,
        [string]$Label
    )

    $stats = @{ pass = 0; fail = 0; skip = 0 }

    if (-not (Test-Path -LiteralPath $AbpcPath)) {
        Write-Error "abpc not found: $AbpcPath"
        return 2
    }

    if (-not $Quiet) {
        Write-Host ""
        Write-Host "=== $Label ==="
        Write-Host "abpc: $AbpcPath"
    }

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

    function Invoke-RunExe([string]$exePath, [int]$expect, [string]$displayName) {
        $proc = Start-Process -FilePath $exePath -WorkingDirectory $Root -PassThru -WindowStyle Hidden
        $exited = $proc.WaitForExit($TimeoutSec * 1000)
        if (-not $exited) {
            try { $proc.Kill() } catch {}
            $stats.fail++
            Add-Result $displayName "FAIL" "timeout (${TimeoutSec}s) expect=$expect"
            return
        }
        $actual = $proc.ExitCode
        if ($actual -eq $expect) {
            $stats.pass++
            Add-Result $displayName "PASS" "exit=$actual"
        } else {
            $stats.fail++
            Add-Result $displayName "FAIL" "exit=$actual expect=$expect"
        }
    }

    function Clear-Artifacts([string]$exePath) {
        if ($KeepArtifacts) { return }
        Remove-Item -LiteralPath $exePath -ErrorAction SilentlyContinue
        $base = [System.IO.Path]::GetFileNameWithoutExtension($exePath)
        Remove-Item -LiteralPath (Join-Path $Root "$base.asm") -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $Root "$base.obj") -ErrorAction SilentlyContinue
    }

    Get-ChildItem -LiteralPath $TestDir -Filter "*.abp" -File | Sort-Object Name | ForEach-Object {
        $key = $_.Name.ToLowerInvariant()
        if ($pjOwned.ContainsKey($key)) {
            $stats.skip++
            Add-Result $_.Name "SKIP" "covered by $($pjOwned[$key])"
            return
        }

        $expect = Get-Expect $_.FullName
        $exeName = [System.IO.Path]::GetFileNameWithoutExtension($_.Name) + "_test.exe"
        $exePath = Join-Path $Root $exeName
        $relIn = Resolve-Path -LiteralPath $_.FullName -Relative

        & $AbpcPath $relIn $exeName 2>&1 | Out-Null
        if (-not (Test-Path -LiteralPath $exePath)) {
            $stats.fail++
            Add-Result $_.Name "FAIL" "build failed"
            return
        }

        Invoke-RunExe $exePath $expect $_.Name
        Clear-Artifacts $exePath
    }

    Get-ChildItem -LiteralPath $TestDir -Filter "*.pj" -File | Sort-Object Name | ForEach-Object {
        $expect = Get-Expect $_.FullName
        $pjDir = $_.DirectoryName
        $outMatch = Select-String -LiteralPath $_.FullName -Pattern "(?i)^#OUTPUT_RELEASE=(.+)$" |
            Select-Object -First 1
        if ($outMatch) {
            $exeRel = $outMatch.Matches[0].Groups[1].Value.Trim() -replace '^\.\\', ''
            $exePath = Join-Path $pjDir $exeRel
        } else {
            $exePath = Join-Path $pjDir ([System.IO.Path]::GetFileNameWithoutExtension($_.Name) + ".exe")
        }

        $relPj = Resolve-Path -LiteralPath $_.FullName -Relative
        & $AbpcPath $relPj 2>&1 | Out-Null
        if (-not (Test-Path -LiteralPath $exePath)) {
            $stats.fail++
            Add-Result $_.Name "FAIL" "build failed"
            return
        }

        Invoke-RunExe $exePath $expect $_.Name
        if (-not $KeepArtifacts) {
            Remove-Item -LiteralPath $exePath -ErrorAction SilentlyContinue
        }
    }

    Write-Host ""
    Write-Host ("Summary ($Label): {0} passed, {1} failed, {2} skipped (total {3})" -f `
        $stats.pass, $stats.fail, $stats.skip, ($stats.pass + $stats.fail + $stats.skip))

    if ($stats.fail -gt 0) { return 1 }
    return 0
}

# -Abpc 指定時は単発（Stage は無視）
if ($Abpc -ne "") {
    exit (Invoke-StageTests -AbpcPath $Abpc -Label $Abpc)
}

$stages = @($Stage | Select-Object -Unique)
if ($stages.Count -eq 0) {
    $stages = @("stage0")
}

$overall = 0
foreach ($s in $stages) {
    $path = Join-Path $Root "bin\$s\abpc.exe"
    $code = Invoke-StageTests -AbpcPath $path -Label $s
    if ($code -ne 0) { $overall = $code }
}

if ($stages.Count -gt 1) {
    Write-Host ""
    if ($overall -eq 0) {
        Write-Host ("All stages OK: {0}" -f ($stages -join ", "))
    } else {
        Write-Host ("Some stages FAILED: {0}" -f ($stages -join ", "))
    }
}

exit $overall
