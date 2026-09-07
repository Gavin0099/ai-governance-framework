# Solo R2 single superseding scoring / sealing authority candidate

Status: CANDIDATE / NOT REVIEWED / NOT OWNER ADOPTED.
Purpose: one prospective recovery of scoring preparation for an already completed Pair; no execution retry.

## S01 Problem and current repository truth

Execution completed and both frozen-oracle evaluations passed 10/10. The sealed bundle failed the frozen rubric's blindness boundary because final-response text contains filesystem custody and execution chronology. No quality scores were produced; no unblinding occurred. Parser acceptance and successful sealing do not establish admissible blindness.

Evidence: memory/evidence/solo-r2-final-scoring-sealing-20260907/result.json and verification.json; memory/evidence/solo-r2-final-blind-scoring-20260907/result.json; memory/evidence/solo-r2-final-oracle-20260907/verified-summary.json.

At baseline commit 2ae93b86c14ed06ac5bb643aefe40117e77e0487:
- solo_r2_disposable_execution.prepare_final_scoring_continuation accepts the adopted eight-event prefix and refuses an existing SCORING_BOUND; it is not a replacement entrypoint.
- solo_r2_controller_state.validate_state_transition permits ATTEMPT_BOUND -> SCORING_BOUND, not SCORING_BOUND -> SCORING_BOUND.
- solo_attempt_ledger_v2.validate_ledger_events accepts CONTROLLER_STATE_SEALED only from ATTEMPTS; SCORING_RECORDED and UNBLINDING_RECORDED must reference the one sealed digest.
- solo_r2_lifecycle_integration.prepare_scoring writes a create-once checkpoint/bundle. Its existing score/unblinding methods use the ledger digest.
- Parent execution E11 requires a fresh scorer. Frozen rubric lines 52-57 require STOP on identity/chronology exposure.

There is no existing authority or production support for supersession. This candidate proposes an explicit instance-limited contract exception, not an interpretation that the old transitions already allow it.

## S02 Exact historical binding and preservation

Applies only to evaluation 74ad1963-e24c-4ced-9f84-32e3c0daf900, Pair 93584d7e-2bf9-4535-93c8-5593fcd3e272, slot R2-SHAKEDOWN.

Historical artifacts (SHA-256 over original bytes):
- Ledger: artifacts/evidence/solo-r2-final-disposable-mechanism-shakedown-20260907/attempt-ledger.v2.1.ndjson; 5193 bytes; nine events; e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77.
- Old bundle: D:/r2-final-disposable-shakedown-20260907/scoring/2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.blind-scoring-bundle.json; 3055 bytes; f0e8af8750182d6dc4bacd5b7f0c280f8b0acccd1dc57ea7844c2fcff5516dce.
- Old checkpoint: D:/r2-final-disposable-shakedown-20260907/controller/2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.scoring-bound.sealed.json; 3074 bytes; 243e6c2defc1272347b940e8ac20786e0e52f626216ff71a43cf34b3a5243558.

All remain exact and unchanged, including after any future scoring or unblinding. Do not append a tenth event through this path, rewrite the ninth event, migrate the ledger, delete, rename or overwrite either historical scoring artifact. Disposition is recorded externally: old bundle NOT_ADMISSIBLE_FOR_SCORING, reason BLINDNESS_IDENTITY_LEAKAGE. This changes admissibility prospectively, not the recorded history of sealing.

## S03 Preserved source authority

Reuse the exact prospective input authority at commit 7a23b95afa09485d8321b638227bf631e2ddad12, memory/evidence/solo-r2-final-scoring-continuation-adoption-20260907/owner-adoption.json, 7664 bytes, SHA-256 6d93cbb66eafdb13d9da7a3572a263a3625faa60f2da01c032f8993a2e614066.

It fixes the two terminal sources, final messages, runtime evidence, oracle originals/corrections, input authority and rubric. Verify all its 22 identities: its historical eight-event ledger identity is checked against the first eight complete lines of S02's nine-event ledger, never by rewriting or truncating the file. Every other artifact still requires its original exact bytes. The absent historical ATTEMPT_BOUND expected-digest custody remains absent; this is prospective adoption, not recovery of original live controller authority.

