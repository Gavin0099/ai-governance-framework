param(
    [Parameter(Mandatory = $true)]
    [string]$CodexCommand,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedLauncherSha256,
    [Parameter(Mandatory = $true)]
    [string]$CodexHome,
    [Parameter(Mandatory = $true)]
    [string]$Workspace,
    [Parameter(Mandatory = $true)]
    [string]$PromptPath,
    [Parameter(Mandatory = $true)]
    [string]$StdoutPath,
    [Parameter(Mandatory = $true)]
    [string]$StderrPath,
    [Parameter(Mandatory = $true)]
    [string]$ExitCodePath
)

$ErrorActionPreference = 'Stop'
$observedLauncherSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath
).Hash.ToLowerInvariant()
if ($observedLauncherSha256 -ne $ExpectedLauncherSha256) {
    throw 'Session launcher implementation identity preflight failed.'
}

foreach ($path in @($PromptPath, $CodexCommand)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required input is missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
    throw "Workspace is missing: $Workspace"
}
if (
    -not (Test-Path -LiteralPath $CodexHome -PathType Container) -or
    -not (Test-Path -LiteralPath (Join-Path $CodexHome 'auth.json') -PathType Leaf)
) {
    throw 'Preflighted Codex home is missing.'
}
foreach ($path in @($StdoutPath, $StderrPath, $ExitCodePath)) {
    if (Test-Path -LiteralPath $path) {
        throw "Output already exists: $path"
    }
    $parent = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Output parent is missing: $parent"
    }
}

$safeWorkspace = ([System.IO.Path]::GetFullPath($Workspace)).Replace('\', '/')
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = $safeWorkspace
$env:PYTHONDONTWRITEBYTECODE = '1'

$syntheticGitName = 'Gate3 Synthetic Producer'
$syntheticGitEmail = 'gate3-producer@example.invalid'
& git -C $Workspace config --local user.name $syntheticGitName
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to set the frozen synthetic Git user name.'
}
& git -C $Workspace config --local user.email $syntheticGitEmail
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to set the frozen synthetic Git user email.'
}
$actualGitName = (& git -C $Workspace config --local --get user.name)
if ($LASTEXITCODE -ne 0) {
    throw 'Frozen synthetic Git user name verification failed.'
}
$actualGitEmail = (& git -C $Workspace config --local --get user.email)
if ($LASTEXITCODE -ne 0) {
    throw 'Frozen synthetic Git user email verification failed.'
}
if ($actualGitName -ne $syntheticGitName -or $actualGitEmail -ne $syntheticGitEmail) {
    throw 'Frozen synthetic Git identity verification failed.'
}

$arguments = @(
    'exec',
    '--strict-config',
    '--ignore-user-config',
    '--ignore-rules',
    '--dangerously-bypass-approvals-and-sandbox',
    '--json',
    '--color', 'never',
    '--model', 'gpt-5.6-luna',
    '--config', 'model_reasoning_effort="low"',
    '--cd', $Workspace,
    '-'
)

$priorCodexHome = $env:CODEX_HOME
try {
    $env:CODEX_HOME = $CodexHome
    $process = Start-Process `
        -FilePath $CodexCommand `
        -ArgumentList $arguments `
        -RedirectStandardInput $PromptPath `
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

$temporaryExitPath = "$ExitCodePath.tmp-$PID"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $temporaryExitPath,
    ([string]$process.ExitCode) + [Environment]::NewLine,
    $utf8
)
Move-Item -LiteralPath $temporaryExitPath -Destination $ExitCodePath
exit $process.ExitCode
