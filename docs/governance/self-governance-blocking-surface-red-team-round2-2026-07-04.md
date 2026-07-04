# Self-Governance Blocking Surface Red-Team Round 2

Status: FINDINGS + NARROW HARDENING
Date: 2026-07-04
Scope: adversarial probe of the B0 selective blocking surface introduced by
RFC rollout steps 3-4 (policy file, workflow / CI wiring, override path)

## DONE

DONE = the new blocking surface was probed with hostile-writer scenarios; the
confirmed silent-kill and claim-inflation paths are fixed with fixtures; the
accepted residual boundaries are registered with honest dispositions.

## Method

Each probe was executed against the real modules (not reasoned about) in a
temporary repo before any fix was written. Probes that confirmed a gap became
fixtures; fixes were only applied where the gap contradicted an already-stated
contract (RFC: "a disabled gate can never masquerade as a passing gate").

## Findings

### F1 (FIXED): corrupting the policy file was a silent kill switch

Probe: a PR that corrupts `governance/memory_blocking_policy.json` and adds a
B0 entry in the same diff passed CI `clean=True`; the broken policy produced
only a warning line.

Fix: a policy file that exists but cannot be loaded is now a blocker
(`blocking_policy_error`) at both gate consumers — workflow and CI. Broken
infrastructure fails the gate instead of degrading it.

Fixtures: `test_step4_workflow_broken_policy_is_itself_a_blocker`,
`test_step4_ci_corrupted_policy_in_diff_fails_the_gate`.

### F2 (FIXED, visibility only): disabling the gate left no trace in CI output

Probe: a PR that sets `enabled: false` (or deletes the file) and adds a B0
entry in the same diff passed CI with no indication the gate was being turned
off.

Fix: CI emits `blocking_policy_changed_in_current_diff` whenever the policy
path appears in the current diff. The change itself stays allowed — turning
the gate off via a valid, versioned edit is a legitimate governance action
owned by diff review — but it is now loud, never ambient.

Residual: this is visibility, not prevention. A reviewer who ignores the
warning still approves the disable. Prevention would require protected-path
enforcement, which is out of scope for this slice.

Fixtures: `test_step4_ci_policy_change_in_diff_is_loud`,
`test_step4_ci_policy_deletion_in_diff_is_loud`,
`test_step4_ci_no_policy_announcement_without_policy_in_diff`.

### F3 (FIXED): unknown blocking codes inflated the claim ceiling

Probe: a policy with a typo'd code (`session_like_non_session_memorytype`)
loaded without error; the guard reported
`claim_ceiling: selective_blocking_phase2` while blocking nothing.

Fix: the loader validates codes against `_BLOCKABLE_VIOLATION_CODES`; unknown
codes disable blocking and surface
`blocking_policy_unknown_code:<codes>`, which is now a blocker via F1.
`authority_override_used` is deliberately not blockable — it is an audit
record.

Residual: calling `run_guard(blocking_codes=...)` directly with an unknown
code still produces the inflated ceiling; the loader is the policy entrance
and the only supported path for gate consumers.

Fixture: `test_policy_loader_unknown_code_disables_but_surfaces_error`.

### F4 (ACCEPTED, documented): authority_override is self-service

Probe: adding `authority_override: myself lol` to a blocked entry downgrades
the block to a warning. No reviewer identity verification exists.

Disposition: accepted by RFC design. The override is an honor-system escape
hatch whose deterrent is the audit trail: the original violation stays
visible, `authority_override_used` is emitted, and the override text is
grep-able in the memory file. This matches the framework trust model (audit
boundary, not security boundary). Candidate future hardening: an
`override_allowed` policy field, or CI surfacing `authority_override_used`
occurring in the current diff.

### F5 (DOCUMENTED semantics): B0 blocking at CI is a repo-state gate

The B0 blocker comes from a full scan of active-window daily memory, not from
the current diff (unlike `active_non_canonical_writer`, which is
diff-scoped at CI). Consequence: if one B0 entry lands (e.g. pushed with
`--no-verify` past the advisory hook), every subsequent CI run fails until
the entry is fixed or overridden — including unrelated PRs.

Disposition: intended for the observation period. A repo-state gate is what
forces landed debt to be dealt with instead of accumulating. If observation
shows this punishes unrelated contributors too often, a diff-scoped variant
needs its own policy decision; do not silently narrow the gate.

### F6 (CARRIED FORWARD): non-daily memory filenames evade the daily scans

Session-shaped content parked in e.g. `memory/notes.md` is outside the daily
scan (`YYYY-MM-DD.md` only) and outside B0 entirely. The workflow still flags
`memory/**` diffs as governed memory tasks, but no guard check classifies the
content. This is a scope boundary of the daily-file contract, not a
regression; it needs its own slice if it is to be closed.

## Cannot Claim

- the blocking surface is now bypass-proof (F2 prevention, F4, F5 narrowing,
  F6 all remain open boundaries);
- override misuse is prevented (it is only audited);
- policy tampering is prevented (corruption blocks; valid disable is loud but
  allowed);
- direct `run_guard` API misuse is validated;
- red-team coverage of this surface is exhaustive.

## Evidence

- probes executed 2026-07-04 against `2eb9a42` before fixes
- fixtures: `tests/test_self_governance_memory_blocking_policy_b0_fixtures.py`
  (36 passing, including 6 new round-2 fixtures)
- scoped regression: guard / workflow / CI consumer suites green
