# Solo Evaluation Revision 2 — Owner Adoption

Status: **OWNER DECISION / ADOPTED**

Date: 2026-08-31

Scope: adoption of the exact Solo Evaluation Revision 2 normative authority set only

## 1. Decision

The owner adopts the following three artifacts together as one indivisible Revision 2 authority set. No artifact is adopted alone, and a path, title, commit, blob or SHA-256 mismatch means the set is not the adopted set.

| Artifact | Canonical path and exact title | Commit / blob / SHA-256 | Normative anchors |
|---|---|---|---|
| Protocol R2 | `docs/governance/solo-engineering-skill-evaluation-protocol-revision-2-20260831.md`; **Solo Engineering Skill Evaluation Protocol — Revision 2** | commit `4ba542ba11be7a29bb0621e84632cfecaaf58984`; blob `1e774d9dcf4a4929162caa25822ca54bde7244b0`; SHA-256 `1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff` | P01–P18 |
| Execution Contract R2 | `docs/governance/solo-evaluation-execution-contract-revision-2-20260831.md`; **Solo Evaluation Execution Contract — Revision 2** | commit `4ba542ba11be7a29bb0621e84632cfecaaf58984`; blob `5eb26f6b0b9229ee43a5ac1cf958eb763a2d6c9b`; SHA-256 `3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea` | E01–E12 |
| Ledger Schema v2 | `docs/governance/solo-attempt-ledger-v2-schema-implementation-contract-20260831.md`; **Solo Attempt Ledger v2 — Schema and Implementation Contract** | commit `4ba542ba11be7a29bb0621e84632cfecaaf58984`; blob `56ba6f86dc9e5f58430e8716a6f08188e8985d65`; SHA-256 `d64d9f881a07947b363ef12d2c53e8628dcd4b4dabbf89ba3cbd42f4131d01bb` | L01–L13 |

The exact set received `R2_CROSS_DOCUMENT_EXACT_IDENTITY_REVIEW_PASS` before this decision. That review disposition is evidence for adoption; it is not a fourth normative artifact.

## 2. Supersession and legacy state

This decision prospectively supersedes the legacy Solo protocol, legacy execution contract and `solo_attempt_ledger.v1` with the adopted R2 set. Legacy bytes, Git history, v1 ledger and disclosure evidence remain immutable historical evidence and are not rewritten, sanitized, migrated or deleted.

Under adopted P05, legacy Pair `solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040` now has permanent protocol-level disposition `PRE_ATTEMPT_TERMINATION`. It remains historical evidence with zero Attempt IDs. This adoption appends no v1 event, creates no v2 event and does not reuse, resume or replace that Pair.

The full reference design, SHA-256 `f9815202d15d3b4bb9c77136088fb8be623bb2700f83cf7c79c875038ed7d339`, remains unchanged reference-only material. The reviewed Solo-profile design source, SHA-256 `e0cd3d4fca39c37c9baad8b0ef2b976cdff910ce997b95c6b241e644e4178741`, remains design provenance; the three identities in Section 1 are the adopted normative authority set.

## 3. Authority boundary

This decision satisfies the exact-identity adoption prerequisite in P02. It does **not** authorize:

- implementation of the v2 ledger, controller state, encryption, bundle, scorer or unblinding interfaces;
- creation of `V2_GENESIS`, an R2-SHAKEDOWN Pair, any analytic Pair or any Attempt handle/ID;
- task exposure, arm execution, oracle execution, scoring or unblinding;
- mutation of the legacy Pair lifecycle or v1 ledger;
- network activity, credential/key creation, cleanup, unrelated backlog work or push.

Implementation and execution remain separate later owner-authorized slices. Adoption cannot be cited as either authority.

## 4. Claim ceiling and evidence routing

All R2 results remain `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`. This adoption does not produce evidence, establish Skill effectiveness, repair prior evidence, reopen provider research or alter Formal Gate 3's `NOT_ESTABLISHED / STOPPED` disposition and zero counted-evidence census.

No implementation conformance, shakedown PASS, anonymization effectiveness, scoring isolation or execution readiness is claimed. The next action, if any, must name its own bounded authority and preserve this record and all three adopted identities unchanged.