Frozen rubric: artifacts/experiments/solo-r2-disposable-input-definition-20260906/rubric.candidate.md; 3754 bytes; SHA-256 a93a1f3d74ef9a191317d345c5e54f31b309ee481174cfe374f42938db4bfca9. Frozen input authority SHA-256 5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb. Preserve existing v2.1 schema ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab, protocol 1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff and execution contract 3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea as parent identities; this candidate's externally adopted digest is the explicit supplemental authority.

Two oracle results remain 10/10 PASS. Preserve original CRLF aggregation failure and correction provenance; do not rerun oracle or reinterpret agent-reported local validation as evaluator PASS. No additional source, test file or rewritten explanation may silently enter scoring; absent evidence remains NOT_ASSESSABLE as the rubric requires.

## S04 Proposed authority mechanism and fixed placement

Exactly ONE detached superseding scoring instance, with a fixed revision of 1. This is a scoring-only allocation, not a new evaluation, Pair, arm Attempt, retry or fresh experiment. No generic registry or repeated revisions.

Under D:/r2-final-disposable-shakedown-20260907, use only:
- controller/superseding-scoring-1/ for private transition inputs, sealing receipt, adoption and consumption records;
- scoring/superseding-scoring-1/blind-scoring-bundle.json for the new scorer delivery;
- controller/superseding-scoring-1/scoring-bound.sealed.json for the new encrypted checkpoint;
- controller/superseding-scoring-1/transition.json for the proposed exact relationship;
- controller/superseding-scoring-1/owner-activation.json for later exact-byte owner activation;
- controller/superseding-scoring-1/scores-frozen.json for a later controller-only score manifest;
- controller/superseding-scoring-1/unblinding-receipt.json for a separately authorized later opening receipt.

These are proposed paths, not created by this candidate. Existing custody separation applies: scorer cannot read controller root, historical bundle, ledger, attempt artifacts, keys, record manifests or this investigative conversation. Controller key remains at its existing verified private path; never print mapping or key. Scorer receives only a delivery of the new bundle and frozen rubric. Result storage must be outside scorer input and identity joins remain controller-only.

Before generating labels or sealing, verify exact policy adoption from an independent owner-supplied committed identity, S02/S03, custody ACLs/identity, no links/reparse/path substitution, no scores/unblinding, and absence of the entire superseding instance. Do not infer expected digests from current disk or filenames. A create-once reservation in the fixed controller directory consumes this single generation opportunity. Partial I/O failure leaves preserved FAILED evidence, never automatic deletion/retry or activation.

## S05 New identity generation and owner activation

The proposed transition is a detached instance: HISTORICAL_SEAL_REJECTED -> SUPERSEDING_CANDIDATE -> OWNER_ACTIVATED -> SCORES_FROZEN -> separately authorized OPENED. It does not add SCORING_BOUND -> SCORING_BOUND to the generic controller or append another legacy sealing event.

Use the existing encrypted state and bundle formats. Internally authenticate old checkpoint using S02's expected digest and original key/AAD; preserve exact evaluation, Pair, immutable arm bindings, order and terminal-output references. Do not reconstruct arm mapping from chronology or expose it. Only new independent scoring labels/presentation order and scorer payload projection change. Reject new-label collisions with historical labels and handles; do not redraw after collision. Use fresh CSPRNG presentation entropy and AEAD nonce; reject nonce reuse against preserved packages. No cross-restart nonce-proof framework is claimed.

After complete validation, generate one candidate bundle and one new encrypted checkpoint; compute byte lengths and SHA-256 from final persisted bytes and verify by readback. Keep them inadmissible until owner activation. transition.json canonically encodes evaluation_id, pair_id, revision=1, policy adoption identity, exact historical ledger/bundle/checkpoint identities, exact source-adoption identity, new bundle/checkpoint identities, old disposition NOT_ADMISSIBLE_FOR_SCORING and state SUPERSEDING_CANDIDATE. No mapping, labels-to-handles, plaintext digest, key or entropy belongs in it. Canonical JSON means UTF-8, no BOM, sorted keys, compact separators, ASCII escaping and one LF; hash exact persisted bytes, not reserialization.

