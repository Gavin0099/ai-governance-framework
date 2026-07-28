# Gate 2 formal execution evidence

This directory preserves the sanitized, reviewer-facing evidence for formal
master run `gate2-formal-20260728-115533`, executed on 2026-07-28.

## Result

- frozen producer order: `D -> C -> A -> B`
- counted outcomes: `D=complete`, `C=terminal_timeout_complete`,
  `A=complete`, `B=complete`
- both arm-identity-blind scorers submitted before mapping release
- scorer model alias: `haiku`
- mapping release: complete
- artifact verification: `PASS`
- preregistered Gate 2 process-integrity decision: `PASS`
- Skill effectiveness: `NOT_CLAIMED`

The pinned image remained:

`sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`

## Preserved evidence

- `resource-admission.json` and `resource-audit.json` preserve the pre-run
  admission gates.
- `pre-mapping-scoring/` preserves both independent scorer submissions and
  the gate proving both existed before mapping release.
- `anonymous-outcomes/` preserves the three redacted scorer-handoff v3
  packets and the arm-blind terminal-timeout v1 packet, together with their
  release reverifications.
- `mapping-release.json`, `preregistered-decision.json`, and
  `artifact-verification-summary.json` preserve the post-submission release,
  frozen decision, and final artifact checks.
- `scorer-model-verification.json` records the model builds observed in the
  omitted raw scorer envelopes and binds that observation to their SHA-256
  digests.

All copied packet and verification files were compared byte-for-byte with the
preserved source under
`D:\gate2-live-run-evidence\gate2-formal-20260728-115533`.

## Deliberately omitted

The repository copy excludes raw Claude streams, transcripts, prompts, scorer
session identifiers, container archives and IDs, process IDs, absolute
operator-private paths, and the non-redacted operator packets. The verified
external-rate-limit attempt remains preserved in the operator evidence
directory but is not reproduced here because it contains operator-private
paths and resource identities.

## Claim boundary

`PASS` establishes that the frozen Gate 2 process completed with four scorable
outcomes, two pre-mapping scorer submissions, mapping release, and verified
artifacts. It does not establish that any treatment is generally effective,
that one pilot predicts future results, or that the framework is correct.
