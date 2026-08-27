# Machine-policy setup long-path correction

## Problem

The setup-02 executor called `git -C` with its deeply nested freeze directory.
Git for Windows could not change into that path and returned `Filename too
long`. The unhandled `CalledProcessError` prevented terminal publication even
though no machine mutation occurred.

## Current repository truth

PR #125 merged the reviewed identity-first freeze commit
`b6a73ba39e4abba5a9d6cb4ddf7c03b346b0ac39`. Its observer and rollback
contracts remain valid. Attempt 02 produced no output root, terminal, setup
evidence, policy receipt, target file, or policy parent directory.

## Target outcome

Resolve the executing commit through the bounded repository root. Any Git
identity failure must create one bounded terminal before observer execution or
machine mutation, without retaining raw Git output.

## Scope

1. Replace the deep-directory Git invocation with a repo-root working directory.
2. Validate one lowercase 40-hex HEAD and reject stderr or non-zero exit.
3. Map launch, timeout, path, exit, and malformed-output failures to
   `MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE`.
4. Publish a terminal with `executing_commit_verified=false` and a zero commit
   sentinel when HEAD cannot be verified.
5. Add synthetic and real deep-path regression tests.

## Non-goals

No setup retry, machine mutation, rollback, qualification, hosted request,
randomization, arm execution, push, or PR belongs to this tranche.

## Affected surfaces

The executor, terminal policy/schema, setup evidence attempt identity,
manifest, tests, README, and this specification are affected. Observer,
rollback, requirements payload, output policy, and downstream receipt semantics
remain unchanged.

## Boundary and failure paths

Git identity remains a pre-authority prerequisite. An unavailable identity
cannot be substituted with the owner-authorized SHA or manifest metadata.
Terminal publication must be create-once and precede observer access. Raw
stderr, exception text, environment data, and paths are forbidden.

## Evidence plan

Run focused tests, an actual deep-path Git fixture, fresh-checkout tests under
`core.autocrlf=true`, frozen-file and source-binding inventory, leakage scan,
diff check, and the canonical precommit entrypoint.

## Claim ceiling

Passing evidence proves only that these frozen bytes use the bounded repo-root
identity path and terminalize synthetic Git identity failures. It does not
prove setup succeeds, authorize retry, install policy, qualify containment, or
authorize randomization or arms.

## Implementation tranche

Create one local correction-freeze commit and stop for independent review.
