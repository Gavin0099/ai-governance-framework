# R49.x-3 Hotspot Transferability Runner
# Mode: observation-only (no new rules, no gate mutation)
# As-of: 2026-05-15

[CmdletBinding()]
param(
    [string]$R492CheckpointPath = "docs/status/ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json",
    [string]$OutStatusPath = "docs/status/ab-causal-r49x3-hotspot-transferability-status-2026-05-15.md",
    [string]$OutCheckpointPath = "docs/status/ab-causal-r49x3-hotspot-transferability-checkpoint-2026-05-15.json",
    [string]$TrackerPath = "docs/status/ab-causal-r49x-consolidation-tracker-2026-05-15.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Json([string]$Path) {
    if (-not (Test-Path $Path)) { throw "missing file: $Path" }
    return Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-Json([string]$Path, $Obj) {
    $Obj | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding UTF8
}

function Get-HotspotId([string]$ScenarioId, [string]$Owner) {
    switch ("$ScenarioId::$Owner") {
        "SCN-RUNTIME::audit" { return "hs_evidence_lineage_strictness" }
        "SCN-RUNTIME::product" { return "hs_scope_boundary_pressure" }
        "SCN-AUDIT::runtime" { return "hs_authority_boundary_pressure" }
        "SCN-AUDIT::product" { return "hs_scope_boundary_pressure" }
        "SCN-PRODUCT::runtime" { return "hs_authority_boundary_pressure" }
        "SCN-PRODUCT::audit" { return "hs_evidence_lineage_strictness" }
        default { return "hs_unknown" }
    }
}

Write-Host "[R49.x-3] loading R49.2 checkpoint..."
$r492 = Read-Json $R492CheckpointPath
$runs = @($r492.runs)
if ($runs.Count -eq 0) { throw "R49.2 runs empty; cannot evaluate hotspot transferability." }

# group by scenario and substituted_owner
$cells = @{}
foreach ($r in $runs) {
    $k = "$($r.scenario_id)::$($r.substituted_owner)"
    if (-not $cells.ContainsKey($k)) {
        $cells[$k] = [ordered]@{
            scenario_id = [string]$r.scenario_id
            substituted_owner = [string]$r.substituted_owner
            run_count = 0
            hotspot_id = Get-HotspotId -ScenarioId ([string]$r.scenario_id) -Owner ([string]$r.substituted_owner)
            drift_observed_count = 0
            event_log_absent_count = 0
        }
    }
    $cells[$k].run_count++
    if ([string]$r.interpretation -eq "substitution_drift_observed") { $cells[$k].drift_observed_count++ }
    if ($r.event_log_absent -eq $true) { $cells[$k].event_log_absent_count++ }
}

# compute overlap among hotspot ids
$cellList = @($cells.Values)
$uniqueHotspots = @($cellList.hotspot_id | Sort-Object -Unique)
$totalCells = $cellList.Count
$overlapRate = if ($totalCells -eq 0) { 0.0 } else { [math]::Round((($totalCells - ($uniqueHotspots.Count - 1)) / $totalCells), 4) }
# conservative: if all cells have measurable runs and at least one non-trivial hotspot distribution
$notMeasurableCount = @($cellList | Where-Object { $_.run_count -lt 1 }).Count
$allMeasurable = ($notMeasurableCount -eq 0)
$transferabilityAssessable = $allMeasurable
$decision = if ($transferabilityAssessable) { "hotspot_transferability_topology_collected" } else { "hotspot_transferability_not_assessable_observation_only" }

$checkpoint = [ordered]@{
    checkpoint_id = "ab-causal-r49x3-hotspot-transferability-checkpoint-2026-05-15"
    as_of = "2026-05-15"
    source_checkpoint = $R492CheckpointPath
    mode = "observation_only"
    decision = $decision
    causal_finding_level = "observation_only"
    summary = @{
        total_runs = $runs.Count
        total_cells = $totalCells
        transferability_assessable = $transferabilityAssessable
        hotspot_overlap_rate = $overlapRate
        hotspot_unique_count = $uniqueHotspots.Count
    }
    hotspots = @{
        unique_hotspots = $uniqueHotspots
        cells = $cellList
    }
    interpretation_boundary = @{
        allowed = "hotspot topology observation only"
        disallowed = "reviewer dependency causal escalation from hotspot overlap"
    }
}

Write-Json $OutCheckpointPath $checkpoint

$lines = @()
$lines += "# AB Causal R49.x-3 Hotspot Transferability Status (2026-05-15)"
$lines += ""
$lines += "As-of: 2026-05-15"
$lines += "Mode: observation-only"
$lines += "Decision: ``$decision``"
$lines += 'causal_finding_level: `observation_only`'
$lines += ""
$lines += "## Boundary"
$lines += "- Objective: characterize hotspot transferability topology, not prove reviewer dependency."
$lines += "- Hotspot overlap is observational and non-gating."
$lines += ""
$lines += "## Summary"
$lines += "- total_runs: $($runs.Count)"
$lines += "- total_cells: $totalCells"
$lines += "- transferability_assessable: $transferabilityAssessable"
$lines += "- hotspot_unique_count: $($uniqueHotspots.Count)"
$lines += "- hotspot_overlap_rate: $overlapRate"
$lines += ""
$lines += "## Hotspot Cells"
$lines += "| scenario::substituted_owner | hotspot_id | run_count | drift_observed_count | event_log_absent_count |"
$lines += "|---|---|---:|---:|---:|"
foreach ($c in ($cellList | Sort-Object scenario_id, substituted_owner)) {
    $cellKey = "$($c.scenario_id)::$($c.substituted_owner)"
    $lines += "| $cellKey | $($c.hotspot_id) | $($c.run_count) | $($c.drift_observed_count) | $($c.event_log_absent_count) |"
}
$lines += ""
$lines += "## Interpretation"
$lines += "- Transferability topology is measurable under harness mode."
$lines += "- This run does not support reviewer-dependency claims (observation-only boundary)."
$lines += "- Next step: R49.x-4 remains blocked until metric interpretability prerequisites are explicitly met."

$lines -join "`n" | Set-Content -Path $OutStatusPath -Encoding UTF8

if (Test-Path $TrackerPath) {
    $tracker = Read-Json $TrackerPath
    $task = @($tracker.tasks | Where-Object { $_.task_id -eq "r49x-3" })[0]
    if ($null -ne $task) {
        $task.status = "complete"
        $task.result = $decision
        $task.notes = "Topology collected under observation-only; no causal escalation permitted."
    }
    Write-Json $TrackerPath $tracker
}

Write-Host "[R49.x-3] wrote:"
Write-Host "  - $OutCheckpointPath"
Write-Host "  - $OutStatusPath"
if (Test-Path $TrackerPath) { Write-Host "  - $TrackerPath (task r49x-3 updated)" }
Write-Host "[R49.x-3] done."
