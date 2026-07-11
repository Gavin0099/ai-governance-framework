# Owner-executed elevated cleanup of sandbox-ACL-locked temp directories.
# Authorization: owner granted environment ACL cleanup on 2026-07-11.
# Run from an ADMINISTRATOR PowerShell:
#   cd D:\ai-governance-framework
#   & .\artifacts\evidence\test-results\cleanup-acl-locked-tmp-dirs-20260711.ps1
#
# Scope is pinned to exactly the paths listed below. The script refuses to
# touch anything else, records per-path results, and writes a result JSON.

$ErrorActionPreference = 'Continue'
$repo = 'D:\ai-governance-framework'
$resultPath = Join-Path $repo 'artifacts\evidence\test-results\cleanup-acl-locked-tmp-dirs-20260711.result.json'
if (Test-Path -LiteralPath $resultPath) { throw "Refusing to overwrite existing result: $resultPath" }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'This script must run in an elevated (Administrator) PowerShell.'
}

# Pinned scope: 25 ACL-locked directories (verified 2026-07-11) + 3 readable
# same-family leftovers. Nothing outside this list is touched.
$lockedDirs = @(
    '.tmp_anchor_provenance_tests',
    '.tmp_codex_closeout_bypass_tests',
    '.tmp_evidence_truth_tests',
    '.tmp_ok_meaning_tests',
    '.tmp_pytest_ab_cost_retire',
    '.tmp_pytest_ai_governance',
    '.tmp_pytest_consumer_fixture_runner',
    '.tmp_pytest_consumer_fixture_runner_memory_sync',
    '.tmp_pytest_external_updater_focus',
    '.tmp_pytest_external_updater_focus2',
    '.tmp_pytest_maturity_table_focus',
    '.tmp_pytest_maturity_table_integration',
    '.tmp_pytest_maturity_table_zh2_focus',
    '.tmp_pytest_maturity_table_zh2_integration',
    '.tmp_pytest_maturity_table_zh_commit',
    '.tmp_pytest_maturity_table_zh_focus',
    '.tmp_pytest_maturity_table_zh_focus2',
    '.tmp_pytest_maturity_table_zh_integration',
    '.tmp_pytest_maturity_table_zh_integration2',
    '.tmp_pytest_memory_guard',
    '.tmp_pytest_update_human_table_integration',
    '.tmp_pytest_updater_human_table',
    '.tmp_session_provenance_tests',
    '.tmp_status_check',
    '.tmp_writer_bypass_tests'
)
$readableDirs = @('.tmp_contract_review', '.tmp-pytest', '.pytest_cache')

$results = @()
foreach ($name in ($lockedDirs + $readableDirs)) {
    $path = Join-Path $repo $name
    $entry = [ordered]@{ path = $path; existed = (Test-Path -LiteralPath $path) }
    if (-not $entry.existed) { $entry.outcome = 'absent'; $results += $entry; continue }
    try {
        takeown /F $path /R /D Y | Out-Null
        icacls $path /reset /T /C /Q | Out-Null
        Remove-Item -LiteralPath $path -Recurse -Force -Confirm:$false
        $entry.outcome = if (Test-Path -LiteralPath $path) { 'REMOVAL_FAILED_STILL_PRESENT' } else { 'removed' }
    } catch {
        $entry.outcome = "error: $($_.Exception.Message)"
    }
    $results += $entry
}

$summary = [ordered]@{
    schema = 'acl_cleanup_result.v0.1'
    executed_at = [DateTime]::UtcNow.ToString('o')
    executed_by = $identity.Name
    elevated = $true
    pinned_scope_count = ($lockedDirs + $readableDirs).Count
    removed = @($results | Where-Object { $_.outcome -eq 'removed' }).Count
    absent = @($results | Where-Object { $_.outcome -eq 'absent' }).Count
    failed = @($results | Where-Object { $_.outcome -notin @('removed','absent') }).Count
    results = $results
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output ("removed={0} absent={1} failed={2} result={3}" -f $summary.removed, $summary.absent, $summary.failed, $resultPath)
