---
name: pr-review-merge-gate
description: Decide whether a pull request can be merged safely, without turning it into subsystem qualification. Use when reviewing a PR, triaging review findings, or re-reviewing after a correction, especially when a real finding is not this PR's responsibility.
---

# PR Review Merge Gate

A merge gate answers one question:

> Can this pull request, at its stated claim ceiling, be merged safely?

It does not answer whether the surrounding subsystem is free of defects. That is
a qualification question, and mixing the two is what turns a small change into
unbounded work:

```text
small PR -> review finds a deeper subsystem issue -> the issue is real
         -> the PR is made to carry full subsystem qualification -> never ends
```

Keep them apart. Engineering merge asks whether this change is safe.
Qualification asks whether a capability is proven.

## 1. Freeze the merge decision before reviewing

Write these down first, and judge every finding against them:

```text
DECISION       what this review is deciding, e.g. can PR #93 merge safely
CLAIM CEILING  what the PR actually claims to have done
BOUNDARY       changed surface plus its real semantic blast radius
```

Without a frozen decision, a reviewer drifts into "since I am already looking at
this subsystem, let me prove the whole subsystem".

## 2. Give every finding four answers

Preserve the severity scale already in use — `BLOCKING`/`WARNING`/`SUGGESTION`
from `REVIEW_CRITERIA.md` §2.1, or `P0`-`P3` from an external reviewer. Do not
invent a second scale.

| Field | What it answers |
|---|---|
| Severity | How bad the finding is |
| Attribution | Introduced, worsened, exposed, or pre-existing |
| Decision impact | Whether it makes this PR's `DONE` or merge safety unsound |
| Disposition | fix now, workaround, carried-forward, separate bounded work |

The third field is the one that changes behaviour. `P1` no longer implies "must
fix before merge"; it implies "this is serious, now decide whether it blocks
*this* decision".

## 3. What actually blocks

A finding blocks merge only when at least one holds:

1. The PR introduces or worsens a blocking-severity issue.
2. The finding makes the PR's stated `DONE` or claim ceiling untrue.
3. The issue is pre-existing, but this PR causes that dangerous path to be
   entered, or widens exposure to it.
4. The finding invalidates evidence, identity, or irreversible state the merge
   decision relies on.

Nothing else blocks merely by being real and severe.

Worked example — a presentation-only PR, where review finds a `P1` in a shared
writer the PR neither modifies nor executes:

```text
Severity        P1
Attribution     pre-existing
Decision impact none - this PR neither modifies nor runs that path
Disposition     carried-forward, separate bounded work
```

That is a complete, legitimate outcome. The wrong outcome is to fix the writer,
then review the fix, then find a parser issue, then fix that.

## 4. Re-review is delta-bounded

Exact-head review stays mandatory: a merge decision must be bound to the exact
bytes being merged, and a verdict on an older head is never carried forward.

But a new head does not reopen the whole subsystem. A re-review looks at:

1. whether the previously reported blockers are actually resolved;
2. whether the correction delta introduces or worsens a blocking issue;
3. the necessary adjacent paths inside the correction's semantic blast radius.

Only three things legitimately widen the boundary again:

- the PR's claim ceiling grew;
- the correction touched a shared semantic choke point that serves other paths;
- new evidence shows the original boundary judgement was wrong.

See `references/rereview-prompt.md` for the wording to send an external reviewer.

## 5. MERGE READY

```text
MERGE READY when:
1. the exact current HEAD has been reviewed;
2. PR-introduced or PR-worsened blocking findings = 0;
3. no unresolved finding invalidates the PR's frozen DONE, claim ceiling,
   merge safety, or relied-upon evidence;
4. required scope-matched checks are green;
5. remaining real findings carry an explicit disposition and are not
   misreported as fixed or absent.
```

This is deliberately not "repository-wide blocking findings = 0".

## 6. Report the decision, not just the findings

```text
MERGE DECISION: READY
Reviewed HEAD: <sha>

Blocking findings:
- none

Carried-forward findings:
- P1 - shared writer identity inconsistency
  Attribution: pre-existing
  Current merge impact: none
  Reason: this PR neither modifies nor executes that path
  Disposition: separate bounded work

Required checks: green
```

Stated this way, "there is an open P1" and "this PR can merge" stop
contradicting each other.

## 7. Evidence freshness follows the same shape

Do not refresh all evidence after every correction. Correct, correct, correct,
then freeze a candidate head, then refresh the merge-critical evidence and run
the exact-head review against it.

The exception: if a correction changed the evidence authority itself, that
evidence must be re-derived rather than reused.

## Specification review

A specification can always be asked about a future version, duplicates,
migration, legacy, multi-writer, or cross-session behaviour. That is why spec
review is the easiest place to lose a week.

> A future-state concern with no executable path today, which does not change
> the next authorized implementation decision, does not block acceptance of the
> current spec.

Record it as a deferred design question. Do not grow the spec to answer it.

## Anti-goals

- Do not build validators, schemas, ledgers, or dashboards to enforce this. The
  failure mode being fixed here is over-governance; answering it with more
  governance surface repeats the mistake.
- Do not lower a real finding's severity to make it non-blocking.
- Do not report a carried-forward finding as fixed, absent, or resolved.