STOP for a separate owner adoption of the ENTIRE transition.json exact bytes and its referenced new identities. No new digest is fabricated in this candidate. owner-activation.json must record that explicit decision and exact transition bytes/digest; an OWNER_ATTESTED field or an auto-created file alone is not adoption proof. The later consumer must receive the expected owner-activation identity independently from the owner's decision, not trust a disk self-hash.

Only the tuple (adopted policy identity, owner-activation identity, transition identity, evaluation, Pair, historical nine-event digest, new bundle digest, new checkpoint digest) authorizes downstream consumption. Missing activation means neither old nor new bundle is score-admissible. Once activated, ONLY new digest is eligible; old/mixed/unadopted digests always reject. Do not use newest-file, last-modified, path membership or latest-record heuristics. No second supersession, reactivation or replacement labels after failure.

## S06 Narrow parent-contract exception and downstream binding

For this exact Pair only, adoption proposes an exception to parent L04 lifecycle routing, L09 one-final-state interpretation and L12 ledger-based scoring/opening digest selection: the detached activated identity replaces the old ledger digest as scoring/opening authority. The nine-event ledger remains a historical execution/sealing ledger, not a complete record of the detached scoring lifecycle. This limitation must be explicit in reports; the ledger alone cannot establish current scoring admissibility.

Do not call legacy acknowledge_score or authenticate_synthetic_unblinding for this instance: they refer to the old digest and append legacy events. No generic ledger/schema/transition validator is relaxed. All original non-superseded evaluations retain existing behavior.

A narrow instance-specific consumer validates S05's complete tuple at scoring dispatch, score freeze and authorized opening. It freezes exactly two score artifacts keyed only to new opaque labels, records their bytes/digests and new checkpoint/bundle identities in the create-once private scores-frozen manifest, and verifies both before opening. Missing/duplicate scores, wrong labels, modified scores or mismatched tuple reject. It cannot accept a mere score_count=2 flag. Later opening authenticates only the new checkpoint, with the same key/AAD and immutable binding checks, after separate owner authorization. A private opening receipt binds activation and frozen-score identities; do not publish mapping to ledger, Git or ordinary stdout. Any arm-attributed report needs separate owner authority.

This exception and its detached receipts require exact-byte owner adoption before implementation; candidate acceptance alone grants nothing. Existing E11 ordering, frozen rubric and blindness requirements remain intact. Explicit scope is a new, inspectable scoring authority, not restoration of original controller continuity.

## S07 Identity stripping and fresh scorer

Transform ONLY the scorer projection of preserved outputs, never the originals. Remove identity-bearing link destinations, absolute/local custody paths, execution ordinals and equivalent provenance joins in free text and nested fields. Preserve repair code, substantive reasoning, validation claims, limitations, correctness and observed costs; do not improve prose, hide contradictory claims or invent tests/results. Store a controller-only deterministic transformation receipt linking original and projected identities. If identity removal cannot preserve evaluative meaning, STOP as unresolved, not silently discard substantive evidence.

Run both structural validation and a semantic boundary check over the complete projected payload before candidate sealing. Reject encoded/escaped path or chronology variants, embedded identity labels, mapping, hashes or metadata joins. No regex PASS alone establishes blindness. The same source bytes may occur in both outputs; do not salt hashes to manufacture differences.

Fresh scorer means a separate context with no old bundle, execution history, handles, mappings, this conversation or inherited investigative summaries. The current context cannot score the replacement. Enforce restricted scorer inputs/capabilities, not merely an instruction to ignore earlier knowledge. Preserve a controller-only input manifest identifying exact bundle/rubric delivery. If isolation or freshness cannot be shown, STOP. Correctness stays 10/10 for each opaque output; regression/scope/cost evidence retain their original statuses. Quality totals remain NOT_ASSESSABLE if required evidence is absent.

