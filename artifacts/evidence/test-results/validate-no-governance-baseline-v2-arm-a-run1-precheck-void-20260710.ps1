$ErrorActionPreference = "Stop"

$scratch = "C:\Users\daish\.codex\visualizations\2026\07\10\019f4c83-2f1f-7b30-af00-324063641a72\v2-baseline-arm-a-run-1"
$taskFile = Join-Path $scratch "fixtures\architecture_drift_compliant.checks.json"

if (-not (Test-Path -LiteralPath $scratch)) {
    throw "expected failed precheck scratch root is absent"
}
if (Test-Path -LiteralPath $taskFile) {
    throw "failed precheck scratch unexpectedly contains the task file"
}

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
git -C $scratch -c "safe.directory=$scratch" rev-parse --verify HEAD 2>$null
$ErrorActionPreference = $previousPreference
if ($LASTEXITCODE -eq 0) {
    throw "failed precheck scratch unexpectedly has a seed commit"
}

$owner = (Get-Acl -LiteralPath $scratch).Owner
Write-Output "PASS Run 1 did not start: fresh scratch root owner=$owner has no task file and no seed commit"
