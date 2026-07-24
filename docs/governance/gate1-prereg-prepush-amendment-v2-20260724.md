# Gate 1 Correction Amendment v2 — pre-push replay pre-registration

Status: **DESIGN FROZEN — owner re-signed 2026-07-24.** The owner re-signed the
three Section E items, so the pre-registration **methodology/design** is now
frozen. Supersedes the isolation method, the validator-packet layout, and the
status wording of amendment v1
([gate1-prereg-prepush-amendment-20260724.md](gate1-prereg-prepush-amendment-20260724.md),
committed at `61b285b2`/`ee08928603`). Prior commits are left intact (append-only
history). This v2 exists because a second review (CHANGES_REQUESTED) found three
blocking defects in v1, all accepted.

Deliberate claim ceiling (owner-stated): this freeze declares only that the
**Gate 1 main design is complete**. It does **not** declare Gate 1 *formally*
complete or Gate 2 ready, because two execution prerequisites do not yet exist:
(a) an actually-built baseline-only isolation instance (the procedure is frozen
and verified, but no instance is built), and (b) four mutually-uncontaminated
producer environments plus a blind scorer. **Experiment execution progress = 0;
what is done is the design, not any result.** No hook/runtime/CI/gate/enforcement
is changed here.

Authoritative status note: **wherever v1 says "Gate 1 complete", that was
premature.** The single source of truth for Gate-1 completion is Section E of
this v2. v1's Section E "CONFIRMED" and header "FROZEN" are downgraded to
"superseded by v2, pending re-sign".

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

- exactly one head: `33006f09097597f5720a2d01661281d564fb2693ec  refs/tmp/prepush-baseline`
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
values + v2 isolation/packet corrections), it is **pending owner re-sign of v2**,
Gate 2 is deferred, and no arm has run.

## E. Owner re-sign — CONFIRMED 2026-07-24 (design freeze only)

The owner re-signed all three:
1. The verified bundle isolation procedure + allowlist (Section A). ✓
2. The producer-safe / designer-only validator split (Section B). ✓
3. That Gate-1 status is owned by this v2 and v1's completion wording is
   superseded. ✓

Effect: the Gate 1 pre-registration **design is frozen**. This is NOT a
declaration that Gate 1 is formally complete or that Gate 2 may start. Formal
completion and Gate-2 readiness additionally require building the baseline-only
isolation instance and standing up four uncontaminated producer environments plus
a blind scorer — none of which exists. Gate 2 stays deferred. No arm has run.

## F. Cannot claim

- That Gate 1 is formally complete (only the design is frozen; the built
  isolation instance and blinded producer/scorer capacity do not exist).
- That Gate 2 may start, or that any arm has run — experiment execution = 0.
- That the isolation environment is proven beyond the verified bundle procedure
  in Section A.
- That Arm D stays blind if the designer-only expectation file is ever copied
  into a producer environment (the allowlist forbids it).
- That the pre-push bug is fixed (preserved at `33006f09`).
