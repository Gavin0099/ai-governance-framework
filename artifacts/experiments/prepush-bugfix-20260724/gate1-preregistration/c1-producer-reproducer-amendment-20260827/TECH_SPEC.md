# Technical specification: C1 A/B producer-visible reproducer

## Problem statement

The frozen C1 common task tells producers to run a supplied black-box reproducer,
but the preregistration freeze contains only a scorer-only oracle. No reviewed,
producer-visible reproducer artifact or exact command exists. Producer execution
must stop rather than invent either input after randomization.

## Current truth

- The immutable preregistration freeze is commit
  `7109f3c24f9e38df161e4fd93c729820a151f0eb`.
- Its common task names a black-box reproducer, but does not bind its bytes or
  command.
- The existing oracle is explicitly `producer_visible=false` and
  `scorer_only=true`; it is not an admissible source for this amendment.
- No C1 producer or arm is executed by this tranche.

## Target outcome

Freeze one task-neutral, black-box Vitest file and one exact shell-free command
as identical common input for A and B. The test calls the baseline's exported
public bulk-import POST route, prints a bounded canonical observation, and makes
no correction assertion.

## Scope boundaries

In scope: pinned baseline public route, synthetic in-memory fixture, exact test
destination, exact command, append-only common-input amendment, aggregate-only
validation evidence, and self-verifying bindings.

Out of scope: scorer-only oracle bytes, candidate commit or diff, historical fix,
producer execution, hosted-model calls, scoring, mapping release, Rekor POST,
randomization, and any C or D producer authorization.

## Affected surfaces

Only this new amendment directory is affected. The original preregistration,
runtime admission, randomization records, memory, and product repository remain
byte-immutable.

## Boundary and exact command

The reproducer source is materialized byte-for-byte at
`src/__tests__/c1-gate1-black-box-reproducer.test.ts` in an owned disposable
checkout of the pinned baseline. The command is the exact structured `argv` in
`reproducer-contract.json`; no shell, glob expansion, network access, or hidden
test discovery is allowed.

The output contract is one line prefixed with
`C1_REPRODUCER_OBSERVATION=`. It records only two synthetic input identifiers and
the two catalog identifiers exposed at the route's staging boundary.

## Claim ceiling

This freeze proves that a common A/B reproducer and command are reviewable and
that the pinned baseline produced the recorded synthetic observation. It does
not prove producer readiness, a corrected outcome, Skill effectiveness,
governance effectiveness, validator-feedback effectiveness, or arm countability.

## Failure paths

- Any source-binding, frozen-file, destination, or command mismatch fails closed.
- Any attempt to add a scorer assertion, candidate-derived expectation, shell,
  extra test path, or forbidden provenance token fails validation.
- A nonzero reproducer exit, missing canonical line, wrong observation digest,
  retained private path, or scratch cleanup failure invalidates validation.
- The reproducer itself does not decide pass/fail for a future producer outcome.

## Evidence plan

Retain only baseline Git object bindings, the reproducer bytes, structured argv,
aggregate command result, canonical observation digest, and cleanup flag. Do not
retain consumer repository names, local paths, raw process streams, file-tree
inventories, candidate bytes, or oracle bytes.

## Implementation tranche recommendation

After this freeze is independently reviewed and merged, a separate producer
pre-run freeze may bind this amendment and implement A/B execution and sealing.
That future tranche requires new owner authorization and remains outside this
DONE condition.
