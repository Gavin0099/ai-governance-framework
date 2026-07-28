# Preserved live execution evidence

Copied byte-for-byte from `D:\gate2-live-run-evidence\` on 2026-07-27 so the
completed live-channel history does not depend on that machine-local directory.

## Preserved completed runs

| Run | Transcript SHA-256 | Adapter log SHA-256 |
|---|---|---|
| `live-canary-20260726-161453` | `a5d76d41cb7e166c7ba0010758933773cec667ccf126521895867ff93c9a1b56` | `3ca8ef6e52ad2f9314bf9d1ec524106b3865250eb273c3e9001c387a2c93478b` |
| `live-canary-20260726-172217` | `de5bf4440cae3fd037453343967b33ec47e6dfa01144a0f075713da7f61084c5` | `9758b2729313be2feadaa35c62a0a7f6ecd59b1f125043c2c98cce34c5894f23` |
| `live-canary-20260726-194819` | `24812892271ff5714a5aefd313bd3117d78e477fe267b32c2dfe9c2c3526144d` | `26fb861c8c9a6351bcda14b2057a9e837203c9eb6f6cd4df7040728c7cf872d2` |

Run `live-canary-20260726-180935` is not listed as a completed channel run:
the preserved source directory contains neither a transcript nor an adapter
log, matching the recorded task-design abort in `RUN-CONFIG.md`.

## Scorer-packet admission evidence

The `live-canary-20260726-194819/scorer-packet-candidate/` directory preserves
the operator-owned `result.json` plus byte-exact final diff, status, tracked-path
inventory, packet manifest, and verifier results.

On 2026-07-27:

- `test_scorer_packet.py` passed 11/11 targeted counterexample tests.
- `verify_scorer_packet.py` passed 15/15 against run id
  `live-canary-20260726-194819`, baseline HEAD
  `2cc7a72228e5e24a4794b5b960eae0b196ecc71f`, and container id
  `948d5c9f4a20c37f41e9ef3d94569a13f49c5e5974f2d6693b03781dedc25e9a`.
- `verification-admission-20260727.json` is byte-identical to the prior
  `verification-v2.json`, SHA-256
  `02ca3e1638a5d861875721e68d9a60bd128207bbd32c8ab5d5006743f427113a`.

## Completed Gate 2 formal run

`gate2-formal-20260728-115533/` preserves the sanitized evidence for the
completed four-arm formal run. The frozen `D -> C -> A -> B` order produced
three normal outcomes and one verified terminal-timeout outcome. Both
arm-identity-blind scorers submitted before mapping release, all released
artifacts reverified, and the preregistered process-integrity decision is
`PASS`.

The decision deliberately records Skill effectiveness as `NOT_CLAIMED`; this
single pilot establishes process completion, not general treatment efficacy.

## Claim boundary

This evidence preserves and re-verifies a historical canary scorer packet. It
does not prove the operator identity, report truth, change quality, current
availability of the pinned Docker image, creation of two independent scorer
contexts, completion of resource admission, Gate 2 readiness, or execution of
any arm.

The completed formal-run subdirectory has its own narrower claim boundary and
supersedes those readiness non-claims only for the named
`gate2-formal-20260728-115533` execution.
