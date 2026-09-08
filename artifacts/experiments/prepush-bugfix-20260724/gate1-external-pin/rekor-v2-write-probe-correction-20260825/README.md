# Rekor v2 write-path correction freeze

## Problem

The first frozen write probe stopped before POST because its executor manually
constructed unhashed TUF target URLs.  Sigstore's consistent-snapshot targets
are hash-prefixed, so both required payload requests returned HTTP 404.  The
failed terminal is valid evidence and must remain immutable; it cannot be
repaired or retried in place.

## Current repository truth

- PR #114 merged the pinned Rekor v2 provider profile, formal TUF bootstrap,
  and proof-bearing receipt verifier at merge commit `26552169e422038f2d642c2141e2a51e7a6b121d`.
- PR #115 merged the first freeze at `293118e2ad89a3c80183f5189fe03568af9d5304`.
  Its single authorized execution produced `WRITE_PROBE_PRECONDITION_FAILED`,
  terminal SHA-256 `baa0824d...e77c`, with zero POST attempts and no possible
  public append.
- The provider profile still declares `write_path_qualified: false` and keeps
  D5 final-head countability unresolved.
- The preregistration freeze is in main.  The separately reviewed admission
  commit `44573d00b0949999035e2d7941f2e5afcf1eef17` is not in main and is not
  consumed by this tranche.
- The official Rekor v2 client contract at the frozen upstream commit defines
  one write API: `POST /api/v2/log/entries`, with a minimum 20-second timeout.

## Target outcome

Freeze a corrected single-use probe whose actual executor delegates metadata
refresh, consistent-snapshot target URL selection, download, and target hash
verification to python-tuf `Updater`.  A later owner authorization may execute
that new exact commit once.  This tranche performs no public write.

## Scope

- exact public endpoint, method, headers, timeout, subject, request schema;
- formal python-tuf refresh, target resolution, download, and provider
  selection before POST;
- per-run ephemeral ECDSA P-256 signing key held in memory only;
- exactly one POST attempt, with no credentials and no retry;
- proof-bearing response verification through `governance_tools.rekor_provider`;
- a bounded normalized proof receipt plus aggregate-only, write-once terminal;
- synthetic success, consistent-snapshot URL, unhashed-404 regression,
  corruption, authority, retention, and failure tests.

## Non-goals

- no POST, public entry, credential access, admission/runtime wiring, mapping
  release, preregistration amendment, randomization, or arm execution;
- no claim that the write path is qualified before the separately authorized
  probe succeeds;
- no resolution of D5 final-head countability;
- no witness or RFC3161 timestamp authority claim.

## Affected surfaces

Only this new freeze directory is changed.  The merged provider module and
profile are consumed by binding and import; they are not modified.  The prior
freeze and its repo-external terminal are not copied or edited.

## Boundary and API considerations

The executor accepts only an owner-authorized commit equal to its current Git
HEAD and verifies every frozen file digest before network access.  TUF GETs are
read-only.  `tuf.ngclient.Updater` owns target URL construction and verifies
downloaded length and hashes; the executor may not construct target URLs.
Because python-tuf 7.0.0 requires a privileged root-cache symlink on Windows,
the frozen adapter replaces only that local alias with an atomic byte copy;
POSIX uses the upstream symlink implementation unchanged.
POST uses only `Accept`, `Content-Type`, and a frozen `User-Agent`;
authorization, cookie, proxy-authentication, and custom credential headers are
forbidden.  A dispatched POST means a public append may have occurred even if
the response is later rejected.

## Failure paths and risk points

- committed manifest schema, authority, or frozen-byte mismatch: stop before
  network and retain a bounded fail-closed terminal when the output surface is
  valid;
- TUF/provider failure, missing target, or manual-client contract drift: stop
  before POST;
- HTTP rejection or transport ambiguity: fail closed and report that append
  may have occurred once dispatch began;
- invalid proof, checkpoint, body, or request binding: fail closed;
- raw response retention, proof-receipt/terminal retention failure, forbidden
  field, or pre-existing terminal: fail closed without retry.

## Evidence plan

Synthetic tests inject a transport and verifier.  A disposable Git repository
also exercises the public `execute_probe` entrypoint against committed freeze
bytes, proving both zero network on authority failure and terminal retention on
committed-schema failure.  The remaining tests prove python-tuf requests
hash-prefixed targets, the two unhashed URLs from the failed freeze are never
requested, target 404 stops before POST, one POST occurs at most, and retention
remains bounded.  Existing Rekor tests remain the authority for TUF, signature,
and inclusion mathematics.

## Claim ceiling

This correction freeze proves only that the observed target-fetch defect has a
committed, testable correction and that the prior failed terminal remains
bound.  It does not prove that a public append was attempted, accepted,
included, countable, or connected to Gate 1.

## Implementation tranche recommendation

After review, push and merge this freeze.  A separate explicit owner authority
bound to the reviewed commit is required before executing the public write.
