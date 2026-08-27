# Technical specification

## Goal

Freeze a reviewable implementation that can make exactly one future machine
mutation: atomically create the exact 58-byte managed requirements file after
all authority, drift, path, and independent rollback checks pass.

## Inputs and bindings

- executing freeze commit and setup-plan digest, supplied by the owner;
- exact committed payload and frozen source bindings;
- read-only observation from `machine_policy_observer.ps1`;
- create-once rollback precheck produced by an independent elevated owner
  PowerShell using `independent_owner_rollback.ps1`.

The two repo-external reviewed packets are bound by literal line, byte, and
SHA-256 metadata in the manifest; their contents are not copied here.

## Preconditions before mutation

1. Frozen files and source bindings are exact.
2. Owner authority equals the executing commit and frozen setup-plan digest.
3. Account/SID and firewall observations equal the frozen bounded projection.
4. The target and legacy alternatives are absent.
5. The target is the exact ProgramData path with no traversal or reparse point.
6. The independent rollback precheck is exact, elevated, outside policy and
   scratch roots, and its shell remains held open.
7. Bounded pre-state evidence is assembled before atomic publication.

Randomness and hosted transport do not exist in this executor.

## Publication and verification

Publication uses an exclusive sibling staging file followed by atomic replace
into an absent target. The executor verifies regular-file type, 58 bytes, and
the frozen SHA-256. It then re-observes account/firewall invariants. Any
post-write failure invokes the frozen rollback script through the already-open
independent owner channel; rollback never authorizes retry.

## Rollback

Rollback removes only the exact target when its resolved path, regular-file
type, byte count, and digest all match. It removes only directories explicitly
recorded as setup-created and only when empty. A mismatch is review-required;
deletion followed by unverifiable absence is state-ambiguous.

## Retention

Retained evidence is aggregate and digest-only. Raw SID, account name, firewall
rule names, security descriptors, payload bytes, credentials, authorization,
hosted prompts/responses/events, and unrelated paths are forbidden recursively.

## Validation

Focused synthetic tests cover authority and plan mismatch, invalid rollback
precheck, state drift, existing target, path/reparse rejection, atomic failure,
post-write rollback outcomes, terminal precedence, forbidden retention,
downstream receipt exactness, and frozen/source binding integrity. Fresh-checkout
focused tests and the canonical precommit gate are required before commit.

## Non-goals and claim ceiling

No setup or rollback execution; no account/firewall/policy mutation; no hosted
request, sandbox qualification, randomization, producer, scorer, mapping
release, Rekor POST, push, or PR. This freeze is implementation evidence only.

