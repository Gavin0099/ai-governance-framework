# AI Governance — Cross-platform instruction architecture autonomous loop

Status: **CANDIDATE / NOT MERGED**. Date: 2026-10-29.
Baseline: `main` `43fa8c71cac7965103193cafe7e789231218e63a`.
Owner request: design the central Framework plan and slices, then execute the scoped implementation loop without per-slice confirmation. **No main merge, no production Consumer changes.**

## Goal

Reduce irrelevant always-on AI Governance instructions across **Codex, Claude Code and GitHub Copilot**, while preserving product-first behavior, Owner Gates, F-7 truthfulness, Memory and legitimate Session-End Closeout. Consumer-specific safety and domain rules must remain intact. Cutting bytes is not itself proof of better behavior.

## Exact source inventory

| Surface | Role | Planned handling |
|---|---|---|
| `baselines/repo-min/AGENTS.md` | Consumer root baseline: 19,435 B LF, roughly 16 KB F-7/update instructions | **First structural target**; keep critical inline router, refuse invalid completion, conditional long SOP |
| `baselines/repo-min/AGENTS.base.md` | Protected Memory, Risk, Closeout and DONE contract | Retain safety triggers; do not remove required Memory/Closeout |
| `governance/agent-contract-template.md` | Managed `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` | Preserve Delivery Convergence and `SYSTEM_PROMPT.md#2.8` SHA projection |
| `governance/copilot-instructions-template.md` | Copilot-specific rules / reporting | Check duplications and effective loading; preserve Owner gates |
| `governance_tools/external_governance_submodule_updater.py` | Updates the Consumer's inline F-7 section | Must propagate new shape without deleting Consumer-owned text |
| `governance_tools/f7_full_update.py` | Appends keyed `f7_update_boundary` if missing | Must not introduce critical tail truncation or false completion |
| `governance_tools/hook_installer.py` | Installs agent surfaces | Must remain idempotent, no unrelated hook rewiring |

ADR-0003 PR #262 remains **PROPOSED** and its reverted extraction was **not** approved for production. PR #267 Delivery Convergence was merged to baseline; the prior 473-byte local F-7 candidate is **not** a delivered baseline.

## Autonomous bounded Slices

| Slice | Work | DONE / verification |
|---|---|---|
| I0 — map | Inventory every central template + updater and mark safety-critical vs conditional/on-demand vs mechanical vs duplicate | Section/source/path/bytes matrix; distinguish file existence from actual agent load |
| I1 — F-7 split | Move verbose, **noncritical** update walkthrough from baseline to an existing or new on-demand `governance/*.md` with an always-visible F-7 route and fail-closed claims. Source-preserve removed text and adjust the updater only if necessary | Candidate size reduction; update/check/manual/blocked/missing-summary cases keep original status and false-completion refusal. No test-only weakening |
| I2 — other rules | Inventory Risk, Must-Test, Contract Output, Closeout, Memory, Copilot reporting and actual duplication. Change at most one demonstrably safe duplicate; `NO CHANGE` is acceptable | Critical Owner, risk escalation, §2.8 SHA, Memory/Closeout semantics unchanged |
| I3 — disposable Consumers | Install/update twice; check Consumer-owned bytes, F-7 boundary, short/long loading and Windows LF/CRLF. Check Codex/Claude/Copilot separately and mark unobservable evidence UNKNOWN | No lost user rules, invented PASS, mandatory truncation or hook rewiring |
| I4 — behavior | Genuine bounded A/B only if runnable: same agent/model/config, clean writable disposable repo, small L0/L1 product task with unrelated warning, plus safety negative case | DONE achievable and measured; otherwise INCONCLUSIVE/NOT RUN, do not repeat unrelated canary |
| I5 — deliver | One branch + one Draft PR with exact HEAD, scoped tests/negative cases, byte delta, rollback, nonclaims | All actual blockers resolved or HOLD; no merge/main deployment |

## Loop controller

- In this approved scope, run **Implement → targeted test → independent exact-HEAD Review → bounded correction** continuously, max **3 revision iterations** and max **2 independent reviews**. If no independent reviewer available, report `NOT REVIEWED`, never self-label APPROVED.
- Do not restart old D0/D1/CP-1 work; do not create a second parallel process, new Gate, Profile, Schema, Dashboard or unrelated PR. Use this one status file for progress, only at real milestones.
- Nonblocking unrelated findings: one line in next options and continue authorized work. Unknown decision impact after bounded check, owner-gated operations, safety/data/firmware risk or actual test failure: HOLD affected path; independent unaffected work may continue.
- Commit/push to this named branch and update its **Draft PR** are authorized; **no main merge, force push, branch deletion, production Consumer changes, billing/release or irreversible actions**.
- Any rewrite requiring changes to canonical §2.8 SHA, Owner rights or F-7 safe completion semantics must **STOP** for specific Owner decision, not silently adjust test assertions.
- STOP when agreed scope DONE, genuine P0/P1 blocker, loop cap, or unsafe semantic change. Report concise completed/held/unknown results; do not make user monitor minute-by-minute.

## Explicit safety cases for negative regression

- Mere `AGENTS.md` / pointer / lock update ≠ `updated` / `already_current`; `manual_update` and `destructive_manual_update` cannot masquerade as complete F-7.
- If adoption table missing: `human_readable_adoption_summary: NOT REPORTED`, `update_report_complete=false`, `completion_claim_allowed=false`, no invented rows.
- F-7 user request triggers governed F-7 and correct six-stage result; `check` remains read-only.
- Consumer-specific permissions/risks and hook failures remain enforced; no override or F-7 install in a live dirty Consumer.
- Session Task DONE ≠ Session End; do not cancel actual mandatory closeout or Memory trigger.
