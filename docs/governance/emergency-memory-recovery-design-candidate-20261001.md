# Emergency Memory Recovery Design Candidate - 2026-10-01

Status: **PARTIALLY ADOPTED LOCALLY: LANE A POLICY DECIDED; LANE B DESIGN CANDIDATE ONLY**
Date: 2026-10-01
Scope: recovery from `memory/01_active_task.md` EMERGENCY pressure without weakening evidence, authority, or rollback guarantees.
Semantic change: Lane A received owner authorization as a bounded §7.4 exception; local implementation is under test and is not yet committed or adopted by other consumers. Lane B remains unadopted.
Runtime behavior change: local canonical writer now has an explicit event-only route; adoption remains incomplete pending review, validation, and commit.
Enforcement change: local normal writers fail closed at EMERGENCY; the explicit event route is limited to daily append and preserves active pressure. No active-state cutover behavior changed.

This document is a partial design record. Lane A policy authorization is recorded in `emergency-event-journal-policy-decision-20261001.md`; the event implementation remains local and must pass its focused review/tests before use. This document does not authorize a write by itself. It does not authorize an active-state replacement, cleanup, pressure reset, or another attempt at the rejected 2026-10-01 candidate. Lane B remains a proposal only.

## Problem

The current policy has two individually defensible constraints but no complete transition between them:

1. EMERGENCY stops ordinary reliance on or expansion of active-task memory. Its bounded-maintenance exception excludes memory mutation and memory-writer/closeout round-trips.
2. Resuming active-state use requires an authorized, verified-archive plus replacement-state cutover. The legacy janitor remains fail-closed.

A semantic-fidelity review can reject a candidate. The 2026-08-30 operational finding further prohibits a third same-method candidate after a blocking review and requires a distinct durable-state versus retrieval-index architecture decision. There is no implemented emergency event journal or reviewed cutover orchestrator to preserve new session events and safely return to a usable active state.

The result is an intentional fail-closed stop with no specified automatic recovery transition. This proposal does not describe that state as a security boundary or claim that every memory task is impossible; it identifies the missing, owner-controlled recovery workflow.

## Design Goals

- Preserve source bytes, event provenance, authority status, claim ceilings, unresolved risks, and consumed authorizations.
- Distinguish append-only event capture from replacement of the active retrieval projection.
- Allow no hidden or generic EMERGENCY override.
- Ensure review binds to the exact candidate bytes and source identity.
- Keep the active file unchanged on every pre-cutover refusal.
- Provide an exact rollback path for every post-cutover validation failure.
- Keep pressure status measured and visible; successful mechanics alone never clear EMERGENCY.
- Keep the normal memory writer and normal active-summary writer unchanged unless the owner separately adopts a narrowly scoped emergency policy.

## Proposed Two-Lane Model

### Lane A: Emergency Event Capture

Policy decision recorded: permit one bounded canonical daily event append while active-task pressure is EMERGENCY, under `emergency-event-journal-policy-decision-20261001.md`.

Recommended candidate policy: allow only one explicit, append-only `session-derived` daily record through the canonical writer when all of these are true:

- a current human instruction authorizes the specific record;
- the event facts and evidence are independently available without relying on the pressured active summary;
- the record cites durable evidence and records unresolved status and claim limits;
- the writer appends only to `memory/YYYY-MM-DD.md` and cannot write `01_active_task.md`, archive files, or arbitrary paths;
- the operation does not claim to reduce pressure or authorize later active-state use;
- the memory workflow guard runs afterward and reports all warnings/blockers.

This is a deliberate, narrow exception to the ordinary no-memory-mutation rule. It does not permit active-state writes or pressure reduction. The owner has authorized this policy change; the local implementation must pass focused review and validation before the real daily event is emitted. Once implemented, events remain ordinary canonical event records, not active-state recovery.

### Lane B: Active-State Recovery

Active-task replacement remains separately gated. The proposed state machine is:

`EMERGENCY_LOCKED -> SOURCE_FROZEN -> CANDIDATE_PREPARED -> REVIEWED_EXACT_HASH -> OWNER_AUTHORIZED -> ATOMIC_CUTOVER -> POST_CUTOVER_VALIDATED -> PRESSURE_REMEASURED`

A transition is fail-closed. A rejected review leaves the source active and unchanged. A changed candidate invalidates the review. A stale source identity invalidates the cutover authorization.

## Required Protocol

