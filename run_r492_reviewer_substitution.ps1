# R49.2 Reviewer Substitution Experiment Runner
# Mode: observation-only — no rules added, no gates triggered
# As-of: 2026-05-15

[CmdletBinding()]
param(
    [string]$DatasetPath    = "docs/status/ab-causal-r492-reviewer-substitution-dataset-2026-05-15.json",
    [string]$CheckpointPath = "docs/status/ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json",
    [string]$OutputDir      = "docs/status",
    # dryrun  — skip all measurement, write nothing
    # stub    — use stub metrics (null/pending), write checkpoint (default)
    # harness — call governance_harness.py, write checkpoint
    [ValidateSet("dryrun", "stub", "harness")]
    [string]$Mode = "stub"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── guard: observation-only ───────────────────────────────────────────────────
$DECISION_LOCK = "reviewer_substitution_observation_only"

Write-Host "[R49.2] Mode: observation-only ($Mode) | Decision locked to: $DECISION_LOCK"
Write-Host "[R49.2] No rules will be added. No gates will be triggered."

# ── load dataset ─────────────────────────────────────────────────────────────
if (-not (Test-Path $DatasetPath)) {
    Write-Error "[R49.2] Dataset not found: $DatasetPath"
    exit 1
}
$dataset = Get-Content $DatasetPath -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host "[R49.2] Loaded dataset: $($dataset.experiment_id)"
Write-Host "[R49.2] Scenarios: $($dataset.scenarios.Count) | Substitution pairs: $($dataset.substitution_matrix.Count)"

# ── invariant: expected_run_count == actual_checkpoint_run_count ──────────────
# Formula: 3 scenarios × 2 substitute_directions × 3 seeds = 18
# Substitution pairs are scenario-scoped (from == scenario.original_owner).
# Cross-product (6 pairs × 3 scenarios × 3 seeds = 54) is explicitly out of scope.
$EXPECTED_RUN_COUNT = $dataset.run_count_invariant.expected_run_count
$computedCount = 0
foreach ($scenario in $dataset.scenarios) {
    $matchingPairs = $dataset.substitution_matrix | Where-Object { $_.from -eq $scenario.original_owner }
    $computedCount += $matchingPairs.Count * $scenario.seeds.Count
}
if ($computedCount -ne $EXPECTED_RUN_COUNT) {
    Write-Error "[R49.2] INVARIANT VIOLATED: expected_run_count=$EXPECTED_RUN_COUNT but computed=$computedCount. Aborting."
    exit 1
}
Write-Host "[R49.2] Invariant OK: expected_run_count=$EXPECTED_RUN_COUNT == computed=$computedCount"

# ── metric collection ────────────────────────────────────────────────────────
# Stub is always kept — harness mode calls through it and replaces output.
# This ensures stub fallback is available if harness fails, and keeps
# measurement_source traceable per run (prevents misattributing harness
# integration errors as reviewer substitution fragility).
function Invoke-StubRun {
    # NT-06 temporal null: measurement window not yet open (harness not wired).
    # drift_result = "not_measured" — NOT "pending" (which conflates NT-01/NT-06).
    return @{
        metrics = @{
            claim_discipline_drift      = $null
            unsupported_count           = $null
            replay_deterministic        = $null
            reviewer_override_frequency = $null
            intervention_entropy        = $null
            drift_result                = "not_measured"
        }
        measurement_source               = "stub"
        harness_exit_code                = $null
        harness_error                    = $null
        evaluator_confidence             = "unknown"
        evaluator_confidence_provenance  = $null
        null_type                        = "NT-06"
        null_status                      = "not_measured"
    }
}

function Invoke-HarnessRun {
    param(
        [string]$ScenarioId,
        [int]$Seed,
        [string]$SubstitutedOwner
    )
    # Calls: python governance_harness.py --scenario <id> --seed <seed> --reviewer <owner> --observe-only
    $harnessArgs = @(
        "governance_harness.py",
        "--scenario", $ScenarioId,
        "--seed", $Seed,
        "--reviewer", $SubstitutedOwner,
        "--observe-only"
    )
    try {
        $raw = & python @harnessArgs 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            # NT-01 technical null: harness failed before producing values.
            # Do NOT read as governance fragility (R49.x-5 audit requirement).
            $stubMetrics = (Invoke-StubRun).metrics
            $stubMetrics.drift_result = "not_measured"   # NT-01, not NT-06
            return @{
                metrics                          = $stubMetrics
                measurement_source               = "harness_error_fallback"
                harness_exit_code                = $exitCode
                harness_error                    = ($raw -join "`n")
                evaluator_confidence             = "unknown"
                evaluator_confidence_provenance  = $null
                null_type                        = "NT-01"
                null_status                      = "not_measured"
            }
        }
        $parsed = $raw | ConvertFrom-Json
        # NT-05 recursive null guard: if harness does not self-report evaluator_confidence,
        # the default "medium" has no provenance — mark it as NT-05 so downstream cannot
        # treat it as a real confidence signal (R49.x-5 audit requirement F5).
        $hasOwnConfidence = $parsed.PSObject.Properties["evaluator_confidence"]
        $harnessConfidence    = if ($hasOwnConfidence) { $parsed.evaluator_confidence } else { "medium" }
        $confidenceProvenance = if ($hasOwnConfidence) { "harness_self_reported" } else { "harness_default_NT-05" }
        return @{
            metrics = @{
                claim_discipline_drift      = $parsed.claim_discipline_drift
                unsupported_count           = $parsed.unsupported_count
                replay_deterministic        = $parsed.replay_deterministic
                reviewer_override_frequency = $parsed.reviewer_override_frequency
                intervention_entropy        = $parsed.intervention_entropy
                drift_result                = $parsed.drift_result
            }
            measurement_source               = "harness"
            harness_exit_code                = $exitCode
            harness_error                    = $null
            evaluator_confidence             = $harnessConfidence
            evaluator_confidence_provenance  = $confidenceProvenance
            null_type                        = $null    # harness ran — no run-level null
            null_status                      = $null    # individual metric nulls classified separately
        }
    } catch {
        $stubMetrics = (Invoke-StubRun).metrics
        $stubMetrics.drift_result = "not_measured"
        return @{
            metrics                          = $stubMetrics
            measurement_source               = "harness_error_fallback"
            harness_exit_code                = -1
            harness_error                    = $_.Exception.Message
            evaluator_confidence             = "unknown"
            evaluator_confidence_provenance  = $null
            null_type                        = "NT-01"
            null_status                      = "not_measured"
        }
    }
}

