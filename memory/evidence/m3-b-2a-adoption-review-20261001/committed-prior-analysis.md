# Current-state claim verification — contract

> **Status**: ADOPTED by owner decision. No governance document, validator, hook,
> gate, schema or memory writer changes because of this document.
> **Date**: 2026-09-13
> **Adopted**: 2026-09-13
> **Re-adopted**: 2026-09-14 (`e33ea9d4`); 2026-09-14 (`32393197`)
> **Baseline**: `main` at `75578e50`
> **Reviewed adoption input**: commit `32393197aff213abd470b41ac1a6e27ee47f2322`,
> blob `32219e1ef96a8abac4ca33309a4c3cf0202aca65`
> **Previous adopted identity**: commit `e33ea9d4e4d621d065b35654270c65b0f9e08e6b`,
> blob `6361296dc725c3ce2d4938a9e1dfc3383125753d`
> **Previous reviewed candidate**: commit `0a3c101bb2ddfd1235bc7681247b7dd0dcbff6a5`,
> blob `7ad0c0b5c63a731f619f4e5e8cd6ee19a4db29d5`
> **Previous path**: `docs/governance/current-state-claim-verification-candidate-20260913.md`

## Correction note

Correction from previous reviewed candidate `0a3c101b`: the staging restriction
previously used in paper replay B was traced to a separate local-branch memory
surface and did not establish authority or applicability. The actual staging
decision had independent human authority. After referent requalification, the
Instance B state-claim verdict remains the same; the evidentiary basis is now
explicit.

Provenance correction after adoption at `8838027b`: `5c5601a1` and `dc66e923`
are unpublished local commits. They are marked as provenance locators only: they
are not required to be fetchable and carry no authority. Case 8b remains `REAL`,
because its material was actually observed during qualification, and is
qualified `RECORDED-ONLY`, because that material is not independently
retrievable from this repository. The rule, the claim classification, the
acceptance cases and their verdicts are unchanged.

Semantic amendment after re-adoption at `e33ea9d4`: a selected ref is movable, so
it is now resolved once to an immutable commit OID, and every subsequent check
uses that OID. Remote-current freshness is scoped to the moment of resolution.
This changes step 2 of the rule, the current-evidence table and its guidance, and
the replays of cases 6 and 7. Every case verdict is unchanged.

## The question this answers

Not "how do we keep memory fresh?" but:

> Before a claim about the repository's **current state** influences a decision,
> how do we verify that claim against evidence bound to the selected current
> identity and scope?

Recency is not the property that makes such a claim trustworthy. One of the two
reproduced instances below was wrong on the day it was written.

## Problem

Memory, ledgers and historical evidence all carry claims about current state.
The reproduced evidence shows three observed failure properties across two
instances. A fourth failure mode is structurally argued but not yet reproduced.

| | Failure property | Evidence |
|---|---|---|
| A | Once true, now stale | observed in instance B |
| B | Contradicted by newer information in the same surface | observed in instance B |
| C | Derived incorrectly from the beginning | observed in instance A |
| D | Historical evidence not bound to the selected current anchor | argued, not reproduced |

A and B co-occur in instance B; they are not independent reproductions.

C is the reason a freshness mechanism is insufficient: a claim that was never
true does not become true by being recent, and does not become false by ageing.

## Reproduced instances

### Instance A — an incorrect derived claim

`memory/01_active_task.md` at `75578e50`, under Open Risks:

> `memory/03_knowledge_base.md` states a 14-day PLAN freshness threshold while
> `governance_tools.plan_freshness` reports a 7-day Sprint policy. Unresolved.

Checked against evidence at `75578e50`:

| Source | Content |
|---|---|
| `PLAN.md` header | `Freshness: Sprint (7d)` — threshold 7 |
| `governance_tools/plan_freshness.py` | `POLICY_DEFAULTS = {"sprint": 7, ...}`; `2 = CRITICAL (距今 > 2× threshold)` |
| `memory/03_knowledge_base.md` | "more than 14 days old → `CRITICAL`" |

There is no conflict. 14 days is exactly the CRITICAL boundary under a 7-day
threshold. The knowledge-base statement is correct. The memory entry read a
CRITICAL boundary as a competing threshold and recorded the result as an
unresolved risk.

Corroborated live: this repository's pre-commit hook reported
`PLAN.md 已 8d 未更新（閾值: 7d）` — STALE at 8 days, not CRITICAL, exactly as a
7-day threshold with a 14-day CRITICAL boundary predicts.

