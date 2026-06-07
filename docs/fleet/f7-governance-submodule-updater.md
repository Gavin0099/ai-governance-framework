# Governed Submodule Update — AI Governance Update to Latest

Legacy tracking code: F-7

## User-Facing Name

The user-facing name for this workflow is:

```text
Update AI Governance to latest
```

In Chinese usage, this corresponds to:

```text
把 AI Governance 更新到最新
```

This user request maps to the governed submodule update workflow, formerly
tracked as F-7.

"F-7" is retained only as a legacy/internal tracking code for historical
references, PLAN entries, and governance traceability.

This workflow optimizes repeatability, reviewability, and scoped governance
updates. It does not guarantee lower token usage than a manual `git pull` for a
single run.

## Intent Resolution

The user-facing request "Update AI Governance to latest" / 「把 AI Governance
更新到最新」 maps to this governed submodule update workflow for repositories
that consume the framework as a Git submodule.

For submodule consumers, the required comparison is:

- governance submodule path;
- nested governance HEAD;
- target upstream framework HEAD;
- dry-run update result.

A valid `already_current` result must be based on the nested governance HEAD
matching the target framework HEAD.

The required report shape is:

```text
AI Governance update check: <already_current | update_available | updated | not_submodule_consumer | not_verified>
governance submodule path: <path | NOT FOUND | NOT CHECKED>
nested governance HEAD: <sha | NOT CHECKED>
target framework HEAD: <sha | NOT CHECKED>
dry-run: PASS | FAIL | NOT RUN
update mode: already_current | fast_forward | detached_target_checkout | NOT CLAIMED
parent repo commit: <hash | NOT NEEDED | NOT CREATED>
```

## Common Misinterpretations

The user-facing request does not mean checking whether local governance
instruction files are unchanged.

Do not claim the governance framework is already current based only on:

- `AGENTS.md` unchanged;
- `AGENTS.base.md` unchanged;
- parent repository `HEAD == origin/main`;
- `git pull --ff-only` reporting already up to date;
- clean parent repository working tree.

Also do not collapse instruction-file sync into framework update status. If the
session updates `AGENTS.md` or another local instruction file without checking
the governance submodule, report that as an instruction-file update and mark the
framework update as `not_verified`.

Invalid conclusion:

```text
AGENTS.md was updated and the parent repo is up to date, so AI Governance is current.
```

Valid partial conclusion:

```text
AGENTS.md was updated, but the AI Governance Framework submodule was not checked.
AI Governance update check: not_verified
governance submodule path: NOT CHECKED
nested governance HEAD: NOT CHECKED
target framework HEAD: NOT CHECKED
dry-run: NOT RUN
update mode: NOT CLAIMED
parent repo commit: NOT CREATED
```

Valid `already_current` conclusion:

```text
AI Governance update check: already_current
governance submodule path: ai-governance-framework
nested governance HEAD: <sha>
target framework HEAD: <same-sha>
dry-run: PASS
update mode: already_current
parent repo commit: NOT NEEDED
```

## Purpose

The governed submodule update workflow provides a deterministic updater for
external repositories that already consume `ai-governance-framework` as a
registered Git submodule.

The intended use is to avoid ambiguous manual handoffs such as:

```text
pull latest ai-governance and apply it to this repo
```

Instead, the agent should run a narrow, auditable submodule pointer update.

## Supported Repositories

This workflow is only for repositories where all of the following are true:

- the consuming repo is a Git worktree;
- the governance framework path is a registered and initialized submodule;
- the nested submodule checkout is clean;
- the consuming repo has no pre-existing staged files;
- the update can be staged as a single submodule gitlink path.

The default submodule path is:

```text
ai-governance-framework
```

For repos using a non-default path, pass `-SubmodulePath`, for example:

```text
.ai-governance-framework
```

## Unsupported Repositories

Do not use this workflow for:

- repos without a registered governance submodule;
- partial scaffold/import copies;
- manual-sync-required repos;
- dirty nested submodule checkouts;
- repos with pre-existing staged files;
- broad fleet updates;
- repo cleanup or dirty-file repair;
- push automation.

For unsupported repos, stop at classification and open a separate scoped slice.

## Dry Run First

Always run dry-run before apply:

```powershell
scripts\update-governance-submodule.ps1 `
  -Repo E:\BackUp\Git_EE\example-repo `
  -SubmodulePath ai-governance-framework `
  -Format json
