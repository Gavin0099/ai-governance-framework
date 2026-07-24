# Gate 1 Correction Amendment v2 — pre-push replay pre-registration

Status: **GATE 1 COMPLETE — owner re-signed 2026-07-24.** The owner re-signed the
three Section E items and a read-only re-review confirmed the corrections, so the
Gate 1 pre-registration is complete. Supersedes the isolation method, the
validator-packet layout, and the status wording of amendment v1
([gate1-prereg-prepush-amendment-20260724.md](gate1-prereg-prepush-amendment-20260724.md),
committed at `61b285b2`/`ee08928603`). Prior commits are left intact (append-only
history). This v2 exists because a second review (CHANGES_REQUESTED) found three
blocking defects in v1, all accepted; a third read-only review then reconciled the
status wording to "Gate 1 complete".

**Gate 1 complete means the pre-registration (the exam rules) is done. It does
NOT mean any of the following, all still true:**
- Gate 2 is not approved and must not start until the Section G preflight passes
  and the owner gives a separate explicit "start Gate 2" command.
- No arm has run; **experiment execution progress = 0** (design done, no result).
- The pre-push bug is not fixed (preserved at baseline `33006f09`).
- Runtime-governance smoke remains a non-goal.
- The Bug Fix Skill is not shown effective; Skill effect cannot even begin to be
  judged before Gate 3 accumulates multiple distinct natural bugs.

No hook/runtime/CI/gate/enforcement is changed here.

Authoritative status note: **wherever v1 says "Gate 1 complete", that was
premature.** The single source of truth for Gate-1 completion is Section E of
this v2. v1's Section E "CONFIRMED" and header "FROZEN" are downgraded to
"superseded by v2 (historical)"; under this v2, Gate 1 is complete.

## A. Isolation — verified bundle procedure (fixes Blocking Finding 1)

v1 froze `git bundle create <file> 33006f09`. That command **fails**; verified in
the design environment:

```
$ git bundle create bare.bundle 33006f09
fatal: Refusing to create empty bundle.
```

Git bundle needs a named ref, not a bare commit SHA. **CORRECTED procedure**
(the earlier `refs/tmp/prepush-baseline` version passed `git bundle verify` but a
real `git clone` of it checked out an EMPTY tree — `refs/tmp/*` is not a branch,
so clone has nothing to check out. This was only caught by actually cloning inside
a Docker container; every prior paper "verify" missed it.):

```
git branch -f prepush-baseline 33006f09
git bundle create prepush-baseline-33006f09.bundle prepush-baseline
git bundle verify prepush-baseline-33006f09.bundle
git branch -D prepush-baseline
# clone MUST name the branch (the bundle has no HEAD):
git clone -b prepush-baseline prepush-baseline-33006f09.bundle work
```

**Authoritative isolation checks (all three, not just verify):**
- `git bundle verify` → exactly one head
  `33006f097597f5720a2d01661281d564fb2693ec refs/heads/prepush-baseline`, complete
  history (no Gate 0 analysis commit — all analysis is after 33006f09).
- `git clone -b prepush-baseline` → **non-empty** checkout; `git rev-parse HEAD`
  == `33006f09…`; `git ls-files` == 3664 files; buggy hook present.
- Bundle sha256 (design env, this instance):
  `da1a47d735a32433dff2ed2be0aeda2e287686a750187a0ba4d6c22ed559f5e7`. Bytes vary
  by git version/packing, so the authoritative invariant is single-head +
  complete-history + **non-empty clone at 33006f09**, not the sha256.

**Verified in a real container** (Docker IS available here — the earlier
"Docker NOT_FOUND" claim was wrong; daemon 29.6.2 running): `docker run
--network=none -v <bundle-dir>:/baseline:ro alpine/git` — host repo paths
unreachable, network DNS blocked, answer analysis files absent, clone HEAD ==
33006f09. See `isolation-template-spec.md`.

**Producer baseline = sanitized ALLOWLIST export (not a checkout denylist):** the
container probe found the full 33006f09 tree carries the experimenter's
meta-artifacts (`memory/2026-07-24.md`, `PLAN.md`, the program docs,
`artifacts/ab-*`) which leak the experimental **frame** (not the answer — 0 answer
hits). A checkout denylist is insufficient: a producer with the raw bundle/`.git`
can `git show HEAD:memory/…` under any sparse checkout. Fixed by an **allowlist
export into a fresh git object database** (built + verified;
`sanitized-baseline-manifest-20260724.md`): source `33006f09`, sanitized tree
`36c346fa951a24cbf914ef04469aac5cb5fd8b86`, 4 allowlisted files, 11 objects total,
`git show`/`git rev-list --objects --all` confirm 0 meta objects reachable. The
producer receives this sanitized repo, never the raw bundle.

