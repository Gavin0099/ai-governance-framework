# Memory replacement semantic-fidelity finding — 2026-08-30

Status: **SESSION-REPORTED OPERATIONAL FIDELITY FAILURE / OWNER-ADOPTED RETRY
BOUNDARY / CUTOVER RETRY REQUIRES SEPARATE AUTHORIZATION**

This finding records the authoring session's report that a bounded manual
verified-archive plus replacement-state cutover failed semantic-fidelity review,
plus the owner-adopted boundary for any later retry. Current repository evidence
independently establishes only the frozen identities and active/archive byte
equality described below; it does not reconstruct the rejected replacement or
review. This is an operational memory-cutover finding. It creates no Gate 3
validity requirement, changes no experiment criterion, moves no source of truth,
and authorizes no replacement retry.

## Problem

Archive byte equality and a passing memory workflow are necessary but not
sufficient evidence that a smaller active state is a faithful replacement. A
replacement can remain syntactically valid and operationally readable while it
omits an irreversible state declaration, upgrades a candidate's status, or
weakens a corrected claim ceiling. Any of those changes can alter a later
agent's decisions even when the replacement is shorter and all structural
checks pass.

## Current repository truth and exact identities

The current uncommitted manifest records the attempted cutover's source `HEAD`
as `6ca4800bf6259ffede7ee02e53a37d958a0e6a92`, with parent
`d84ebf8e9ee990bcc340a327d5e44f30706b7bd9`. Current repository `HEAD` and
parent independently match those values. This corroborates the recorded
identity, not the timing of the attempted operation.

The frozen predecessor was:

```text
path:              memory/01_active_task.md
SHA-256:           38680653be7302482a0736af7d2ab92a282bc3fa311362f7a56db90c04824d78
raw Git blob:      0ebf087ea6d6ddac4cc6362475401576a7bc2ce9
HEAD Git blob:     10b58d479ac1e2d29398f6a31c8a3600b0824ecf
bytes / chars:     11,447 / 11,435
LF / CR:           159 / 0
BOM / trailing LF: absent / present
pressure:          CRITICAL by character count
```

The authoring session reported that it created an exact-byte archive before
cutover at `memory/archive/active_task_20260830_021544.md`. Its current SHA-256,
byte count, character count, LF/CR state, BOM state, trailing-LF state and raw
Git blob independently match the current active file and recorded predecessor.
That equality corroborates content identity, not creation timing. The archive
currently remains untracked; its manifest entry currently remains an
uncommitted worktree change. Those facts do not make either artifact committed
authority. Byte equality preserves the old projection; it does not prove that
every statement in that projection is canonical or correct.

The rejected replacement was reported in the authoring session at:

```text
SHA-256:           70d81ebb6939102fb1554ad8efe9b9435c60bb1039133909288ea96d5af851a4
raw Git blob:      d38bcca8c7b3c9232ac3669c07589d9a1fa7777f
bytes / chars:     6,642 / 6,638
LF / CR:           117 / 0
BOM / trailing LF: absent / present
```

The replacement file itself and the complete fresh-review transcript were not
present among the scoped artifacts reviewed for this finding, and the recorded
replacement Git blob is not present in the current object database. The current
uncommitted
`memory/archive/manifest.json` records the replacement identity and metrics,
not its content or the review reasoning. This finding therefore records the
session-reported review disposition and recovery sequence; it does not claim
that the rejected replacement bytes, full reviewer response or command outputs
can be reconstructed from the repository.

## Session-reported failure and rollback

The authoring session reported that the replacement passed the direct
post-cutover operational checks that were run: the memory workflow and run
guard completed successfully, and the janitor classified the smaller active
projection as `SAFE`. A fresh hostile semantic reviewer in that session
nevertheless reported `CHANGES_REQUESTED / HIGH` for two blocking fidelity
failures and one warning:

1. **[BLOCKING]** The replacement upgraded the committed Release-Order design
   candidate from a proposal with bounded conditional claims into wording that
   treated it as established conditional proof. A replacement may preserve a
   pointer and its recorded disposition; it may not upgrade the authority or
   evidence maturity of the referenced artifact.
2. **[BLOCKING]** The replacement omitted the predecessor's irreversible
   declaration that the consumed Gate 3 A/B pair is `NON_SUCCESS`, cannot be
   reused, retried or replaced, and that credentials, preflight and live remain
   unauthorized. In the frozen archive this begins at
   `memory/archive/active_task_20260830_021544.md:24` under SHA-256
   `38680653be7302482a0736af7d2ab92a282bc3fa311362f7a56db90c04824d78`.
3. **[WARNING]** The replacement weakened the twice-corrected native-path claim
   ceiling. The frozen predecessor distinguishes objects N3c-2 creates from the
   borrowed `base` and its ancestors; the effective wording begins at
   `memory/archive/active_task_20260830_021544.md:114` under the same frozen
   archive identity.

The authoring session reported that no commit followed the failed review, that
recovery copied the already verified archive back to
`memory/01_active_task.md`, and that a post-recovery byte comparison restored
the exact predecessor identity. The current active file and frozen archive are
independently re-verifiable as byte-identical at the recorded SHA-256. That
present-state equality corroborates the reported rollback outcome; it does not
retain the copy operation itself or prove that a future replacement is
semantically faithful.

