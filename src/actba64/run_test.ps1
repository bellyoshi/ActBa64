# run_test.ps1 - wrapper for run_test2.ps1
& "$PSScriptRoot\run_test2.ps1" stage0
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage0 failed"
    exit 1
}
& "$PSScriptRoot\run_test2.ps1" stage1
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage1 failed"
    exit 1
}
& "$PSScriptRoot\run_test2.ps1" stage2
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage2 failed"
    exit 1
}
& "$PSScriptRoot\run_test2.ps1" stage0 -Actba32
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage0 -Actba32 failed"
    exit 1
}
& "$PSScriptRoot\run_test2.ps1" stage1 -Actba32
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage1 -Actba32 failed"
    exit 1
}
& "$PSScriptRoot\run_test2.ps1" stage2 -Actba32
if ($LASTEXITCODE -ne 0) {
    Write-Error "stage2 -Actba32 failed"
    exit 1
}
exit $LASTEXITCODE