### Producer-environment file allowlist (frozen)

The producer/arm environment contains ONLY: the **sanitized producer repo**
(fresh object DB, allowlist export from 33006f09 — Section A / sanitized-baseline
manifest; the raw bundle is designer-side only and is **never** given to a
producer), plus these files copied in as standalone inputs (per arm):

| File | Arms | sha256 |
|---|---|---|
| arm-dispatch-packet.md (symptom-only) | A/B/C/D | `59ef5915bccf09eb6a5c7a344412d512415eb6e8fab0c83e7f122612a3b822a8` |
| skill-packet-bugfix.md | B/C/D | `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14` |
| governance-packet.md | C/D | `f6dfe7268851b59717405550c39502a76774165a1b35ee9c9e056506c79bdc28` |
| validator-pins.md (producer-safe) | D | `6ea4b3226a3f54dce265ad27a67209b9d803b27d690cc4d899d20fff9a7f2d5f` |

Everything else is EXCLUDED by construction — the Gate 0 doc, both amendments,
`memory/*`, and specifically `validator-expectation-DESIGNER-ONLY.md`.

## B. Validator packet split (fixes Blocking Finding 2)

v1's `validator-pins.md` leaked the root cause ("an ignore-stdin logic error").
Split into:

- **Producer-safe** `validator-pins.md` (sha256 `6ea4b322…`): versions, configs,
  commands, role mechanics only. Verified to contain no root-cause term.
- **Designer/scorer-only** `validator-expectation-DESIGNER-ONLY.md`
  (sha256 `dcff3d2d0d3f02f4ef57283718c61b5fe890e54b109b90be05b68d7a25fb52c6`):
  the expected-null signal and its reasoning. Never enters a producer
  environment (excluded by the Section A allowlist).

## C. All other frozen values carry over from v1 unchanged

Baseline `33006f09`; baseline instruction tree `8c1bd5a5…`; hook blob `5b388f1a…`;
guard blob `7d2a5192…`; task scope = version-bump advisory file-count only;
runtime smoke = non-goal; budget 60 tool calls / 30 min per arm; model uniformity
across arms stamped at dispatch; randomization seed 20260724; second-scorer subset
100% of semantic claims; validator required versions shellcheck 0.10.0 / ruff
0.6.9 / mypy 1.11.2. The four arms and the git-stdin oracle are unchanged.

## D. Status unification (fixes Blocking Finding 3)

Corrected across all surfaces in this same slice:

- v1 amendment: its self-contradictory "Cannot claim: partially frozen pending
  re-sign" line and Section F "pending re-sign" wording are reconciled — v1 is
  marked superseded-by-v2, and Gate-1 completion is owned solely by v2 Section E.
- `memory/01_active_task.md`: the pre-push bullet updated to reference v2 and the
  pending-re-sign-of-v2 state.
- `PLAN.md`: a Pending-Work entry is actually added in this slice (v1 claimed a
  PLAN edit that never happened).

The planning surfaces now agree: a Gate 1 pre-registration exists (v1 frozen
values + v2 isolation/packet corrections), **Gate 1 is complete** (owner
re-signed 2026-07-24), Gate 2 is deferred behind the Section G preflight plus a
separate owner command, and no arm has run.

## E. Owner re-sign — CONFIRMED 2026-07-24; Gate 1 COMPLETE

The owner re-signed all three, and a read-only re-review confirmed them:
1. The verified bundle isolation procedure + allowlist (Section A). ✓
2. The producer-safe / designer-only validator split (Section B). ✓
3. Status reconciled: all governance surfaces now state "Gate 1 complete"
   consistently, with the four caveats preserved. ✓

Effect: **Gate 1 is complete** — the pre-registration is done. Gate 2 does not
start automatically; it is gated by the Section G preflight AND a separate
explicit owner command. No arm has run; execution progress = 0.

## G. Gate 2 preflight — ALL must pass before the separate "start Gate 2" command

Gate 1 being complete does not open Gate 2. Every item below must be true first,
and then the owner must still issue an explicit "start Gate 2" command.

Two distinct things must not be conflated: the **baseline bundle artifact** (a
file — BUILT) and the **isolated execution environment** (where arms run — NOT
built). Their states differ.

