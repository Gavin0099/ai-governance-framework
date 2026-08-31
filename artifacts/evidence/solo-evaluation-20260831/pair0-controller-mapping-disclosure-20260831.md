# Pair 0 Controller Mapping Disclosure

Status: **DISCLOSURE RECORDED / CONTAINED / PRE-ATTEMPT STOP**

- Record type: `CONTROLLER_MAPPING_DISCLOSURE`
- Recorded at: `2026-08-31T01:54:17.1425015Z`
- Pair slot: `Pair 0`
- Pair ID: `solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040`
- Bootstrap commit: `d33305516c465289df7c0b066a8121dd0b5e4f90`
- Ledger blob: `b9e63e0e375f093bf4ee72dc050888c11fc67c39`
- Ledger SHA-256: `596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab`
- Execution-contract commit: `63f6b5e7fd9eb43e6e6e63c336c09be33247f2ad`
- Execution-contract SHA-256: `cf98dd010d05172a7bfe2f8924c2af4d3166c0b3c1e037836f1f904ebd51acb5`

## Event

During post-bootstrap controller-side verification, a filter matched the nested
Pair record rather than limiting its output to schema and key-presence facts.
The resulting controller output reproduced the anonymous scoring labels
together with their arm associations in the current conversation context.

This record intentionally does **not** reproduce either label, the mapping, a
serialized Pair record, or any other controller-only value.

At disclosure time:

- Pair IDs: `1`;
- Attempt IDs: `0`;
- arm executions: `0`;
- task exposures: `0`;
- scoring events: `0`.

## Impact and claim boundary

- Pair 0 is the pre-declared shakedown Pair and contributes no analytic product
  comparison result.
- Pair 0 scoring blindness remains possible only if its scorer is a fresh
  context that cannot receive this conversation, a summary or transcript of
  this conversation, the controller ledger, or any derived mapping-bearing
  output.
- The current conversation context and every context derived from its history
  are permanently ineligible to score Pair 0.
- A1 through A6 are unaffected: none has a Pair ID, anonymous labels, Attempt
  ID, task exposure, arm execution or scoring context at this checkpoint.
- This is a controller-side process disclosure. It is not classified as an
  `ANONYMIZATION_FAILURE`, does not create a qualification result, and does not
  authorize replacement, retry, execution or scoring.

## Containment and required gate

Effective immediately:

1. Controller-ledger verification may return only fixed PASS/FAIL tokens,
   schema version, event type, key-presence facts and non-sensitive counts.
2. It must not print, serialize, log or relay nested Pair or arm records,
   anonymous labels, label-to-arm mappings, task bindings or hidden evidence.
3. Execution and scoring contexts remain denied access to the controller
   ledger and to this conversation history.
4. Before the first Attempt ID is authorized, a safe-verifier gate must prove
   that its execution-visible output contains no controller-only field values.
   A missing, failing or value-bearing verifier result is `STOP`; it does not
   authorize an Attempt ID.
5. The append-only attempt ledger remains unchanged. Its frozen lifecycle
   schema does not admit `CONTROLLER_MAPPING_DISCLOSURE` as a ledger event, so
   this evidence is preserved as a separate commit-bound disclosure artifact
   rather than an invalid second ledger event.

## Disposition

`DISCLOSURE_RECORDED / PAIR0_SCORING_CONTEXT_RESTRICTED /
PRE_ATTEMPT_SAFE_VERIFIER_GATE_REQUIRED`

Solo execution remains stopped. This artifact creates no Attempt ID and
authorizes no task exposure, arm execution, scoring or push.
