# Gate 2 timeout-outcome amendment v1 — 2026-07-28

Status: **owner-authorized for a new formal run only**.

Authority: the owner directed “先commit再往下做” after the operator proposed
this exact bounded slice: do not salvage the blocked run, pre-register a
blind-scorable terminal timeout outcome, fix only the experiment-local Windows
timeout cleanup, validate and commit, then start a new `D -> C -> A -> B` run.

## Problem

Formal run `gate2-formal-20260727-213336` observed a real protocol gap. Arm B
reached the frozen 1800-second wall-clock cap. The runbook already classifies
giving up or inability to complete as a legitimate result, but the scorer
handoff accepted only a clean producer output commit plus producer
`result.json`. The timeout therefore had no admissible blind-scorer packet and
the run correctly stopped as `BLOCKED`.

The Windows launcher also killed the `.cmd` wrapper before its child process
tree. The child retained the stdout pipe, so the existing timeout handler could
not finish until the operator terminated that exact child after the cap.

## Current repository truth

- The exact pinned image remains
  `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`.
- The sanitized source tree remains
  `36c346fa951a24cbf914ef04469aac5cb5fd8b86`.
- The order remains `D -> C -> A -> B`.
- The per-arm limits remain 60 tool calls and 1800 seconds.
- Normal completed outputs remain governed by scorer-handoff v3.
- The blocked run and its non-counted attempts are append-only evidence and
  are not inputs to the new formal run.

## Target outcome

A new formal run can finish process-integrity evaluation when each arm produces
exactly one of:

1. a normal, verified scorer-handoff v3 packet; or
2. a verified terminal-timeout v1 packet created after the frozen 1800-second
   cap.

Both packet kinds are presented to both independent scorers before mapping
release. The same five criteria, acceptance judgment, completion/evidence
consistency judgment, treatment guess and confidence fields remain required.

## Scope

- Add one experiment-local terminal-timeout packet builder/verifier.
- Make the experiment-local runner terminate the exact Windows process tree
  before collecting the timeout streams.
- On timeout, capture the final diff, final status, current HEAD/tree, exact
  cleanup receipt and digests of the transcript, adapter log and model stream.
- Mark the arm `terminal_timeout_complete` only after packet verification
  passes.
- Permit formal scoring and release when all four arms are either `complete` or
  `terminal_timeout_complete`.
- Reverify each packet according to its packet kind at mapping release.

## Non-goals

- Do not edit or reinterpret `gate2-formal-20260727-213336`.
- Do not synthesize a producer `result.json` or output commit.
- Do not change the successful scorer-handoff v3 contract or loosen its
  verifiers.
- Do not change the task, Skill, Governance, validator packets, scoring
  criteria, treatment mapping, model alias, budgets, image or baseline.
- Do not add a generic process runner, governance schema, hook, CI gate or
  framework-level timeout policy.
- Do not claim Skill effectiveness from one pilot.

## Terminal-timeout packet contract

The packet is operator-owned and contains no arm letter or mapping. It records:

- opaque run and container identities plus the frozen baseline commit;
- `outcome = timeout` and the frozen limit;
- whether a producer completion claim was submitted before the cap and, when
  present, its byte-exact `result.json`;
- the byte-exact final diff and complete porcelain status;
- current container HEAD/tree;
- a create-once timeout cleanup receipt;
- SHA-256 and byte counts for transcript, adapter log and model stream.

The anonymous ID is `OUT-` plus the first 12 hex characters of the SHA-256 of
the canonical packet core before the anonymous ID is attached. The full core
digest is retained. The manifest is written last and is the transaction marker.

Verification fails on an unexpected file set, identity mismatch, missing
artifact, digest/byte mismatch, non-timeout outcome, changed timeout constant,
arm-identity-bearing identity field, malformed cleanup receipt or absent
timeout evidence.

## Scoring semantics

For a terminal packet, “completion claim/evidence consistency” means whether
the operator statement about claim presence agrees with the packet and, when a
producer claim exists, whether that byte-exact claim agrees with the evidence.
An absent claim is never synthesized or replaced by operator prose.
Scorers award the same five evidence points; unsupported criteria remain false.
No score normalization or special timeout bonus is allowed.

## Process-integrity decision

Gate 2 process integrity is `PASS` only when:

- resource and scorer admission passed before formal calls;
- D, C, A and B were dispatched in frozen order;
- every arm has one verified normal or terminal-timeout packet;
- both scorers submitted all required judgments before mapping existed;
- mapping release and packet reverification succeeded.

A timeout may therefore be a valid experimental outcome without being an
accepted bug fix.

## Failure paths

- Process-tree cleanup cannot be verified: stop; no terminal packet.
- Container evidence cannot be captured: stop; no terminal packet.
- Terminal packet verification fails: stop; arm is not complete.
- External rate limit or instrument failure: preserve as non-counted only under
  the already frozen recovery rules.
- Any old-run mutation or mapping disclosure before both submissions: stop and
  invalidate the new run.

## Evidence plan

- Focused unit tests for exact Windows tree cleanup ordering, timeout receipt,
  packet create/verify, tamper rejection, arm-identity rejection and mixed
  normal/terminal completion logic.
- Existing formal-runner, scorer packet, scorer handoff and channel tests.
- Canonical `scripts/run-runtime-governance.sh --mode enforce`.
- Fresh pinned-image resource audit and two live scorer admissions before the
  first new formal arm.

## Claim ceiling

This amendment authorizes and specifies one new formal run. It does not make the
blocked run complete, prove the new implementation correct before validation,
or establish Skill effectiveness.
