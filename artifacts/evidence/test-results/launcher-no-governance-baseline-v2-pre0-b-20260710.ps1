$ErrorActionPreference = "Stop"

$expectedVersion = "26.707.3748.0"
$expectedPfn = "OpenAI.Codex_2p2nqsd0c76g0"
$appId = "App"
$scratch = "D:\ai-governance-framework\artifacts\runtime\v2-codex-write-probe"
$stdoutPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.jsonl"
$stderrPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.stderr.txt"
$resultPath = "D:\ai-governance-framework\artifacts\evidence\test-results\raw-no-governance-baseline-v2-pre0-b-20260710.result.json"
$prompt = "Use apply_patch to create a new file named write-probe.txt containing exactly: workspace-write-ok. Then read the file back, run git status --short, and report whether the exact content is present. Do not modify any other file."

$package = Get-AppxPackage -Name OpenAI.Codex
if (-not $package) { throw "OpenAI.Codex package not found" }
if ($package.PackageFamilyName -ne $expectedPfn) { throw "Unexpected PFN: $($package.PackageFamilyName)" }
if ($package.Version.ToString() -ne $expectedVersion) { throw "Unexpected package version: $($package.Version)" }

$codex = Join-Path $package.InstallLocation "app\resources\codex.exe"
if (-not (Test-Path -LiteralPath $codex)) { throw "Packaged codex.exe not found" }
foreach ($path in @($stdoutPath, $stderrPath, $resultPath)) {
    if (Test-Path -LiteralPath $path) { throw "Refusing to overwrite existing evidence: $path" }
}

$tracked = @(git -C $scratch -c "safe.directory=$scratch" ls-files)
if ($LASTEXITCODE -ne 0) { throw "Unable to enumerate scratch repo" }
if ($tracked.Count -ne 1 -or $tracked[0] -ne "README.md") {
    throw "Scratch repo file set is not exactly README.md"
}
if (Test-Path -LiteralPath (Join-Path $scratch "write-probe.txt")) {
    throw "Probe file already exists before run"
}

$inner = @'
$ErrorActionPreference = "Stop"
$codex = "__CODEX__"
$scratch = "__SCRATCH__"
$stdoutPath = "__STDOUT__"
$stderrPath = "__STDERR__"
$resultPath = "__RESULT__"
$prompt = "__PROMPT__"
$startedAt = [DateTime]::UtcNow.ToString("o")
$arguments = @(
    "exec",
    "--ignore-user-config",
    "-m", "gpt-5.6-terra",
    "-c", "model_reasoning_effort=medium",
    "-c", "windows.sandbox=elevated",
    "-c", "approval_policy=on-request",
    "-c", "project_doc_max_bytes=0",
    "--disable", "multi_agent",
    "--disable", "code_mode",
    "--disable", "code_mode_host",
    "--disable", "code_mode_only",
    "-s", "workspace-write",
    "-C", $scratch,
    "--json",
    ('"' + $prompt + '"')
)
$process = Start-Process -FilePath $codex -ArgumentList $arguments -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
[ordered]@{
    exit_code = $process.ExitCode
    started_at = $startedAt
    finished_at = [DateTime]::UtcNow.ToString("o")
    package_context = $true
    prevent_breakaway = $true
} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
exit $process.ExitCode
'@

$inner = $inner.Replace("__CODEX__", $codex.Replace("\", "\"))
$inner = $inner.Replace("__SCRATCH__", $scratch.Replace("\", "\"))
$inner = $inner.Replace("__STDOUT__", $stdoutPath.Replace("\", "\"))
$inner = $inner.Replace("__STDERR__", $stderrPath.Replace("\", "\"))
$inner = $inner.Replace("__RESULT__", $resultPath.Replace("\", "\"))
$inner = $inner.Replace("__PROMPT__", $prompt.Replace('"', '`"'))
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))

Invoke-CommandInDesktopPackage `
    -PackageFamilyName $expectedPfn `
    -AppId $appId `
    -Command "powershell.exe" `
    -Args "-NoProfile -NonInteractive -EncodedCommand $encoded" `
    -PreventBreakaway `
    -ErrorAction Stop

$deadline = [DateTime]::UtcNow.AddMinutes(3)
while (-not (Test-Path -LiteralPath $resultPath)) {
    if ([DateTime]::UtcNow -ge $deadline) { throw "Timed out waiting for package-context Codex result" }
    Start-Sleep -Seconds 1
}

$result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
$result | ConvertTo-Json -Compress | Write-Output
exit [int]$result.exit_code
