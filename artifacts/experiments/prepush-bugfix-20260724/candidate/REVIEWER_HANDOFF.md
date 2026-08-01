# Gate 3 Preregistration — Reviewer Handoff

Branch `codex/gate3-gpt-live-canary-v3-clean`, prepared 2026-08-01.

| | Commit |
|---|---|
| Candidate manifest | `38e2bf33…0ccedfb6` |
| Supersedes | `51ac1219…a5a6801`, changed by the semantic review below |

This document is not itself a candidate file, so it does not appear in the
manifest. Submit against the branch head.

## What is being asked of you

Independent review of the preregistration candidate bytes, so the owner can
sign them. Nothing here authorizes Gate 3, and nothing here asks you to
approve the acceptance implementation — that is deliberately not part of the
signed set. See the four sections below; they are separate on purpose and
should not be reviewed as one thing.

Counted Gate 3 execution stands at zero. No successful scorer packet exists.

---

## 1. Candidate bytes the owner will sign

**This is the review target.**

Manifest: `artifacts/experiments/prepush-bugfix-20260724/candidate/gate3-preregistration-amendment-v1-candidate-manifest.json`
Manifest SHA-256: `38e2bf33373aab25350ceba21734ea334453682119f71a533465e80c0ccedfb6`
Declared base commit: `3dbafc7f8f75feba485167b09d85345a3c7ac9cc`

Six files, all verified byte-intact against the manifest as of this handoff:

| SHA-256 (prefix) | Bytes | Path |
|---|---|---|
| `5f4dc9e7…` | 6447 | `.gitattributes` |
| `84d0265b…` | 16704 | `docs/governance/gate3-preregistration-amendment-v1-candidate-20260729.md` |
| `9ea0ed43…` | 4433 | `artifacts/…/candidate/gate3-harness-contract-v1.json` |
| `11fce85f…` | 7164 | `artifacts/…/candidate/gate3-protocol-contract-v1.json` |
| `223e63b0…` | 81295 | `artifacts/…/gate3-runtime/gate3_evidence_chain.py` |
| `8c7e88eb…` | 54572 | `artifacts/…/gate3-runtime/test_gate3_evidence_chain.py` |

To re-verify independently, start with the narrow check. It reads the manifest
and the six files and nothing else, so it has no side effects and its failure
modes are unambiguous:

```bash
python artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3_evidence_chain.py verify-candidate --repo-root . --manifest artifacts/experiments/prepush-bugfix-20260724/candidate/gate3-preregistration-amendment-v1-candidate-manifest.json
```

Expect `status=PASS`, seven checks — the six files plus
`byte_preservation_attributes_complete` — and the manifest SHA-256 above.

Only if you want the second layer of evidence, that the candidate bytes also
drive a working rehearsal end to end, run the fuller build. It writes a
scratch tree:

```bash
python artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3_common_harness.py build --repo-root . --out <scratch-dir>
```

Expect `status=PASS`, seven of seven checks including `candidate_exact_bytes`.
Both were re-run at handoff time and passed.

The manifest's own `not_claimed` list is authoritative and unchanged:
independent approval, owner signature, canonical promotion, safe structured
write harness, natural bug admission, Gate 3 start, cryptographic writer
authentication, Skill effectiveness.

---

## 2. Acceptance implementation — NOT in the signed set

`gate3_codex_live_canary.py` and `gate3_wrapper_semantic_contract.py` are
**not** members of the candidate manifest. Verified: neither path appears in
it. They serve the final non-counted Codex route canary only.

They have been independently reviewed on their own track and approved. The
policy digest moved during the preregistration semantic review: that review
required the scorer packet to carry an exact field set, and the canary's own
packet builder emitted a field outside it, so the canary had to change. The
move is a consequence of a required fix, not drift. Current identity:

