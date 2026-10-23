# Claude closeout authorization gate — design candidate 2026-10-23

Status: **DESIGN CANDIDATE / UNREVIEWED**. Scope only. No implementation is
authorized by this document, and nothing below has been built or validated.

Issue: #233, Tranche 2. Depends on Tranche 1 (#237, currently BLOCKED on P1-a).
Related: #236 (Tranche 1 spec), #231/#232 (not modified).

## Problem

Tranche 1 moves the evidence path: a Claude session can produce a release proof
R2 accepts. It deliberately contains **no authorization gate**. Nothing in it
establishes that the user asked session A to close out, so today the distinction
between these two is invisible to the system:

- session A saved a checkpoint and something invoked the release path;
- the user explicitly asked session A to close out.

Both arrive as a call with a legal `trigger_mode`. **A legal `trigger_mode` is
not an authorization.** Treating Tranche 1's `wrapper` receipt as sufficient
would be renaming the rejected `manual_fallback` and keeping its actual defect:
no evidence that anyone with authority asked.

## What this gate cannot be — read this before the design

Nothing in this runtime can distinguish a user-typed command from an
agent-issued one. Both are process invocations on the same machine with the same
write surface. Therefore:

- This gate is **not authentication**. It cannot prove who called it.
- This gate is **not anti-forgery**. A hostile local writer who can write the
  repository can write anything this gate reads.
- The session transcript **cannot be the authority source**. Tranche 1's
  snapshot carries `AUTHORITY = {source_semantics: sessionend_observed_snapshot,
  completeness: unqualified, decision_authority: none}`. Using it as
  authorization would contradict a constant the same path preserves verbatim.
  It may serve as *corroborating evidence*, never as the predicate.

What it **can** be: a conjunctive, evidence-bound predicate that makes an
unauthorized release impossible to perform **silently**. Every release names the
exact attestation it consumed; an attestation binds the exact session,
generation and summary bytes; anything missing or mismatched fails closed with
no side effects. That is a non-repudiation and non-silence boundary, and the
document must not claim more.

This framing is not new here. `governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md`
already separates "an authenticated owner action can prove who performed the
merge" from "it does not retroactively prove that the pre-merge attestation
predicate was satisfied". The same separation applies to closeout.

## Target outcome

> The user explicitly asks Claude A to close out. The system records an
> attestation bound to that exact session, generation and summary, validates the
> Tranche 1 evidence, releases ownership once, and names the attestation it
> consumed. Claude B then acquires ownership.

Two acceptance properties, both required, neither sufficient alone:

- **No wrongful release.** No release without a current attestation bound to
  the exact owner generation and candidate bytes.
- **No permanent block.** A session whose attestation is missing, stale or
  malformed is not stuck. It can be re-attested, and recovery validation stays
  available. A gate that strands work is a failure, not a safe default.

## The predicate: owner closeout attestation

By direct analogy to the merge contract's owner attestation predicate.

The owner must make a **current, explicit human statement authorizing closeout
of the exact session and summary bytes**. It may be recorded in an authoring
session, an authenticated comment, or another durable surface that identifies
the target bytes.

An agent **must not infer** this attestation from:

- a checkpoint save, or the fact that a summary exists;
- a memory `next_step`, a PLAN item, or a general continuation instruction;
- "wrap up", "finish", or any instruction that does not name closeout;
- a governed lifecycle hook firing at session end;
- a legal `trigger_mode`, including `wrapper`;
- its own recommendation that closing out would be appropriate;
- the later fact that a release occurred.

That a release was performed can show *what* happened in an audit. It never
retroactively establishes that the attestation predicate was satisfied.

## Scope

1. An **attestation record** under `artifacts/runtime/closeout-intents/<sid>/`,
   published under the existing R2 exclusion and digest-bound like every other
   record in this area. Fields bind it to one exact state:
   `consumer_root`, `session_id`, `generation`, `candidate_identity`,
   `text_digest`, the quoted owner statement, where it was observed, `attested_at`,
   and `attestation_id` as the digest of the canonical bytes.
2. **Release consumes exactly one attestation.** The receipt records which
   `attestation_id` it consumed, so the pairing is auditable after the fact and
   an attestation cannot be consumed twice.
3. **Admission checks** in the formal closeout path: no attestation, a
   generation mismatch, a candidate or text-digest mismatch, a foreign session,
   or an already-consumed attestation each fail closed before any state change.
4. A **re-attestation path** so a stale or malformed attestation does not strand
   the session, and recovery validation remains reachable without one.

## Non-goals

- **Not authentication**, not identity proof, not anti-forgery. Stated above and
  repeated here because this is where the design will be over-read.
- **Not** using the transcript as the authority source.
- **Not** relaxing, renaming or re-qualifying `manual_fallback`. It stays
  rejected by both guards; an attestation does not resurrect it.
- **Not** automatic closeout at exit, and **not** wiring this to any lifecycle
  hook. #231/#232 already decided against automatic closeout, and a hook firing
  is explicitly excluded from the predicate.
- **Not** "release ownership without closing out". Still deferred, still a
  governance bypass shaped like a convenience.
- **Not** changing R2 release-proof requirements, the receipt schema's existing
  fields, or the ownership state machine.
- **Not** touching #231's or #232's file sets, and **not** Tranche 1's P1-a or
  P2-c, which have their own blockers.
