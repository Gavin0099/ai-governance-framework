param(
    [Parameter(Mandatory = $true)][string]$FrameworkRepoRoot,
    [Parameter(Mandatory = $true)][string]$ConsumerRepoRoot,
    [Parameter(Mandatory = $true)][string]$FrameworkCommit,
    [Parameter(Mandatory = $true)][string]$RemoteBranch,
    [Parameter(Mandatory = $true)][string]$RunRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$attemptStartEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0

$attemptRoot = "artifacts/experiments/prepush-bugfix-20260724/gate1-validator-probe/c1-stryker-sidecar-attempt-03"
$manifestPath = Join-Path $PSScriptRoot "validator-sidecar-probe-manifest.json"
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$gitPath = $manifest.tcb.git.path
$pythonPath = $manifest.tcb.python.path
$evidenceDir = Join-Path $RunRoot "evidence"
$frameworkInput = Join-Path $RunRoot "framework-input"
if (Test-Path -LiteralPath $RunRoot) {
    if (-not (Test-Path -LiteralPath $RunRoot -PathType Container) -or (Get-ChildItem -LiteralPath $RunRoot -Force).Count -ne 0) {
        throw "SIDECAR_RESOLUTION_FAILED:RUN_ROOT_NOT_EMPTY"
    }
}
else {
    New-Item -ItemType Directory -Path $RunRoot | Out-Null
}
New-Item -ItemType Directory -Path $evidenceDir | Out-Null

function Get-Sha256Lower([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Assert-Binding($Binding, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "SIDECAR_RESOLUTION_FAILED:TCB_OR_BOOTSTRAP_FILE_MISSING:$Path"
    }
    $actualHash = Get-Sha256Lower $Path
    $actualBytes = (Get-Item -LiteralPath $Path).Length
    if ($actualHash -cne $Binding.sha256 -or $actualBytes -ne $Binding.bytes) {
        throw "SIDECAR_RESOLUTION_FAILED:TCB_OR_BOOTSTRAP_BINDING:$Path"
    }
}

try {
    Assert-Binding $manifest.tcb.git $gitPath
    Assert-Binding $manifest.tcb.python $pythonPath
    foreach ($binding in $manifest.bootstrap_bindings) {
        Assert-Binding $binding (Join-Path $PSScriptRoot $binding.path)
    }

    $pathsPath = Join-Path $RunRoot "attempt03-paths.json"
    [System.IO.File]::WriteAllText($pathsPath, (($manifest.attempt03_raw_paths | ConvertTo-Json -Compress) + "`n"), [System.Text.UTF8Encoding]::new($false))
    $bootstrapInventory = Join-Path $evidenceDir "attempt03-bootstrap-raw-object-inventory.json"
    & $pythonPath (Join-Path $PSScriptRoot "raw_git_materialize.py") `
        --git $gitPath `
        --repo $FrameworkRepoRoot `
        --commit $FrameworkCommit `
        --destination $frameworkInput `
        --paths-json $pathsPath `
        --output $bootstrapInventory
    if ($LASTEXITCODE -ne 0) {
        throw "SIDECAR_RESOLUTION_FAILED:BOOTSTRAP_RAW_OBJECT_MATERIALIZATION"
    }

    foreach ($binding in $manifest.attempt03_raw_bindings) {
        $rawPath = Join-Path $frameworkInput $binding.path
        Assert-Binding $binding $rawPath
    }

    & $pythonPath (Join-Path $frameworkInput "$attemptRoot/run_sidecar_probe.py") `
        --framework-repo $FrameworkRepoRoot `
        --consumer-repo $ConsumerRepoRoot `
        --framework-commit $FrameworkCommit `
        --remote-branch $RemoteBranch `
        --run-root $RunRoot `
        --attempt-start-epoch $attemptStartEpoch `
        --git $gitPath `
        --python $pythonPath `
        --docker $manifest.execution_environment.docker.path
    if ($LASTEXITCODE -ne 0) {
        throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZED_RUNNER_EXIT:$LASTEXITCODE"
    }
}
catch {
    $failure = $_.Exception.Message
    $terminalPath = Join-Path $evidenceDir "probe-terminal.json"
    if (-not (Test-Path -LiteralPath $terminalPath)) {
        $terminal = [ordered]@{
            schema = "c1-stryker-sidecar-probe-terminal.v3"
            probe_id = "c1-stryker-sidecar-raw-object-20260822-03"
            terminal = "SIDECAR_RESOLUTION_FAILED"
            completed_at_utc = [DateTime]::UtcNow.ToString("o")
            bindings = [ordered]@{
                framework_commit = $FrameworkCommit
                remote_branch = $RemoteBranch
                manifest_sha256 = Get-Sha256Lower $manifestPath
                manifest_bytes = (Get-Item -LiteralPath $manifestPath).Length
            }
            bootstrap_failure = $failure
            repair_in_place = $false
            retry_authorized = $false
            claim_ceiling = "Conditional on the declared TCB, this terminal records only an attempt-03 bootstrap/materialization failure. It does not establish the sidecar boundary, Git/Python/bootstrap correctness, validator or Skill effect, Gate 1 readiness, preregistration, freeze, or an A/B/C/D result."
            not_claimed = @("sidecar boundary result", "Git/Python/bootstrap correctness", "validator effect", "Skill effect", "Gate 1 readiness", "preregistration", "Gate 1 freeze", "A/B/C/D result")
        }
        [System.IO.File]::WriteAllText($terminalPath, (($terminal | ConvertTo-Json -Depth 20) + "`n"), [System.Text.UTF8Encoding]::new($false))
    }
    Write-Error $failure
    exit 1
}
