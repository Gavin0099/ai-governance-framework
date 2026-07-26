# Gate 1 Correction Amendment v4 Candidate — commit-bound scorer handoff

Status: **CANDIDATE ONLY — PENDING OWNER RE-SIGN AND CANONICAL PROMOTION.**
This file does not authorize Gate 2. Amendments v2 and v3 and the frozen
`gate2-scorer-handoff.v2` contract remain canonical until the owner signs the
exact candidate bytes listed here and a later, separate promotion step updates
the preflight manifest.

Source base commit: `13b9abff` (`fix(gate2): bind scorer handoff to output
commit`).

## A. Observed failures requiring this amendment

The correction is failure-driven:

1. Live canaries `172217` and `194819` showed that manual base64 changed the
   producer's solution. In `194819` the producer removed a module docstring to
   reduce transcription risk. The channel is therefore common-mode but not
   evidence-neutral.
2. The immutable `result.json` in `194819` omitted that deletion. A scorer must
   receive the operator-captured final diff, not rely on producer prose.
3. The first scorer packet closed that visibility gap for an uncommitted canary
   workspace, but its `git diff HEAD` model conflicts with the frozen Gate 2
   producer receipt: the receipt requires a clean worktree and
   `linked_commit == output commit`. After a real producer commits, `git diff
   HEAD` is empty.
4. The frozen v2 handoff contract names a four-section `raw-output.txt`, but
   does not mechanically require `FIX_DIFF` to come from the container-bound
   packet or bind the four sections to run/container/commit identities.
5. Independent review of the first v3 candidate showed that its published-set
   verifier checked only internal digest consistency. A coherent rewrite of
   `FIX_DIFF`, `raw_output_sha256`, anon id, packet, receipt and marker still
   passed while the declared source diff digest remained unchanged.
6. The same review reproduced `core.autocrlf=true` checkout rewrites for the
   three canonical files named in Section E and for the unpinned
   `redaction_runner.py` dependency.
7. A second independent review built a digest-consistent scorer packet whose
   tracked-path artifact, workspace inventory and fixed scorer inputs
   contradicted one another. `scorer_packet_v2.verify_packet` rejected all
   three contradictions, but the offline handoff verifier accepted them
   because it rechecked bytes and identity without rechecking packet semantics.
8. The same review found that v3 always built
   `blinding_compromised=null` and required that value during verification.
   An experimenter who correctly flagged a residual identity leak therefore
   could not produce a deterministically verifiable handoff.

These are experiment-validity failures. They do not relax any gate or claim
that the experiment may start.

## B. Scorer-packet schema v2 candidate

`gate2-runtime/scorer_packet_v2.py` is append-only relative to admission-canary
schema v1. It does not rewrite or reinterpret old evidence.

The v2 capture requires:

- a full baseline commit;
- the current full output commit;
- baseline must be an ancestor of output;
- `HEAD == output_commit`;
- an empty porcelain status (clean worktree);
- the fixed receipt path `/work/out/producer-receipt.json`;
- `producer-receipt.json.linked_commit == output_commit`;
- a non-empty binary-capable `git diff baseline_commit output_commit`;
- a sorted tracked-path inventory covered by that diff;
- result, diff, status, path inventory and raw receipt bytes in fixed paths.

The manifest `scorer-packet-v2.json` is written last. Every component is
create-once and atomically written; any publish failure removes all partial
finals. Verification is not manifest-only: it re-reads the named running
container and requires exact equality for container id, commits, result, diff,
status, tracked paths and receipt bytes.

Claim boundary: this proves byte and identity linkage to the observed running
container. It does not authenticate the operator or prove the fix, result or
receipt is truthful.

## C. Scorer-handoff v3 candidate

`candidate/scorer-handoff-contract-v3.json` and
`gate2-runtime/scorer_handoff_v3.py` require a live-verified schema v2 packet
before assembling the scoring input.

The four sections are mapped exactly:

| Section | Source |
|---|---|
| `FIX_DIFF` | `scorer_packet.artifacts.diff` |
| `TEST_LOG` | operator-captured post-fix test log |
| `VALIDATOR_OUTPUT` | uniform post-hoc validator output |
| `COMPLETION_CLAIM` | immutable `scorer_packet.artifacts.result` |

All section bytes must be non-empty UTF-8/LF and may not contain a reserved
standalone marker. The unredacted four-section value stays in experimenter
memory. The published set is:

- `redacted-packet.json`;
- `redacted-receipt.json`;
- `scorer-handoff-v3.json`, written last as the completeness marker.

The marker binds the candidate contract, source packet, run id, baseline
commit, output commit, container id, every source artifact, section mapping,
redacted packet, anonymized receipt and anon id. Missing output, output tamper,
source omission, wrong identity, wrong digest, path substitution, output alias
or simulated publish failure rejects the set.

Mechanical verification is reproduction, not published-set self-consistency.
Before scorer delivery, the experimenter or owner verifier must read the exact
pinned scorer-packet v2 set, test log, validator output, candidate contract and
pinned `redaction_runner.py`; deterministically rebuild the packet and
anonymized receipt; and compare their canonical bytes plus the marker against
the published set. Identity-bearing source material is not released to the
arm-identity-blind scorers. They receive only the verified redacted set and the
identity-free verification result.

Offline reproduction also rechecks the three packet semantics that previously
existed only in the live packet verifier: every captured tracked path must
appear in the diff, the manifest workspace inventory must equal the captured
path artifact, and `scorer_input_core` plus required attachments must equal the
fixed contract values. Digest-consistent contradictions fail before handoff
reconstruction.

