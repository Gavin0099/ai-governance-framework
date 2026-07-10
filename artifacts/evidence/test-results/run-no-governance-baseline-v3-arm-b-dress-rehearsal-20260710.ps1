$ErrorActionPreference = "Stop"

$frameworkRoot = "D:\ai-governance-framework"
$source = "C:\Users\daish\.codex\visualizations\2026\07\10\019f4c83-2f1f-7b30-af00-324063641a72\v3-baseline-arm-a-dress-rehearsal-retry2"
$scratch = "C:\Users\daish\.codex\visualizations\2026\07\10\019f4c83-2f1f-7b30-af00-324063641a72\v3-governed-arm-b-dress-rehearsal-retry"
$resultPath = Join-Path $frameworkRoot "artifacts\evidence\test-results\raw-no-governance-baseline-v3-arm-b-dress-rehearsal-20260710.result.json"
$expectedSeedTree = "27b7d8f9e7c7b7bccce5d47ce991c92a6e3fea71"
$python = Join-Path $frameworkRoot ".venv\Scripts\python.exe"

foreach ($path in @($scratch, $resultPath)) {
    if (Test-Path -LiteralPath $path) { throw "Refusing to reuse or overwrite: $path" }
}

$sourceTree = (git -C $source -c "safe.directory=$source" rev-parse "HEAD^{tree}").Trim()
if ($sourceTree -ne $expectedSeedTree) { throw "Unexpected source seed tree: $sourceTree" }

git clone --no-hardlinks $source $scratch
if ($LASTEXITCODE -ne 0) { throw "Failed to clone verified seed" }
$scratchTree = (git -C $scratch rev-parse "HEAD^{tree}").Trim()
if ($scratchTree -ne $expectedSeedTree) { throw "Fresh Arm B copy does not match seed tree: $scratchTree" }

$installerOutput = & $python (Join-Path $frameworkRoot "governance_tools\hook_installer.py") --repo $scratch --framework-root $frameworkRoot --hooks-only --format json 2>&1
$installerExit = $LASTEXITCODE
if ($installerExit -ne 0) { throw "hook_installer exited $installerExit`n$($installerOutput -join "`n")" }
$installer = ($installerOutput -join "`n") | ConvertFrom-Json
if (-not $installer.ok) { throw "hook_installer reported ok=false" }

$validatorOutput = & $python (Join-Path $frameworkRoot "governance_tools\hook_install_validator.py") --repo $scratch --framework-root $frameworkRoot --format json 2>&1
$validatorExit = $LASTEXITCODE
if ($validatorExit -ne 0) { throw "hook_install_validator exited $validatorExit`n$($validatorOutput -join "`n")" }
$validator = ($validatorOutput -join "`n") | ConvertFrom-Json
if (-not $validator.valid) { throw "hook_install_validator reported valid=false" }

$probeFile = Join-Path $scratch "ARM_B_HOOK_REHEARSAL.md"
[IO.File]::WriteAllText($probeFile, "Arm B offline hook rehearsal only.`n", [Text.UTF8Encoding]::new($false))
git -C $scratch add -- ARM_B_HOOK_REHEARSAL.md
$previousTrace = $env:GIT_TRACE
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$env:GIT_TRACE = "1"
$commitOutput = & git -C $scratch -c user.name="v3-arm-b-rehearsal" -c user.email="v3-arm-b-rehearsal@local.invalid" commit -m "v3 arm b hook rehearsal" 2>&1
$commitExit = $LASTEXITCODE
$env:GIT_TRACE = $previousTrace
$ErrorActionPreference = $previousErrorActionPreference
if ($commitExit -ne 0) { throw "manual commit exited $commitExit`n$($commitOutput -join "`n")" }
$commitText = $commitOutput -join "`n"
if ($commitText -notmatch "pre-commit") { throw "GIT_TRACE did not show pre-commit invocation" }

$status = @(git -C $scratch status --short)
if ($status.Count -ne 0) { throw "Arm B scratch is not clean after hook rehearsal: $($status -join '; ')" }
$hookConfig = Get-Content -Raw -LiteralPath (Join-Path $scratch ".git\hooks\ai-governance-framework-root")
if ($hookConfig.Trim() -ne $frameworkRoot) { throw "framework root hook config mismatch" }

[ordered]@{
    schema = "no_governance_baseline_v3_arm_b_dress_rehearsal.v0.1"
    api_call_performed = $false
    scratch = $scratch
    scratch_root_owner = (Get-Acl -LiteralPath $scratch).Owner
    source_seed_tree_hash = $sourceTree
    scratch_seed_tree_hash = $scratchTree
    hook_install = [ordered]@{ exit_code = $installerExit; ok = $installer.ok; changed_files = $installer.changed_files; errors = $installer.errors }
    hook_validation = [ordered]@{ exit_code = $validatorExit; valid = $validator.valid }
    manual_commit = [ordered]@{ exit_code = $commitExit; trace_showed_pre_commit = $true; output = $commitText }
    framework_root_hook_config = $hookConfig.Trim()
    post_rehearsal_git_status = $status
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8

Write-Output "PASS v3 Arm B offline dress rehearsal completed; api_call_performed=false; seed_tree_hash=$scratchTree"
