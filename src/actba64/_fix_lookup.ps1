$p = 'C:\Users\bellm\source\repos\bellyoshi\ActBa64\src\actba64\AstLower.abp'
$c = [IO.File]::ReadAllText($p)
$c2 = [regex]::Replace($c, 'LowLookupVar\(([^,]+),\s*([^,]+),\s*vOff,\s*vTy,\s*vTypeIdx,\s*vByRef,\s*vGlob\)', 'LowLookupVar($1, $2, VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob))')
$c2 = [regex]::Replace($c2, 'LowLookupVar\(([^,]+),\s*([^,]+),\s*off,\s*ty,\s*typeIdx,\s*byRef,\s*isGlob\)', 'LowLookupVar($1, $2, VarPtr(off), VarPtr(ty), VarPtr(typeIdx), VarPtr(byRef), VarPtr(isGlob))')
[IO.File]::WriteAllText($p, $c2)
$old = ([regex]::Matches($c2, 'LowLookupVar\([^)]*,\s*vOff,')).Count
$neu = ([regex]::Matches($c2, 'VarPtr\(vOff\)')).Count
Write-Output "remaining_old=$old varptr_vOff=$neu"
