# R49.x-1 Evaluator Neutrality Topology Runner
# Mode: observation-only (no new rules, no gate mutation)
# As-of: 2026-05-15

[CmdletBinding()]
param(
    [string]$R492CheckpointPath = "docs/status/ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json",
    [string]$OutStatusPath = "docs/status/ab-causal-r49x1-evaluator-neutrality-topology-status-2026-05-15.md",
    [string]$OutCheckpointPath = "docs/status/ab-causal-r49x1-evaluator-neutrality-topology-checkpoint-2026-05-15.json",
    [string]$TrackerPath = "docs/status/ab-causal-r49x-consolidation-tracker-2026-05-15.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Json([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "missing file: $Path"
    }
    return Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-Json([string]$Path, $Obj) {
    $Obj | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding UTF8
}

Write-Host "[R49.x-1] loading R49.2 checkpoint..."
$r492 = Read-Json $R492CheckpointPath
$runs = @($r492.runs)
if ($runs.Count -eq 0) {
    throw "R49.2 runs empty; cannot evaluate neutrality topology."
}

$preflight = $r492.guard.preflight
$guardOk = (
    $preflight.no_new_ontology_layers -eq $true -and
    $preflight.memory_dedupe_active -eq $true -and
    $preflight.closeout_fail_closed_memory_label_active -eq $true
)

$bySource = @{}
$byNullType = @{}
$byInterp = @{}
$byScenarioOwner = @{}

foreach ($r in $runs) {
    $src = [string]$r.measurement_source
    $nt = if ($null -eq $r.null_type) { "null" } else { [string]$r.null_type }
    $ip = [string]$r.interpretation
    $key = "$($r.scenario_id)::$($r.substituted_owner)"

    if (-not $bySource.ContainsKey($src)) { $bySource[$src] = 0 }
    if (-not $byNullType.ContainsKey($nt)) { $byNullType[$nt] = 0 }
    if (-not $byInterp.ContainsKey($ip)) { $byInterp[$ip] = 0 }
    if (-not $byScenarioOwner.ContainsKey($key)) {
        $byScenarioOwner[$key] = @{
            run_count = 0
            harness_error_fallback = 0
            not_measured = 0
        }
    }
    $bySource[$src]++
    $byNullType[$nt]++
    $byInterp[$ip]++
    $byScenarioOwner[$key].run_count++
    if ($src -eq "harness_error_fallback") { $byScenarioOwner[$key].harness_error_fallback++ }
    if ($ip -eq "not_measured") { $byScenarioOwner[$key].not_measured++ }
}

$total = $runs.Count
$allHarnessFallback = ($bySource.Keys.Count -eq 1 -and $bySource.ContainsKey("harness_error_fallback"))
$allNt01 = ($byNullType.Keys.Count -eq 1 -and $byNullType.ContainsKey("NT-01"))
$allNotMeasured = ($byInterp.Keys.Count -eq 1 -and $byInterp.ContainsKey("not_measured"))

$neutralityAssessable = -not ($allHarnessFallback -and $allNt01 -and $allNotMeasured)

$topologyClass = if ($neutralityAssessable) { "mixed" } else { "global_measurement_collapse_nt01" }
$decision = if ($neutralityAssessable) { "neutrality_topology_collected" } else { "neutrality_not_assessable_observation_only" }
$causalLevel = "observation_only"

$out = [ordered]@{
    checkpoint_id = "ab-causal-r49x1-evaluator-neutrality-topology-checkpoint-2026-05-15"
    as_of = "2026-05-15"
    source_checkpoint = $R492CheckpointPath
    mode = "observation_only"
    decision = $decision
    causal_finding_level = $causalLevel
    preflight_guard_pass = $guardOk
    summary = @{
        total_runs = $total
        neutrality_assessable = $neutralityAssessable
        topology_class = $topologyClass
    }
    distributions = @{
        measurement_source = $bySource
        null_type = $byNullType
        interpretation = $byInterp
    }
    neutrality_failure_topology = @{
        scenario_owner_cells = $byScenarioOwner
        dominant_failure = if ($allHarnessFallback) { "harness_error_fallback" } else { "mixed" }
        dominant_null_type = if ($allNt01) { "NT-01" } else { "mixed" }
        note = "Topology output is observational and non-gating."
    }
    interpretation_boundary = @{
        allowed = "substitution_drift_observed as observation"
        disallowed = "tacit dependency causal escalation from measurement collapse"
    }
}

