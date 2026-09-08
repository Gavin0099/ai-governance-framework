$ErrorActionPreference = 'Stop'

function Get-Sha256Hex([byte[]] $Bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { $hash = $algorithm.ComputeHash($Bytes) } finally { $algorithm.Dispose() }
    return -join ($hash | ForEach-Object { $_.ToString('x2') })
}

function Get-Utf8Sha256([string] $Text) {
    return Get-Sha256Hex ([Text.Encoding]::UTF8.GetBytes($Text))
}

$account = Get-LocalUser -Name 'CodexSandboxOffline'
$sid = [string]$account.SID.Value
$sidDigest = Get-Utf8Sha256 $sid

$profiles = @{}
Get-NetFirewallProfile | ForEach-Object {
    $profiles[[string]$_.Name] = [bool]$_.Enabled
}

$block = Get-NetFirewallRule -Direction Outbound -Action Block |
    Where-Object DisplayName -eq 'codex_sandbox_offline_block_outbound'
$allow = Get-NetFirewallRule -Direction Outbound -Action Allow |
    Where-Object DisplayName -eq 'Codex'
if (@($block).Count -ne 1 -or @($allow).Count -ne 1) {
    throw 'bounded relevant firewall rule set differs from freeze'
}
$security = $block | Get-NetFirewallSecurityFilter
$descriptor = [string]$security.LocalUser
$relation = $descriptor.Contains($sid)

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
$summaryBytes = [Text.Encoding]::UTF8.GetBytes(($summary | ConvertTo-Json -Compress -Depth 4))

$target = Join-Path $env:ProgramData 'OpenAI\Codex\requirements.toml'
$legacy = Join-Path $env:ProgramData 'OpenAI\Codex\managed-requirements.toml'
$userTarget = Join-Path $env:USERPROFILE '.codex\requirements.toml'

$result = [ordered]@{
    account_present = $true
    account_enabled = [bool]$account.Enabled
    password_required = [bool]$account.PasswordRequired
    sid_sha256 = $sidDigest
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

[Console]::Out.Write(($result | ConvertTo-Json -Compress -Depth 4))
