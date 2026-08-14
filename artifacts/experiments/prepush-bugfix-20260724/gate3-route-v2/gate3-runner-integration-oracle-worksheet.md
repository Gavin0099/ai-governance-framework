# Runner integration oracle — derivation worksheet

Companion to `gate3_runner_integration_oracle.py`. It records how each expected
literal is derived, so a reviewer can re-derive a sampled subset independently
instead of trusting an author claim.

## What this worksheet can and cannot establish

A literal derived by hand and one pasted out of the production serializer are
byte-identical. **Nothing in this repository distinguishes them**, and this
worksheet does not change that.

- An import guard proves the oracle module is runtime-independent of the
  production modules. It says nothing about what was run before a value was
  pasted.
- Mutation tests measure whether the *verifier* rejects tampering. That is
  orthogonal to how a literal was historically produced.
- Independent re-derivation is **corroboration**: it raises confidence that the
  values are correct. It is not detection of author history.

Claim ceiling for the whole fixture: *runtime-independent of production code,
with values independently re-derived*. Nothing stronger.

## Canonicalization rules

Every artifact is the canonical JSON encoding used across this experiment:

1. object keys sorted lexicographically by code point;
2. separators `,` and `:` with no spaces;
3. ASCII only, non-ASCII escaped;
4. exactly one trailing `\n`;
5. digests are lowercase hex SHA-256 over those exact bytes.

A reviewer re-deriving a value should produce the bytes first, confirm they
match the literal, then hash.

## Fixture inputs

The complete-path package in the oracle module is produced from this synthetic
fixture; every value below is a test constant, not a runtime observation.

| Input | Value |
| --- | --- |
| arm | `A` |
| action / capture bindings | `capture.synthetic_bindings()` |
| runtime subjects | seven v1 subjects plus `bridge_source = b"synthetic bridge source\n"` |
| workspace baseline | `{"notes.md": b"baseline\n", "src/app.py": b"print(1)\n"}` |
| observed workspace | baseline with `notes.md` replaced by `b"edited\n"` → `CHANGED` |
| final observation | `CAPTURED` |
| contained result | `returncode=0`, complete NDJSON stdout, `stderr` canary |
| cleanup | `PASS` |

## Derivation order

Each step consumes only values fixed by earlier steps.

1. **`ORACLE_V1_CONTRACT_BYTES`** — the frozen v1 contract. Independent check:
   SHA-256 must equal `efac9147b39cc5290fc60c7e3516bebc774c4c22c8b026658755e127614ccc91`,
   the value pinned by the runner/capture integration milestone.
2. **`ORACLE_V2_CONTRACT_BYTES`** — v1 plus `evidence_classes:["SYNTHETIC"]` and
   `bridge_source` inserted into the sorted `runtime_subjects` list. SHA-256
   `0c0fe789ff3046677b97aeb93e90cd1fc4d2dbde63f5c3557d1f4aa5c11e7bb2`.
3. **`capture-authorization.json`** — canonical bytes of the capture bindings
   authorization. Its digest feeds the observation stage and the seal.
4. **`runner-integration-authority.json`** — the v2 authority public value.
   `workspace_baseline_sha256` is SHA-256 over the canonical bytes of
   `{artifact_id: sha256(content)}` for the baseline map above. Its digest feeds
   the seal as `authority_sha256`.
5. **`runner-observation-stage.json`** — binds the capture authorization digest
   from step 3.
6. **`process-result.json`**, **`capture-result.json`**,
   **`lifecycle-projection.json`** — the capture chain for the fixture stdout.
   Their digests appear in the seal's `capture_artifact_sha256` map, sorted by
   path.
7. **`final-output-observation.json`**, **`workspace-observation.json`** — closed
   state tokens `CAPTURED` and `CHANGED`.
8. **`runner-observation-seal.json`** — binds steps 2, 4, 5, 6 and 7 plus the
   derived profile. Its digest is `seal_sha256` for everything after it.
9. **`runner-cleanup-authorization.json`**, **`runner-cleanup-result.json`** —
   both carry `seal_sha256` from step 8.
10. **`runner-receipt.json`** — carries `seal_sha256` and `cleanup_sha256`, the
    digest of step 9's cleanup result.
11. **`runner-finalization.json`** — carries `receipt_sha256`, the digest of
    step 10.

## How to re-derive a sample

Pick any artifact from steps 3–11, rebuild its field map from the inputs and the
digests of the artifacts it depends on, canonicalize by the rules above, and
compare against the literal. Doing this for the seal exercises the widest set of
links, because every earlier digest feeds into it.

Do not re-derive by importing the production modules and printing their output.
That produces a passing comparison with no independent content.

## When the fixture must be regenerated

Any change to the contract bytes, the authority key set, the capture chain, or
the fixture inputs invalidates these literals. Regenerating them is a reviewed
change: the new values need the same treatment as the originals, including a
fresh independent re-derivation of a sampled subset.
