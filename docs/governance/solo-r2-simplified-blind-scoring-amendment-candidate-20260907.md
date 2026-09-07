# Solo R2 simplified blind scoring / claim-ceiling adjustment

Status: CANDIDATE / NOT OWNER ADOPTED.
Scope: one prospective decision-support scoring step for the existing completed evaluation; no new run or bundle.

## C01 Purpose and exact scope

Permit a limited comparison of the already-completed Solo R2 outputs without claiming OS-attested scorer isolation or strict end-to-end shakedown PASS. This is an explicit reduction in scorer assurance and claim ceiling, not a statement that the previous ceiling is unchanged.

Applies only to evaluation `74ad1963-e24c-4ced-9f84-32e3c0daf900`, Pair `93584d7e-2bf9-4535-93c8-5593fcd3e272`, slot `R2-SHAKEDOWN`.

The only permitted scoring identity is the already-activated superseding identity:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Superseding bundle | 2796 | `b2097cda3b973b5154b5393d01d2ec98aa662574ba0e529879a405bc67b01bd3` |
| Superseding transition | 1668 | `20b5cfcc131c2e09cf1f9d858666c2f62af4d9a817931a29721cb2d1b4303fb5` |
| Owner activation record | 254 | `9d748ef3746c737c66c146efad4bbfad6d9a919f442257926ba289f12e452218` |
| Frozen rubric | 3754 | `a93a1f3d74ef9a191317d345c5e54f31b309ee481174cfe374f42938db4bfca9` |

The fixed paths and relationships remain those of the existing transition and activation. No arbitrary bundle, replacement identity or caller-selected evaluation is accepted. The current nine-event ledger remains unchanged, SHA-256 `e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77`.

## C02 Claim ceiling and narrow exception

Results under this amendment are limited to `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.

Explicitly NOT CLAIMED:
- OS-level isolation of the actual scorer;
- strict end-to-end Solo R2 shakedown PASS;
- Formal Gate 3 or counted evidence;
- generalized Bug Fix Safety effectiveness beyond this evaluated task.

For this scoring step only, this amendment permits context-level freshness and restricted input delivery instead of requiring OS-attested isolation of the scorer execution. It narrowly adjusts the fresh-scorer execution assurance required by S07 of the adopted superseding policy (SHA-256 `10fc9ad2e7ab83088391ed3beaa705d65fc69f0456142bfd3fb329f5cb77535c`) and the subsequent owner OS-isolation execution requirements for this instance. All remaining identity, history-preservation, correctness, score-freeze and separate-unblinding boundaries remain in force.

Do not claim that an OS verifier passed for a context that did not run inside that boundary. Existing isolation probes retain their original limited evidentiary meaning. AppContainer model integration, local-model discovery and network-scorer sandbox work are POST-GATE3 and are not prerequisites for this decision-support route.

## C03 Preserved evidence

Do not modify, replace, rerun or invalidate the completed arm executions, preserved outputs, verified oracle results, activated superseding bundle, activation record, nine-event ledger, historical rejected bundle/checkpoint, or collected AppContainer/custody/isolation evidence.

The historical rejected bundle remains `NOT_ADMISSIBLE_FOR_SCORING`. This amendment does not restore its admissibility, erase the earlier blindness failure, recover missing historical custody, or imply that the strict scoring path was completed.

## C04 One fresh scorer context

Use exactly one new scorer context with no prior conversation or scoring context from this evaluation. It must not have seen the rejected bundle or been given CONTROL/TREATMENT mapping. Do not fork or copy the current conversation, investigative summaries, execution history or prior review context into it. The current controller/reviewer context cannot serve as the scorer.

Deliver only the activated anonymous scoring materials, the exact frozen rubric, and explicitly permitted correctness information. Use opaque presentation keys; exclude controller-only identity wrappers, repository/workspace or execution identities, mappings, rejected materials and investigation records. Do not alter the preserved bundle to perform delivery.

Restrict the supplied inputs and available capabilities to scoring. Instruct the scorer not to infer, request or obtain arm mapping or other prohibited materials. Preserve a controller-only manifest of the actual fresh context and exact delivered inputs; do not send that provenance manifest to the scorer. This records delivery and declared context freshness, not OS proof that all other information is inaccessible.

If context freshness or restricted delivery cannot be established, or identity leakage is observed, STOP without scoring; do not silently substitute the current context or repair the preserved bundle.

## C05 Blind scoring and freeze

Score both opaque outputs using the frozen rubric. Both outputs have verified oracle correctness of 10/10; quality scoring must not reverse, redefine or rerun that result. Preserve the supplied regression, scope and observed cost statuses rather than inferring missing measurements.

For each opaque output, preserve the four rubric dimensions, permitted 0/1/2 or NOT_ASSESSABLE values, supporting evidence, and the rubric's total rule. Missing evidence remains NOT_ASSESSABLE; do not force a numeric total. Capture and durably freeze both opaque scores and scorer evidence, verify their exact identities, then STOP. Reject malformed, incomplete, identity-leaking or out-of-rubric results.

This amendment permits the first score artifacts for this activated identity after scoring is separately authorized. It does not permit regenerating the bundle, checkpoint, transition, activation or already-frozen scores. Preserve the existing identity-bound score-result semantics; do not fabricate an OS-isolation receipt to satisfy a consumer.

## C06 Unblinding and prohibitions

CONTROL/TREATMENT mapping remains unavailable throughout scoring. Unblinding requires a separate owner authorization after both scores are frozen and verified. No implicit opening follows score completion.

No arm/oracle rerun, nine-event ledger modification, new evaluation/Pair, replacement allocation, second supersession, historical evidence rewrite, A1-A6 progression, Formal/counted claim or push is authorized.

## C07 Interpretation and adoption sequence

A later authorized comparison may state only: "On this single evaluated task, under a Solo-controlled decision-support evaluation, the frozen Bug Fix Safety treatment produced the observed comparison result against the control."

That statement must include the observed limitations; it is not proof of general Skill effectiveness, causal generalization, or completion of strict OS-isolated scoring. A decision-support result does not retroactively upgrade the earlier partial mechanism validation.

This candidate is not authority by its existence or by technical review. Sequence: exact-byte review -> owner adoption of the reviewed bytes -> scoped local adoption commit -> STOP. No adoption or commit is performed by preparing this candidate. Actual scoring/freeze and subsequent unblinding remain separately authorized actions. No production implementation change is authorized by this candidate.
