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

$credentialSource = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\auth.json'
$privateRoot = Split-Path -Parent $PrivateReceiptPath
$preflightPassed = $false
$sessionInvocations = 0
$sessionExit = $null
$caughtFailure = $false
$login = $false
$seedCompare = $false

function New-ImplementationSnapshot {
    param(
        [string]$Parent,
        [string]$CommonSource,
        [string]$LauncherSource
    )
    $root = Join-Path $Parent ('.implementation-snapshot-' + [Guid]::NewGuid().ToString('N'))
    [void]([IO.Directory]::CreateDirectory($root))
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object Security.AccessControl.FileSystemAccessRule(
        $identity,
        [Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.AddAccessRule($rule)
    [IO.Directory]::SetAccessControl($root, $acl)
    $common = Join-Path $root 'gate3_codex_credential_common.ps1'
    $launcherCopy = Join-Path $root 'gate3_codex_session_launcher.ps1'
    [IO.File]::WriteAllBytes($common, [IO.File]::ReadAllBytes($CommonSource))
    [IO.File]::WriteAllBytes($launcherCopy, [IO.File]::ReadAllBytes($LauncherSource))
    $commonLock = New-Object IO.FileStream(
        $common,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $launcherLock = New-Object IO.FileStream(
        $launcherCopy,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $commonSha = ([BitConverter]::ToString(
            $sha.ComputeHash($commonLock)
        )).Replace('-', '').ToLowerInvariant()
        $launcherSha = ([BitConverter]::ToString(
            $sha.ComputeHash($launcherLock)
        )).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
    $ready = [ordered]@{
        common_sha256 = $commonSha
        launcher_sha256 = $launcherSha
        schema = 'gate3-codex-implementation-snapshot.v1'
    }
    [IO.File]::WriteAllText(
        (Join-Path $root 'snapshot-ready.json'),
        (($ready | ConvertTo-Json -Compress) + [Environment]::NewLine),
        (New-Object Text.UTF8Encoding($false))
    )
    return [pscustomobject]@{
        CommonLock = $commonLock
        CommonPath = $common
        CommonSha256 = $commonSha
        LauncherLock = $launcherLock
        LauncherPath = $launcherCopy
        LauncherSha256 = $launcherSha
        Root = $root
    }
}

function Close-ImplementationSnapshot {
    param($Snapshot)
    if ($null -eq $Snapshot) { return }
    $Snapshot.CommonLock.Dispose()
    $Snapshot.LauncherLock.Dispose()
    if (Test-Path -LiteralPath $Snapshot.Root) {
        Remove-Item -LiteralPath $Snapshot.Root -Recurse -Force
    }
    if (Test-Path -LiteralPath $Snapshot.Root) {
        throw 'Implementation snapshot cleanup failed.'
    }
}

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
$runnerSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath
).Hash.ToLowerInvariant()
$implementationSnapshot = New-ImplementationSnapshot `
    -Parent $privateRoot `
    -CommonSource $credentialCommon `
    -LauncherSource $launcher
$launcherSha256 = $implementationSnapshot.LauncherSha256
$credentialCommonSha256 = $implementationSnapshot.CommonSha256
$routePlanSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $RoutePlanPath
).Hash.ToLowerInvariant()
$routePlan = Get-Content -Raw -LiteralPath $RoutePlanPath | ConvertFrom-Json
if (
    $routePlan.schema -ne 'gate3-codex-calibration-route-plan.v2' -or
    $routePlan.authorization -ne $CALIBRATION_AUTHORIZATION -or
    $routePlan.frozen_route.calibration_runner_implementation_sha256 -ne
        $runnerSha256 -or
    $routePlan.frozen_route.launcher_implementation_sha256 -ne
        $launcherSha256 -or
    $routePlan.frozen_route.credential_common_implementation_sha256 -ne
        $credentialCommonSha256
) {
    Close-ImplementationSnapshot -Snapshot $implementationSnapshot
    throw 'Calibration runner implementation identity preflight failed.'
}

# The common file is executable PowerShell. Verify its exact bytes before it is
# dot-sourced so tampered code cannot run before the mismatch is reported.
try {
. $implementationSnapshot.CommonPath
$userTemp = Get-UserTempRoot
$secretRoot = Join-Path $userTemp ("gate3-calibration-" + [Guid]::NewGuid().ToString('N'))
$seedPath = Join-Path $secretRoot 'seed.json'
$loginOut = Join-Path $secretRoot 'login.out'
$loginErr = Join-Path $secretRoot 'login.err'
$sessionAuth = Join-Path $CodexHome 'auth.json'
$secretPaths = @($seedPath, $sessionAuth)
$privateTransientPaths = @($loginOut, $loginErr)
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
}
catch {
    Close-ImplementationSnapshot -Snapshot $implementationSnapshot
    throw
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
        -CodexCommand $CodexCommand `
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
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $implementationSnapshot.LauncherPath `
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
        schema = 'gate3-codex-calibration-runner-receipt.v2'
        secret_material_retained = $secretMaterialRetained
        session_exit_code = $sessionExit
        session_invocations = $sessionInvocations
    }
    Write-Utf8Atomic `
        -Path $PrivateReceiptPath `
        -Text (($receipt | ConvertTo-Json -Depth 5) + [Environment]::NewLine)
    Close-ImplementationSnapshot -Snapshot $implementationSnapshot
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