# ── interpret a single run ────────────────────────────────────────────────────
# Takes the full $run hashtable (not just metrics) so it can check null_type.
# Returns null_status when the run has a run-level null (NT-01..NT-06).
# Returns semantic interpretations only when harness produced real values.
#
# Null status vocabulary (R49.x-5 audit requirement F3):
#   not_measured      — NT-06 stub, or NT-01 harness failure
#   premature         — NT-06 dryrun, precondition not met
#   not_applicable    — NT-02 structural (metric not valid for this topology)
#   undecidable       — NT-03 semantic (measured, but meaning ambiguous)
#   unattributable    — NT-04 causal (signal exists, cause ambiguous)
#   untrusted_evaluator — NT-05 recursive (evaluator has no provenance)
function Get-SubstitutionInterpretation {
    param([hashtable]$Run)

    # Run-level null: return the typed null_status directly (F3 fix).
    if ($null -ne $Run.null_type) { return $Run.null_status }

    $Metrics = $Run.metrics

    # Harness ran but primary metric is null — NT-02 structural or NT-03 semantic.
    # Cannot determine cause here; caller should investigate topology before attributing.
    if ($null -eq $Metrics.claim_discipline_drift) { return "undecidable" }

    # NT-05 guard: if evaluator_confidence has no real provenance, all findings are untrusted.
    if ($Run.evaluator_confidence_provenance -eq "harness_default_NT-05") {
        return "untrusted_evaluator"
    }

    if ($Metrics.claim_discipline_drift -gt 0 -or $Metrics.unsupported_count -gt 0) {
        return "tacit_dependency_detected"
    }
    if ($Metrics.replay_deterministic -eq $false) {
        return "runtime_consistency_broken"
    }
    if ($Metrics.reviewer_override_frequency -gt 0 -and $Metrics.claim_discipline_drift -eq 0) {
        return "substitutable_higher_cost"
    }
    if ($null -ne $Metrics.intervention_entropy -and $Metrics.intervention_entropy -lt 0.2) {
        return "silo_risk_flagged"
    }
    return "stable_candidate"
}

# ── main run loop ─────────────────────────────────────────────────────────────
$results = @()
$completed = 0
$driftDetected = $false
$siloFlagged = $false
$substitutionCandidates = 0

