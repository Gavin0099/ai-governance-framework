# Long-Term Memory

## Identity And Account Mapping
<!-- memory_type: structural_long_term -->
<!-- promotion_status: authoritative -->
<!-- proposed_by: ai / 2026-04-30 -->
<!-- promoted_by: Gavin / 2026-07-08 (owner-authorized; verified this session against git config user.name=GavinWu, user.email=Gavin.Wu@genesyslogic.com.tw, origin=github/Gavin0099, gitlab=GavinWu) -->
- GitHub upload account: `Gavin0099`
- GitLab upload account: `GavinWu`
- git config user.email for GitLab pushes: `Gavin.Wu@genesyslogic.com.tw`

## Conventions
<!-- memory_type: structural_long_term -->
<!-- promotion_status: authoritative -->
<!-- promoted_by: Gavin / 2026-04-30 -->
<!-- promoted_at: 2026-04-30 -->
<!-- source_anchor: AGENTS.md -->
- Long-term memory must live in `memory/00_long_term.md` (not repo-root `MEMORY.md`).
- In main sessions, after every push, write a short daily memory entry with `what changed`, `commit`, `tests`, and `next step`.
- External/private tool memory (for example `C:\Users\reiko\.claude\projects\...\memory\MEMORY.md`) is not cross-agent governance authority; canonical cross-agent memory must be copied into repo `memory/`.

## Workflow Preferences
<!-- memory_type: structural_long_term -->
<!-- promotion_status: candidate -->
<!-- proposed_by: ai / 2026-04-30 -->
<!-- human_review_needed: confirm strict loop and dual-push policy still apply -->
- User requires a strict loop: after each completed change, update the corresponding `memory/YYYY-MM-DD.md` entry and push.
- User requires every completed change to be pushed to both `gitlab` and `origin` (GitHub), with author identity intentionally separated per remote.
- User requires every completed slice report to include an explicit next-step prompt or recommendation after the done/validation/push summary.
- User prefers explanations and status reports in Chinese by default; preserve fixed governance field names, command names, and machine tokens in their original language, with Chinese explanation when helpful.
- Enforced operating rule (2026-05-12): every completed change must include:
  1) memory update in `memory/YYYY-MM-DD.md`
  2) commit
  3) push to `origin`
  4) push to `gitlab`

## Governance State (cross-agent readable facts)
<!-- memory_type: structural_long_term -->
<!-- promotion_status: candidate -->
<!-- proposed_by: ai / 2026-04-30 -->
<!-- source_anchor: artifact:artifacts/governance/phase-d-reviewer-closeout.json; PLAN.md phase checklist -->
<!-- partial_review 2026-07-08: phase table + version re-verified against PLAN.md (E=in_progress per `[>]`, v1.2.0 current); learning-loop implementation paused pending owner unpause. Runtime capability boundary section NOT re-verified this pass. -->
<!-- human_review_needed: verify runtime capability boundary (F4 immutability hash, F16/F17 exception authority path) is current -->

> This section is the authoritative in-repo governance state for agents that cannot
> access Claude Code's private project memory (C:\Users\reiko\.claude\projects\...\memory\MEMORY.md).
> Update this section whenever phase state or version changes.

### Framework Version
- Current release: **v1.2.0** (Phase D governance baseline freeze + runtime structural enforcement v0.1)
- Badge source: `README.md`; release notes: `CHANGELOG.md`

### Phase Status (as of 2026-04-28; phase-level re-verified 2026-07-08 vs PLAN.md)
| Phase | Status | Notes |
|-------|--------|-------|
| A | completed | governance core baseline |
| B | completed | adoption / validator / freshness / memory |
| C | completed | runtime governance, DBL, observation surfaces |
| D | **completed** | reviewer closeout signed 2026-04-28T11:59:44Z by Gavin0099 |
| E | in_progress | failure decision boundary, exclusion governance, usage enforcement; validity-before-expansion posture, learning-loop implementation paused pending owner unpause (PLAN.md) |

### Phase D Closeout Artifact
- Canonical path: `artifacts/governance/phase-d-reviewer-closeout.json`
- Reviewer: `Gavin0099`
- Confirmed at: `2026-04-28T11:59:44Z`
- Status: `ok=True`, `failures=[]`, `missing_required_conditions=[]`
- Authority contract: `governance/PHASE_D_CLOSE_AUTHORITY.md`

### Phase D Required Conditions (exact tokens — F10/F11 enforcement)
The following 5 strings must appear verbatim in `confirmed_conditions` for
`assess_phase_d_closeout()` to return `ok=True`:
```
reviewer_independent_of_author
phase_c_surface_gap_resolved
validator_output_reviewed
fail_closed_semantics_accepted
no_unresolved_blocking_conditions
```
Source: `governance_tools/phase_d_closeout_writer.py::REQUIRED_CONDITIONS`

### Runtime Capability Boundary (v1.2.0)
- **Runtime-enforced (F1–F11)**: artifact presence, schema, writer identity, reviewer_id,
  confirmed_conditions presence, confirmed_at, verdict, required condition coverage (5 tokens),
  VRB-3 exception path explicitly `unsupported`
- **Reviewer-attested only (F12–F15)**: self-review prohibition, proxy review (RI-2),
  wrong scope (RI-4), retroactive signing — runtime cannot machine-verify
- **Not yet implemented**: F4 immutability hash, F16/F17 exception authority artifact path

## CodeBurn Phase 1 Status (2026-04-30)
<!-- memory_type: structural_long_term -->
<!-- promotion_status: authoritative -->
<!-- proposed_by: ai / 2026-04-30 -->
<!-- promoted_by: Gavin / 2026-07-08 (owner-authorized; corroborated by Phase 1 CLOSED forensic record + cross-agent memory) -->
<!-- source_anchor: codeburn/README.md:3,99; memory/2026-04-30.md:81-83; commit:1398417 -->

