# ADR-0002 — A session envelope is identity, not closeout obligation

Status: **Accepted (semantics only)** — owner ratified the three-state
definition and the error-code separation on 2026-10-27. **No implementation is
authorized by this record.** The code change, and the two questions listed under
"Deliberately not decided", each need their own authorization.

Date: 2026-10-27

Observed failure this record answers:
`Gavin0099/ai-governance-framework#256`, reproduced during the #233 step 3 real
Claude A→B handover acceptance against framework head
`ba12d21c22aa07e7ed016c64abcd2d9bf2122328`. Two real Claude sessions started
before either saved progress, and **neither** could then acquire ownership; the
shared closeout became permanently un-initializable. State after both refusals
was clean, so the failure is fail-closed availability loss, not wrongful
release.

## Conflict check — `ARCHITECTURE.md` §6.2

Performed before writing this record, as §6.2 requires and as its closing line
makes a governance failure to omit.

| Step | Result |
| --- | --- |
| 1. related titles in `docs/adr/` | one record exists: `0001-gate3-native-directory-handle-boundary.md` |
| 2. conflicts found | **none.** 0001 decides *OS handle* ownership (`CloseHandle`, handle lifetime, close semantics) and uses "owner" for the repository's human owner and owner rulings. This record decides *shared-closeout worktree* ownership state semantics. The two share the word "ownership" and nothing else; 0001 never mentions the session envelope, the owner record, or `AMBIGUOUS_LEGACY_STATE` |
| 3. ambiguity, supersession | none. Nothing in 0001 is superseded or narrowed |
| 4. related ADRs linked | `docs/adr/0001-gate3-native-directory-handle-boundary.md`, linked here as the only prior record, with no overlapping decision |

The near-collision is worth recording on its own: two records touching
"ownership" that mean different things is the same shape as the defect this
record fixes — a name treated as the property it resembles.

## Triggers — `ARCHITECTURE.md` §6.1

| Trigger | Applies |
| --- | --- |
| boundary partitioning | **yes** — which on-disk surface carries which responsibility |
| long-lived interface placement | **yes** — the ownership error-code vocabulary is an interface that callers and tests match on |
| memory ownership strategy | no |
| cross-platform loading strategy | no |
| ABI or calling convention | no |

## Context

`shared_closeout_ownership._initial` runs only when no owner record exists yet.
It walks several directories under `artifacts/runtime/` and, for every entry
that is not the acquiring session, requires both a readable session envelope and
a completion marker, failing with
`AMBIGUOUS_LEGACY_STATE: active or orphan lifecycle evidence`.

`artifacts/runtime/sessions/<sid>/session-envelope.json` is written
unconditionally by SessionStart. Every session that has ever started in the
repository leaves one, permanently. Applying the completion-marker requirement
to that directory therefore means:

> the shared closeout may only be initialized if every session that has ever
> started here has already been formally closed out.

Completion markers come from formal closeout, formal closeout requires
ownership, and ownership requires `_initial` to pass. Before the first owner
record exists the condition can hold only when at most one session has ever
started.

The root cause is a category error: **an identity registry was read as a
closeout ledger.** An envelope's existence states that an id was bound to this
worktree root. It does not state that the session has an outstanding closeout
obligation. This is the anti-pattern already recorded in
`memory/03_knowledge_base.md` as "A mechanical signal is not the semantic
property it resembles (2026-10-23)".

## Decisions

### D1 — three named states, and only one of them blocks

For a session id other than the one acquiring, while no owner record exists:

| Name | On-disk shape | Meaning | Blocks initialization |
| --- | --- | --- | --- |
| `IDENTITY_ONLY` | envelope only; no candidate, receipt, release record, completion marker or shared closeout text | the session never acquired ownership and produced no closeout-side artifact. **There is nothing to reconcile** | **no** |
| `CLOSED` | completion marker present and consistent with its receipt | already explained | no (unchanged) |
| `IN_FLIGHT` | at least one of: candidate, receipt, release record, shared closeout text — and no completion marker | a closeout was interrupted part-way | **yes** |

`IN_FLIGHT` is the state the existing error message actually describes. The
reported defect is `IDENTITY_ONLY` being classified as `IN_FLIGHT`.

### D2 — `sessions/` is not a closeout-obligation surface

