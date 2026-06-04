# Fleet Git Read-Check Blockers - 2026-06-04

## Scope

Phase F-5 read-only diagnosis of the `git_check_failed` rows observed in the
Phase F-4 local overlay trial.

Commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& scripts\sync_governance_submodules.ps1 -VerifyModelOnly -LocalScopeFile governance\fleet\governance_scope.local.yaml | Out-String -Width 360"
```

Representative direct checks:

```powershell
git -C E:/BackUp/Git_EE/hp-firmware-stresstest-tool rev-parse --is-inside-work-tree
```

```powershell
git -C E:/BackUp/IsptoolRefine2018_EndUser_Tool rev-parse --is-inside-work-tree
```

## Result Summary

Observed required-tier rows: 10

- `global_ignore_permission`: 5
- `dubious_ownership`: 5
- `other`: 0

## Blocker Classes

### global_ignore_permission

Rows:

- hp-firmware-stresstest-tool
- cli
- CFU
- gl_electron_tool
- ai-governance-framework

Observed note:

```text
warning: unable to access 'C:\Users\reiko/.config/git/ignore': Permission denied
```

Representative direct check:

```text
git -C E:/BackUp/Git_EE/hp-firmware-stresstest-tool rev-parse --is-inside-work-tree
true
```

Interpretation:

This warning is not a hard Git worktree blocker. The direct representative
check returned `true`.

The current helper likely reports these rows as `git_check_failed` because it
compares the captured `rev-parse` output exactly to `true`; when Git emits a
warning before `true`, the output is no longer exactly equal to `true`.

Recommended next remediation:

- update the helper to parse `rev-parse --is-inside-work-tree` more robustly;
- accept a final or present line equal to `true` even if warnings are also
  emitted;
- preserve the warning in `Note` rather than treating it as a hard failure.

### dubious_ownership

Rows:

- IsptoolRefine2018_EndUser_Tool
- lenoveo-isp-tool-avalonia
- Command_Line_Tool
- General_End_User_Tool
- Kernel-Driver-Contract

Observed representative note:

```text
fatal: detected dubious ownership in repository at 'E:/BackUp/IsptoolRefine2018_EndUser_Tool'
```

Representative direct check:

```text
git -C E:/BackUp/IsptoolRefine2018_EndUser_Tool rev-parse --is-inside-work-tree
fatal: detected dubious ownership in repository at 'E:/BackUp/IsptoolRefine2018_EndUser_Tool'
```

Interpretation:

This is a real read-check blocker for the current sandbox user. The direct
representative check failed before normal worktree detection.

Recommended next remediation:

- do not auto-repair from the helper;
- require explicit user approval before running any `git config --global --add safe.directory ...`;
- if approved, apply safe-directory exceptions only to the required paths that
  the user intends to inventory.

## Suggested Next Slice

Phase F-6 should be a helper robustness fix, not a Git permission repair:

- classify non-fatal global ignore warnings separately;
- parse `rev-parse` output for a `true` line instead of strict full-output
  equality;
- preserve warning notes;
- rerun inventory to see whether the five `global_ignore_permission` rows can
  proceed to submodule detection.

The `dubious_ownership` rows should remain blocked until explicit user approval
is given for safe-directory configuration.

## Claim Ceiling

CLAIMED:

- read-only diagnosis of the 10 F-4 `git_check_failed` rows;
- classification into 5 non-fatal global ignore permission warnings and 5
  dubious ownership blockers;
- remediation proposal only.

NOT CLAIMED:

- Git access repaired;
- safe-directory configured;
- global ignore permission fixed;
- external repos modified;
- submodule model detected;
- fleet migration state;
- update or sync readiness;
- hook, validator, matrix, runtime, or sync enforcement.
