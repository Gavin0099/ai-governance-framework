[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pythonRunner = Join-Path $repoRoot "scripts\codex-python.ps1"
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

& $pythonRunner @finalArgs
exit $LASTEXITCODE
