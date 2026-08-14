# Parallel-session memory writes: collision analysis

**Date:** 2026-08-13
**Status:** design note — read-only analysis, no tool or memory changes made
**Scope:** why two sessions writing the same day's memory file collide, and what
a contract would have to decide. Does not propose an implementation for approval.

## Claim boundary

This note documents an observed failure with two confirmed occurrences, both on
2026-08-13, and one earlier precursor that is a different shape. It does **not**
claim the proposed directions are correct, sized, or free of side effects; none
of them has been prototyped. It does not claim the memory record format is
wrong — the format is not implicated.

## What happened

Two confirmed occurrences, plus one earlier precursor that is **not** the same
shape and should not be counted as one.

| when | where | effect |
|---|---|---|
| 2026-08-13 | `CFU/ai-governance-framework/memory/2026-08-13.md` | untracked locally, tracked upstream. Blocked `git merge --ff-only`, which fail-closed the consumer's F-7 update. |
| 2026-08-13 | `memory/2026-08-10.md` … `2026-08-13.md` | 41 untracked local records vs 13 committed upstream, fully disjoint. Blocked `git pull --ff-only` on main. |

**Precursor, 2026-08-06.** `memory/2026-08-06.md` ends up holding four records
from four session ids (`019fd534…`, `codex-20260806-post-merge-verification`,
`session-20260806T064136-0decea`, `session-20260806T090312-43cc50`). That shows
parallel writers sharing a file; it does not show this failure. Git history has
one commit adding the file (`1eed6ec9`) and two later commits modifying it
(`849f8079`, `1b780caa`) — each with the file already present in its parent. No
independent creation, no recorded git refusal, no untracked collision.

An earlier note deferred 2026-08-06 as "cross-session file ownership". That
concerned who may write records belonging to another session *inside* a file — a
different question from two checkouts creating the same path. Treating them as
one incident inflated the evidence; they are listed separately here.

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

The append writer is not the cause of *these two* failures: in both, the file
was born untracked, concurrently, at a predictable path, and git refused before
any merge logic ran.

It does not follow that appending is safe once both sides are tracked. It is
not. Reproduced in a scratch repo:

| scenario | result |
|---|---|
| both sides tracked, both append at EOF | `CONFLICT (content)` |
| file absent in base, both sides create and commit | `CONFLICT (add/add)` |
| both sides tracked, `m.md merge=union` declared | merges clean, both records kept |

So there are two distinct failures on the same path, and tracking status decides
which one is reached. Making the file tracked does not remove the problem; it
changes which mechanism blocks.

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
- It genuinely fixes the tracked-side failure — verified above, both records
  survive the merge. That failure is real even though neither observed incident
  reached it.
- **It does nothing for the untracked case**, which is what occurred both times.
  Git refuses before consulting any merge driver. On its own this is not a fix
  for the observed incidents; it closes the adjacent hole, not this one.

### Structural: separate the source from the aggregate

Have `session_end` write to a per-session path — `memory/sessions/YYYY-MM-DD.<session-id>.md` —
and treat `memory/YYYY-MM-DD.md` as a deterministic aggregate regenerated from
those sources.

- **Source** collisions become structurally impossible: no two sessions share a
  source path. This is the part that is actually closed.
- The aggregate is not closed by this. `memory/YYYY-MM-DD.md` remains a shared,
  predictable path, and if every checkout materialises it locally while it is
  untracked, the original collision reappears one level up. The direction is
  incomplete until three things are decided: whether the aggregate is an ignored
  projection, a single-owner committed artifact, or generated only in CI and at
  query time; who materialises it; and when it may be committed.
- It is the pattern this repo already uses elsewhere — canonical source plus a
  regenerable projection, with a digest to detect drift.
- Cost is real: every tool that reads `memory/YYYY-MM-DD.md` keeps working only
  as long as the aggregate is faithfully regenerated, and the regeneration step
  becomes a thing that can itself go stale. That is a new surface, on a repo
  that is already carrying 101 queued surface-maintenance entries.

### Rejected while writing this

Having `session_end` commit the memory file. This was rejected for the wrong
reason on the first pass, which said it "does close the hole". It does not — it
makes the file tracked, which moves the failure from a refused checkout to
`CONFLICT (content)` on the next merge, as reproduced above. It trades one
blocking mechanism for another.

The cost objection stands on its own and is the real one: a hook would create
commits the human did not ask for, in a worktree that may hold unrelated dirty
state. That condition was observed in this incident — the consumer's worktree
carried modified firmware validation packages throughout — though nothing here
establishes how common it is across the fleet.

## What is not being claimed

- That the format, the append writer, or the provenance model needs to change.
  None is implicated.
- That either direction above is the right size. Neither has been prototyped.
- That this needs to be fixed before the 101-entry surface maintenance queue is
  re-validated. It is small and independent; sequencing is the owner's call.

## Relation to memory retrieval work

This failure is a **write and ownership** failure, not a retrieval failure. A
derived retrieval index over canonical memory — the Graphiti direction assessed
earlier — would not have prevented, detected, or repaired either occurrence,
and would inherit the inconsistency rather than resolve it. The
admission trigger for that work is a reproducible retrieval failure, and this
is not one.
