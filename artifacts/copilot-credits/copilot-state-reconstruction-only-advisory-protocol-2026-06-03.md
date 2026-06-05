# Copilot State Reconstruction Only Advisory Protocol

## Scope

This advisory protocol defines a small experiment for the first turn after a
compacted or long-context continuation. It is based on the Copilot UI credit
outlier review in:

`artifacts/copilot-credits/copilot-ui-credit-outlier-review-2026-06-03.md`

The goal is to reduce avoidable context cost by separating state recovery from
implementation, qualification, commit, push, memory writing, and closeout work.

## Claim Ceiling

CLAIMED:

- A non-enforcing advisory protocol for `state_reconstruction_only` turns.
- A bounded task shape for post-compaction context recovery.
- A trial-ready output format for one future observation.

NOT CLAIMED:

- Enforcement.
- Budget threshold.
- Runtime gate.
- Hook integration.
- Automated detection of compaction.
- Automated credit reduction.
- Billing truth.
- Token count.
- Proof that the protocol reduces credits.

## Trigger

Use this advisory protocol when any of the following is true:

- The UI or assistant context says `Compacted conversation`.
- The user asks to continue a long-running task after a context reset.
- The assistant needs to reconstruct prior state before deciding the next
  implementation or validation step.

Do not use it when the user gives a small, direct, self-contained task that does
not require state recovery.

## Allowed Actions

During a `state_reconstruction_only` turn, the assistant may:

- Read the minimum relevant prior artifact or summary.
- Identify current task state.
- Identify the last completed concrete outcome.
- Identify the next narrow DONE candidate.
- List known blockers and unknowns.
- Report whether implementation can safely proceed in the next turn.

## Forbidden Actions

During a `state_reconstruction_only` turn, the assistant should not:

- Edit files.
- Run broad tests.
- Commit.
- Push.
- Write memory.
- Generate new governance artifacts.
- Open a new implementation slice.
- Convert the reconstruction into closeout.
- Decide budget thresholds or workflow policy.

Exception: if the user explicitly requests one of these actions, treat that as a
new task and leave `state_reconstruction_only` mode.

## Output Shape

Recommended output:

```text
Mode: state_reconstruction_only
mode_source: compacted_or_long_context_continuation
task_authority: user_request

Recovered state:
- last completed outcome: <one line>
- current unresolved issue: <one line>
- relevant artifacts: <short list>

Next DONE candidate:
- <one narrow measurable outcome>

Not doing in this turn:
- edits
- tests
- commit
- push
- memory
- closeout

Risk:
- <one line about uncertainty or missing mapping>
```

## Success Signal

The protocol is considered useful only if a future observation shows:

- The reconstruction turn stays bounded.
- The next implementation or validation turn has a narrower DONE.
- The user can decide whether to proceed without requiring another broad
  context recovery turn.

Credit reduction is a hypothesis, not a claim.

## Trial Record Template

For a future trial, record:

```text
date:
source_context:
used_protocol: yes/no
credits:
next_turn_credits:
task_class:
compacted: yes/no
did_edit_files: yes/no
did_run_tests: yes/no
did_commit_or_push: yes/no
useful_outcome:
notes:
```

## Non-Goals

- This protocol does not replace implementation planning.
- This protocol does not make high-credit work invalid.
- This protocol does not block useful high-cost implementation.
- This protocol does not prove billing behavior.
- This protocol does not become repository policy until supported by more
  observations.