**Status**: decision-capable false claim = YES. Actual wrong decision caused =
NOT PROVEN. No reconciliation task was created from it.

### Instance B — a stale state claim, self-contradicted

Same file, two lines:

- line 61: "M3-b-2A remains implemented but **uncommitted** in six scoped files"
- line 139: "M3-b-2A **merged by PR #108** at `a59b0aef`"

"Uncommitted" is a predicate whose natural scope is one checkout's local state.
Canonical merge evidence alone cannot refute a claim that some checkout still
holds uncommitted changes, so the referent of line 61 is established before any
verdict is drawn.

**Referent.** Line 61 records a focused plus M1-adjacent result of 291 passed.
The test receipt shipped in PR #108,
`artifacts/evidence/test-results/m3b2a-in-process-20260820.json`, records 291
passed on 2026-08-20 for a test set that includes
`test_gate3_historical_process.py`, and links base commit `e03afc85`, in which
neither `gate3_historical_process.py` nor its test module exists. Both files
first appear on any ref in `ff9cdb77`, "checkpoint M3-b-2A transport". That
commit, which `origin/main:PLAN.md` names as the implementation commit of PR #108,
changes nine files: `.gitattributes`, the two receipt artifacts, and six files
under `gate3-route-v2` — `gate3_historical_child.py`,
`gate3_historical_materialize.py`, `gate3_historical_process.py` and their three
focused test modules. The receipt's remaining test module,
`test_gate3_historical_bootstrap.py`, is not among them. Line 61 therefore
describes the M3-b-2A implementation checkpoint, those six files. This
identification is itself a derived inference; every premise it rests on is
committed evidence.

An uncommitted local review-log entry names the same six-file allowlist. It
exists only in one local working tree and has never been committed on any ref,
so it is cited as corroboration only, not as authority.

**Verdict.** Checked against a selected anchor: `origin/main`, fetched in-session
and resolving to `75578e50`. `ff9cdb77` and the PR #108 merge `a59b0aef` are
both contained in that anchor, and all six scoped files are present at it. The
implementation line 61 describes is committed. The underlying checkpoint state
was true at the 2026-08-20 receipt: the scoped implementation had not yet been
committed. Once `ff9cdb77` was committed, that state ceased to be current. The
stale wording was present in the 2026-08-30 cutover, the earliest committed
history in which it can be found. It contradicts line 139, which concerns the
same implementation.

**Status**: reproduced staleness and self-contradiction, with the referent
established from committed evidence. No wrong decision demonstrated.

### Related prescriptive requalification — a real negative example

This is a separate surface with its own authority chain. It is not part of
Instance B and inherits nothing from it.

A restriction was cited for a staging decision in the working session that
examined Instance B:

> the existing M3-b-2A `PLAN.md` hunk is not authorized for staging, cleanup, or
> reconciliation here.

It appears in `memory/01_active_task.md` on the local branch
`feat/gate3-historical-materialization`, first committed in `5c5601a1`, a local
compaction commit; before that it existed only as uncommitted working-tree
content. It has never been on `origin/main`, and `origin/main`'s copy of the same
file does not contain it.

`5c5601a1` is an unpublished local historical commit, cited as a provenance
locator only. It is not required to be fetchable and carries no authority. What
was observed during qualification is recorded here: the source path and branch
above, the restriction's text as quoted, and the applicability findings below.
This is a record, not independently reproducible evidence; the case is
`RECORDED-ONLY`.

| Factor | Finding |
|---|---|
| Authority | **Not established.** The surface declares itself "a retrieval index, not normative authority". `MEMORY_PROTOCOL` states that current authorization comes "from current human instruction or an approved change, never from memory or PLAN alone". No decision or review record creating the restriction was found in this checkout's `memory/` or `docs/`. |
| Subject | **Imprecise.** It names one hunk; the local `PLAN.md` diff holds eighteen, two of which mention M3-b-2A, and the session applied it to all eighteen. |
| Scope | **Not established as current.** "Here" is the Gate 3 replacement-preparation slice that file describes; that branch's delivery, PR #155, merged on 2026-09-08. |
| Conditions / expiry | None stated. |
| Supersession | **Subject content superseded.** The local hunks describe M3-b-2A as implemented "only ... in the working tree"; `origin/main:PLAN.md` records that it "was merged by PR #108" (implementation `ff9cdb77`, merge `a59b0aef`). |
| Revocation | None recorded. |

