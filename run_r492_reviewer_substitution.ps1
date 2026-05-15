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
    # harness — call $HarnessScript, write checkpoint
    [ValidateSet("dryrun", "stub", "harness")]
    [string]$Mode = "stub",
    # HarnessScript: which Python script to invoke in harness mode.
    #   Default: governance_harness.py (R48 cross-repo harness — CLI mismatch → NT-01)
    #   Smoke:   scripts/r492_harness_adapter.py (adapter smoke — contract shape only)
    # Boundary: swapping this does NOT change the decision lock or observation-only contract.
    [string]$HarnessScript = "scripts/r492_governance_harness.py",
    # HarnessExtraArgs: additional args passed verbatim to $HarnessScript after the standard args.
    #   Example: "--case nt05" to test NT-05 path via adapter smoke.
    [string[]]$HarnessExtraArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── guard: observation-only ───────────────────────────────────────────────────
$DECISION_LOCK = "reviewer_substitution_observation_only"
$TRACKER_PATH = "docs/status/ab-causal-r49x-consolidation-tracker-2026-05-15.json"

function Test-R492Preflight {
    Write-Host "[R49.2][preflight] validating boundary guards..."
    $errors = @()

    if (-not (Test-Path $TRACKER_PATH)) {
        $errors += "consolidation tracker missing: $TRACKER_PATH"
    } else {
        try {
            $tracker = Get-Content $TRACKER_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
            if (-not $tracker.guard.no_new_ontology_layers) {
                $errors += "guard.no_new_ontology_layers is not active"
            }
        } catch {
            $errors += "cannot parse consolidation tracker: $($_.Exception.Message)"
        }
    }

    $memoryRecord = "governance_tools/memory_record.py"
    if (-not (Test-Path $memoryRecord)) {
        $errors += "memory_record.py missing"
    } else {
        $mr = Get-Content $memoryRecord -Raw -Encoding UTF8
        if ($mr -notmatch "_has_equivalent_session_derived_entry") {
            $errors += "memory dedupe function not detected in memory_record.py"
        }
    }

    $sessionEnd = "runtime_hooks/core/session_end.py"
    if (-not (Test-Path $sessionEnd)) {
        $errors += "session_end.py missing"
    } else {
        $se = Get-Content $sessionEnd -Raw -Encoding UTF8
        if ($se -notmatch "FAIL_CLOSED_CLOSEOUT_") {
            $errors += "fail-closed closeout memory label not detected in session_end.py"
        }
    }

    if ($errors.Count -gt 0) {
        Write-Error "[R49.2][preflight] failed: $($errors -join '; ')"
        exit 1
    }
    Write-Host "[R49.2][preflight] pass"
}

Write-Host "[R49.2] Mode: observation-only ($Mode) | Decision locked to: $DECISION_LOCK"
Write-Host "[R49.2] No rules will be added. No gates will be triggered."
if ($HarnessScript -eq "scripts/r492_harness_adapter.py") {
    Write-Host "[R49.2] ADAPTER SMOKE: HarnessScript=$HarnessScript — contract shape only, not evidence collection"
} elseif ($HarnessScript -ne "governance_harness.py") {
    Write-Host "[R49.2] HARNESS OVERRIDE: HarnessScript=$HarnessScript (interpretation A — deterministic reviewer profile substitution)"
}
if ($HarnessExtraArgs.Count -gt 0) {
    Write-Host "[R49.2] HarnessExtraArgs: $($HarnessExtraArgs -join ' ')"
}
Test-R492Preflight

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
        event_log_absent                 = $null   # not applicable: no harness ran
        event_log_absent_null_type       = $null
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
        $Script:HarnessScript,
        "--scenario", $ScenarioId,
        "--seed", $Seed,
        "--reviewer", $SubstitutedOwner,
        "--observe-only"
    ) + $Script:HarnessExtraArgs
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
                event_log_absent                 = $null   # NT-01: harness never ran
                event_log_absent_null_type       = $null
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
            # MIP-04: event log provenance — must be checked before using reviewer_override_frequency
            event_log_absent                 = if ($parsed.PSObject.Properties["event_log_absent"]) { $parsed.event_log_absent } else { $null }
            event_log_absent_null_type       = if ($parsed.PSObject.Properties["event_log_absent_null_type"]) { $parsed.event_log_absent_null_type } else { $null }
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
            event_log_absent                 = $null   # NT-01: exception, harness never ran
            event_log_absent_null_type       = $null
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
        # MIP-02 boundary: drift is observation, not admissible causal finding.
        return "substitution_drift_observed"
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

function Get-AdmissibilityTier {
    param([string]$Interpretation)
    switch ($Interpretation) {
        "substitution_drift_observed" { return "admissible_observation" }
        "runtime_consistency_broken" { return "admissible_observation" }
        "substitutable_higher_cost" { return "admissible_observation" }
        "silo_risk_flagged" { return "admissible_observation" }
        "stable_candidate" { return "admissible_observation" }
        "not_measured" { return "null_typed_observation" }
        "premature" { return "null_typed_observation" }
        "not_applicable" { return "null_typed_observation" }
        "undecidable" { return "null_typed_observation" }
        "unattributable" { return "null_typed_observation" }
        "untrusted_evaluator" { return "null_typed_observation" }
        default { return "unknown_observation" }
    }
}

function Get-CausalFindingLevel {
    param([string]$Interpretation)
    return "observation_only"
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
                        event_log_absent                 = $null   # dryrun: harness not called
                        event_log_absent_null_type       = $null
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
            if ($interp -in @("substitution_drift_observed", "runtime_consistency_broken")) { $driftDetected = $true }
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
                admissibility_tier              = Get-AdmissibilityTier -Interpretation $interp
                causal_finding_level            = Get-CausalFindingLevel -Interpretation $interp
                non_gating                       = $true
                observation_only                 = $true
                # MIP-04 provenance — present only for harness runs; null for stub/dryrun
                event_log_absent                 = $run.event_log_absent
                event_log_absent_null_type       = $run.event_log_absent_null_type
            }

            $mip04Note = if ($run.event_log_absent -eq $true) { " event_log_absent:true(NT-06)" } else { "" }
            Write-Host "[R49.2]   result: $interp  null_type: $($run.null_type)  source: $($run.measurement_source)  confidence: $($run.evaluator_confidence)$mip04Note"
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
        preflight = @{
            memory_dedupe_active = $true
            closeout_fail_closed_memory_label_active = $true
            no_new_ontology_layers = $true
        }
    }
    interpretation_boundary = @{
        rule = "measurement_to_classification_must_not_skip_attribution_validation"
        admissible_observation = "substitution_drift_observed"
        disallowed_premature_finding = "tacit_dependency_detected"
        finding_ladder = @(
            "substitution_drift_observed",
            "tacit_dependency_plausible",
            "tacit_dependency_supported",
            "tacit_dependency_established"
        )
        requires = @{
            tacit_dependency_plausible = @("R49.x-1")
            tacit_dependency_supported = @("R49.x-1", "R49.x-3", "replay_consistency", "attribution_sufficiency")
            tacit_dependency_established = @("future-level claim boundary")
        }
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

