# Technical specification: Probe-02 invocation journal

## Problem

Probe-01 consumed one owner-authorized invocation before an attempt claim and
left no terminal. The Probe-02 readiness correction removes the observed empty
parent trigger, but its terminal policy still consumes authority on a preclaim
failure while forbidding a preclaim terminal. The child terminal publisher can
also fail after an attempt claim and leave only an unauthenticated empty
directory.

## Current repository truth

- Correction head `2e42cc6abe0c3f6cdea89e660cc1271c5842fb33` keeps
  `preclaim_failure_consumes_owner_pipeline_authority=true` and
  `preclaim_failure_terminal_allowed=false`.
- Its driver rethrows every exception before `claim_owned` becomes true.
- Synthetic `os.replace` denial after claim left no terminal or staging bytes.
- Read-only audit session `2026-08-28-69` returned
  `SILENT_FAILURE_PATH_REMAINS`.

## Target outcome

Create one independent journal root. Publish and read back a bounded start
receipt before launching the child. The receipt binds the exact execution
packet, readiness review, commit and journal bootstrap. The visible start receipt is the only
authority-consumption boundary. It survives child crash, nonzero exit, absent
child terminal and journal outcome-publication failure.

## Scope

- One new frozen directory.
- One streamed outer bootstrap and its exact manifest.
- Start/outcome journal schemas and state inspection.
- Synthetic ordering, crash, nonzero, publication-denial and concurrency tests.

## Non-goals

- No readiness execution or receipt.
- No Probe-02 or sandbox helper launch.
- No hosted request, auth payload, qualification-03, randomization or arms.
- No modification of the existing Probe-01 or Probe-02 freezes.
- No claim that arbitrary power loss or storage loss is preventable.

## Affected surfaces

Only the new directory is affected. The child pipeline is source-bound to the
reviewed Probe-02 bootstrap bytes at `2e42cc6a`. Existing terminal policy and
executor files remain byte-identical.

## Boundary and API considerations

Before `start.json` is visible, failure does not consume formal execution
authority and the child must not launch. Once `start.json` is visible, absence
of `outcome.json` is a bounded `INVOCATION_STARTED_OUTCOME_INCOMPLETE` state,
not a claim that the child completed. A concurrent loser cannot publish,
cleanup or launch.

## Failure paths and risk points

- Binding/runtime/root failure: no journal, no child, authority unconsumed.
- Start publication failure: no child; empty root is removed when safe.
- Child launch exception/crash/nonzero/timeout: bounded outcome is attempted.
- Outcome publication failure: durable start receipt remains authoritative.
- Abrupt wrapper death after start: start-only journal is bounded incomplete
  evidence.
- Concurrent invocation: one atomic journal owner; loser has no side effects.

## Evidence plan

Tests assert exact ordering, raw-output exclusion, create-once behavior,
start-only inspection, child terminal digest projection, frozen bindings and
absence of all formal roots. Focused tests and canonical precommit must pass
before the local commit.

## Claim ceiling

This freeze may establish only reviewed implementation bytes and synthetic
failure behavior. It cannot establish readiness PASS, Probe-02 execution,
sandbox capability, qualification, randomization or treatment effects.

## Implementation tranche recommendation

This directory is the single tranche. Stop after its local commit and
independent review. Any execution authorization must later bind the exact
merged commit, bootstrap blob OID and full streamed command.
