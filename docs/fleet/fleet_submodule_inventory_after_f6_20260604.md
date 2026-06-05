# Fleet Submodule Inventory After F-6 - 2026-06-04

## Scope

Phase F-6 helper robustness fix validation.

The helper was updated to avoid treating non-fatal Git stderr warnings as hard
read-check failures. It now:

- captures native Git stderr without triggering the outer catch path;
- treats `rev-parse --is-inside-work-tree` as successful when output contains a
  line equal to `true`;
- keeps `dubious_ownership` failures blocked.

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& scripts\sync_governance_submodules.ps1 -VerifyModelOnly -LocalScopeFile governance\fleet\governance_scope.local.yaml | Out-String -Width 520"
```

Input overlay:

```text
governance/fleet/governance_scope.local.yaml
```

Overlay status:

```text
ignored local-only file; not committed
```

## Result Summary

Observed required-tier rows: 10

- `submodule_based`: 0
- `not_submodule_based`: 3
- `missing_governance_path`: 2
- `missing_local_path`: 0
- `missing_repo`: 0
- `not_git_repo`: 0
- `git_check_failed`: 5

## Rows

| Repo | Tier | Model | Dirty | Path | Note |
| --- | --- | --- | --- | --- | --- |
| hp-firmware-stresstest-tool | required | not_submodule_based | True | E:/BackUp/Git_EE/hp-firmware-stresstest-tool | governance path exists but is not a registered submodule |
| cli | required | missing_governance_path | True | E:/BackUp/Git_EE/cli | path missing: ai-governance-framework |
| CFU | required | not_submodule_based | True | E:/BackUp/Git_EE/CFU | governance path exists but is not a registered submodule |
| IsptoolRefine2018_EndUser_Tool | required | git_check_failed | - | E:/BackUp/IsptoolRefine2018_EndUser_Tool | dubious ownership blocks read-only Git inspection |
| lenoveo-isp-tool-avalonia | required | git_check_failed | - | E:/BackUp/Git_EE/lenoveo-isp-tool-avalonia | dubious ownership blocks read-only Git inspection |
| gl_electron_tool | required | not_submodule_based | True | E:/BackUp/Git_EE/gl_electron_tool | governance path exists but is not a registered submodule |
| Command_Line_Tool | required | git_check_failed | - | E:/BackUp/Git_EE/Command_Line_Tool | dubious ownership blocks read-only Git inspection |
| General_End_User_Tool | required | git_check_failed | - | E:/BackUp/Git_EE/General_End_User_Tool | dubious ownership blocks read-only Git inspection |
| ai-governance-framework | required | missing_governance_path | True | E:/BackUp/Git_EE/ai-governance-framework | path missing: ai-governance-framework |
| Kernel-Driver-Contract | required | git_check_failed | - | E:/BackUp/Git_EE/Kernel-Driver-Contract | dubious ownership blocks read-only Git inspection |

## Interpretation

The F-6 helper robustness fix worked for the non-fatal warning class.

Before F-6:

```text
git_check_failed: 10
```

After F-6:

```text
git_check_failed: 5
not_submodule_based: 3
missing_governance_path: 2
```

The remaining `git_check_failed` rows are the expected `dubious_ownership`
blockers. F-6 does not repair them.

## Claim Ceiling

CLAIMED:

- helper robustness improved for non-fatal Git warning handling;
- five rows now advance past Git worktree detection;
- five dubious-ownership rows remain blocked.

NOT CLAIMED:

- Git access fully repaired;
- `safe.directory` configured;
- external repos modified;
- submodule migration completed;
- external repo correctness;
- update or sync readiness;
- hook, validator, matrix, runtime, or sync enforcement.
