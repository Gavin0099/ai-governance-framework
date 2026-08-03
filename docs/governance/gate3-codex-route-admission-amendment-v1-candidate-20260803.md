# Gate 3 Codex route admission amendment v1 candidate

Status: **CANDIDATE ONLY — PENDING INDEPENDENT REVIEW, EXACT-BYTE OWNER
SIGNATURE AND CANONICAL PROMOTION.**

This amendment does not authorize a calibration session, a live pair or a
counted Gate 3 run. It changes no runtime or formal admission behavior until a
separate implementation, review, signature and promotion sequence completes.

## Purpose

Record the owner's evidence-informed ruling for the two context fields left
open by the approved Gate 3 Codex route simplification specification:
`originator` and `source`.

The ruling replaces neither the existing preregistration candidate nor its
manifest. It is a candidate input to a future admission revision.

## Authority and source evidence

Owner ruling date: `2026-08-03`.

Owner-accepted anchors:

```text
originator = Codex Desktop
source = exec
scope = calibration-frozen / experiment-wide
rationale = execution and instruction surface identity;
            cross-pair drift is validity-critical
```

Calibration source:

| Field | Value |
|---|---|
| run ID | `gate3-codex-calibration-v1-20260803-150000` |
| execution source commit | `76aac8302a8c1e2b8f7ecbcf7a8b1c0313b11290` |
| public receipt schema | `gate3-codex-calibration-probe-receipt.v3` |
| public receipt bytes | `8139` |
| public receipt SHA-256 | `d333ad13ce2b6c5a3ce841cd465efc0c646ad1a6f3e1fcfe3f32a23c4e5faab2` |
| session invocations | exactly `1` |
| orchestrator retries | `0` |
| formal admission performed | `false` |
| scoreable | `false` |
| cleanup | `PASS` |

The public receipt intentionally does not publish the private artifact path,
digest or the exact open-ruling values. The owner ruling above was made after a
read-only extraction from the current-user-only private decision artifact.
That extraction verified:

- the private run ID matched the public run ID;
- the directory and file DACLs were protected;
- each DACL contained exactly one explicit `Allow FullControl` ACE for the
  current user SID and no inherited ACE; and
- `originator` and `source` were each single-valued.

No credential, credential digest, instruction text, command, path or raw
rollout is incorporated into this amendment.

Follow-up calibration and independent read-only disposition review:

| Field | Value |
|---|---|
| run ID | `gate3-codex-calibration-v2-20260803-215100` |
| execution source commit | `34b022102550eaa1236bf6f344e3c7c5c5523357` |
| public receipt schema | `gate3-codex-calibration-probe-receipt.v4` |
| nested public calibration schema | `gate3-codex-calibration-public-receipt.v2` |
| public receipt bytes | `7904` |
| public receipt SHA-256 | `9166b24d5801c9ad64cfdba09cf00d25a7926ed8dcb08a294e6b9253aff52e71` |
| session invocations | exactly `1` |
| orchestrator retries | `0` |
| formal admission performed | `false` |
| scoreable | `false` |
| cleanup | `PASS` |

The follow-up review used an authorized, read-only access to the
current-user-only private decision artifact. It verified the private/public
run and schema binding, the protected non-inherited DACL boundary, the total
three-field census under `session_meta`, the absence of the private field names
from the public receipt, and the ordered developer-instruction structure. The
review published only the privacy-safe field dispositions and structural
comparison below. It published no private artifact path or digest, credential,
raw value, instruction content or rollout.

## Ruling

### `originator`

Disposition: **calibration-frozen / experiment-wide**.

Required literal: `Codex Desktop`.

Reason: the field identifies an execution or instruction surface. Treating it
as pair-equal would allow a later pair to use a different surface while still
passing within-pair equality. That would introduce a cross-pair confound.

### `source`

Disposition: **calibration-frozen / experiment-wide**.

Required literal: `exec`.

Reason: the field describes the same execution route and must be governed with
`originator`. Allowing it to drift independently would make the surface ruling
internally inconsistent.

### Joint invariant

Formal admission must eventually require the exact ordered identity:

```json
{
  "originator": "Codex Desktop",
  "source": "exec"
}
```

Every admitted arm and every pair in the experiment must match both literals.
A missing field, non-string value, duplicate or conflicting observation, or
literal mismatch must fail closed before producer output becomes scoreable.
The two values may not be learned or replaced from a counted run.

