# Technical specification

## Problem

The original C1 producer permissions freeze `network=false`, while the selected
runner invokes `--dangerously-bypass-approvals-and-sandbox`. That combination
cannot establish the common-input boundary and can expose later history or a
historical fix asymmetrically across A and B.

## Target

Freeze a new exact runner using:

```text
codex exec --ignore-user-config --sandbox workspace-write
  --ask-for-approval never
  -c windows.sandbox="elevated"
  -c sandbox_workspace_write.network_access=false
```

The runner retains the existing Job Object process-tree launcher as an exact
source-bound dependency. It replaces only the Codex command, preflight, command
contract, and related client identity projection.

## Boundaries

- Hosted transport is permitted for one task-neutral qualification request.
- Model-generated task commands must be offline.
- Only the elevated Windows sandbox is acceptable.
- A reviewed machine-policy receipt is separately owner-bound before execution.
- The task denial artifact must be produced inside the exact runner workspace.
- No randomization state is read or written.

## Evidence

Qualification requires the conjunction of successful hosted transport, all
applicable network classes denied in parent and child task processes, observation
of the dedicated offline sandbox account class, exact policy bytes, exact
preflight, cleanup, inventory guard, and leakage scan.

## Claim ceiling

This committed directory freezes implementation bytes only. It does not prove
machine setup, network containment, hosted compatibility, pair-03 readiness, or
any arm effectiveness.

