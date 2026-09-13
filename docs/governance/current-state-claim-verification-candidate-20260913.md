# Current-state claim verification — candidate contract

> **Status**: CANDIDATE. Not adopted. No governance document, validator, hook,
> gate, schema or memory writer changes because of this document.
> **Date**: 2026-09-13
> **Baseline**: `main` at `75578e50`
> **Owner decision required before any of this is applied.**

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

Checked against a selected anchor: `origin/main`, fetched in-session and
resolving to `75578e50`. `a59b0aef` is an ancestor of that anchor, and PR #108
is reported merged on 2026-08-24 by the remote PR API. Line 61 is false about
that anchor, and the file carries no rule for deciding which of its own lines is
current.

**Status**: reproduced staleness and self-contradiction. No wrong decision
demonstrated.

## Claim classification, at consumption time only

Claims are read on two independent axes. A single flat list of classes conflates
them: "PR #108 merged at `a59b0aef`" is both historical and directly observed,
while "therefore the feature still exists" is about current state and derived.

**Target** — what the claim is about:

| Target | Example |
|---|---|
| `CURRENT_STATE` | "M3-b-2A remains uncommitted" |
| `HISTORICAL` | "commit `a59b0aef` introduced M3-b-2A" |
| `PRESCRIPTIVE` | "this `PLAN.md` hunk is not authorized for staging" |

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
conditions, expiry, supersession and revocation status. Instance B shows why the
distinction matters: the state line was stale while the staging restriction was
still applicable — but that restriction was still applicable because its own
subject and conditions still held, not because prescriptions persist until
someone withdraws them.

## Current observable evidence, with scope

"Current observable evidence" is not a synonym for "current source". Each source
answers a different question and must carry its scope:

| Evidence | Scope it establishes |
|---|---|
| `git show <selected-ref>:<path>` | content of that file at the exact locally resolved selected ref |
| `git rev-parse <selected-ref>` | exact commit identity of that current-state anchor |
| `git merge-base --is-ancestor X <selected-ref>` | whether historical commit X is contained in the selected anchor |
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

Two further consequences:

- A working-tree observation is never automatically canonical. It describes one
  checkout, possibly dirty, possibly not the pushed subject.
- Historical evidence becomes usable toward current state only once it is
  **bound to the selected current anchor**. The defect is unbound history, not
  history. `git merge-base --is-ancestor X <selected-ref>` is historical evidence
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
  2. verify it against evidence bound to a selected current anchor, stating that
     anchor's identity and the freshness actually established for it
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

**Instance B.**

*Actual session.* The staging decision was correct because the independently
applicable prescriptive constraint was still valid. This candidate was not in
force and receives no causal credit for that outcome.

*Paper replay.* Line 61 is `CURRENT_STATE` + `DIRECT`; line 139 is `HISTORICAL`
+ `DIRECT`; the staging restriction is `PRESCRIPTIVE` + `DIRECT`. Line 61 is
verified against the selected anchor — `origin/main`, fetched in-session,
`75578e50` — using `merge-base --is-ancestor` plus PR state, and is false for
that anchor. The staging restriction is checked for applicability rather than
freshness: its subject, the local unstaged `PLAN.md` hunks, is still present and
not contained in the anchor, so it still applies. Under this candidate, the
distinction between the stale state claim and the still-applicable prescription
would have been made explicit before the decision.

## Tests this candidate must pass before it is adopted

Not implemented here. Listed so that adoption is falsifiable.

- [ ] positive: a `CURRENT_STATE` + `DIRECT` claim confirmed by current evidence
      carries a decision
- [ ] negative: stale memory does not override newer direct evidence
- [ ] negative: unbound historical evidence does not establish current state
- [ ] negative: an incorrect derived claim is rejected even though every premise
      is individually true — instance A
- [ ] negative: a dirty working tree is not treated as canonical current state
- [ ] negative: a stale remote-tracking ref is not reported as remote-current
      state
- [ ] negative: a historical `DERIVED` claim does not establish `CURRENT_STATE`
      merely because its source commit is an ancestor of the selected anchor; a
      later change or revert must cause the current-state conclusion to fail
- [ ] a `PRESCRIPTIVE` claim is not invalidated by a state change alone, and is
      invalidated when its subject, scope, conditions, expiry, supersession or
      revocation status no longer supports it
- [ ] reading a claim without acting on it triggers no verification cost

## What this candidate does not establish

- That either instance caused a wrong decision. Neither did.
- That failure mode D occurs in practice. It is argued from structure, not
  reproduced.
- That the cost of decision-bound verification is lower than the cost it avoids.
  Not measured.
- That this generalises beyond current-state claims.