```

Expected dry-run properties:

- `ok=true`;
- `mode=dry_run`;
- `staged_files=[]`;
- `after_head` remains equal to `before_head`;
- `target_head` is visible for review.

Dry-run does not modify files.

## Apply And Commit

If dry-run is acceptable, apply and commit:

```powershell
scripts\update-governance-submodule.ps1 `
  -Repo E:\BackUp\Git_EE\example-repo `
  -SubmodulePath ai-governance-framework `
  -Apply `
  -Stage `
  -Commit `
  -CommitMessage "chore(governance): update ai governance submodule" `
  -Format json
```

Expected apply properties:

- `ok=true`;
- `mode=apply`;
- `staged_files` contains only the submodule path before commit;
- `committed=true` when `-Commit` is used;
- `commit_hash` is populated when commit succeeds;
- the consuming repo has no staged files after commit.

If the nested submodule already points at `target_head`, apply mode is a no-op:

- `ok=true`;
- `update_mode=already_current`;
- `staged_files=[]`;
- `committed=false`;
- `commit_hash=null`;
- no consuming repo commit is created.

## Non-Fast-Forward Updates

Fast-forward is the default. If the nested submodule cannot fast-forward, this
workflow fails unless detached target checkout is explicitly allowed.

Use this only when the reviewer accepts replacing the nested submodule worktree
HEAD with the fetched target commit:

```powershell
scripts\update-governance-submodule.ps1 `
  -Repo E:\BackUp\Git_EE\example-repo `
  -SubmodulePath .ai-governance-framework `
  -Apply `
  -Stage `
  -Commit `
  -AllowDetachedTargetCheckout `
  -CommitMessage "chore(governance): update ai governance submodule" `
  -Format json
```

Expected explicit checkout properties:

- `update_mode=detached_target_checkout`;
- `fast_forward=false`;
- `after_head` equals `target_head`;
- only the submodule pointer is staged/committed.

Do not use `-AllowDetachedTargetCheckout` as the default path.

## Post-Run Checks

After apply/commit, verify:

```powershell
git -C E:\BackUp\Git_EE\example-repo diff --name-only HEAD~1 HEAD
git -C E:\BackUp\Git_EE\example-repo diff --cached --name-only
git -C E:\BackUp\Git_EE\example-repo\ai-governance-framework rev-parse HEAD
git -C E:\BackUp\Git_EE\example-repo status --branch --short
```

Required result:

- commit-only diff contains only the submodule path;
- staged files are empty after commit;
- nested HEAD equals the updater `target_head`;
- unrelated dirty files, if present, remain unstaged and unclaimed.

## Push Boundary

This workflow does not push by default.

Push only when the user explicitly approves a separate push slice:

```text
DONE = push existing external repo governance submodule pointer commit, without
staging, editing, committing, or cleaning unrelated dirty files.
```

## Troubleshooting

`submodule not registered or not initialized`

: The repo is not a governed submodule update consumer for the requested path.
  Classify it as scaffold/import/manual-sync work instead of forcing the
  workflow.

`consuming repo has pre-existing staged files`

: Stop. Do not mix the governance submodule update with existing staged work.

`nested submodule checkout is dirty`

: Stop. Audit the nested checkout in a separate scoped slice.

`merge --ff-only ... failed`

: Default behavior is correct. Use `-AllowDetachedTargetCheckout` only after
  explicit reviewer/user approval.

Windows output decoding errors

: The updater requests UTF-8 replacement decoding for Git subprocess output. If
  decoding still fails, classify the run as tool-output failure and audit
  post-state before retrying.

## Claim Ceiling

CLAIMED:

- deterministic submodule pointer update for registered submodule consumers;
- dry-run before apply;
- path-limited staging and commit;
- opt-in detached checkout for non-fast-forward targets;
- Windows subprocess output decode hardening;
- focused fixture tests for supported updater behavior.

NOT CLAIMED:

- fleet-wide update;
- automatic push;
- scaffold/import/manual-sync update;
- conversion of non-submodule repos into submodule consumers;
- dirty workspace cleanup;
- nested submodule repair;
- product/runtime correctness in consuming repos;
- semantic correctness of the target framework commit;
- Copilot-specific integration;
- token or credit reduction proven.
