# build.ps1 - リリース一式を release\ に揃える
#
#   既定: actba32 自己ホスト → actba64 ブートストラップ → ProjectEditor → コピー
#   -SkipSelfHost: 既存 stage2 を使い、ProjectEditor 再コンパイルとコピーのみ
#   -SkipCompare: 子スクリプトのバイナリ比較をスキップ
#
# 使い方:
#   .\build.ps1
#   .\build.ps1 -SkipSelfHost
#   .\build.ps1 -SkipCompare

param(
    [switch]$SkipSelfHost,
    [switch]$SkipCompare
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$Actba32Dir = Join-Path $Root "src\actba32"
$Actba64Dir = Join-Path $Root "src\actba64"
$EditorDir = Join-Path $Root "src\projecteditor"
$ReleaseDir = Join-Path $Root "release"

$Actba32Stage2 = Join-Path $Actba32Dir "bin\stage2"
$Actba64Stage2 = Join-Path $Actba64Dir "bin\stage2"
$Actba64Exe = Join-Path $Actba64Stage2 "actba64.exe"
$IncludeSrc = Join-Path $Root "src\Include"
$HelpSrc = Join-Path $EditorDir "help"
$EditorPj = Join-Path $EditorDir "ProjectEditor.pj"

$Actba32Tools = @("actba32.exe", "abc.exe", "abassembler.exe", "ablinker.exe")
$EditorWbp = @("Callback.wbp", "MakeWindow.wbp")

function Invoke-ChildScript([string]$scriptPath, [string[]]$scriptArgs) {
    Write-Host ""
    Write-Host "=== $scriptPath $($scriptArgs -join ' ') ==="
    & $scriptPath @scriptArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "failed: $scriptPath exit=$LASTEXITCODE"
        exit 1
    }
}

function Assert-File([string]$path, [string]$hint) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Error "$hint : $path"
        exit 2
    }
}

function Copy-LockedAware([string]$src, [string]$dst) {
    try {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    } catch {
        Write-Error "copy failed (close ProjectEditor if it is running from release\): $dst`n$($_.Exception.Message)"
        exit 1
    }
}

if (-not $SkipSelfHost) {
    $selfArgs = @()
    $actba64Args = @()
    if ($SkipCompare) {
        $selfArgs += "-SkipCompare"
        $actba64Args += "-SkipCompare"
    }
    Invoke-ChildScript (Join-Path $Actba32Dir "selfbuild.ps1") $selfArgs
    Invoke-ChildScript (Join-Path $Actba64Dir "build.ps1") $actba64Args
}

foreach ($t in $Actba32Tools) {
    Assert-File (Join-Path $Actba32Stage2 $t) "actba32 stage2 missing (run without -SkipSelfHost, and keep src\actba32\bin\stage0)"
}
Assert-File $Actba64Exe "actba64 stage2 missing (run without -SkipSelfHost)"
Assert-File $IncludeSrc "Include missing"
Assert-File $EditorPj "ProjectEditor project missing"
Assert-File $HelpSrc "help missing"

foreach ($w in $EditorWbp) {
    Assert-File (Join-Path $EditorDir $w) "ProjectEditor RAD file missing (not in repo; needed to compile the editor)"
}

$tmpEditor = Join-Path $EditorDir "_release_ProjectEditor.exe"
if (Test-Path -LiteralPath $tmpEditor) {
    Remove-Item -LiteralPath $tmpEditor -Force
}

Write-Host ""
Write-Host "=== ProjectEditor.pj -> $tmpEditor ==="
Push-Location $EditorDir
try {
    $log = & $Actba64Exe $EditorPj -o $tmpEditor 2>&1 | ForEach-Object { "$_" }
    $code = [int]$LASTEXITCODE
} finally {
    Pop-Location
}
foreach ($line in $log) { Write-Host $line }
if ($code -ne 0 -or -not (Test-Path -LiteralPath $tmpEditor)) {
    Write-Error "ProjectEditor build failed exit=$code"
    exit 1
}

try {
    if (Test-Path -LiteralPath $ReleaseDir) {
        Remove-Item -LiteralPath $ReleaseDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
} catch {
    Write-Error "cannot recreate release\ (close ProjectEditor if it is running from release\): $($_.Exception.Message)"
    exit 1
}

Copy-LockedAware $tmpEditor (Join-Path $ReleaseDir "ProjectEditor.exe")
Remove-Item -LiteralPath $tmpEditor -Force

Copy-Item -LiteralPath $Actba64Exe -Destination (Join-Path $ReleaseDir "actba64.exe") -Force
foreach ($t in $Actba32Tools) {
    Copy-Item -LiteralPath (Join-Path $Actba32Stage2 $t) -Destination (Join-Path $ReleaseDir $t) -Force
}

Copy-Item -LiteralPath $IncludeSrc -Destination (Join-Path $ReleaseDir "Include") -Recurse -Force
Copy-Item -LiteralPath $HelpSrc -Destination (Join-Path $ReleaseDir "help") -Recurse -Force

Write-Host ""
Write-Host "release ready: $ReleaseDir"
Get-ChildItem -LiteralPath $ReleaseDir | ForEach-Object { Write-Host ("  {0}" -f $_.Name) }
exit 0
