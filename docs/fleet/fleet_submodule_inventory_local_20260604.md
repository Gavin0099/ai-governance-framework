# Fleet Submodule Inventory Local Overlay Trial - 2026-06-04

## Scope

Phase F-4 read-only local overlay completeness trial.

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& scripts\sync_governance_submodules.ps1 -VerifyModelOnly -LocalScopeFile governance\fleet\governance_scope.local.yaml | Out-String -Width 300"
```

Input overlay:

```text
governance/fleet/governance_scope.local.yaml
```

Overlay status:

```text
ignored local-only file; not committed
```

Tier scope:

```text
required only
```

## Result Summary

Observed required-tier rows: 10

- `submodule_based`: 0
- `not_submodule_based`: 0
- `missing_governance_path`: 0
- `missing_local_path`: 0
- `missing_repo`: 0
- `not_git_repo`: 0
- `git_check_failed`: 10

## Rows

| Repo | Tier | Model | Dirty | Path | Note |
| --- | --- | --- | --- | --- | --- |
| hp-firmware-stresstest-tool | required | git_check_failed | - | E:/BackUp/Git_EE/hp-firmware-stresstest-tool | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| cli | required | git_check_failed | - | E:/BackUp/Git_EE/cli | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| CFU | required | git_check_failed | - | E:/BackUp/Git_EE/CFU | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| IsptoolRefine2018_EndUser_Tool | required | git_check_failed | - | E:/BackUp/IsptoolRefine2018_EndUser_Tool | fatal: detected dubious ownership in repository |
| lenoveo-isp-tool-avalonia | required | git_check_failed | - | E:/BackUp/Git_EE/lenoveo-isp-tool-avalonia | fatal: detected dubious ownership in repository |
| gl_electron_tool | required | git_check_failed | - | E:/BackUp/Git_EE/gl_electron_tool | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| Command_Line_Tool | required | git_check_failed | - | E:/BackUp/Git_EE/Command_Line_Tool | fatal: detected dubious ownership in repository |
| General_End_User_Tool | required | git_check_failed | - | E:/BackUp/Git_EE/General_End_User_Tool | fatal: detected dubious ownership in repository |
| ai-governance-framework | required | git_check_failed | - | E:/BackUp/Git_EE/ai-governance-framework | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| Kernel-Driver-Contract | required | git_check_failed | - | E:/BackUp/Git_EE/Kernel-Driver-Contract | fatal: detected dubious ownership in repository |

## Interpretation

The local overlay completeness blocker is resolved for this machine's required
tier paths. The remaining blocker is read-only Git inspection access.

This trial does not establish whether any repo is submodule-based. The helper
could not reach submodule detection because each required-tier row failed at
Git worktree inspection.

## Claim Ceiling

CLAIMED:

- local-only overlay completeness for the 10 required-tier repo path entries;
- single-run observation that every required-tier row is blocked by
  `git_check_failed`;
- no missing local paths remain in this run.

NOT CLAIMED:

- fleet submodule migration state;
- external repo correctness;
- external repo update readiness;
- Git `safe.directory` correctness;
- permission repair;
- token or credit reduction;
- hook, validator, matrix, runtime, or sync enforcement.
