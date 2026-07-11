# Runtime Treatment Census — Closeout Pair Tranche 2 (2026-07-11)

Status: read-only assessment of two pinned census units. This document proposes
no closeout, schema, hook, gate, F-7, or runtime change.

## Problem

The census gives the closeout pair the only `observed` decision-evidence label
in its 33-unit set. This tranche checks whether that observation supports
retention, whether the two units duplicate each other, and whether their output
is understandable to a reviewer rather than only to runtime code.

## Scope and method

Units assessed:

1. `runtime_hooks/core/session_end.py`
2. `runtime_hooks/core/_canonical_closeout.py`

The review uses the census's stated observation that closeout receipts are
consumed in the F-7/P1-C evidence chain. It does not upgrade that observation
to measured effectiveness, framework correctness, or consumer adoption proof.

## Assessment

| Unit | Decision effect | Maintenance cost | Duplication assessment | Plain-language purpose | Disposition candidate |
| --- | --- | --- | --- | --- | --- |
| `runtime_hooks/core/session_end.py` (1366 LOC; census 7 filename-containment tests) | **Observed, not measured.** Its lifecycle emits canonical closeout-related evidence that is consumed by the F-7/P1-C evidence chain. That evidence determines whether an update/onboarding claim may be reported with the required closeout evidence, but does not prove the underlying work is correct. | High: this is a wide orchestrator spanning closeout, memory, promotion, claim-enforcement packets, indexes, and runtime summaries. The focused session-end/canonical suite passed 48 tests, but test count does not prove each subfamily is needed. | **Not duplicate.** It owns lifecycle orchestration and invokes the canonicalizer before writing artifacts; it has responsibilities beyond canonicalization. | “At the end of a session, this gathers the session outcome and writes the evidence that later reviewers and update workflows can inspect.” | `keep_observe`: its observed evidence-chain role warrants retention; any future cost reduction must inspect its internal subfamilies, not merge it with the canonicalizer. |
| `runtime_hooks/core/_canonical_closeout.py` (342 LOC; census 3 filename-containment tests) | **Observed, not measured.** It is the canonicalization boundary for the artifacts consumed downstream. Its documented fallback statuses stop an AI-authored candidate from being treated as authoritative evidence without validation. | Medium: a concentrated, documented trust-boundary module. Its candidate/schema/semantic status rules are load-bearing and must remain aligned with its producer and consumers. | **Not duplicate.** It is the sole canonicalization function; `session_end` supplies lifecycle inputs and writes its result. Removing or inlining it would erase the explicit trust boundary rather than remove duplicated behavior. | “This turns an agent's untrusted end-of-session note into one consistent system record, or labels it missing, invalid, incomplete, or inconsistent.” | `keep`: retain as a distinct trust boundary. A retirement or merge case would require replacement evidence and a focused safety review, not absence of recent output. |

## Cross-unit conclusion

The pair has a real division of responsibility:

```text
agent candidate (untrusted)
  -> _canonical_closeout validates and normalizes
  -> session_end coordinates writes and related lifecycle outputs
  -> F-7 / P1-C evidence chain consumes the canonical result
```

This is not two validators checking the same fact. The observed downstream use
supports retaining both roles, with different maintenance posture: the
canonicalizer is a concentrated trust boundary; the session-end orchestrator
is the future cost-review candidate because it carries several unrelated
subfamilies.

## Human comprehensibility finding

The canonical closeout artifact is reviewer-auditable but not, by itself, a
plain-language operator report. The closeout schema names the status meanings,
while F-7 and newcomer-facing summaries translate update/adoption state for a
human. Therefore this pair should not be promoted as the complete “human
understanding layer”; it is the evidence layer that those summaries rely on.

## Evidence checked

- `docs/governance/runtime-treatment-census-manifest-2026-07-11.md` — pinned
  units and the only recorded observed downstream consumption boundary.
- `docs/closeout-schema.md` — candidate/canonical trust boundary, status
  meanings, and `build_canonical_closeout()` ownership.
- `runtime_hooks/core/session_end.py` and
  `runtime_hooks/core/_canonical_closeout.py` — call relation and lifecycle
  separation.
- `.venv\\Scripts\\python.exe -m pytest tests/test_runtime_session_end.py
  tests/test_canonical_closeout.py -q -p no:cacheprovider` — 48 passed.

## Claim ceiling and next evidence

This tranche supports `keep`/`keep_observe` candidates only. It does not prove
every session end result is correct, that the pair has positive behavioral
effect, that F-7 is complete, or that a closeout receipt proves framework
correctness.

The least-cost next review is an internal, read-only subfamily map of
`session_end.py` that separates canonical-closeout coordination from memory,
claim-enforcement, index, and summary side effects. It must not start from an
assumption that any subfamily is removable.