> Cross-agent readable. See `codeburn/README.md` for full navigation.

- **Phase 1: CLOSED** — 9 milestones (M1–M9) all passed runtime smoke
- Entry page: `codeburn/phase1/CODEBURN_PHASE1_STATUS.md`
- Governance contract: `codeburn/phase1/CODEBURN_PHASE1_ANALYSIS_CONTRACT.md` (v1.0.0)
- Phase 2 limits: `codeburn/phase1/CODEBURN_PHASE2_ENTRY_CONSTRAINTS.md`

**Permanent invariants (must not change without CODEBURN_DECISION_AUTHORITY_CONTRACT.md):**
- `analysis_safe_for_decision: false` — all JSON output
- `decision_usage_allowed: false` — all JSON output

**Phase 2 entry criteria (P1–P4 all required):**
- P1: 7 pytest test files pass in clean environment
- P2: forbidden phrase scanner excludes user metadata fields
- P3: all extensions follow §7 amendment process
- P4: `validate_phase1_data.py --include-analysis` is CI gate

**Known limitation L1:** phrase scanner includes user task name → false positive if task contains forbidden word.

---

## Claim Discipline Guardrail
<!-- memory_type: structural_long_term -->
<!-- promotion_status: authoritative -->
<!-- promoted_by: Gavin / 2026-04-30 -->
<!-- promoted_at: 2026-04-30 -->
<!-- source_anchor: docs/CLAIM_BOUNDARY.md -->
- Canonical short-form claim constitution is `docs/CLAIM_BOUNDARY.md`.
- Non-negotiable rule: if wording is ambiguous, downgrade claim instead of upgrading certainty.
- Prevent semantic drift from `bounded_support` toward `governance proven`.

---

## Gate C Observation Governance Rules (2026-05-12)
<!-- memory_type: structural_long_term -->
<!-- promotion_status: candidate -->
<!-- proposed_by: ai / 2026-05-12 -->
<!-- source_anchor: enumd/docs/status/gate-c-cross-window-trend-2026-05-12.md -->
<!-- human_review_needed: confirm these rules should be promoted to authoritative -->

- Date governance rule:
  - `window_id` must match execution date (UTC).
  - If same-day reuse is required, use `-rN` suffix (for example `...-r2`) instead of future-date labels.
- Evidence source classification must be explicit in Gate C logs:
  - `live-only`: live_row_ratio == 1.00
  - `live-covered`: 0.70 <= live_row_ratio < 1.00
  - `observational-only (non-live)`: live_row_ratio < 0.70
- Legacy rows missing `agent_source` are treated as `proxy` for backward compatibility.
- Guardrail for using `cross-agent validated (execution governance scope)`:
  - allowed only when all are true:
    - cross_lane_decision == pass
    - live_row_ratio == 1.00
    - consecutive live-only pass windows >= N
  - current operational N baseline: 2 (observed continuity reached and extended to N=3 in r4/r5/r6 sequence).
- Outcome-layer interpretation boundary:
  - track only `avg_review_minutes`, `reopen_revert_rate`, `stability_degraded_rate` across windows
  - keep conclusion observational-only
  - do not claim quality/reasoning uplift from these trend signals alone

---

## Fleet Onboarding Design Patterns (observed 2026-05-25 to 2026-05-26)
<!-- memory_type: design_lesson -->
<!-- promotion_status: n/a (design lesson, not a promotable invariant; excluded from promotion queue) -->
<!-- proposed_by: Gavin / 2026-05-26 -->
<!-- source_anchor: governance/fleet/scope_normalized_trend.jsonl; docs/fleet/ -->
<!-- human_review_needed: no — recorded by human directly -->

Observed during 0/10 → 9/10 fleet onboarding. Use as lens when making v2 decisions.

### Pattern 1: Analysis output speed exceeds implementation absorption speed

Multiple complete architectural proposals were produced during the onboarding
(six-layer change plan, four-state evidence model, hardware evidence tier, v2
contract). Most were rejected or deferred. Final progress (3/10 → 9/10) was
achieved primarily through repetitive mechanical fixes (hooks + lock + closeout
+ dirty_explained), not architectural innovation.

Design implication: framework evolution should start from minimum viable change,
not from complete architecture. "Draft full architecture then reduce" is the
observed pattern; it is not the efficient pattern.

### Pattern 2: Tracking mechanisms are the first thing dropped under acceleration

trend.jsonl stopped at 3/10 exactly when onboarding pace accelerated. Checkpoint
docs only started at 6/10. The governance framework enforced fail-closed rules
for consuming repos but had no enforcement — not even advisory — for its own
tracking process.

Design implication: any tracking step that is manual and not on the critical path
will be skipped when velocity increases. This is the same failure mode as
`--no-verify` bypassing hooks. PS1 automation for trend.jsonl auto-append is
the fix; broader lesson: governance designed for others must be tested against
your own actual behavior under pressure.

### Pattern 3: Highest-value discoveries came from collisions, not planning

- gate_blocked evidence consumed: found when running CFU (unplanned)
- agents=scaffold as dominant blocker: visible only after dirty fix changed nothing
- Kernel-Driver-Contract domain authority conflict: surfaced at repo 10, not at design time
- dirty-path dependency: noticed at 5/10, not anticipated

The framework's value is its ability to force confrontation with unanticipated
boundary conditions during execution, not the completeness of its pre-planned
rules. v2 direction: strengthen the framework's ability to surface surprises
rather than add more pre-emptive rules.
