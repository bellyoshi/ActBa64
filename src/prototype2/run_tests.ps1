# run_tests.ps1 - abpc 回帰テスト
# 使い方:
#   .\run_tests.ps1
#   .\run_tests.ps1 -Filter "t_neg*"
#   .\run_tests.ps1 -Filter "t2*" -Quiet
#
# 各テストの先頭付近の ' Expect: N を読み、
# abpc で exe を作り、実行して終了コードを比較する。

param(
    [string]$Filter = "t*.abp",
    [string]$Abpc = ".\abpc.exe",
    [int]$TimeoutSec = 5,
    [switch]$Quiet,
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
Set-Location $Root

if (-not (Test-Path $Abpc)) {
    Write-Error "abpc not found: $Abpc"
    exit 2
}

function Get-Expect([string]$path) {
    $lines = Get-Content -LiteralPath $path -Encoding Default -ErrorAction Stop
    foreach ($line in $lines) {
        if ($line -match "^\s*'\s*Expect\s*:\s*(-?\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    return $null
}

function Test-HasMessageBox([string]$path) {
    $text = Get-Content -LiteralPath $path -Raw -Encoding Default
    return $text -match "(?i)\bMessageBox\s*\("
}

# .pj の #SOURCE に含まれる副ソース（単体ビルド対象外）
function Get-PjSecondarySources {
    $secondaries = @{}
    Get-ChildItem -LiteralPath $Root -Filter "*.pj" | ForEach-Object {
        $inSource = $false
        $sources = @()
        foreach ($line in (Get-Content -LiteralPath $_.FullName -Encoding Default)) {
            $t = $line.Trim()
            if ($t -match "^'") { continue }
            if ($t -match "(?i)^#SOURCE\s*$") {
                $inSource = $true
                continue
            }
            if ($inSource) {
                if ($t -match "^#") { break }
                if ($t -ne "") { $sources += $t }
            }
        }
        if ($sources.Count -gt 1) {
            for ($i = 0; $i -lt $sources.Count - 1; $i++) {
                $secondaries[$sources[$i].ToLowerInvariant()] = $true
            }
            # メイン以外も副扱い: 複数ソースのときは単独 .abp をスキップし .pj 側で実行
            foreach ($s in $sources) {
                $secondaries[$s.ToLowerInvariant()] = $_.Name
            }
        }
    }
    return $secondaries
}

$pjOwned = Get-PjSecondarySources

$pass = 0
$fail = 0
$skip = 0
$results = @()

function Add-Result($name, $status, $detail) {
    $script:results += [pscustomobject]@{ Name = $name; Status = $status; Detail = $detail }
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

function Invoke-OneTest([string]$inputPath, [string]$exePath, [int]$expect, [string]$displayName) {
    $relIn = Resolve-Path -LiteralPath $inputPath -Relative
    $relExe = [System.IO.Path]::GetFileName($exePath)
    $buildOut = & $Abpc $relIn $relExe 2>&1 | Out-String
    if (-not (Test-Path -LiteralPath $exePath)) {
        $script:fail++
        Add-Result $displayName "FAIL" "build failed"
        if (-not $Quiet) {
            Write-Host $buildOut
        }
        return
    }

    $proc = Start-Process -FilePath $exePath -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    $exited = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $exited) {
        try { $proc.Kill() } catch {}
        $script:fail++
        Add-Result $displayName "FAIL" "timeout (${TimeoutSec}s) expect=$expect"
        return
    }

    $actual = $proc.ExitCode
    if ($actual -eq $expect) {
        $script:pass++
        Add-Result $displayName "PASS" "exit=$actual"
    } else {
        $script:fail++
        Add-Result $displayName "FAIL" "exit=$actual expect=$expect"
    }

    if (-not $KeepArtifacts) {
        Remove-Item -LiteralPath $exePath -ErrorAction SilentlyContinue
        $base = [System.IO.Path]::GetFileNameWithoutExtension($exePath)
        Remove-Item -LiteralPath (Join-Path $Root "$base.asm") -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $Root "$base.obj") -ErrorAction SilentlyContinue
    }
}

# --- .abp テスト ---
$abpFiles = Get-ChildItem -LiteralPath $Root -Filter $Filter |
    Where-Object { $_.Extension -eq ".abp" } |
    Sort-Object Name

foreach ($f in $abpFiles) {
    $expect = Get-Expect $f.FullName
    if ($null -eq $expect) {
        continue
    }

    $key = $f.Name.ToLowerInvariant()
    if ($pjOwned.ContainsKey($key)) {
        $skip++
        Add-Result $f.Name "SKIP" "covered by $($pjOwned[$key])"
        continue
    }

    if (Test-HasMessageBox $f.FullName) {
        $skip++
        Add-Result $f.Name "SKIP" "MessageBox (interactive)"
        continue
    }

    $exeName = [System.IO.Path]::GetFileNameWithoutExtension($f.Name) + "_test.exe"
    $exePath = Join-Path $Root $exeName
    Invoke-OneTest $f.FullName $exePath $expect $f.Name
}

# --- Expect 付き .pj（複数ソース）。Filter がデフォルトか *.pj のときだけ ---
$runPj = ($Filter -eq "t*.abp") -or ($Filter -like "*.pj") -or ($Filter -eq "*")
if ($runPj) {
Get-ChildItem -LiteralPath $Root -Filter "*.pj" | Sort-Object Name | ForEach-Object {
    if ($Filter -like "*.pj" -and $_.Name -notlike $Filter) { return }
    $expect = Get-Expect $_.FullName
    if ($null -eq $expect) { return }

    $outMatch = Select-String -LiteralPath $_.FullName -Pattern "(?i)^#OUTPUT_RELEASE=(.+)$" |
        Select-Object -First 1
    if ($outMatch) {
        $exeRel = $outMatch.Matches[0].Groups[1].Value.Trim()
        $exePath = Join-Path $Root ($exeRel -replace '^\.\\', '')
    } else {
        $exePath = Join-Path $Root ([System.IO.Path]::GetFileNameWithoutExtension($_.Name) + ".exe")
    }

    # abpc project.pj は第2引数を取らない
    $relPj = Resolve-Path -LiteralPath $_.FullName -Relative
    $buildOut = & $Abpc $relPj 2>&1 | Out-String
    if (-not (Test-Path -LiteralPath $exePath)) {
        $script:fail++
        Add-Result $_.Name "FAIL" "build failed"
        if (-not $Quiet) { Write-Host $buildOut }
        return
    }

    $proc = Start-Process -FilePath $exePath -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    $exited = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $exited) {
        try { $proc.Kill() } catch {}
        $script:fail++
        Add-Result $_.Name "FAIL" "timeout (${TimeoutSec}s) expect=$expect"
        return
    }

    $actual = $proc.ExitCode
    if ($actual -eq $expect) {
        $script:pass++
        Add-Result $_.Name "PASS" "exit=$actual"
    } else {
        $script:fail++
        Add-Result $_.Name "FAIL" "exit=$actual expect=$expect"
    }
}
} # end if $runPj

Write-Host ""
Write-Host ("Summary: {0} passed, {1} failed, {2} skipped (total {3})" -f $pass, $fail, $skip, ($pass + $fail + $skip))

if ($fail -gt 0) { exit 1 } else { exit 0 }
