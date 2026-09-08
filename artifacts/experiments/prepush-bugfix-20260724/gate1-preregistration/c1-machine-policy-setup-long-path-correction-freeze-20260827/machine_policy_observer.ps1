param(
    [ValidateSet('Identity', 'Full')]
    [string] $Mode = 'Full'
)

$ErrorActionPreference = 'Stop'
$SandboxAccountSidSha256 = 'f0499f65a3828dfd191d0f3179ee47528dd723df2c1753e0f4131f83cd5017ce'

function Get-Sha256Hex([byte[]] $Bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { $hash = $algorithm.ComputeHash($Bytes) } finally { $algorithm.Dispose() }
    return -join ($hash | ForEach-Object { $_.ToString('x2') })
}

function Get-Utf8Sha256([string] $Text) {
    return Get-Sha256Hex ([Text.Encoding]::UTF8.GetBytes($Text))
}

function Get-BoundedErrorClass([System.Management.Automation.ErrorRecord] $Record) {
    $category = [string]$Record.CategoryInfo.Category
    $errorId = [string]$Record.FullyQualifiedErrorId
    $typeName = [string]$Record.Exception.GetType().FullName
    if ($category -eq 'PermissionDenied' -or
        $errorId -match 'AccessDenied|Unauthorized' -or
        $typeName -match 'UnauthorizedAccess') {
        return 'INSUFFICIENT_PRIVILEGE'
    }
    return 'CMDLET_FAILURE'
}

function Write-Envelope(
    [string] $Status,
    [string] $Stage,
    [string] $ErrorClass,
    [object] $Identity,
    [object] $MachineState
) {
    $value = [ordered]@{
        schema = 'c1-machine-policy-observation.v2'
        mode = $Mode.ToLowerInvariant()
        status = $Status
        stage = $Stage
        error_class = $ErrorClass
        identity = $Identity
        machine_state = $MachineState
    }
    [Console]::Out.Write(($value | ConvertTo-Json -Compress -Depth 6))
}

function Stop-Bounded(
    [string] $Stage,
    [string] $ErrorClass,
    [object] $Identity
) {
    Write-Envelope 'OBSERVATION_FAILED' $Stage $ErrorClass $Identity $null
    exit 12
}

$identity = $null
try {
    $windowsIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $sidDigest = Get-Utf8Sha256 ([string]$windowsIdentity.User.Value)
    $principal = [Security.Principal.WindowsPrincipal]::new($windowsIdentity)
    $administrator = $principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    $accountClass = if ($sidDigest -eq $SandboxAccountSidSha256) {
        'sandbox_account'
    } else {
        'owner_candidate'
    }
    $identity = [ordered]@{
        sid_sha256 = $sidDigest
        account_class = $accountClass
        administrator_role_enabled = [bool]$administrator
    }
} catch {
    Stop-Bounded 'identity' 'IDENTITY_QUERY_FAILED' $null
}

if (-not $identity.administrator_role_enabled -or
    $identity.account_class -eq 'sandbox_account') {
    Stop-Bounded 'identity' 'INSUFFICIENT_PRIVILEGE' $identity
}

if ($Mode -eq 'Identity') {
    Write-Envelope 'OBSERVATION_PASSED' 'identity_complete' 'NONE' $identity $null
    exit 0
}

try {
    $account = Get-LocalUser -Name 'CodexSandboxOffline'
    $sandboxSid = [string]$account.SID.Value
    $sandboxSidDigest = Get-Utf8Sha256 $sandboxSid
} catch {
    Stop-Bounded 'sandbox_account' (Get-BoundedErrorClass $_) $identity
}

try {
    $profiles = @{}
    Get-NetFirewallProfile | ForEach-Object {
        $profiles[[string]$_.Name] = [bool]$_.Enabled
    }
} catch {
    Stop-Bounded 'firewall_profiles' (Get-BoundedErrorClass $_) $identity
}

try {
    $block = Get-NetFirewallRule -Direction Outbound -Action Block |
        Where-Object DisplayName -eq 'codex_sandbox_offline_block_outbound'
    $allow = Get-NetFirewallRule -Direction Outbound -Action Allow |
        Where-Object DisplayName -eq 'Codex'
} catch {
    Stop-Bounded 'firewall_rules' (Get-BoundedErrorClass $_) $identity
}
if (@($block).Count -ne 1 -or @($allow).Count -ne 1) {
    Stop-Bounded 'firewall_rule_set' 'STATE_MISMATCH' $identity
}

try {
    $security = $block | Get-NetFirewallSecurityFilter
    $descriptor = [string]$security.LocalUser
    $relation = $descriptor.Contains($sandboxSid)
} catch {
    Stop-Bounded 'firewall_security_filter' (Get-BoundedErrorClass $_) $identity
}

try {
    $summary = @(
        [ordered]@{
            class = 'sandbox_offline'
            enabled = ([string]$block.Enabled -eq 'True') -or ([int]$block.Enabled -eq 1)
            profile = [string]$block.Profile
            direction = [string]$block.Direction
            action = [string]$block.Action
            status_ok = ([string]$block.Status -match '65536')
            local_user_sha256 = Get-Utf8Sha256 $descriptor
        },
        [ordered]@{
            class = 'codex_application'
            enabled = ([string]$allow.Enabled -eq 'True') -or ([int]$allow.Enabled -eq 1)
            profile = [string]$allow.Profile
            direction = [string]$allow.Direction
            action = [string]$allow.Action
            status_ok = ([string]$allow.Status -match '65536')
            local_user_sha256 = $null
        }
    )
    $summaryBytes = [Text.Encoding]::UTF8.GetBytes(
        ($summary | ConvertTo-Json -Compress -Depth 4)
    )
} catch {
    Stop-Bounded 'firewall_projection' (Get-BoundedErrorClass $_) $identity
}

try {
    $target = Join-Path $env:ProgramData 'OpenAI\Codex\requirements.toml'
    $legacy = Join-Path $env:ProgramData 'OpenAI\Codex\managed-requirements.toml'
    $userTarget = Join-Path $env:USERPROFILE '.codex\requirements.toml'
    $machineState = [ordered]@{
        account_present = $true
        account_enabled = [bool]$account.Enabled
        password_required = [bool]$account.PasswordRequired
        sid_sha256 = $sandboxSidDigest
        domain_profile_enabled = [bool]$profiles['Domain']
        private_profile_enabled = [bool]$profiles['Private']
        public_profile_enabled = [bool]$profiles['Public']
        relevant_outbound_rule_count = 2
        outbound_block_rule_count = 1
        outbound_allow_rule_count = 1
        rule_summary_bytes = $summaryBytes.Length
        rule_summary_sha256 = Get-Sha256Hex $summaryBytes
        account_block_relation_verified = $relation
        security_descriptor_sha256 = Get-Utf8Sha256 $descriptor
        target_exists = Test-Path -LiteralPath $target -PathType Leaf
        legacy_target_exists = Test-Path -LiteralPath $legacy -PathType Leaf
        user_target_exists = Test-Path -LiteralPath $userTarget -PathType Leaf
    }
} catch {
    Stop-Bounded 'target_paths' (Get-BoundedErrorClass $_) $identity
}

Write-Envelope 'OBSERVATION_PASSED' 'complete' 'NONE' $identity $machineState
