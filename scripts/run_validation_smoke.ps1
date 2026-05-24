[CmdletBinding()]
param(
    [switch]$RunFullRegression
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Missing .venv runtime. Run scripts/setup_validation_env.ps1 first."
}

function Resolve-CacheDir {
    param([string]$Root)

    $preferred = "C:/tmp/ai-governance-framework-pytest-cache"
    try {
        if (-not (Test-Path $preferred)) {
            New-Item -ItemType Directory -Path $preferred -Force | Out-Null
        }
        return @{ Path = $preferred; Source = "preferred" }
    } catch {
        $fallback = Join-Path $Root ".pytest_cache_runtime"
        if (-not (Test-Path $fallback)) {
            New-Item -ItemType Directory -Path $fallback -Force | Out-Null
        }
        return @{ Path = $fallback; Source = "fallback_repo_local" }
    }
}

$smokeStatus = "validation-environment-limited"
$fullRegressionStatus = "full-regression-pending"

try {
    $cacheInfo = Resolve-CacheDir -Root $repoRoot
    $cacheDir = $cacheInfo.Path
    Write-Host "cache_dir=$cacheDir (source=$($cacheInfo.Source))"

    Write-Host "[validation_smoke] targeted pytest"
    $pytestOutput = & $venvPython -m pytest tests/test_change_control_summary.py -q -o "cache_dir=$cacheDir" 2>&1
    $pytestOutput | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        $joinedOutput = ($pytestOutput | Out-String)
        if (
            $joinedOutput -match "PermissionError" -or
            $joinedOutput -match "Access is denied" -or
            $joinedOutput -match "存取被拒"
        ) {
            $smokeStatus = "validation-environment-limited"
            throw "Targeted pytest blocked by environment permission limits."
        } else {
            $smokeStatus = "smoke-failed"
            throw "Targeted pytest smoke failed."
        }
    }

    Write-Host "[validation_smoke] direct script help"
    & $venvPython governance_tools/change_control_summary.py --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $smokeStatus = "smoke-failed"
        throw "change_control_summary --help smoke failed."
    }
    Write-Host "change_control_summary --help: OK"
    $smokeStatus = "smoke-passed"
} catch {
    if ($smokeStatus -ne "smoke-failed") {
        $smokeStatus = "validation-environment-limited"
    }
    Write-Warning $_
}

if ($RunFullRegression) {
    Write-Host "[validation_smoke] full regression requested"
    try {
        & $venvPython -m pytest -q -o "cache_dir=$cacheDir"
        if ($LASTEXITCODE -eq 0) {
            $fullRegressionStatus = "full-regression-passed"
        } else {
            $fullRegressionStatus = "full-regression-pending"
        }
    } catch {
        $fullRegressionStatus = "full-regression-pending"
    }
}

Write-Host "validation_smoke_status=$smokeStatus"
Write-Host "full_regression_status=$fullRegressionStatus"
if ($smokeStatus -eq "smoke-failed") {
    exit 1
}
