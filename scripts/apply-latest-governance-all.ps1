param(
    [ValidateSet("required", "recommended", "all")]
    [string]$Tier = "required",
    [string]$ProjectRoot = ".",
    [string]$Snapshot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$scopePath = Join-Path $resolvedRoot "governance/fleet/governance_scope.yaml"
if (-not (Test-Path $scopePath)) {
    throw "governance scope file not found: $scopePath"
}

$scopeRaw = Get-Content -Path $scopePath -Raw -Encoding UTF8

function Get-TierRepos {
    param(
        [string]$Raw,
        [string]$TierName
    )
    $m = [regex]::Match($Raw, "(?s)${TierName}:\s*\n.*?repos:(.*?)(?=\n  \w+:|$)")
    if (-not $m.Success) { return @() }
    $repos = @()
    foreach ($pm in [regex]::Matches($m.Groups[1].Value, '- path:\s*(.+)')) {
        $repos += $pm.Groups[1].Value.Trim()
    }
    return $repos
}

$requiredRepos = Get-TierRepos -Raw $scopeRaw -TierName "required"
$recommendedRepos = Get-TierRepos -Raw $scopeRaw -TierName "recommended"

$targets = switch ($Tier) {
    "required" { $requiredRepos }
    "recommended" { $recommendedRepos }
    "all" { @($requiredRepos + $recommendedRepos | Select-Object -Unique) }
}

if ($targets.Count -eq 0) {
    throw "No repos found for tier: $Tier"
}

$onboardScript = Join-Path $resolvedRoot "scripts/onboard-latest-governance.ps1"
if (-not (Test-Path $onboardScript)) {
    throw "onboard script not found: $onboardScript"
}

$rows = @()
foreach ($repo in $targets) {
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $onboardScript,
        "-Repo", $repo,
        "-Mode", "apply",
        "-ProjectRoot", $resolvedRoot,
        "-WriteReport"
    )
    if (-not [string]::IsNullOrWhiteSpace($Snapshot)) {
        $args += @("-Snapshot", $Snapshot)
    }

    $out = & powershell @args 2>&1
    $txt = ($out | Out-String)
    $report = ([regex]::Match($txt, "report_path=(.+)")).Groups[1].Value.Trim()

    $row = [ordered]@{
        repo = $repo
        hooks = $null
        fw = $null
        agents = $null
        evidence = $null
        head_ok = $null
        ts_ok = $null
        repo_native_verified = $null
        detector_errors = $null
        classification_after = ""
        report_path = $report
    }

    if (-not [string]::IsNullOrWhiteSpace($report) -and (Test-Path $report)) {
        try {
            $j = Get-Content -Path $report -Raw -Encoding UTF8 | ConvertFrom-Json
            $a = $j.acceptance_after
            $row.hooks = $a.hooks
            $row.fw = $a.fw
            $row.agents = $a.agents
            $row.evidence = $a.evidence
            $row.head_ok = $a.head_ok
            $row.ts_ok = $a.ts_ok
            $row.repo_native_verified = $a.repo_native_verified
            $row.detector_errors = $a.detector_errors
            $row.classification_after = [string]$j.classification_after
        } catch {
            $row.classification_after = "report_parse_error"
        }
    } else {
        $row.classification_after = "report_missing"
    }
    $rows += [pscustomobject]$row
}

$rows | ConvertTo-Json -Depth 5
