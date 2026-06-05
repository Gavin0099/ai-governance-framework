# Fleet Submodule Advisory Report

## Purpose

This advisory describes how to use the Phase F-1 read-only helper before asking
an agent to pull, copy, or re-apply the latest `ai-governance-framework` into
other repositories.

The goal is to reduce repeated state reconstruction and token-heavy manual
handoffs by answering one narrow question first:

```text
Which fleet repositories are already submodule-based, and which are not?
```

For the Phase F-7 updater contract that applies after a repo is confirmed
`submodule_based`, see:

```text
docs/fleet/f7-governance-submodule-updater.md
```

## Command

Create a local overlay from the example:

```powershell
Copy-Item governance/fleet/governance_scope.local.example.yaml governance/fleet/governance_scope.local.yaml
```

Edit the local paths for this machine, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_governance_submodules.ps1 -VerifyModelOnly
```

By default, the helper checks only `required` fleet repos.

Optional tier expansion:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_governance_submodules.ps1 -VerifyModelOnly -IncludeRecommended
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_governance_submodules.ps1 -VerifyModelOnly -IncludeRecommended -IncludeExempt
```

## Output Meaning

The report prints:

```text
Repo, Tier, Model, Dirty, Path, Note
```

`Model` values:

- `submodule_based`: the repo has a registered `ai-governance-framework` submodule.
- `not_submodule_based`: the governance path exists but is not registered as a submodule.
- `missing_governance_path`: the repo exists but does not contain the expected governance path.
- `missing_local_path`: the local overlay has no path for this repo.
- `missing_repo`: the local overlay path does not exist.
- `not_git_repo`: the local path is not a Git worktree.
- `git_check_failed`: read-only Git inspection failed, for example due to `safe.directory`.

`Dirty` is advisory only. A dirty repo is not modified or cleaned by this helper.

## Recommended Agent Handoff

Use this helper before issuing broad prompts such as:

```text
pull latest ai-governance and apply it to this repo
```

Preferred handoff:

```text
First run the fleet submodule advisory check.
Do not update external repos yet.
Summarize which repos are submodule_based, not_submodule_based, missing_governance_path,
missing_local_path, missing_repo, not_git_repo, or git_check_failed.
Then propose the next narrow update slice.
```

This keeps the first round as state inventory instead of implementation.

## Claim Ceiling

CLAIMED:

- read-only fleet submodule model inventory guidance;
- advisory usage before cross-repo governance update prompts;
- interpretation of current F-1 helper output states.

NOT CLAIMED:

- external repo update;
- automatic pull or sync;
- submodule migration completion;
- hook, pre-push, or runtime enforcement;
- matrix integration;
- token or credit reduction proven;
- correctness of local overlay paths;
- correctness of Git `safe.directory` configuration.

## Boundary

This advisory does not replace repo-specific review. It only prevents a broad
update prompt from starting before the current fleet model is visible.