## Owner-adopted operational preservation invariant

The owner adopted the following boundary in the 2026-08-30 authorization chain
for this finding. It governs only any later separately authorized manual
replacement retry; it is not an empirical conclusion or advance authorization
for that retry.

Any later, separately authorized replacement-state candidate must preserve the
effective meaning and decision effect of every predecessor item in these three
classes:

1. **Irreversible state declarations** — terminal consumption, non-reuse,
   non-retry, non-replacement, revocation, or other state whose omission could
   restore authority that no longer exists.
2. **Effective claim ceilings** — the operative limitation together with any
   qualifier or correction needed to prevent a broader claim. A shortened
   sentence is unacceptable when it reintroduces an already corrected
   overclaim.
3. **Pre-existing authority references and recorded status** — exact identity,
   authority class, disposition and unresolved status needed to interpret a
   referenced artifact without promoting a candidate, observation or
   uncommitted projection into authority.

Permitted preservation modes are:

- verbatim preservation;
- an exact pointer to an already-existing canonical durable source established
  by evidence outside this finding; or
- a reviewed semantic equivalent whose decision effect is shown to be the
  same.

An exact pointer may refer only to authority that already exists. Inventory or
cutover work must not create a new authority source, relocate a source of truth,
or silently promote active-memory-only text. If an item's authority or durable
home is ambiguous, the item remains unresolved and cannot be omitted from the
candidate on the theory that it is merely historical.

## Required preservation matrix for any later retry

Before any later active-state write, a manual preservation matrix must identify
at least:

| Field | Required evidence |
| --- | --- |
| predecessor item | exact text anchor and frozen predecessor identity |
| class | irreversible state, effective claim ceiling, or authority reference/status |
| preservation mode | verbatim, exact existing pointer, or reviewed semantic equivalent |
| replacement location | exact candidate anchor or pointer target |
| authority effect | unchanged; unresolved ambiguity stated rather than dispositioned |
| review result | fresh reviewer disposition with every required row checked |

The candidate author cannot self-certify the matrix as `PASS`. Structural
checks, archive equality, pressure reduction and a passing memory guard do not
substitute for this semantic review.

## Failure paths and stop rule

- If the verified archive or matrix is incomplete before cutover, do not write
  the active state.
- If any post-cutover recovery, authority-reference or semantic-fidelity check
  fails, restore the predecessor from the verified byte-identical rollback
  archive identified by the frozen digest and manifest, then verify exact-byte
  equality before stopping.
- Owner-adopted stop rule: only one further replacement candidate may be
  attempted by this manual compression/cutover method, and only under separate
  owner authorization. If that candidate receives a semantic-fidelity blocking
  finding, do not start a third same-method revision loop. Stop and evaluate
  durable-state versus retrieval-index separation as a distinct architecture
  decision.
- A failure does not authorize automatic archive, pointer migration, authority
  promotion, active-memory freeze, tool redesign, or Gate 3 work.

## Scope, affected surfaces and non-goals

This finding affects only the review and acceptance boundary for a future
manual replacement of `memory/01_active_task.md`. It records a session-reported
operational failure and an owner-adopted boundary because the checks reported in
that session did not detect the semantic loss later reported by the reviewer.
The only added governance surface is this documented manual operational
review-and-acceptance boundary for a separately authorized retry.

It does not:

- change `memory/01_active_task.md`, its archive, or its manifest;
- commit or bless the current partial archive artifacts;
- define which predecessor items are canonical authority versus projection;
- perform the Historical/Future Authority-Freeze Audit;
- move irreversible state, claim ceilings or authority references to another
  file or storage system;
- add a schema, validator, automated/runtime gate, hook, automation or memory
  lifecycle mechanism;
- authorize a cutover retry, memory cleanup or active-summary write freeze;
- create or modify any Gate 3 validity predicate, evidence standard, PLAN text,
  preregistration, rev9 disposition or Release-Order claim; or
- authorize provider feasibility, implementation, network, rehearsal, counted
  execution, visualizations work, push or unrelated dirty-work cleanup.

## Evidence and re-evaluation plan

The smallest next evidence step, if separately authorized, is a read-only,
item-level placement inventory of the frozen predecessor. It should distinguish
existing canonical pointers from active-memory-only structural debt and from
episodic history without deciding ambiguous authority. That inventory can test
whether a final bounded replacement attempt is worthwhile; it is not itself an
authority migration or cutover authorization.

Re-evaluate this finding only after a later reviewed and committed cutover
contract or implementation supersedes the manual preservation boundary. Until
then, it remains evidence that successful archival and structural validation
do not establish replacement semantic fidelity.

## Claim ceiling

This document claims only that the authoring session reported the described
semantic-fidelity failure and rollback sequence, that the current active file
and frozen archive are independently re-verifiable as byte-identical, and that
the three preservation classes above are mandatory under the owner-adopted
boundary for any separately authorized manual retry. It does not claim that
the rejected replacement or full review transcript is recoverable, that every
predecessor item has been classified, that a safe replacement exists, that
memory pressure is resolved, or that Gate 3 has advanced.