| | SHA-256 |
|---|---|
| Acceptance policy digest | `1f23b94a80e41c76fe9966e382c6069235b0a6c4335c7c1c673bb6a8f9bd1ba9` |
| Semantic contract | `b000d3bc34f21a958d3d7b14f5c00c82e7ef94fb68b3d3f2ffca051f15b49c13` |
| Route validators | `f67f9ec7da08ca0c71511123616f29741070674f8db4685fd821dd81e07c162b` |

What the policy admits: cosmetic wrapper variance only — whitespace, key order,
quoted keys, the result variable's name, a trailing semicolon, direct
text-await, an inline patch argument. What it refuses: extra fields including
execution bounds, privilege-affecting fields, multiple calls, out-of-route
tools, unvalidated envelopes, duplicate fields, and any value the route's own
validation rejects. `TOLERATED_FIELDS` is empty by owner decision of
2026-08-01.

The policy digest pins the content of both files, so **any edit to either,
including a comment, moves it**. Treat it as frozen from here to the final
canary. It is final only for as long as neither file is touched.

---

## 3. Historical Codex route evidence

Five non-counted negative results, retained under
`artifacts/…/gate3-runtime/evidence-live-canary/`:

| Run | Outcome |
|---|---|
| v1 `20260730-145456` | terminated at private cleanup verification |
| v2 `20260730-175032` | `packet_build`, pinned world_state assumption |
| v3 `20260731-114500` | `route_prepare`, zero session invocations |
| v4 `20260731-121500` | `packet_build`, arm A source parse failure |
| v5 `20260731-184000` | `packet_build`, arm A clean both phases, arm B source failure |

**Scope of what the policy digest change invalidates, stated narrowly.** Codex
live-route receipts carrying an earlier `acceptance_policy_sha256`, and
evidence whose verification depends on that field, are refused by the current
route verifier. That is intended fail-closed behaviour and makes exactly that
material historical: it attests to what happened under the policy of its day.

It reaches no further. The common-harness rehearsal and the candidate bytes in
section 1 are verified by tooling that never consults the policy digest, and
both still verify under current tools. An earlier revision of `PLAN.md`
described all prior evidence as historical; that was wrong and is corrected.

The raw rollouts from v1–v5 were wiped by cleanup and cannot be replayed, so
arm B's failure in v5 remains unexplained. That is the question the final
canary exists to answer.

---

## 4. The final non-counted live pair — not authorized, not run

Not yet requested. It requires a **separate** exact-two, no-replacement
authorization under `non_counted_codex_live_canary_only`.

This authorization is not Gate 3 start authority and does not require Gate 3 to
have been started. The two were conflated in an earlier record and that is
corrected. Correct order:

1. Independent review of section 1 ← **you are here**
2. Owner exact-byte signature
3. Canonical promotion
4. Separate exact-two/no-replacement authorization; run the final canary
5. Natural-bug and resource admission
6. Separate Gate 3 start authority
7. Counted execution

**Stop line, agreed 2026-08-01.** At most one further non-counted pair. If it
fails on another wrapper detail, Gate 3 pauses and the experiment channel is
re-evaluated. No additional census tooling, no replacement session.

---

## Verification state at handoff

| Check | Result |
|---|---|
| Gate 3 focused suite | 453 passed, 0 failed |
| Canonical precommit (`--mode enforce`) | pass |
| `verify-candidate` | `status=PASS`, 7/7 |
| Common-harness rebuild and verify | `status=PASS`, 7/7 |
| Candidate bytes vs manifest | intact |
| Acceptance policy digest | moved; see section 2 |
| Working tree | clean, branch synced |

Not independently reproduced in this repository: the focused-suite count across
other environments. A prior review environment hit pytest basetemp permission
errors that were setup failures, not assertion failures.

## Cannot claim

- That preregistration is approved, signed, or canonically promoted.
- That the acceptance implementation is part of the signed candidate set.
- That the policy digest is formally frozen or signed.
- That the final non-counted pair is authorized.
- That Gate 3 start authority exists.
- That Gate 3 has begun, or that any scorer packet has succeeded.
- That any of this tooling has yet been reused successfully in another project.