Fresh scores must freeze before any separately authorized unblinding. This policy, artifact generation and artifact activation each independently confer NO scoring or unblinding execution permission.

## S08 Minimum implementation allowlist and boundary considerations

Proposed only; no implementation authorized now:
- NEW governance_tools/solo_r2_superseding_scoring.py: fixed-instance detached authority, generation, activation verification, consumption and receipt handling. Concrete dependency: legacy sealed Pair cannot reseal or select a new digest. No arbitrary evaluator/registry API.
- governance_tools/solo_r2_blind_scoring_bundle.py: complete payload leakage validation for the observed free-text hole; preserve existing bundle shape.
- tests/test_solo_r2_superseding_scoring.py: isolated end-to-end candidate/activation/score/opening simulations, never real arms/oracle or real custody.
- tests/test_solo_r2_blind_scoring_bundle.py: directly related leakage and legitimate-content regressions.

Reuse existing crypto validation, bundle construction, input binding and filesystem custody helpers without modifying them. No changes to solo_attempt_ledger_v2.py, solo_r2_lifecycle_integration.py, execution launcher, runtime window, allocation, cost model or frozen inputs. If a concrete required dependency cannot be satisfied within this allowlist, STOP and document it before extension. The blind-scoring bundle module IS R1-bound: its eventual implementation commit requires the separate immediate R1 refresh under existing rules. No refresh now.

Proposal-time architecture preview used identical before/after execution-module paths and reported medium / review-required, error-path coverage. It is provisional tooling output, not evidence this future implementation is safe. Actual implementation review must cover changed bytes and error paths.

## S09 Required negative and positive evidence

Positive: isolated preserved nine-event fixture -> validated candidate artifacts -> explicit exact adoption fixture -> fresh scorer delivery -> two frozen scores -> separately authorized opening using new digest only. Assert original ledger and artifacts unchanged at every stage; no arm/oracle execution.

Negative: old digest; new digest without independent owner activation; altered transition/activation; wrong policy/evaluation/Pair/source/rubric/oracle; mixed old/new bundle/checkpoint; changed nine-event prefix; second generation/reservation/replay; reused labels/nonce; preexisting paths/reparse/hardlink/ACL ambiguity; invalid generation leaving no ACTIVE identity; identity-bearing free-text/Markdown/encoded variants; mapping handed to scorer; stale/non-fresh scorer context; dropped substantive evidence; missing/changed/duplicate score or wrong label; unblinding before score freeze or without separate authorization; legacy consumer used for detached identity. Each rejects without historical mutation or disclosure.

Tests must include failure after reservation, checkpoint creation and bundle write: partial files remain quarantined/inadmissible, no active identity or success claim. No cleanup/retry authority is inferred. Public records and scorer delivery must not leak any label-to-attempt/arm join. Parent v2/v2.1 non-superseded validation remains unchanged.

## S10 Unresolved prerequisites, claim ceiling and stop

Unresolved: exact-byte review/adoption of this policy; separately authorized implementation/review/commit and R1 refresh; verified new custody paths and fresh scorer isolation; artifact-generation authorization; exact newly generated transition/bundle/checkpoint identities; independent owner activation; later scoring and unblinding permissions. None is already satisfied by writing this document. No new evaluation ID, scoring label, entropy, nonce or artifact digest is generated now.

Existing hard stop against further experiment allocation remains. A failed superseding generation does not authorize another attempt at generation; a rejected fresh bundle does not authorize revision 2. If review rejects the detached contract exception or necessary isolation cannot be established, retain partial mechanism-validation closeout with no additional execution.

DONE for this slice: one reviewable exact-byte candidate, implementation allowlist, negative tests and unresolved prerequisites reported; STOP before adoption, production, ledger changes, artifact generation, scoring, unblinding, commit or push.

Claim ceiling: proposed authority only. Existing execution and oracle remain validated; complete shakedown, successful blind scoring, Skill effect, Formal/counted evidence and A1-A6 progression remain unclaimed.