## Instruction identity observed with the ruling

The calibration session observed one base-instruction content anchor:

```text
072920a4e81002dc96aa4b7be4e9079c81edcfc0c93ea4e6cd4a31fb50f299db
```

The original calibration observed two developer-instruction records with two
distinct content digests, so its historical anchor status was correctly
recorded as `multiple`.

The follow-up calibration observed one developer-instruction record with one
content digest. That digest was not present in the original two-digest set.
This is both cardinality drift and content drift, not merely a collapse from
two records to one. The historical `multiple` statement remains run-specific
history and is not rewritten.

No canonical developer-instruction record structure or normalized content
anchor is established by these observations. The approved simplification
specification continues to require an explicit owner choice, independent
review and pre-counted-run freezing before such an anchor can govern formal
admission.

## Follow-up calibration field dispositions

The follow-up public receipt reports `unknown_context_field_count = 3`, all
under `session_meta`. The authorized independent review classified the three
privacy-safe schema tokens as follows. No raw value was published or used as a
caller-supplied admission fact.

### `timestamp`

Disposition: **canonical alias** of the approved general `timestamps`
observational row.

Required treatment: validate parseability and ordering only. Do not require
exact-value equality and do not promote the observed value to a calibration
anchor.

### `context_window`

Disposition: **genuinely new admission field**.

Reason: no closed-inventory row currently covers context-capacity metadata,
and capacity may affect producer behavior. This amendment records the field's
existence but does not choose hard-frozen, calibration-frozen, pair-equal,
normalized-equal or observational semantics for it. Formal admission must
remain fail closed until an explicit owner ruling is independently reviewed
and promoted before any counted run.

### `git`

Disposition: **unresolved**.

Reason: a name-only census cannot prove whether the field aliases the frozen
baseline Git identity, represents additional repository state, or contains a
separate nested structure. Formal admission must remain fail closed until a
privacy-safe type/subfield projection or a separately reviewed owner ruling
proves its mapping. It must not be silently aliased from its name.

None of the three fields is classified as **already covered structure** on the
available evidence.

## Required future implementation behavior

A later implementation tranche may consume this amendment only if it:

1. pins these exact amendment bytes through the admission policy identity;
2. extracts `originator` and `source` from the verified session context rather
   than from caller-supplied summary data;
3. checks both literals before wrapper or producer-output admission;
4. binds both arms and every pair to the same promoted amendment identity;
5. publishes a fixed-vocabulary, privacy-safe rejection reason without
   publishing arbitrary observed values; and
6. includes mutation tests for missing, non-string, mismatched, duplicated and
   cross-pair-drift cases.

This section specifies required behavior only. No such runtime change is made
or claimed by this document. Because this candidate still records unresolved
admission semantics, it may not itself become an admitting policy. The
accepted rulings must first be incorporated into revised amendment bytes and
those exact bytes must pass independent review.

## Review and promotion sequence

The required order is:

1. independent semantic review of this candidate;
2. owner rulings for `context_window`, the unresolved `git` field and the
   canonical developer-instruction structure/content anchor;
3. incorporation of the accepted rulings into revised amendment bytes;
4. independent semantic review of those exact revised amendment bytes;
5. preparation and review of the formal admission implementation;
6. one exact candidate manifest covering the reviewed amendment bytes and
   implementation;
7. exact-byte owner signature;
8. canonical promotion; and
9. only then, separate consideration of an exact-session live-pair
   authorization.

No later step may treat this calibration probe as a scored result or as proof
that a future pair will pass.

## Claim ceiling

This candidate claims only that the owner accepted two experiment-wide
calibration anchors from the original non-counted probe, and that the
follow-up calibration's privacy-safe field dispositions and
developer-instruction drift are documented. It does not resolve the new or
unresolved admission semantics.

## Cannot claim

- Independent approval of this amendment.
- A canonical developer-instruction structure or content anchor.
- Admission semantics for `context_window`.
- Proof that `git` aliases the frozen baseline Git identity or another approved
  structure.
- Runtime enforcement of either anchor.
- A rebuilt or signed candidate manifest.
- Canonical promotion.
- Authorization for another session or live pair.
- A successful scorer packet.
- Gate 3 resumption or counted execution greater than zero.
