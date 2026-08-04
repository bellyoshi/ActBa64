# selfhost_abpc.ps1 - ソースを selfhost\ に展開し、そこで abpc を自己ホストビルド
#
# 直下の abpc/abc/abassembler/ablinker.exe は当面 ab420(GUI) 製ホスト。
# .pj の #OUTPUT_RELEASE は直下相対（.\xxx.exe）。セルフホストは selfhost\ 上でビルドする。
# 詳細は README.md。
#
# 使い方:
#   .\selfhost_abpc.ps1
#   .\selfhost_abpc.ps1 -Pass2
#   .\selfhost_abpc.ps1 -Abpc .\abpc.exe

param(
    [string]$Abpc = "",
    [string]$Project = ".\abpc.pj",
    [string]$OutExe = ".\abpc.exe",
    [switch]$Pass2,
    [switch]$SkipStage
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$OutDir = Join-Path $Root "selfhost"
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# ツールソース（.pj の #SOURCE + 索引）
$ToolFiles = @(
    "Utils.abp", "Common.abp", "FileIO.abp", "StringBuffer.abp",
    "coff.abp", "pe.abp",
    "abcGlobals.abp", "abcLexer.abp", "abcParser.abp", "abcEmit.abp", "abc.abp",
    "abassembler.abp", "ablinker.abp", "abpc.abp",
    "abc.pj", "abc2.pj", "abassembler.pj", "ablinker.pj", "abpc.pj",
    "abc.idx", "abassembler.idx", "ablinker.idx", "abpc.idx",
    "hello.abp", "run_tests.ps1"
)

$HostExes = @("abpc.exe", "abc.exe", "abassembler.exe", "ablinker.exe")

function Sync-SelfHostTree {
    Write-Host "=== stage sources -> selfhost\ ==="

    foreach ($name in $ToolFiles) {
        $src = Join-Path $Root $name
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $OutDir $name) -Force
        }
    }

    $includeSrc = Join-Path $Root "Include"
    $includeDst = Join-Path $OutDir "Include"
    if (Test-Path -LiteralPath $includeSrc) {
        if (Test-Path -LiteralPath $includeDst) {
            Remove-Item -LiteralPath $includeDst -Recurse -Force
        }
        Copy-Item -LiteralPath $includeSrc -Destination $includeDst -Recurse -Force
    }

    $testSrc = Join-Path $Root "test"
    $testDst = Join-Path $OutDir "test"
    if (Test-Path -LiteralPath $testSrc) {
        if (Test-Path -LiteralPath $testDst) {
            Remove-Item -LiteralPath $testDst -Recurse -Force
        }
        Copy-Item -LiteralPath $testSrc -Destination $testDst -Recurse -Force
    }

    foreach ($name in $HostExes) {
        $src = Join-Path $Root $name
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Error "missing host tool: $src"
            exit 2
        }
        Copy-Item -LiteralPath $src -Destination (Join-Path $OutDir $name) -Force
    }

    Write-Host "staged: tools, Include\, test\, host exes"
    Write-Host ""
}

if (-not $SkipStage) {
    Sync-SelfHostTree
}

# 以降は selfhost\ をカレントにビルド（#OUTPUT_RELEASE=.\xxx.exe → selfhost\xxx.exe）
Set-Location $OutDir

if ($Abpc -eq "") {
    if (Test-Path ".\abpc.exe") { $Abpc = ".\abpc.exe" }
}

if (-not (Test-Path $Abpc)) {
    Write-Error "abpc driver not found in selfhost\: $Abpc"
    exit 2
}
foreach ($req in @($Project, ".\abc.exe", ".\abassembler.exe", ".\ablinker.exe")) {
    if (-not (Test-Path $req)) {
        Write-Error "missing in selfhost\: $req"
        exit 2
    }
}

