param(
    [ValidateSet("required", "recommended", "all")]
    [string]$Tier = "required",
    [string]$ProjectRoot = ".",
    [string]$Snapshot = "",
    [switch]$Brief
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
    $repoName = Split-Path -Leaf $repo
    $reportPattern = "onboard_latest_governance_${repoName}_*.json"
    $beforeReports = @(Get-ChildItem -Path (Join-Path $resolvedRoot "artifacts/session") -Filter $reportPattern -ErrorAction SilentlyContinue)

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $onboardScript,
        "-Repo", $repo,
        "-Mode", "apply",
        "-ProjectRoot", $resolvedRoot,
        "-WriteReport"
    )
    if ($Brief) {
        $args += "-Brief"
    }
    if (-not [string]::IsNullOrWhiteSpace($Snapshot)) {
        $args += @("-Snapshot", $Snapshot)
    }

    $out = & powershell @args 2>&1
    $txt = ($out | Out-String)
    $report = ([regex]::Match($txt, "report_path=(.+)")).Groups[1].Value.Trim()
    if ([string]::IsNullOrWhiteSpace($report)) {
        $afterReports = @(Get-ChildItem -Path (Join-Path $resolvedRoot "artifacts/session") -Filter $reportPattern -ErrorAction SilentlyContinue)
        if ($afterReports.Count -gt 0) {
            if ($beforeReports.Count -eq 0) {
                $report = ($afterReports | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
            } else {
                $beforeSet = @{}
                foreach ($b in $beforeReports) { $beforeSet[$b.FullName] = $true }
                $newOnes = @($afterReports | Where-Object { -not $beforeSet.ContainsKey($_.FullName) })
                if ($newOnes.Count -gt 0) {
                    $report = ($newOnes | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
                } else {
                    $report = ($afterReports | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
                }
            }
        }
    }

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
        final_report_requirement_status = "not_available"
        final_report_required_marker = "[human_readable_adoption_summary]"
        human_readable_adoption_summary = "not_relayed_in_aggregate"
        aggregate_final_report_boundary = "aggregate_only; inspect report_path for final-report table rows"
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
            if ($null -ne $j.final_report_requirement) {
                $row.final_report_requirement_status = [string]$j.final_report_requirement.status
                $row.final_report_required_marker = [string]$j.final_report_requirement.required_marker
            }
        } catch {
            $row.classification_after = "report_parse_error"
            $row.aggregate_final_report_boundary = "aggregate_only; report_path could not be parsed for final-report fields"
        }
    } else {
        $row.classification_after = "report_missing"
        $row.aggregate_final_report_boundary = "aggregate_only; report_path missing so final-report fields are not available"
    }
    $rows += [pscustomobject]$row
}

$rows | ConvertTo-Json -Depth 5
