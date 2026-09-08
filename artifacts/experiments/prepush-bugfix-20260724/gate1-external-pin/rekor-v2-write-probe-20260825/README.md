# Rekor v2 write-path qualification freeze

## Problem

The read and proof-verification path is qualified, but a real Rekor write is a
public, irreversible side effect.  The exact executor, request boundary,
retention policy, and terminal semantics must therefore be reviewable before
any POST occurs.

## Current repository truth

- PR #114 merged the pinned Rekor v2 provider profile, formal TUF bootstrap,
  and proof-bearing receipt verifier at merge commit `26552169e422038f2d642c2141e2a51e7a6b121d`.
- The provider profile still declares `write_path_qualified: false` and keeps
  D5 final-head countability unresolved.
- The preregistration freeze is in main.  The separately reviewed admission
  commit `44573d00b0949999035e2d7941f2e5afcf1eef17` is not in main and is not
  consumed by this tranche.
- The official Rekor v2 client contract at the frozen upstream commit defines
  one write API: `POST /api/v2/log/entries`, with a minimum 20-second timeout.

## Target outcome

Freeze a single-use, non-counted synthetic write probe whose actual executor
is included in the reviewed bytes.  A later owner authorization may execute
that exact commit once.  This tranche performs no public write.

## Scope

- exact public endpoint, method, headers, timeout, subject, request schema;
- formal TUF refresh and provider selection before POST;
- per-run ephemeral ECDSA P-256 signing key held in memory only;
- exactly one POST attempt, with no credentials and no retry;
- proof-bearing response verification through `governance_tools.rekor_provider`;
- a bounded normalized proof receipt plus aggregate-only, write-once terminal;
- synthetic success, corruption, authority, retention, and failure tests.

## Non-goals

- no POST, public entry, credential access, admission/runtime wiring, mapping
  release, preregistration amendment, randomization, or arm execution;
- no claim that the write path is qualified before the separately authorized
  probe succeeds;
- no resolution of D5 final-head countability;
- no witness or RFC3161 timestamp authority claim.

## Affected surfaces

Only this new freeze directory is changed.  The merged provider module and
profile are consumed by binding and import; they are not modified.

## Boundary and API considerations

The executor accepts only an owner-authorized commit equal to its current Git
HEAD and verifies every frozen file digest before network access.  TUF GETs are
read-only.  POST uses only `Accept`, `Content-Type`, and a frozen `User-Agent`;
authorization, cookie, proxy-authentication, and custom credential headers are
forbidden.  A dispatched POST means a public append may have occurred even if
the response is later rejected.

## Failure paths and risk points

- authority or frozen-byte mismatch: stop before network;
- TUF/provider failure: stop before POST;
- HTTP rejection or transport ambiguity: fail closed and report that append
  may have occurred once dispatch began;
- invalid proof, checkpoint, body, or request binding: fail closed;
- raw response retention, proof-receipt/terminal retention failure, forbidden
  field, or pre-existing terminal: fail closed without retry.

## Evidence plan

Synthetic tests inject a transport and verifier.  They prove zero network on
precondition failure, one POST at most, exact endpoint/headers, no credentials,
aggregate-only terminal shape, bounded proof-receipt retention, and fail-closed
terminal precedence.  The normalized receipt retains only the public material
needed to rerun the merged proof verifier; the raw HTTP response is never
written.  Existing Rekor tests remain the authority for TUF, signature, and
inclusion mathematics.

## Claim ceiling

This freeze proves only that the proposed one-shot executor and its failure
semantics are committed and testable.  It does not prove that a public append
was attempted, accepted, included, countable, or connected to Gate 1.

## Implementation tranche recommendation

After review, push and merge this freeze.  A separate explicit owner authority
bound to the reviewed commit is required before executing the public write.