foreach ($scenario in $dataset.scenarios) {
    foreach ($pair in $dataset.substitution_matrix | Where-Object { $_.from -eq $scenario.original_owner }) {
        foreach ($seed in $scenario.seeds) {

            $runId = "r492-$($pair.from)-to-$($pair.to)-s$seed"
            Write-Host "[R49.2] Running: $runId  scenario=$($scenario.scenario_id)  mode=$Mode"

            switch ($Mode) {
                "dryrun" {
                    Write-Host "[R49.2]   dryrun — skipping all measurement"
                    # NT-06 temporal null, premature variant: run loop verified but harness not called.
                    $run = @{
                        metrics = @{
                            claim_discipline_drift      = $null
                            unsupported_count           = $null
                            replay_deterministic        = $null
                            reviewer_override_frequency = $null
                            intervention_entropy        = $null
                            drift_result                = "premature"
                        }
                        measurement_source               = "dryrun"
                        harness_exit_code                = $null
                        harness_error                    = $null
                        evaluator_confidence             = "unknown"
                        evaluator_confidence_provenance  = $null
                        null_type                        = "NT-06"
                        null_status                      = "premature"
                    }
                }
                "stub" {
                    $run = Invoke-StubRun
                }
                "harness" {
                    $run = Invoke-HarnessRun `
                        -ScenarioId $scenario.scenario_id `
                        -Seed $seed `
                        -SubstitutedOwner $pair.to
                }
            }

            # F3 fix: pass full $run, not just metrics, so null_type is accessible.
            $interp = Get-SubstitutionInterpretation -Run $run

            # F4 fix: exclusion list uses typed null_status vocabulary, not ambiguous "pending".
            $NULL_STATUSES = @("not_measured", "premature", "not_applicable", "undecidable", "unattributable", "untrusted_evaluator")
            if ($interp -notin $NULL_STATUSES) { $completed++ }
            if ($interp -in @("tacit_dependency_detected", "runtime_consistency_broken")) { $driftDetected = $true }
            if ($interp -eq "silo_risk_flagged") { $siloFlagged = $true }
            if ($interp -in @("stable_candidate", "substitutable_higher_cost")) { $substitutionCandidates++ }

            $results += [PSCustomObject]@{
                run_id                           = $runId
                scenario_id                      = $scenario.scenario_id
                seed                             = $seed
                original_owner                   = $pair.from
                substituted_owner                = $pair.to
                metrics                          = $run.metrics
                measurement_source               = $run.measurement_source
                harness_exit_code                = $run.harness_exit_code
                harness_error                    = $run.harness_error
                evaluator_confidence             = $run.evaluator_confidence
                evaluator_confidence_provenance  = $run.evaluator_confidence_provenance
                null_type                        = $run.null_type
                null_status                      = $run.null_status
                interpretation                   = $interp
                non_gating                       = $true
                observation_only                 = $true
            }

            Write-Host "[R49.2]   result: $interp  null_type: $($run.null_type)  source: $($run.measurement_source)  confidence: $($run.evaluator_confidence)"
        }
    }
}

# ── write checkpoint ──────────────────────────────────────────────────────────
$checkpoint = @{
    checkpoint_id   = "ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15"
    as_of           = "2026-05-15"
    experiment_id   = $dataset.experiment_id
    phase           = "observation_only"
    decision        = $DECISION_LOCK
    runs            = $results
    aggregate       = @{
        total_runs                  = $results.Count
        completed                   = $completed
        pending                     = ($results.Count - $completed)
        drift_detected              = $driftDetected
        silo_risk_flagged           = $siloFlagged
        substitution_candidate_count = $substitutionCandidates
    }
    guard           = @{
        no_rule_added       = $true
        no_gate_added       = $true
        decision_locked_to  = $DECISION_LOCK
    }
}

$checkpointJson = $checkpoint | ConvertTo-Json -Depth 10

if ($Mode -ne "dryrun") {
    $checkpointJson | Set-Content -Path $CheckpointPath -Encoding UTF8
    Write-Host "[R49.2] Checkpoint written: $CheckpointPath"
} else {
    Write-Host "[R49.2] dryrun — checkpoint not written."
}

# ── summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== R49.2 Summary ==="
Write-Host "  Total runs            : $($results.Count)"
Write-Host "  Completed             : $completed"
Write-Host "  Drift detected        : $driftDetected"
Write-Host "  Silo risk flagged     : $siloFlagged"
Write-Host "  Substitution candidates: $substitutionCandidates"
Write-Host "  Decision              : $DECISION_LOCK"
Write-Host ""
Write-Host "  Boundary: R49.2 evaluates reviewer substitutability as an observation-only"
Write-Host "  fragility signal. It does not prove reviewer independence or governance scalability."
Write-Host ""
Write-Host "[R49.2] Done."
