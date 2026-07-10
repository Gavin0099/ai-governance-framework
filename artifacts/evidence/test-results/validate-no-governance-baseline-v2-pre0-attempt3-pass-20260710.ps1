$ErrorActionPreference = "Stop"

$scratch = "D:\ai-governance-framework\artifacts\runtime\v2-codex-write-probe-attempt3"
$probe = Join-Path $scratch "write-probe.txt"
$stdoutPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-attempt3-20260710.jsonl"
$stderrPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-attempt3-20260710.stderr.txt"
$resultPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-attempt3-20260710.result.json"
$sandboxLog = "C:\Users\daish\.codex\.sandbox\sandbox.2026-07-10.log"
$expectedOwner = "DESKTOP-EJOULKM\daish"
$expectedBytes = [Text.Encoding]::UTF8.GetBytes("workspace-write-ok`n")

if (-not (Test-Path -LiteralPath $probe)) { throw "Probe file is absent" }
$actualBytes = [IO.File]::ReadAllBytes($probe)
if ($actualBytes.Length -ne $expectedBytes.Length) { throw "Unexpected probe length: $($actualBytes.Length)" }
for ($i = 0; $i -lt $expectedBytes.Length; $i++) {
    if ($actualBytes[$i] -ne $expectedBytes[$i]) { throw "Probe byte mismatch at offset $i" }
}

$status = @(git -C $scratch status --short)
if ($LASTEXITCODE -ne 0 -or $status.Count -ne 1 -or $status[0] -ne "?? write-probe.txt") {
    throw "Scratch status is not exactly the probe file"
}
$tracked = @(git -C $scratch ls-files)
if ($LASTEXITCODE -ne 0 -or $tracked.Count -ne 1 -or $tracked[0] -ne "README.md") {
    throw "Scratch tracked set is not exactly README.md"
}

$acl = Get-Acl -LiteralPath $scratch
if ($acl.Owner -ne $expectedOwner) { throw "Unexpected scratch owner: $($acl.Owner)" }
$stdout = Get-Content -Raw -LiteralPath $stdoutPath
$stderrBytes = [IO.File]::ReadAllBytes($stderrPath)
$result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
if ($result.exit_code -ne 0 -or -not $result.package_context -or -not $result.prevent_breakaway) {
    throw "Launcher result does not preserve the qualified configuration"
}
if ($stdout -notmatch '"status":"completed"' -or $stdout -notmatch 'CONTENT=<workspace-write-ok\\n>' -or $stdout -notmatch '\?\? write-probe.txt') {
    throw "Raw stdout does not preserve successful write/readback/status"
}
if ($stderrBytes.Length -ne 0) { throw "Raw stderr is not empty" }

$logEvidence = @(Select-String -LiteralPath $sandboxLog -Pattern 'setup refresh: processed 2 write roots \(read roots delegated\); errors=\[\]' | Where-Object { $_.LineNumber -ge 9913 -and $_.LineNumber -le 9954 })
$logErrors = @(Select-String -LiteralPath $sandboxLog -Pattern 'setup error|completed with errors|SetNamedSecurityInfoW failed' | Where-Object { $_.LineNumber -ge 9913 -and $_.LineNumber -le 9954 })
if ($logEvidence.Count -eq 0 -or $logErrors.Count -ne 0) { throw "Sandbox helper window is not clean" }

[ordered]@{
    semantic_result = "PASS"
    process_exit_code = 0
    probe_exists = $true
    probe_length = $actualBytes.Length
    expected_utf8_text = "workspace-write-ok`n"
    scratch_status = $status
    tracked_files = $tracked
    scratch_owner = $acl.Owner
    package_context = $true
    prevent_breakaway = $true
    helper_errors = @()
    sandbox_log_lines = @($logEvidence | ForEach-Object { $_.LineNumber })
    sandbox_log_evidence = @($logEvidence | ForEach-Object { $_.Line.Trim() })
    qualification_pass = $true
    v2_preregistration_created = $false
} | ConvertTo-Json -Compress | Write-Output
