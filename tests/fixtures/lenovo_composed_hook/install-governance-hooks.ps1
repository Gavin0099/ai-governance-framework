<#
.SYNOPSIS
    Canonical install-time composition of this repo's governance git hooks.

.DESCRIPTION
    Treats tracked sources as the single source-of-truth and (re)composes the
    repo's git hooks deterministically at install time:

      1. Installs the framework-managed hooks (pre-commit, pre-push) from the
         submodule via governance_tools/hook_installer.py.
      2. Re-applies the tracked memory-quality pre-push fragment
         (scripts/hooks/pre-push.memory-quality.fragment.sh) idempotently.

    Running this installer always yields the same composed hook from version
    controlled inputs, so the repo-specific memory-quality gate survives any
    framework hook re-install instead of relying on a one-off local mutation.

.PARAMETER RepoRoot
    Repository root. Defaults to the current directory.

.PARAMETER FrameworkRoot
    Path (relative to RepoRoot or absolute) to the governance framework
    submodule. Defaults to external/ai-governance-framework.
#>
param(
    [string]$RepoRoot = ".",
    [string]$FrameworkRoot = "external/ai-governance-framework"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path $RepoRoot).Path

$frameworkCandidate = if ([System.IO.Path]::IsPathRooted($FrameworkRoot)) {
    $FrameworkRoot
}
else {
    Join-Path $repoRoot $FrameworkRoot
}
if (-not (Test-Path $frameworkCandidate)) {
    Write-Error "governance framework root not found: $frameworkCandidate"
    exit 1
}
$frameworkRoot = (Resolve-Path $frameworkCandidate).Path

$installer = Join-Path $frameworkRoot "governance_tools/hook_installer.py"
if (-not (Test-Path $installer)) {
    Write-Error "framework hook installer not found: $installer"
    exit 1
}

$wireScript = Join-Path $repoRoot "wire-pre-push-memory-quality.ps1"
if (-not (Test-Path $wireScript)) {
    Write-Error "memory-quality wiring script not found: $wireScript"
    exit 1
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
else { $null }
if (-not $python) {
    Write-Error "Python not found; cannot run framework hook installer"
    exit 1
}

# Step 1: install framework-managed hooks from the submodule source-of-truth.
Write-Host "[install-hooks] installing framework-managed hooks..."
$installerExit = 1
Push-Location $frameworkRoot
try {
    & $python -m governance_tools.hook_installer --repo $repoRoot --framework-root $frameworkRoot --hooks-only
    $installerExit = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($installerExit -ne 0) {
    Write-Error "framework hook installer failed (exit $installerExit)"
    exit $installerExit
}

# Step 2: re-apply the tracked memory-quality fragment idempotently.
Write-Host "[install-hooks] applying tracked memory-quality pre-push fragment..."
Push-Location $repoRoot
try {
    & $wireScript
    if ($LASTEXITCODE -ne 0) {
        Write-Error "memory-quality fragment wiring failed (exit $LASTEXITCODE)"
        exit 1
    }
}
finally {
    Pop-Location
}

# Step 3: verify the composed hook carries the repo gate marker.
$hookPath = Join-Path $repoRoot ".git/hooks/pre-push"
$marker = "# BEGIN LENOVO_ISP_MEMORY_QUALITY_GATE"
if (-not (Select-String -Path $hookPath -SimpleMatch -Pattern $marker -Quiet)) {
    Write-Error "verification failed: memory-quality gate marker missing from $hookPath"
    exit 1
}

Write-Host "[install-hooks] ok: framework hooks + memory-quality gate composed at $hookPath"
