param(
    [Parameter(Mandatory = $true)]
    [string]$CodexCommand,
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

foreach ($path in @($PromptPath, $CodexCommand)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required input is missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
    throw "Workspace is missing: $Workspace"
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

$process = Start-Process `
    -FilePath $CodexCommand `
    -ArgumentList $arguments `
    -RedirectStandardInput $PromptPath `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -WindowStyle Hidden `
    -Wait `
    -PassThru

$temporaryExitPath = "$ExitCodePath.tmp-$PID"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $temporaryExitPath,
    ([string]$process.ExitCode) + [Environment]::NewLine,
    $utf8
)
Move-Item -LiteralPath $temporaryExitPath -Destination $ExitCodePath
exit $process.ExitCode