**Result**: `NOT APPLICABLE`. The restriction does not establish applicability.

This is an observed provenance and equivalence failure, and it supports the
general identity/scope concern. It is **not** an exact match for failure mode D,
which remains argued and not reproduced.

## Claim classification, at consumption time only

Claims are read on two independent axes. A single flat list of classes conflates
them: "PR #108 merged at `a59b0aef`" is both historical and directly observed,
while "therefore the feature still exists" is about current state and derived.

**Target** — what the claim is about:

| Target | Example |
|---|---|
| `CURRENT_STATE` | "M3-b-2A remains uncommitted" |
| `HISTORICAL` | "commit `ff9cdb77` introduced the M3-b-2A implementation" |
| `PRESCRIPTIVE` | "an approved decision forbids staging file F during slice S" |

**Form** — how the claim was arrived at:

| Form | Example |
|---|---|
| `DIRECT` | the `PLAN.md` header reads `Sprint (7d)` |
| `DERIVED` | "14d and 7d disagree, therefore an unresolved risk exists" |

What each combination requires:

```text
CURRENT_STATE + DIRECT   -> verify against current evidence
CURRENT_STATE + DERIVED  -> verify against current evidence,
                            and additionally revalidate the inference
HISTORICAL + DIRECT      -> verify historical authority
HISTORICAL + DERIVED     -> verify historical evidence,
                            and additionally revalidate the inference
HISTORICAL -> CURRENT_STATE
                         -> bind the history to the selected anchor;
                            ancestry proves the history is contained,
                            not that its effect persists;
                            the CURRENT_STATE conclusion still needs
                            current verification
PRESCRIPTIVE             -> verify authority, subject, scope, conditions,
                            expiry, supersession and revocation,
                            not current-state freshness
```

When a `HISTORICAL` claim is used to support a `CURRENT_STATE` conclusion,
binding the historical evidence to the selected anchor establishes only that the
referenced history is contained in that anchor. It does not establish that the
historical effect still holds. Any `DERIVED` inference must be revalidated, and
the resulting `CURRENT_STATE` conclusion must be verified against evidence scoped
to the selected current-state anchor.

Both axes are applied when a claim is **read and about to be used**. They are
deliberately **not** a memory authoring schema. No `claim_type` field, no schema
version bump, no writer-side classification, no validator. One clean instance of
a mis-derived claim does not justify a migration and a permanent maintenance
burden.

A `PRESCRIPTIVE` claim is not invalidated merely because surrounding state
changes. Its applicability is determined by its authority, subject, scope,
conditions, expiry, supersession and revocation status — each of these
dimensions must be checked, not only whether its subject still appears to
exist. The related prescriptive
requalification above is a real case in which a restriction looked applicable
from subject existence alone and failed on authority and supersession.

## Current observable evidence, with scope

"Current observable evidence" is not a synonym for "current source". Each source
answers a different question and must carry its scope:

| Evidence | Scope it establishes |
|---|---|
| `git rev-parse <selected-ref>^{commit}`, run once | the immutable commit OID of the current-state anchor, `<anchor-oid>` |
| `git show <anchor-oid>:<path>` | content of that file at the anchor commit |
| `git merge-base --is-ancestor X <anchor-oid>` | whether historical commit X is contained in the anchor commit |
| PR state (open / merged / current head) | remote pull-request lifecycle state, as reported at query time |
| current configuration files | declared policy, not effective behaviour |
| working-tree diff / status | **local, uncommitted** state of one checkout only |
| runtime output | behaviour of the code as actually executed, in that environment |

`origin/main` establishes the **locally known remote-tracking state**. It
establishes remote-current main only when the freshness of that ref has
separately been established. Verifying a claim against a stale remote-tracking
ref and reporting the result as current state would reproduce the very failure
this contract addresses. A fetch is not always required; claiming more scope than
the evidence supports is never allowed.

**Resolve the anchor once.** A selected ref such as `origin/main` is movable: a
concurrent fetch or commit can advance it between two commands. Resolve it once
to an immutable commit OID and run every subsequent check against that OID, never
against the ref again. Reporting one resolution as the anchor's identity while
inspecting content or ancestry through a later resolution binds the claim to a
commit that was not inspected.

The OID is a fixed snapshot. A claim that the evidence reflects remote-current
state requires freshness to be established at the moment the OID is resolved.
When the ref moves afterwards, the evidence keeps its identity but is no longer
remote-current: it is evidence about that commit, not about the ref.

