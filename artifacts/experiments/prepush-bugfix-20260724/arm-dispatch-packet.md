# Arm Dispatch Packet — pre-push version-bump advisory (SYMPTOM ONLY)

This is the ONLY task description an arm producer may read. It states the
observable symptom and reproduction. It deliberately contains **no** root cause,
no hypothesis, and no fix. Producers must diagnose and fix independently.

Producers must NOT read: any `docs/status/gate0-*`, any `docs/governance/gate1-*`,
`memory/*`, or any repository history newer than the baseline bundle. Doing so
invalidates the arm (the answer is recorded in those files).

## Environment

- You are given an isolated checkout at a single baseline commit. There is no
  network access to any remote and no history beyond the baseline.
- The repository is an AI-governance framework with git hooks under
  `scripts/hooks/` and Python tools under `governance_tools/`.

## Observed symptom

When a branch is pushed, the pre-push hook prints an advisory "version bump
recommendation" that reports `changed_files=0`, even in pushes whose commits
add or modify files. The count does not reflect what the push actually delivers
to the remote branch.

## Reproduction

1. On the baseline checkout, create one commit that adds at least one file, on a
   branch whose tip is **not** the currently checked-out `HEAD` (for example,
   build the commit with git plumbing while `HEAD` stays on another branch; or
   check out a branch that is behind the remote default branch).
2. Trigger the pre-push path so the version-bump advisory runs for that pushed
   branch.
3. Observe the advisory prints `changed_files=0` while the pushed commit adds
   files.

## Acceptance criterion (what "fixed" means)

The version-bump advisory reports the files that the push actually adds/changes
for the pushed ref, in the reproduction scenario above. A regression test must
fail before your change and pass after it, and must fail again if your change is
reverted.

## Scope

- In scope: the version-bump advisory's file-counting behavior only.
- Out of scope (do NOT change): the runtime-governance smoke step, CI workflows,
  gates, enforcement, or any consumer repository.
