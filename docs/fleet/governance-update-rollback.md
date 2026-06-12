# Governance Update Rollback Procedure

Status: documented procedure, **never execution-tested**.
Scope: rollback of a governance framework update (F-7 style submodule
update) in a consumer repository, after a failed update, failed
post-update smoke, or observed destructive behavior.

Evidence basis: the P1-C rollback observation (PLAN.md, P1-C items,
2026-06-12) — observed submodule pointer chain on meiandraybook
origin/main `da1d4f3 -> 0eafe10 -> 554607f -> b14c15b`, with rollback
identified as checking out the previous known-good pointer (`554607f`)
inside the submodule and committing on a clean worktree. Observation
only; this document turns that observation into a bounded procedure.

Core principle: updating governance is itself a trust-surface mutation.
A trust-surface mutation without a rollback path is asymmetric risk —
expensive, explicit, **reversible** (PLAN core principle).

> **Grade caveat**: this procedure is derived from read-only observation,
> not from an executed rollback. The first real rollback must be treated
> as its own evidence-producing slice, and this document must be
> reconciled against what actually happened.

## 1. What can be rolled back

- **The submodule pointer**: checkout of the previous known-good
  framework commit inside the consumer's submodule, committed on a clean
  consumer worktree. This is the primary rollback object.
- **Managed governance surfaces** (hooks, managed advisory files, AGENTS
  keyed sections inside the F-7 managed allowlist): regenerated from the
  rolled-back framework version via the managed apply path — not
  hand-edited back.

## 2. What must NOT be auto-rolled-back

- **Memory records** (`memory/YYYY-MM-DD.md`, structured memory): they
  are evidence. A rollback must never rewrite or delete the records that
  describe the failed update. History of the failure is part of the
  audit trail.
- **Closeout receipts and ledgers**: same evidence rule.
- **`contract.yaml` human decisions** (domain, risk tier): human
  authority, not update payload.
- **Consumer-owned code and files outside the managed allowlist**: the
  updater had no authority over them going forward; rollback has none
  going backward.
- **The framework repository itself**: rollback happens in the consumer's
  pointer, never by rewriting framework history (no force-push as
  rollback).

## 3. Pre-rollback evidence capture (before any mutation)

Record, in a session-derived memory record on the consumer side or the
operating environment:

1. Current (bad) pointer commit and the target known-good pointer commit.
2. The failure evidence triggering rollback: failed smoke output, drift
   checker errors, or the observed destructive behavior — verbatim, not
   summarized.
3. Consumer worktree dirty status (`git status --short`).
4. Declared rollback intent and scope (which of the items in section 1
   will be touched).

## 4. Rollback execution order

1. **Stop** further governance-claiming work in the consumer repo.
2. Capture pre-rollback evidence (section 3).
3. **Clean-worktree gate**: if the consumer worktree is dirty in paths
   overlapping the rollback, stop at diagnosis and report. Rollback on a
   dirty overlapping worktree is remediation, not rollback.
4. Checkout the known-good framework commit inside the submodule.
5. Re-run the managed apply / hook install from the rolled-back framework
   version, so managed surfaces match the pointer (no mixed-version
   state).
6. Commit the pointer rollback and regenerated managed surfaces as one
   scoped commit, with a memory record binding it.
7. Run post-rollback verification (section 5) before any claim.

## 5. Post-rollback verification

- Runtime smoke / hook validator passes at the rolled-back version.
- Submodule pointer equals the intended known-good commit
  (`git ls-tree` evidence, not recollection).
- Managed surfaces correspond to the rolled-back version (no
  newer-version leftovers in managed files).
- Expected and acceptable: currentness checks report the consumer as
  behind-latest. That is the *correct* post-rollback state, not a defect
  to fix in the same slice.

## 6. Claim ceiling after rollback

CAN claim:

- The consumer is restored to known-good framework commit X, with bound
  pre/post evidence.
- The failed update's evidence trail is preserved.

CANNOT claim:

- That the failed update never happened (history is retained, not
  erased).
- That the rolled-back version is "current" (it is known-good, and
  behind-latest by construction).
- That the root cause is resolved — failure analysis is a separate
  slice; rollback only restores a known-good state.
- That rollback is automated, enforced, or tested — this is a manual,
  documented procedure derived from observation, and remains so until a
  real execution produces evidence.
