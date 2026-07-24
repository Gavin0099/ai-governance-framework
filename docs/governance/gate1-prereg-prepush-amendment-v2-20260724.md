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

Git bundle needs a named ref, not a bare commit SHA. **Frozen verified
procedure** (executed and confirmed in the design environment):

```
git update-ref refs/tmp/prepush-baseline 33006f09
git bundle create prepush-baseline-33006f09.bundle refs/tmp/prepush-baseline
git bundle verify prepush-baseline-33006f09.bundle
git update-ref -d refs/tmp/prepush-baseline
```

Frozen expected `git bundle verify` result (the authoritative isolation check):

- exactly one head: `33006f097597f5720a2d01661281d564fb2693ec  refs/tmp/prepush-baseline`
- "The bundle records a complete history." — i.e. root..33006f09 only, and
  therefore **no** commit carrying the Gate 0 analysis (all analysis commits are
  after 33006f09).

Bundle sha256 recorded in the design environment:
`58f720c0b7d17b5bb88ecc93fcdd60f750d50216be55d62ff613cf2558036f9c`.
Reproducibility caveat: bundle bytes can vary by git version/packing, so the
**authoritative** invariant is the single-head + complete-history verify result
above, not the sha256. The producer environment consumes this bundle only; it has
no other refs and no network path to the remote.

### Producer-environment file allowlist (frozen)

The producer/arm environment contains ONLY: the baseline bundle above, plus these
files copied in as standalone inputs (per arm):

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

**(b) Isolated execution environment — NOT built:**
- [ ] The bundle is placed in an environment that **technically cannot** read this
  repo, current `main`, the Gate 0 analysis, `memory/*`, or this conversation
  (container / VM / Windows Sandbox / separate OS account / remote runner mounting
  only the bundle).
- [ ] Four mutually-isolated producer contexts (one per arm) — "four independent
  clean sessions/contexts, not necessarily four machines or four people"; each
  sees only its own arm's allowlisted inputs.
- [ ] A primary scorer blind to arm identity, and a second scorer who re-reads all
  semantic completion claims — both blind to the answer.
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

**(d) Scorer anonymization handoff — FROZEN procedure (must run before scoring):**
Anonymization removes **identity labels only**, never substantive evidence. The
scorer must judge the real code diff, tests, validator output, and completion
claim; deleting any of those would reshape the output and break the comparison,
and would let an answer-knowing experimenter subjectively pick what survives. The
frozen, mechanically-replayable handoff:
- [ ] The **experimenter** (may know the answer; is not a producer or scorer)
  collects the four raw producer outputs + receipts.
- [ ] The experimenter assigns an **anonymous ID** (hash-derived) to each output.
- [ ] **Redaction scope (frozen, pre-specified, replayable) — remove ONLY:** the
  receipt `arm` field, packet filenames, and explicit treatment-assignment
  metadata (e.g. "Arm C", "governance packet", "validator feedback" labels). A
  fixed redaction map (literal token → placeholder) is frozen before the run so
  the redaction is deterministic and re-runnable by anyone.
- [ ] **Preserved intact (never redacted):** the raw code diff, the tests, the
  validator output, and the completion claim. These are exactly what the scorer
  evaluates.
- [ ] If the substantive content itself lets a scorer infer the treatment, that is
  recorded as **`blinding_compromised: true`** for that output (with the reason)
  — it is **not** hidden by deleting the real evidence. A compromised-blinding
  output is scored and flagged, not sanitized.
- [ ] The scorer receives **only** the redacted output + the frozen rubric — no
  `arm` field, no treatment packet, no mapping table.
- [ ] The **anonymous-ID → arm mapping is held solely by the experimenter** and
  released only after both scorers finish; each redacted packet records the
  **sha256 of the raw producer output** it derives from, so de-anonymization is
  auditable and tamper-evident.

### Resource-based blocker classification (not a place)

The remaining blockers are **resources**, not a geographic location. "Back at the
company" was over-simplified; the correct statement is that each line waits on a
specific capability, satisfiable in any secure environment:

| Work | Real blocker | Must be at a company? |
|---|---|---|
| Gate 2 setup (this section's [x] items) | none — done this session | no |
| Gate 2 producers | an environment that technically cannot read the answer (container / VM / Windows Sandbox / separate OS account / remote runner mounting only the baseline bundle) | no |
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
- That the isolated execution environment exists (only the baseline bundle
  artifact is built; the execution environment where arms run is NOT built).
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
