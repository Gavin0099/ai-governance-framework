# Self-Governance Memory Blocking Policy RFC

Status: RFC / DESIGN ONLY — no enforcement change in this document
Date: 2026-07-04
Scope: R4 blocking policy for memory authority warnings

## DONE

DONE = the policy questions that must be answered before any memory authority
warning becomes blocking are written down: candidate blocking class, backcompat
for existing memory debt, hook / CI ownership, bypass survivability, and
escape-hatch semantics, without changing `memory_authority_guard`, hooks, CI,
tests, schema, runtime, or gate policy behavior.

## Problem

`memory_authority_guard.run_guard` is intentionally Phase 1:

- `ok=True` with `ok_meaning: guard_executed_report_only_not_authority_clean`;
- `enforcement_action: allow`, `blocking_violation_codes: []`;
- `claim_ceiling: report_only_phase1`;
- `not_claimed` includes `blocking_enforcement`.

Turning any of the six current violation codes into a blocker is a policy
change, not a detector tweak. Done wrong, it either floods historical memory
debt with hard failures, or creates an enforcement claim that a trivial bypass
falsifies.

Prior lesson applied: an earlier blocking attempt in this project cut to
fail-closed before the underlying contract was defined, and had to be walked
back. The direction was right; the sequencing was wrong. This RFC exists so
Phase 2 blocking is switched on only after its contract, fixtures, and override
semantics already exist.

## Candidate Blocking Classes

Inventory of current report-only codes and their suitability as the first
blocker:

| Code | Historical debt | Determinism | First-blocker suitability |
| --- | --- | --- | --- |
| `unbound_memory` | large (pre-contract daily files) | needs git worktree | unsuitable first; debt floods signal |
| `structural_memory_auto_write` | moderate | text-only | unsuitable first; promotion flow still evolving |
| `private_memory_cited` | small | filesystem scan | possible later; scan surface too broad for a gate |
| `missing_canonical_memory` | large | git-log dependent | unsuitable; punishes history, not new writes |
| `test_evidence_provenance_not_found` | moderate | filesystem + regex | premature until R3 receipt shape exists |
| `session_like_non_session_memory_type` | none (already active-window scoped) | text-only, no git needed | **recommended first blocker (B0)** |

### B0: active-window `session_like_non_session_memory_type`

Recommended first blocking class.

Reasons:

- the detector is already scoped to an activation window, so historical
  entries are structurally excluded — backcompat is built in;
- detection is deterministic from entry text alone: no git worktree, no
  filesystem provenance, no network — the same input always gives the same
  verdict in hook and CI;
- the violation is a canonical-writer bypass attempt, which is exactly the
  class blocking is meant to stop, not a data-quality debt problem.

### B1 (deferred): newly-created fabricated anchors

Fabricated `commit` / `session_id` anchors on newly added entries are the
higher-value target, but they are not safe as the first blocker:

- anchor resolution needs a git worktree; the no-worktree case currently
  degrades to not-bound-but-not-proven-fabricated, and a blocker would have to
  pick fail-open (a documented bypass) or fail-closed (false positives in
  copy-based consumers);
- "newly created" needs a precise definition (staged diff vs. active window vs.
  file mtime), each with different bypass shapes.

B1 should get its own mutation contract after B0 has run in practice.

Explicitly rejected as blockers in this RFC: historical `unbound_memory` and
`missing_canonical_memory`. They measure debt, not intent.

## Backcompat Policy

- Blocking applies only to violations whose activation-window condition places
  them at or after the policy activation date; nothing that already exists in
  `memory/` on the day the switch turns on may start failing.
- Historical debt stays visible through `report_only_violation_codes`
  unchanged. No retroactive de-verification, no forced backfill.
- The active-window boundary must be derived from entry content plus file
  identity as already implemented, not from git blame, so that verdicts remain
  identical across hook and CI checkouts.

## Ownership

Three surfaces exist today; the blocker's authority order must be explicit:

1. **CI (`.github/workflows/governance.yml` → `ci_memory_workflow_check`)** —
   authoritative gate. CI is the surface a hostile or careless writer cannot
   `--no-verify` past. Blocking semantics land here first.
