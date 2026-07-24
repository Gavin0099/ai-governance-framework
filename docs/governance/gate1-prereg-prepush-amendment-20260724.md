# Gate 1 Correction Amendment — pre-push replay pre-registration

Status: **SUPERSEDED BY v2, pending owner re-sign.** A second review found this
v1 had an unexecutable bundle command (Blocking 1), a root-cause leak in the
producer-facing validator file (Blocking 2), and internal status contradictions
(Blocking 3). The earlier "FROZEN / Gate 1 complete" wording here was premature
and is withdrawn. The authoritative isolation method, validator-packet split, and
Gate-1 completion status now live in
[gate1-prereg-prepush-amendment-v2-20260724.md](gate1-prereg-prepush-amendment-v2-20260724.md).
The frozen VALUES in Sections B–C below (hashes, budget, seed, subset, versions,
scope, non-goal) carry forward unchanged and are still valid; only the isolation
method, the validator layout, and the completion status are superseded by v2.
No hook, runtime, CI, gate, or enforcement is changed here.

Review that prompted this: CHANGES_REQUESTED, three blocking findings plus two
corrections. All are accepted.

## A. Task narrowing (fixes Blocking Finding 3)

The only defect with natural evidence is the **version-bump advisory using the
wrong HEAD** (Gate 0 line 13). The prior pre-registration wrongly also required
changing the runtime-governance smoke step (`pre-push:63`) to target the outgoing
ref.

- **Frozen scope: the version-bump advisory's file-count only.**
- **Non-goal: runtime-governance smoke.** It is defined as
  `framework_self_smoke_advisory` and has neither a natural failure nor an
  independent oracle. It is NOT part of this task and must not be changed by any
  arm. Revisiting it would require its own Gate 0 with its own oracle.
- The frozen oracle already matches this narrowing: it asserts only the guard's
  `changed_files`.

## B. Actually-frozen values (fixes Blocking Finding 1)

Content-addressable where possible (git object ids at baseline `33006f09` are
reproducible by anyone):

| Parameter | Frozen value |
|---|---|
| Baseline commit | `33006f09` |
| Baseline instruction set = `governance/rules/common` tree @ baseline | `8c1bd5a523eb7038cc4c6a247c2b45df05d49c04` |
| Artifact under test = `scripts/hooks/pre-push` blob @ baseline | `5b388f1aa83bd9b2027d1144d981b99979c51120` |
| `governance_tools/version_bump_guard.py` blob @ baseline | `7d2a51924a7567ce5da336653480c9964806ffa5` |
| Arm dispatch packet (symptom-only) sha256 | `59ef5915bccf09eb6a5c7a344412d512415eb6e8fab0c83e7f122612a3b822a8` |
| Skill packet (B/C/D) sha256 | `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14` |
| Governance packet (C/D) sha256 | `f6dfe7268851b59717405550c39502a76774165a1b35ee9c9e056506c79bdc28` |
| Validator pins (versions + configs) sha256 | `a54caabb174389d1b15e5fd78ce30e831f83696e357c1182944a16d66a78bfb5` |

Packet files: `artifacts/experiments/prepush-bugfix-20260724/`.

- **Validators:** shellcheck 0.10.0, ruff 0.6.9, mypy 1.11.2 with the frozen
  configs in `validator-pins.md`. None is installed in the design environment, so
  they are frozen as **run-environment requirements**; a run whose versions differ
  is INVALID. (That the external tools are absent is itself a data point on the
  external-tooling question — see Section F.)
- **Budget (frozen):** each arm capped at 60 tool calls and 30 minutes wall-clock;
  same cap for all four arms. Exceeding the cap ends the arm and is recorded.
- **Model uniformity (frozen):** identical model build across all four arms,
  stamped at dispatch; a build that differs between arms is INVALID. The specific
  build string is recorded at dispatch, before any arm sees its packet.
- **Randomization (frozen):** arm execution order is a permutation of [A,B,C,D]
  drawn with `python -c "import random;random.seed(20260724);print(random.sample(['A','B','C','D'],4))"`
  → recorded at dispatch; blinding labels are assigned from this seed.
- **Second-scorer subset (frozen):** 100% of semantic/judgment completion claims
  are independently re-scored by the second blind scorer (the claim set is small).
  Machine-checkable claims use the Section-B checklist and need no second scorer.
  Raw agreement and every disagreement are reported.

## C. Isolation redesign (fixes Blocking Finding 2)

A pinned worktree does NOT isolate the answer: it shares the object database and
refs, so a fresh session could `git show main:docs/status/gate0-...` or read the
original workspace. And the prior pre-reg text itself named the root cause.
Frozen isolation method instead:

1. **Producers read only the symptom-only dispatch packet** (Section B hash) plus,
   per arm, the Skill/Governance packets. They never receive the Gate 0 doc, the
   pre-registration, this amendment, or `memory/*`.
2. **Baseline delivered as a standalone bundle/clone containing only history up to
   `33006f09`** — created with `git bundle create <file> 33006f09` and verified to
   have a single head at `33006f09`. It contains the buggy code but none of the
   later analysis (analysis commits are all after `33006f09`).
3. **The run environment has no read access** to the original repository, to
   `origin/main`, or to this conversation, and no network path to the remote.
4. **Recorded at dispatch:** the dispatch-packet sha256, the baseline bundle sha256,
   and the baseline instruction-set tree hash, so the blind conditions are auditable.

## D. Correction — reviewer capacity ≠ Gate 2 capacity

The prior claim that the meiandraybook independent reviewer and this Gate 2 are
"the same resource" was imprecise. They need different things:

- meiandraybook: a **real non-author human review** that reads the governance
  evidence and accepts/returns on it.
- Gate 2: a **genuinely blinded producer and blind scorer** for a controlled
  four-arm replay.

Both are "independent capacity we do not have in this session," but they are not
interchangeable and should be tracked as two distinct blocked items.

## E. Owner re-sign — SUPERSEDED BY v2

The 2026-07-24 re-sign recorded here was premature: a later review found the
isolation and validator-leak defects above. Gate-1 completion is NOT owned by
this section. It is owned by amendment v2 Section E, which is pending owner
re-sign. Treat Gate 1 as **incomplete** until v2 is re-signed.

## F. Planning-truth sync (fixes the second correction)

The program document is still marked review-only DRAFT and PLAN/active task do not
record an approved experiment. Owner sign-off authorizes this document work, but
before Gate 2 the planning surface must state: a Gate 1 pre-registration exists
for the pre-push bug, it is corrected and pending re-sign, Gate 2 is deferred, and
no arm has run. This amendment records that requirement; the PLAN/active-task edit
is made in the same slice.

Note toward the external-tooling question (Section F reference): this task shows
mature external validators (shellcheck/ruff/mypy) neither present in-environment
nor able to catch the defect, while the in-repo Python guard also missed it. That
is one data point that "replace in-house checks with external tools" is
defect-type-dependent, and is exactly what `D−C` is designed to measure — it is
not settled by this task alone.

## Cannot claim

- That Gate 1 is complete (this v1 is superseded by v2, which is pending owner
  re-sign; Gate 1 is incomplete until then).
- That Gate 2 may start.
- That a fresh session is automatically a blind environment (Section C is the
  method that must hold).
- That runtime self-smoke is a proven bug (it is a non-goal, unproven).
- That the pre-push bug is fixed (preserved at `33006f09`).
