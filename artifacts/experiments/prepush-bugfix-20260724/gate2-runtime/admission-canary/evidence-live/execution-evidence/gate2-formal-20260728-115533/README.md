# Gate 2 formal execution evidence

This directory preserves the sanitized, reviewer-facing evidence for formal
master run `gate2-formal-20260728-115533`, executed on 2026-07-28.

## Result

- frozen producer order: `D -> C -> A -> B`
- counted outcomes: `D=complete`, `C=terminal_timeout_complete`,
  `A=complete`, `B=complete`
- two arm-identity-blind scorer submissions are preserved; their ordering
  relative to mapping release is not independently established
- scorer model alias: `haiku`
- mapping release: complete
- artifact verification: `PASS`
- Gate 2 process integrity: `NOT_ESTABLISHED`
- Skill effectiveness: `NOT_CLAIMED`

The pinned image remained:

`sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`

## Preserved evidence

- `resource-admission.json` and `resource-audit.json` preserve the pre-run
  admission gates.
- `pre-mapping-scoring/` preserves both independent scorer submissions and
  the operator-recorded gate state. It does not contain a create-once
  timestamp, digest, or receipt chain proving both submissions existed before
  mapping release.
- `anonymous-outcomes/` preserves the three redacted scorer-handoff v3
  packets and the arm-blind terminal-timeout v1 packet, together with their
  release reverifications.
- `mapping-release.json`, `preregistered-decision.json`, and
  `artifact-verification-summary.json` preserve the post-submission release,
  frozen decision, and final artifact checks.
- `scorer-model-verification.json` records the model builds observed in the
  omitted raw scorer envelopes and binds that observation to their SHA-256
  digests.

At preservation time, copied packet and verification files were reported as
compared byte-for-byte with the machine-local operator evidence directory. That
external directory is not available in this checkout, so this correction does
not independently replay that comparison.

## Deliberately omitted

The repository copy excludes raw Claude streams, transcripts, prompts, scorer
session identifiers, container archives, absolute operator-private paths, and
the non-redacted operator packets. Sanitized packet metadata retains container
resource correlation identifiers, and the timeout-cleanup evidence retains its
process ID. The verified external-rate-limit attempt remains in the unavailable
operator evidence directory and is not reproduced here.

## Claim boundary

The preserved artifacts establish four scorable outcomes, two scorer
submissions, a mapping release, and successful packet/handoff verification.
They do not contain an independently verifiable receipt chain establishing that
both submissions preceded mapping release, so Gate 2 process integrity is
`NOT_ESTABLISHED`. They also do not establish that any treatment is generally
effective, that one pilot predicts future results, or that the framework is
correct.
