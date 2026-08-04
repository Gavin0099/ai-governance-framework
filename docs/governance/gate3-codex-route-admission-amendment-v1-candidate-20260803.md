# Gate 3 Codex route admission amendment v1 candidate

Status: **CANDIDATE ONLY — PENDING INDEPENDENT REVIEW, EXACT-BYTE OWNER
SIGNATURE AND CANONICAL PROMOTION.**

This amendment does not authorize a calibration session, a live pair or a
counted Gate 3 run. It changes no runtime or formal admission behavior until a
separate implementation, review, signature and promotion sequence completes.

## Purpose

Record the owner's evidence-informed rulings for the context and instruction
identity fields left open by the approved Gate 3 Codex route simplification
specification and the two calibration probes: `originator`, `source`,
`context_window`, `git`, and the unresolved developer-instruction source.

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

Follow-up owner rulings accepted on `2026-08-03`:

```text
context_window = new structural inventory row for per-session identity
git = new structural inventory row for initial repository identity
developer instruction = unresolved; observed v2 digest is not an admission anchor
```

Developer-instruction source and authority ruling accepted on `2026-08-04`:

```text
identity = pre-first-tool normalized developer envelope rendered by the pinned
           Codex implementation
raw digest anchor = forbidden
config-level developer override = absent
collaboration developer instructions = null
unknown source or unclassified section = fail closed
post-tool developer records = observational only; excluded from initial admission
post-tool session-meta base instructions = observational only; excluded from initial admission
```

Calibration source:

| Field | Value |
|---|---|
| run ID | `gate3-codex-calibration-v1-20260803-150000` |
| execution source commit | `76aac8302a8c1e2b8f7ecbcf7a8b1c0313b11290` |
| public receipt schema | `gate3-codex-calibration-probe-receipt.v3` |
| repo-bound public receipt | `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-codex-calibration-v1-20260803-150000.calibration.json` |
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
| repo-bound public receipt | `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-codex-calibration-v2-20260803-215100.calibration.json` |
| public receipt bytes | `7904` |
| public receipt SHA-256 | `9166b24d5801c9ad64cfdba09cf00d25a7926ed8dcb08a294e6b9253aff52e71` |
| session invocations | exactly `1` |
| orchestrator retries | `0` |
| observed wrapper calls | `0` |
| observed turns | `1` |
| observed session metadata records | `1` |
| path match census | all five match counts were `0` |
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

The follow-up session issued no tool call, so it exercised no wrapper shape and
did not observe repository state after a producer commit. Its path census also
reported zero matches for session metadata cwd, turn cwd, machine cwd, turn
workspace root and machine workspace root. The calibration therefore supports
closed structural inspection of the recorded metadata only. It does not prove
wrapper acceptance, expected-workspace placement, post-commit Git projection,
or a complete producer workflow. The original calibration issued only one tool
call and therefore could not have completed the producer workflow.

A later owner-authorized, read-only inspection of the official Codex `0.146.0`
package and source at tag `rust-v0.146.0` (commit
`e363b08c9175ac1cbe5893615dd2cb9ddf95043b`) established the structural and
semantic sources needed to classify `context_window` and `git`. No Codex
session was launched and no package binary was executed during that
inspection. The source establishes that `context_window.window_id` is a
UUIDv7 session-window identity rather than token capacity, and that `git` is
an optional repository projection containing `commit_hash`, `branch`, and
`repository_url`.

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

Both calibration sessions observed the same base-instruction content identity:

```text
072920a4e81002dc96aa4b7be4e9079c81edcfc0c93ea4e6cd4a31fb50f299db
```

Disposition: **stable across the two observed calibrations (`2/2`), but
observation only in this amendment**. This candidate does not replace the
simplification specification's existing `D then B / experiment` treatment and
does not promote the observed digest to a new frozen anchor.

The original calibration observed two developer-instruction records with two
distinct content digests, so its historical run-specific status was correctly
recorded as `multiple`.

The follow-up calibration observed one developer-instruction record with one
content digest. That digest was not present in the original two-digest set.
This is both cardinality drift and content drift, not merely a collapse from
two records to one. The historical `multiple` statement remains run-specific
history and is not rewritten.

The follow-up calibration observed the following developer-instruction
identity:

