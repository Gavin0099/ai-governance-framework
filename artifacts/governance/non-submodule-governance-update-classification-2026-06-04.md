# Non-Submodule Governance Update Classification - 2026-06-04

## Scope

Read-only classification of repos that did not pass the default F-7
`ai-governance-framework` submodule updater path.

DONE boundary:

```text
classify non-submodule repos into scaffold-import update candidates vs manual-sync-required, without modifying external repos.
```

No external repo files were modified, staged, committed, pushed, cleaned,
deleted, or rewritten.

## Evidence Commands

Read-only commands used:

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/update-governance-submodule.ps1 -Repo <repo> -Format json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/update-governance-submodule.ps1 -Repo E:\BackUp\Git_EE\Bookstore-Scraper -SubmodulePath .ai-governance-framework -Format json
python -m governance_tools.external_repo_version_audit --repo <repo> --format json
git -C <repo> status --short
git -C <repo> status --short -- ai-governance-framework .gitmodules
git -C <repo> submodule status -- <path>
```

## Classification Summary

| repo | observed model | classification | rationale | next action |
| --- | --- | --- | --- | --- |
| `Bookstore-Scraper` | non-default submodule path `.ai-governance-framework` | `f7_submodule_candidate_non_default_path` | default F-7 failed because path is not `ai-governance-framework`, but dry-run with `-SubmodulePath .ai-governance-framework` passed | use F-7 with explicit `-SubmodulePath .ai-governance-framework` |
| `cli` | repo-local scaffold / non-governance submodule present | `manual_sync_required` | no registered `ai-governance-framework` submodule; existing `.gitmodules` points to `SubModule/IspEngine_Lib`; governance files are untracked/dirty enough that scaffold refresh would mix adoption state with dirty work | audit/commit or exclude existing governance scaffold state before any deterministic scaffold updater |
| `financial-pdf-reader` | unregistered nested `ai-governance-framework` path + partial scaffold | `manual_sync_required` | `ai-governance-framework` is a nested git checkout but not a registered submodule; framework lock, baseline, and contract are missing; nested checkout is dirty | decide whether to convert to submodule or run a fresh scaffold import in a separate scoped slice |
| `Enumd` | registered submodule path, but blocked | `not_non_submodule_blocked_by_staged_scope` | `ai-governance-framework` is registered, but pre-existing staged files caused F-7 to refuse scope mixing | clear/review staged files before rerunning F-7 |

## Bookstore-Scraper

Default F-7 result:

```text
submodule not registered or not initialized: ai-governance-framework
```

Actual `.gitmodules` entry:

```text
[submodule ".ai-governance-framework"]
    path = .ai-governance-framework
    url = https://github.com/Gavin0099/ai-governance-framework
```

F-7 dry-run with explicit submodule path:

```text
ok=True
submodule_path=.ai-governance-framework
before_head=8efaa7ea506541c24d0b766893f5ff6acf030ae0
target_head=208643e749e9f5348bcf7f69e261cca0d00fb0b9
after_head=8efaa7ea506541c24d0b766893f5ff6acf030ae0
staged_files=[]
```

Disposition:

```text
f7_submodule_candidate_non_default_path
```

This repo should not be treated as scaffold-import/manual-sync just because the
default path failed. It needs the existing F-7 updater with an explicit
`-SubmodulePath .ai-governance-framework` argument.

## cli

Observed files:

```text
AGENTS.md
AGENTS.base.md
contract.yaml
PLAN.md
governance/framework.lock.json
.governance/baseline.yaml
.gitmodules
```

`.gitmodules` points to a product submodule:

```text
[submodule "SubModule/IspEngine_Lib"]
    path = SubModule/IspEngine_Lib
    url = ../ispengine_lib.git
```

Dirty-state indicators include:

```text
M  SubModule/IspEngine_Lib
?? .github/
?? .governance/
?? AGENTS.base.md
?? AGENTS.md
?? PLAN.md
?? contract.yaml
?? governance/
?? memory/
```

Version audit reports `framework_version.state=current`, but the working tree
contains untracked governance scaffold paths. That makes a deterministic
scaffold refresh unsafe without a prior dirty-state decision.

Disposition:

```text
manual_sync_required
```

Reason:

- not an `ai-governance-framework` submodule consumer;
- scaffold state appears present but not cleanly committed;
- existing product submodule dirty state is unrelated;
- deterministic scaffold update could accidentally normalize or overwrite
  uncommitted governance adoption state.

## financial-pdf-reader

Observed files:

```text
AGENTS.md
PLAN.md
ai-governance-framework
```

The `ai-governance-framework` path is a nested git checkout:

```text
77c63281eb200c85266d0150ef23eb2df3685d83
```

Nested checkout dirty state:

```text
M .governance-state.yaml
M artifacts/governance/version_compatibility.json
```

Readiness/version audit reports:

- no `contract.yaml` resolved;
- `.governance/baseline.yaml` missing;
- `governance/framework.lock.json` missing;
- AGENTS calibration is scaffold-only;
- PLAN is severely stale.

Disposition:

```text
manual_sync_required
```

Reason:

- not a registered submodule;
- partial scaffold state;
- missing framework lock/baseline/contract;
- dirty nested framework checkout.

This repo needs an explicit decision:

- convert the nested checkout into a real submodule; or
- remove/ignore the nested checkout and run a fresh scoped scaffold import.

Either path modifies repo structure and is outside this read-only classification.

## Enumd Boundary

Enumd is not a non-submodule repo for this classification.

Observed:

```text
M ai-governance-framework
+8139b1fa74a239371c688b878dfa1e31770d8bb4 ai-governance-framework (heads/main)
```

F-7 refusal reason:

```text
consuming repo has pre-existing staged files; refusing to mix scopes
```

Disposition:

```text
not_non_submodule_blocked_by_staged_scope
```

It should be handled by a staged-file audit before rerunning F-7, not by a
scaffold-import updater.

## Final Classification

| class | repos |
| --- | --- |
| `f7_submodule_candidate_non_default_path` | `Bookstore-Scraper` |
| `manual_sync_required` | `cli`, `financial-pdf-reader` |
| `not_non_submodule_blocked_by_staged_scope` | `Enumd` |

No repo in this sample is currently a clean `scaffold_import_update_candidate`.

## Claim Ceiling

CLAIMED:

- read-only classification of non-default/non-F-7-default update paths;
- Bookstore-Scraper should use F-7 with explicit submodule path;
- cli and financial-pdf-reader require manual sync decisions before any
  deterministic scaffold updater;
- Enumd is submodule-based but blocked by staged scope.

NOT CLAIMED:

- external repo modifications;
- scaffold updater implementation;
- scaffold import readiness;
- submodule conversion readiness;
- external repo validation/build/test status;
- dirty-state safety;
- semantic correctness;
- Copilot token reduction measured.

## Recommended Next Slice

The next implementation slice should not be a generic scaffold updater yet.

Safer next slice:

```text
DONE = run F-7 updater dry-run on Bookstore-Scraper with -SubmodulePath .ai-governance-framework, then apply/commit only that submodule pointer if dry-run remains clean.
```

For `cli` and `financial-pdf-reader`, open separate dirty/import audits before
any scaffold update.
