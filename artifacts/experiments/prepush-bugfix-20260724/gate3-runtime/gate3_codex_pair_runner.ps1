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
$credentialSource = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\auth.json'
$privateRoot = Split-Path -Parent $PrivateReceiptPath
$userTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
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
$preflightPassed = $false
$sessionInvocations = 0
$armAExit = $null
$armBExit = $null
$caughtFailure = $false
$loginA = $false
$loginB = $false
$seedCompare = $false
$pairRunnerSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath
).Hash.ToLowerInvariant()
$launcherSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $launcher
).Hash.ToLowerInvariant()
$routePlanSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $RoutePlanPath
).Hash.ToLowerInvariant()

function Write-Utf8Atomic {
    param([string]$Path, [string]$Text)
    $temporary = "$Path.tmp-$PID"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temporary, $Text, $utf8)
    Move-Item -LiteralPath $temporary -Destination $Path
}

function Assert-UserTempPath {
    param([string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $tempPrefix = $userTemp.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith(
        $tempPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw 'Credential runner private runtime path is outside user Temp.'
    }
}

function Set-CurrentUserOnlyAcl {
    param(
        [string]$Path,
        [switch]$Container
    )
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    if ($Container) {
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            (
                [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
                [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
            ),
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
    }
    else {
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
    }
    $acl.SetAccessRuleProtection($true, $false)
    [void]$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
    $observed = Get-Acl -LiteralPath $Path
    $allowRules = @(
        $observed.Access |
            Where-Object {
                $_.AccessControlType -eq
                    [System.Security.AccessControl.AccessControlType]::Allow
            }
    )
    if (
        -not $observed.AreAccessRulesProtected -or
        $allowRules.Count -ne 1 -or
        $allowRules[0].IdentityReference.Translate(
            [System.Security.Principal.SecurityIdentifier]
        ).Value -ne $sid.Value -or
        $allowRules[0].FileSystemRights -ne
            [System.Security.AccessControl.FileSystemRights]::FullControl
    ) {
        throw 'Private credential ACL verification failed.'
    }
}

function Copy-PrivateCredential {
    param([string]$Source, [string]$Destination)
    $temporary = "$Destination.tmp-$PID"
    try {
        [System.IO.File]::Copy($Source, $temporary, $false)
        Set-CurrentUserOnlyAcl -Path $temporary
        Move-Item -LiteralPath $temporary -Destination $Destination
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Test-ExactBytes {
    param([string]$Left, [string]$Right)
    $leftBytes = [System.IO.File]::ReadAllBytes($Left)
    $rightBytes = [System.IO.File]::ReadAllBytes($Right)
    if ($leftBytes.Length -ne $rightBytes.Length) {
        return $false
    }
    $difference = 0
    for ($index = 0; $index -lt $leftBytes.Length; $index++) {
        $difference = $difference -bor ($leftBytes[$index] -bxor $rightBytes[$index])
    }
    return $difference -eq 0
}

function Test-ChatGptLogin {
    param(
        [string]$CodexHome,
        [string]$StdoutPath,
        [string]$StderrPath
    )
    $priorCodexHome = $env:CODEX_HOME
    try {
        $env:CODEX_HOME = $CodexHome
        $process = Start-Process `
            -FilePath $CodexCommand `
            -ArgumentList @('login', 'status') `
            -RedirectStandardOutput $StdoutPath `
            -RedirectStandardError $StderrPath `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
    }
    finally {
        if ($null -eq $priorCodexHome) {
            Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
        }
        else {
            $env:CODEX_HOME = $priorCodexHome
        }
    }
    if ($process.ExitCode -ne 0) {
        return $false
    }
    $statusText = (
        (Get-Content -Raw -LiteralPath $StdoutPath) + "`n" +
        (Get-Content -Raw -LiteralPath $StderrPath)
    )
    return $statusText -match '(?i)ChatGPT'
}

foreach ($requiredFile in @(
    $CodexCommand,
    $credentialSource,
    $RoutePlanPath,
    $ArmAPromptPath,
    $ArmBPromptPath,
    $launcher
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw 'Credential runner required input is missing.'
    }
}
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
$routePlan = Get-Content -Raw -LiteralPath $RoutePlanPath | ConvertFrom-Json
if (
    $routePlan.schema -ne 'gate3-codex-live-route-plan.v4' -or
    $routePlan.frozen_route.pair_runner_implementation_sha256 -ne
        $pairRunnerSha256 -or
    $routePlan.frozen_route.launcher_implementation_sha256 -ne
        $launcherSha256
) {
    throw 'Credential runner implementation identity preflight failed.'
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
        -CodexHome $ArmACodexHome `
        -StdoutPath $loginAOut `
        -StderrPath $loginAErr
    $loginB = Test-ChatGptLogin `
        -CodexHome $ArmBCodexHome `
        -StdoutPath $loginBOut `
        -StderrPath $loginBErr
    if (-not $loginA -or -not $loginB) {
        throw 'Credential preflight did not confirm the ChatGPT route.'
    }
    if (-not (Test-ExactBytes -Left $armAAuth -Right $armBAuth)) {
        throw 'Credential homes differ after login preflight.'
    }
    $preflightPassed = $true

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher `
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

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher `
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
            launcher_sha256 = $launcherSha256
            pair_runner_sha256 = $pairRunnerSha256
        }
        route_plan_sha256 = $routePlanSha256
        schema = 'gate3-codex-credential-runner-receipt.v1'
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
