# AUTHORITY Repair Proposal - Governance Document Freshness P0 - 2026-06-25

Status: proposal-only
Scope: docs-only planning artifact
Runtime impact: none in this slice

## Problem

The governance document freshness classification audit identified `governance/AUTHORITY.md` and `governance/PLAN.md` as P0 freshness risks because they are not merely old reference documents. Their authority metadata participates in the `session_start` authority filtering path.

The main risk is a stale or misleading planning authority boundary:

- Root `PLAN.md` is the current planning state for active repo work.
- `governance/PLAN.md` is a governance planning template / meta-document.
- `governance/PLAN.md` is currently classified as canonical and `default_load: always`, which places it in the `session_start` always-tier authority set.

That creates a live allowlist / audit-list ambiguity: an agent or loader can treat a meta-template as current planning authority when the repo root `PLAN.md` should remain the active planning source.

## Current repository truth

The relevant current behavior is:

- `runtime_hooks/core/session_start.py` loads governance authority metadata through `governance_tools.authority_loader`.
- `authority_loader.load_authority_table(governance_dir)` derives authority rows from governance document frontmatter.
- `authority_loader.filter_for_session(...)` includes `default_load: always` documents for all task levels.
- For L1/L2-style sessions, `include_on_demand=True` also admits `default_load: on-demand` documents into the allowed governance file set.
- `session_start` passes `allowed_governance_files` into authority validation / audit surfaces.
- This observed path proves allowlist / gate / audit-list consumption.
- This does not prove full document text injection into the model prompt.

The repair therefore cannot be only a prose edit inside `governance/AUTHORITY.md`. The live classification must be repaired at the document frontmatter level for any file whose `default_load` currently drives `session_start`.

For `governance/PLAN.md`, the currently relevant distinction is:

- Root `PLAN.md`: current planning authority for active repo state.
- `governance/PLAN.md`: planning protocol / meta-template for how planning should be maintained.

## Target outcome

Create a bounded repair plan that:

- corrects stale / misleading `AUTHORITY.md` metadata and human-facing description;
- reclassifies `governance/PLAN.md` away from the `session_start` always tier;
- preserves `governance/PLAN.md` as historical / protocol reference rather than current planning state;
- keeps root `PLAN.md` as the active planning authority;
- defines focused validation for `authority_loader` and `session_start` behavior;
- avoids rewriting adjacent governance doctrine in this slice.

## Scope

The proposed future implementation should be limited to:

- `governance/AUTHORITY.md` header / table / explanatory note cleanup;
- `governance/PLAN.md` authority frontmatter reclassification;
- any required narrow focused tests or smoke checks that prove authority filtering changed as intended.

This proposal itself changes none of those files.

## Non-goals

This proposal does not authorize:

- rewriting `governance/SYSTEM_PROMPT.md`;
- rewriting `governance/AGENT.md`;
- rewriting `governance/HUMAN-OVERSIGHT.md`;
- rewriting `governance/MEMORY_AUTHORITY_CONTRACT.md`;
- changing `governance_tools/**`;
- changing `runtime_hooks/**`;
- changing hook, validator, or enforcement behavior;
- changing prompt injection behavior;
- claiming full governance document freshness repair.

## Affected surfaces

Primary surfaces for a later implementation:

- `governance/AUTHORITY.md`
- `governance/PLAN.md`

Validation / evidence surfaces:

- `governance_tools/authority_loader.py`
- `runtime_hooks/core/session_start.py`
- focused tests covering authority filtering and session-start authority payload validation

Non-target adjacent surfaces:

- `governance/SYSTEM_PROMPT.md`
- `governance/AGENT.md`
- `governance/HUMAN-OVERSIGHT.md`
- `governance/MEMORY_AUTHORITY_CONTRACT.md`
- `governance/rules/**`

## Boundary and API considerations

### AUTHORITY.md header correction strategy

`governance/AUTHORITY.md` should be updated so its header and explanatory text reflect the current model:

- it is an authority registry / documentation surface;
- the live `session_start` filter is driven by per-document governance frontmatter parsed by `authority_loader`;
- `AUTHORITY.md` table rows must not contradict the frontmatter-driven live behavior;
- the update date should reflect the repair commit, not an old historical date.

The implementation must avoid implying that editing the `AUTHORITY.md` table alone changes runtime filtering. If a table row is changed, the corresponding document frontmatter must be changed in the same repair slice or the repair is misleading.

### governance/PLAN.md reclassification strategy

Recommended first repair:

- reclassify `governance/PLAN.md` away from `default_load: always`;
- keep it as a governance planning protocol / meta-template;
- classify it as on-demand reference rather than current planning authority.

