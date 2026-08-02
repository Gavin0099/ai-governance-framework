param(
    [Parameter(Mandatory = $true)]
    [string]$Authorization,
    [Parameter(Mandatory = $true)]
    [string]$CodexCommand,
    [Parameter(Mandatory = $true)]
    [string]$RoutePlanPath,
    [Parameter(Mandatory = $true)]
    [string]$Workspace,
    [Parameter(Mandatory = $true)]
    [string]$PromptPath,
    [Parameter(Mandatory = $true)]
    [string]$CodexHome,
    [Parameter(Mandatory = $true)]
    [string]$StdoutPath,
    [Parameter(Mandatory = $true)]
    [string]$StderrPath,
    [Parameter(Mandatory = $true)]
    [string]$ExitCodePath,
    [Parameter(Mandatory = $true)]
    [string]$PrivateReceiptPath
)

# Single-session calibration runner.
#
# One session, never two. The pair runner exists to invoke exactly two
# sessions; this exists to invoke exactly one, and the two authorizations are
# deliberately not routed through one script. A mode switch would put both
# authorizations in one executable, where a single defect could let a
# calibration authorization spend a pair's worth of sessions.
#
# Everything about credential handling is shared, not copied: seeding, ACL
# narrowing, the user-Temp confinement check and the login preflight all come
# from gate3_codex_credential_common.ps1, whose digest is pinned by the route
# plan exactly as the launcher's and this script's are.
#
# It admits nothing. It produces a rollout and an exit code for the calibration
# probe to read; scoring, packet building and admission are not its business.

$ErrorActionPreference = 'Stop'
$CALIBRATION_AUTHORIZATION = 'non_counted_codex_calibration_probe_only'

$launcher = Join-Path $PSScriptRoot 'gate3_codex_session_launcher.ps1'
$credentialCommon = Join-Path $PSScriptRoot 'gate3_codex_credential_common.ps1'
. $credentialCommon

$credentialSource = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\auth.json'
$privateRoot = Split-Path -Parent $PrivateReceiptPath
$userTemp = Get-UserTempRoot
$secretRoot = Join-Path $userTemp ("gate3-calibration-" + [Guid]::NewGuid().ToString('N'))
$seedPath = Join-Path $secretRoot 'seed.json'
$loginOut = Join-Path $secretRoot 'login.out'
$loginErr = Join-Path $secretRoot 'login.err'
$sessionAuth = Join-Path $CodexHome 'auth.json'
$secretPaths = @($seedPath, $sessionAuth)
$privateTransientPaths = @($loginOut, $loginErr)
$preflightPassed = $false
$sessionInvocations = 0
$sessionExit = $null
$caughtFailure = $false
$login = $false
$seedCompare = $false

$runnerSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath
).Hash.ToLowerInvariant()
$launcherSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $launcher
).Hash.ToLowerInvariant()
$credentialCommonSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $credentialCommon
).Hash.ToLowerInvariant()
$routePlanSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $RoutePlanPath
).Hash.ToLowerInvariant()

# Authorization first, before any credential is touched. A calibration
# authorization is the only thing this script accepts; a pair authorization
# must not be spendable here.
if ($Authorization -ne $CALIBRATION_AUTHORIZATION) {
    [Console]::Error.WriteLine('Calibration runner authorization is invalid.')
    exit 2
}

foreach ($requiredFile in @(
    $CodexCommand,
    $credentialSource,
    $RoutePlanPath,
    $PromptPath,
    $launcher,
    $credentialCommon
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw 'Calibration runner required input is missing.'
    }
}
foreach ($privateRuntimePath in @(
    $CodexCommand,
    $RoutePlanPath,
    $Workspace,
    $PromptPath,
    $CodexHome,
    $StdoutPath,
    $StderrPath,
    $ExitCodePath,
    $PrivateReceiptPath
)) {
    Assert-UserTempPath -Path $privateRuntimePath
}
$routePlan = Get-Content -Raw -LiteralPath $RoutePlanPath | ConvertFrom-Json
if (
    $routePlan.schema -ne 'gate3-codex-calibration-route-plan.v1' -or
    $routePlan.authorization -ne $CALIBRATION_AUTHORIZATION -or
    $routePlan.frozen_route.calibration_runner_implementation_sha256 -ne
        $runnerSha256 -or
    $routePlan.frozen_route.launcher_implementation_sha256 -ne
        $launcherSha256 -or
    $routePlan.frozen_route.credential_common_implementation_sha256 -ne
        $credentialCommonSha256
) {
    throw 'Calibration runner implementation identity preflight failed.'
}
foreach ($requiredDirectory in @($privateRoot, $Workspace, $CodexHome)) {
    if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
        throw 'Calibration runner required directory is missing.'
    }
}
foreach ($mustBeAbsent in @(
    $PrivateReceiptPath,
    $secretRoot,
    $seedPath,
    $sessionAuth,
    $StdoutPath,
    $StderrPath,
    $ExitCodePath
)) {
    if (Test-Path -LiteralPath $mustBeAbsent) {
        throw 'Calibration runner output already exists.'
    }
}

