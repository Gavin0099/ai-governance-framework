[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pythonRunner = Join-Path $repoRoot "scripts\codex-python.ps1"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$baseTemp = Join-Path $repoRoot ".pytest_tmp\codex-basetemp"

if (-not (Test-Path -LiteralPath $baseTemp)) {
    New-Item -ItemType Directory -Path $baseTemp -Force | Out-Null
}

$finalArgs = @("-B", "-m", "pytest")
if ($PytestArgs) {
    $finalArgs += $PytestArgs
}
if (-not ($PytestArgs | Where-Object { $_ -eq "--basetemp" -or $_ -like "--basetemp=*" })) {
    $finalArgs += @("--basetemp", $baseTemp)
}
if (-not ($PytestArgs | Where-Object { $_ -eq "-p" })) {
    $finalArgs += @("-p", "no:cacheprovider")
}

$receiptArgs = @(
    "-B",
    "-m",
    "governance_tools.test_evidence_receipt_writer",
    "--project-root",
    $repoRoot,
    "--runner",
    "scripts/codex-pytest.ps1",
    "--",
    $venvPython
) + $finalArgs

& $pythonRunner @receiptArgs
exit $LASTEXITCODE
