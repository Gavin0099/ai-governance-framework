# Fleet Submodule Inventory - 2026-06-04

## Scope

Phase F-3 read-only inventory run using the Phase F-1 helper.

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& scripts\sync_governance_submodules.ps1 -VerifyModelOnly -LocalScopeFile governance\fleet\governance_scope.local.example.yaml | Out-String -Width 260"
```

Input overlay:

```text
governance/fleet/governance_scope.local.example.yaml
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
- `missing_local_path`: 7
- `missing_repo`: 0
- `not_git_repo`: 0
- `git_check_failed`: 3

## Rows

| Repo | Tier | Model | Dirty | Path | Note |
| --- | --- | --- | --- | --- | --- |
| hp-firmware-stresstest-tool | required | git_check_failed | - | E:/BackUp/Git_EE/hp-firmware-stresstest-tool | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| cli | required | git_check_failed | - | E:/BackUp/Git_EE/cli | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| CFU | required | git_check_failed | - | E:/BackUp/Git_EE/CFU | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| IsptoolRefine2018_EndUser_Tool | required | missing_local_path | - |  | no local overlay entry |
| lenoveo-isp-tool-avalonia | required | missing_local_path | - |  | no local overlay entry |
| gl_electron_tool | required | git_check_failed | - | E:/BackUp/Git_EE/gl_electron_tool | warning: unable to access `C:\Users\reiko/.config/git/ignore`: Permission denied |
| Command_Line_Tool | required | missing_local_path | - |  | no local overlay entry |
| General_End_User_Tool | required | missing_local_path | - |  | no local overlay entry |
| ai-governance-framework | required | missing_local_path | - |  | no local overlay entry |
| Kernel-Driver-Contract | required | missing_local_path | - |  | no local overlay entry |

## Interpretation

This run does not establish submodule adoption. It establishes only that the
current example overlay is insufficient for a complete required-tier inventory.

The immediate blocker for a useful F-3 inventory is local overlay completeness
and read-only Git inspection access.

## Claim Ceiling

CLAIMED:

- read-only required-tier inventory artifact from the current example overlay;
- aggregate model counts for this single run;
- observed blockers: missing local overlay entries and Git read-check failures.

NOT CLAIMED:

- fleet submodule migration state;
- external repo correctness;
- external repo update readiness;
- token or credit reduction;
- Git `safe.directory` correctness;
- local overlay completeness;
- hook, validator, matrix, runtime, or sync enforcement.