Two further consequences:

- A working-tree observation is never automatically canonical. It describes one
  checkout, possibly dirty, possibly not the pushed subject.
- Historical evidence becomes usable toward current state only once it is
  **bound to the selected current anchor**. The defect is unbound history, not
  history. `git merge-base --is-ancestor X <anchor-oid>` is historical evidence
  that is usable for exactly what it establishes — that X is contained in the
  anchor — and not for whether X's effect survives later commits.

## The rule

```text
For establishing CURRENT repository state, a claim from memory, a ledger, or
unbound historical evidence is context until it is verified against evidence
bound to the selected current-state identity and scope.

When such a claim is about to influence a decision, task, finding, remediation
or implementation:

  1. classify the claim on both axes: target and form
  2. resolve a selected current anchor once to an immutable commit OID, and
     verify the claim against evidence bound to that OID, stating the OID and the
     freshness actually established when it was resolved
  3. only then let it carry the decision

Current evidence validates premises. A CURRENT_STATE + DERIVED claim
additionally requires the inference itself to be revalidated: each premise, the
semantic relationship asserted between them, and the conclusion.
```

This rule governs current-state claims only. A ledger remains authoritative for
why an option was rejected, and history remains authoritative for what was true
at a past revision.

## Verification is decision-bound, not session-bound

Re-verifying every current-state claim on every session start would be
expensive and would become the ceremony this work exists to reduce.

```text
claim seen while reading            -> context, no verification owed
claim about to change what is done  -> verification required before acting
```

Reading "Open Risk: freshness policy conflict" costs nothing and requires
nothing. Preparing to open a reconciliation task, amend the policy, edit
`plan_freshness.py`, or file a finding from it is the point at which
verification becomes mandatory.

## Preserved from the rejected alternative

Carried forward from the earlier candidate `dc66e923`, whose reasoning survives
its own supersession:

1. Stale memory cannot stand as current state.
2. Historical evidence does not automatically represent current state either.
   Rejecting memory in favour of history swaps one stale authority for another.
3. `git show` exposing source does not make current source untrustworthy; the
   interface is not the problem.
4. Current-source evidence must itself carry verifiable identity and scope.
5. Finding is not task.

The earlier proposal to forbid source inspection and permit only PLAN, memory
and Git metadata is **rejected and must not be re-proposed**: `git show <commit>`
already renders source, so removing the permission hides the access rather than
removing it, and a rule permitting commit history while forbidding current
source produces the symmetric failure — a commit that claims to add a safeguard
does not prove the safeguard survives today.

`dc66e923` is an unpublished local commit holding the rejected candidate, cited
as a provenance locator only. It is not required to be fetchable and is not
current authority. The reasoning carried forward from it, and the reason its
proposal was rejected, are stated in full above.

## Non-goals

- Not a memory freshness mechanism, and not a replacement for one.
- Not a memory authoring schema, `claim_type` field, or writer change. The two
  classification axes exist only at consumption time.
- Not a universal evidence precedence order. This governs current-state claims
  only.
- Not a requirement to fetch before every verification.
- Not a change to pre-push subject binding, the version-bump advisory, the
  runtime-smoke semantics, or npm tool-version binding.
- Not a new gate, validator, registry, daemon or runtime component.
- Does not authorize re-verifying all memory at session start.

## Paper replay

**Instance A.** The Open Risk is `CURRENT_STATE` + `DERIVED`. Nothing is owed
while merely reading it. At the point of opening a reconciliation task, the
inference is revalidated: premise 1 (the knowledge base says 14 days) holds;
premise 2 (the code uses a 7-day sprint threshold) holds; the asserted semantic
relationship — that 14 is a competing threshold — does **not** hold, because 14
is `2 ×` the threshold and names the CRITICAL boundary; the conclusion therefore
fails. No task is created. Verifying only that both numbers appear would have
confirmed the false claim, which is why premise-checking alone is insufficient
for a derived claim.

**Instance B.** Line 61 is `CURRENT_STATE` + `DIRECT`. Its predicate,
"uncommitted", is naturally checkout-scoped, so its referent is established
first: the M3-b-2A implementation checkpoint, identified from the committed
PR #108 receipt and the commit that first added the scoped files. Verified
against the selected anchor — `origin/main`, fetched in-session, `75578e50` —
that implementation is committed, so line 61 is false for its referent. Line 139
is `HISTORICAL` + `DIRECT`; bound to that anchor, `merge-base --is-ancestor` and
PR state confirm the merge occurred. Result: the stale current-state claim cannot
carry a current decision.

