$ErrorActionPreference = "Stop"

$scratch = "D:\ai-governance-framework\artifacts\runtime\v2-codex-write-probe"
$probe = Join-Path $scratch "write-probe.txt"
$stdoutPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.jsonl"
$stderrPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.stderr.txt"
$resultPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.result.json"
$sandboxLog = "C:\Users\daish\.codex\.sandbox\sandbox.2026-07-10.log"

if (Test-Path -LiteralPath $probe) { throw "Probe unexpectedly exists" }
$status = @(git -C $scratch -c "safe.directory=$scratch" status --short)
if ($LASTEXITCODE -ne 0 -or $status.Count -ne 0) { throw "Scratch repo is not clean" }
$tracked = @(git -C $scratch -c "safe.directory=$scratch" ls-files)
if ($LASTEXITCODE -ne 0 -or $tracked.Count -ne 1 -or $tracked[0] -ne "README.md") {
    throw "Scratch tracked set is not exactly README.md"
}

$stdout = Get-Content -Raw -LiteralPath $stdoutPath
$stderr = Get-Content -Raw -LiteralPath $stderrPath
$result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
if ($result.exit_code -ne 0) { throw "Codex process exit code changed" }
if ($stdout -notmatch '"status":"failed"' -or $stdout -notmatch 'helper_unknown_error') {
    throw "Raw stdout does not preserve semantic failure"
}
if ($stderr -notmatch 'Failed to write file' -or $stderr -notmatch 'setup refresh had errors') {
    throw "Raw stderr does not preserve write/setup failure"
}

$acl = Get-Acl -LiteralPath $scratch
if ($acl.Owner -ne "DESKTOP-EJOULKM\CodexSandboxOffline") {
    throw "Unexpected scratch owner: $($acl.Owner)"
}
$logEvidence = @(Select-String -LiteralPath $sandboxLog -Pattern 'SetNamedSecurityInfoW failed: 5' | Where-Object { $_.LineNumber -ge 9518 -and $_.LineNumber -le 9546 })
if ($logEvidence.Count -eq 0) { throw "Sandbox ACL failure not found in expected run window" }

[ordered]@{
    semantic_result = "FAIL"
    process_exit_code = 0
    probe_exists = $false
    scratch_status_entries = 0
    tracked_files = $tracked
    scratch_owner = $acl.Owner
    helper_spawned = $true
    write_ace_error = "SetNamedSecurityInfoW failed: 5"
    sandbox_log_lines = @($logEvidence | ForEach-Object { $_.LineNumber })
    sandbox_log_evidence = @($logEvidence | ForEach-Object { $_.Line.Trim() })
    qualification_pass = $false
    v2_preregistration_allowed = $false
} | ConvertTo-Json -Compress | Write-Output
