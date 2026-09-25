$Files = @(
  'src/actba64/AstLower.abp',
  'src/actba64/AstLowerApi.abp',
  'src/actba64/AstLowerDriver.abp',
  'src/actba64/AstLowerRt.abp',
  'src/actba64/AstLowerStmtCtrl.abp',
  'src/actba64/StrGcRt.abp'
)

$results = @()
foreach ($f in $Files) {
    $lines = Get-Content -LiteralPath $f
    $start = -1; $name = ''; $kind = ''
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $l = $lines[$i]
        if ($start -lt 0) {
            if ($l -match '^\s*(Function|Sub)\s+([A-Za-z_][A-Za-z0-9_\$]*)') {
                $kind = $Matches[1]; $name = $Matches[2]; $start = $i
            }
        } else {
            if ($l -match '^\s*End\s+(Function|Sub)\s*$') {
                $len = $i - $start + 1
                $results += [pscustomobject]@{ File = (Split-Path $f -Leaf); Name = $name; Kind = $kind; Start = $start + 1; End = $i + 1; Len = $len }
                $start = -1
            }
        }
    }
}

$over = @($results | Where-Object { $_.Len -gt 50 } | Sort-Object -Property Len -Descending)
$over | Format-Table -AutoSize | Out-String -Width 200
Write-Output ("TOTAL_FUNCS=" + $results.Count)
Write-Output ("TOTAL_OVER_50=" + $over.Count)