```text
record count = exactly 1
ordered structure = one-record singleton list
normalized content SHA-256 =
  31c31c4ac9a140c384fc9ac9159101c92662e48369416aa40998a29d841a1a1d
status = historical observation only; not an admission anchor
```

This value is not calibration-frozen. The original and follow-up probes used
the same CLI version, model/build identity, base-instruction anchor, launcher,
live-canary route and byte-identical repository `AGENTS.md`, yet the developer
records changed from two records to one and the digest sets did not overlap.
The repo-side launcher does not inject those developer records, and the
retained evidence does not identify their controlling source. Freezing the v2
digest would therefore make admission depend on an unexplained, presently
uncontrolled input. The owner therefore explicitly forbids using this or any
other raw developer-record digest as an experiment anchor.

The historical two-record observation remains run-specific evidence and is
not rewritten. Read-only inspection of the pinned official Codex `0.146.0`
implementation identified the source boundary: initial developer context is
assembled by `build_initial_context_with_world_state`, with each generated
section retained as a separate content item by `build_developer_update_item`.
The implementation can also prepend a config-level developer override and can
append later developer records after tool execution or lifecycle updates.

The accepted authority rule is therefore structural rather than a raw digest:

- formal admission consumes only the developer message emitted before the
  first tool call and preserves its ordered content-item section boundaries;
- every section must be a recognized envelope generated by the pinned Codex
  implementation; an unmarked config override, unknown marker, duplicate
  section kind, malformed content item or extra initial developer message fails
  closed;
- the `<context_window>` section must be structurally bound to the initial
  `session_meta` session and window identities, after which those per-session
  values are replaced by fixed tokens before cross-arm comparison;
- workspace paths are normalized only through the existing A/B workspace-token
  rule; no arbitrary free-text or UUID folding is allowed;
- the collaboration-mode developer-instruction value must be JSON `null`, and
  each isolated `CODEX_HOME` must be empty before the credential-only
  `auth.json` is seeded, so a config-level override has no admitted source; and
- developer records emitted after the first tool call remain structurally
  readable and are counted, but their contents do not enter initial context
  identity or cross-arm admission.

The two arms must have byte-identical canonical JSON for this normalized
initial envelope. The published receipt may carry only the normalized-envelope
digest, section classes/count and post-tool record count; it must not publish or
pin a digest of the raw developer text.

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

Disposition: **new coverage inventory row (E); structurally validated
observational session identity**.

Reason: official Codex `0.146.0` source defines this field as an optional
`SessionContextWindow` whose `window_id` is generated as UUIDv7. It is not the
model token-capacity field and therefore must not be frozen to a capacity
literal or treated as a pair-equal value. The follow-up v2 calibration observed
the object (`1/1`). The v1 public receipt exposes only an aggregate unknown-field
count and cannot establish whether `context_window` was present. The official
source structure and owner ruling support the candidate presence rule, but the
public calibration evidence does not prove presence across two probes or an
unexercised complete producer lifecycle.

Required treatment:

- admission must consume exactly one initial `session_meta` record emitted
  before the first tool call;
- the initial `context_window` object must be present and its exact key set must
  be `{ "window_id" }`;
- `window_id` must be a valid UUIDv7 string;
- the A and B sessions must have distinct `window_id` values; and
- no observed `window_id` may become an exact-value, calibration-frozen, or
  pair-equal anchor.

A missing or additional initial metadata record, missing object, unknown
subfield, invalid UUIDv7 value, or reuse across the A/B sessions must fail
closed. No claim is made that a window identity remains unchanged across
compaction or another later session-lifecycle event; the calibration did not
exercise that lifecycle.

### `git`

Disposition: **new coverage inventory row (E); initial repository projection**.

Reason: official Codex `0.146.0` source defines `git` as the optional repository
projection collected from the session working directory, with optional
`commit_hash`, `branch`, and `repository_url` fields. This source inspection
defines the structure, but the zero path-match census does not prove that the
calibration ran in the expected synthetic workspace. The rule below therefore
binds only the unique initial session metadata record and does not claim that
the calibration verified a post-commit projection. Presence is required because
the formal route requires every arm to start inside a fresh synthetic Git
repository; absence would contradict that admitted route rather than represent
an allowed non-Git variant.

Required treatment:

- admission must consume the same unique initial `session_meta` record emitted
  before the first tool call;
- the `git` object must be present; its allowed key set is
  `{ "commit_hash", "branch", "repository_url" }`, and its required keys are
  `commit_hash` and `branch`;
