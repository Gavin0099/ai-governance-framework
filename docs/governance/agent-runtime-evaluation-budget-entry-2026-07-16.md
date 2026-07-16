# Agent Runtime Evaluation - Surface Maintenance Budget Entry - 2026-07-16

Status: conditionally approved by repo owner (2026-07-16) with required
amendments; amendments applied in this revision. Implementation start is
additionally gated on the pending Copilot spike result and final owner
confirmation.
Runtime behavior change: no. Tranche 1 emits information only; it does not
automatically change gates, required commands, approval policy, or execution
flow. Any "changes review posture" evidence in this note means a human read
the output and decided — never an automatic effect.
Enforcement change: no
Consumer repo change: no (tranche 1 is framework-repo only)
Tooling change: approved scope below, not yet implemented

## Purpose

Register the Agent Runtime Evaluation plan as a maintenance-budget item under
the budget model in
`governance-surface-maintenance-budget-design-2026-07-07.md`, answering its
five budget questions before any schema or tool is built. This note approves
nothing by itself; the owner decision gate is at the end.

## Spike Evidence (prerequisite, completed)

Detection feasibility was tested before this entry, per the pre-registered
kill-switch in `spikes/runtime-detect/SIGNALS.md`:

- Claude Code / Windows / desktop: agent, agent_version, model, surface,
  session_id, governance_version all `verified` without agent self-report
  (`spikes/runtime-detect/result-claude_code-claude-desktop.json`).
- Codex / Windows / Codex Desktop: agent `verified`
  (`CODEX_INTERNAL_ORIGINATOR_OVERRIDE`), model `detected` only
  (config default, not session-bound), agent_version `unknown`
  (WindowsApps alias blocks `codex --version`)
  (`spikes/runtime-detect/result-codex-codex-desktop.json`).
- Negative tests on both agents: stripping env markers degrades to `unknown`
  with no guessing.
- Verdict against pre-registered criteria: GO (both primary agents reach
  agent>=verified and model>=detected).

## The Five Budget Questions

### 1. What observed failure requires this defense?

- Receipts carry no runtime identity: evidence produced under different
  agents, models, and surfaces is statistically indistinguishable, so
  validation quality cannot be compared or trended per runtime.
- Runtime drift is invisible: agent version bumps and model changes leave no
  trace, while the 2026-07-07 forensics ("queue born expired") showed
  cross-session parallel work drifts fast enough to invalidate artifacts.
- The 2026-07-06 consumer test-quality audit found `validation_passed`
  signals of very different trustworthiness; today nothing records which
  runtime produced which signal, so theater and real validation aggregate
  into one number.

### 2. Why do existing defenses not cover that failure?

- `runtime_hooks/adapters/*` identify the agent implicitly (by which adapter
  fires) but record no agent_version, model, or surface (verified 2026-07-16:
  no such field reads in the adapter tree).
- `governance_tools/runtime_profile_validator.py` validates declared claim
  ceilings and surfaces; it does not detect runtime identity. Name collision
  noted below.
- Session receipts have no runtime_profile binding field.
- No existing tool computes per-runtime local statistics.

### 3. What surface does this defense replace, merge, or deliberately coexist with?

- Replaces: nothing.
- Coexists with `runtime_hooks` adapters: detection must consume the
  SessionStart hook payload (permission_mode and tools are hook-payload-only;
  spike-proven not visible from shell env).
- Coexists with `runtime_profile_validator.py`; to avoid a vocabulary debt the
  new tool must NOT be named `runtime_profile.py`. Proposed name:
  `runtime_identity.py` (detection) + `evaluation_summary.py` (local stats).
- Receipt schema gains fields (runtime_profile_id, detection status,
  sample_origin, validator_signal); old receipts stay readable as `unknown`.
  Verified 2026-07-16: the closeout receipt already has a formal schema
  (`schemas/closeout_receipt.schema.json`, `additionalProperties: false`,
  carries `schema_version`, `agent_id`, `session_id`), so adding fields
  requires a receipt schema version bump. This is counted as a third schema
  surface in the cost accounting below, not a free "field group".

### 4. What evidence will show that this defense changes decisions?

Two evidence levels, deliberately separated. One documented case proves the
tranche is worth keeping alive; it must never be presented as proof that
cross-runtime governance works.

**Tranche survival evidence** (minimum to pass the review point in Q5) — at
least one documented, real (non-manufactured) case of:

- a real runtime drift (agent/model/surface change) is detected and a human
  changes review posture because of it (marks accumulated samples Drifted,
  orders a rerun);
- the local evaluation summary is cited by a repo owner in an actual decision
  (require validator rerun, add human spot-check, block a claim);
- a profile-bound receipt statistic exposes a validation mis-claim that
  aggregate numbers hid.

Survival-evidence hygiene: cases manufactured by the framework author to
satisfy this gate do not count; cases where the summary was read but changed
nothing must also be recorded, not discarded.

**G4 evidence** (out of tranche 1 scope; requires all of):

- repeated natural-task observations across independent consumer repos;
- runtime diversity (at least two agent/surface profiles);
- both success and failure cases on record;
- non-author decision use;
- at least one instance where governance avoided a wrong claim because
  runtime identity was distinguishable.

