# Technical specification

## Problem

The reviewed readiness bootstrap returns the readiness receipt only on stdout.
No frozen executable owns create-once publication at the manifest-bound
repo-external receipt path, so a shell capture failure could leave an
owner-authorized readiness invocation without trustworthy evidence.

## Current repository truth

- Predecessor merge commit: `0872889912ec7bc6f881e59082d726c7fc2db67e`.
- Trusted bootstrap blob: `595e0111df1b1b8a1927609a12c9e3430a801e08`.
- The predecessor bootstrap verifies bindings and returns one receipt on
  stdout; it does not publish that receipt.
- The frozen readiness manifest requires immutable rev1 receipt and review
  paths. Neither file nor their evidence root existed when this freeze was
  authored.

## Target outcome

Freeze a trusted publisher that makes every post-start readiness result
reviewable as either the exact success receipt or a bounded failure terminal.

## Scope

- Verify all bindings before evidence-root creation and child launch.
- Exclusively create the fixed evidence leaf root.
- Publish and read back a start record before child launch.
- Capture bounded child transport evidence without retaining raw output.
- Accept only one strict readiness receipt and publish its exact bytes.
- Publish a bounded terminal for post-start failure.

## Non-goals

- No readiness execution or authorization.
- No review packet creation or approval assertion.
- No Probe-02, hosted request, Qualification-03, randomization, producer,
  scorer, mapping release, Rekor POST, or arm execution.
- No modification of predecessor freeze bytes.

## Affected surfaces

Only this new freeze directory. The evidence path is bound but not created by
this authoring tranche.

## Boundary and API considerations

The publisher is stdin-only. `PATH`, working-tree code, `sys.path`, and Git
replace objects are not trust roots. The child is the exact predecessor
bootstrap blob and receives the future exact owner-authorized freeze commit.
The predecessor commit is a source baseline; it cannot be the future executing
commit because this publisher does not exist in that tree.

The evidence root permits only `start.json`, the fixed rev1 receipt, and
`terminal.json` before independent review. The review packet remains absent.
Receipt or terminal staging files are removed on publication failure.

## Claim ceiling

This freeze can establish reviewable publisher bytes and synthetic ordering,
classification, and publication behavior. It cannot establish readiness PASS,
evidence-root availability, Probe-02 readiness, sandbox capability, execution
convergence, or any downstream authority.

## Failure paths and risk points

- Binding failure occurs before root creation and child launch.
- Existing evidence root fails closed and cannot be reused.
- Start publication failure launches no child; an empty claimed root is removed.
- Nonzero, timeout, stderr, invalid JSON/schema, and receipt publication failure
  produce a bounded terminal after durable start.
- Terminal publication failure leaves durable start evidence and raises.
- Concurrent invocation losers cannot launch or clean up the winner.

## Evidence plan

Focused tests cover direct execution, binding-before-root, existing root,
successful exact receipt publication, nonzero, timeout, stderr, invalid JSON,
schema drift, receipt-publication denial, terminal-publication denial,
concurrency, staging cleanup, and absence of raw child output. A fresh checkout
repeats the focused suite. Canonical precommit remains the repository boundary
gate and is not full-repository proof.

## Implementation tranche recommendation

This directory is the sole tranche. Commit locally after focused,
fresh-checkout, and canonical precommit validation, then stop for independent
review.