`artifacts/runtime/sessions/` is the identity registry. It carries no closeout
obligation and must not be used to derive one. The genuine obligation surfaces
are `closeout_candidates/`, `closeout-receipts/`, `closeouts/`,
`closeout-completions/` and the shared closeout text, which `_initial` already
inspects separately; those checks are what detect `IN_FLIGHT` and they are
unchanged by this record.

`sessions/<sid>/` keeps a **containment** check — the directory may hold only
`session-envelope.json` — because a stray file there is a path-safety concern.
Containment is "nothing was planted here". It is not "this session owes a
closeout". Expressing both through one predicate is what made the two
indistinguishable in the field.

### D3 — the two conditions get distinct error codes

| Condition | Code | Detail |
| --- | --- | --- |
| obligation unmet (`IN_FLIGHT`) | `AMBIGUOUS_LEGACY_STATE` (unchanged) | `active or orphan lifecycle evidence` |
| containment violated | `SESSION_DIR_UNEXPECTED_FILE` (new) | the offending relative path |

Both are fail-closed refusals; only the diagnosis differs. Diagnosing #256 cost
an extra investigation round precisely because both conditions surfaced as the
same code, so this separation is the part of the decision with immediate
operational value.

### D4 — liveness is not `_initial`'s question

`_initial` runs only when no owner record exists, so there is no owner to
conflict with. Two sessions acquiring concurrently are serialized by
`execution_exclusion`, after which the second observes an existing owner and is
refused `OWNER_CONFLICT` — observed as criterion R2 of the #233 step 3 real
acceptance. The `sessions/` block therefore buys no safety that
`execution_exclusion` plus `owner.json` does not already provide; it only
forfeits availability.

If liveness ever has to become a first-class property it belongs in a lease with
a TTL or heartbeat, which is the shape `execution_exclusion` already has. It
does not belong in inferences drawn from the presence of registry files.

### D5 — a resumable checkpoint must never be read as liveness

`artifacts/runtime/session-checkpoints/<sid>.json` carries `exited_at`, and must
not be used to decide whether a session is finished. Neither direction holds:

- **present ≠ finished.** The checkpoint is deliberately *resumable* and writes
  no completion marker, so `claude --resume` continues the same session.
- **absent ≠ live.** SessionEnd may not fire, and the installed hook has a
  five-second timeout.

Adopting `exited_at` as a liveness signal would repeat the category error of
D1/D2 under a different filename. This decision exists to foreclose the most
intuitive wrong fix.

## Deliberately not decided

Ratified on 2026-10-27: D1 through D5 only. The owner deferred the rest.

1. **Recovery for `IN_FLIGHT` when no owner record exists.** Narrowing
   `_initial` leaves a smaller and *correct* refusal for genuine `IN_FLIGHT`
   state — but no recovery path exists for it. `reconcile_release` reaches
   `_matching` → `_owner`, which raises when the owner record is absent, so every
   recovery entry presupposes the record. A recovery entry that does not require
   an owner would need its own authorization gate, or it becomes a way around the
   attestation gate; this is structural remediation under `AGENT.md` §2.5 and may
   not be slipped in alongside the narrowing.
2. **Whether `sessions/<sid>/` containment should stay "envelope only".** If
   anything is ever legitimately written there, an envelope-only rule becomes the
   next refusal of the same shape.

## Consequences

- `AMBIGUOUS_LEGACY_STATE` is matched as a literal string in
  `governance_tools/shared_closeout_ownership.py`,
  `tests/test_shared_closeout_ownership.py` and
  `tests/test_prepare_closeout_candidate.py`. Splitting the code is a
  test-visible contract change, not an internal rename, and the tests that
  currently assert the single code are the evidence that the split landed.
- The error-code vocabulary is open at the mechanism level: `OwnershipError`
  takes any `code` string. Adding `SESSION_DIR_UNEXPECTED_FILE` needs no new
  registry, and this record deliberately does not create one.
- No new validator, hook, schema field or governance surface is introduced. This
  record narrows one existing predicate and splits one existing error code.

## Authorization boundary

This record documents ratified semantics. It does not authorize the code change,
either deferred question, a push, or a pull request. The #256 reproduction scenes
are preserved at `D:\ai-gov-step3b-20261027` and `D:\ai-gov-step3c-20261027`.