- **Not** an attestation surface for other agents yet. Prove it for Claude
  first.

## Affected surfaces

Provisional, pending Tranche 1's own resolution:

- a new attestation module under `governance_tools/`
- the formal closeout entry (Tranche 2's CLI, not yet written)
- `artifacts/runtime/closeout-intents/<sid>/**`, a new runtime area
- the closeout receipt, gaining the consumed `attestation_id`
- `tests/` — a new negative-first module
- `docs/governance/` — this document

## Boundary and API considerations

- The receipt schema gains a field. That is a schema change and needs its own
  version handling; it must not be smuggled in as an optional key whose absence
  silently means "unauthorized release was fine".
- The attestation binds `generation`. This is what makes replay fail: an
  attestation for generation N cannot release N+1. It also means any legitimate
  re-preparation invalidates an outstanding attestation, which is correct and
  must be stated to the user rather than worked around.
- Binding `candidate_identity` and `text_digest` means the attestation
  authorizes **these summary bytes**, not "closeout in general". A summary
  rewritten after attestation requires re-attestation.
- The attestation area must follow the same `canonical()` path rules as the rest
  of R2: real files, no symlink or junction placement.
- Where the quoted statement is recorded, the record should carry a locator
  rather than only prose, so a reviewer can go look. The locator is evidence of
  where it was observed, not proof that it was said.

## Failure paths and risk points

- **Over-reading the gate** is the largest risk, and it is a documentation risk
  rather than a code one. If anyone treats a consumed attestation as proof the
  user authorized the release, the gate has made things worse by lending
  false confidence to the same unauthorized path. The claim ceiling section
  exists for this.
- **Stranding.** An attestation bound to a generation that has since advanced
  must produce a clear, actionable rejection and a re-attestation route, not a
  dead end. This is the acceptance property most likely to be missed, because
  tests naturally focus on wrongful release.
- **Attestation reuse** across sessions or generations. Bound fields plus
  single consumption address it; both need negative tests.
- **Partial evidence after a failed release.** A rejected attempt must not leave
  an artifact a later call can consume. Tranche 1's review showed that asserting
  rejection without asserting side-effect absence is not enough.
- **Agent self-attestation.** The predicate's anti-inference list is the control,
  and it is a rule, not a mechanism. Honest consequence: an agent that ignores
  the rule can still produce a well-formed attestation. The gate makes that act
  recorded and attributable; it does not prevent it.

## Evidence plan

Negative-first, and every case asserts **rejection plus side-effect absence** —
no release receipt written, no owner state change, no consumable residue. An
error code alone is not evidence of safety; that lesson came from Tranche 1's
review and applies here from the start.

| # | Case | Must hold |
| --- | --- | --- |
| A1 | release attempted with no attestation | rejected; owner unchanged; no receipt |
| A2 | attestation for generation N, owner at N+1 | rejected; no release; re-attestation possible |
| A3 | attestation already consumed | rejected; first release unchanged |
| A4 | attestation for a different session | rejected |
| A5 | attestation's `candidate_identity` does not match the current candidate | rejected |
| A6 | attestation's `text_digest` does not match the summary bytes | rejected |
| A7 | attestation bytes altered after publication | rejected |
| A8 | attestation present but Tranche 1 evidence invalid | rejected; attestation **not** consumed |
| A9 | checkpoint save alone | publishes no attestation; release path unreachable |
| A10 | governed hook firing at session end | does not constitute an attestation |
| A11 | `manual_fallback` with a valid attestation | still rejected by both guards |
| A12 | malformed or truncated attestation | rejected, not ignored |
| A13 | stale attestation then re-attestation | second attestation succeeds; session not stranded |
| A14 | recovery validation with no attestation | remains available |

Then the positive pair: the user attests, A releases once naming the consumed
`attestation_id`; B acquires with generation incremented.

A11 and A9/A10 are the regression guards for the two ways this work could
quietly become the thing it was meant to prevent.

## Implementation tranche recommendation

**Tranche 2a — attestation record and admission only.** The record, its
validation, the single-consumption rule, and A1–A14. No CLI, no receipt schema
change, no release wiring. This is testable against Tranche 1's admission layer
and proves the predicate before anything can act on it.

Tranche 2b — the receipt field and the release wiring, plus the positive pair.

Tranche 2c — the formal closeout CLI that a user actually invokes, using the
reviewed core rather than a second mechanism.

Tranche 3 — `manage_agent_closeout print-manual` points at the real entry.

Tranche 2a is `review-required` at minimum, and the claim ceiling should be
reviewed as carefully as the code, because the failure mode here is a true
statement read as a stronger one.

## Ordering and dependencies

This design does not depend on Tranche 1's P1-a: the authorization leg is
independent of envelope identity. It cannot be **verified end to end** until
P1-a lands, because no Claude request can be published until then.

So the honest ordering is:

```
#231 -> #232 (Claude root-bound identity; contains P1-a's fix)
      -> #237 P1-a unlock and re-review
      -> Tranche 2a..2c (this document)
      -> real Claude A/B handover acceptance
```

Tranche 2a can be written and reviewed in parallel with the first two steps.
Nothing in it should be claimed as working before the real handover acceptance
succeeds, and the product judgement stays unchanged until then: cross-session
memory is not a closed loop.
