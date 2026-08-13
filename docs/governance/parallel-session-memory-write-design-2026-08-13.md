# Parallel-session memory writes: collision analysis

**Date:** 2026-08-13
**Status:** design note — read-only analysis, no tool or memory changes made
**Scope:** why two sessions writing the same day's memory file collide, and what
a contract would have to decide. Does not propose an implementation for approval.

## Claim boundary

This note documents an observed failure with three occurrences. It does **not**
claim the proposed directions are correct, sized, or free of side effects; none
of them has been prototyped. It does not claim the memory record format is
wrong — the format is not implicated.

## What happened

Three occurrences of one shape. The first was recognised at the time and
deferred as "cross-session file ownership, not a format problem".

| when | where | effect |
|---|---|---|
| 2026-08-06 | `memory/2026-08-06.md` | four records from four session ids in one file: `019fd534…`, `codex-20260806-post-merge-verification`, `session-20260806T064136-0decea`, `session-20260806T090312-43cc50`. Noticed, deferred. |
| 2026-08-13 | `CFU/ai-governance-framework/memory/2026-08-13.md` | untracked locally, tracked upstream. Blocked `git merge --ff-only`, which fail-closed the consumer's F-7 update. |
| 2026-08-13 | `memory/2026-08-10.md` … `2026-08-13.md` | 41 untracked local records vs 13 committed upstream, fully disjoint. Blocked `git pull --ff-only` on main. |

The third occurrence did measurable damage. Because main could not advance, a
test run used sources from `ea0dcdf1` while claiming to exercise a fix that
lived in `20c97b94` — a fix was evaluated against the code it was meant to
replace. That was caught, but by luck: the test failed for a reason that
happened to look wrong.

## Mechanism

Not a merge conflict. A **name collision between independently created files**.

1. `memory_record.append_session_derived_entry_with_outcome` creates
   `memory/YYYY-MM-DD.md` with a date header when it does not exist
   (`governance_tools/memory_record.py:217`) and otherwise opens it in append
   mode (`:230`).
2. `runtime_hooks/core/session_end.py` calls that writer at session end. It
   resolves HEAD and computes `memory_binding`, but **never stages or commits** —
   there is no `git add` or `git commit` for memory anywhere in `runtime_hooks/`
   or `memory_record.py`.
3. So each session, starting from whatever base commit it has, finds the day's
   file absent and creates it. Two sessions on divergent bases each end up with
   their own untracked file at the same path.
4. When one of them commits and pushes, the other's checkout has an **untracked**
   file where git wants to place a **tracked** one. Git refuses — correctly; it
   will not overwrite unversioned content.
5. `.gitattributes` declares no merge strategy for `memory/`, so nothing
   downstream reconciles them either.

The append writer is not the problem. Appending is correct and would compose
fine if both sides were tracked. The problem is that the file is *born
untracked*, concurrently, at a predictable path.

## Why nothing caught it

- `daily_memory_gate` reads the **staged** diff; an untracked file has no staged
  diff, so it reports "no added lines" and cannot see the situation.
- `memory_authority_guard` checks provenance per record — writer, binding,
  evidence. Every record in both sets passed. Provenance was never in doubt.
- The CI job (`Memory Workflow Selective Blocker`) is green on both sides,
  because each side is internally consistent. The collision only exists in the
  relationship between two checkouts.

Nothing is checking the property that actually broke: *whether this path can be
fast-forwarded onto*.

## What a contract has to decide

**Who owns a date-named file.** Today, nobody. Each session behaves as if it is
the only writer. Any fix has to answer this first; the rest follows.

Two directions, not mutually exclusive:

### Stopgap: make the collision survivable

Declare a union merge for `memory/*.md` in `.gitattributes` and add an
untracked-memory warning to the existing pre-commit advisory.

- Cheap, standard git, no format change.
- **Only helps once both sides are tracked.** It does not address the case that
  occurred all three times, where one side is untracked. On its own this is not
  a fix — it narrows the window, it does not close it.

### Structural: separate the source from the aggregate

Have `session_end` write to a per-session path — `memory/sessions/YYYY-MM-DD.<session-id>.md` —
and treat `memory/YYYY-MM-DD.md` as a deterministic aggregate regenerated from
those sources.

- Collisions become structurally impossible: no two sessions share a path.
- It is the pattern this repo already uses elsewhere — canonical source plus a
  regenerable projection, with a digest to detect drift.
- Cost is real: every tool that reads `memory/YYYY-MM-DD.md` keeps working only
  as long as the aggregate is faithfully regenerated, and the regeneration step
  becomes a thing that can itself go stale. That is a new surface, on a repo
  that is already carrying 101 queued surface-maintenance entries.

### Rejected while writing this

Having `session_end` commit the memory file. It makes the file tracked
immediately, which does close the hole — but it means a hook creates commits the
human did not ask for, in a worktree that may hold unrelated dirty state. Every
consumer repo in this fleet has firmware or product files dirty at any given
moment. Trading a blocked fast-forward for surprise commits in a consumer's
worktree is a worse deal.

## What is not being claimed

- That the format, the append writer, or the provenance model needs to change.
  None is implicated.
- That either direction above is the right size. Neither has been prototyped.
- That this needs to be fixed before the 101-entry surface maintenance queue is
  re-validated. It is small and independent; sequencing is the owner's call.

## Relation to memory retrieval work

This failure is a **write and ownership** failure, not a retrieval failure. A
derived retrieval index over canonical memory — the Graphiti direction assessed
earlier — would not have prevented, detected, or repaired any of the three
occurrences, and would inherit the inconsistency rather than resolve it. The
admission trigger for that work is a reproducible retrieval failure, and this
is not one.