**(a) Baseline bundle artifact — BUILT + verified this session:**
- [x] Built via the verified named-ref procedure; `git bundle verify` shows a
  single head `33006f097597f5720a2d01661281d564fb2693ec` and complete history;
  design-env sha256
  `6ad5bcca8cf4b743e1990310837097081a90bb65805f6cce698904baeb1cbe6e`, 8.3 MiB.
  Reproducibility caveat: bundle bytes vary by git version/packing, so a rebuild
  yields a different sha256; only the procedure + single-head/complete-history
  invariant are reproducible, not that specific hash.

**(b) Isolated execution environment — mechanism VERIFIED in Docker, template NOT production-ready:**
- [x] The isolation mechanism works: a designer-side `docker run --network=none`
  probe (designer-side, mounting the bundle only to exercise the mechanism — the
  producer surface is the sanitized repo, not the bundle) proved
  host-repo-unreachable + network-off + answer
  analysis absent + clone HEAD == 33006f09 (see Section A / isolation-template-spec).
- [x] **Producer baseline sanitized (Finding 2, RESOLVED via allowlist export):**
  a fresh git object DB with only the 4 allowlisted code files (sanitized tree
  `36c346fa…`); `git show`/`rev-list` confirm 0 meta objects. A denylist was
  insufficient (git show reads the object DB). See sanitized-baseline-manifest.
  The producer receives this sanitized repo, never the raw bundle.
- [ ] The **sanitized producer repo** (never the raw bundle) + the dispatch packet
  are placed in an environment that **technically cannot** read this repo, current
  `main`, the Gate 0 analysis, `memory/*`, the raw bundle, or this conversation
  (container / VM / Windows Sandbox / separate OS account / remote runner).
- [ ] Four **answer-blind** producer contexts (one per arm) — "four independent
  clean sessions/contexts, not necessarily four machines or four people". Each
  does **not** know the root cause or fix, but **does** know which treatment it
  received (Arm B knows it has the Skill packet, etc.): answer-blind, not
  treatment-blind. Each sees only its own arm's allowlisted inputs.
- [ ] Two **arm-identity-blind** scorers — before scoring, neither knows the
  A/B/C/D mapping for any output; the second scorer independently re-reads all
  semantic completion claims.
- [ ] None of these roles is this design session or the author.

**(c) Execution constants — answer-safe setup done this session where marked:**
- [x] 60 tool calls / 30 min cap per arm (frozen policy).
- [x] dispatch / Skill / Governance / validator packet sha256 verified to match
  Section A/B values (Gate 2 preflight manifest 2026-07-24).
- [x] Randomized arm order generated from frozen seed 20260724 and recorded:
  **[D, C, A, B]** (deterministic; `random.seed(20260724);
  random.sample(['A','B','C','D'],4)`).
- [x] Producer receipt template prepared (answer-safe; raw producer-side, not
  scorer-facing — see the anonymization handoff below).
- [ ] Identical model build across all four arms — stamped identically at dispatch.
- [ ] **Non-treatment** tool permissions identical across arms; **Arm D's
  treatment-time validator feedback is the pre-registered treatment exception**,
  not a permission difference to be equalized away.
- [ ] shellcheck 0.10.0, ruff 0.6.9, mypy 1.11.2 installed **in the producer/
  scorer environment** (all three pinned versions confirmed to exist; install
  belongs in the isolated run env, not this design session).
- [ ] Every arm's receipt actually binds to its own output commit (verified at run).

**(d) Scorer anonymization handoff — EXECUTABLE CONTRACT (must run before scoring):**
Anonymization removes **identity labels only**, never substantive evidence. The
principle is now an executable, mechanically-replayable contract
[`artifacts/experiments/prepush-bugfix-20260724/scorer-handoff-contract.json`](../../artifacts/experiments/prepush-bugfix-20260724/scorer-handoff-contract.json)
(**`gate2-scorer-handoff.v2`, frozen — owner re-signed 2026-07-25**; v1 was
re-signed 2026-07-24 then substantively changed with the mandatory receipt pair,
anon-id binding, path-alias rejection, and staged-publish atomicity, so it was
bumped to v2 and re-signed. Frozen is necessary but not sufficient for Gate 2,
which still needs the resource preflight and a separate owner start command). It
fixes the parts the review flagged as still principle-only:
- **Producer output artifact** `raw-output.txt` with a fixed section order
  (FIX_DIFF, TEST_LOG, VALIDATOR_OUTPUT, COMPLETION_CLAIM); redaction applies only
  to COMPLETION_CLAIM free text + receipt metadata; sections 1–3 are never redacted.
