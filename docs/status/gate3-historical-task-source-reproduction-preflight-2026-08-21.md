# Gate 3 Historical Task Source — Gate 0 Reproduction Preflight

Status: **SPECIFICATION ONLY — ALL THREE CANDIDATES `NOT_VERIFIED`**.

This document does not admit a candidate at Gate 0, run a reproduction, start
Route C, authorize a counted Gate 3 experiment, or establish Skill
effectiveness. It specifies the smallest authoritative baseline-fail / fixed-pass
check needed before any of those historical candidates can be described as
reconstructable.

Program authority:
[evidence-backed-engineering-skill-program-2026-07-24.md](../governance/evidence-backed-engineering-skill-program-2026-07-24.md),
especially Section 5 task admissibility and Section 8 Gate 0.

## Problem

A fixed-window census found three post-packet historical bugs with retrievable
Git objects, candidate regression oracles, and distinct root-cause families.
Git-object availability is not an authoritative build check. Each fix, root
cause, and available test was already visible when the task was selected, so
the selection is informed and cannot be treated as random, prospective, or
outcome-blind.

Without a frozen reproduction procedure, later work could silently conflate:

- Git-object availability with a trusted baseline;
- historical task sourcing with the Route C natural pilot;
- a selected counterfactual replay with measured Skill effectiveness; or
- a test that passes on the fixed tree with an oracle that demonstrably fails
  on the common baseline.

## Current repository truth

- The experimental Skill packet is frozen at framework commit `61b285b2`,
  committed at `2026-07-24T17:52:58+08:00`.
- The three candidate fixes are later than that freeze and their baseline
  commits are ancestors of the fetched consumer remote tips.
- The census used fetched Git refs and objects only. It did not pull, checkout,
  install dependencies, build, or run a consumer test.
- The candidates were selected after their fixes, root causes, and regression
  evidence were visible. No complete, prospectively frozen eligible population
  exists for this selection.
- Docker Desktop 4.87.0 is installed in the current user profile. Its Docker
  client and Linux `x86_64` server both answered at version `29.7.2` on
  2026-08-21. No container image is pinned and no candidate has run in Docker.
- The Ruiyi install path requires Linux `bash`, `flock`, GNU `timeout`, `curl`,
  `sha256sum`, and Node `>=22.13.0`. A Docker daemon being available does not
  establish that those requirements or the repository build pass.

## Candidate-selection history

The first fixed-window shortlist named these three candidates:

| Initial candidate | Initial disposition |
|---|---|
| english-vocab-trainer `eee0e9b3101b` / baseline `8e0dbf385a71` — Firestore progress document IDs containing `/` | `CONDITIONAL`: required a product-path probe beyond its helper-level regression |
| english-vocab-trainer `4cebf3dadeb` / baseline `1345dc3a205` — stalled initial Firebase auth state | `CONDITIONAL`: required an observable hook-state oracle beyond its timer-helper regression |
| ruiyi-life-map `00be918ef650` / baseline `ae5b720f1d1f` — hardcoded current 大限 | retained as C2 after the independent clock-controlled oracle was identified |

After that shortlist was visible, deeper post-fetch screening changed two of
the three selections:

- `eee0e9b3101b` was replaced by C1 `a60756436095` because C1 has a
  behavior-level import regression tied to a recorded production identity
  collision, while the Firestore candidate's product-path condition remains
  unsatisfied.
- `4cebf3dadeb` was replaced by C3 `2e854d9a5662` because C3 has a recorded
  TestFlight production failure, an exact two-file change, and a focused
  workflow regression, while the initial-auth candidate's observable
  hook-state condition remains unsatisfied.

The two replaced English candidates are `RESERVE_NOT_SELECTED`, not rejected,
admitted, or silently cured. Their original `CONDITIONAL` requirements remain
open. Selecting replacements after the initial candidates' oracle strength and
reconstruction difficulty were known is a second, stronger informed-selection
channel. The claim ceiling below covers both the initial selection and this
post-census reselection.

## Target outcome

Produce, in a later execution tranche, one fail-closed Gate 0 reproduction
record per candidate showing all of the following against byte-pinned inputs:

1. the exact baseline tree installs and reaches the authoritative oracle;
2. the frozen oracle fails for the expected defect on that baseline;
3. the exact fixed tree installs under the same environment;
4. the same frozen oracle passes on the fixed tree; and
5. unrelated setup, network, build, or test failures are not misclassified as
   reproduction of the defect.

Only a candidate satisfying all five may change from `NOT_VERIFIED` to
`VERIFIED_FOR_GATE0_REVIEW`. That status still is not Gate 0 admission.

## Scope

- Freeze exact baseline, fixed, oracle, and dependency-lock inputs for three
  historical candidates.
- Define the authoritative install and focused test command for each candidate.
- Require disposable materialization outside existing consumer worktrees.
- Require the same container image digest, dependency lock, oracle bytes, and
  command for a candidate's baseline and fixed runs.
- Define fail-closed dispositions and the evidence required for later review.

## Non-goals

