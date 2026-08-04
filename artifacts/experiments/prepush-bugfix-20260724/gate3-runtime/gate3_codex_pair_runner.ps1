param(
    [Parameter(Mandatory = $true)]
    [string]$CodexCommand,
    [Parameter(Mandatory = $true)]
    [string]$RoutePlanPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmAWorkspace,
    [Parameter(Mandatory = $true)]
    [string]$ArmBWorkspace,
    [Parameter(Mandatory = $true)]
    [string]$ArmAPromptPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmBPromptPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmACodexHome,
    [Parameter(Mandatory = $true)]
    [string]$ArmBCodexHome,
    [Parameter(Mandatory = $true)]
    [string]$ArmAStdoutPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmBStdoutPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmAStderrPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmBStderrPath,
    [Parameter(Mandatory = $true)]
    [string]$ArmAExitCodePath,
    [Parameter(Mandatory = $true)]
    [string]$ArmBExitCodePath,
    [Parameter(Mandatory = $true)]
    [string]$PrivateReceiptPath
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'gate3_codex_session_launcher.ps1'
$credentialCommon = Join-Path $PSScriptRoot 'gate3_codex_credential_common.ps1'
$credentialSource = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\auth.json'
$privateRoot = Split-Path -Parent $PrivateReceiptPath
$preflightPassed = $false
$sessionInvocations = 0
$armAExit = $null
$armBExit = $null
$caughtFailure = $false
$loginA = $false
$loginB = $false
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
foreach ($requiredFile in @(
    $CodexCommand,
    $credentialSource,
    $RoutePlanPath,
    $ArmAPromptPath,
    $ArmBPromptPath,
    $launcher,
    $credentialCommon
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw 'Credential runner required input is missing.'
    }
}
$pairRunnerSha256 = (
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
    $routePlan.schema -ne 'gate3-codex-live-route-plan.v6' -or
    $routePlan.frozen_route.pair_runner_implementation_sha256 -ne
        $pairRunnerSha256 -or
    $routePlan.frozen_route.launcher_implementation_sha256 -ne
        $launcherSha256 -or
    $routePlan.frozen_route.credential_common_implementation_sha256 -ne
        $credentialCommonSha256
) {
    Close-ImplementationSnapshot -Snapshot $implementationSnapshot
    throw 'Credential runner implementation identity preflight failed.'
}

# The shared file is executable. Match its bytes to the route plan before
# dot-sourcing so a rejected implementation never gets a chance to run.
try {
. $implementationSnapshot.CommonPath
$userTemp = Get-UserTempRoot
$secretRoot = Join-Path $userTemp ("gate3-credential-" + [Guid]::NewGuid().ToString('N'))
$seedPath = Join-Path $secretRoot 'seed.json'
$loginAOut = Join-Path $secretRoot 'login-a.out'
$loginAErr = Join-Path $secretRoot 'login-a.err'
$loginBOut = Join-Path $secretRoot 'login-b.out'
$loginBErr = Join-Path $secretRoot 'login-b.err'
$armAAuth = Join-Path $ArmACodexHome 'auth.json'
$armBAuth = Join-Path $ArmBCodexHome 'auth.json'
$secretPaths = @($seedPath, $armAAuth, $armBAuth)
$privateTransientPaths = @($loginAOut, $loginAErr, $loginBOut, $loginBErr)
foreach ($privateRuntimePath in @(
    $CodexCommand,
    $RoutePlanPath,
    $ArmAWorkspace,
    $ArmBWorkspace,
    $ArmAPromptPath,
    $ArmBPromptPath,
    $ArmACodexHome,
    $ArmBCodexHome,
    $ArmAStdoutPath,
    $ArmBStdoutPath,
    $ArmAStderrPath,
    $ArmBStderrPath,
    $ArmAExitCodePath,
    $ArmBExitCodePath,
    $PrivateReceiptPath
)) {
    Assert-UserTempPath -Path $privateRuntimePath
}
foreach ($requiredDirectory in @(
    $privateRoot,
    $ArmAWorkspace,
    $ArmBWorkspace,
    $ArmACodexHome,
    $ArmBCodexHome
)) {
    if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
        throw 'Credential runner required directory is missing.'
    }
}
foreach ($codexHome in @($ArmACodexHome, $ArmBCodexHome)) {
    if (@(Get-ChildItem -LiteralPath $codexHome -Force).Count -ne 0) {
        throw 'Isolated Codex home must be empty before credential seeding.'
    }
}
foreach ($mustBeAbsent in @(
    $PrivateReceiptPath,
    $secretRoot,
    $seedPath,
    $armAAuth,
    $armBAuth,
    $ArmAStdoutPath,
    $ArmBStdoutPath,
    $ArmAStderrPath,
    $ArmBStderrPath,
    $ArmAExitCodePath,
    $ArmBExitCodePath
)) {
    if (Test-Path -LiteralPath $mustBeAbsent) {
        throw 'Credential runner output already exists.'
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
    Set-CurrentUserOnlyAcl -Path $ArmACodexHome -Container
    Set-CurrentUserOnlyAcl -Path $ArmBCodexHome -Container
    Copy-PrivateCredential -Source $credentialSource -Destination $seedPath
    Copy-PrivateCredential -Source $seedPath -Destination $armAAuth
    Copy-PrivateCredential -Source $seedPath -Destination $armBAuth
    $seedCompare = (
        (Test-ExactBytes -Left $seedPath -Right $armAAuth) -and
        (Test-ExactBytes -Left $seedPath -Right $armBAuth)
    )
    if (-not $seedCompare) {
        throw 'Credential seed byte comparison failed.'
    }
    $loginA = Test-ChatGptLogin `
        -CodexCommand $CodexCommand `
        -CodexHome $ArmACodexHome `
        -StdoutPath $loginAOut `
        -StderrPath $loginAErr
    $loginB = Test-ChatGptLogin `
        -CodexCommand $CodexCommand `
        -CodexHome $ArmBCodexHome `
        -StdoutPath $loginBOut `
        -StderrPath $loginBErr
    if (-not $loginA -or -not $loginB) {
        throw 'Credential preflight did not confirm the ChatGPT route.'
    }
    foreach ($codexHomeState in @(
        [ordered]@{ Path = $ArmACodexHome; Auth = $armAAuth },
        [ordered]@{ Path = $ArmBCodexHome; Auth = $armBAuth }
    )) {
        $inventory = @(Get-ChildItem -LiteralPath $codexHomeState.Path -Force)
        if (
            $inventory.Count -ne 1 -or
            $inventory[0].PSIsContainer -or
            $inventory[0].FullName -ne $codexHomeState.Auth
        ) {
            throw 'Credential home inventory changed after login preflight.'
        }
        if (
            -not (Test-ExactBytes -Left $seedPath -Right $codexHomeState.Auth) -or
            -not (Test-CurrentUserOnlyAcl -Path $codexHomeState.Path) -or
            -not (Test-CurrentUserOnlyAcl -Path $codexHomeState.Auth)
        ) {
            throw 'Credential home integrity changed after login preflight.'
        }
    }
    $preflightPassed = $true

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $implementationSnapshot.LauncherPath `
        -CodexCommand $CodexCommand `
        -ExpectedLauncherSha256 $launcherSha256 `
        -CodexHome $ArmACodexHome `
        -Workspace $ArmAWorkspace `
        -PromptPath $ArmAPromptPath `
        -StdoutPath $ArmAStdoutPath `
        -StderrPath $ArmAStderrPath `
        -ExitCodePath $ArmAExitCodePath
    $armAExit = $LASTEXITCODE
    $sessionInvocations++

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $implementationSnapshot.LauncherPath `
        -CodexCommand $CodexCommand `
        -ExpectedLauncherSha256 $launcherSha256 `
        -CodexHome $ArmBCodexHome `
        -Workspace $ArmBWorkspace `
        -PromptPath $ArmBPromptPath `
        -StdoutPath $ArmBStdoutPath `
        -StderrPath $ArmBStderrPath `
        -ExitCodePath $ArmBExitCodePath
    $armBExit = $LASTEXITCODE
    $sessionInvocations++
}
catch {
    $caughtFailure = $true
}
finally {
    foreach ($codexHomePath in @($ArmACodexHome, $ArmBCodexHome)) {
        if (Test-Path -LiteralPath $codexHomePath) {
            foreach ($child in @(Get-ChildItem -LiteralPath $codexHomePath -Force)) {
                Remove-Item -LiteralPath $child.FullName -Recurse -Force
            }
        }
    }
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
        credential_seed_compare = if ($seedCompare) { 'PASS' } else { 'FAIL' }
        login_status = [ordered]@{
            A = if ($loginA) { 'PASS' } else { 'FAIL' }
            B = if ($loginB) { 'PASS' } else { 'FAIL' }
        }
        implementation = [ordered]@{
            credential_common_sha256 = $credentialCommonSha256
            launcher_sha256 = $launcherSha256
            pair_runner_sha256 = $pairRunnerSha256
        }
        route_plan_sha256 = $routePlanSha256
        schema = 'gate3-codex-credential-runner-receipt.v2'
        secret_material_retained = $secretMaterialRetained
        session_exit_codes = [ordered]@{
            A = $armAExit
            B = $armBExit
        }
        session_invocations = $sessionInvocations
    }
    Write-Utf8Atomic `
        -Path $PrivateReceiptPath `
        -Text (($receipt | ConvertTo-Json -Depth 5) + [Environment]::NewLine)
    Close-ImplementationSnapshot -Snapshot $implementationSnapshot
}

if ($caughtFailure) {
    [Console]::Error.WriteLine('Credential runner failed closed.')
    exit 2
}
if ($armAExit -ne 0 -or $armBExit -ne 0) {
    [Console]::Error.WriteLine('One or more authorized sessions failed.')
    exit 1
}
Write-Output 'PAIR_RUNNER_STATUS=PASS SESSION_INVOCATIONS=2'
exit 0
