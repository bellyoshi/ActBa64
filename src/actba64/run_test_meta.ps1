function Get-Meta([string]$path) {
    $expect = 0
    $gui = $null
    $target = $false
    $skip32 = $false
    $compileFail = $false
    $expectErrors = -1
    $stdin = @()
    $base = [System.IO.Path]::GetFileName($path)
    foreach ($line in (Get-Content -LiteralPath $path -Encoding Default -ErrorAction Stop)) {
        # Single-quoted regex: Windows PowerShell 5.1 treats [01] inside "..." as a type name.
        if ($line -match '^\s*''\s*Expect\s*:\s*(-?\d+)\s*$') {
            $expect = [int]$Matches[1]
        }
        if ($line -match '^\s*''\s*Gui\s*:\s*([01])\s*$') {
            $gui = [int]$Matches[1]
        }
        if ($line -match '(?i)^\s*''\s*Target\s*:\s*actba64\s*$') {
            $target = $true
        }
        if ($line -match '(?i)^\s*''\s*Skip32\s*:\s*1\s*$') {
            $skip32 = $true
        }
        if ($line -match '(?i)^\s*''\s*CompileFail\s*:\s*1\s*$') {
            $compileFail = $true
        }
        if ($line -match '^\s*''\s*ExpectErrors\s*:\s*(-?\d+)\s*$') {
            $expectErrors = [int]$Matches[1]
        }
        if ($line -match '^\s*''\s*Stdin\s*:\s?(.*)$') {
            $stdin += $Matches[1]
        }
        if ($line -match '(?i)^\s*#USEWINDOW\s*=\s*1\s*$') {
            if ($null -eq $gui) { $gui = 1 }
        }
    }
    if ($null -eq $gui) {
        if ($base -match '(?i)^_pe_gui') {
            $gui = 1
        } else {
            $gui = 0
        }
    }
    return @{ Expect = $expect; Gui = $gui; Target = $target; Skip32 = $skip32; Stdin = $stdin; CompileFail = $compileFail; ExpectErrors = $expectErrors }
}