The experimenter may supply
`--blinding-compromised-reason <non-blank reason>` to both build and verify.
When absent, the packet deterministically contains null flag and reason. When
present, the flag is true and the exact reason string is preserved. Omission,
substitution or any string change at verification fails source reproduction;
substantive evidence is never removed.

If any arm source contains CR or a reserved standalone marker, the complete
four-arm run is **NO-GO before scoring**. The experimenter must not selectively
exclude, repair or rerun one arm. Any escaping or recapture rule requires a
separately reviewed owner amendment and a fresh run of every arm.

The v3 contract deliberately contains `frozen=false` and every output states
`pending_owner_resign`. A mechanically valid candidate is not authorized.

## D. Base64 common-mode treatment effect

The owner is asked to pre-register this exact interpretation:

- all four producers use the same argv-only adapter and base64 write/report
  body mechanism;
- the burden is common-mode but may affect producer behavior and solution
  quality;
- scorers receive the complete operator-captured diff and may score resulting
  quality loss normally;
- there is no score normalization or post-hoc adjustment for base64 burden;
- a plaintext shell write verb is not introduced because it would reopen
  quoting, metacharacter and injection surfaces;
- common-mode exposure does not prove equal behavioral impact across arms.

This is an experimental-design acknowledgement, not a claim of treatment
neutrality.

## E. Append-only candidate map and exact hashes

The existing bytes remain canonical and unchanged:

| Existing canonical file | SHA-256 |
|---|---|
| `scorer-handoff-contract.json` | `e8945c4b7eee256c96e6c7f21beef02f885b9f6c7caf6b2b65197088bcd5226a` |
| `gate1-prereg-prepush-amendment-v2-20260724.md` | `eb1a7747e51bd01566ee04d17123cab5262452961f53631d8769fe392f8a9c64` |
| `gate1-prereg-prepush-amendment-v3-20260725.md` | `376fd1f4fc9a1915e2240b6ba4d97d1163158f711e60948c7e20a175d588bdd3` |

Candidate bytes offered for review and later owner re-sign:

| Candidate file | Bytes | SHA-256 |
|---|---:|---|
| `.gitattributes` (exact candidate/evidence paths only) | 1,233 | `5a5b522aa46a62724dc804c2ee4a1ef9f2e04bc614cce8eb31c4b7ec5d2793c3` |
| `candidate/scorer-handoff-contract-v3.json` | 8,631 | `ced0e02c815494b5f66d6ceffa8dd7e490ac8f880adf935686579b7b69426eda` |
| `redaction_runner.py` (pinned semantic dependency; unchanged) | 16,152 | `d612f75e0851239fe164f9918fd13e55416f7fff9b1f337ad3f54460a91955d5` |
| `gate2-runtime/scorer_packet_v2.py` | 23,520 | `a96711338ed5b873660fde892cc32b0b28cd25deaa440c4f67b1571371bbb40e` |
| `gate2-runtime/scorer_handoff_v3.py` | 41,857 | `8de66027f66552ff4ca750e88ac6ec77c471cd3b3c27394d6c28e830c7f5c417` |
| `gate2-runtime/test_scorer_packet_v2.py` | 12,558 | `724250f537201e3ac4aa173b41ba6a786c7846807e1f7577bbd9c10e561e5055` |
| `gate2-runtime/test_scorer_handoff_v3.py` | 32,588 | `2d2497cd94628c71cd612ae2d88069f5b2192e9bb44d9f0401f75ea0a07b9a5a` |

Any edit changes the hash and requires a new review/signature target. Do not
rewrite amendment v2/v3 or the frozen v2 contract in place.

## F. Candidate validation before signature request

Targeted evidence already required by this candidate:

- scorer-packet schema v2 counter-examples: 14/14;
- scorer-handoff v3 counter-examples: 20/20;
- frozen v2 redaction runner regression: 23/23;
- candidate scripts compile;
- candidate contract parses as JSON.

The canonical focused precommit and the final candidate receipt must also pass
before the owner is asked to sign. These are evidence for review, not owner
signature and not canonical promotion.

`CANDIDATE_FILE_SET`, `CANONICAL_FILES` and `BYTE_PRESERVATION_PATHS` are
declared in `scorer_handoff_v3.py`, which is itself a candidate member. An
independent reviewer must inspect the verifier source diff as well as run
`verify-candidate`; the verifier cannot independently establish the
completeness of its own hard-coded declarations.

## G. Owner decisions required after review

The later re-sign request must ask the owner to confirm all three:

1. the exact v3 contract and runtime hashes in Section E;
2. the Section D base64 common-mode interpretation;
3. that a later promotion may supersede scorer-handoff v2 only, without
   changing producer treatments, arm order, budgets, validators or scoring
   release gates.

Owner confirmation is not inferred from authorizing implementation of this
candidate. It must be a separate explicit re-sign after review.

## H. Promotion and execution remain separate

Even after re-sign:

1. update the canonical preflight manifest in a separate promotion slice;
2. perform resource admission for four answer-blind producers, two
   arm-identity-blind scorers and the out-of-band runner;
3. stamp model build, permissions, validator installation and per-arm dispatch;
4. obtain a separate explicit owner `start Gate 2` command.

No step in this candidate starts an arm.

## Cannot claim

- That this candidate is owner-signed, frozen or canonical.
- That scorer-handoff v2 has been superseded.
- That packet or handoff writers are cryptographically authenticated.
- That coordinated direct writers cannot fabricate a coherent set.
- That the base64 burden affects all arms equally.
- That a scorer will interpret the diff correctly.
- That required producer/scorer resources exist.
- That Gate 2 may start or that any arm has run.