- **Literal redaction map** (11 explicit regex → placeholder rules, case-insensitive,
  `\s+` for internal spaces, basename match for filenames, applied in order) that
  removes ONLY arm labels, packet filenames, and treatment-assignment tokens →
  `[ARM]` / `[PACKET]` / `[ASSIGNMENT]`; the receipt `arm` field is dropped.
- **Anonymous ID algorithm:** `OUT-` + first 12 lowercase hex of
  `sha256(raw-output.txt UTF-8/LF bytes)`; full 64-hex sha256 recorded to bind
  raw → redacted (tamper-evident); explicit 16-hex collision rule.
- **`blinding_compromised`** set by the experimenter, per output, with reason, when
  a non-label feature unavoidably signals the treatment — the revealing substantive
  evidence is flagged, never deleted; the output is still scored.
- **Scorer blinding-check:** before the mapping is released, each scorer records
  per anon_id `suspected_treatment` (A/B/C/D/unsure), `suspected_confidence`, and
  `reason`, so blinding integrity is measured, not assumed.
- **Release gate:** the anon-ID → arm mapping is held solely by the experimenter
  and released only after both scorers submit scores AND blinding-check guesses.
- **Canonical runner (executed, answer-safe):** `redaction_runner.py` applies the
  map to a producer `raw-output.txt`, redacting only COMPLETION_CLAIM and emitting
  a `gate2-redacted-packet.v1` with `contract_sha256`, `raw_output_sha256`,
  `redacted_output_sha256`, `anon_id`, and per-rule match counts. Demonstrated
  deterministic, identity-neutral, and substance-preserving on a synthetic input.
- **Validator-output split (WARNING 2):** the scorer's VALIDATOR_OUTPUT section is
  the **post-hoc uniform** validator run applied identically to all four arms, so
  it does not signal treatment. Arm D's **treatment-time** validator feedback stays
  in experimenter provenance and never reaches a scorer. If a completion claim's
  substance still reveals Arm D acted on that feedback, it is flagged
  `blinding_compromised`, not deleted.

### Resource-based blocker classification (not a place)

The remaining blockers are **resources**, not a geographic location. "Back at the
company" was over-simplified; the correct statement is that each line waits on a
specific capability, satisfiable in any secure environment:

| Work | Real blocker | Must be at a company? |
|---|---|---|
| Gate 2 setup (this section's [x] items) | none — done this session | no |
| Gate 2 producers | an environment that technically cannot read the answer (container / VM / Windows Sandbox / separate OS account / remote runner) holding only the **sanitized producer repo** (never the raw bundle) + the dispatch packet | no |
| Gate 2 scorers | an isolated, blinded scoring context (fresh agent session or another person) with no arm identity and no treatment labels | no |
| meiandraybook product delivery | none — owner's own project; merge/deploy/replay need no non-author reviewer | no |
| meiandraybook independent-review evidence | **NOT PURSUED (owner decision)** → this evidence is `NOT PRESENT`; it cannot be used to claim independent use or raise G4 strength | n/a |
| IMPORT_API_SECRET replay | the owner safely obtaining and using the secret | only if the secret lives solely in a company vault/device |

Even after a full Gate 2 run, the most that may be claimed is: the four-arm
process runs, evidence and commits bind correctly, and the scoring method works.
**Skill effectiveness still may NOT be claimed** — that waits for Gate 3.

## F. Cannot claim

- That Gate 2 may start, or that any arm has run — experiment execution = 0; the
  Section G preflight is unmet and no separate start command has been given.
- That the isolated execution environment exists (only the sanitized producer
  baseline and the designer-side bundle artifact are built; the execution
  environment where arms run is NOT built).
- That the Bug Fix Skill is effective (a Gate 2 pilot could not show it; that is
  a Gate 3 question).
- That external tools can or cannot replace the in-house Python tools. This
  four-arm design measures only whether adding treatment-time validator feedback
  helps (`D−C`). A replacement judgment needs a separate comparison: in-house vs
  external under the same contract and test set, comparing accuracy, false
  positives, false negatives, cost, and maintenance.
- That Arm D stays blind if the designer-only expectation file is ever copied
  into a producer environment (the allowlist forbids it).
- That the pre-push bug is fixed (preserved at `33006f09`).
