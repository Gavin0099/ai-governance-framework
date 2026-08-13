# Stale-checkout evidence chain: audit

**Date:** 2026-08-13
**Status:** audit findings + one disclosure change
**Scope:** trace what actually happened after the memory collision blocked an
update, and determine whether a "green but not the latest code" verdict was
produced. Companion to the collision analysis note.

## The chain, traced

`git pull --ff-only` failed → who still ran tests → who produced a verdict.

**1. The update failed and stopped.** Both occurrences fail-closed correctly.
Git refused to place a tracked file over untracked content; F-7 reported
`blocked` with `changed=[]` and wrote nothing.

**2. No automated flow continued.** Neither `f7_full_update.py` nor
`external_governance_submodule_updater.py` invokes tests or emits a verdict
after a failed update. The only matches for test invocation in the update path
are incidental: a path-prefix filter at `f7_full_update.py:506` (`_pytest_tmp`)
and a comment at `runtime_hooks/core/session_end.py:1110`. There is no hook that
runs a suite once an update returns blocked.

**3. The test run was operator-initiated.** A suite was run by hand in a
worktree whose `main` could not advance, so it executed sources from `ea0dcdf1`
while the work under test lived in `20c97b94`.

**4. No false success was produced.** This is the part worth being precise
about. The stale run **failed** — `assert 2 == 1` — and that failure is what
led to discovering the staleness, via an unrelated `AttributeError` for a symbol
that only exists in the newer revision.

So the realised harm was a **false negative**, not a false positive: the
momentary conclusion was that a correct fix was broken. The "all green on stale
sources" scenario is a plausible risk, not an observed one. Recording it as
observed would overstate the evidence.

## What was actually missing

Every head in an F-7 report describes the repo **being updated**:
`before_head`, `target_head`, `after_head`, `lock_adopted_commit`. The receipt
records `framework_root` — a path, not a revision. `_framework_head_commit`
resolves the *target's* framework root, which is the thing the tool has just
fast-forwarded.

Nothing described the checkout **doing** the updating, and the two are routinely
different: `framework_root` is the consumer's nested copy, while the tool runs
from wherever the module was imported. In the incident they differed by four
commits, and the report offered no way to see it.

## Change made

`F7Result.tool_provenance` — `executing_root`, `executing_revision`,
`executing_worktree_dirty`, and a claim boundary. Set in `__post_init__`, so a
result path added later cannot report a target without disclosing what produced
it. Surfaced in the human report as `produced_by_revision`, not JSON only: a
field that is not printed would not have been read in the situation it exists
for.

**Disclosure only.** It does not gate, block, or compare. There is no general
notion of a "required" revision for an arbitrary invocation, and inventing one
is a separate decision from recording what ran. Had this field existed on
2026-08-13, the stale run would have printed `ea0dcdf1` beside a target of
`20c97b94`.

## Deliberately not done

- **No gating on HEAD before evidence-bearing tests.** That was the remedy for
  the case where an automated flow continues past a failed update. Finding 2
  says no such flow exists here, so adding a runtime gate would be building for
  a mechanism that was not the one that failed.
- **No memory format, writer, or `.gitattributes` change.** The collision
  contract remains open, as set out in the companion note.
- **No global dedupe of repeated `record_identity` across dates.** That is a
  question about what a record asserts — an event or a write — and is not data
  corruption from this incident.
- **No Graphiti or plugin-architecture work.** Neither has an admission trigger.

## Claim boundary

This audit covers one incident on 2026-08-13 in this repository and one consumer.
It does not establish how often stale-checkout runs occur, that no false-success
verdict has ever been produced, or that the new field is sufficient to prevent
one. It records that in this incident the failure surfaced by accident, and that
the report now carries the fact that would have surfaced it deliberately.