- the initial `commit_hash` must exactly equal the frozen baseline commit;
- `branch` must be a non-empty string and pair-equal across A and B, but is not
  frozen to a historical literal; and
- `repository_url` must either be absent or be JSON `null`; both representations
  mean that the fresh synthetic repository has no remote, while any non-null
  value must fail closed.

A missing or additional initial metadata record, missing object, unknown
subfield, missing or mismatched initial commit, empty or cross-arm-mismatched
branch, or non-null repository URL must fail closed. The later producer
`output_commit` must not be compared to this initial metadata field; it remains
governed by the existing requirement that the output commit has the frozen
baseline as its sole parent and by the retained bundle/outcome verification.

Both `context_window.window_id` and the `git` subfields must be added explicitly
to the simplification specification's coverage inventory before implementation
review. Official source semantics alone do not make them already-covered rows.

## Required future implementation behavior

A later implementation tranche may consume this amendment only if it:

1. pins the exact bytes of an independently reviewed superseding amendment
   containing the developer-instruction source and authority rule above;
2. extracts `originator` and `source` from the verified session context rather
   than from caller-supplied summary data;
3. checks both literals before wrapper or producer-output admission;
4. validates `context_window` and `git` with the structural and cross-arm
   invariants above, deriving the frozen baseline commit from the admitted
   experiment inputs rather than caller-supplied summary data;
5. adds the new context-window and Git rows to the closed coverage inventory;
6. derives developer identity only from the normalized pre-first-tool envelope,
   forbids raw developer-digest anchors, and treats post-tool developer records
   as observation-only;
7. binds both arms and every pair to the same promoted amendment identity;
8. publishes a fixed-vocabulary, privacy-safe rejection reason without
   publishing arbitrary observed values; and
9. includes mutation tests for missing, malformed, mismatched, duplicated,
   reordered, unknown-field, cross-arm-drift and forbidden-reuse cases,
   including `0`, `1`, and `2` pre-tool `session_meta` records before the
   exactly-one rule may be promoted.

This section specifies candidate required behavior. A formal admission
implementation may be prepared against these bytes, but neither document nor
implementation becomes an admitting policy until independent review, manifest
rebuild, exact-byte owner signature and canonical promotion complete.

## Review and promotion sequence

The required order is:

1. independent semantic review of these exact revised amendment bytes and the
   repo-bound v2 public receipt;
2. independent review of the developer-instruction source, authority and
   normalization ruling now incorporated above;
3. preparation and review of the formal admission implementation and coverage
   inventory additions;
4. mutation evidence demonstrating each fail-closed rule above;
5. one exact candidate manifest covering the reviewed amendment bytes and
   implementation;
6. exact-byte owner signature;
7. canonical promotion; and
8. only then, separate consideration of an exact-session live-pair
   authorization.

No later step may treat this calibration probe as a scored result or as proof
that a future pair will pass.

## Claim ceiling

This candidate claims only that the two non-counted calibration receipts are
preserved with their limitations, that the owner accepted the initial-context
field dispositions as revised above, and that official Codex `0.146.0` source
supports the stated field structures. It specifies candidate admission
semantics for `originator`, `source`, the initial `context_window`, initial
`git` projection and normalized pre-first-tool developer envelope. It does not
independently approve, sign, promote or execute any rule.

## Cannot claim

- Independent approval of this amendment.
- Reproducibility of the observed v2 developer digest in another session.
- The cause of the v1-to-v2 developer-record cardinality and content drift.
- Wrapper conformance from the v2 calibration, which issued no tool call.
- Expected-workspace placement from either calibration's zero path-match
  census.
- Stability of `context_window.window_id` across compaction or later lifecycle
  events.
- Presence of `context_window` in the v1 calibration; its public receipt does
  not identify the three unknown field names.
- The number of `session_meta` records emitted before the first tool call in a
  complete producer workflow; synthetic `0`/`1`/`2` coverage validates the
  candidate gate, not live emission stability.
- Independent approval of the candidate runtime enforcement.
- Proof that every future Codex developer section is represented in the closed
  allowlist; any new section must fail closed and return to review.
- A rebuilt or signed candidate manifest.
- Canonical promotion.
- Authorization for another session or live pair.
- A successful scorer packet.
- Gate 3 resumption or counted execution greater than zero.