try {
    [void](New-Item -ItemType Directory -Path $secretRoot)
    Set-CurrentUserOnlyAcl -Path $secretRoot -Container
    Set-CurrentUserOnlyAcl -Path $CodexHome -Container
    Copy-PrivateCredential -Source $credentialSource -Destination $seedPath
    Copy-PrivateCredential -Source $seedPath -Destination $sessionAuth
    $seedCompare = Test-ExactBytes -Left $seedPath -Right $sessionAuth
    if (-not $seedCompare) {
        throw 'Credential seed byte comparison failed.'
    }
    $login = Test-ChatGptLogin `
        -CodexHome $CodexHome `
        -StdoutPath $loginOut `
        -StderrPath $loginErr
    if (-not $login) {
        throw 'Credential preflight did not confirm the ChatGPT route.'
    }
    $preflightPassed = $true

    if ($sessionInvocations -ne 0) {
        throw 'Calibration runner attempted more than one session.'
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher `
        -CodexCommand $CodexCommand `
        -ExpectedLauncherSha256 $launcherSha256 `
        -CodexHome $CodexHome `
        -Workspace $Workspace `
        -PromptPath $PromptPath `
        -StdoutPath $StdoutPath `
        -StderrPath $StderrPath `
        -ExitCodePath $ExitCodePath
    $sessionExit = $LASTEXITCODE
    $sessionInvocations++
}
catch {
    $caughtFailure = $true
}
finally {
    foreach ($path in @($secretPaths + $privateTransientPaths)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }
    if (Test-Path -LiteralPath $secretRoot) {
        Remove-Item -LiteralPath $secretRoot -Recurse -Force
    }
    $secretMaterialRetained = @(
        $secretPaths | Where-Object { Test-Path -LiteralPath $_ }
    ).Count -ne 0
    $receipt = [ordered]@{
        auth_files_removed = -not $secretMaterialRetained
        auth_route = if ($preflightPassed) { 'chatgpt' } else { 'unverified' }
        authorization = $CALIBRATION_AUTHORIZATION
        credential_seed_compare = if ($seedCompare) { 'PASS' } else { 'FAIL' }
        implementation = [ordered]@{
            calibration_runner_sha256 = $runnerSha256
            credential_common_sha256 = $credentialCommonSha256
            launcher_sha256 = $launcherSha256
        }
        login_status = if ($login) { 'PASS' } else { 'FAIL' }
        replacement_sessions = 0
        route_plan_sha256 = $routePlanSha256
        schema = 'gate3-codex-calibration-runner-receipt.v1'
        secret_material_retained = $secretMaterialRetained
        session_exit_code = $sessionExit
        session_invocations = $sessionInvocations
    }
    Write-Utf8Atomic `
        -Path $PrivateReceiptPath `
        -Text (($receipt | ConvertTo-Json -Depth 5) + [Environment]::NewLine)
}

if ($caughtFailure) {
    [Console]::Error.WriteLine('Calibration runner failed closed.')
    exit 2
}
if ($sessionInvocations -ne 1) {
    [Console]::Error.WriteLine('Calibration runner did not invoke exactly one session.')
    exit 2
}
if ($sessionExit -ne 0) {
    [Console]::Error.WriteLine('The authorized calibration session failed.')
    exit 1
}
Write-Output 'CALIBRATION_RUNNER_STATUS=PASS SESSION_INVOCATIONS=1'
exit 0