2. **pre-commit (`scripts/hooks/pre-commit` → `memory_workflow --run-guard`)** —
   convenience mirror of the same verdict, so failures surface before push.
   Hook bypass via `--no-verify` is expected and stays classified as
   `manual_update`, consistent with the framework trust model: this is an
   audit boundary, not a security boundary.
3. **pre-push** — not an owner. Adding a third verdict point increases drift
   risk without adding authority.

Rule: hook and CI must call the same guard entrypoint with the same policy
input. A blocker that exists only in a hook is not a blocker; it is a
suggestion.

## Result Semantics After The Switch

The Phase 1 result shape was hardened so `ok=True` cannot be read as
"authority clean". The Phase 2 switch must extend, not mutate, that contract:

- `claim_ceiling` moves to `selective_blocking_phase2` (new value; the old
  value never silently changes meaning);
- blocked codes appear in `blocking_violation_codes`; everything else stays in
  `report_only_violation_codes`;
- `enforcement_action: block` and `ok=False` only when a blocking code fires;
- `not_claimed` keeps `semantic_truth_verification` and gains
  `full_blocking_enforcement` — blocking one class never claims blocking all;
- exit code becomes nonzero only for blocking violations, so existing
  report-only consumers keep parsing successfully.

## Escape Hatch And Override

- Override is per-entry and auditable: an explicit
  `authority_override: <reviewer identity> <reason>` field inside the flagged
  memory entry downgrades the block to a warning and emits a new report-only
  code `authority_override_used`.
- Overrides are never silent: the code appears in guard output and remains
  grep-able in the memory file itself.
- A repo-level kill switch (policy input, e.g. a versioned policy file or
  explicit CLI flag) can revert to Phase 1 semantics in one change, without
  touching detector code. The kill switch state must be visible in guard
  output so a disabled gate can never masquerade as a passing gate.
- No environment-variable override: env state is invisible to review and
  would create an unauditable bypass.

## Mutation Contract Required Before The Switch

The blocker may not ship until focused fixtures prove it survives the expected
bypasses of B0:

1. rewording the session-shaped entry while keeping a non-session
   `memory_type` — must still block;
2. novel `memory_type` values outside any known list — must still block if the
   session-shape condition holds;
3. appending a new session-shaped entry into an old (pre-window) daily file —
   must still block; window classification must come from the entry, not the
   file date alone;
4. hook bypass via `--no-verify` — hook does not catch it, CI must; the
   fixture asserts the CI path fails;
5. `authority_override` present — must downgrade to warning and emit
   `authority_override_used`;
6. kill switch active — must allow, and output must show the disabled state.

Each fixture lands as a test before the policy flips. Only after these pass
may the catalog row move toward a blocking claim, and even then the honest
ceiling is `selective blocking for one violation class`, not
`memory authority enforced`.

## Rollout Order

1. RFC review (this document).
2. Mutation fixtures for B0 (tests only, guard still report-only).
3. Policy input plumbing with default = Phase 1 (behavior unchanged;
   opt-in flag exercised only in tests).
4. Opt-in activation in this repository only; observe false positives across
   real sessions.
5. Default-on in this repository; external consumers remain opt-in via their
   own policy input.
6. B1 fabricated-anchor RFC, informed by B0 operation.

Each step is a separate slice with its own claim ceiling. No step may borrow
the next step's claim.

## Non-Goals

This RFC does not:

- modify `memory_authority_guard.py`, `memory_workflow.py`, hooks, or CI;
- add tests, fixtures, schema, or policy files;
- flip any warning to blocking;
- upgrade `unbound_memory` or `missing_canonical_memory` to blockers;
- retroactively de-verify or backfill historical memory;
- define B1 fabricated-anchor blocking semantics beyond deferral;
- claim hook-level blocking is a security boundary;
- update `docs/e1-mutation-catalog.md`;
- change Phase E / Gate 3 status, which remains frozen.

## Claim Ceiling

This RFC can claim:

- the first-blocker candidate is chosen with reasons
  (`session_like_non_session_memory_type`, active window);
- backcompat, ownership, override, and rollout semantics are defined before
  any code change;
- the bypass set the blocker must survive is enumerated;
- no enforcement behavior changed.

This RFC cannot claim:

- any blocking enforcement exists;
- `ok=True` means authority clean;
- memory authority violations are prevented;
- fabricated anchors are blocked;
- Phase E enforcement is complete;
- red-team audit is fully fixed.
