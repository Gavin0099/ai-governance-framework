# Binding correction technical specification

## Problem

PR #127 validated historical Git blobs but later imported executable modules
from working-tree paths. It also read its self-excluded manifest from the
working tree before checking owner authority. A dirty tree could therefore
change the execution policy or code while preserving the authorized HEAD.

## Current repository truth

- PR #127 merged at `0ead587a44938d780a97570d0b9a4ac1067a6a07`.
- Its reviewed head is `b6e8eb166dca2b3100ead420c5767f576221a023`.
- GitHub Codex review comments `3873331468` and `3873331472` identify the two
  P1 binding failures.
- Qualification attempt 01 has no output or staging root and no hosted request.
- The machine-policy payload remains independently reviewed and unchanged.

## Target outcome

The owner-authorized commit is the sole source of manifest and executable
dependency bytes. Working-tree or module-cache state cannot select them.

## Scope

- one new correction freeze directory;
- corrected executor, manifest, terminal policy, frozen receipt, and tests;
- exact reuse of the reviewed qualification semantics and attempt identity.

## Non-goals

- no qualification or hosted request;
- no consumer amendment, randomization, producer, scorer, or arm;
- no edit to the merged PR #127 directory;
- no machine-policy change, mapping release, or Rekor POST.

## Affected surfaces

- manifest bootstrap;
- Git-object source validation/materialization;
- module loading and dependency-name isolation;
- pre-auth and pre-staging ordering;
- create-once qualification terminal path.

## Boundary and API considerations

The CLI remains exactly `--owner-authorized-freeze-commit` plus `--auth-file`.
The attempt ID and publication roots remain unchanged. The manifest remains
self-excluded from its own frozen-file list, but is loaded only as a Git blob
from the authorized commit.

## Claim ceiling

This freeze can establish only that the correction bytes are reviewable and
tested. It does not establish sandbox qualification, hosted transport, network
denial, consumer readiness, or machine-wide bypass prohibition.

## Failure paths and risk points

- wrong authority fails before manifest use;
- invalid manifest/source blobs fail before staging or auth read;
- unsafe bound paths fail before materialization;
- pre-existing output/staging roots are never overwritten or deleted;
- module-cache entries are restored after exact modules are loaded;
- any terminal still consumes the future qualification attempt.

## Evidence plan

- adversarial dirty-manifest redirect test;
- dirty runner and dirty legacy launcher tests;
- pre-seeded module-cache/path injection test;
- binding failure tripwires for zero auth read, zero root creation, and zero
  hosted launcher calls;
- focused, fresh-checkout, inventory, leakage, diff, and canonical precommit.

## Implementation tranche

Add and commit only this directory, then stop for independent review before any
execution authorization.