- No consumer `pull`, `checkout`, branch change, or worktree mutation.
- No reproduction, dependency install, image pull, or test execution in this
  specification tranche.
- No Gate 0 admission, Gate 1 preregistration, A/B arm creation, scorer run, or
  counted Gate 3 execution.
- No Route C activation or modification. Its natural pilot and
  2026-09-11 automatic STOP remain separate and unchanged.
- No claim that the three selected tasks form a random, complete,
  representative, or prospectively frozen population.
- No `PLAN.md`, memory, Gate 3 runtime, schema, validator, hook, CI, or consumer
  repository change.

## Frozen candidate inputs

### C1 — meiandraybook strong-identity collision

| Input | Frozen value |
|---|---|
| consumer repository | `D:/meiandraybook` |
| baseline | `15d5d51356b4808e5fb12782961a94d9985b2ae6` |
| fixed | `a60756436095fb3b14aecbc9094dd88a8ab9ef16` |
| fixed date | `2026-07-29T17:13:59+08:00` |
| root-cause family | strong ISBN/URL identities incorrectly allowed to fall through to title-based soft matching |
| frozen oracle source | fixed commit, `src/lib/integration/__tests__/bulk_import_integrity.test.ts` |
| oracle SHA-256 / bytes | `7c0c5055543332cb00431623861ea99539e6130bc712b2cc4e1de358219d7042` / `8352` |
| dependency lock | fixed commit, `package-lock.json` |
| lock SHA-256 / bytes | `70d76b7f160040851ec64ba31d12f35bda0394f37937b546310f3d5d41e9440f` / `474302` |
| install command | `npm ci` |
| focused command | `npm test -- src/lib/integration/__tests__/bulk_import_integrity.test.ts` |
| expected baseline signal | the distinct strong-identity case maps the second incoming book to an existing book instead of producing `existing_book_id: null` with `action: created` |
| current status | `NOT_VERIFIED` |

The oracle is the complete fixed-tree test file, not a hand-edited baseline
variant. It must be overlaid byte-for-byte into both disposable trees before
the focused command runs.

### C2 — ruiyi-life-map current-limit rollover

| Input | Frozen value |
|---|---|
| consumer repository | `D:/ruiyi-life-map` |
| baseline | `ae5b720f1d1f35f54fe66303a276695b4b4757a5` |
| fixed | `00be918ef6506b4ae9aaa74a00a66728d30c7c85` |
| fixed date | `2026-08-08T15:48:49+08:00` |
| root-cause family | the current 大限 was hardcoded to wealth/index 4 instead of derived from the calendar year |
| frozen oracle source | corrected test commit `030e1ac2c2b6fb512420c2dc7518cd32b6a6ff07`, `tests/rendered-html.test.mjs` |
| oracle SHA-256 / bytes | `0d5d1d8124a5317b150c6533c3de99f9ac8cdd2f9e6b31d95e7b2478d21817e8` / `9599` |
| dependency lock | fixed commit, `package-lock.json` |
| lock SHA-256 / bytes | `283dbdf55081ff6e460baff80764f39f722f13a0720e1a5fa13153ea877051a5` / `380145` |
| install command | `npm run install:ci` |
| authoritative command | `npm test` |
| expected baseline signal | controlled `2036-01-01T00:00:00Z` render remains on wealth instead of rolling to health; the 2026 and 2035 boundary cases remain wealth |
| current status | `NOT_VERIFIED` |

The corrected oracle commit is test-only and postdates the fix. Its entire test
file must be overlaid byte-for-byte into both disposable trees. Execution is
Linux-only and requires a content-addressed container image selected and
recorded before the first run. An image tag alone is insufficient.

### C3 — english-vocab-trainer TestFlight Firebase injection

| Input | Frozen value |
|---|---|
| consumer repository | `D:/english-vocab-trainer` |
| baseline | `6414235c19fe83a4c441dbf5635ae067ffdfccca` |
| fixed | `2e854d9a56625d18544072afe9ed9a2f714e22e8` |
| fixed date | `2026-08-14T16:31:36+08:00` |
| root-cause family | TestFlight archive step omitted six required Vite Firebase variables |
| frozen oracle source | fixed commit, `scripts/testflight-firebase-config.test.mjs` |
| oracle SHA-256 / bytes | `748f1a5f1da5866907f517b003e503624e1ccac5f69aca6b4d6ad12e0d4badcc` / `1791` |
| dependency lock | fixed commit, `package-lock.json` |
| lock SHA-256 / bytes | `08dabc49071203e66586dfd3553d516beab6e86ab65fb5ebea38abafe1234727` / `601071` |
| install command | `npm ci` |
| focused command | `npm test -- scripts/testflight-firebase-config.test.mjs` |
| expected baseline signal | the required verification step and six-variable archive environment are absent from `.github/workflows/testflight.yml` |
| current status | `NOT_VERIFIED` |

