# Gate 0 Admissibility — pre-push guard binds to working-dir HEAD, not the outgoing ref

Status: Gate 0 assessment only. No fix is committed, no experiment is run,
no Skill / validator / schema / runtime / hook / CI / gate / enforcement is
added or changed by this document. Recording admissibility does not authorize
Gate 1 pre-registration or any run; the Engineering Skill Program itself
remains owner-review DRAFT.

Program reference:
[evidence-backed-engineering-skill-program-2026-07-24.md](../governance/evidence-backed-engineering-skill-program-2026-07-24.md),
Section 8 Gate 0 and Section 5 task admissibility.

## Candidate task

The shipped `pre-push` hook template measures the wrong diff. A `git push`
hook receives, on stdin, one line per pushed ref of the form
`<local ref> <local sha1> <remote ref> <remote sha1>`. The template ignores
stdin entirely and passes `--head-ref HEAD` — the checked-out working-tree
HEAD — to `version_bump_guard.py`. When the pushed ref is not the checked-out
branch (or the working tree is behind the remote default branch), the guard
diffs the wrong commits and can report `changed_files=0` while the outgoing
commit changes files.

## Gate 0 checklist (Section 8)

| Requirement | Status | Evidence |
|---|---|---|
| Real bug, not manufactured | PASS | Hit naturally on 2026-07-24 while pushing `governance/grimm-price-receipt-bc513fa` to Bookstore-Scraper. The push log showed `changed_files=0`; the outgoing commit `74b637e` added 2 files. Reproduced a second time on the follow-up commit `b887d1f` push. |
| Clear reproduction | PASS | Push any branch whose tip differs from the checked-out HEAD, or push while the working tree is behind `origin/HEAD`. `git diff --name-only <base>...HEAD` over the wrong HEAD yields an empty set; over the pushed sha it yields the real files. |
| Credible behavior source (independent of production logic) | PASS | Git's documented pre-push stdin contract is the oracle: the guard must diff the sha actually being pushed, not the checked-out HEAD. This is a spec source, not the code under test. |
| Common baseline commit exists and is clean | PASS | Framework `origin/main == HEAD == 33006f09`, `git status` empty at assessment time. |

Gate 0 verdict: **ADMISSIBLE** as a Bug Fix study candidate task.

## Defect location (shipped template, not a single consumer)

- [scripts/hooks/pre-push:80](../../scripts/hooks/pre-push) — `--head-ref HEAD`
  hardcoded; stdin outgoing refs never read.
- [scripts/hooks/pre-push:63](../../scripts/hooks/pre-push) — runtime smoke runs
  `cd "$FRAMEWORK_ROOT" && ... --mode smoke`, i.e. the framework's own canned
  example payloads (`framework_self_smoke_advisory`), not the outgoing change.
- Consumer copies are line-for-line identical (Bookstore-Scraper
  `.git/hooks/pre-push` confirmed). The framework's own `.githooks/pre-push`
  is a different hook and does NOT carry this pattern; blast radius is
  onboarded consumers, not the framework repo itself.
- `grep "while read"` across `scripts/hooks/` and `.githooks/`: zero hits,
  confirming no hook consumes the git stdin ref contract.

## Severity framing

The guard is advisory (`|| true`, `pre-push:84`); it cannot block a push. The
authoritative gate is hosted CI, which diffs the real outgoing commit and was
confirmed green on Bookstore-Scraper PR #3. So this is a **local false-negative
in an advisory belt-and-suspenders check**, not a fail-open on a blocking gate.
Short-term risk of leaving it unfixed is low, which is what makes preserving it
as an experiment candidate acceptable.

## Root-cause family

This is the second independent surfacing this session of one root cause:
governance tooling binds to the *ambient working-directory state* rather than
to the *actual artifact under governance*.

| Surfacing | Bound to | Should bind to |
|---|---|---|
| Grimm receipts committed in Bookstore `c9cd494` | run-time HEAD `e478409` (parent) | the commit carrying the change `c9cd494` |
| This pre-push guard | working-tree HEAD | the outgoing pushed ref |

## What Gate 0 does NOT authorize

- No fix is written or committed here. Fixing inline would consume this clean
  natural baseline and contaminate any later four-arm replay (Section 5).
- No Gate 1 pre-registration, no experiment run.
- Owner still decides: (A) treat as an ordinary bug and fix now, forfeiting the
  experiment candidate; or (B) preserve it, hold the fix as a frozen candidate
  recipe for Gate 1. These are mutually exclusive for the same bug.
