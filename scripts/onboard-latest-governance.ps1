param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,
    [ValidateSet("plan", "apply")]
    [string]$Mode = "plan",
    [string]$ProjectRoot = ".",
    [string]$Snapshot = "",
    [string]$RefreshSnapshotCommand = "",
    [switch]$Brief,
    [switch]$WriteReport
)

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$previousPythonPath = $env:PYTHONPATH
if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
    $env:PYTHONPATH = $resolvedProjectRoot
} else {
    $env:PYTHONPATH = "$resolvedProjectRoot;$previousPythonPath"
}

$args = @(
    "-m", "governance_tools.onboard_latest_governance",
    "--repo", $Repo,
    "--mode", $Mode,
    "--project-root", $resolvedProjectRoot,
    "--format", "human"
)

if ($Snapshot -ne "") {
    $args += @("--snapshot", $Snapshot)
}

if ($RefreshSnapshotCommand -ne "") {
    $args += @("--refresh-snapshot-command", $RefreshSnapshotCommand)
}

if ($WriteReport) {
    $args += "--write-report"
}
if ($Brief) {
    $args += "--brief"
}

python @args
$exitCode = $LASTEXITCODE
$env:PYTHONPATH = $previousPythonPath
exit $exitCode