Write-Json $OutCheckpointPath $out

$lines = @()
$lines += "# AB Causal R49.x-1 Evaluator Neutrality Topology Status (2026-05-15)"
$lines += ""
$lines += "As-of: 2026-05-15"
$lines += "Mode: observation-only"
$lines += "Decision: ``$decision``"
$lines += "causal_finding_level: ``$causalLevel``"
$lines += ""
$lines += "## Boundary"
$lines += "- Objective: characterize neutrality failure topology, not optimize neutrality score."
$lines += "- `substitution_drift_observed distribution collected` does not imply tacit dependency evidence."
$lines += ""
$lines += "## Preflight"
$lines += "- guard pass: $guardOk"
$lines += "- no_new_ontology_layers: $($preflight.no_new_ontology_layers)"
$lines += "- memory_dedupe_active: $($preflight.memory_dedupe_active)"
$lines += "- closeout_fail_closed_memory_label_active: $($preflight.closeout_fail_closed_memory_label_active)"
$lines += ""
$lines += "## Result"
$lines += "- total_runs: $total"
$lines += "- neutrality_assessable: $neutralityAssessable"
$lines += "- topology_class: $topologyClass"
$lines += ""
$lines += "## Distribution"
$lines += "- measurement_source: $(($bySource.GetEnumerator() | ForEach-Object { ""$($_.Key)=$($_.Value)"" }) -join ', ')"
$lines += "- null_type: $(($byNullType.GetEnumerator() | ForEach-Object { ""$($_.Key)=$($_.Value)"" }) -join ', ')"
$lines += "- interpretation: $(($byInterp.GetEnumerator() | ForEach-Object { ""$($_.Key)=$($_.Value)"" }) -join ', ')"
$lines += ""
$lines += "## Neutrality Failure Topology"
$lines += "| scenario::substituted_owner | run_count | harness_error_fallback | not_measured |"
$lines += "|---|---:|---:|---:|"
foreach ($k in ($byScenarioOwner.Keys | Sort-Object)) {
    $v = $byScenarioOwner[$k]
    $lines += "| $k | $($v.run_count) | $($v.harness_error_fallback) | $($v.not_measured) |"
}
$lines += ""
$lines += "## Interpretation"
if ($topologyClass -eq "global_measurement_collapse_nt01") {
    $lines += "- Current evidence is an initialized surface with global NT-01 collapse."
    $lines += "- Neutrality is not assessable under measurement collapse."
    $lines += "- Next step is harness availability recovery before R49.x-3."
} else {
    $lines += "- Neutrality topology is now measurable under harness mode."
    $lines += "- This run still does not support reviewer-dependency claims (observation-only boundary)."
    $lines += "- Next step: R49.x-3 hotspot transferability with the same causal boundary lock."
}

$lines -join "`n" | Set-Content -Path $OutStatusPath -Encoding UTF8

if (Test-Path $TrackerPath) {
    $tracker = Read-Json $TrackerPath
    $task = @($tracker.tasks | Where-Object { $_.task_id -eq "r49x-1" })[0]
    if ($null -ne $task) {
        $task.status = "complete"
        $task.result = $decision
        $task.notes = "Topology collected under observation-only; neutrality not assessable in global NT-01 collapse."
    }
    Write-Json $TrackerPath $tracker
}

Write-Host "[R49.x-1] wrote:"
Write-Host "  - $OutCheckpointPath"
Write-Host "  - $OutStatusPath"
if (Test-Path $TrackerPath) { Write-Host "  - $TrackerPath (task r49x-1 updated)" }
Write-Host "[R49.x-1] done."
