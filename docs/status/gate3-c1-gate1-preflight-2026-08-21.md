# Gate 3 C1 — Gate 1 Preflight

Status: **`VALIDATOR_CANDIDATE_FOUND` — NOT PREREGISTERED, NOT FROZEN**

Date: 2026-08-21

This preflight answers only two questions left open by the approved C1 Gate 1
proposal:

1. whether identifier-free title/publisher matching has a product basis that
   is independent of the later C1 fix and scorer oracle; and
2. whether a credible Arm D validator candidate exists without exposing the
   hidden scorer variants.

The permitted terminal states were `VALIDATOR_CANDIDATE_FOUND`,
`NARROWER_DESIGN_REQUIRED`, and `STOP_BEFORE_PREREGISTRATION`. The result is
`VALIDATOR_CANDIDATE_FOUND`.

This result identifies a candidate worth materializing and testing in a later,
separately authorized tranche. It does not select exact bytes, prove the
integration works, or authorize Gate 1 preregistration.

## Authority and completed prerequisite

The owner authorized this bounded preflight and the byte-preserving merge of
the approved C1 Gate 1 proposal. PR #87 was merged at framework commit
`4b84b8d477639a4ea258275c51ad4bc199ee7545`; its reviewed head remained
`fcc617ca0f17cd8090873efb254634aea6949231`.

The governing proposal is
`docs/governance/gate1-c1-bugfix-skill-proposal-candidate-20260821.md`.
It remains a proposal rather than a preregistration.

## Problem

The producer-visible proposal says imports without a catalog identifier may
intentionally resolve by title and publisher. If that behavior came only from
the historical fix or the redesigned hidden oracle, including it in the common
task would leak post-hoc analysis into every arm.

The four-arm design also requires a credible `D-C` mechanism. A generic linter
with no relationship to C1 would be ceremonial, while exposing hidden scorer
fixtures to Arm D would destroy the producer/scorer boundary.

## Current repository truth

### C1 bindings

| Surface | Binding |
|---|---|
| consumer | `https://github.com/Gavin0099/meiandraybook.git` |
| consumer baseline | `15d5d51356b4808e5fb12782961a94d9985b2ae6` |
| historical fix | direct child `a60756436095fb3b14aecbc9094dd88a8ab9ef16` |
| framework Skill freeze | `61b285b25e97872526057c6ab6b01637fbfa1d2b`, 2026-07-24 |
| C1 proposal merge | `4b84b8d477639a4ea258275c51ad4bc199ee7545` |

### Independent product basis

Consumer commit `48a5cd89716f637b928698c83e2eeed8b311a25a`, authored and committed
2026-07-22T18:18:20+08:00, is an ancestor of the C1 baseline. It predates both
the framework Skill freeze and the 2026-07-29 historical fix.

At that commit, the consumer owner recorded this completed product behavior in
`PLAN.md`:

> bulk import 補 ISBN / URL / title+publisher+series soft identity；soft match
> 一律保留人工審核

The same commit added a focused test named:

> uses an exact title/publisher/series soft match when stronger keys are absent

The test supplies an incoming book with empty ISBN and URL values, supplies an
existing matching title/publisher row, and requires the import result to link
that row while recording `review_soft_match`.

Both sources remain present at the exact C1 baseline:

| Source | Baseline binding |
|---|---|
| `PLAN.md` | Git blob `7f29380f839b00c9acddc54f1e49ffe623dfc672`; SHA-256 `5afca857537a30c6fd7932487bad0ea72622179bb4b8761688630ab3ad5487c5`; 29,415 bytes; relevant line 110 |
| `src/lib/integration/__tests__/bulk_import_integrity.test.ts` | Git blob `0d79658b36da2c4fea61b971a8860e8b922940d3`; SHA-256 `d68f3e37df8055117d18c6bd6d58d3fec8d6995f45ad4c66046f4a5b9e5ccb8d`; 6,511 bytes; relevant test begins at line 145 |

