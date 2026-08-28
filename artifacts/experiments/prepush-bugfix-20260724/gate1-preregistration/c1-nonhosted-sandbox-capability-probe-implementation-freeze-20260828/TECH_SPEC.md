# Technical specification: non-hosted absolute-Python sandbox probe

## Problem

Qualification-02 failed because the frozen runner deliberately omitted `PATH`
while its prompt used bare `python`. The remaining uncertainty is narrower:
whether pinned absolute Python is visible and executable through the same exact
Windows sandbox task-command filesystem/exec plane.

## Current truth

- rev1 freezes the two-control design and create-once evidence rules.
- rev2 binds exact-build `sandbox --help` and corrects the interface to
  `codex sandbox [OPTIONS] [COMMAND]...`.
- qualification-01 and qualification-02 are consumed and immutable.
- no qualification-03 or cohort-02 randomization exists.

## Target outcome

One later owner-authorized execution produces exactly one terminal:

- `ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE`
- `CAPABILITY_PROBE_SURFACE_UNAVAILABLE`
- `CAPABILITY_PROBE_AMBIGUOUS`
- `CAPABILITY_PROBE_CLEANUP_FAILED`

The implementation deliberately has no `ABSOLUTE_PYTHON_TASK_PLANE_DENIED`
terminal. A nonzero absolute-control result without a separate bounded denial
proof remains `CAPABILITY_PROBE_AMBIGUOUS`; raw stderr text or message
substrings may not upgrade that evidence to denial.

## Boundaries

All Git bindings, external packet bindings, runtime bytes, and create-once root
absence are checked before any probe root exists. The bootstrap and executor are
both streamed from authorized Git blobs. `PATH` is absent. No auth payload is
accepted by the parser or read by the implementation.

The negative control runs first. A marker or zero exit from bare `python`
invalidates the probe. The positive control uses the exact absolute Python path.
Only exact marker bytes, zero exit, empty stdout, and empty stderr are positive.

Private roots and the staged CLI are deleted before a positive terminal is
published. Cleanup failure overrides every other result.

The final output directory is created atomically before any private or CLI root.
That successful `mkdir` is the create-once attempt claim. An overlapping loser
must stop before materialization and may not clean or publish anything owned by
the winner.

## Non-goals

No hosted request, sandbox qualification, qualification-03, consumer amendment,
machine-policy mutation, randomization, producer, scorer, arm, mapping release,
Rekor POST, provider-model observation, or Skill-effectiveness claim.

## Evidence plan

Focused tests cover dirty working-tree redirection, direct executor rejection,
binding-before-root ordering, forbidden argv, missing `PATH`, negative-control
unexpected success, ambiguous nonzero positive evidence, atomic attempt ownership,
loser cleanup isolation, ambiguous marker/output, cleanup override,
create-once publication, and zero hosted/auth surfaces. Fresh checkout and the
canonical precommit gate are required before the local freeze commit.