Expected semantic target:

```yaml
audience: agent-on-demand
authority: reference
default_load: on-demand
```

This preserves human and agent access for planning-protocol questions while removing it from the L0 always set.

A stricter alternative is `default_load: never`, but that would remove it from the `session_start` allowed set entirely and should require a separate justification. The current observed failure only requires removing it from the always tier, not removing all on-demand access.

### Root PLAN.md versus governance/PLAN.md

The repair should add explicit language distinguishing:

- root `PLAN.md` = current active planning state;
- `governance/PLAN.md` = protocol / template / historical planning guidance.

This distinction should be visible both in `AUTHORITY.md` and inside `governance/PLAN.md` itself so readers do not infer that the meta-template supersedes current root planning state.

## Expected effect on session_start allowed_governance_files

If `governance/PLAN.md` changes from `default_load: always` to `default_load: on-demand`:

- L0 / always-only session filtering should no longer include `governance/PLAN.md` in `allowed_governance_files`.
- L1/L2-style filtering with `include_on_demand=True` may still include `governance/PLAN.md` in `allowed_governance_files`.
- The inclusion, if present for L1/L2, should be interpreted as permission to load / audit the planning protocol, not proof that its full content is injected into the model prompt.
- Root `PLAN.md` remains outside the governance frontmatter table and remains the active planning authority by repo convention.

If a future repair chooses `default_load: never` instead:

- `governance/PLAN.md` should be absent from both L0 and L1/L2 `allowed_governance_files`;
- this stricter behavior should be reviewed as a separate routing decision.

## Claim ceiling

This proposal may claim:

- a proposed repair boundary;
- the intended future classification change;
- the expected authority-filtering effect if frontmatter changes are made;
- a validation plan.

This proposal must not claim:

- `AUTHORITY.md` has been repaired;
- `governance/PLAN.md` has been reclassified;
- `session_start` behavior has changed;
- stale prompt docs have been rewritten;
- full-text prompt injection was proven;
- governance enforcement changed;
- the governance document freshness audit is resolved.

## Failure paths or risk points

1. Table-only repair

Changing only `governance/AUTHORITY.md` without changing `governance/PLAN.md` frontmatter would leave `session_start` behavior unchanged while making human-facing documentation look repaired.

2. Frontmatter-only repair

Changing only `governance/PLAN.md` frontmatter without updating `AUTHORITY.md` would change live filtering while leaving the registry stale.

3. Over-broad freshness cleanup

Bundling SYSTEM_PROMPT, AGENT, HUMAN-OVERSIGHT, MEMORY_AUTHORITY_CONTRACT, and rules-cluster rewrites into this P0 repair would expand scope beyond the observed failure and increase review cost.

4. Injection overclaim

The observed path supports allowlist / gate / audit-list claims. It does not support claiming that these documents are always injected as full prompt text.

5. L1/L2 surprise

Moving `governance/PLAN.md` from `always` to `on-demand` removes it from L0 always filtering but may still include it in L1/L2 allowed sets. Reviewers must not mistake that for a failed repair if the intended repair is specifically "away from always tier."

## Evidence plan

For the future implementation commit, run focused checks that prove both documentation and live filtering changed as intended:

1. Authority metadata inspection

Verify `governance/PLAN.md` frontmatter no longer declares `default_load: always`.

2. Authority loader focused check

Run a focused authority-loader check showing:

- L0 / always-only output excludes `governance/PLAN.md`;
- L1/L2 output behavior matches the chosen classification (`on-demand` includes it; `never` excludes it).

3. Session-start focused check

Run the existing focused session-start / authority payload validation path and confirm:

- `allowed_governance_files` reflects the new `governance/PLAN.md` classification;
- authority validation still passes;
- no unrelated governance files are dropped.

4. Registry consistency check

Verify `governance/AUTHORITY.md` no longer contradicts `governance/PLAN.md` frontmatter and clearly states the root `PLAN.md` distinction.

5. Diff-scope check

Confirm the implementation touches only the approved docs and any focused tests required by the repair.

## Implementation tranche recommendation

Recommended next tranche:

1. Edit `governance/PLAN.md` frontmatter and short description to mark it as on-demand reference / planning protocol.
2. Edit `governance/AUTHORITY.md` header and table row to match the new classification and distinguish root `PLAN.md` as current planning authority.
3. Run focused authority-loader and session-start checks.
4. Record canonical memory bound to the implementation commit.

Do not include SYSTEM_PROMPT, AGENT, HUMAN-OVERSIGHT, MEMORY_AUTHORITY_CONTRACT, runtime hooks, validators, or enforcement changes in that tranche.