Additionally, Phase 3 completion requires one non-framework-author judging the
local summary decision-useful (promoted from the plan's G4 gate to tranche 1,
because if nobody finds the local summary useful, nothing downstream matters).

### 5. What is the planned review or expiry point if no decision effect appears?

Two failure modes are kept separate: "implementation slipped" and "feature
has no decision value". Neither may be blamed on the other.

- Implementation deadline: Phase 3 (local summary) must be live in the first
  repo by 2026-08-31. Missing this is a scheduling failure — the owner decides
  to extend or cancel, and no observation-window judgment is made.
- Evidence review: 60 days after Phase 3 becomes live (a full window, not
  truncated by a calendar date).
- Absolute review deadline: no later than 2026-10-31, unless the owner
  explicitly extends it in writing.
- If no tranche-survival evidence (Q4) by the evidence review: the two tools
  become retire_candidate under the standard two-step retirement, the receipt
  fields stay (schema-versioned, cheap, readable as unknown), and no further
  phases (F-7 integration, export, central collection) may start.

Spike evidence preservation (spike is superseded by formal tests, not deleted
on schema completion):

- keep `spikes/runtime-detect/SIGNALS.md` (methodology, per-agent signal
  tables, pre-registered kill-switch) permanently or until converted;
- convert the detection assertions and both negative tests into formal
  regression tests when Phase 1 lands; only then may `detect_spike.py` be
  removed;
- move result JSONs to formal evidence storage with a binding to the spike
  commit hash, so method and verdict remain reproducible;
- transient run products may be deleted at any time.

## Approved Scope If Accepted (tranche 1 only)

Plan Phase 0-3, local-only, with these spike- and review-driven amendments:

1. Detection-tier semantics are bounded. `verified` means "verified against
   an approved runtime signal", NOT cryptographically proven runtime
   identity — env markers can be inherited, overwritten, or forged. Each
   detected field records `signal_source` and `binding_scope`
   (session / installation / config-default), e.g. Codex model from
   config.toml is `binding_scope: config-default`, never session-bound.
   The schema documentation must state this ceiling verbatim.
2. Two-tier fingerprint over normalized model identity, not string-guessed
   majors. Model is stored structured
   (`provider / family / variant / version / revision / binding`); coarse id
   = `agent_family + model_family + surface_class` (sample accumulation),
   full id = all known normalized fields (drift marking only). The
   fingerprint algorithm carries its own `fingerprint_schema_version` so an
   algorithm change is never misread as runtime drift. Prevents every agent
   version bump from resetting samples to Uncalibrated.
3. Primary signals are env markers + SessionStart hook payload; parent-process
   chain is fallback-only (spike showed it breaks when intermediate shells
   exit).
4. Statistics must group by detection tier; `detected` model values (Codex
   config default) must never aggregate with `verified` ones as equals.
5. `validator_signal` on receipts is registry-derived, never agent-filled.
   Tiers are explanatory categories (`test_backed` / `structural_only` /
   `self_reported` / `unknown`), not high/medium/low. The tier comes from a
   versioned validator registry entry (`tier_source` + validator version
   recorded); no registry entry means `unknown`; validator updates require
   re-tiering (2026-07-06 audit linkage). An agent-writable tier field would
   be just another self-claim and is prohibited.
6. `honest_uncertainty_rate` is dropped from v1 schemas entirely (no objective
   rule exists; schema fields are the hardest surfaces to retire).

Surface cost of tranche 1: 2 tools and 3 schema surfaces — runtime identity
schema (new), evaluation summary schema (new), and a closeout receipt schema
version bump (existing schema is `additionalProperties: false`, so new fields
force a version). Everything else in the plan (F-7, adoption doctor items,
export, import, cross-repo, governance profiles) is explicitly out of
tranche 1 and requires a new budget entry or an amendment to this one.

## Non-Goals (unchanged from plan)

No ranking, no auto-upload, no prompt/code/diff storage, no gate skipping on
good scores, no engineer performance use.

## Non-Claims

- No tool, schema, or receipt field exists yet.
- The spike proves detectability on two runtimes on one machine, not detection
  accuracy in general.
- Codex model binding is unproven (config default only); Codex agent_version
  is currently not obtainable on this machine.
- GO means "worth building tranche 1", not "the plan is validated".
- Tranche 1 establishes G4 observability (the ability to separate evidence by
  runtime); it is not itself G4 evidence, and no report may present it as
  such.

## Owner Decision Record

2026-07-16 — repo owner: **APPROVE TRANCHE 1 WITH AMENDMENTS** (amendments 1-7
of the owner review; all applied in this revision).

Approved:

- Phase 0-3, framework-repo only;
- report-only runtime identity detection;
- receipt binding (with receipt schema version bump);
- local evaluation summary;
- no enforcement or automatic workflow change.

Not approved:

- F-7 integration;
- consumer rollout;
- export/import;
- central collection;
- agent ranking;
- governance profile automation.

Implementation start gate: pending Copilot spike result and final owner
confirmation. Suggested implementation branch:
`feature/agent-runtime-evaluation-tranche-1`. Any scope growth reopens the
five questions.