1. **Freeze the source.** Capture repository identity, branch/HEAD, active path, exact bytes, SHA-256, Git blob, line/character counts, newline/BOM state, and file type. Reject symlinks, path aliases, unexpected hard links, staged conflicts, or a changed source.
2. **Create a verified rollback archive.** Create once on the same filesystem without overwrite. Flush and reopen it; verify exact-byte equality, digest, metadata, and path identity before preparing replacement.
3. **Build a placement matrix.** For every predecessor item, classify irreversible state, effective claim ceiling, authority/reference status, open risk, or historical event. Identify exact source anchors, existing durable destinations, candidate locations, decision effect, and unresolved ambiguity. No candidate may silently promote a projection or create authority by pointer alone.
4. **Prepare the candidate off-target.** The active file remains untouched. Require explicit current-state sections, explicit non-claims, current next action, historical-source pointers, and unresolved items. Candidate generation must be deterministic or its exact output hash frozen.
5. **Review the exact bytes independently.** Reviewer checks every matrix row, all irreversible declarations, all corrected claim ceilings, and all current authority/status references. Approval binds to the source digest, candidate digest, matrix digest, and tool/reviewer identity. Any edit invalidates approval. The candidate author cannot self-approve.
6. **Authorize the exact cutover.** Human authorization names source digest, archive digest, candidate digest, matrix/review digest, target path, maximum write set, and allowed rollback action. Authorization does not include commit or push unless stated separately.
7. **Revalidate immediately before mutation.** Recompute source identity and confirm it is unchanged; confirm candidate and review digests; confirm archive equality; confirm no newly staged or overlapping changes; confirm target is a regular file in the expected repository.
8. **Replace atomically.** Write a same-filesystem temporary file, fsync it, reopen and verify candidate digest, then use an atomic replace. Preserve the archive. Never use the legacy janitor `--execute` path.
9. **Validate after replacement.** Reopen the active path, verify exact candidate digest and encoding, run structural checks, resolve each required pointer, and test retrieval of the matrix's decision-critical items. Structural checks do not replace semantic approval.
10. **Rollback on any post-write failure.** Atomically restore from the verified archive, reopen and verify the predecessor digest, then stop. If rollback cannot be verified, report an explicit unresolved recovery state and require human intervention; do not retry automatically.
11. **Remeasure pressure.** Apply the canonical line and character thresholds to the resulting active file. Only the measured result determines pressure status. A successful cutover that remains over threshold stays EMERGENCY; status is not cleared by review approval or a passing writer/guard.
12. **Retain recovery evidence.** Preserve source/archive/candidate/matrix/review/operation digests and outcomes in an auditable receipt. Do not delete prior records or imply that receipt presence proves semantic correctness.

## Failure Matrix

| Failure | Required behavior |
| --- | --- |
| Archive missing, occupied, unreadable, or digest mismatch | Refuse; active source unchanged |
| Candidate or matrix omits an item or authority is ambiguous | Reviewer rejects; active source unchanged |
| Reviewer unavailable, non-independent, or not bound to exact hashes | Refuse; active source unchanged |
| Candidate changes after approval | Invalidate approval; no write |
| Active source changes after freeze | Invalidate authorization; no write |
| Dirty/staged overlap or target identity mismatch | Refuse; active source unchanged |
| Atomic replacement fails before completion | Restore/retain predecessor; verify exact digest |
| Post-cutover retrieval or digest check fails | Restore verified predecessor atomically; verify; stop |
| Rollback verification fails | Stop with recovery unresolved; human intervention required |
| Pressure remains above the threshold | Keep EMERGENCY; no claim that normal reliance is restored |
| Semantic review returns a blocking finding | Do not iterate the same manual candidate path; require a separately reviewed architecture/design decision |

## Required Tests Before Adoption

- Normal daily emergency-event append is either explicitly allowed by policy and tested, or explicitly remains blocked; no implicit writer bypass.
- Active-state recovery tests use temporary repositories/filesystems and assert exact bytes and digests.
- Pre-cutover rejection tests prove source immutability for every refusal row in the failure matrix.
- Hash-binding tests prove any candidate/matrix/source mutation invalidates approval.
- Crash/fault-injection tests cover archive flush, temporary write, atomic replace, post-cutover read, and rollback.
- Semantic fixtures cover irreversible state, corrected claim ceilings, authority references, unresolved rows, and historical `next_step` values that must not become current authorization.
- Pressure tests verify both line and character thresholds before and after cutover.
- The legacy janitor remains fail-closed; no new path calls its mutating entrypoint.
- The final gate remains distinct from reviewer approval: approval does not itself authorize a write.

## Decisions Still Required Before Active-State Recovery

1. Choose the canonical receipt storage/writer for active-state cutover; preserve the rule that operational records live under `memory/`, and do not treat external evidence as canonical memory.
2. Define reviewer independence, exact-hash attestation, authorization identity, and whether another candidate after the prior HIGH rejection requires a new architecture tranche.
3. Define atomic replacement portability and durability requirements for supported filesystems/platforms.
4. Define retrieval assertions required after cutover without promoting projections into authority.
5. Decide whether automatic code may perform a reviewed atomic operation or whether active-state cutover remains a human-run procedure.

## Non-Goals

This candidate does not:

- adopt Lane B active-state cutover or change its rejection boundary;
- authorize cleanup, active-state rewrite, pressure reset, firmware, commit, or push;
- authorize another attempt using the rejected 2026-10-01 replacement candidate;
- interpret or alter existing obligation ledgers, PLAN state, firmware state, or P40 evidence;
- claim adoption by other consumers or full governance/runtime enforcement.

## Acceptance Boundary

This document can support architecture review only. It cannot be cited as an adopted recovery policy or as permission to write memory. Implementation requires a separate owner decision on the open questions, a reviewed contract update, focused failure-path tests, and explicit adoption through the framework's normal governance process.
