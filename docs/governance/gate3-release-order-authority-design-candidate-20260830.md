# Gate 3 Release-Order Authority — design candidate 1

Status: **DESIGN ONLY / CONDITIONAL SUFFICIENCY / HOSTILE REVIEW REQUIRED**

Date: 2026-08-30
This is a bounded architecture tranche, not revision 10 of Plan B. It
authorizes no implementation, provider, credential, network call, rehearsal,
commit or push.

## 1. Identity and authority

The governing PLAN authority is bound by all of:

```text
commit:       01e8c0b4f61b1288d80495230f5fb4d8aeed525a
PLAN blob:    d4ed290ad17b8e5e7aec83c92f2e1498ed170a63
PLAN SHA-256: 315f7f61ec5f06fbf31675b55de98fe3464ff256c2daa8d3fb1b987be22d5f53
section:      ### Gate 3 first-Skill funding gate — principal before engineering
section SHA-256: 7974b94ce78e91ee7b2d047208c22caf8ddbee52e93c34ae9d635b980477c168
```
It requires a separately controlled external pin, genuinely independent pin
controller, retained append-only/protection evidence, and fail-closed refusal
of retrospective pinning.
The unchanged rejected rev9 candidate is problem evidence only:

```text
path: docs/governance/gate3-first-skill-external-pin-plan-b-design-candidate-20260820.md
SHA-256: 92004c3f59aa16dcc6152c1be61d83f7ee67e4f1be963b058d7f9e3acc481f7d
bytes/LF/CR: 90126 / 1495 / 0
```
Rev9 orders its producer path pin before release but expressly does not prove
first publication or historical publication order. It is not amended here.
The only committed ADR, proposed ADR-0001 for a Windows native handle boundary,
has no normative conflict and is not generalized. A later accepted integration
may require its own ADR; this candidate does not create one.

## 2. Single falsifiable problem

Current-state local evidence can leave identical final bytes in both histories:

```text
valid:   PIN -> current authoritative RELEASE
hostile: earlier authoritative RELEASE -> delete/reconstruct -> PIN
         -> current RELEASE
```
An inclusion proof for the displayed PIN and current RELEASE cannot distinguish
them. The required proposition is:

```text
For canonical comparison unit U in admitted authority A,
PIN(U) precedes the first authoritative mapping RELEASE(U).
```
Without historical empty state, monotonic continuity and non-equivocation
evidence, this proposition is unprovable and the tranche stops.

## 3. Closed publication and roles

Before unit activity, the owner freezes descriptor `D`: one authority instance
and genesis, canonical namespace/key derivation, transition rules, finality and
anti-equivocation policy, and the only authoritative-publication meaning.

```text
authoritative_mapping_publication(A, U, B)
    iff A finalizes RELEASE_AND_PUBLISH(U, B) under D
```
RELEASE must itself expose exact canonical mapping bytes for independent public
retrieval. A digest-only
receipt, later statement about publication elsewhere, or pointer to coordinator-
controlled storage is not publication evidence. If another surface remains an
authoritative publication channel, the predicate is not closed and this design
stops.
Roles are semantic; no identity or provider is selected:

- `C`, coordinator/local chain writer, is untrusted for historical order and
  may delete all local state;
- `I`, independent pin controller, is not another account of the same natural
  person or automation agent as `C`;
- `A`, externally protected ordered authority, finalizes transitions; and
- `V`, independent verifier, trusts no history claim from `C`.

The PIN proof retained under `D` must show that `C` cannot delete, reset, merge,
force-update or select a private fork of `A`. Unknown or changed protection,
controller, namespace or genesis fails closed.

## 4. One monotonic publication register

`U` is derived from the frozen canonical comparison-unit identity, never a
caller label, and contains no mutable epoch. Alternate encodings for the same
identity are invalid, not fresh units. `X` binds exact pre-release evidence,
including event 6 and the mapping commitment; `B,N` open that commitment.
Authority `A` keeps one never-clear state per `U`:

```text
EMPTY
  | PIN(U, X), authorized by I
  v
PINNED(P)
  | RELEASE_AND_PUBLISH(U, B, N, pin_ref=P)
  v
RELEASED(R)                         terminal
```
`PIN` atomically requires authenticated `EMPTY`, then finalizes `P` binding
`D`, `U`, `X`, `I`, predecessor state and authority order.
`RELEASE_AND_PUBLISH` atomically requires `PINNED(P)`, verifies `B,N`, publishes
exact `B`, and finalizes `R` binding `D`, `U`, `P`, `B` and later order.
No other transition exists. `RELEASED` cannot be deleted, tombstoned, reset,
reopened or succeeded. Rotation is inadmissible unless predecessor-authorized
evidence carries the complete state root forward; a fresh epoch is not
continuity.
It is not attempt counting, a receipt service or a general publication
framework, and claims nothing across distinct canonical comparison units.

