# Self-Governance Catalog Consistency Audit

Status: AUDIT REPORT / DOCS ONLY
Date: 2026-07-05
Scope: every claim row in `docs/e1-mutation-catalog.md` verified against
current code state at `6286d77`

## DONE

DONE = each catalog row's claimed surface, violation code, and status was
checked against the current source; confirmed drift was corrected in the
catalog; one missing enforcement registration (E1-D policy gap) was added.
No runtime, guard, hook, CI, policy, or test behavior changed.

## Method

- every Expected Violation Code grepped against its claimed surface module;
- footnote line references opened and compared;
- lane-specific claims (normalizer, claim-label, authority precedence)
  verified against current function/caller state;
- runner report artifacts checked for existence;
- self-governance baseline rows compared against the detector behavior that
  landed 2026-07-04 .. 2026-07-05.

Mutation runner scenarios (section 1 PROTECTED/VULNERABLE statuses) were NOT
re-executed; their status is dated evidence (2026-06-27) and this audit only
verified that the referenced surfaces and codes still exist.

## Verified Accurate (no change)

- Section 2 hostile-input rows: all six violation codes still emitted by the
  claimed surfaces (`escalation_authority_writer`,
  `state_reconciliation_validator`, `assess_authority_directory` path).
- Footnote ² line references (escalation_authority_writer ~588-593,
  validate_prewrite_payload ~240): still approximately correct.
- Normalizer alias-miss rows: `detect_unmapped_gate_keys` and the
  `metadata.unmapped_gate_relevant_keys` surfacing exist as described;
  token-scoped limit still VULNERABLE.
- Claim-label rows: `claim_label_understates_claim_text` emitted as
  described; markerless strong claim still VULNERABLE (R2 design registered,
  unimplemented).
- Authority precedence row: `resolve_conflict` still has no non-test runtime
  caller; VULNERABLE baseline claim remains true.
- Evidence rows (Unverified Test Evidence, Fabricated Evidence Artifact
  Content): current as of the R3 Option C update.
- Phase 2 runner reports (2026-05-12, 2026-06-27) exist at the cited paths.

## Confirmed Drift (fixed in this audit)

1. **Confirmation Bypass row**: "line 80–81 check" was stale — lines 80-81 now
   hold `resolved_confirmed_auto_write_forbidden` /
   `author_provisional_cannot_confirm_resolution`; the reviewer-confirmation
   code is emitted at lines 40/87. Row updated with dated line references.
2. **Canonical Writer Bypass row**: "override-downgraded entries remain
   report-only" predated `override_mode`. Override handling is now
   mode-dependent (`allowed` downgrades; `receipt_required`/`disallowed`
   reject and the block stands) and the diff-context pre-window scan was
   missing from the row. Row updated.
3. **Report-Only Ok Semantics row**: "`ok=True` remains non-blocking" is now
   only true in the default report-only mode; with a blocking policy the
   guard can return `ok=False` / `block` / `selective_blocking_phase2`. Row
   qualified as policy-dependent.

## Missing Registration (added)

`blocking_policy_error` — corrupt/unloadable policy files (bad JSON, schema
mismatch, invalid or unknown codes, unknown `override_mode`) fail the gate at
both workflow and CI. This is enforced behavior that had fixtures and design
docs but no catalog row, violating section 4's "No mutation contract = No
enforcement claim". A new "Blocking-Policy Tamper Baselines (2026-07-05)"
subsection registers it, together with the deliberately report-only
valid-disable/deletion visibility row (blocking the disable path would
deadlock gate recovery; see the F2 attestation design).

## Not Audited / Carried Forward

- Section 1 PROTECTED/VULNERABLE statuses were not re-proven by running
  `mutation_proof_runner_phase2`; they remain dated evidence (2026-06-27).
  A rerun is the natural refresh when any of the four surfaces changes.
- The advisory report-only codes added by F4/F6/R3 (rejected, non-daily,
  metadata family) are not separately registered as rows because they carry
  no enforcement claim; they are documented in their design docs and the
  evidence scenario row.
- The P1-F mutation contract memo current-state question raised in
  memory/2026-07-05.md (concurrent session) overlaps this audit's scope but
  was not adjudicated here.

## Cannot Claim

- section 1 mutation statuses re-proven;
- catalog completeness against every advisory code in the codebase;
- any change in enforcement or protection level from this audit;
- red-team residuals closed.