function Repair-MidRuntime([string]$asmPath) {
    if (-not (Test-Path $asmPath)) { return $false }
    $t = [IO.File]::ReadAllText((Resolve-Path $asmPath)) -replace "`r`n", "`n"
    $n = 0
    $pairs = @(
        @(
            "rt_mid_start_ok:`n    add ebx, 4`n    mov edx, [ebx]`n    push edi`n    call _lstrlenA@4`n    sub eax, esi",
            "rt_mid_start_ok:`n    add ebx, 4`n    mov edx, [ebx]`n    push edx`n    push edi`n    call _lstrlenA@4`n    pop edx`n    sub eax, esi"
        ),
        @(
            "    push eax`n    call _GetProcessHeap@0`n    push esi`n    push 0`n    push eax`n    call _HeapAlloc@12`n    mov ebx, eax`n    mov edx, eax`nrt_mid_loop:",
            "    push eax`n    call _GetProcessHeap@0`n    pop ecx`n    push ecx`n    push 0`n    push eax`n    call _HeapAlloc@12`n    mov ebx, eax`n    mov edx, eax`nrt_mid_loop:"
        ),
        @(
            "    push eax`n    call _GetProcessHeap@0`n    push esi`n    push 0`n    push eax`n    call _HeapAlloc@12`n    mov ebx, eax`n    mov edx, eax`nrt_left_loop:",
            "    push eax`n    call _GetProcessHeap@0`n    pop ecx`n    push ecx`n    push 0`n    push eax`n    call _HeapAlloc@12`n    mov ebx, eax`n    mov edx, eax`nrt_left_loop:"
        )
    )
    foreach ($p in $pairs) {
        if ($t.Contains($p[0])) {
            $t = $t.Replace($p[0], $p[1])
            $n++
        }
    }
    if ($n -eq 0) {
        Write-Host "Mid$ repair: no patches needed (already fixed or pattern changed)"
        return $false
    }
    [IO.File]::WriteAllText((Resolve-Path $asmPath), ($t -replace "`n", "`r`n"))
    Write-Host "Mid`$ repair: applied $n patch(es) to $asmPath"
    return $true
}

function Invoke-AbpcBuild([string]$driver, [string]$outPath, [string]$label) {
    Write-Host "=== $label ==="
    Write-Host "cwd: $((Get-Location).Path)"
    Write-Host "driver: $driver"
    Write-Host "project: $Project"
    Write-Host "output: $outPath"

    $beforeTime = [datetime]::MinValue
    $beforeLen = -1
    if (Test-Path $outPath) {
        $prev = Get-Item $outPath
        $beforeTime = $prev.LastWriteTimeUtc
        $beforeLen = $prev.Length
    }

    $log = New-Object System.Collections.Generic.List[string]
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $driver $Project $outPath 2>&1 | ForEach-Object {
        $line = "$_"
        $log.Add($line)
        Write-Host $line
    }
    $code = $LASTEXITCODE
    $sw.Stop()
    Write-Host ("exit=$code elapsed_sec=" + [math]::Round($sw.Elapsed.TotalSeconds, 2))

    $joined = [string]::Join("`n", $log)
    if ($code -ne 0 -or $joined -match "(?i)abc fail|asm fail|link fail|cannot |not found:") {
        Write-Error "build failed ($label)"
        exit 1
    }
    if ($joined -notmatch "(?i)OK:.*->") {
        Write-Error "build failed ($label): no OK line"
        exit 1
    }

    # abc が出す Mid$/Left$ ランタイムを修復してから再リンク（自己ホスト安定化）
    $asm = $null
    foreach ($c in @(".\abpc_combined.asm")) {
        if (Test-Path $c) { $asm = $c; break }
    }
    if ($null -ne $asm) {
        $patched = Repair-MidRuntime $asm
        if ($patched) {
            $obj = [IO.Path]::ChangeExtension($asm, ".obj")
            & .\abassembler.exe $asm $obj
            if ($LASTEXITCODE -ne 0) { Write-Error "re-assemble failed"; exit 1 }
            & .\ablinker.exe $obj $outPath
            if ($LASTEXITCODE -ne 0) { Write-Error "re-link failed"; exit 1 }
        }
    }

    if (-not (Test-Path $outPath)) {
        Write-Error "output missing: $outPath"
        exit 1
    }
    $fi = Get-Item $outPath
    if ($fi.LastWriteTimeUtc -le $beforeTime -and $fi.Length -eq $beforeLen) {
        Write-Error "output was not updated: $outPath"
        exit 1
    }
    Write-Host ("OK: " + $fi.FullName + " (" + $fi.Length + " bytes)")
    Write-Host ""
}

Invoke-AbpcBuild -driver $Abpc -outPath $OutExe -label "pass1: abpc -> selfhost\abpc.exe"

if ($Pass2) {
    $pass2Out = ".\abpc2.exe"
    # ToolDir はドライバ隣。selfhost\ 内なので成果物をドライバ名で使う
    $pass2Driver = ".\abpc_pass2_driver.exe"
    Copy-Item $OutExe $pass2Driver -Force
    Invoke-AbpcBuild -driver $pass2Driver -outPath $pass2Out -label "pass2: selfhost\abpc.exe -> selfhost\abpc2.exe"
    Remove-Item $pass2Driver -Force -ErrorAction SilentlyContinue
    $b1 = (Get-FileHash -Algorithm SHA256 $OutExe).Hash
    $b2 = (Get-FileHash -Algorithm SHA256 $pass2Out).Hash
    if ($b1 -eq $b2) {
        Write-Host "PASS2: binaries match (SHA256)"
    } else {
        Write-Host "PASS2: binaries differ"
        Write-Host "  pass1=$b1"
        Write-Host "  pass2=$b2"
    }
}

Write-Host "selfhost_abpc done."
