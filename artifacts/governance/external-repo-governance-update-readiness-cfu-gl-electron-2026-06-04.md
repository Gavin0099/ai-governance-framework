# External Repo Governance Update Readiness - CFU and gl_electron_tool - 2026-06-04

## Scope

Read-only submodule/update readiness inventory for:

- `E:/BackUp/Git_EE/CFU`
- `E:/BackUp/Git_EE/gl_electron_tool`

DONE boundary:

```text
run read-only submodule/update readiness inventory for CFU and gl_electron_tool, classify whether each repo can receive latest ai-governance via submodule update, scaffold apply, or manual scoped sync, without modifying external repos.
```

No external repository files were modified, staged, committed, pushed, or
rewritten for this inventory.

## Framework Baseline

Current framework HEAD in this repository:

```text
7f816a467e28772db4bf831705b3ec9ee29dd81e
```

## Read-Only Commands

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_governance_submodules.ps1 -VerifyModelOnly -LocalScopeFile governance/fleet/governance_scope.local.yaml
git -C E:/BackUp/Git_EE/CFU submodule status -- ai-governance-framework
git -C E:/BackUp/Git_EE/gl_electron_tool submodule status -- ai-governance-framework
git -C E:/BackUp/Git_EE/CFU/ai-governance-framework rev-parse HEAD
git -C E:/BackUp/Git_EE/gl_electron_tool/ai-governance-framework rev-parse HEAD
git -C E:/BackUp/Git_EE/CFU status --short
git -C E:/BackUp/Git_EE/gl_electron_tool status --short
git -C E:/BackUp/Git_EE/CFU/ai-governance-framework status --short
```

## Classification Summary

| repo | model | pinned framework commit | latest framework commit | dirty state | recommended update mode | readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `CFU` | `submodule_based` | `ccbb85aff62904768af6bd43c23a7d1c7d056d29` | `7f816a467e28772db4bf831705b3ec9ee29dd81e` | dirty outer repo; nested framework marker modified | `submodule_update_after_dirty_audit` | not ready for immediate update |
| `gl_electron_tool` | `submodule_based` | `70a54b3056c7662d0a2a6ed6fd69a7bf5d37abfd` | `7f816a467e28772db4bf831705b3ec9ee29dd81e` | dirty outer repo | `submodule_update_after_dirty_audit` | not ready for immediate update |

## Per-Repo Findings

### CFU

Read-only model:

```text
Model = submodule_based
Dirty = True
Path = E:/BackUp/Git_EE/CFU
```

Submodule status:

```text
ccbb85aff62904768af6bd43c23a7d1c7d056d29 ai-governance-framework (heads/main)
```

Interpretation:

- CFU already consumes `ai-governance-framework` as a registered submodule.
- The pinned framework commit is behind current framework HEAD.
- The correct update path is submodule pointer update, not scaffold apply and
  not manual scoped sync.
- CFU is not ready for immediate update because the outer repo is dirty and
  `ai-governance-framework` appears as a modified submodule entry in
  `git status --short`.
- A future update slice must first audit CFU dirty state and decide whether the
  submodule pointer update can be isolated from unrelated product changes.

Recommended next action for CFU:

```text
CFU scoped dirty audit before submodule pointer update
```

Do not run scaffold apply by default. CFU is already submodule-based, and
scaffold apply could mix governance scaffold refresh with product dirty state.

### gl_electron_tool

Read-only model:

```text
Model = submodule_based
Dirty = True
Path = E:/BackUp/Git_EE/gl_electron_tool
```

Submodule status:

```text
70a54b3056c7662d0a2a6ed6fd69a7bf5d37abfd ai-governance-framework (heads/main)
```

Interpretation:

- gl_electron_tool already consumes `ai-governance-framework` as a registered
  submodule.
- The pinned framework commit is behind current framework HEAD.
- The correct update path is submodule pointer update, not scaffold apply and
  not manual scoped sync.
- gl_electron_tool is not ready for immediate update because the outer repo is
  dirty.
- A future update slice should isolate the submodule pointer update from the
  existing dirty runtime/product artifacts.

Recommended next action for gl_electron_tool:

```text
gl_electron_tool scoped dirty audit before submodule pointer update
```

## Mode Decision

| update mode | CFU | gl_electron_tool | rationale |
| --- | --- | --- | --- |
| `submodule update` | candidate after dirty audit | candidate after dirty audit | both repos are already `submodule_based` |
| `scaffold apply` | not preferred | not preferred | would duplicate or mix with existing submodule model |
| `manual scoped sync` | not preferred | not preferred | no evidence that submodule model is unavailable |

## Claim Ceiling

CLAIMED:

- read-only update-readiness classification for CFU and gl_electron_tool;
- both repos are submodule-based consumers of `ai-governance-framework`;
- both repos are behind current framework HEAD;
- both should use submodule update after dirty-state audit;
- no external repo modification was performed.

NOT CLAIMED:

- CFU updated to latest framework;
- gl_electron_tool updated to latest framework;
- external repo dirty state is safe;
- submodule pointer update committed;
- scaffold apply readiness;
- manual sync correctness;
- external repo validation;
- external repo build/test status;
- hook/runtime enforcement;
- semantic correctness.

## Recommended Next Slice

If continuing this line, use one repo at a time:

```text
DONE = audit gl_electron_tool dirty state for a scoped ai-governance submodule pointer update, without modifying files.
```

Then, only after that audit:

```text
DONE = update gl_electron_tool ai-governance-framework submodule pointer to current framework HEAD and commit only the submodule pointer change, if dirty-state audit confirms it can be isolated.
```

CFU should be handled separately because its dirty state is much larger and
includes extensive product and generated artifacts.
