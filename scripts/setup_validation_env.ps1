[CmdletBinding()]
param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Explicit)
    if ($Explicit) {
        return $Explicit
    }

    $candidates = @(
        @{ Cmd = "py"; Args = @("-3.12", "-c", "import sys; print(sys.executable)") },
        @{ Cmd = "py"; Args = @("-3.11", "-c", "import sys; print(sys.executable)") },
        @{ Cmd = "python"; Args = @("-c", "import sys; print(sys.executable)") }
    )

    foreach ($candidate in $candidates) {
        try {
            $output = & $candidate.Cmd @candidate.Args 2>$null
            if ($LASTEXITCODE -eq 0 -and $output) {
                return ($output | Select-Object -First 1).Trim()
            }
        } catch {
            continue
        }
    }

    throw "No usable Python runtime found. Install Python 3.11 or 3.12, or pass -PythonExe explicitly."
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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$resolvedPython = Resolve-Python -Explicit $PythonExe
Write-Host "Using Python: $resolvedPython"

$venvPath = Join-Path $repoRoot ".venv"
if (Test-Path $venvPath) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = Join-Path $repoRoot ".venv.backup.$stamp"
    Move-Item -LiteralPath $venvPath -Destination $backupPath
    Write-Host "Existing .venv moved to: $backupPath"
}

& $resolvedPython -m venv .venv
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found: $venvPython"
}

& $venvPython -m pip install --upgrade pip setuptools wheel
& $venvPython -m pip install -r requirements.txt
& $venvPython -m pip install --upgrade pytest

$cacheInfo = Resolve-CacheDir -Root $repoRoot

Write-Host ""
Write-Host "Validation runtime ready."
& $venvPython --version
& $venvPython -m pytest --version
Write-Host "pytest cache_dir: $($cacheInfo.Path) (source=$($cacheInfo.Source))"