The program's task-admissibility rule accepts a fixed fixture as a credible
behavior source. These two sources establish that weak-identity fallback and
manual review were product behavior before C1 was selected, analyzed, or
fixed. The common acceptance sentence therefore need not be inferred from the
historical fix or hidden scorer oracle.

Here, **independent** means temporally and logically independent of the later
C1 fix, redesigned oracle, and framework analysis. It does not mean that a
separate organization authored the product decision; the consumer PLAN and
fixture are owner-authored repository evidence.

### Existing validator truth

The framework's `failure_completeness_validator.py` checks reported failure,
exception, rollback, and cleanup metadata. It does not execute the submitted
tests, perturb production behavior, or determine whether a C1 regression test
can distinguish a semantic defect. It has no credible C1 `D-C` mechanism.

The framework already describes mutation testing as the executable form of
test-sensitivity checking in `governance/TESTING.md`. That text specifically
permits surviving mutants to be returned to an agent as a test-improvement
prompt, while warning that mutant score is not a KPI or automatic gate.

The Engineering Skill program independently lists StrykerJS as a TypeScript
test-quality candidate and requires mutation scoring, when used, to run
post-hoc and identically across all arms. The same rule explicitly preserves a
separately declared treatment-time validator for Arm D.

No Stryker package or configuration is currently installed or committed in
the C1 consumer or this framework for this study.

## Validator candidate

The credible candidate is **StrykerJS mutation testing** using the official
Vitest runner.

Registry and compatibility facts observed on 2026-08-21:

| Component | Candidate metadata observed, not frozen |
|---|---|
| `@stryker-mutator/core` | version `10.0.0`; Node `>=22.0.0`; npm integrity `sha512-ZvMsRyaXQQ5e6Thcid9pkuODv6Fn9E3nrBQJUap+hcJuGJ4unm26afo3m6YKSjn8kinyxJ/3TXf0cTWRDaTxVw==` |
| `@stryker-mutator/vitest-runner` | version `10.0.0`; Node `>=22.0.0`; peer requirements `vitest >=2.0.0` and core `10.0.0`; npm integrity `sha512-SHK2/vfvRUpiz7jXPnQMBnr6zLdm69DK03Mo5mPhaZWcRSygrKUqYsPqWsXsK+5ySHzlMTfCyFK5NQ/X9sJFFw==` |
| consumer baseline | Vitest `^4.0.18` in `package.json` |
| last reproduced environment | Node `v22.23.2` in the attempt-02 pinned image |

Official references:

- `https://stryker-mutator.io/docs/stryker-js/vitest-runner/`
- `https://stryker-mutator.io/docs/stryker-js/configuration/`
- `https://www.npmjs.com/package/@stryker-mutator/vitest-runner`

Those facts establish ecosystem compatibility on paper. They do not establish
that a C1 configuration has installed or executed successfully.

## Proposed non-leaking Arm D mechanism

A later candidate may materialize a generic, task-neutral adapter with this
boundary:

1. derive mutation targets only from production lines changed by the producer
   relative to the common baseline;
2. run only producer-visible tests already present in that arm's tree;
3. never mount, copy, name, hash, query, or network-fetch the hidden scorer
   bundle, historical fix, Gate 0 attempts, method-sensitivity analysis, or
   proposal analysis;
4. return to Arm D only Stryker execution status and mutant results derived
   from Arm D's own changed production code and producer-visible tests; and
5. after every arm output is committed, let the blind scorer run the exact same
   frozen validator/config post-hoc against A/B/C/D without returning those
   results to A/B/C.

This gives `D-C` a plausible mechanism: D can improve a weak producer-authored
regression after a surviving mutation shows that the submitted tests do not
detect a change in the submitted production behavior. No hidden C1 behavior
family or expected value is needed as validator input.

The adapter and output policy must be task-neutral. They must not name
`import-logic.ts`, identity tiers, ISBN, URL, title/publisher fallback,
historical commits, expected branches, or hidden fixtures. Mutation targets
must come from the producer diff rule rather than a C1-specific path list.

This is a C1 study candidate, not a silent new program-wide requirement that
every Bug Fix study use Stryker or retain four arms.

## Alternatives rejected in this preflight

