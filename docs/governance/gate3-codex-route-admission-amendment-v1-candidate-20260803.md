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

The developer-instruction anchor status was `multiple`. This amendment does
not collapse those records into one value and does not declare their content
identity resolved. The approved simplification specification continues to
govern developer-instruction structure as pair-equal and normalized content
anchors as calibration-frozen after explicit review.

## Open calibration findings

The public calibration receipt reports `unknown_context_field_count = 3`.
Their names and values were not projected into public evidence. This amendment
does not classify, ignore or admit them.

Before any new pair authorization, a separate reviewed decision must either:

1. map each field into the approved closed context inventory with an explicit
   disposition; or
2. prove that the count is caused by fields already covered under a canonical
   alias or structural projection.

Formal admission must remain fail closed for genuinely unknown context fields.

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
or claimed by this document.

## Review and promotion sequence

The required order is:

1. independent semantic review of this candidate;
2. resolution of the three unknown context fields and the multiple developer
   instruction anchor;
3. preparation and review of the formal admission implementation;
4. one exact candidate manifest covering the amendment and implementation;
5. exact-byte owner signature;
6. canonical promotion; and
7. only then, separate consideration of an exact-session live-pair
   authorization.

No later step may treat this calibration probe as a scored result or as proof
that a future pair will pass.

## Claim ceiling

This candidate claims only that the owner accepted two experiment-wide
calibration anchors from the named non-counted probe and that the proposed
future admission semantics are documented.

## Cannot claim

- Independent approval of this amendment.
- Resolution of the multiple developer-instruction anchor.
- Resolution of the three unknown context fields.
- Runtime enforcement of either anchor.
- A rebuilt or signed candidate manifest.
- Canonical promotion.
- Authorization for another session or live pair.
- A successful scorer packet.
- Gate 3 resumption or counted execution greater than zero.
