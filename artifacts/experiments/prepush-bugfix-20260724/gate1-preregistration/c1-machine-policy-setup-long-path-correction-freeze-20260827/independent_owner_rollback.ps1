param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Precheck', 'Rollback')]
    [string] $Mode,
    [Parameter(Mandatory = $true)]
    [string] $SetupFreezeCommit,
    [Parameter(Mandatory = $true)]
    [string] $ReceiptPath,
    [string] $TerminalPath,
    [string] $RollbackRequestPath,
    [string] $RollbackHeartbeatPath,
    [string[]] $CreatedDirectories = @()
)

$ErrorActionPreference = 'Stop'
$ExpectedBytes = 58
$ExpectedSha256 = '9aa1f17cc4a36a3ac502862eb42d84044799eaf1b4de7c8cb1e31a25b10c3440'
$ExpectedPowerShellSha256 = '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5'
$Target = [IO.Path]::GetFullPath((Join-Path $env:ProgramData 'OpenAI\Codex\requirements.toml'))
$PolicyRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramData 'OpenAI\Codex'))

function Get-FileSha256([string] $Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-Utf8Sha256([string] $Text) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = $algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))
    } finally {
        $algorithm.Dispose()
    }
    return -join ($hash | ForEach-Object { $_.ToString('x2') })
}

function Write-Receipt([hashtable] $Value) {
    $parent = Split-Path -Parent $ReceiptPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw 'receipt parent is unavailable'
    }
    $json = ($Value | ConvertTo-Json -Compress -Depth 5) + "`n"
    [IO.File]::WriteAllText($ReceiptPath, $json, [Text.UTF8Encoding]::new($false))
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-ExactTargetPath {
    if ([IO.Path]::GetFullPath($Target) -ne (Join-Path $PolicyRoot 'requirements.toml')) {
        throw 'target path differs from frozen path'
    }
    $cursor = $PolicyRoot
    while ($cursor -and (Test-Path -LiteralPath $cursor)) {
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'reparse point in policy path'
        }
        $cursor = Split-Path -Parent $cursor
        if ($cursor -eq [IO.Path]::GetPathRoot($cursor)) { break }
    }
}

if (-not (Test-Administrator)) {
    throw 'independent owner shell is not elevated'
}
Assert-ExactTargetPath
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDigest = Get-FileSha256 $scriptPath
$powerShellDigest = Get-FileSha256 ([Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)
$ownerIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$ownerSidDigest = Get-Utf8Sha256 ([string]$ownerIdentity.User.Value)

if ($Mode -eq 'Precheck') {
    if (Test-Path -LiteralPath $Target) { throw 'target exists before setup' }
    if (-not $TerminalPath -or -not $RollbackRequestPath -or -not $RollbackHeartbeatPath) {
        throw 'terminal, rollback request, and heartbeat paths are required'
    }
    $scriptRoot = [IO.Path]::GetFullPath((Split-Path -Parent $scriptPath))
    $terminalRoot = [IO.Path]::GetFullPath((Split-Path -Parent $TerminalPath))
    $outside = -not $scriptRoot.StartsWith($PolicyRoot, [StringComparison]::OrdinalIgnoreCase) -and
        -not $scriptRoot.StartsWith($terminalRoot, [StringComparison]::OrdinalIgnoreCase)
    if (-not $outside) { throw 'rollback script is not independent from policy and scratch roots' }
    $receipt = [ordered]@{
        schema = 'c1-machine-policy-independent-rollback-precheck.v2'
        setup_freeze_commit = $SetupFreezeCommit
        rollback_script_sha256 = $scriptDigest
        powershell_executable_sha256 = $powerShellDigest
        owner_sid_sha256 = $ownerSidDigest
        owner_account_class = 'owner_administrator'
        owner_shell_independent_from_codex = $true
        administrator_role_enabled = $true
        target_absent = $true
        rollback_script_outside_policy_and_scratch_roots = $true
        shell_held_open_until_terminal = $true
        observed_at_utc = [DateTime]::UtcNow.ToString('o')
        status = 'INDEPENDENT_ELEVATED_ROLLBACK_CHANNEL_READY'
        diagnostic = 'independent elevated owner shell held open for setup terminal'
    }
    Write-Receipt $receipt
    while (-not (Test-Path -LiteralPath $TerminalPath -PathType Leaf)) {
        [IO.File]::WriteAllText(
            $RollbackHeartbeatPath,
            [DateTime]::UtcNow.ToString('o'),
            [Text.UTF8Encoding]::new($false)
        )
        if (Test-Path -LiteralPath $RollbackRequestPath -PathType Leaf) { break }
        Start-Sleep -Milliseconds 250
    }
    if (Test-Path -LiteralPath $TerminalPath -PathType Leaf) { exit 0 }
}

$status = 'MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED'
$diagnostic = 'installed target differs from exact rollback binding'
$deleteDispatched = $false
if (Test-Path -LiteralPath $Target -PathType Leaf) {
    $item = Get-Item -LiteralPath $Target -Force
    $isRegular = (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)
    if ($isRegular -and $item.Length -eq $ExpectedBytes -and (Get-FileSha256 $Target) -eq $ExpectedSha256) {
        $deleteDispatched = $true
        Remove-Item -LiteralPath $Target -Force
        if (Test-Path -LiteralPath $Target) {
            $status = 'MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS'
            $diagnostic = 'delete dispatched but target absence is unverified'
        } else {
            $status = 'MACHINE_POLICY_ROLLBACK_COMPLETE'
            $diagnostic = 'exact managed requirement removed'
        }
    }
}
foreach ($name in $CreatedDirectories) {
    if ($name -notin @('Codex', 'OpenAI')) { continue }
    $candidate = if ($name -eq 'Codex') { $PolicyRoot } else { Split-Path -Parent $PolicyRoot }
    if ((Test-Path -LiteralPath $candidate -PathType Container) -and
        @(Get-ChildItem -LiteralPath $candidate -Force).Count -eq 0) {
        Remove-Item -LiteralPath $candidate -Force
    }
}
Write-Receipt ([ordered]@{
    schema = 'c1-machine-policy-independent-rollback-receipt.v1'
    setup_freeze_commit = $SetupFreezeCommit
    rollback_script_sha256 = $scriptDigest
    target_expected_sha256 = $ExpectedSha256
    deletion_dispatched = $deleteDispatched
    target_absent_verified = -not (Test-Path -LiteralPath $Target)
    status = $status
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
    diagnostic = $diagnostic
})
if ($status -ne 'MACHINE_POLICY_ROLLBACK_COMPLETE') { exit 2 }