The frozen oracle must be overlaid byte-for-byte into both disposable trees.
The focused source-level workflow oracle does not itself repeat a signed
TestFlight upload and must not be described as signed-device or App Store
evidence. Its compact YAML omission may also provide limited leverage for
discriminating the experimental method: Gate 0 reproduction can establish the
defect pair, but cannot establish that C3 is sufficiently method-sensitive for
Gate 1 or that it should consume one third of a later Gate 3 task set.

## Affected surfaces

This specification adds only this status document. A later reproduction tranche
may create disposable directories and evidence records under a separately
approved allowlist. It must not edit consumer repositories or reuse
any consumer repository's current worktree as an execution directory.

## Boundary and API considerations

- Candidate membership is fixed by exact Git object IDs, not mutable branch
  names or local checkout state.
- Oracle and lock inputs are fixed by source commit, path, SHA-256, and byte
  length. The execution tranche must verify those values before installation.
- Baseline and fixed runs for one candidate form a pair. A changed image digest,
  lockfile, oracle, command, environment variable set, or timeout invalidates
  the pair rather than permitting an in-place repair.
- Oracle overlay is allowed only for the frozen test file. Production files,
  package manifests, dependency locks, scripts, and configuration remain from
  the materialized baseline or fixed tree.
- Network access used by `npm ci` is setup evidence, not bug evidence. Registry,
  integrity, timeout, or install failure yields `ENVIRONMENT_FAILURE`.
- The Ruiyi container must supply its declared Linux tools and Node engine. The
  image repository, immutable digest, platform, and tool versions must be
  recorded before execution.

## Claim ceiling

These historical tasks were knowingly selected after their fixes, root causes,
and available regression evidence were visible, then two were knowingly
replaced after the initial candidates' oracle strength and reconstruction
difficulty were also visible. They are not a random or complete sample. Their
reproduction can support bounded technical feasibility and
reviewer-counterfactual judgment only; it cannot establish measured Skill
effectiveness, effect size, prevalence, countability, process integrity,
promotion evidence, or generalization.

The tasks belong only to the Gate 3 historical task-source bucket. They are not
Route C observations. Reproducing them does not alter, continue, satisfy, or
replace the separately authorized Route C natural pilot.

## Failure paths and risk points

| Condition | Required disposition |
|---|---|
| exact Git object, oracle digest, or lock digest unavailable or mismatched | `INPUT_MISMATCH`; stop the candidate |
| baseline or fixed dependency installation fails | `ENVIRONMENT_FAILURE`; no bug conclusion |
| baseline build cannot reach the oracle | `BASELINE_NOT_RECONSTRUCTED`; remain `NOT_VERIFIED` |
| baseline oracle passes | `ORACLE_DOES_NOT_DISCRIMINATE`; reject or redesign before Gate 0 review |
| baseline fails for an unrelated assertion | `WRONG_FAILURE`; no bug reproduction claim |
| fixed build or oracle fails | `FIX_NOT_VERIFIED`; remain `NOT_VERIFIED` |
| baseline and fixed use different execution inputs | `PAIR_INVALID`; discard both results |
| oracle requires editing production code or dependency metadata | `CONTAMINATED`; stop the candidate |
| only a mutable image tag is recorded | `ENVIRONMENT_UNPINNED`; do not run |

No failed pair may be repaired in place and then described as the original
attempt. A changed input requires a new attempt identity and a new record.

## Evidence plan

For each candidate, retain one pre-run manifest and either two terminal role
receipts or, when a fail-closed disposition stops the pair before the second
role runs, one receipt for the executed role plus a terminal attempt record
that binds the reason the other role was not run. The manifest must record:

- candidate ID and attempt ID;
- baseline, fixed, and oracle source commits;
- source repository remote URL and fetched remote tip used for ancestry checks;
- Git tree IDs for baseline and fixed;
- oracle and lock SHA-256 values and byte lengths;
- container image repository, immutable digest, and platform;
- Node, npm, kernel, and required Linux tool versions;
- exact materialization, install, and test commands;
- explicit environment-variable allowlist and timeouts; and
- the expected defect-specific baseline failure.

Each executed-role receipt must bind to the manifest digest, tree role
(`baseline` or `fixed`), exact stdout/stderr artifact digests, exit status,
test counts, and one closed disposition from the table above. An early-stop
terminal attempt record must bind to the manifest digest, the completed role
receipt digest, both role statuses, the fail-closed disposition, and the reason
the unexecuted role was not run. Reviewer admission requires a defect-specific
baseline failure and a fixed pass from the same manifest.

## Implementation tranche recommendation

Authorize one candidate at a time, beginning with C1 because it has the smallest
production/test surface and no build-before-test requirement. The first tranche
should:

1. select and freeze one Linux `amd64` Node image by registry digest;
2. materialize C1 baseline and fixed Git archives into two new disposable
   directories outside the consumer worktree;
3. verify tree inputs, oracle bytes, and lock bytes before network access;
4. overlay only the frozen oracle into both trees;
5. run the paired install and focused commands with identical bounded inputs;
6. retain the manifest and the complete terminal evidence set defined above;
   and
7. stop for review.

C2 and C3 are deferred options, not commitments. No subsequent candidate
follows automatically from C1, regardless of result.
