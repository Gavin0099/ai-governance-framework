# Framework Self Test-Signal Audit (2026-07-06)

As-of: 2026-07-06
Scope: read-only dogfood run of `governance_tools/test_signal_quality_audit.py`
(v0.2, report-only) against the framework's own contract surfaces, answering
"which of our validators are formality-only?". No validator, fixture,
contract, or tool is changed by this note.

## Run Matrix

| target | overall | validator fixture pairing | runner |
|---|---|---|---|
| examples/usb-hub-contract | partial | 1/1 paired (pos+neg) | not_found |
| examples/cpp-userspace-contract | partial | 3/3 paired | present |
| examples/csharp-arch-contract | partial | 1/1 paired | present |
| examples/nextjs-byok-contract | partial | 2/2 paired | present |
| examples/multi-validator-contract | weak | 0/4 paired (no fixture harness) | not_found |
| examples/decision-boundary | weak | falls back to root contract | not_found |
| examples/starter-pack | weak | falls back to root contract | not_found |
| framework root | weak | root validator 0/1 paired | scripts present |

chaos-demo, todo-app-demo, runtime-profiles have no contract.yaml and were
not auditable targets.

## Findings

1. Formality-check question has a two-layer answer.
   - Module layer: NOT formality. All four validators declared by
     multi-validator-contract (architecture_drift, driver_evidence,
     failure_completeness, refactor_evidence) have dedicated pytest suites in
     tests/. The validator implementations are exercised.
   - Contract-template layer: FORMALITY RISK. The example contracts that
     declare them provide zero pass/fail fixture pairs, so a consumer
     onboarding from `multi-validator-contract` or `starter-pack` copies a
     template in which validators are wired without any fixture harness.
     The template teaches the anti-pattern the audit exists to catch.
2. The framework's own root `contract.yaml` declares
   `architecture_drift_checker` with no fixture pair
   (validator_without_fixture_harness), while consumer-facing guidance
   (F-7 managed block, a5ae276e) tells consumers validators should have
   pass/fail fixture expectations. Self-hosting gap.
3. `decision-boundary` and `starter-pack` silently resolve to the framework
   root contract.yaml when audited as repos. Correct fallback behavior, but
   it means their weak status is the root contract's weakness, not their own.
4. Framework-root lexical warnings (production_derived_expected_value,
   mock_only_weak_signal, time_or_random_uncontrolled) are partially
   self-contamination from the audit tool's own test fixtures, consistent
   with the seed ledger's `noisy` classification of lexical signals. They are
   reviewer aids here, not findings.

## Recommended Follow-Up (one action, not implemented here)

Add pass/fail fixture pairs to `examples/multi-validator-contract` and a
fixture pair for the root `architecture_drift_checker` declaration in a
single narrow template-hardening slice, so onboarding examples demonstrate
the fixture discipline the framework asks consumers to follow. The four
validator modules themselves need no rescue.

## Claim Boundary

- Report-only audit; presence of fixtures or runners does not prove
  execution, semantic correctness, or industry-grade testing.
- This note does not authorize the follow-up slice; it records the evidence
  and one recommendation.