**Related prescriptive requalification.** The local-branch restriction was
examined separately. It does not inherit authority from Instance B, nor from
memory merely because it appears in memory. Full applicability review rejects
it: authority not established, subject not precise enough, governing slice not
established as current, subject content superseded on main. The actual staging
decision remains independently supported by the owner's current in-chat
instruction, which authorized exactly two `PLAN.md` hunks and forbade staging,
modifying, cleaning or reconciling any other. A correct decision does not
validate the governance basis originally cited for it.

## Adoption acceptance cases

This contract may be adopted only after each case below has been evaluated at
the contract level and the rule yields the expected result.

These are paper-level acceptance cases for the contract semantics. They answer
whether the rule, applied to a given situation, reaches the correct verdict.
They do not require a validator, hook, runtime gate, memory schema, test harness
or any other executable governance mechanism to exist.

This is a correction of the test level, not a waiver. The earlier wording left
the qualification level ambiguous and could be read as requiring executable
machinery that the current evidence does not justify. This amendment makes the
intended qualification level explicit. Contract acceptance and implementation
conformance are separate qualifications.

If an executable implementation of these semantics is introduced later, that
implementation requires its own conformance tests against these semantics.
Adoption of this contract does not qualify any future implementation.

**Stop condition.** If every case below is decidable and passes, that result
must not be used as a reason to build a test harness, validator, hook or gate.

Evidence basis is labelled per case. `REAL` means the case is evaluated on
material observed in this repository. `CONSTRUCTED` means the premises are
stated for the purpose of the evaluation. A constructed case is not a reproduced
incident and must not be cited as one.

`RECORDED-ONLY` qualifies a `REAL` case whose original source is not
independently retrievable from this repository. The case records material
actually observed during qualification, but the record is not a substitute for
the source: it must not be cited as repo-reproducible evidence or as independent
audit proof.

| # | Case | Claim | Evidence basis | Verdict |
|---|---|---|---|---|
| 1 | Confirmed direct claim carries a decision | `CURRENT_STATE` + `DIRECT` | `REAL` (instance A material) | PASS |
| 2 | Stale memory does not override newer direct evidence | `CURRENT_STATE` + `DIRECT` | `REAL` (instance B) | PASS |
| 3 | Unbound history does not establish current state | `HISTORICAL` -> `CURRENT_STATE` | `CONSTRUCTED` | PASS |
| 4 | Incorrect derived claim rejected though every premise holds | `CURRENT_STATE` + `DERIVED` | `REAL` (instance A) | PASS |
| 5 | Dirty working tree is not canonical current state | `CURRENT_STATE` + `DIRECT` | `CONSTRUCTED` | PASS |
| 6 | Stale remote-tracking ref not reported as remote-current | `CURRENT_STATE` + `DIRECT` | `CONSTRUCTED` | PASS |
| 7 | Ancestry does not prove a historical effect persists | `HISTORICAL` + `DERIVED` -> `CURRENT_STATE` | `CONSTRUCTED` | PASS |
| 8a | Valid prescription survives a surrounding state change | `PRESCRIPTIVE` + `DIRECT` | `CONSTRUCTED` | PASS |
| 8b | Prescription without established authority is not applicable, though its subject appears to exist | `PRESCRIPTIVE` + `DIRECT` | `REAL`, `RECORDED-ONLY` (observed during qualification; original source `5c5601a1` unpublished; not independently reproducible from this repository) | PASS |
| 9 | Reading a claim without acting on it owes no verification | any | `CONSTRUCTED` | PASS |

### Case replays

**1.** Claim: the knowledge base states that more than 14 days without a PLAN
update yields `CRITICAL`. About to be used to judge PLAN urgency. Verified at the
selected anchor against `plan_freshness.py` (`sprint: 7`, CRITICAL above `2 ×`
threshold) and the `PLAN.md` header (`Sprint (7d)`). Confirmed; the claim may
carry the decision. Expected: carries. Result: carries.

**2.** Claim, memory line 61: the M3-b-2A implementation remains uncommitted.
Before any verdict, the referent is established from committed evidence as the
M3-b-2A implementation checkpoint, the six scoped files, not the local state of
some checkout. Newer evidence bound to the selected anchor (`origin/main`,
fetched in-session, `75578e50`): `ff9cdb77` and `a59b0aef` are contained and all
six files are present. Expected: memory does not override. Result: line 61
rejected for that referent. Had the referent been one checkout's local diff,
anchor evidence alone would not have sufficed; working-tree evidence for that
checkout would have been required.

