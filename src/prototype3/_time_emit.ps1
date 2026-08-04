$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Time-Step([string]$title, [scriptblock]$block) {
    Write-Host "=== $title ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $block
    $sw.Stop()
    Write-Host ("SEC=" + [math]::Round($sw.Elapsed.TotalSeconds, 3))
    Write-Host ""
    return $sw.Elapsed.TotalSeconds
}

Write-Host ("abc.exe=" + (Get-Item abc.exe).LastWriteTime)
Write-Host ("src=_bench_large.abp bytes=" + (Get-Item _bench_large.abp).Length)

# repeat to amplify
$lines = Get-Content _bench_large.abp
$body = @()
$body += "#console"
$body += "Dim i As Long"
$body += "Dim sum As Long"
$body += "Dim x(511) As Long"
for ($r = 0; $r -lt 80; $r++) {
    $body += "sum = 0"
    $body += "i = 0"
    $body += "While i < 40"
    $body += "    sum = sum + i * 3 + 1"
    $body += "    x(i) = sum"
    $body += "    i = i + 1"
    $body += "Wend"
}
$body += "ExitProcess(sum And 255)"
$body | Set-Content -Encoding Ascii _bench_xlarge.abp
Write-Host ("src=_bench_xlarge.abp bytes=" + (Get-Item _bench_xlarge.abp).Length)
Write-Host ""

Time-Step "abc _bench_xlarge.abp" {
    & .\abc.exe _bench_xlarge.abp _bench_xlarge.asm 2>&1 | ForEach-Object { Write-Host $_ }
    if (Test-Path _bench_xlarge.asm) {
        Write-Host ("asm_bytes=" + (Get-Item _bench_xlarge.asm).Length)
        $db0 = (Select-String -Path _bench_xlarge.asm -Pattern "^\s+db 0\s*$" -AllMatches).Count
        $times = (Select-String -Path _bench_xlarge.asm -Pattern "times " -AllMatches).Count
        Write-Host ("db0_lines=" + $db0 + " times_lines=" + $times)
    }
}

if (Test-Path _bench_xlarge.asm) {
    Time-Step "abassembler _bench_xlarge.asm" {
        & .\abassembler.exe _bench_xlarge.asm _bench_xlarge.obj 2>&1 | ForEach-Object { Write-Host $_ }
        if (Test-Path _bench_xlarge.obj) {
            Write-Host ("obj_bytes=" + (Get-Item _bench_xlarge.obj).Length)
        }
    }
}
