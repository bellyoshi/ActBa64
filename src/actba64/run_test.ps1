# run_test.ps1 - wrapper for run_test2.ps1
& "$PSScriptRoot\run_test2.ps1" @args
exit $LASTEXITCODE
