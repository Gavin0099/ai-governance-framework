[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$scratchRoot = Join-Path $repoRoot ".pytest_tmp\codex"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Repo Python was not found at $venvPython. Run scripts/setup_validation_env.ps1 with an explicit -PythonExe, or restore the repo .venv."
}

if (-not (Test-Path -LiteralPath $scratchRoot)) {
    New-Item -ItemType Directory -Path $scratchRoot -Force | Out-Null
}

$previousPythonPath = $env:PYTHONPATH
$previousTemp = $env:TEMP
$previousTmp = $env:TMP

try {
    if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
        $env:PYTHONPATH = $repoRoot
    } else {
        $env:PYTHONPATH = "$repoRoot;$previousPythonPath"
    }
    $env:TEMP = $scratchRoot
    $env:TMP = $scratchRoot

    if (-not $PythonArgs -or $PythonArgs.Count -eq 0) {
        $PythonArgs = @("--version")
    }

    & $venvPython @PythonArgs
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
}
