# Emergency Event Journal Policy Decision - 2026-10-01

Status: **OWNER-AUTHORIZED POLICY CHANGE / IMPLEMENTED LOCALLY; REVIEW AND COMMIT PENDING**
Date: 2026-10-01
Scope: one append-only canonical daily event during measured active-task EMERGENCY pressure.
Authority: the owner authorized starting the §7.4 policy change and directed that today's daily memory be repaired. This decision records only the narrow event-journal exception; it does not grant active-state cutover, cleanup, or firmware authority.

## Decision

Accept a narrowly bounded Emergency Event Journal exception to the ordinary EMERGENCY no-memory-mutation rule. The exception permits one canonical session-derived event appended only to `memory/YYYY-MM-DD.md` through `governance_tools.memory_record --emergency-event`, subject to the conditions below.

This is an explicit policy semantic change, not a reinterpretation of bounded maintenance. The bounded-maintenance exception remains unchanged and still prohibits memory mutation and memory writer/closeout round-trips. The event lane is separate and is not bounded maintenance.

## Admission Conditions

- Current owner authorization is required for each event; the writer records a single-line authorization reference. The reference is audit context, not cryptographic proof of human identity.
- The writer remeasures pressure at invocation. It refuses unless the active file is a stable, regular, strict-UTF-8 file whose canonical line or character count is EMERGENCY.
- The event is canonical `session-derived` daily memory and records what happened, evidence location/hash, what remains incomplete, current next step, timestamp, active-source SHA-256 and its measured pressure counts.
- Evidence must be an existing regular, non-symlink file under repository `artifacts/evidence/`, at most 10 MiB. The writer hashes the file and binds its path/hash into `test_evidence` and the record identity.
- One event of at most 4 KiB may be appended per active-source SHA-256. A same-directory exclusive lock serializes event attempts. Failure to lock or validate refuses the write.
- The writer only appends to the canonical date-named daily file. It refuses projections, `01_active_task.md`, archives, PLAN, arbitrary paths, missing evidence, reused quota, oversize content, and non-EMERGENCY pressure.
- After a successful event append, run the memory workflow dispatcher with `--run-guard` and report its warnings/blockers.

## Explicit Non-Effects

The event lane does not:

- modify, replace, summarize, or reduce `memory/01_active_task.md`;
- archive, delete, compress, or otherwise clean memory;
- lower or clear EMERGENCY pressure;
- authorize new product/hardware decisions, firmware writes, cutover, commit, push, or continuation based only on the record;
- make evidence semantically true merely because its path and hash are recorded; or
- supersede the independent review finding against the 2026-10-01 active-state replacement candidate.

The previous active-state candidate remains `CHANGES_REQUESTED / HIGH` and was not applied. Any future active-state retrieval-index/cutover mechanism is a separate architecture decision and authorization.

## Implementation Boundary

The local implementation adds an ordinary-writer EMERGENCY gate plus the explicit event API/CLI, focused failure-path tests, §7.4 and Memory Protocol text, and janitor guidance. The implementation remains uncommitted pending focused validation and review. This decision does not claim that all framework execution surfaces or external consumers have adopted the change.

## Validation Required Before Commit

- focused tests prove normal daily and projection writers refuse under EMERGENCY;
- success fixture proves the event is daily-only, evidence-hash-bound, bounded, and leaves active bytes and pressure unchanged;
- fail-closed fixtures cover non-EMERGENCY state, missing/forged authorization fields, evidence escape/symlink/size, duplicate active digest, PLAN mutation, unsupported locking, and write/target identity mismatch;
- janitor cleanup remains fail-closed;
- documentation and tests agree on the one-event quota and all non-effects;
- run the relevant memory workflow/authority guard after the eventual real daily append.
