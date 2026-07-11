# Runtime Treatment Census — `session_end.py` Subfamilies Tranche 3 (2026-07-11)

Status: read-only internal map of one pinned census unit. This document
proposes no refactor, deletion, extraction, schema change, or runtime change.

## Problem

The preceding closeout-pair tranche retained `session_end.py` because the
closeout chain has observed downstream consumption. At 1366 LOC, that parent
observation must not be treated as proof that every side effect inside the
orchestrator has equal decision effect or maintenance value.

## Method

The module is partitioned by its existing function boundaries and outputs.
Line counts below are approximate review aids, not a claim that every line
belongs to exactly one concern. Direct decision evidence is intentionally
stricter than parent-level closeout evidence.

| Subfamily | Approx. source area | Primary outputs / consumers | Decision evidence | Maintenance / human-readability finding | Candidate |
| --- | --- | --- | --- | --- | --- |
| Lifecycle setup and ledger controls | lines 45–174 | runtime artifact directories; session index; compact claim-enforcement receipt | **None at subfamily level.** The session index is documented as a cache, not a source of truth. | Small but mixed durability semantics: the index is non-fatal/cache-like, while claim receipt emission is evidence-facing. Their shared location hides that difference. | `investigate`: read-only consumer map of `_append_session_index()` is the one focused-review candidate. |
| Contract, policy, and decision context | lines 175–571 | runtime policy context, risk/oversight classification, memory eligibility | **None at subfamily level** in this census. | Largest pre-orchestration cluster; it gives reviewers reasons and state, but its outputs are still mostly technical fields. | `keep_observe`: do not split or alter without policy/decision evidence. |
| Memory candidate and promotion lifecycle | lines 572–641 plus daily-memory helpers at 260–333 | memory snapshots, promotion policy, canonical daily-memory record | **Not separately measured.** Memory records support continuity, but this tranche found no attribution from one helper to a later owner decision. | Medium coupling: candidate detection, promotion, and daily memory are distinct concepts but coordinate through one session-end path. | `keep_observe`: memory-authority changes need their own protocol and focused evidence. |
| Verdict, trace, and runtime evidence artifacts | lines 642–828 | verdict JSON, failure trace, runtime trace, phase summary | **None at subfamily level.** Parent closeout consumption does not prove each artifact has a reader. | This is where evidence is emitted for reviewers; artifact names are machine-oriented and need a higher-layer summary for non-engineers. | `keep_observe`: inventory readers before judging duplicate/noisy artifacts. |
| Final orchestration and canonical closeout coordination | lines 829–1229 | candidate/curated/summary/verdict/trace artifacts; canonical closeout; claim packet | **Observed at parent closeout-chain level.** The census records downstream F-7/P1-C consumption of canonical closeout evidence, but does not attribute that use to every write in this block. | High integration risk: this is the only subfamily that binds all paths together. Its canonical-closeout call is required before artifact writing; it is not a removable wrapper. | `keep`: retain coordination. Any change requires the closeout contract and focused regression evidence. |
| Human result formatting and CLI | lines 1230–1366 | CLI response lines for operators and scripts | **None separately observed** in this census. | It exposes raw fields with some compact summaries; it is a projection, not the complete human-understanding layer. | `keep_observe`: assess only after a concrete operator comprehension failure identifies a missing or misleading field. |

## What the map changes

The observed parent-level closeout value supports the canonical coordination
role, but it does **not** justify calling all other subfamilies decision
changing. The only low-cost follow-up candidate exposed by this map is the
session-index cache path, because its own documentation explicitly says it is
not authoritative. That is an `investigate` candidate, not a retire candidate:
a reader/caller inventory and a safety review are still required.

No extraction is proposed. Moving code solely because the file is large could
make evidence ordering and failure behavior less understandable without
reducing governance overhead.

## Existing test visibility

`tests/test_runtime_session_end.py` covers low-risk promotion, no-ledger mode,
memory modes, contract-field failure, evidence summaries, human output,
forced runtime failure, replay, and classification transitions. Together with
`tests/test_canonical_closeout.py`, the focused suite passed 48 tests in this
tranche. This demonstrates exercised paths, not complete subfamily-level
decision effect or removal safety.

## Claim ceiling

This is a responsibility map and prioritization aid. It does not prove any
subfamily is redundant, noisy, safe to extract, or safe to retire. It does not
prove closeout artifacts are human-readable, nor does it alter F-7/P1-C
completion or evidence semantics.
