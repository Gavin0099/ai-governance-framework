param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,
    [ValidateSet("plan", "apply")]
    [string]$Mode = "plan",
    [string]$ProjectRoot = ".",
    [string]$Snapshot = "",
    [string]$RefreshSnapshotCommand = "",
    [switch]$WriteReport
)

$args = @(
    "-m", "governance_tools.onboard_latest_governance",
    "--repo", $Repo,
    "--mode", $Mode,
    "--project-root", $ProjectRoot,
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

python @args
exit $LASTEXITCODE