## 5. Independent verifier predicate

`V` accepts only if one coherent proof package establishes all of:

1. `D` is the owner-admitted descriptor fixed before `U` began.
2. `U` is uniquely derived from the frozen comparison-unit identity.
3. Finalized `P` binds exact `U`, event 6, mapping commitment, controller and
   pin-time protection state.
4. An authenticated predecessor/non-membership proof shows `State[U]=EMPTY`
   immediately before `P`.
5. A valid transition proof shows `EMPTY -> PINNED(P)`.
6. Finalized `R` references exact `P` and contains exact canonical `B`.
7. `B,N` open the commitment bound by `P`.
8. A valid transition proof shows `PINNED(P) -> RELEASED(R)`.
9. Authority order proves `order(P) < order(R)`.
10. Genesis-to-`P`-to-`R` consistency proves never-clear state, no reset,
    unlinked epoch or accepted transition outside this machine.
11. Witness/quorum/consensus evidence satisfies the admitted policy under which
    conflicting histories cannot both be finalized.
12. `V` independently obtained the canonical finalized view; caller-selected
    stale checkpoints and incomplete prefixes are not authority.
An inclusion-only append-only log fails items 4, 10 and 11. An authenticated
map, complete-prefix/earliest-event proof or other construction is acceptable
only if it proves the same predicates; timestamps and sequence numbers alone do
not.
If earlier authoritative `R0` existed, the closed predicate places it in this
register, permanently leaving `State[U]=RELEASED(R0)`. A later EMPTY proof and
PIN cannot verify. Local deletion changes no external state; reset, alias, fork
or fresh epoch invalidates items 2, 4, 10 or 11. Thus an accepted package
excludes the hostile history under `D`.

## 6. Claim ceiling

This candidate establishes only conditional abstract sufficiency:

> If an admitted authority implements this closed, monotonic, non-equivocating
> register, an independent verifier can prove that the qualifying pin precedes
> its first mapping release for canonical comparison unit `U`.
It proves no provider has the capability. It also does not prove:

- absence of private, covert, scorer-visible or out-of-band disclosure;
- globally first Internet publication or first publication for another unit;
- scorer blindness/independence or coordinator ignorance;
- attempt count, no discarded runs, first append, dispatch or global unit
  uniqueness;
- non-collusion beyond admitted assumptions; or
- Gate 2 repair, Gate 3 completion or implementation readiness.

Hash/signature security, honest admitted finality, canonical identity,
controller independence and closed publication remain trust assumptions.

## 7. Hostile evidence plan

Exact-byte review must cover at least:

1. `PIN #100 -> first RELEASE #105`: accept with every proof.
2. `RELEASE #80 -> PIN #100`: no valid EMPTY proof; reject.
3. `RELEASE #80 -> local deletion/reconstruction -> PIN #100 -> RELEASE #105`:
   reject even when final local bytes equal case 1.
4. Receipt after publication on another authoritative surface: reject `D`.
5. Inclusion without predecessor/consistency proof: reject firstness.
6. Alternate unit encoding, caller alias or fresh empty epoch: reject.
7. Tombstoned state, truncated history or unlinked rotation: reject.
8. Conflicting checkpoints or weak anti-equivocation evidence: reject.
9. Mutated unit, event 6, mapping bytes, opening or pin reference: reject.
10. Unknown controller independence, protection or finality: reject.
Fixtures test evidence semantics, not provider APIs or runtime code.

## 8. Deferred integration and STOP

This produces a verifier proposition, not an event-7 field, proof-bundle schema,
serializable token or function contract. Rev9's pin request, provider profile,
filesystem binding, retained lineage, error precedence, legacy paths and three
residual blockers remain untouched.
Provider selection, signer/account lifecycle, credentials, transport, network,
rehearsal, runtime/native code, countability, implementation, commit and push
are outside this tranche.
Stop rather than expand if publication cannot equal RELEASE; another
authoritative channel remains; `U` has aliases; authority can reset, delete,
truncate, fork or start an unlinked epoch; empty-state/consistency/anti-
equivocation evidence is unavailable; the claim becomes absence of covert
disclosure; or closure needs provider APIs, signer lifecycle, attempt authority,
rev9 residual fixes, error taxonomy or another state subsystem.

The only next action authorized here is exact-byte hostile review. Any provider-
feasibility, integration, ADR or implementation tranche needs a new owner
decision after that review.
