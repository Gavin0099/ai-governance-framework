# Re-review prompt

Wording to send an external reviewer when a correction has produced a new head.
The point is to keep exact-head rigour while stopping the review from expanding
into subsystem qualification on every iteration.

```text
Review the exact current HEAD for this PR's frozen merge decision.

Prioritize:
1. whether previously reported blockers are actually resolved;
2. whether the correction delta introduces or worsens a blocking issue;
3. necessary adjacent paths affected by the correction's semantic blast radius.

Do not expand the review into unrelated subsystem qualification unless:
- the PR claim ceiling expanded,
- the correction changed a shared semantic choke point, or
- new evidence proves the prior review boundary was incomplete.

Preserve the severity of real findings, but separately determine whether each
finding materially blocks this PR's merge decision.
```

## Why the last line matters

Without it, a reviewer has only one lever: report the finding and let severity
imply "must fix now". With it, a genuine `P1` in an untouched path can be
reported at full severity and still be dispositioned as carried-forward, which
is what a senior reviewer would do.

## Symptom that this prompt is missing

Successive review rounds report real findings that all sit in the guard, the
test, or the tooling around the change rather than in the change itself, while
the reviewed implementation has not moved for several heads. That is a boundary
problem, not a quality problem.

When that happens, state the boundary explicitly in the artifact under review —
what it is, what it deliberately does not cover, and why covering that would be
disproportionate — so the next round has a stated answer to cite instead of
another iteration.