**3.** Given: memory states "safeguard Y was added in commit X"; no anchor is
selected and no containment check is performed. Claim used to conclude Y exists
now. Rule: unbound historical evidence is context until bound to the selected
anchor, and binding proves only containment. Expected: no current-state
conclusion. Result: none reached; the decision is not carried.

**4.** Instance A. Premises hold (14 days in the knowledge base, 7-day sprint
threshold in code); the asserted relationship, that 14 is a competing
threshold, fails because 14 is `2 ×` the threshold. Expected: rejected despite
true premises. Result: rejected; no reconciliation task.

**5.** Given: the selected anchor's `PLAN.md` contains text A; a local dirty
checkout's `PLAN.md` contains A plus uncommitted text B. Claim: "B is canonical
current state", read from the working tree. Rule: working-tree evidence
establishes the local uncommitted state of one checkout only. Expected: reject.
Result: rejected. The working tree establishes only local state; content at the
selected anchor must be checked separately.

**6.** Given: `origin/main` last fetched at an unknown or old time, resolving to
commit C. Claim "main currently contains S" verified by resolving `origin/main`
once to C and running `git show C:<path>`. Rule: `origin/main` establishes locally
known remote-tracking state; remote-current only when its freshness is separately
established. Expected: not reported as remote-current. Result: the conclusion is
limited to "at locally known `origin/main` = C"; no fetch is mandated, but the
remote-current scope is not claimed. If a concurrent fetch then advances
`origin/main` to D, the checks already run remain bound to C, and the conclusion
is still stated for C, not for D.

**7.** Given: memory states "commit X added safeguard Y, therefore Y is
present". X is an ancestor of the anchor; a later commit Z, also an ancestor,
removed Y. Rule: ancestry proves containment, not persistence; the derived
inference is revalidated; the current-state conclusion is verified against
`git show <anchor-oid>:<path>`, which shows Y absent. Expected: conclusion
fails. Result: fails.

**8a.** Given: an approved decision, still in force, forbids staging file F
during slice S; slice S is current; F still carries uncommitted changes; since
the decision, unrelated repository state has changed — other files merged, main
advanced. Rule: applicability depends on authority, subject, scope, conditions,
expiry, supersession and revocation. Expected: still applicable. Result: authority
established by the approved decision, subject present, scope current, no expiry,
supersession or revocation; applicable. The surrounding state change alone does
not invalidate it.

**8b.** The local-branch restriction at `5c5601a1`, examined in the related
prescriptive requalification. Its subject appears to exist: local `PLAN.md` hunks
mentioning M3-b-2A are present. Applied in full, the rule finds authority not
established, subject imprecise, scope not established as current and subject
content superseded on main. Expected: not applicable despite apparent subject
existence. Result: not applicable. The staging decision it was cited for was
correct on the independent authority of the owner's in-chat instruction.
The case is evaluated on the restriction text and applicability findings
recorded in this document; `5c5601a1` locates their source and is not required
to be fetchable. The case is `RECORDED-ONLY` and must not be cited as
repo-reproducible evidence or as independent audit proof.

**9.** Given: an agent reads the Open Risks section while loading context and
takes no action derived from it. Rule: verification is owed only when a claim is
about to change what is done. Expected: no verification owed. Result: none owed.

### Residual observations, not blockers

Every listed case is decidable. Three boundaries are not defined by the contract
and are recorded here without being resolved:

- **What establishes freshness** for a remote-tracking ref. Case 6 tests only the
  negative direction, which is decidable; the positive direction — what evidence
  suffices to claim remote-current — is unspecified.
- **Where "about to change what is done" begins.** Case 9 covers pure reading. A
  borderline act, such as repeating a claim in a status report, is not
  classified.
- **Prescriptions with established authority but no stated subject or scope.**
  Case 8b is decidable because authority fails before subject precision matters,
  and case 8a states its subject and scope explicitly. A prescription whose
  authority is valid but which names no subject or scope gives the applicability
  check nothing to evaluate.

## What this contract does not establish

- That either instance caused a wrong decision. Neither did.
- That failure mode D occurs in practice. It is argued from structure, not
  reproduced.
- That the cost of decision-bound verification is lower than the cost it avoids.
  Not measured.
- That this generalises beyond current-state claims.