| Candidate | Disposition | Reason |
|---|---|---|
| framework failure-completeness validator | rejected | checks declared metadata and heuristic names, not C1 semantic test sensitivity |
| ESLint or `tsc --noEmit` | rejected | credible syntax/type signals but no specific mechanism for the observed semantic identity/test-fixture failure |
| ordinary Vitest execution | rejected as D-only treatment | producers already need ordinary relevant tests; making the test runner D-only would confound basic execution with validation |
| hidden scorer oracle as D feedback | rejected | directly violates the owner-authorized scorer-only boundary |
| C1-specific static rule naming the guard or file | rejected | leaks task architecture/fix direction and overfits the historical correction |

## Scope

- Bind the independent product sources for weak-identity fallback.
- Identify and bound one credible non-leaking Arm D validator candidate.
- Record why obvious alternatives do not satisfy the C1 mechanism.
- Choose one of the three owner-authorized terminal states.

## Non-goals

- No Gate 1 preregistration, approval, signature, or freeze.
- No package installation, lockfile change, Stryker configuration, adapter,
  validator output schema, fixture, receipt, task packet, oracle, or rubric.
- No validator execution, compatibility probe, dry run, rehearsal, producer,
  scorer, worktree, arm, or model call.
- No A/B/C/D creation or execution and no C2/C3 or Route C change.
- No change to the consumer repository, frozen Skill packet, runtime, schema,
  hook, CI, gate, or enforcement.
- No claim that mutation survival identifies a product defect or that Stryker
  will produce a positive `D-C` difference.

## Affected surfaces

This preflight changes only this decision document. It records repository and
external package facts; it creates none of the candidate mechanisms it names.

## Failure paths and remaining risk

Before a preregistration candidate could treat Stryker as the Arm D validator,
a separate authorized tranche would have to fail closed if any of these hold:

- exact packages do not install under the pinned study image and lock policy;
- the Vitest runner cannot execute the producer-visible test topology;
- the diff-derived mutation scope includes tests, generated files, unchanged
  production paths, or an unbounded portion of the repository;
- the validator receives any hidden scorer bytes or C1-specific configuration;
- output reveals hidden cases, historical fix material, coordinator analysis,
  or data not derivable from the producer's own tree and validator execution;
- the dry run fails, times out, or returns partial output but is reported as a
  clean validator result;
- runtime or token cost cannot fit the common arm budget; or
- the post-hoc all-arm invocation differs from the treatment-time D tool/config
  except for feedback availability.

## Evidence plan for the next possible tranche

If separately authorized, the smallest next tranche is a **validator
materialization and non-leakage probe**, not preregistration. It would need to:

1. pin exact package tarball/integrity, Node image, configuration, adapter, and
   output-policy bytes;
2. use a disposable copy of the exact consumer baseline or an independently
   declared compatibility fixture, never an arm;
3. prove install, Stryker dry-run, bounded changed-line mutation, timeout, and
   failure classifications;
4. audit the complete filesystem/input allowlist and raw output for hidden-
   oracle or task-specific leakage; and
5. record cost and decide whether the candidate is affordable enough to enter
   a later preregistration proposal.

That tranche is not authorized by this document.

## Claim ceiling

This preflight may claim only that:

- C1's identifier-free title/publisher fallback has a product source and fixed
  fixture that predate the Skill freeze, historical fix, and hidden oracle; and
- StrykerJS with its Vitest runner is a credible candidate for a non-leaking,
  diff-scoped Arm D test-sensitivity mechanism worth a later compatibility and
  leakage probe.

It does not claim that Stryker is installed, integrated, executable in C1,
affordable, frozen, accepted, or effective. It does not claim that Gate 1 is
ready for preregistration or that any experiment may run.

## Terminal disposition

Terminal disposition: **`VALIDATOR_CANDIDATE_FOUND`**.

The independent product-source question is closed. The prior
`OPEN_BLOCKING_BEFORE_PREREGISTRATION` state is narrowed: a credible validator
candidate now exists, but its exact integration and non-leakage behavior remain
unverified. Gate 1 preregistration therefore remains unauthorized.
