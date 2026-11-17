# PLAN.md - AI Governance Framework

## Canonical Planning Surface

> **最後更新**: 2026-11-17
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
> **Created**: 2026-04-10
> **Risk tier**: L2
> **Planning window**: 2026-03 through 2026-09
> **Encoding status**: UTF-8 reviewer-readable canonical replacement
> **Task Level**: L2 framework; this documentation slice is L1.

| Read first | Current instruction |
|---|---|
| Now | #331 is delivered: merged at `737eadeb` (candidate `f876428a`, owner merge authorization bound to that SHA), closing #328 (F-7 tells a submodule consumer that formal closeout still needs `governance/framework.lock.json`; first-import SOP lock repair) and removing the conflicting `[Decision Summary]` opening rule; main CI on `737eadeb`: 7 success, 5 skipped, 0 failed, including the Canonical Drift Post-Merge Audit. Retained limits: Windows native argument passing for the Codex hook remains unverified (`tests/test_codex_windows_hook_command.py::test_outer_powershell_reaches_python_with_space_paths[0]` and `[7]` decode PowerShell's cp950 stderr as UTF-8, so their argument checks never run); real consumer end-to-end closeout and native Stop acceptance are not done; a first-import lock is still added by hand. First backlog-convergence group delivered: #275 closed as superseded by #291; #258 (ADR-0002, with its implementation record) merged at `5ecaaaf3` (candidate `c21675dd`); main CI on `5ecaaaf3`: 7 success, 5 skipped, 0 failed, including the Canonical Drift Post-Merge Audit. Second group delivered: PLAN sync #332 merged at `39d57baf` (candidate `01728943`; the owner's reply "授權合併 #332" answered a question naming that SHA); main CI on `39d57baf`: 7 success, 5 skipped, 0 failed, including the Canonical Drift Post-Merge Audit; the proposal-PR dispositions, the #213 / #282 reproduction verdicts and the #223 review were reported as proposals. Now: the #213 Copilot closeout gaps reproduced on main, re-implemented from main as one new PR with separately verifiable commits (slices S1–S6). |
| Authority | Owner decision, 2026-11-17 ("先修 #213"), with the owner's slice plan: S1 a legacy turn Stop is not a session end; S2 missing agent input is not recorded as work; S3 a session is consumed only after its closeout is accepted, and accepted content is verified on replay; S4 CHECKS_RUN tells a run check from a mention; S5 integration, comparison with old #213, PR, independent review and CI; S6 owner merge decision, main CI and the disposition of old #213. Merging needs a separate owner decision bound to the exact candidate SHA under [SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md](governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md). |
| Allowed | Framework code and tests for the four reproduced gaps, descriptions those fixes make false, and this PLAN and active-task update through the existing canonical writer, to a reviewed candidate with CI. |
| Limits | No merge; no new gate; no change to the R1/R2 basic contracts; no consumer repository touched; old #213 is not rebased or reused wholesale; synthetic tests do not stand in for native SessionEnd evidence. Other open PRs keep their state; #176 stays paused because another session's uncommitted work touches the same memory files. [Standing conditions](#active-claim-boundaries) remain in force. |
| DONE | Hand the owner the final candidate SHA and change scope, independent review and CI for that SHA, a comparison showing what of old #213 is carried, dropped or superseded, and the still-unverified native execution items. |
| Next | Owner merge decision on the #213 fix PR, then the disposition of old #213; owner decisions on the proposal-PR dispositions, #282 behaviour verification and the #223 rebase. #324 stays Draft: its selector expects the old PLAN headings and falls back to the full PLAN on the restructured one; re-measure its value on the new PLAN before adoption or closure. After the backlog, return to real consumer end-to-end acceptance. The nine August constraints still await owner adjudication and remain in force. Do not automatically start backlog work. |
| Phase | [A–D completed; E in progress](#phase-overview), validity before expansion. |
| Full source | [Verbatim pre-restructure PLAN](docs/status/plan-history-2026-11-16-6c7e24c3.md) and [512-unit preservation/authorization map](docs/status/plan-information-architecture-2026-11-16-mapping.md). History is not a planning source. |

The front-door table above answers now / authority / limits. Source IDs Mnnnn refer to original PLAN@6c7e24c3 lines; archive line = original line + 10. Every effective condition is stated here; links supply full provenance, not missing authority. The nine August standing constraints remain **still awaiting owner adjudication; kept in force unchanged**.

## Current Sprint - 2026-11-17

- [>] #213 Copilot closeout gaps (S1–S6): re-implement the four gaps reproduced on main as one new PR with separately verifiable commits, to a reviewable candidate with independent review and CI, per the owner decision of 2026-11-17.

Claim ceiling: the backlog's first and second groups are delivered (#258 merged at `5ecaaaf3`, #332 at `39d57baf`; main CI green on both, including the Canonical Drift Post-Merge Audit). The #213 fixes are proven by framework tests on synthetic repositories; Windows native argument passing, native Copilot / Claude / Codex SessionEnd execution and real consumer end-to-end closeout remain unverified (see the first-screen Now row). Allowed and limits for this slice are the first-screen Allowed and Limits rows: no merge, no new gate, no R1/R2 basic-contract change, and no other PR's state changed. Merge requires a separate owner decision on the exact candidate SHA under [SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md](governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md). Follow-up order and holds are stated in the first-screen Next row; the nine August constraints still await owner adjudication and remain in force. Do not automatically start backlog work.

## Authorizations And Owner Decisions

Claim ceiling: original grants keep their scope and limits. Existing valid grants are not renewed or extended by this edit. Ended single-use grants are terminal records; their observed outcomes and source limits below apply to their own instances. Quoted text is verbatim; the history link supplies the per-step narrative.

### Authorized PLAN information architecture — 2026-11-16

Scope: framework root PLAN, immutable history, compact mapping, baseline inventory and the existing real-PLAN layout/count test inventories. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0146 · Maintain portable AI governance contracts and reviewer-facing evidence.** Claim ceiling (verbatim):
Claim ceiling: Maintain portable AI governance contracts and reviewer-facing evidence.
Claim ceiling: Define runtime observation, closeout, claim ceiling, and evidence surfaces.
Claim ceiling: Preserve repo-local memory / state authority and traceability.
Claim ceiling: Support external repo adoption, readiness, framework version, and source audit.
Claim ceiling: Keep governance docs and static validators aligned with observed failures.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L156-L160)

**M0154 · Not a full execution harness.** Claim ceiling (verbatim):
Claim ceiling: Not a full execution harness.
Claim ceiling: Not a machine-authoritative semantic advisory system.
Claim ceiling: Not a generic multi-agent orchestration platform.
Claim ceiling: Not an OS sandbox, RBAC system, or enterprise AIMS replacement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L164-L167)

**M0175 · original encoding-repair claim ceiling.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling for this repair:
Claim ceiling: CLAIMED: reviewer readability of the active `PLAN.md` planning surface.
Claim ceiling: NOT CLAIMED: roadmap semantic change, historical evidence migration, artifact
  cleanup, validator behavior change, hook behavior change, or enforcement
  change.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L185-L190)

**M0228 · Onboarding false-positive and F-7 explicit-target corrections are merged.** Claim ceiling (verbatim):
Claim ceiling: Onboarding false-positive and F-7 explicit-target corrections are merged
  through PR #195 and PR #196. Their delivery does not qualify consumer runtime.
Claim ceiling: Keep these findings as separate slices.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L238-L245)

**M0508 · Restore the canonical planning surface to current repository truth.** Claim ceiling (verbatim):
Claim ceiling: Restore the canonical planning surface to current repository truth.
Claim ceiling: Finish existing review, disposition, publication and consumer-transfer work
  before adding governance surface.
Claim ceiling: Keep reviewer-facing narrative drift observation-only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L518-L521)

**M0558 · Any lifecycle restructuring must first disposition PR #28, which already.** Claim ceiling (verbatim):
Claim ceiling: Any lifecycle restructuring must first disposition PR #28, which already
  carries a fleet census, a lifecycle contract spec, heading decision tables
  and a rollover proposal with open items. Reuse, supersede or explicitly
  reject those inputs; do not create a second, parallel PLAN lifecycle
  contract beside it.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L568-L572)

**M0569 · No `.tmp_*` worktree cleanup in this slice.** Claim ceiling (verbatim):
Claim ceiling: No `.tmp_*` worktree cleanup in this slice.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L579-L579)

**M1331 · Commit `PLAN.md` repair separately from runtime ledgers.** Claim ceiling (verbatim):
Claim ceiling: Commit `PLAN.md` repair separately from runtime ledgers.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1341-L1341)

### Authorized #309 consumer AGENTS.md instruction budget — 2026-11-15

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0005 · original #309 framework-template grant; delivery terminal at #311; not a consumer-edit grant.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Owner authorized the bounded Issue #309 fix from `main@8db71dc2` on
  `fix/309-agents-md-budget`.
Claim ceiling: Merge is not authorized.
Claim ceiling: DONE: replace managed Update Intent and F-7 calibration prose with canonical
  pointers, preserve memory routing and every moved rule, and measure the final
  AGENTS.md in both F-7 backends including dry-run. On-disk sizes greater than
  32,768 bytes downgrade successful completion to `partially_updated`, including
  the update receipt; CRLF-only worst-case overflow remains a warning.
Claim ceiling: Real agent loading, CI and independent review remain unverified.
Claim ceiling: Non-goals: S4 drift checking, new gates/schema/hooks/tiers, R2/closeout/
  ownership changes, root AGENTS.md edits, or changes to any consumer repo.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L15-L29)

### Owner-recommended #250 Codex Stop hook output fix — 2026-11-15

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0021 · original #250 hook-output-only grant; framework delivery terminal at #308.** Claim ceiling (verbatim):
Claim ceiling: Delivered at PR #308; the original grant is consumed and not reusable. The following DONE text is the preserved native-only output contract, not a new execution instruction.
Claim ceiling: Owner plan "real consumer validation and friction reduction", S2 prerequisite:
  a minimal #250 fix of the hook output contract only, without changing R2
  semantics. Push and PR by the orchestrator; merge stays with the owner.
Claim ceiling: DONE: for `--agent-id codex --trigger-mode native_hook` only, a turn whose
  session holds no prepared (OWNED) R2 owner record exits 0 silently with a
  stderr reason, and a successful closeout keeps stdout empty with a stderr
  summary. An unreadable owner record, a HOLD state for this session and
  pipeline errors still exit 1. Claude, Copilot and the other trigger modes are
  unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L31-L46)

### Authorized S1-B memory text transport and worktree framework root — 2026-11-15

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0038 · original S1B transport/worktree-root grant; installed-hook status superseded-by #321; Copilot bridge remains separate.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Owner plan "real consumer validation and friction reduction", stage S1-B,
  authorized 2026-11-15 from `main@ea2da76b`: diagnose the Traditional Chinese
  loss seen in a real consumer handoff and the worktree framework path, with the
  smallest fix. Push and PR by the orchestrator; merge stays with the owner.
Claim ceiling: Diagnosis: Windows PowerShell 5.1 pipes text to a native program's stdin with
  `$OutputEncoding` (default US-ASCII), so non-ASCII text arrives as `?`;
  argv and UTF-8 file input are exact.
Claim ceiling: DONE: `governance/MEMORY_PROTOCOL.md` documents the safe transport and
  readback check; `governance_tools/memory_workflow.py` prefers a linked
  worktree's own framework copy when the shared hook root file points outside
  that worktree (main checkouts and external frameworks unchanged); three
  tests in `tests/test_memory_workflow.py`, one of which fails on the base.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L48-L66)

### Authorized I2 agent core rules (S2-A/S2-B) — 2026-10-30

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0058 · original I2 S2A/S2B grant; delivery terminal; core-rule boundaries retained.** Claim ceiling (verbatim):
Claim ceiling: Delivered S2-A/S2-B; grant consumed. The DONE sentence below names the agent-contract and Copilot templates referred to by "those templates"; the framework-root copy remains held out.
Claim ceiling: Owner ruling C1-C7 adopted 2026-10-30; slices S2-A (single canonical core)
  and S2-B (projection) authorized on branch `feat/i2-core-rules-pr` from
  `main@48f0ce76`. Push, PR and merge stay with the orchestrator/owner.
Claim ceiling: DONE: `governance/AGENT_CORE_RULES.md` body projected byte-identical into the
  agent-contract and Copilot templates; conflicting Copilot DONE/owner/label
  wording removed; baseline memory triggers and DoD aligned with ruling C2/C3;
  drift test `tests/test_agent_core_rules_projection.py`.
Claim ceiling: Scope: those templates, `baselines/repo-min/AGENTS.base.md` (framework-root copy held out), tests and the proposal
  `docs/proposals/i2-core-rules-20261030.md`. No change to the 2.8 projection,
  Owner Gate scope, F-7 fail-closed rules or memory semantics beyond the ruling.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L68-L79)

### Authorized VS Code Stop wiring repair — 2026-10-15

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0071 · original VSCode Stop fix grant; delivery terminal at #211; original Draft/consumer scope retained.** Claim ceiling (verbatim):
Claim ceiling: Owner authorized a bounded fix from `main@2a09d54`, independent review and
  one Draft PR; stop after delivery. Merge and consumer updates are not authorized.
Claim ceiling: DONE: fresh install and managed upgrade do not wire VS Code Stop to closeout;
  preserve custom hooks, reject ambiguous configurations, keep genuine sessionEnd
  and single SessionStart registration, and remain idempotent through F-7.
Claim ceiling: Scope: existing VS Code template, installer, validator, related tests and docs.
  No memory semantics, authority, lifecycle event, gate, schema or receipt changes.
Claim ceiling: Other planning entries below retain their own historical evidence boundaries.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L81-L92)

### Authorized GDScript support — 2026-10-13

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0084 · GDScript S1/S2 and repair delivery terminal at #209/#210; sequential consumer S3/S4 grant retains original scope.** Claim ceiling (verbatim):
Claim ceiling: S1/S2 delivered at #209 / 06b98906 and #210 / 2a09d542. The quoted State paragraph is the earlier S2 PR #210 repaired-head checkpoint (88824c4d), including its review/CI prerequisites. That conditional-merge grant ended with #210; it does not authorize consumer S3/S4 merge or pin adoption. The S1/S2 acceptance and exclusion-normalization limits still bind their delivered behavior.
Claim ceiling: Owner confirmed sequential S1–S4 implementation after scope analysis.
Claim ceiling: Owner additionally authorized separate S1/S2 commits, pushes and Draft PRs
  on 2026-10-13; merge and consumer pin adoption remain separate gates.
Claim ceiling: S1 DONE: explicit GDScript contracts and non-empty rule loading work;
  checkpoint projections agree and existing language behavior remains valid.
Claim ceiling: S2 DONE: product `.gd` signals are suggested without using test, document,
  framework-copy or Godot-only signals as product-language proof.
Claim ceiling: S3/S4 belong to DiceMercenaries: bind its existing native checker and add
  post-task/memory CI coverage using the existing extension interfaces.
Claim ceiling: Allowed framework scope: language enum, validator, rule-pack metadata/content,
  language suggestion, checkpoint projections and directly related tests.
Claim ceiling: State: S1 PR #209 merged at 06b98906 after independent review and green CI.
  S2 PR #210 now targets main. Its original final tree passed review and CI,
  but external P2 review exposed case-varied non-product root false positives;
  repair 88824c4d normalizes the existing exclusion without threshold changes.
  Final repaired-head review and CI remain pending before conditional merge.
  Owner authorized CI restoration and review followed by conditional merge.
  Consumer S3/S4 candidates remain local/uncommitted;
  pin adoption and hosted checks are pending framework review and delivery.
Claim ceiling: Claim ceiling: scoped implementation, tests and authorized Draft delivery.
  Merge, hosted CI, consumer pin adoption, owner classification acceptance and
  full adoption remain separate authorization/evidence gates.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L94-L120)

### Authorized observed-failure repair — 2026-10-03

Scope: original bounded framework/consumer work stated in the following clause. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0112 · framework repair terminal at #204; original reviewed eight-blob consumer-policy/product-push grant retains its bounds.** Claim ceiling (verbatim):
Claim ceiling: Framework delivery is terminal at #204. The quoted PR204 repair/review/CI sentence is the original exact-head prerequisite, not a current repair instruction; merge alone is not proof that all three checks passed. The separately reviewed eight-blob consumer scope remains distinct.
Claim ceiling: Owner instruction: repair Bookstore-Scraper's pre-push publication blocker
  before resuming its sequential reviewed product slices.
Claim ceiling: DONE: a reviewed framework PR supports a private, exact-blob historical JSON
  parse-debt policy; real Git push proves known historical failures can be
  acknowledged while newly introduced parse failures and inventory findings
  still block. After framework delivery, deploy only the separately reviewed
  eight-blob consumer policy and retry the ordinary product push.
Claim ceiling: Allowed: `governance_tools/external_tree_inventory_guard.py`, managed
  `scripts/hooks/pre-push`, directly related tests, policy documentation,
  evidence and canonical closeout companion. Observed PR gates also require
  preserving protected `safe.directory` configuration (including operator
  environment-selected global/system and command sources) and retiring nine
  expired test exclusions whose local fixtures now pass (no expiry renewal).
  No ancestry exclusion, threshold
  relaxation, history rewriting, production imports or unrelated roadmap work.
Claim ceiling: State: implementation and focused validation pass; independent review has
  approved the implementation and exact eight-blob policy.
Claim ceiling: PR204 P1 and the expired-registry CI failure are being repaired; current-head
  independent review, Codex review and complete CI must pass before delivery.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L122-L144)

### Authorized R0 specification — 2026-09-02

Scope: framework bounded active_task work, with spec/implementation/feasibility separated. Status: original exact-instance acceptance/delivery recorded satisfied; grant consumed; no future RAG or qualification authority. Claim ceiling: retained verbatim source conditions below.

**M0239 · Define one bounded exact round-trip specification for one.** Claim ceiling (verbatim):
Claim ceiling: This exact-instance acceptance/delivery is recorded satisfied by the original named source/head/merge below; its grant was consumed for that delivery. The quoted requires clauses apply to that original instance, not a pending approval. Future RAG, qualification or other implementation is not authorized by it.
Claim ceiling: Define one bounded exact round-trip specification for one
  caller-authorized canonical session-derived record and logical `active_task`
  surface.
Claim ceiling: DONE: the reviewed specification reuses the canonical writer's public
  outcome, `build_record_identity()`, `render_active_task_projection()`, and
  `memory_pipeline.memory_layout.resolve_memory_file()`; keeps writer-owned
  identity continuity separate from exact content continuity; requires the
  writer outcome path to equal the resolver snapshot before retrieval; treats
  missing surfaces, malformed or ambiguous persisted markers, path drift,
  invalid UTF-8, invalid inputs, and ordinary dependency exceptions as
  fail-closed; binds the caller-admitted M-1 observation to the exact query,
  logical surface, and canonical record identity; preserves M-1 non-resolved
  states without context rendering; permits structurally valid historical
  non-target identities while requiring exactly one byte-matching target
  payload; accepts only LF or CRLF persisted framing and renders the verified
  payload through the public writer's canonical LF line; requires a resolved
  authority observation to match both record identity and the SHA-256 of that
  public renderer's exact UTF-8 bytes while leaving legacy digest-less
  observations parseable but non-resolving;
  forbids silent drop, injection, and duplicate rendering; and freezes the
  focused evidence-case inventory without implementing runtime behavior.
Claim ceiling: Claim ceiling: specification for one caller-authorized active-task exact
  round trip only. No authority-policy creation, writer or identity redesign,
  MRCSP detector invocation or runtime integration, semantic retrieval, RAG,
  update, supersession, freshness, deletion, Runtime public result transport or
  schema, API versioning, hook, CI, gate, blocker, enforcement, Memory Runtime
  R1, or Gate 3 behavior is authorized.
Claim ceiling: Implementation-readiness acceptance requires an owner merge attestation
  recorded for the exact candidate HEAD before merge, technical review
  approving that same HEAD with no unresolved P0/P1, green required checks,
  reviewed-head preservation, and merge. A later merge action cannot
  retroactively establish the owner-attestation predicate. Acceptance
  does not activate a governance authority. Runtime implementation requires a
  separate owner authorization after specification acceptance.
Claim ceiling: Implementation-readiness predicates were satisfied for exact reviewed head
  `b2cc43bc5e7e9032d55aa49f5e820220a792eb43`, merged through PR #139 at
  `ee44240f` after owner attestation, zero unresolved P0/P1, green checks, and
  reviewed-head preservation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L249-L286)

### Authorized R0 implementation — 2026-09-02

Scope: framework bounded active_task work, with spec/implementation/feasibility separated. Status: original exact-instance acceptance/delivery recorded satisfied; grant consumed; no future RAG or qualification authority. Claim ceiling: retained verbatim source conditions below.

**M0277 · Implement the smallest active-task Runtime vertical slice over one.** Claim ceiling (verbatim):
Claim ceiling: This exact-instance acceptance/delivery is recorded satisfied by the original named source/head/merge below; its grant was consumed for that delivery. The quoted requires clauses apply to that original instance, not a pending approval. Future RAG, qualification or other implementation is not authorized by it.
Claim ceiling: Implement the smallest active-task Runtime vertical slice over one
  caller-authorized canonical record and one caller-admitted M-1 observation.
Claim ceiling: DONE: the Runtime calls the canonical active-task writer, snapshots the
  logical resolver path and exact persisted bytes, independently parses every
  projection-looking active-task line fail closed, permits well-formed
  historical non-target identities, requires exactly one target identity and
  exact canonical payload, binds `resolved` to both writer-owned identity and
  the SHA-256 of public-renderer UTF-8 bytes, preserves the four M-1
  non-resolved states with zero context bytes, and returns the public
  renderer's canonical LF bytes only after the entire bounded chain succeeds;
  every frozen R0 evidence case has executable focused coverage.
Claim ceiling: Claim ceiling: one active-task exact write-resolve-read-verify-render path
  only. No writer, resolver, authority, identity, MRCSP, schema, hook, CI, gate,
  enforcement, RAG, semantic retrieval, update, supersession, deletion, crash
  safety, Runtime R1, or Gate 3 behavior is changed or authorized.
Claim ceiling: Delivery predicates were satisfied for exact independently reviewed head
  `966dbbb3f4f8e8c987e286396a032d9230dc2940`, merged through PR #140 at
  `ae926fc7b877c413036ba37cc0655cf62fbda75c` after owner authorization, zero
  unresolved P0/P1, green pre-merge checks, reviewed-head preservation, and a
  successful post-merge Governance Check whose Canonical Drift Post-Merge Audit
  passed.
Claim ceiling: This one-time reconciliation records that earlier delivery event; its later
  closeout commit does not imply that the PLAN or memory record existed in merge
  commit `ae926fc7`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L287-L313)

### Authorized R1 specification — 2026-09-04

Scope: framework bounded active_task work, with spec/implementation/feasibility separated. Status: original exact-instance acceptance/delivery recorded satisfied; grant consumed; no future RAG or qualification authority. Claim ceiling: retained verbatim source conditions below.

**M0307 · Define one non-authoritative technical specification for exactly one.** Claim ceiling (verbatim):
Claim ceiling: This exact-instance acceptance/delivery is recorded satisfied by the original named source/head/merge below; its grant was consumed for that delivery. The quoted requires clauses apply to that original instance, not a pending approval. Future RAG, qualification or other implementation is not authorized by it.
Claim ceiling: Define one non-authoritative technical specification for exactly one
  append-only `active_task` supersession edge from distinct v1 and v2 canonical
  record identities.
Claim ceiling: DONE: the specification keeps `build_record_identity()` and
  `memory_layout.py` unchanged; binds each version through the existing record
  identity plus the SHA-256 of public-renderer bytes; preserves v1 as history;
  defines exactly three dispositions where v1-only is the base current, one
  exact v1-to-v2 relation makes v2 the superseding current, and every partial or
  ambiguous state yields zero context; permits only one relation-only retry for
  the exact v1-plus-v2 missing-edge partial state when exactly one currently
  M-1-resolved authorization binds the persisted endpoint pairs;
  requires a caller-admitted M-1-resolved semantic authorization binding the
  supersede decision and both endpoint identity/digest pairs; requires complete
  immutable pre-write snapshot validation before either writer invocation;
  fails closed without mutation on every other pre-existing missing, malformed,
  duplicate, conflicting, cyclic, self-referential, or content-mismatched
  lineage state; and defines a focused evidence plan without implementing
  Runtime behavior.
Claim ceiling: Claim ceiling: one proposed two-version, one-edge `active_task` supersession
  contract only. No implementation, writer/identity/layout semantic change,
  authority-policy creation, longer lineage, migration, deletion, expiry,
  atomicity, crash/concurrency qualification, RAG, semantic retrieval, hook,
  CI, gate, blocker, enforcement, Gate 3, or governance authority is authorized.
Claim ceiling: Specification acceptance requires exact-head technical review with no
  unresolved P0/P1, green scope-matched checks, reviewed-head preservation, and
  owner merge authorization. Acceptance does not authorize the implementation
  tranche or any RAG work.
Claim ceiling: Specification acceptance predicates were satisfied for exact reviewed head
  `c56bef21f4993cdedd6dc41f92b2ada88ff6d5c8`, merged through PR #144 at
  `c751644be56439ec8ea910de0cfaebc3c078f4ad` after owner authorization, zero
  unresolved P0/P1, green checks, and reviewed-head preservation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L317-L347)

### Authorized R1 implementation — 2026-09-04

Scope: framework bounded active_task work, with spec/implementation/feasibility separated. Status: original exact-instance acceptance/delivery recorded satisfied; grant consumed; no future RAG or qualification authority. Claim ceiling: retained verbatim source conditions below.

**M0338 · Implement the bounded two-version `active_task` supersession vertical.** Claim ceiling (verbatim):
Claim ceiling: This exact-instance acceptance/delivery is recorded satisfied by the original named source/head/merge below; its grant was consumed for that delivery. The quoted requires clauses apply to that original instance, not a pending approval. Future RAG, qualification or other implementation is not authorized by it.
Claim ceiling: Implement the bounded two-version `active_task` supersession vertical
  slice defined by the accepted R1 specification.
Claim ceiling: DONE: from a fully validated immutable pre-write snapshot, a canonical v1
  plus one content-bound resolved supersession authorization can append the
  canonical v2 projection and one exact v1-to-v2 relation; the verified final
  snapshot returns only v2 as current while retaining v1 as history; a complete
  retry performs zero writes; a v2-written/relation-missing partial state
  returns zero context and permits only a fresh authorized relation-only retry;
  every pre-existing invalid state fails before either writer invocation with
  bytes unchanged; and the four valid M-1 non-resolved states preserve their
  disposition with zero context and zero writes.
Claim ceiling: Claim ceiling: one two-version, one-edge active-task supersession path only.
  No longer lineage or graph engine, RAG, semantic retrieval, delete, expiry,
  rollback, crash atomicity, general concurrency control, writer-owned record
  identity redesign, R0 parser change, memory-layout change, authority-policy
  creation, hook, CI, gate, blocker, enforcement, or Gate 3 behavior is
  authorized.
Claim ceiling: Delivery requires exact-head technical review with no unresolved P0/P1,
  green scope-matched checks, reviewed-head preservation, and separate owner
  merge authorization.
Claim ceiling: Implementation delivery predicates were satisfied for exact reviewed head
  `6b441071c794ac38f69403919ce969eb205abcc7`, merged through PR #145 at
  `c6e5d9e14ddba7ec1d7543f1808c98c946d297ee` after owner authorization,
  zero unresolved P0/P1, green required and post-merge checks, and
  reviewed-head preservation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L348-L372)

### Authorized NSI-N0 feasibility — 2026-09-04

Scope: framework bounded active_task work, with spec/implementation/feasibility separated. Status: original exact-instance acceptance/delivery recorded satisfied; grant consumed; no future RAG or qualification authority. Claim ceiling: retained verbatim source conditions below.

**M0372 · Record the bounded NSI-N0 feasibility result without defining an.** Claim ceiling (verbatim):
Claim ceiling: Record the bounded NSI-N0 feasibility result without defining an
  implementation-ready persisted-session reader grammar.
Claim ceiling: DONE: current persisted logical `active_task` and `review_log` surfaces can
  reconstruct record plus summary, but current repository state cannot
  mechanically establish cross-session authority freshness; resolved Natural
  Session replay is therefore `BLOCKED` with zero context;
  `current_human_instruction` cannot be replayed as resolved without an
  independently comparable persisted instruction-state identity;
  `approved_change` cannot be replayed as resolved from repository HEAD equality
  alone, and a pre-write HEAD is self-invalidating across the
  attachment-containing commit; this decision does not define reader grammar,
  attachment cardinality, historical precedence, standalone-v2 admission, or
  R1 edge-selection semantics.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L382-L397)

### Authorized report-only MRCSP boundaries — 2026-09-02

Scope: M0/M1a/M1b synthetic/caller-admitted report-only detectors. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0402 · Add one deterministic report-only detector for one caller-admitted.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Add one deterministic report-only detector for one caller-admitted
  `memory_root` directory and one logical name defined by
  `MEMORY_FILE_ALIASES`.
Claim ceiling: DONE: resolution reuses
  `memory_pipeline.memory_layout.resolve_memory_file()`; an existing canonical
  or secondary alias produces zero findings; all configured aliases missing
  produces exactly one `missing_logical_memory_surface` warning; repeated
  unchanged input produces byte-stable JSON; invalid roots, logical names,
  argument types, and ordinary resolver exceptions fail closed with
  `ValueError`.
Claim ceiling: Claim ceiling: one caller-specified logical surface at one filesystem
  observation only. No repository-wide completeness, parsing, repair,
  creation, deletion, alias inference, normalization, semantic identity,
  freshness, supersession, reader, projection, writer, schema, runtime, hook,
  CI, gate, blocker, enforcement, or M2 behavior is authorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L412-L430)

**M0424 · Add one deterministic report-only namespaced knowledge-identity collision.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Add one deterministic report-only namespaced knowledge-identity collision
  detector over exactly two caller-admitted `KnowledgeIdentityObservation`
  values.
Claim ceiling: DONE: two distinct record identities with the same exact case-sensitive
  `knowledge_id` produce exactly one `knowledge_identity_collision` finding;
  different identifiers produce zero findings; input order does not change the
  result; repeated input produces byte-stable JSON; invalid input fails closed
  with `ValueError`.
Claim ceiling: Claim ceiling: exact caller-supplied knowledge-identifier equality only. No
  Markdown parsing, normalization, semantic identity, missing logical surface,
  reader, projection, supersession, schema, runtime, hook, CI, gate, blocker,
  enforcement, or M2 behavior is authorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L434-L449)

**M0443 · Add one deterministic report-only encoding-integrity detector for one.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Add one deterministic report-only encoding-integrity detector for one
  caller-admitted `MemoryRecordBytes` value.
Claim ceiling: DONE: invalid UTF-8 produces exactly one
  `memory_encoding_integrity_anomaly` finding; valid UTF-8 containing U+FFFD
  produces exactly one finding; clean valid UTF-8 produces zero findings;
  repeated input produces byte-stable JSON; non-record and empty-content input
  fail closed with `ValueError`.
Claim ceiling: Claim ceiling: strict UTF-8 decode failure and literal U+FFFD presence only.
  No heuristic mojibake detection, repair, identity collision, missing logical
  surface, reader, projection, supersession, schema, runtime, hook, CI, gate,
  blocker, enforcement, or M2 behavior is authorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L453-L467)

**M0477 · Implement one deterministic report-only exact-byte duplicate detector.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Implement one deterministic report-only exact-byte duplicate detector
  over exactly two independently identified, caller-admitted memory record byte
  payloads.
Claim ceiling: DONE: equal raw bytes produce exactly one `duplicate_memory_entry` warning;
  a one-byte mutation produces zero findings; identical logical input produces
  byte-stable JSON.
Claim ceiling: Claim ceiling: raw-byte SHA-256 equality only. No fixture admission,
  normalization, semantic reconciliation, reader, projection, writer, public
  schema, runtime, hook, CI, gate, blocker, enforcement, historical scan, or
  memory mutation is authorized.
Claim ceiling: The
  detector is active at its report-only claim ceiling.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L487-L500)

**M0494 · Define the M0 fixture-admissibility contract and one synthetic redacted.** Claim ceiling (verbatim):
Claim ceiling: Define the M0 fixture-admissibility contract and one synthetic redacted
  exact-byte-duplicate test fixture with provenance, a complete redaction
  boundary, pinned SHA-256, and fail-closed tests for byte mismatch, missing
  provenance, missing digest, and incomplete redaction.
Claim ceiling: Claim ceiling: contract and one test-only fixture only. No reader, M1a,
  writer/runtime, public schema, hook, CI, gate, enforcement, reconciliation,
  consumer replay, or historical normalization is authorized.
Claim ceiling: The M0
  fixture remains test-only and does not itself prove detector correctness.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L504-L512)

### Authorized solo-owner delivery predicates — 2026-08-24

Scope: prospective exact-head delivery correction. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0461 · Replace the unsupported claim that a solo-owner repository requires a.** Claim ceiling (verbatim):
Claim ceiling: Replace the unsupported claim that a solo-owner repository requires a
  GitHub `APPROVED` review with a canonical conjunctive merge decision:
  exact-head owner merge attestation, exact-head independent technical review,
  green required checks, and preservation of the reviewed head.
Claim ceiling: DONE: contract cases and mutation tests prove that all four predicates are
  required, while GitHub `APPROVED` is optional additional evidence and cannot
  substitute for a missing predicate.
Claim ceiling: Claim ceiling: merge authority and reviewer-facing reporting semantics only.
  No GitHub setting, branch protection, ruleset, CI, runtime, hook, schema,
  gate, blocker, enforcement, or M1b work is authorized.
Claim ceiling: This
  correction is prospective and does not retroactively satisfy that prose gate.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L471-L483)

### Authorized response-readability slices — 2026-07-22

Scope: the separately owner-authorized opt-in readability changes. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0729 · A plain-language response failure has already been observed rather than.** Claim ceiling (verbatim):
Claim ceiling: A plain-language response failure has already been observed rather than
  remaining hypothetical: two comprehension failures required a report rewrite
  before an engineer or the owner could act. This satisfies the
  failure-driven eligibility condition for a separate response-quality slice;
  it does not authorize implementation by itself.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L739-L743)

**M0734 · Owner-authorized on 2026-07-17 and implemented at `61673ca9`: mechanical.** Claim ceiling (verbatim):
Claim ceiling: Owner-authorized on 2026-07-17 and implemented at `61673ca9`: mechanical
  plain-language final-report validation exists as opt-in
  `--check-response-quality` in `response_envelope_validator.py`, requiring
  `conclusion`, `recommended_action`, and `next_action` to be non-empty and
  positioned before `evidence_refs`. Default validator behavior is unchanged,
  and no hook, CI, gate, or default invocation enables the check; enabling it
  anywhere remains a separate owner decision.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L744-L752)

**M0743 · Second failure-driven response-quality slice (owner-authorized.** Claim ceiling (verbatim):
Claim ceiling: Delivered v0.5 regression acceptance remains binding. This adds no gate and does not enable either opt-in check by default.
Claim ceiling: Added opt-in `--check-plain-summary`: `conclusion`,
  `reason`, `next_action` exactly once before `evidence_refs`, each a
  sentence rather than a bare machine token (tokens need a plain-language
  gloss; `next_action: none` rejected). The observed unreadable reply is a
  must-fail regression fixture; the owner's three-line plain version is a
  must-pass fixture. Contract v0.5 records the honest boundary: structural
  proxy only — it raises the probability of readable reports and cannot
  prove comprehension; the real success signal remains direct reader
  feedback. Default behavior unchanged; no hook/CI/gate enables either
  check.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L753-L765)

**M0756 · Third failure-driven owner-summary refinement (owner-authorized.** Claim ceiling (verbatim):
Claim ceiling: Contract v0.6 now makes the
  literal first three non-empty lines `Result / Reason / Next step` (translated
  to the session language), moves technical evidence after that preface, and
  uses actual reader understanding as acceptance. The existing opt-in
  validator remains unchanged; no hook, CI, gate, or default enforcement was
  added.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L766-L773)

**M0991 · Response Envelope Contract v0.2: added Evidence Term Glossing.** Claim ceiling (verbatim):
Claim ceiling: Advisory only; `response_envelope_validator.py`
  unchanged; no gate, no enforcement claim. v0.3 adds the Next-Step Judgment
  required closing section (status / basis / recommended action / cannot-claim)
  for decision-readability; still advisory, validator still unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1001-L1007)

### Authorized no-governance baseline scope — 2026-07-22

Scope: original v1/v2 void states and exact frozen v3 Run 1. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0794 · Slice B voided under owner-approved Pre-Run Amendment 2 (FINAL).** Claim ceiling (verbatim):
Claim ceiling: Slice B voided under owner-approved Pre-Run Amendment 2 (FINAL).
  The first A1 attempt is excluded as a protocol-fidelity failure: its
  writes/validation were blocked by the effective Codex sandbox/policy
  despite the frozen `workspace-write` spec, and it produced no scoreable
  output (scratch repo unchanged at seed `dd34ac3`); receipts are retained.
  The observed voluntary `AGENTS.md` read is handled intent-to-treat: Arm A
  is defined as no harness-injected governance, and voluntary governance-doc
  reads are recorded per run as an observed variable. The Arm B entrypoint
  is now frozen (hook_installer --hooks-only + hook_install_validator
  valid=true).
Claim ceiling: No valid baseline
  run or score exists; continuation requires a separate v2 pre-registration.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L804-L818)

**M0810 · v2 Pre-0 execution-surface qualification passed on the final authorized.** Claim ceiling (verbatim):
Claim ceiling: The v2 experiment is void before Run 1; see
  `docs/status/no-governance-baseline-v2-void-2026-07-10.md`.
Claim ceiling: Under v2's zero-amendment
  rule, no replacement scratch may be improvised. No Codex session, OpenAI API
  transmission, run, score, metric, or attribution conclusion occurred.
Claim ceiling: Future v2 scratch
  repos must be created by the launcher user outside sandbox context;
  qualification does not transfer across launcher or package version.
  v2 locks the successful ICIDP launcher/PFN/AppId/`-PreventBreakaway`, native
  `elevated`, `workspace-write`, and package `26.707.3748.0`; every run must
  retain a matching package check. Scratch roots must be created outside the
  sandbox by launcher user `daish`; no amendment is allowed after the v2 freeze.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L820-L842)

**M0841 · v3 Arm B offline rehearsal completed without an API call. A fresh clone.** Claim ceiling (verbatim):
Claim ceiling: The
  package-context hook path remains untested.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L851-L857)

**M0849 · v3 preregistration frozen from both rehearsed arms at.** Claim ceiling (verbatim):
Claim ceiling: v3 preregistration frozen from both rehearsed arms at
  `docs/governance/no-governance-baseline-v3-preregistration-2026-07-10.md`.
  It binds the baseline/seed/task hashes, launcher/package/provenance locks,
  both arm procedures, and a pre-declared zero-scoreable-output exclusion rule
  for package-context Arm B hook-environment failure. The owner subsequently
  authorized task-prompt and scratch-content transmission for Run 1 only. Arm
  A Run 1 completed through the owner-executed launcher and is archived at
  `docs/status/no-governance-baseline-v3-a1-archive-2026-07-11.md`; its raw
  evidence and poststate are retained, but no metrics, blind review, ledger,
  or attribution conclusion has been created.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L859-L868)

### Authorized bounded P1-C evidence — 2026-07-22

Scope: accepted earlier clean consumer apply and a single natural-session receipt verification. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1357 · P1-C - F-7 external rollout verification with manual PLAN reconciliation.** Claim ceiling (verbatim):
Claim ceiling: P1-C - F-7 external rollout verification with manual PLAN reconciliation
fixture (scoped to `meiandraybook` only; one slice one evidence; do not
claim rollout complete):
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1367-L1369)

**M1361 · Re-scope note (2026-06-12, ratified): P1-C may accept prior.** Claim ceiling (verbatim):
Claim ceiling: Re-scope note (2026-06-12, ratified): P1-C may accept prior
clean-remediation-worktree F-7 apply evidence when the primary consumer
worktree is stale/dirty and re-running apply would create duplicate or
misleading verification evidence. In that case, P1-C scope becomes
post-apply evidence verification, not re-application. Acceptable evidence
sources: meiandraybook origin/main, the 2026-06-11 memory records
(`678c4c9` / `3ddff9d`), framework-side fleet snapshot, and read-only
checks against current remote state. Not acceptable: pull/merge/apply on
the stale primary dirty worktree, bundling stale-worktree cleanup into
P1-C, or re-running the completed apply to manufacture new evidence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1371-L1380)

**M1383 · Verify external repo closeout receipts persist the pinned writer schema.** Claim ceiling (verbatim):
Claim ceiling: Verify external repo closeout receipts persist the pinned writer schema
  and memory-workflow fields: completed by read-only adjudication on 2026-07-22.
  The qualifying natural-session artifact is meiandraybook receipt
  `closeout_receipt_20260722T062442354802Z.json`. The consumer gitlink and
  nested framework HEAD are `8a98df2e`, whose writer emits schema `1.4`; the
  receipt has `schema_version="1.4"` and persists all six close-condition
  surfaces in the same artifact: `memory_workflow_dispatch_ran`,
  `memory_workflow_status`, `memory_workflow_warning_codes`,
  `memory_workflow_blocker_codes`, and `memory_workflow_guard_summary`, plus
  the pinned schema match.
  Natural Stop-hook provenance is external to the receipt's `unknown` identity
  fields: meiandraybook `.claude/settings.json` routes `Stop` to the pinned
  `session_closeout_entry.py`, and the matching Claude session transcript
  records `attachment_type=hook_success`, `hookName=Stop`, `hookEvent=Stop`,
  `cwd=D:\meiandraybook`, and the same session UUID approximately 19 ms after
  receipt creation. No manual receipt was created or replayed for this verdict.
  Separate consumer memory state remains explicit: the receipt reports
  `active_non_canonical_writer=1` and `memory_completion_claim_allowed=false`.
  That blocker prevents a clean consumer memory-completion claim but does not
  invalidate P1-C schema/field persistence or natural Stop-hook provenance;
  its correction requires a separately authorized consumer-memory slice.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1393-L1413)

**M1404 · Keep submodule pointer update reported as stage success only, not F-7.** Claim ceiling (verbatim):
Claim ceiling: Keep submodule pointer update reported as stage success only, not F-7
  completion: accepted evidence shows `full_update_completed` came from full
  surface verification, not pointer-only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1414-L1416)

**M1417 · CAN CLAIM: meiandraybook used as first external F-7 verification target;.** Claim ceiling (verbatim):
Claim ceiling: CAN CLAIM: meiandraybook used as first external F-7 verification target;
  selected F-7 update surfaces verified or explicitly failed; fleet snapshot
  refreshed as evidence; memory_layout alias behavior observed; rollback
  expectation observed; manual reconciliation fixture produced; the 2026-07-22
  natural Stop-hook receipt matches pinned schema `1.4` and persists the P1-C
  memory-workflow close-condition fields.
Claim ceiling: CANNOT CLAIM: F-7 works for all consumers; fleet rollout complete;
  copy-based consumers solved; rollback procedure implemented; blocking
  validator added; automatic PLAN reconciliation solved; primary
  meiandraybook worktree updated; stale dirty worktree resolved; the F-7
  apply was originally executed in this slice; the 2026-07-22 consumer
  closeout gate passed; consumer memory completion was allowed; the separate
  `active_non_canonical_writer` blocker was corrected.
Claim ceiling: Hard limit: on unexpected dirty state, destructive update behavior, or
  ambiguous repo role, stop at diagnosis and report; do not push through
  remaining checklist items. A verification slice must not silently become
  a remediation slice.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1427-L1443)

**M1442 · Verify memory file naming against `memory_layout` aliases during F-7.** Claim ceiling (verbatim):
Claim ceiling: Verify memory file naming against `memory_layout` aliases during F-7
  application: meiandraybook uses `memory/02_tech_stack.md`, compatible with
  both `F7_GOVERNANCE_ALLOWLIST` and `memory_layout` aliases. Divergence
  seed remains latent for consumers using `02_workflow.md`; NOT claimed
  resolved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1452-L1456)

**M1455 · Document rollback procedure for a failed F-7 update / failed smoke.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Updating governance is itself a trust-surface
  change and must be reversible per the core principle (expensive,
  explicit, reversible). (Closed 2026-06-13:
  `docs/fleet/governance-update-rollback.md` — what can / must not be
  auto-rolled-back, pre-rollback evidence capture, execution order with
  clean-worktree stop-at-diagnosis gate, post-rollback verification
  (behind-latest is the correct post-rollback state), and claim ceiling
  after rollback. Grade caveat recorded in the doc: derived from the
  P1-C read-only observation, never execution-tested; the first real
  rollback is its own evidence-producing slice. No rollback executed,
  no updater/F-7/hook/validator change, no consumer repo touched.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1465-L1476)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1457-L1460)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1462-L1463)

### Decision P1-F keep advisory — 2026-07-18

Scope: CLI declaration, historical parsing, four-proxy deferred report and separate runtime path. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1207 · original advisory checkpoint; P1E/P1F status superseded-by M1495/M1634; report status by M1642/M1661 (C11/C12).** Claim ceiling (verbatim):
Claim ceiling: NOT CLAIMED: blocking enforcement (P1-F, separate OP-HC decision),
  deferred-debt report, P1-E FP/FN window completed, PLAN auto-sync,
  retroactive declaration coverage for historical records, or that a
  deferred declaration equals reconciliation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1217-L1226)

**M1471 · Goal: every completion-oriented memory record must declare whether it has.** Claim ceiling (verbatim):
Claim ceiling: Goal: every completion-oriented memory record must declare whether it has
  been reconciled with PLAN, and if not, why not. The gate target is silent
  drift, not deferred drift. This is NOT PLAN auto-sync and must not induce
  agents to edit canonical PLAN to legalize their own completion claims.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1481-L1484)

**M1475 · Add `--plan-reconciliation` field to `governance_tools.memory_record`.** Claim ceiling (verbatim):
Claim ceiling: The first sentence records the historical pre-Option-B writer contract. The following c06014c4 sentence explicitly supersedes its omission behavior; the old behavior is not restored as current permission.
Claim ceiling: Add `--plan-reconciliation` field to `governance_tools.memory_record`
  (2026-06-12): `updated` | `not_applicable` | `deferred:<reason>`;
  at that time, omission was recorded as `not_declared` with a writer
  advisory (never blocks), while malformed values were rejected as input
  errors (exit 2). This historical writer behavior was superseded by P1-F
  Option B at `c06014c4`: the canonical writer now requires an explicit
  declaration and rejects omission with exit 2 before any memory write.
  Historical parsing can still represent older omitted declarations as
  `not_declared`; the writer contract does not make omission a current-diff
  blocker.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1485-L1494)

**M1485 · Deferred reasons validated against the reason taxonomy.** Claim ceiling (verbatim):
Claim ceiling: Deferred reasons validated against the reason taxonomy
  (`requires-human-plan-review`, `awaiting-reviewer-verdict`,
  `scope-split-next-slice`, `canonical-update-not-authorized`,
  `dirty-workspace-prevents-safe-edit`); empty or vacuous reasons
  (`later` / `todo` / `pending` / `soon` / `TBD`) rejected. Taxonomy
  extension is PR-only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1495-L1500)

**M1491 · Pre-push advisory implemented on the current-date memory gate seam:.** Claim ceiling (verbatim):
Claim ceiling: Pre-push advisory implemented on the current-date memory gate seam:
  reports session-derived records in today's memory file lacking a
  declaration; advisory only, never blocks.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1501-L1504)

**M1495 · P1-E: collect 2-4 weeks of false-positive / false-negative samples.** Claim ceiling (verbatim):
Claim ceiling: All 44 `not_declared` records
  are classified: 14 absent-field on the introduction day plus 30
  advisory-era literal `not_declared` produced by the pre-Option-B
  canonical writer's omission normalization; every one is canonical-writer
  output legal at write time, and the last is dated 2026-07-10 — the day
  before Option B (`c06014c4`) made the CLI declaration mandatory.
Claim ceiling: FP/FN conclusion (corrected 2026-07-18
  after review): treating advisory-era literals as violations would be
  false positives; no false negatives observed in the sample, but Option B
  covers the CLI entry point only — `build_session_derived_record()` still
  defaults to `not_declared` and the runtime `session_end` hook calls it
  without a declaration, so that path can still emit `not_declared` and is
  unobserved, not eliminated. As of this checkpoint there is no observed
  failure driver for a current-diff blocker; the Option B CLI contract is
  sufficient for the CLI path observed in this window. Whether the runtime
  path needs the same treatment is a separate failure-driven,
  owner-authorized question. This closes P1-E collection only. P1-F was
  subsequently decided on 2026-07-18: maintain advisory and add no
  current-diff blocker; reopen only after a natural post-Option-B
  `not_declared` failure.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1505-L1550)

**M1634 · P1-F decided 2026-07-18 by owner: maintain advisory and do not add a.** Claim ceiling (verbatim):
Claim ceiling: P1-F decided 2026-07-18 by owner: maintain advisory and do not add a
  current-diff blocker.
Claim ceiling: The runtime
  `session_end` path can still emit `not_declared`, but no natural
  post-Option-B failure has been observed; a current-diff blocker is not a
  substitute for a writer-path fix. Reopen a separate failure-driven slice
  only if a natural post-Option-B `not_declared` record appears. This
  decision does not claim the runtime writer path is fixed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1644-L1651)

**M1642 · Add a non-blocking deferred-debt report (deferred count by reason,.** Claim ceiling (verbatim):
Claim ceiling: Historical observed input-quality gap in the 2026-06-13 report, not a new blocker. M1661 narrows semantic PLAN-touched detection to four proxies only; it does not supersede this decode caveat. Whether those two files were repaired later requires new evidence; no present-day corruption claim is made.
Claim ceiling: (Implemented 2026-06-13 exactly per the checkpoint below:
  `governance_tools/deferred_debt_report.py`, read-only, deterministic
  given `--as-of`, json/human stdout, optional `--output`; the four
  checkpoint observables only; pre_field guard verified by a dedicated
  test; historical non-UTF-8 daily files (2026-04-10, 2026-05-04)
  surfaced as `files_with_decode_errors` via lossy decode — observed,
  not repaired. 12 focused tests passed; adjacent memory_record /
  memory_workflow 23 tests passed. First real-repo run as-of
  2026-06-13: updated=18, deferred=0, not_declared=14 (oldest
  2026-06-12, matching the P1-E first data point), pre_field=249,
  malformed=0. No CI wiring, no thresholds, no gate semantics, no
  historical record rewritten.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1652-L1666)

**M1661 · Report scope (exactly four observables, all machine-decidable from.** Claim ceiling (verbatim):
Claim ceiling: Report scope (exactly four observables, all machine-decidable from
  record fields):
  1. count of session-derived records by `plan_reconciliation` value
     (`updated` / `not_applicable` / `deferred:<reason>` /
     `not_declared`);
  2. deferred breakdown by taxonomy reason;
  3. oldest age per deferred reason (days since record's file date);
  4. `not_declared` count and oldest age (the silent class the gate
     targets).
Claim ceiling: Explicitly OUT of report scope: semantic detection of "PLAN-touched
  records without `updated`". Whether a record's work touched PLAN is
  not machine-decidable from record fields; `not_declared` and
  `deferred` are the observable proxies. The original PLAN wording is
  narrowed to these proxies; semantic detection would require content
  analysis and is not claimed.
Claim ceiling: Input source: canonical daily memory files `memory/YYYY-MM-DD.md`
  only, parsed with the same record format the memory workflow uses.
  Records pre-dating the field (before 2026-06-12) are bucketed as
  `pre_field` and are NOT debt — they are expected history, consistent
  with the P1-E first data point (14 of 15 same-day records pre-dated
  the field).
Claim ceiling: Output format: read-only tool, `--format json|human` to stdout,
  optional `--output <path>`; deterministic given the same inputs; no
  ledger append, no artifact mutation by default (no-write discipline).
Claim ceiling: Claim ceiling: observation-class only. A deferred declaration with a
  taxonomy reason is a legal honest state, not a failure; a
  `not_declared` is advisory-era data, not a violation; the report has
  no thresholds, no pass/fail, and is not a gate input. It may later be
  cited as evidence by the P1-F decision but cannot close P1-E or
  authorize blocking by itself.
Claim ceiling: Implementation slice (when opened): `governance_tools/`
  read-only tool plus focused tests; non-goals pre-declared — no
  validator change, no CI wiring, no blocking semantics, no thresholds,
  no auto-cleanup, no rewriting or reclassifying historical records.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1671-L1704)

**M1698 · Decide whether any CI or hook path should opt into `--fail-on-blocker`:.** Claim ceiling (verbatim):
Claim ceiling: Decide whether any CI or hook path should opt into `--fail-on-blocker`:
  CI workflow path only, current-diff scope.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1708-L1709)

**M1700 · Preserve default advisory mode unless current-diff blocker false-positive.** Claim ceiling (verbatim):
Claim ceiling: Preserve default advisory mode unless current-diff blocker false-positive
  rate is acceptable: hooks remain advisory.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1710-L1711)

- [x] **M1702 · Do not upgrade historical `missing_canonical_memory` or `unbound_memory`.** Claim ceiling (verbatim):
  Claim ceiling: Do not upgrade historical `missing_canonical_memory` or `unbound_memory`
  warnings into blockers without separate approval: preserved, warning-only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1712-L1713)

### Decision fleet evidence-duty and freshness — 2026-06-12

Scope: four independently maintained evidence-duty scopes and event-driven freshness. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1220 · CLAIMED: four scope sets defined by evidence duty with membership.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: four scope sets defined by evidence duty with membership
  criteria; meiandraybook classified (f7_consumer + submodule_consumer,
  not fleet); hardcoded fleet enumeration explicitly accepted with a
  named re-evaluation trigger; manifest-driven generator deferred,
  failure-driven.
Claim ceiling: NOT CLAIMED: fleet coverage complete, all consumers monitored,
  copy-based consumer update path solved, scope manifest implemented,
  or repo-class freshness SLA defined.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1230-L1237)

**M1231 · CLAIMED: event-driven freshness policy adopted; refresh via the.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: event-driven freshness policy adopted; refresh via the
  registered generator required before rollout / release / external
  claims citing fleet state; `required_verified` ratio defined as
  freshness-window evidence.
Claim ceiling: NOT CLAIMED: fleet health restored, continuous monitoring, weekly
  cadence, repo-class SLA, or that idle-period decay is a defect.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1241-L1246)

**M1556 · Reproduction verified: registered tool regenerated the fleet matrix.** Claim ceiling (verbatim):
Claim ceiling: Claim boundary — CLAIMED: fleet matrix generation is reproducible
  through a registered, attributable tool. NOT CLAIMED: fleet evidence
  fresh, refresh cadence solved, monitored repo set correct, fleet
  health restored, or meiandraybook in scope.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1566-L1571)

**M1565 · Decision: event-driven (Option A adopted now; Option C repo-class SLA.** Claim ceiling (verbatim):
Claim ceiling: Decision: event-driven (Option A adopted now; Option C repo-class SLA
deferred; Option B weekly scheduler rejected for now).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1575-L1576)

**M1573 · Semantics defined: `required_verified` ratio is freshness-window.** Claim ceiling (verbatim):
Claim ceiling: Semantics defined: `required_verified` ratio is freshness-window
  evidence (a time-window observation), NOT a permanent health score.
  A low ratio after an idle period is expected decay.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1583-L1585)

**M1576 · Policy adopted: fleet freshness is event-driven. A fleet matrix.** Claim ceiling (verbatim):
Claim ceiling: Policy adopted: fleet freshness is event-driven. A fleet matrix
  refresh via the registered generator is REQUIRED before rollout,
  release, or any external presentation claim that cites fleet state.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1586-L1588)

**M1579 · Weekly scheduler explicitly rejected for now: ritual-refresh risk,.** Claim ceiling (verbatim):
Claim ceiling: Weekly scheduler explicitly rejected for now: ritual-refresh risk,
  background-execution claim burden, and missed-run semantics cost —
  the same boundary class as manual/resume-triggered reviewer polling.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1589-L1591)

**M1588 · Each scope is defined by what a member repo's evidence must prove, not by.** Claim ceiling (verbatim):
Claim ceiling: Each scope is defined by what a member repo's evidence must prove, not by
where the repo happens to live:
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1598-L1599)

**M1591 · `fleet_scope`: repos whose governance state feeds the freshness matrix.** Claim ceiling (verbatim):
Claim ceiling: `fleet_scope`: repos whose governance state feeds the freshness matrix.
  Membership criteria: locally checked out where the registered generator
  runs; governance surfaces adopted or onboarding-tracked; cited by
  release / rollout / external claims. Evidence duty: freshness-window
  matrix (event-driven per P1-H).
Claim ceiling: `submodule_consumer_scope`: any repo consuming the framework through a
  git submodule. Evidence duty: framework.lock / submodule pointer
  currentness only.
Claim ceiling: `f7_consumer_scope`: subset of submodule_consumer_scope receiving
  managed F-7 full updates (AGENTS keyed sections, managed hooks, memory
  workflow router). Evidence duty: per-update F-7 apply / verification
  evidence, event-driven.
Claim ceiling: `external_contract_repo_scope`: repos providing domain contracts that
  the framework consumes. Evidence duty: contract validation evidence,
  event-driven.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1601-L1615)

**M1607 · Set relations: f7_consumer is a subset of submodule_consumer; fleet may.** Claim ceiling (verbatim):
Claim ceiling: Set relations: f7_consumer is a subset of submodule_consumer; fleet may
intersect any other set (observed today: Kernel-Driver-Contract,
verilog-domain-contract, and writing-contract are simultaneously fleet
members and contract repos). Membership in one set does not inherit the
evidence duties of another.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1617-L1621)

**M1615 · meiandraybook classified: f7_consumer_scope and.** Claim ceiling (verbatim):
Claim ceiling: meiandraybook classified: f7_consumer_scope and
  submodule_consumer_scope; NOT fleet_scope — and the taxonomy does not
  require it there, because its claims are update-evidence-based
  (pointer currentness + F-7 verification), not freshness-matrix-based.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1625-L1629)

**M1620 · hardcoded-in-tool repo set: ACCEPTED for now as the operational.** Claim ceiling (verbatim):
Claim ceiling: hardcoded-in-tool repo set: ACCEPTED for now as the operational
  enumeration of fleet_scope (single operator environment; set stable
  since 2026-05-25; self-declared in snapshot metadata). Re-evaluation
  trigger: the first taxonomy-driven membership change request, or a
  second operator environment.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1630-L1634)

### Authorized per-surface publication decisions — 2026-06-13

Scope: exact C3 description and separately gated topics/badge/release surfaces. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1252 · original publish checkpoint; C3-edit status superseded-by M1762/M1918 only.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: per-surface publish decision checkpoint canonicalized —
  description and topics allowed only after exact-text ratification
  under a mechanism-only ceiling; badge deferred until the first gated
  release; release publish remains gated; prohibited wording classes
  recorded; publish text may never claim above the README capability
  table.
Claim ceiling: NOT CLAIMED: any publish surface edited, any release published, any
  badge added, promotion readiness, or that P2 core documentation
  completion equals public-promotion ready.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1262-L1270)

**M1762 · C3 ratification/application record dated 2026-06-13; not a new remote-metadata observation.** Claim ceiling (verbatim):
Claim ceiling: (P2-G closed 2026-06-13:
  ratified C3 string applied manually by the user in the GitHub web UI —
  no authorized agent-side metadata write path existed and none was
  created; agent verification via unauthenticated GET
  /repos/Gavin0099/ai-governance-framework returned exact_match=True
  against the PLAN-recorded string, em dash intact, repo
  updated_at=2026-06-12T16:44:24Z.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1772-L1778)

**M1773 · Align README capability table with current reality: mutation topology.** Claim ceiling (verbatim):
Claim ceiling: (P2-A 2026-06-12:
  table gained a Claim class axis — Enforced / Advisory / Observation /
  Cannot claim — with definitions; MEM-DISPATCH row added as Advisory +
  selective Enforced scoped to current-diff `active_non_canonical_writer`;
  stale "10 required repos verified" wording removed; positioning sentence
  now present in both ZH and EN sections.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1783-L1790)

**M1781 · State in README that the fleet freshness ratio is time-window.** Claim ceiling (verbatim):
Claim ceiling: State in README that the fleet freshness ratio is time-window
  evidence under an event-driven refresh policy, not a permanent health
  score (prevents idle-period decay being read as regression).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1791-L1795)

**M1786 · original English-readability review; named four-section asymmetry superseded-by M1823 only.** Claim ceiling (verbatim):
Claim ceiling: Closure scope: this closes the
  README English review pass only — English readability + claim-class
  consistency. NOT claimed: bilingual content parity. The English README
  half contains sections newer/more complete than the Chinese half
  (Agent Runtime Governance Profile, Governance Artifact Discipline Index,
  f7 Key-Documents row, one-line apply prompt); that asymmetry is a
  bilingual-content gap, not an English-readability failure, and any
  parity repair is a separate slice.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1796-L1805)

**M1796 · Reviewer entry doc `docs/REVIEWER_ENTRYPOINT.md` created: claims /.** Claim ceiling (verbatim):
Claim ceiling: Reviewer entry doc `docs/REVIEWER_ENTRYPOINT.md` created: claims /
    non-claims / evidence required for done / advisory-vs-enforcement
    reading rules; linked from README Key Documents (ZH+EN). Bounded by
    PLAN Active Claim Boundaries with explicit PLAN-wins precedence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1806-L1809)

**M1800 · Starter-pack English review pass. (P2-D 2026-06-12: full English.** Claim ceiling (verbatim):
Claim ceiling: (P2-D 2026-06-12: full English
    mirror section added to `examples/starter-pack/README.md`; adoption
    model alignment note added in both languages — copying starter-pack
    files does not make a repo a governed consumer; upgrade path is
    submodule adoption.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1810-L1814)

**M1805 · Onboarding SOP English review pass. (P2-D 2026-06-12: SOP scoped.** Claim ceiling (verbatim):
Claim ceiling: (P2-D 2026-06-12: SOP scoped
    to the submodule-consumer path; Step 0 classification gate added per
    `docs/ADOPTION_MODEL.md` with copy-based stop rule; internal GitLab
    hostname replaced with `<framework-remote-url>` placeholder; claim
    ceiling section added — onboarding evidence only, no fleet or
    currentness claims.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1815-L1820)

**M1811 · README English review pass. (Done 2026-06-13. Dedicated English.** Claim ceiling (verbatim):
Claim ceiling: Dedicated English
    readability + claim-class consistency pass over the README English
    half: ten-row capability table reviewed — Status / Claim class
    identical across both language halves, no claim drift; all claim
    ceilings intact (audit-not-security-boundary, single-point E1-B
    Phase 2 / mutation protection not claimed, copy-based unsupported,
    Agent Runtime Profile not-X clauses, freshness not-a-health-score).
Claim ceiling: NOT
    claimed: all English docs reviewed, bilingual parity completed,
    README perfect, content symmetry achieved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1821-L1832)

**M1823 · README bilingual content parity. (Done 2026-06-13. Commits.** Claim ceiling (verbatim):
Claim ceiling: Four English-only sections mirrored to Chinese
    half: one-line apply prompt, f7 key-documents row, Agent Runtime
    Governance Profile with all seven claim-ceiling clauses, Governance
    Artifact Discipline Index.
Claim ceiling: Verdict: ACCEPT_WITH_CAVEATS.
Claim ceiling: NOT claimed: full bilingual
    symmetry, complete content parity, or any runtime guarantee
    expansion.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1833-L1845)

**M1843 · Governing rule: publish surfaces (GitHub description, topics, badges,.** Claim ceiling (verbatim):
Claim ceiling: Governing rule: publish surfaces (GitHub description, topics, badges,
release notes) are claim amplifiers — they are read as first-impression
self-claims with no Claim class column attached. No publish-surface text
may claim above the README capability table; on conflict, the table and
the Active Claim Boundaries win.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1853-L1857)

**M1849 · Prohibited wording classes on any publish surface: "solved", "fully.** Claim ceiling (verbatim):
Claim ceiling: Prohibited wording classes on any publish surface: "solved", "fully
automated", "production-ready", "secure" / "security boundary",
"fleet-ready" / "fleet rollout complete", "supports all repos",
"automatic adoption" / "automatic updates", and any wording that
contradicts the audit-framework-not-security-boundary positioning or
the copy-based audit-only classification.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1859-L1864)

**M1858 · GitHub description: ALLOWED, gated on exact-string ratification.** Claim ceiling (verbatim):
Claim ceiling: GitHub description: ALLOWED, gated on exact-string ratification.
  Ceiling: mechanism description only (contract-bound execution,
  artifact-backed verification, fail-closed decisions); no outcome
  claims. The exact string is the deliverable of its own slice and must
  be recorded in PLAN before applying.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1868-L1872)

**M1863 · GitHub topics: ALLOWED, gated on exact-list ratification. Ceiling:.** Claim ceiling (verbatim):
Claim ceiling: GitHub topics: ALLOWED, gated on exact-list ratification. Ceiling:
  descriptive taxonomy nouns only; no maturity-, guarantee-, or
  scale-implying topics.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1873-L1875)

**M1869 · Release publish: remains GATED by the existing canonical rule.** Claim ceiling (verbatim):
Claim ceiling: Release publish: remains GATED by the existing canonical rule
  (accurate release notes and claim ceiling first), plus the Claim class
  taxonomy / reviewer-entrypoint linkage requirement above.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1879-L1881)

**M1873 · Activation rule: each ALLOWED surface still requires its own slice whose.** Claim ceiling (verbatim):
Claim ceiling: Activation rule: each ALLOWED surface still requires its own slice whose
deliverable is the exact text or list, checked against this ceiling and
user-ratified before the edit is applied. "P2 core documentation
calibration complete" does not equal "public promotion ready".
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1883-L1886)

**M1881 · Ratified final GitHub description (exact string):.** Claim ceiling (verbatim):
Claim ceiling: Ratified final GitHub description (exact string):
Claim ceiling: Audit framework for AI-assisted engineering: contract-bound
    execution, artifact-backed verification, fail-closed decisions
    — not a security boundary.
Claim ceiling: (Single line when applied; wrapped here for PLAN readability.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1891-L1897)

**M1889 · Ratified claim ceiling: mechanism-only. The description may describe.** Claim ceiling (verbatim):
Claim ceiling: Ratified claim ceiling: mechanism-only. The description may describe
the framework's audit/governance mechanisms but must not imply security
coverage, fleet readiness, automatic adoption, or production
completeness.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1899-L1904)

**M1918 · Ratification rule (satisfied 2026-06-13): exactly one candidate.** Claim ceiling (verbatim):
Claim ceiling: Ratification rule (satisfied 2026-06-13): exactly one candidate
(possibly amended) must be ratified by the user; the ratified string is
recorded above as final.
Claim ceiling: Topics remain a
separate slice (P2-H) — they are not bundled, because topic words like
"security" / "automation" / "ci" can re-amplify claims independently.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1928-L1933)

### Authorized Gate 3 diagnostic scope — 2026-08-13

Scope: the consumed NON_SUCCESS pair and distinct offline diagnostic/design/capture tranches. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2053 · Gate 3 NON_SUCCESS pair-final manifest promoted 2026-08-11.** The.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: The one authorized pair ran once on 2026-08-11 and terminated `NON_SUCCESS`:
  both arms exited zero but produced no final message and left the calibrated
  workspace unchanged. Public pair-final SHA-256 is
  `8201b7c1331b1b91dccf528ff79b5b020ef295b9c5aac25c4eac51ca3dbb9722`;
  the public bytes in evidence commit `53fc93f7` were internally coherent, but
  independent review found that its exact Git tree omitted three contract-
  required empty runtime directories. Repair commit `230679cf` adds a checkout
  materializer that restores only those empty directories before delegating to
  the unchanged frozen verifier.
Claim ceiling: Public
  evidence confirms task-execution failure in both arms because `result.txt`
  stayed at the `PENDING\n` baseline. The nearer cause of the absent final
  message remains unresolved between CLI final-output production and model
  completion because raw NDJSON event types were not published. Retry,
  replacement, counted execution, other interpreters, and any treatment or
  Skill-effect conclusion remain unauthorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2063-L2093)

**M2085 · Gate 3 final-message diagnostic offline tranche completed.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: **Gate 3 final-message diagnostic offline tranche completed
  2026-08-12.** Implementation commit `7c1c42e0` adds only the pure in-memory
  synthetic classifier and its focused tests.
Claim ceiling: This tranche
  does not integrate a lifecycle observer or evidence publication, does not
  use credentials or authorize preflight/live, does not reuse the consumed
  pair, and does not change its `NON_SUCCESS` result or establish Gate 3 or
  treatment effectiveness.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2095-L2106)

**M2111 · Gate 3 final-message diagnostic offline integration completed.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: **Gate 3 final-message diagnostic offline integration completed
  2026-08-13.** Implementation commit `e3b70173` adds the synthetic retained-
  fixture lifecycle observer, create-once store, pre-cleanup seal/cleanup/
  receipt chain, route and external recovery profiles, privacy verifier, and
  crash/TOCTOU fail-closed behavior.
Claim ceiling: This milestone is
  synthetic and offline only: no credentials, preflight, live execution, old-
  pair reuse, retry, or replacement occurred or is authorized; the consumed
  pair remains `NON_SUCCESS`, and no Gate 3 success or treatment/Skill-effect
  conclusion is established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2121-L2134)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2108-L2119)

**M2126 · Gate 3 actual-capture adapter design accepted 2026-08-13.** Design.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: **Gate 3 actual-capture adapter design accepted 2026-08-13.** Design
  commit `420a7f42` records the independently approved private-stdout parser
  ACL, privacy-safe lifecycle projection, create-once capture evidence links,
  crash/TOCTOU fail-closed plan, and minimal offline implementation tranche at
  exact SHA-256
  `6d52ecda73c542e300c1612a712beb38c4ce7b44a66e5335965d254052905a34`.
Claim ceiling: The public claim ceiling is limited to internally linked adapter
  reports and `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`; it does not
  prove correspondence to private stdout, executable provenance, lifecycle
  truth, model completion, or final-answer production.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2136-L2150)

**M2142 · Gate 3 actual-capture adapter minimal offline tranche completed.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: **Gate 3 actual-capture adapter minimal offline tranche completed
  2026-08-13.** Implementation commit `25a9da65` adds only the pure private
  NDJSON parser ACL, privacy-safe lifecycle projector, closed public capture
  artifacts, create-once synthetic publisher/verifier behavior, and focused
  offline tests.
Claim ceiling: This tranche
  does not wire `CodexExecRunner`, prove correspondence between private stdout
  and public markers, use credentials, run preflight/live, or reuse, retry, or
  replace the consumed pair. The public positive claim remains
  `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`; the consumed pair remains
  `NON_SUCCESS`, and Gate 3 or treatment/Skill success is not established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2152-L2166)

**M2158 · Gate 3 runner/capture integration minimal offline tranche completed.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: **Gate 3 runner/capture integration minimal offline tranche completed
  2026-08-13.** Implementation commit `854fef93` adds only the injected
  contained-process runner seam, authorization-consumed launch ordinal, single
  stdout handoff, private runtime TOCTOU checks, mutually exclusive evidence
  profiles, seal-before-cleanup chain, create-once cleanup continuation, and
  focused synthetic regressions.
Claim ceiling: The reviewed
  design basis is preserved retrospectively in commit `dc76c293` at exact
  SHA-256 `d0d1609bc111bb8cef28f8442f80beddeb6ad87744be9e74723d3e11126a19fd`;
  this does not establish that the design was repository-available or committed
  authority before implementation commit `854fef93`.
  This tranche uses injected synthetic results only: it does not wire or launch
  the real runner, prove private-stdout correspondence or execution provenance,
  use credentials, run preflight/live, or reuse, retry, or replace the consumed
  pair. The public claim ceiling remains
  `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`; the consumed pair remains
  `NON_SUCCESS`, and Gate 3 or treatment/Skill success is not established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2168-L2188)

### Decision Group A production prerequisites — 2026-08-14

Scope: synthetic contract v2 and mapping-only bridge. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2180 · Gate 3 real-runner contained-result bridge design accepted 2026-08-13.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 real-runner contained-result bridge design accepted 2026-08-13.**
  Design commit `013f227a` records the `_ContainedResult` to
  `InjectedContainedResult` mapping, the single stdout handoff, stderr exclusion,
  non-interference with `CodexExecRunner.__call__` and `TrustedLiveRunner`, the
  launch-authority/TOCTOU/capture ordering, the fail-closed disposition mapping,
  and a mapping-only offline tranche, at exact SHA-256
  `5e0279c9115f9f4eb47f3e2fd713091c58e8028be9bc6760ca5f462a21e7a015`.
  Exact-digest read-only review returned `APPROVED` with zero open findings after
  three earlier revisions were rejected; the superseded digests `ed7807d6…`,
  `71a6943d…` and `6c3552e2…` are not approval targets. No GitHub review record
  exists for the pull request; this acceptance is the owner's.
Claim ceiling: This checkpoint accepts design bytes only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2190-L2210)

**M2202 · Gate 3 Group A runner integration contract v2 completed 2026-08-14.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 Group A runner integration contract v2 completed 2026-08-14.**
  Delivered as three reviewed commits on one branch, because A1 and A2 are
  transitional states that must not be recorded as mainline milestones: `38991f35`
  freezes the v1 contract as a literal and identifies contract version from exact
  bytes before any authority validation; `7c0ee75e` adds the v2 contract literal,
  `RuntimeAuthorityV2`, `bridge_blob`, `bridge_source`, `workspace_baseline_sha256`
  and per-version validator dispatch while leaving v2 unverifiable; `3ca52b49`
  activates v2, moves workspace observation from the bridge to the coordinator and
  implements the claim ladder.
Claim ceiling: Claim ceiling: v2 admits `evidence_class = SYNTHETIC` and rejects `PRODUCTION`,
  because `invoke` is an injected callable and a declared class would be caller
  intent rather than execution provenance. Public v2 bytes reach only
  `BASELINE_DIGEST_DECLARED`; a matching private map supplied out of band reaches
  `SUPPLIED_BASELINE_MAP_MATCHES_DECLARED_DIGEST`. **No arrangement of inputs
  establishes that a run performed the baseline comparison**, and no artifact,
  claim token, plan entry or memory record may say so. The oracle fixture is
  runtime-independent of the production modules and its values were independently
  re-derived; serializer reuse is not detectable and is not claimed to be.
  Group A closes two of the five production-wiring preconditions — bridge-source
  runtime binding and workspace-baseline authority. The remaining three are a
  pre-seal credential-residue recovery contract, a structural non-`repr` boundary
  and machine-enforced path exclusivity. This tranche does not wire or launch the
  real runner, use credentials, run preflight or live, or reuse, retry or replace
  the consumed pair; the consumed pair remains `NON_SUCCESS`, and Gate 3 or
  treatment/Skill effectiveness is not established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2212-L2249)

**M2241 · original v1 mapping-only bridge; bridge/baseline authority superseded-by Group A v2 / M2202 (C13).** Claim ceiling (verbatim):
Claim ceiling: The tranche maps `_ContainedResult` to `InjectedContainedResult`, drops
  `returncode` on the timeout path because a non-`EXITED` disposition requires a
  null exit code, sets `stderr` empty rather than forwarding it, treats
  incomplete process-tree termination as a closed error rather than a
  `TERMINATED` row, and refuses to claim `START_FAILED` from an unattributable
  failure, accepting a consumed launch ordinal instead.
  Claim ceiling: mapping characterization only. The bridge source is not a
  `RUNTIME_SUBJECTS` member and claims no runtime authority; the workspace
  baseline is a caller-supplied synthetic fixture, so its `CHANGED`/`UNCHANGED`
  verdict is not public evidence about a real workspace; and the preparation
  test asserts only that an in-memory fake ran, which is not credential-write
  detection. Both the contained call and private preparation are injected fakes.
  This tranche does not wire or launch the real runner, use credentials, run
  preflight or live, or reuse, retry or replace the consumed pair.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2251-L2276)

### Authorized historical-materialization scope — 2026-08-19

Scope: N1–N3, M1–M3 bounded native/materialization designs and delivered implementation tranches. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2268 · Gate 3 historical materialization M1 completed 2026-08-15.** Claim ceiling (verbatim):
Claim ceiling: M1 establishes which authority a historical
  reconstruction may derive from; it materializes nothing and reads no
  credentials.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2278-L2284)

**M2276 · Gate 3 native handle-boundary design, ADR-0001 and ABI.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 native handle-boundary design, ADR-0001 and ABI
  characterization accepted 2026-08-15.** Design commit `1c78de39` records why
  the Windows standard library cannot bind a directory ancestor: this CPython
  reports `os.supports_dir_fd == []` and offers no `O_NOFOLLOW`, no
  `O_DIRECTORY` and no directory file descriptor, so an ancestor replaced by a
  junction between check and use cannot be excluded by stdlib means. ADR-0001
  exact SHA-256 is
  `ec6d9acaca40b90502d099938680a3d0789bf3f37eaa4f7119310ca2e332dc58`; it
  records the `ARCHITECTURE.md` §6.2 conflict check, decisions D1-D9, eight
  owner rulings verbatim, and a four-row deviation register including the
  slice-specific `NATIVE-INTEROP.md` §4.1 exception. The owner ruling for that
  exception is recorded in ADR-0001 and is not generalized to other native
  slices.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2286-L2298)

**M2290 · Gate 3 native ABI expected-layout oracle completed 2026-08-15.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 native ABI expected-layout oracle completed 2026-08-15.**
  Commit `c4c7e14e` adds an extractor that derives the expected structure
  layout from pinned Windows SDK headers rather than from the running
  interpreter, so the measurement it checks is not also its own oracle.
Claim ceiling: The
  package digest is verified before the archive is opened, a closed nine-entry
  header inventory and a closed fourteen-key provenance schema are enforced,
  and the artifact declares `measurement_class = computed-not-compiled` because
  no compiler ran. Coverage differs by stage and must not be collapsed: the
  SDK artifact derives eleven layouts; the earlier characterization measured
  nine of them, so `EXCEPTION_RECORD` and `OSVERSIONINFOEXW` are values the
  oracle supplied rather than values it confirmed; and it is the N1 layout gate
  that later checked all eleven ctypes declarations against the artifact.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2300-L2316)

**M2308 · Gate 3 native boundary tranches N1, N2, N3a and N3b completed.** Claim ceiling (verbatim):
Claim ceiling: `SUPPORTED_MACHINES` admits
  `AMD64` only, because ARM64 was never verified and admitting it would have
  been an unverified claim.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2318-L2329)

**M2321 · Gate 3 native boundary N3c-1 completed 2026-08-16.** Implementation.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 native boundary N3c-1 completed 2026-08-16.** Implementation
  commit `1486fdb5` pins every component from the volume root down to `base`,
  each open handle-relative to the one above it, so no component is ever
  re-resolved by name.
Claim ceiling: The pin comes from omitting `FILE_SHARE_DELETE`, not from requesting `DELETE`
  on a borrowed directory, and revision 17's role-1 mask is what makes the
  required reparse-tag check possible at all.
Claim ceiling: Claim ceiling: this tranche opens and holds directory handles and does
  nothing else. It creates, renames and removes nothing;
  `NtCreateFile`, `SetFileInformationByHandle`, `WriteFile` and
  `GetVolumeInformationByHandleW` remain bound and uncalled, asserted
  structurally. `handle_boundary_available()` and `ACTIVE` are both `False`, so
  no production path reaches it. N3c-2 — creation, deletion and the absence
  probe — was not authorized at that point and did not follow from this
  approval; it was authorized separately, designed and delivered afterwards,
  recorded below. The consumed pair remains `NON_SUCCESS`, and Gate 3 or
  treatment/Skill effectiveness is not established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2331-L2367)

**M2359 · Gate 3 M3-b blockers taken 2026-08-19.** Merged to `main` as `f802dba4`.** Claim ceiling (verbatim):
Claim ceiling: The original BLOCKED-1/2/3 identities below are the antecedents of "Two" and "The third"; the accepted historical amendments and later BLOCKED-3 closure remain distinct, with no new permission.
Claim ceiling: **Gate 3 M3-b blockers taken 2026-08-19.** Merged to `main` as `f802dba4`
  (PR #76): BLOCKED-1 `fa10dda8`, BLOCKED-2 `4ea55d3e`, BLOCKED-3 `95838ac0`,
  after the record reconciliation `09597ace`. Two are amendments made under
  explicit human authorization. The third is not an amendment: **merging did not
  close BLOCKED-3**, which was in `main` and still OPEN at that checkpoint; it
  was later closed after acceptance of `95838ac0` and measured layouts in
  `fe44deb4`.
  **BLOCKED-1 — executable authority widens by one module.**
  `RUNTIME_MODULE_ALLOWLIST` is five in both frozen copies, adding
  `gate3_route_v2_ab_candidate.py`: the module whose execution *is* the
  reconstruction, since `build_contract_manifest()` and `build_candidate_set()`
  live in it. Loading it from the pinned commit rather than calling the present
  one is the difference between reconstructing history and re-running the
  present.
Claim ceiling: A literal pin outside the module now fixes the five paths,
  the count, their uniqueness and the sorted order the wire depends on, so a
  sixth requires an edit a reviewer reads.
Claim ceiling: The
  36-mutation battery from `cfa2c1ec` was **not** re-run: that harness was
  session-local and is not in the repository, so this carries no mutation
  evidence.
  **BLOCKED-2 — two checks are retired, and that is a contract change.** The
  amendment is made in its own authority document, the historical evidence
  materialization design, now revision 11, as step 9:
  `_verify_source_commit_inputs` and `_verify_byte_preservation_attributes` are
  not part of the reconstruction path and are not reimplemented on it.
Claim ceiling: What must not be
  claimed downstream is that the reconstruction performs these checks or an
  equivalent; it performs neither and relies on an earlier link. The parent-side
  result object carrying the two "not asserted" markers is **not** written —
  that is M3-b-3.
Claim ceiling: Two findings came out of following the requirement
  to its end: the surface is **fourteen calls and four owned resources**, not
  eight and three, because bounding what the child inherits needs
  `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` and its attribute list — the one resource
  whose leak is silent; and the obvious shortcut, `bInheritHandles = FALSE` with
  handles set in `STARTUPINFOW`, produces a child with no usable stdin.
  Claim ceiling: BLOCKED-1 authorizes a fifth module to be loaded and loads
  nothing.
Claim ceiling: BLOCKED-3 binds no symbol, starts no process and creates no job.
  `ACTIVE` stays `False`, no availability predicate moved, nothing calls in, and
  no committed tranche executes historical code.
Claim ceiling: The consumed pair
  remains `NON_SUCCESS`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2369-L2433)

**M2425 · M3-b-1/decoder and original native design; old call/resource inventory superseded-by M2359.S21; wait states by M2734/M2745.** Claim ceiling (verbatim):
Claim ceiling: **BLOCKED-3**: the process-control
  surface is a second native boundary, and naming its Win32 calls is not
  specifying it; `NATIVE-INTEROP` requires layouts, ownership, unwind and error
  translation first, for a surface with eight calls, three kinds of handle and
  at least six ways to fail.
  M3-b-1 is therefore only the machinery the other two tranches sit on, built
  where nothing executes it: the closed loader over the verified buffer map and
  the `GATE3HR\0` return frame, in-process, no spawn, no native call, no
  historical import. The loader is a `MetaPathFinder` returning `None` for every
  name outside its inventory, so the standard library resolves normally; a
  stdlib allowlist is deliberately absent, because it would have to be
  maintained against a standard library older than the code importing from it.
  The return frame is deliberately not the inbound format, carries four
  required labels and no paths, and both its digest labels are recomputed
  rather than trusted.
Claim ceiling: **Metadata a module can grant itself is not authority**: loader ownership
  accepted any loader the finder had made, and a module can read its own
  `__loader__` and put it on another module's spec. **Position is not what puts
  a module in scope; having loaded it is** — the audit gated its whole check on
  the module's current `__file__` being under the materialized root, so a
  module body that reassigned `__file__` skipped the object-identity,
  expected-origin and exact-loader checks together, and the one module the
  audit exists for was the one able to leave its scope.
Claim ceiling: **A
  specification that does not retire beside the thing replacing it specifies
  neither.** **A setting can read as a guarantee and provide nothing**:
  `PYTHONHASHSEED=0` is ignored under `-I`, measured, and the determinism claim
  it supported was withdrawn rather than re-explained.
Claim ceiling: Revision 6 corrected the design against its own implementation rather than
  the reverse: revision 5 had excluded f26 and f27 to BLOCKED-2 with f28, but
  the frame's label set and its internal digest consistency are decisions the
  decoder must make before returning anything. The implementation had them
  because they cannot be left out, and the authority was wrong.
  Claim ceiling: nothing here executes, spawns, compiles or imports anything
  historical. `ACTIVE` stays `False`, no availability predicate moved, nothing
  calls in, and canonical precommit passing proves the repository gate still
  passes with these files present and proves nothing about whether the loader is
  right.
Claim ceiling: The
  runner's trust root and its TOCTOU window remain accepted assumptions of M3.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2435-L2502)

**M2494 · Gate 3 M3 design and M3-a delivered 2026-08-19.** Merged to `main` as.** Claim ceiling (verbatim):
Claim ceiling: The transport is
  therefore one self-contained stdlib-only file that the parent imports for its
  encoder and the child will later execute as `__main__`, which is what makes
  the encoder and the decoder *share* the wire grammar instead of agreeing
  about it.
Claim ceiling: Rather than assert a stricter grammar in the subordinate
  document, the design was marked blocked and the authority was amended:
  revision 10 specifies a wire grammar defined once and applied by both sides,
  accepting a subset of what the containment check accepts, with that direction
  bound by a test over a named corpus and the reverse inclusion recorded as
  false with named witnesses.
Claim ceiling: Claim ceiling: `ACTIVE = False`, no production caller, no spawn, nothing
  compiled and no historical module imported. The trusted computing base is
  named rather than assumed — the runner is executed by path and nothing
  verifies those bytes first, so "defends against a corrupted parent" covers
  the parent's transport and data state and explicitly **not** the spawn
  target, and runner identity and its TOCTOU window are accepted trust
  assumptions rather than deferred work. The child's re-derivation is not
  independent verification in the strong sense: both copies come from one
  author and one design.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2504-L2560)

**M2552 · Gate 3 held-handle read implemented 2026-08-18.** Commit `6e7393e2`.** Claim ceiling (verbatim):
Claim ceiling: The read takes no length: it is sealed into the `Leaf` at creation, so "how
  many bytes should be here" is not answerable by whoever is asking. All four
  `ReadFile` outcomes are mapped, including a count larger than the request —
  a broken call rather than a changed file, and refused rather than trusted,
  because a fake binding can return it and treating it as a short read would
  advance past what was written. Every read rewinds first and checks the
  returned position, not only the boolean.
Claim ceiling: Claim ceiling: a read surface. It moved no availability flag, and the share
  mask it reads under is not total exclusion — measured, a native reader
  sharing read, write and delete does open a held role 3 file.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2562-L2585)

**M2577 · Gate 3 M2 completed 2026-08-18.** Commit `5a04ec79` rebuilds.** Claim ceiling (verbatim):
Claim ceiling: Every filesystem operation is handle-relative; the path-based versions are
  deleted rather than kept as a fallback. `base` is borrowed and is never
  created, deleted or marked. The phase order is the security property: blobs
  are read and verified while no handle is open, and only then is the base
  pinned. Cleanup is a per-object transaction — mark, close, confirm absent —
  where deletion stops at the first object that will not confirm gone while
  handle release continues through everything deletion did not reach.
Claim ceiling: Claim ceiling: `materialize()` and `cleanup()` still refuse.
  `handle_boundary_available()` forwards to the boundary, which reports `False`
  while no admission record and no capability probe exist — this module does
  not decide its own availability. **Verification is not entirely
  handle-bound:** the enumeration comparing the observed file set against the
  record is still a path walk, and the adapter offers no handle-bound directory
  enumeration to replace it. That limit is in the module docstring, in
  `verify`'s docstring, and in a test that fails if a later revision deletes the
  caveat while leaving the walk.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2587-L2622)

**M2614 · Gate 3 held-handle read design amendment accepted 2026-08-18.** Claim ceiling (verbatim):
Claim ceiling: Role 3 gains `FILE_READ_DATA`
  and the adapter gains `read_all(leaf)`, whose expected length is sealed at
  creation rather than supplied by whoever is asking.
Claim ceiling: Two claims were withdrawn against measurement. A held created file does
  **not** admit no other opener — a native reader sharing read, write and
  delete succeeds, while one sharing less is refused — so the reason for
  reading through the creating handle is that it resolves no name and adds no
  second ownership path, not exclusivity. And byte immutability rests on three
  things together: the share mask, the opaque handle, and a call census showing
  no `WriteFile` after creation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2624-L2651)

**M2643 · N3c2 design; path-read/_contained dependency superseded-by M2722.S02.** Claim ceiling (verbatim):
Claim ceiling: "It" below is the original exact accepted N3c-2 design identified by commit and digest. This is historical design evidence; the retained M2722 supersession and original no-implementation/no-live limits are unchanged.
Claim ceiling: **Gate 3 N3c-2 design accepted 2026-08-17.** Design-only commit
  `520cc306`, exact SHA-256
  `25d0a2522c5bd4a482bb28fcc3c9cdfc62d5c0768f44f897445053fdead6aaba`
  (20,180 bytes), subordinate to revision 17 and restating none of it. It
  carries the owner ruling that `base` must pre-exist and stay a borrowed
  ancestor, with the reasoning that generalizes: a created object owes a
  deletion and a borrowed one owes never deleting, so an object made to carry
  both obligations can discharge neither.
Claim ceiling: A safety-scope
  defect: `_contained` was to be deleted as structurally unnecessary while
  `verify` still resolved by path and still called it, and a digest comparison
  does not cover for it — it says nothing when an external location happens to
  hold exactly the expected bytes.
Claim ceiling: Claim ceiling: design bytes. Approval moved no availability flag and
  authorized no filesystem operation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2653-L2673)

**M2665 · Gate 3 native boundary N3c-2 completed 2026-08-17.** Implementation.** Claim ceiling (verbatim):
Claim ceiling: **Gate 3 native boundary N3c-2 completed 2026-08-17.** Implementation
  commit `495fe52f` adds role 2 directory creation, role 3 file creation with
  the payload written through the held handle, handle-bound deletion with its
  fallback, and the absence probe.
Claim ceiling: `BASE_NOT_FOUND` and `BASE_NOT_ADMISSIBLE` are appended at 11 and 12 with
  every earlier ordinal asserted individually, so `HANDLE_BOUNDARY_UNAVAILABLE`
  now means only that the boundary cannot be used on this platform rather than
  also answering for a path the caller could fix.
Claim ceiling: Claim ceiling: this tranche creates and deletes real filesystem objects, all
  of them under a `base` the caller supplies and this code never creates,
  deletes or marks. `handle_boundary_available()` and `ACTIVE` are both `False`,
  so no production path reaches it; M2 is not wired; the consumed pair remains
  `NON_SUCCESS`, and Gate 3 or treatment/Skill effectiveness is not
  established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2675-L2707)

**M2699 · Gate 3 native handle-boundary design revision 17 accepted 2026-08-16.** Claim ceiling (verbatim):
Claim ceiling: All three roles now request
  `FILE_READ_ATTRIBUTES`, because an audit found none exempt.
  `FILE_WRITE_ATTRIBUTES` is explicitly rejected as a justification for
  reading: the two are independent rights.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2709-L2719)

**M2718 · The held-handle read (N3c-3) is complete and delivered in `6e7393e2`. It is.** Claim ceiling (verbatim):
Claim ceiling: It is
  what makes a materialized file readable at all: role 3 holds each file it
  creates, and its share mask refuses every opener unwilling to tolerate our
  write and delete access.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2728-L2731)

**M2722 · M2 is complete and delivered in `5a04ec79`. `_contained` went with it: it.** Claim ceiling (verbatim):
Claim ceiling: `_contained` went with it: it
  guarded a path-based read that no longer exists, since `verify` now reads
  through the creating handle.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2732-L2734)

**M2728 · M3-b has its design in `8a8dbc2c`, revised in `70d62fd1`, and its first.** Claim ceiling (verbatim):
Claim ceiling: **It is still true
  that no committed tranche executes historical code.**
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2738-L2743)

**M2734 · BLOCKED-3 is CLOSED.** The process-control design slice in `95838ac0` was.** Claim ceiling (verbatim):
Claim ceiling: **BLOCKED-3 is CLOSED.** The process-control design slice in `95838ac0` was
  accepted after `fe44deb4` committed the digest-pinned SDK provenance, seven
  measured process-control layouts, their pure `ctypes` declarations and the
  independent fixtures.
Claim ceiling: No symbol is bound or
  called and `ACTIVE` remains `False`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2744-L2752)

**M2751 · M3-b-2A binds one live `MaterializedTree` authority to one launch envelope.** Claim ceiling (verbatim):
Claim ceiling: M3-b-2A binds one live `MaterializedTree` authority to one launch envelope
  containing the unchanged M3-a frame and root. The child validates syntax and
  the deterministic leaf; the full absolute base remains parent-trusted. It has
  no `__main__`, process, native call, historical import or active caller.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2761-L2765)

**M2759 · The seven failing tests in `test_gate3_route_v2_ab_candidate.py` and.** Claim ceiling (verbatim):
Claim ceiling: The quoted HEAD/worktree comparison is the original B-1 divergence checkpoint, not a fresh observation of this checkout. "That commit" means only its named SOURCE_COMMIT; later M4 requirements are unchanged.
Claim ceiling: At `HEAD`, `gate3_route_v2.py` and
  `gate3_route_v2_codex.py` are byte-identical to `SOURCE_COMMIT`
  `204965c94bd843d599986d9f9d0fd552ea053dff`; only the worktree differs. The
  historical candidate is verified by comparing live worktree bytes against
  that commit, which holds only while the implementing source never moves.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2769-L2775)

**M2766 · B1 structural non-repr boundary; status CHANGES_REQUESTED / PAUSED_BEHIND_M4; unstaged storage superseded-by #110 / 9d51a3c8 (C14).** Claim ceiling (verbatim):
Claim ceiling: Its dependency is `N3c-2 -> M2 -> M3 -> M4 -> B-1`: M4 is what
  lets a historical candidate be verified against materialized historical bytes
  instead of against the live worktree. Splitting B-1 to land only the unpinned
  consumer was considered and rejected by the owner, because it would narrow
  the census from three consumers to one and leave the two actually under pin
  unprotected.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2776-L2783)

**M2774 · No manifest is repinned, no pair evidence is rewritten, and the consumed.** Claim ceiling (verbatim):
Claim ceiling: No manifest is repinned, no pair evidence is rewritten, and the consumed
  `NON_SUCCESS` pair does not regain usability through any of this.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2784-L2785)

**M2782 · retrieval-only memory/05_authority_index.md cutover.** Claim ceiling (verbatim):
Claim ceiling: The index is retrieval-only, not new
  authority or independent proof.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2792-L2796)

**M2787 · original 2026-09-04 non-exposure keyring qualification; later Solo allocations are distinct.** Claim ceiling (verbatim):
Claim ceiling: R2 sandbox/custody qualification and both V2 wrappers are frozen.
Claim ceiling: The qualification-home authentication sub-blocker
  is cleared; production runner explicit keyring wiring and runtime
  requalification remain required.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2797-L2804)

**M2839 · M4 is not started, and M3 is delivered only as M3-a, M3-b-1 and bounded.** Claim ceiling (verbatim):
Claim ceiling: M4 is not started, and M3 is delivered only as M3-a, M3-b-1 and bounded
  M3-b-2A. Nothing is wired to M2 or to M3-a, nothing calls M3-b-1 or M3-b-2A,
  and no availability flag moved: `handle_boundary_available()` and `ACTIVE`
  are both `False`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2849-L2852)

**M2843 · Credentials, preflight and live remain unauthorized.** Claim ceiling (verbatim):
Claim ceiling: Credentials, preflight and live remain unauthorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2853-L2853)

**M2846 · Claim ceiling: this work item has produced design authority, an independent.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling: this work item has produced design authority, an independent
ABI oracle, declaration, loader, fail-fast and runtime-fact tranches, a
committed tranche that opens and holds directory handles (N3c-1), and one that
creates, writes, deletes and probes for absence (N3c-2). The sentence that
stood here until 2026-08-18 — that no committed tranche creates or deletes a
filesystem object — was true when written and was contradicted by `495fe52f`
the same week. What remains true is narrower and is the part that matters:
every object N3c-2 creates or deletes is one it created itself, under a `base`
supplied by the caller that this code never creates, deletes or marks.
`handle_boundary_available()` and
`ACTIVE` are both `False`, so the boundary is not reachable from any production
path. Accepted design bytes are not an implementation, exact-digest review
approval is not runtime evidence, and none of this reuses, retries or replaces
the consumed A/B pair. The consumed pair remains `NON_SUCCESS`, and Gate 3 or
treatment/Skill effectiveness is not established.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2856-L2870)

### Decision C1 pre-randomization admission — 2026-08-26

Scope: reviewed D5 pre-randomization rules/provider/identity/admission. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2862 · Gate 3 common-harness non-counted synthetic rehearsal completed.** Claim ceiling (verbatim):
Claim ceiling: This rehearsal is synthetic and non-counted; its scorer fixtures are not
  independent judgments and it does not approve, sign, promote or start Gate 3.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2872-L2884)

**M2876 · C1 Gate 1 preregistration and pre-randomization admission completed.** Claim ceiling (verbatim):
Claim ceiling: The separate final-head
  countability decision was frozen in reviewed commit `1ced27d0` and merged as
  `3351584a` by PR #120. Its terminal is
  `ARM_EXECUTION_ADMISSION_PASSED_NOT_RANDOMIZED`: event 7 remains a mandatory
  proof-bearing external pin before event 8 mapping release; an additional
  event-9-style external final-head receipt is not required for this internal
  Skill-funding experiment. Randomization has not been created, A/B/C/D arms
  have not executed, and both remain unauthorized pending separate explicit
  owner authority bound to the reviewed D5 admission commit.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2886-L2899)

**M2891 · Claim ceiling for this checkpoint: the experimental rules, validator path,.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling for this checkpoint: the experimental rules, validator path,
external pin provider, client identity boundary and pre-randomization admission
are available and reviewed. This does not establish Gate 3 readiness,
treatment effect, governance effectiveness, validator-feedback effectiveness
or Skill effectiveness, and it does not authorize randomization, producer or
scorer execution, mapping release, or any A/B/C/D arm.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2901-L2906)

### Decision Solo R2 terminal dispositions — 2026-09-08

Scope: original fixed-instance Solo R2 input, Attempt, allocation, wiring and scoring records (2026-09-06–08). Status: ended single-use grants; quoted observed terminal outcomes apply to their own instances. Claim ceiling: retained verbatim source conditions below.

**M3036 · Exact task/rubric adoption.** Claim ceiling (verbatim):
Claim ceiling: The task and rubric bytes remain unchanged.
Claim ceiling: No retrospective binding
to an existing Pair, new Pair, Attempt, execution, or push is authorized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3046-L3055)

**M3048 · Disposable input freeze.** Claim ceiling (verbatim):
Claim ceiling: Grimm stays reserved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3058-L3070)

**M3063 · v2.1 schema adoption.** Claim ceiling (verbatim):
Claim ceiling: Binding spec is preserved subordinate design provenance, not implementation authority.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3073-L3080)

**M3091 · Disposable production binding.** Claim ceiling (verbatim):
Claim ceiling: STOP with implementation/test/review evidence ready; future actions need their own scope.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3101-L3114)

**M3106 · Materializer/arm integration.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Exact subtree and packet binding, durable exposure-before-dispatch, per-arm runtime
freeze and retained source/runtime evidence are covered by 28 passing new tests.
Claim ceiling: Frozen inputs unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3116-L3127)

**M3131 · R1 after 3b820a2c.** Claim ceiling (verbatim):
Claim ceiling: Scope: structural evidence only; no real evaluation, ledger, Pair, Attempt, admission, or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3141-L3145)

**M3143 · Unavailable-cost amendment.** Claim ceiling (verbatim):
Claim ceiling: No retry, Attempt 2, new Pair, A1-A6 or push authority.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3153-L3158)

**M3150 · Unavailable-cost implementation.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Minimal v2.1 cost representation implemented; numeric v2 unchanged. Extended append requires exact adoption and durable controller evidence verified against the retained trace.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3160-L3164)

**M3156 · Unavailable-cost R1 refresh.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: The commit named below is the antecedent of "that commit" in this consumed historical R1 refresh; it is not the current HEAD or a new refresh grant.
Claim ceiling: Implementation committed at `0c48594a0e6e474bcb58bfcd1f25e2a7f9940bab`; targeted 138 PASS and independent 42 PASS / Blocking 0.
Claim ceiling: R1 refresh binds the two changed sources to that commit, preserves the other five bindings and entropy-call structure, and recognizes the reviewed `record_harness_failure` API.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3166-L3171)

**M3163 · Historical Attempt terminal.** Claim ceiling (verbatim):
Claim ceiling: Owner-authorized historical append completed: fifth event EXECUTION_TERMINAL / HARNESS_FAILURE; original four-event prefix preserved byte-for-byte.
Claim ceiling: Initiated count remains 1; terminal count is 1.
Claim ceiling: No output sealing, correctness evaluation, retry, Attempt 2 or push. STOP; later bug-fix/retry decisions remain separate.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3173-L3177)

**M3169 · Harness repair.** Claim ceiling (verbatim):
Claim ceiling: Scope is local committed repair and static import binding only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3179-L3184)

**M3176 · Replacement allocation.** Claim ceiling (verbatim):
Claim ceiling: Old evaluation FAILED_MECHANISM_SHAKEDOWN / PRESERVED / NO_FURTHER_ARM; existing five-event ledger unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3186-L3192)

**M3184 · Replacement binding adoption.** Claim ceiling (verbatim):
Claim ceiling: Attempt ceilings are per-ledger; cross-evaluation allocation is owner-bound, not a schema-global counter.
Claim ceiling: Replacement append requires binding + genesis + evaluation + exact path; path membership alone is insufficient.
Claim ceiling: Old five-event ledger and consumed Attempt preserved; no production edits, migration, new experiment, execution or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3194-L3200)

**M3192 · Replacement binding implementation.** Claim ceiling (verbatim):
Claim ceiling: Fixed replacement create/append APIs bind exact adopted authority, genesis, evaluation and placement; old cost authority is not transferred.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3202-L3207)

**M3199 · Replacement binding R1 refresh.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: The commit named below is the antecedent of "that commit" in this consumed historical R1 refresh; it is not the current HEAD or a new refresh grant.
Claim ceiling: Implementation committed at de85d2f8ecf5f1ccb732e09ec4053b74456ab180; reviewed source bytes verified 9/9.
Claim ceiling: R1 binds ledger_v2/pair_creation/lifecycle to that commit, preserving other four bindings and entropy-call semantics.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3209-L3214)

**M3206 · Replacement launcher static delivery.** Claim ceiling (verbatim):
Claim ceiling: Replacement-only external launcher offers check and Phase A creation-to-candidate STOP; no readiness/execution/adoption modes.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3216-L3221)

**M3213 · Replacement payload-pin adoption.** Claim ceiling (verbatim):
Claim ceiling: No readiness, execution, payload regeneration or old-pin reuse.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3223-L3228)

**M3220 · Replacement Phase B.** Claim ceiling (verbatim):
Claim ceiling: Consumed historical replacement Phase B checkpoint only. Its pending-scope status is the antecedent that M3227.S02 subsequently supersedes for one exact transition; it is not a current blocker, READY claim or new permission.
Claim ceiling: Added committed-adoption/external-state verification, replacement-only readiness object assembly, and live in-process wait. Blank input and EOF do not return; explicit ABORT discards live handoff.
Claim ceiling: Execution entry remains disabled pending owner scope answer; do not claim executable continuation READY.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3230-L3235)

**M3227 · Controlled EXECUTE wiring.** Claim ceiling (verbatim):
Claim ceiling: Owner separately authorized the final one-use live execution transition; this supersedes the preceding pending-scope note only.
Claim ceiling: Exact evaluation/Pair/nonce authorization revalidates current adoption/state/ledger/payload and original live objects, then calls the existing execution API once. No second readiness run or cross-process resume.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3237-L3242)

**M3235 · Final fresh allocation.** Claim ceiling (verbatim):
Claim ceiling: One final evaluation/ledger/Pair and two fresh arms as allocation only; all creation and execution require separate authorization. Historical runs preserved, no further automatic replacement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3245-L3247)

**M3239 · Final fresh binding implementation.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Lifecycle unchanged; historical ledgers/frozen inputs preserved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3249-L3251)

**M3243 · Final fresh R1 refresh.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Refresh binds exact committed ledger/pair bytes; five other pins unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3253-L3255)

**M3251 · Scoring continuation adoption.** Claim ceiling (verbatim):
Claim ceiling: Owner adopts exact preserved scoring inputs as new prospective authority; historical ATTEMPT_BOUND digest custody remains ABSENT.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3261-L3263)

**M3255 · Scoring continuation implementation.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Final-only consumer verifies prospective adoption and 22 exact artifacts before existing scoring preparation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3265-L3267)

**M3259 · Superseding scoring adoption.** Claim ceiling (verbatim):
Claim ceiling: Historical nine-event ledger and rejected bundle/checkpoint preserved. One prospective detached supersession only; implementation, artifact activation, fresh scoring and unblinding require separate authorization.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3269-L3271)

**M3263 · Superseding implementation.** Claim ceiling (verbatim):
Claim ceiling: Original fixed-instance prerequisite, subsequently narrowed only by the owner-adopted C02 exception quoted in M3288. Fresh context and restricted delivery survive; the old OS-attested assurance is not restored. This consumed instance is not a scoring grant.
Claim ceiling: Fresh scorer/host custody remains execution prerequisite.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3273-L3275)

**M3268 · Superseding R1 refresh.** Claim ceiling (verbatim):
Claim ceiling: Only R1 metadata refreshed; historical ledger/bundle/checkpoint unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3278-L3280)

**M3272 · AppContainer minimal environment.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Only LOCALAPPDATA added to the existing sanitized Probe.cs environment.
Claim ceiling: Corrected source compiled; external Probe.exe remains historical and has not been redeployed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3282-L3284)

**M3276 · Runtime parent custody.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Fixed D:/r2-final-disposable-shakedown-20260907 root DACL protected with owner/SYSTEM/Administrators only.
Claim ceiling: Windows converted inherited ACEs to explicit/protected on 11 direct children; existing grants unchanged, but child SDDL not identical. Disk ACL and preserved ledger/bundle/checkpoint bytes and ACLs unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3286-L3288)

**M3280 · Synthetic scorer isolation durability.** Claim ceiling (verbatim):
Claim ceiling: Real bundle anonymity, Python consumer integration and scorer execution remain unclaimed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3290-L3292)

**M3284 · Real-bundle callback wiring.** Claim ceiling (verbatim):
Claim ceiling: Fixed-instance generator now requires reviewed semantic payload identities, new-instance custody initialization using the existing ACL model, and native verification of the persisted real bundle before its transition receipt.
Claim ceiling: Real parent custody, reviewed deployed executable/RX and semantic payload digest custody remain runtime prerequisites; no R1 source pin changed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3294-L3296)

**M3288 · Simplified scoring ceiling adoption.** Claim ceiling (verbatim):
Claim ceiling: Ended scoring instance only: evaluation 74ad1963-e24c-4ced-9f84-32e3c0daf900, Pair 93584d7e-2bf9-4535-93c8-5593fcd3e272, R2-SHAKEDOWN. Adoption record interprets the unchanged candidate header as historical. The following exact adopted C01/C02/C04 conditions narrow OS assurance while retaining fresh-context, input and STOP predicates; M3298 records the terminal outcome. No new scorer, rerun, freeze or unblinding grant is created.
Claim ceiling: Owner adopted exact amendment SHA256 a9ca58223b6b452dd2518a8138c49a95d077fe85862bed737441b36932712a03 (7170 bytes, 73 lines). Claim ceiling is NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY; OS scorer isolation, strict end-to-end PASS and Formal/counted evidence are not claimed. Prior evidence remains unchanged. Record: memory/evidence/solo-r2-simplified-scoring-amendment-20260907/owner-adoption.json. Scoped adoption commit and identity verification then STOP; actual fresh-context scoring/freeze and later unblinding require separate authorizations.
Claim ceiling: Exact adopted source excerpts (C01/C02/C04); all grants here are consumed.

Claim ceiling: Adopted C01 conditions (verbatim)
> Permit a limited comparison of the already-completed Solo R2 outputs without claiming OS-attested scorer isolation or strict end-to-end shakedown PASS. This is an explicit reduction in scorer assurance and claim ceiling, not a statement that the previous ceiling is unchanged.
>
> Applies only to evaluation `74ad1963-e24c-4ced-9f84-32e3c0daf900`, Pair `93584d7e-2bf9-4535-93c8-5593fcd3e272`, slot `R2-SHAKEDOWN`.
>
> The only permitted scoring identity is the already-activated superseding identity:
>
> | Artifact | Bytes | SHA-256 |
> |---|---:|---|
> | Superseding bundle | 2796 | `b2097cda3b973b5154b5393d01d2ec98aa662574ba0e529879a405bc67b01bd3` |
> | Superseding transition | 1668 | `20b5cfcc131c2e09cf1f9d858666c2f62af4d9a817931a29721cb2d1b4303fb5` |
> | Owner activation record | 254 | `9d748ef3746c737c66c146efad4bbfad6d9a919f442257926ba289f12e452218` |
> | Frozen rubric | 3754 | `a93a1f3d74ef9a191317d345c5e54f31b309ee481174cfe374f42938db4bfca9` |
>
> The fixed paths and relationships remain those of the existing transition and activation. No arbitrary bundle, replacement identity or caller-selected evaluation is accepted. The current nine-event ledger remains unchanged, SHA-256 `e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77`.

Claim ceiling: Adopted C02 conditions (verbatim)
> Results under this amendment are limited to `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.
>
> Explicitly NOT CLAIMED:
> - OS-level isolation of the actual scorer;
> - strict end-to-end Solo R2 shakedown PASS;
> - Formal Gate 3 or counted evidence;
> - generalized Bug Fix Safety effectiveness beyond this evaluated task.
>
> For this scoring step only, this amendment permits context-level freshness and restricted input delivery instead of requiring OS-attested isolation of the scorer execution. It narrowly adjusts the fresh-scorer execution assurance required by S07 of the adopted superseding policy (SHA-256 `10fc9ad2e7ab83088391ed3beaa705d65fc69f0456142bfd3fb329f5cb77535c`) and the subsequent owner OS-isolation execution requirements for this instance. All remaining identity, history-preservation, correctness, score-freeze and separate-unblinding boundaries remain in force.
>
> Do not claim that an OS verifier passed for a context that did not run inside that boundary. Existing isolation probes retain their original limited evidentiary meaning. AppContainer model integration, local-model discovery and network-scorer sandbox work are POST-GATE3 and are not prerequisites for this decision-support route.

Claim ceiling: Adopted C04 conditions (verbatim)
> Use exactly one new scorer context with no prior conversation or scoring context from this evaluation. It must not have seen the rejected bundle or been given CONTROL/TREATMENT mapping. Do not fork or copy the current conversation, investigative summaries, execution history or prior review context into it. The current controller/reviewer context cannot serve as the scorer.
>
> Deliver only the activated anonymous scoring materials, the exact frozen rubric, and explicitly permitted correctness information. Use opaque presentation keys; exclude controller-only identity wrappers, repository/workspace or execution identities, mappings, rejected materials and investigation records. Do not alter the preserved bundle to perform delivery.
>
> Restrict the supplied inputs and available capabilities to scoring. Instruct the scorer not to infer, request or obtain arm mapping or other prohibited materials. Preserve a controller-only manifest of the actual fresh context and exact delivered inputs; do not send that provenance manifest to the scorer. This records delivery and declared context freshness, not OS proof that all other information is inaccessible.
>
> If context freshness or restricted delivery cannot be established, or identity leakage is observed, STOP without scoring; do not silently substitute the current context or repair the preserved bundle.
[adopted amendment](docs/governance/solo-r2-simplified-blind-scoring-amendment-candidate-20260907.md) · [owner adoption](memory/evidence/solo-r2-simplified-scoring-amendment-20260907/owner-adoption.json)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3298-L3300)

**M3293 · Regression projection adoption.** Claim ceiling (verbatim):
Claim ceiling: Real launcher integration, Python investigation, fresh round and push are not authorized by this adoption.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3303-L3305)

**M3298 · Solo R2 decision-support closeout.** Claim ceiling (verbatim):
Claim ceiling: Execution, oracle (10/10 each), simplified score freeze and unblinding are complete. Regression safety and overall quality/tie remain undetermined. Claim ceiling: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY; no strict OS-isolated shakedown PASS.
Claim ceiling: Python capability remains UNKNOWN and is POST-GATE3, not a closeout blocker. Scoped evidence commit/push and STOP; no new probe, scoring or allocation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3308-L3310)

### Decision Lite single-fixture delivery and durability — 2026-09-08

Scope: the original exact instances, IDs, digests and single-use actions in the dated source clauses below. Status: ended single-use grants; terminal outcomes and surviving input/claim limits follow. Claim ceiling: retained verbatim source conditions below.

**M3303 · Lite synthetic Slice 1.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Synthetic Lite flow implemented: anonymous input -> fixture scoring -> freeze -> explicitly authorized unblinding -> report. Existing future scoring consumer reused unchanged.
Claim ceiling: Ceiling: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY. Real runner/scorer, OS isolation, strict equivalence and actual cost reduction are not established. Strict and historical rounds unchanged.
Claim ceiling: P1 remains closed UNKNOWN.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3313-L3318)

**M3311 · Lite Slice 2 initial 401.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Bounded real adapter implemented: fresh model patch generation, host oracle/regression, anonymous scorer input, freeze then authorized unblinding.
Claim ceiling: One live invocation stopped at first model HTTP 401 (missing auth header), process exit 1. No CONTROL output; TREATMENT/oracle/scorer/freeze/report not run.
Claim ceiling: Result: REAL_LITE_END_TO_END_BLOCKED.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3321-L3326)

**M3318 · Lite auth override replay.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Shared Lite exec now explicitly selects the existing keyring store while retaining --ignore-user-config.
Claim ceiling: One authorized live replay: CONTROL model process exit 0 with response and turn.completed; parser rejects runtime item.error warnings as tool access. No observed tool event. TREATMENT/oracle/scorer/freeze/unblind not run. REAL_LITE_END_TO_END_BLOCKED; no automatic retry.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3328-L3332)

**M3325 · Lite warning parser.** Claim ceiling (verbatim):
Claim ceiling: Known 0.153.4 runtime warnings are distinguished from forbidden tools using full-message matches. Unknown error/incomplete turn/tool events still reject; exact warnings remain host-only and are retained in reports.
Claim ceiling: No automatic retry, Strict changes, or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3335-L3339)

**M3331 · Lite E2E outcome.** Claim ceiling (verbatim):
Claim ceiling: Compatibility implementation committed at 85dcfa7456957d943a621bb7ddd2c9c746ee5978; one subsequent authorized Lite E2E completed in 87,015 ms of adapter time. Real model generation + host oracle/regression + fresh scorer + freeze + authorized unblinding/report completed.
Claim ceiling: One bounded pipeline fixture only; no general Skill efficacy, measured cost reduction, OS isolation or Strict equivalence.
Claim ceiling: Result REAL_LITE_END_TO_END_VALIDATED; report memory/evidence/p2-lite-parser-20260908/live/report.json.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3341-L3345)

**M3338 · Lite Slice 2 durability.** Claim ceiling (verbatim):
Claim ceiling: Preserve the real flow report, frozen scores, raw model/host receipts and exact identity verification; historical precommit snapshots remain unchanged. No production changes, rerun, rescoring, benchmark or push.
Claim ceiling: The single-task 7/8 vs 8/8 observation does not establish general Skill efficacy or average cost reduction.
Claim ceiling: After committed bytes verification, P2 Slice 2 durability is closed; any mini benchmark is future scope, not an automatic continuation.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3348-L3352)

### Decision Lite three-task preparation, failures and disposition — 2026-09-08

Scope: the original exact instances, IDs, digests and single-use actions in the dated source clauses below. Status: ended single-use grants; terminal outcomes and surviving input/claim limits follow. Claim ceiling: retained verbatim source conditions below.

**M3345 · prospective benchmark preparation; integration status superseded-by M3368; adoption status by M3360.** Claim ceiling (verbatim):
Claim ceiling: Specifications/baselines/literal oracles/regression panels/rubrics fixed in tests/fixtures/bug_fix_safety_mini_benchmark/manifest.json before validation and any model execution.
Claim ceiling: Source/test evidence and current-version completion requirements declared before scoring; missing evidence stays NOT_ASSESSABLE.
Claim ceiling: Existing Lite adapter remains task-specific; integration and difficulty calibration not claimed.
Claim ceiling: Candidate identity is not owner adoption or authorization for real benchmark runs.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3355-L3360)

**M3360 · Benchmark hint fix and adoption.** Claim ceiling (verbatim):
Claim ceiling: The quoted unverified/no-change/no-push sentence describes the adopted benchmark-pack checkpoint. Only runner integration and later single-instance model execution were subsequently supplied by M3368 / M3383 / M3390; difficulty calibration and generalized effectiveness are not thereby established. Later grants apply only to their named instances; the earlier preparation grant is consumed.
Claim ceiling: Removed only the Hard public TASK implementation-specific ignore-revisits hint; functional cycle detection requirement remains. Manifest updates only that TASK identity; other 17 entries unchanged.
Claim ceiling: Accepted pack manifest SHA256 a55394136c8dfead4940c577fc94aa999ae4b9593bb2d652ef981241fd3cbe34. Exact snapshot and historical review evidence retained; no claim that earlier candidate snapshots were adopted.
Claim ceiling: Runner integration/difficulty calibration/model evaluation remain unverified; no runner/Skill/scorer or historical-result changes, no push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3370-L3375)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3363-L3367)

**M3368 · bounded default-P2 Lite benchmark adapter; prospective opt-in P3 is separately scoped in M3414.** Claim ceiling (verbatim):
Claim ceiling: BENCHMARK_LITE_INTEGRATION_READY: three adopted fixtures verify manifest/bytes, materialize separate two-arm workspaces, use their own oracle cases and rubric, preserve host source/test versions and regression diagnostics through the existing anonymous consumer.
Claim ceiling: Only new bounded adapter/test and opt-in Lite AST support; Strict modules and all fixture bytes unchanged.
Claim ceiling: Completed zero-test evidence remains unassessable. Regression launch/timeout/import failures preserve raw receipts and STOP rather than promising continued scoring. Host alias mapping is explicit; no OS isolation/general sandbox claim.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3378-L3383)

**M3376 · Lite harness compatibility.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Host now delegates a unique standard final unittest.main entry to actual suite execution; disk source/test bytes preserved. Only Medium test zip/assertIsInstance and Hard test DictComp/IfExp/self.subTest context admitted; other with/I/O paths still reject.
Claim ceiling: All original43 failure artifacts and adopted benchmark materials unchanged.
Claim ceiling: Scoped compatibility commit and STOP; no second real benchmark or push without separate authorization.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3386-L3390)

**M3383 · First three-task real invocation.** Claim ceiling (verbatim):
Claim ceiling: One authorized invocation per task completed its terminal disposition: 0 complete comparisons / 3 blocked at CONTROL.
Claim ceiling: No retry or runner/fixture/Skill changes; next tasks used independent contexts and unchanged frozen materials.
Claim ceiling: No Skill quality conclusion.
Claim ceiling: Prior frozen results preserved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3393-L3397)

**M3390 · Preserved CONTROL completion.** Claim ceiling (verbatim):
Claim ceiling: Completed three fresh TREATMENT calls and three fresh anonymous scorer calls; no CONTROL model rerun. Original single-run CONTROL bytes recollected under 983d5fad committed harness, no import/fixture/Skill changes.
Claim ceiling: No Treatment quality advantage established; no aggregate tie/general Skill efficacy claim.
Claim ceiling: Scores durably frozen before authorized unblinding.
Claim ceiling: NON_COUNTED/SOLO_CONTROLLED/DECISION_SUPPORT_ONLY.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3400-L3405)

**M3398 · Lite multi-task disposition.** Claim ceiling (verbatim):
Claim ceiling: REAL_LITE_MULTI_TASK_BENCHMARK_VALIDATED: three preserved CONTROL + three fresh TREATMENT comparisons completed, scores frozen then unblinded. Easy regression/total NOT_ASSESSABLE both; Medium/Hard8vs8. No stable Treatment advantage established.
Claim ceiling: Owner provisional disposition KEEP_OBSERVE / OPTIONAL; no Skill packet/default-loading/config change. Hard3vs2methods does not prove greater coverage. Earlier7vs8 signal remains separate; no generalized efficacy or average-cost claim.
Claim ceiling: Preserve first-run failures and completed artifacts in scoped local commit.
Claim ceiling: NON_COUNTED/SOLO_CONTROLLED/DECISION_SUPPORT_ONLY.
Claim ceiling: Candidate future work: another Skill or separately scoped Lite/Strict cost-value review; neither executes automatically.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3408-L3413)

### Decision P3 future-only grading — 2026-09-08

Scope: adopted future-only P3 grading and opt-in synthetic integration. Status: retained conditions. Claim ceiling: retained verbatim source conditions below.

**M3406 · P3 rubric amendment adoption.** Claim ceiling (verbatim):
Claim ceiling: Future-only: complete current-version execution evidence attributing regression nonexecution to submitted content supports0; evidence gaps/harness/environment/ambiguous attribution stayNOT_ASSESSABLE. Nonzero exit alone insufficient. Historical frozen scores and closeout unchanged.
Claim ceiling: No benchmark/model execution, Skill/fixture edits, historical rescoring or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3416-L3421)

**M3414 · P3 future projection/scorer integration.** Claim ceiling (verbatim):
Claim ceiling: Explicit p3=True future Lite adapter uses adopted amendment9ffa3492 and owner recordb22c8300. Existing default Lite and Strict sources remain unchanged except additive selection; frozen fixture/rubric and historical scores are preserved.
Claim ceiling: Host receipts separate current source/test versions from execution errors and identify the failing submitted/host phase. Missing import or syntax with attributable exact execution, and assertion failures, require0; harness/environment/unknown/missing evidence remainNOT_ASSESSABLE. Nonzero alone insufficient. Passing receipts leave unchanged coverage-based0/1/2 judgment to scorer.
Claim ceiling: Scorer receives explicit import/no-symbol-injection contract and anonymous failure locations; receipt digests remain host-only. Syntax-invalid submissions compile only; no unchecked submission execution.
Claim ceiling: DONE limited to synthetic integration plus scoped local commit. No real model, old benchmark rerun/rescoring, Skill change, adopted rubric edit or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3424-L3429)

### Decision P5 local profile and PR155 limits — 2026-09-08

Scope: fixed-generation local P5 profile and original PR155 integration. Status: retained original-scope conditions. Claim ceiling: retained verbatim source conditions below.

**M3422 · P5 fixed-generation integrity.** Claim ceiling (verbatim):
Claim ceiling: Fixed 195a204f local profile binds explicit repository/config adoption, hook/scanner/verifier identities and receipt before unchanged object-closure scanning. Missing or drifted identities stop before scan. Not a canonical installer migration.
Claim ceiling: Exact historical scanner stored only as a test fixture; no unreachable-object dependency.
Claim ceiling: Actual hook/scanner/config unchanged; no deployment, P4 work or push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3432-L3436)

**M3428 · PR155 integration delivery.** Claim ceiling (verbatim):
Claim ceiling: PR155 delivery is terminal. The final Strict rerun and GitHub current-head review/CI sentence below is the original exact-integration prerequisite, not a newly opened gate or proof those checks passed; the merge fact alone cannot establish them.
Claim ceiling: Integrate main a6a2d622 with feature 09248cb4 without rewriting either history. Preserve both branches' canonical memory records and historical claim boundaries.
Claim ceiling: No production trust pin, model invocation, historical score, or P4 change.
Claim ceiling: Runtime smoke plus 201 tests and Lite/P3/P5 129 tests passed; final Strict rerun and GitHub current-head review / CI remain required before merge.
Claim ceiling: Original dirty workspace and local P5 installation remain separate; deployment compatibility does not establish a canonical or portable installer. Results remain NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3438-L3443)

## Reconciliation And Evidence Gaps

### Decision conflict reconciliation — 2026-11-16

Scope: the 17 source pairs identified in step 1. Claim ceiling: factual delivery reconciliation only, with both sources preserved; no implicit owner approval, consumer adoption or historical-check proof.

| ID | Original source at 6c7e24c3 | Later / opposing evidence | Reconciled scope and remaining limit |
|---|---|---|---|
| C01 | PLAN L7–9、L15–19 | D6 #311 f80a5345；D2 #316 19de5d07 是獨立 S4 交付，不能反向併入 #309 原授權 | 記 framework merged；原 consumer、root AGENTS、S4 exclusion 只約束 #309 當時 slice，不能否認後續獨立授權。 #311 — means no follow-up recorded. |
| C02 | PLAN L40–56 | D9 #321 7da58f1a（pre-commit + pre-push）；main #307 e3e4adb0；D1 #315 8765bad6 是 write-side protection | 關閉精確 pre-commit 缺口；Copilot lifecycle bridge 仍 shared-root、submodule working-tree immutability 未證明；不可一起結案。 |
| C03 | PLAN L73–81 | main #211 82170f87，merge title fix(vscode): stop is not session end；原實作 6f097eb8 | 保留原 Draft-only 授權與 reviewed-head 證據；另記後來 merge 事實，不推定 consumer 已升級或以 merge 追認舊禁止。 |
| C04 | PLAN L88–109 | main #209 06b98906、#210 2a09d542；L104 已有 review + conditional-merge 授權 | 框架 S1/S2 記 merged；S3/S4 的原始 sequential 授權、framework review/delivery 前提與 consumer pin/hosted checks 另列，沒有 consumer 完成證據。 |
| C05 | PLAN L114–133 | main #204 15722daa；L119–120 的 separately reviewed eight-blob consumer policy 仍是不同 repo 的動作 | 只調整 framework delivery；八 blob policy 安裝與 product push 未在本輪驗證，原順序與既有授權保留。 |
| C06 | PLAN L228–235 | main #197 0f6b70f9、#199 7ba35db3；#195 b2a14b03、#196 0556fb70 | 分項記 merged；保留各 slice / no consumer-runtime qualification 限制，不沿用 stale CI blocker 當目前狀態。 |
| C07 | PLAN L459–473 | main #104 f788e2b0；L266–272 / L330–337 已實際使用 conjunctive exact-head predicates | 改為 delivered decision 的候選；PR #103 未滿足舊 GitHub approving-review prose 的歷史事實不被補正。 |
| C08 | PLAN L531–538 | main #165 409a4542 的 invoking-worktree smoke；D9 #321 7da58f1a 的 local pinned framework；pushed-commit subject 並未由這些證據證明 | 不把整段都當已修或未修；worktree routing 已修，推送 commit freshness 仍是證據缺口。 |
| C09 | PLAN L548–557；L558–562 | 本輪 owner 2026-11-16：step 1 only mapping、whole round framework PLAN/baseline/minimal readers、to PR/no merge | 本輪窄範圍覆蓋舊 not-authorised-here；PR #28 只重用分類/保存/consumer non-goal，未採納全 fleet lifecycle contract 或 parser 改動。 |
| C10 | PLAN L1198–1203 | PLAN L1053–1055 / L2971–2977；ffd9609 untrack+ignore、bf798d4 manifest-only export | 保留 no-write 模式自身界線，另記 Option B；不得把整個 workspace clean 或 elimination of all side effects 一起升級。 |
| C11 | PLAN L1207–1216 | PLAN L1475–1484 c06014c4 CLI requires explicit declaration；L1495–1521 / L1634–1641 P1-E closed、P1-F keep advisory | CLI omission exit 2 與 current-diff blocker 未增加是兩件事；runtime builder/session_end 可 emit not_declared 的未觀測缺口保留。 |
| C12 | PLAN L1642–1656 | PLAN L1661–1694 尤其 L1670–1675：只四個 machine-decidable proxies；12 focused + 23 adjacent evidence | 使用明示 narrowed-to-proxies 的決定，兩段都保存；不把 report 說成語義偵測或 gate。 |
| C13 | PLAN L2256–2266 | PLAN L2202–2239：Group A 明確 closes two of five，仍餘 credential recovery / non-repr / exclusivity 三項 | 這是舊 checkpoint 的限制，保留原文；現在 dependency projection 列已解兩項及仍缺三項，不能只按同日日期排序。 |
| C14 | PLAN L2759–2773 | main #110 346ebb64 / 9d51a3c8 五檔 paused B-1 preservation；#108 a59b0aef 與 L2734–2755 的 2A delivery | 只更正 durability/dirty-attribution；CHANGES_REQUESTED / PAUSED_BEHIND_M4、owner 拒絕縮為一 consumer 的決定保持，不把 preservation 當 B-1 acceptance。 |
| C15 | PLAN L3000–3001 | PLAN L1372–1403：一個具名 consumer accepted apply / natural receipt field verification；L1417–1429 明確不宣稱 rollout complete | 第一個 bounded verification 與全 fleet rollout 分開，兩者都不延伸為現在 consumer 全部已採用。 |
| C16 | PLAN L3003–3021 | main #16 61111f5f / 7f47b12f；本輪 owner step 1 四個 temp artifacts / step 2 to PR | 舊 P0b 一次交付清單保留 history；持續 PR trigger / critical-drift fail-closed / main-push audit / regression / unchanged-surface 條件在根 M3003 原文保留，不重新開 CI/gate work。 |
| C17 | PLAN L3430–3433 | main #155 3be20695（integrates feature 09248cb4 with main a6a2d622） | 只記已 merge 事實；保留當時 continuous push/PR/review/conditional merge 的精確整合授權，不能延伸本輪 merge 或 deployment。 |

### Decision framework merged versus consumer adoption — 2026-11-16

Scope: coordinator delivery record 2026-11-15/16, corroborated by main first-parent merges through 6c7e24c3. Claim ceiling: framework merged, consumer adoption and verification gaps are separate. Private consumers are not named.

Claim ceiling: framework deliveries and their separately tracked follow-ups:
| Framework merged | Commit | Delivered scope / limit |
|---|---|---|
| #315 | 8765bad6 | 拒 linked worktree apply（兩 backend）；dry-run 可用; write side，read side 見 D9 |
| #316 | 19de5d07 | AGENTS byte helper、agents_context_budget drift、root 32182→27298; &gt;32768 critical / exact 32768 pass；CRLF worst-case advisory；其他 instruction 檔未覆蓋；consumer 升級可 fail closed |
| #314 | 9726ac58 | ordered backlog counts P1=4/P2=6; 摘要 scope 由 D11 擴展，舊交付不刪 |
| #312 | b32a45d6 | CLAUDE short engineering explanation rule; 未觀察效果，等 3–5 natural reports；consumer template/starter pack 未更新 |
| #311 | f80a5345 | consumer AGENTS pointers；F-7 budget stage; No follow-up recorded (—); original #309 limits and validation ceiling remain separate. |
| #323 | 73145303 | install/verify/repair single classification；adapter declaration; configuration only；native Stop bypass/double closeout 未觀測；#319 consumer 未改 |
| #322 | 5f68a531 | report-only Codex hooks/list trust diagnostic; trusted ≠ executed；installed_modified unit-only；adoption summary 不主動啟 app-server |
| #321 | 7da58f1a | pre-commit/pre-push use declared initialized pinned local framework; 不證 submodule working-tree immutable；Copilot lifecycle bridge 仍 shared root |
| #320 | 4ef0f998 | post-upgrade size prediction；dry-run-first managed duplicate slimming; 無 consumer 改動；differing duplicates refuse，需要人選版本；另一 consumer main 尚待檢查 |
| #318 | f785d85f | full open/in-progress/constraints/decisions/completed boundaries/index; correctness only；summary-first 未證成本下降；約194KB vs227KB |
| #317 | 6c7e24c3 | opt-in --compress-output；passing logs lossless gzip; default 不變；是否自動化是 owner decision；fail log 保持 plain text |

Claim ceiling / consumer status: one private Codex consumer separately adopted f80a5345 (AGENTS.md 34,400 → 25,068 on-disk bytes); no consumer has adopted batch 2 according to the coordinator record. No consumer was read or modified in this round. A private consumer with differing managed duplicates needs a human version choice and separate consumer-change authorization; another private consumer still needs its main/pin checked.

Claim ceiling / verification gaps and follow-ups outside this DONE: Copilot lifecycle bridge still reads the shared root; #321 proves copy selection, not an unmodified submodule worktree; #319 native Codex Stop bypass/double closeout remains unobserved; #246 installed_modified is unit-tested only and trusted is not executed; observe the next 3–5 natural Claude reports for #312, whose consumer template/starter pack remain unchanged; #324 stays Draft (24/24 correct, uncached input +12% and slower), to be reconsidered after this restructure with no load-rule change here; #313 remains Draft/analysis-only, not a Gate 3 claim; #317 compression stays opt-in and automatic use remains an owner decision. #311 has no follow-up recorded, not an unknown follow-up.

## Pending Work - Ordered

Claim ceiling: These are tracked original intents and holds, not authorization to execute them in this PLAN round. Current work stays in Current Sprint. A source-stated existing grant is not re-requested; a source-stated missing grant or prerequisite is not inferred from a checkbox.

### Decision E2 retrospective evidence — 2026-06-12

Scope: the two original engineer onboardings. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P1 - E2 retrospective evidence:

- [ ] **M1738 · Collect retrospective E2 adoption evidence from the two engineer.** Claim ceiling (verbatim):
  Claim ceiling: P1 - adoption evidence collection (E2-relevant; evidence class, not
presentation class):
  Claim ceiling: Collect retrospective E2 adoption evidence from the two engineer
  onboardings: onboarding artifacts from their environments, friction log
  (time to green smoke, walls hit, remediation source), and author
  intervention count declaration.
  Claim ceiling: Record evidence grade explicitly as retrospective / self-reported.
  Claim ceiling: Do not claim sustained lifecycle, E2 closure, or low framework
  friction from this evidence alone.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1745-L1746)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1748-L1751)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1752-L1752)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1753-L1754)

### Decision R1 identity normalization P2 — 2026-09-04

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - R1 identity normalization P2:

- [ ] **M0363 · R1 whitespace identity normalization P2.** Claim ceiling (verbatim):
  Claim ceiling: Known non-blocking P2 carried forward: daily-only versus multi-surface CLI
  invocation can derive different daily record identities from otherwise
  identical whitespace-bearing inputs. This delivery does not change
  daily-only identity normalization semantics.
  Claim ceiling: This records bounded R1 implementation delivery only. It does not establish
  R1 qualification or authorize RAG or any later lifecycle slice.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L373-L378)

### Decision NSI-N0 minimal spike — 2026-09-04

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - NSI-N0 minimal spike:

- [ ] **M0388 · NSI-N0 freshness spike.** Claim ceiling (verbatim):
  Claim ceiling: Next candidate: one separately authorized minimal technical spike to determine
  the smallest persisted freshness evidence capable of mechanically classifying
  Session B as same, changed, or unverifiable relative to Session A. The spike
  may conclude that no safe bounded representation exists.
  Claim ceiling: Claim ceiling: feasibility and representation decision only. No reader,
  adapter, attachment writer, schema, instruction ledger, bootstrap, migration,
  Session A/B pilot, RAG, lifecycle expansion, Runtime change, governance
  authority, enforcement, or merge is authorized.
  Claim ceiling: Acceptance requires exact-head independent review with no unresolved P0/P1,
  green scope-matched checks, reviewed-head preservation, and separate owner
  merge authorization.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L398-L408)

### Decision Maintenance queue owner adjudication — 2026-08-14

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P1 - Maintenance queue owner adjudication:

- [ ] **M0515 · 14 undetermined maintenance entries.** Claim ceiling (verbatim):
  Claim ceiling: Owner adjudicates the 14 `undetermined` entries in the maintenance queue
  ledger. Each already carries a recommended disposition; what is undetermined
  is whether a script can confirm the surface exists, not what to do with it.
  The owner decides whether to accept each disposition, name the canonical
  target where the recommendation is `merge`, and authorise any change.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L525-L529)

### Decision Three reviewed corrections — 2026-08-14

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P1 - Three reviewed corrections:

- [ ] **M0520 · Publish the three reviewed weekly-report corrections: PR #26 narrowed to.** Claim ceiling (verbatim):
  Claim ceiling: Publish the three reviewed weekly-report corrections: PR #26 narrowed to
  structural session-binding rejections only, all G4 maturity percentages
  removed, and the consumer-surface claim narrowed from "consumer repos" to the
  single submodule consumer that exercised the path.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L530-L533)

### Decision Selected-checkpoint CFU verification — 2026-08-14

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P1 - Selected-checkpoint CFU verification:

- [ ] **M0524 · CFU selected-checkpoint transfer verification.** Claim ceiling (verbatim):
  Claim ceiling: Run CFU transfer verification against a deliberately selected framework
  checkpoint, in a clean isolated worktree via F-7. The selected checkpoint is
  not "latest" and must not be described as such; CFU's own worktree carries
  unrelated modifications and must not be updated in place.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L534-L537)

### Decision PR-body drift disposition — 2026-08-14

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P1 - PR-body drift disposition:

- [ ] **M0539 · PR-body drift response.** Claim ceiling (verbatim):
  Claim ceiling: The quoted "this PR" and third occurrence belong to the original PR-description drift checkpoint, not this repair. This restores the failure referent only; the retained owner-decision and separate-approval limits remain unchanged.
  Claim ceiling: Reviewer-facing body drift has now occurred three times: PR #57, PR #60, and
  this PR's original description. In each case the branch content was corrected
  while the pull request description continued to publish withdrawn claims, and
  every instance was caught by external review, none by CI. This is a
  manual-copy failure, and the honest response is to stop retyping numbers that
  already exist in an artifact. The third occurrence admits an owner decision
  only; it does not authorise a gate, generator or new surface. Any
  implementation still requires separate owner approval and must first
  disposition PR #28.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L549-L557)

### Decision Learning-loop implementation pause — 2026-06-18

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - Learning-loop implementation pause:

**M1060 · Learning-loop implementation.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling for the above: learning-loop implementation remains paused and
advisory-only; OQ-1/OQ-2 resolved does NOT open Gate 3; no banking, replay
runner, CI/completion gate, or enforcement exists.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1070-L1072)

### Decision Census value and bilateral endpoint — 2026-07-14

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - Census value and bilateral endpoint:

- [ ] **M1300 · eToken composite-workspace report-only census.** Claim ceiling (verbatim):
  Claim ceiling: Deferred follow-up: observe normal-user census use before claiming G4 value,
then request a separate owner decision on any bilateral membership endpoint.
Do not expand F-7 from this completed tranche.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1310-L1312)

### Decision Manifest-driven fleet enumeration — 2026-06-12

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - Manifest-driven fleet enumeration:

- [ ] **M1625 · Manifest-driven fleet enumeration.** Claim ceiling (verbatim):
  Claim ceiling: Scope manifest decision recorded: a manifest extending
  `governance/fleet/governance_scope.yaml` (which today classifies tiers
  but does not enumerate members) is the correct long-term single
  source; migrating the generator to manifest-driven enumeration is
  DEFERRED until the first real membership change requires it
  (failure-driven; no tool change in this slice).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1635-L1640)

### Decision Repo-class SLA — 2026-06-12

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - Repo-class SLA:

- [ ] **M1631 · Repo-class SLA.** Claim ceiling (verbatim):
  Claim ceiling: Repo-class freshness SLA (P1-H Option C) remains deferred until
  this taxonomy survives at least one real membership decision.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1641-L1642)

### Decision GitHub topics exact list — 2026-06-13

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - GitHub topics exact list:

- [ ] **M1769 · GitHub topics.** Claim ceiling (verbatim):
  Claim ceiling: Add relevant topics. (Gated by P2-E: allowed only after exact-list
  ratification; descriptive taxonomy nouns only.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1779-L1780)

### Decision README badge first gated release — 2026-06-13

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - README badge first gated release:

- [ ] **M1771 · README badge.** Claim ceiling (verbatim):
  Claim ceiling: Align README badge with current release state. (P2-E decision:
  DEFERRED until the first gated release exists; no badge before that.)
  Claim ceiling: README badge: DEFERRED. A badge must reflect a real, gated release
  state; no release currently passes release-notes gating, so any badge
  now is decoration or inflation. Revisit at the first gated release.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1781-L1782)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1876-L1878)

### Decision Skill study funding and integrity — 2026-07-28

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - Skill study funding and integrity:

**M1934 · Engineering Skill funding / Gate 2 integrity.** Claim ceiling (verbatim):
Claim ceiling: P3 - Engineering Skill Program, pre-push bug study (Gate 1 complete; Gate 2 process integrity not established; Skill effectiveness not claimed):
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1944-L1944)

### Decision M3-b-2B native integration — 2026-08-26

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - M3-b-2B native integration:

- [ ] **M2743 · M3-b-2B native integration.** Claim ceiling (verbatim):
  Claim ceiling: M3-b-2B still owns native process/job/scratch/pipe integration and has not
  begun.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2753-L2754)

### Decision M3-b-3 reconstruction — 2026-08-26

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - M3-b-3 reconstruction:

- [ ] **M2745 · M3-b-3, the reconstruction call, is **unblocked as authority**, and that.** Claim ceiling (verbatim):
  Claim ceiling: M3-b-3, the reconstruction call, is **unblocked as authority**, and that
  authority is now in `main`: BLOCKED-1 (`fa10dda8`) gave it a defined callee and
  BLOCKED-2 (`4ea55d3e`) a defined verification contract. What remains is that it
  be written and reviewed — and it owns the parent-side result object with the
  two "not asserted" markers, which the BLOCKED-2 amendment requires and does
  not build.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2755-L2760)

### Decision M4 historical verification — 2026-08-26

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - M4 historical verification:

- [ ] **M2756 · M4.** Claim ceiling (verbatim):
  Claim ceiling: M4 follows, and is what lets a historical candidate be verified against
  materialized historical bytes instead of against the live worktree — which is
  what B-1 is waiting for.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2766-L2768)

### Decision Historical keyring sequence — 2026-09-04

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P3 - Historical keyring sequence:

**M2795 · original 2026-09-04 non-exposure keyring continuation; staging/runtime state not re-observed.** Claim ceiling (verbatim):
Claim ceiling: Current order: commit the staged runner keyring wiring, refresh R1 generation
  8, rebound only the dry-run wrapper HEAD/runner pins, then separately
  authorize the second real non-exposure dry-run. This reconciliation authorizes
  no Login, credential read/copy/mutation, live execution, Attempt, or Gate 3
  success claim.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2805-L2809)

### Decision Memory-quality reviewer agreement — 2026-07-27

Scope: only the original named work and its original authorization, if any. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

P2 - Memory-quality reviewer agreement:

- [ ] **M2928 · Memory quality reviewer agreement.** Claim ceiling (verbatim):
  Claim ceiling: Memory quality measurement claim ceiling: the recent-20 baseline and causal
audit are single-annotator, retrospective observations. Reviewer agreement
remains pending; the sample is concentrated in four work items and is not G4
outcome evidence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2938-L2941)

## Active Claim Boundaries

### Decision cache-aware and census boundaries — 2026-07-22

Scope: fixed validator-delegation census, eToken composite-workspace report-only census, and repo-feasible authority-manifest candidates. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0653 · fixed validator-delegation census: e737572e / 197 modules.** Claim ceiling (verbatim):
Claim ceiling: The published census artifact is intentionally frozen to base
  `e737572e`, `population_count=197`, and normalized hash
  `b590fb5fef8dc1a921655877091447a44f42232219c8d91c3a413f467e74da6f`.
  This remains a historical fixed snapshot only; it does not claim coverage
  of any later tip, and it does not authorize delegation implementation,
  retirement, migration, or external adoption.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L663-L668)

- [x] **M0659 · fixed validator-delegation census: e737572e / 197 modules.** Claim ceiling (verbatim):
  Claim ceiling: No further census action is currently authorized. The fixed-snapshot
  claim boundary remains in force until a separate owner-approved slice
  explicitly authorizes refresh or downstream use.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L669-L671)

**M0670 · Cache-aware docs phase collected the harness/repo/enforcement boundary:.** Claim ceiling (verbatim):
Claim ceiling: Cache-aware docs phase collected the harness/repo/enforcement boundary:
  prompt cache, compaction control, deferred tool loading, and mode-as-tool-call
  remain HARNESS-only; repo-feasible work is limited to reviewer-facing
  detection/accountability artifacts.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L680-L683)

**M0674 · Cache-aware receipt alignment clarified that `REVIEW_RECEIPT`,.** Claim ceiling (verbatim):
Claim ceiling: Cache-aware receipt alignment clarified that `REVIEW_RECEIPT`,
  mode/auth, tool-denial, and compaction receipts remain candidate/PENDING
  evidence unless a later adopted contract changes their authority.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L684-L686)

**M0677 · Operator prompt playbook now records daily rules that keep sub-agent.** Claim ceiling (verbatim):
Claim ceiling: Operator prompt playbook now records daily rules that keep sub-agent
  receipts evidence-only and keep push, memory write, and cross-repo write under
  main-thread gates plus explicit authorization.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L687-L689)

**M0683 · AUTHORITY_MANIFEST implementation tech spec narrowed the tranche:.** Claim ceiling (verbatim):
Claim ceiling: AUTHORITY_MANIFEST implementation tech spec narrowed the tranche:
  derive from or extend `.governance/baseline.yaml`, summarize
  `governance_drift_checker.py` semantics, and do not create a parallel
  authority map.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L693-L696)

**M0691 · Read-only AUTHORITY_MANIFEST preflight consumer simulation implemented.** Claim ceiling (verbatim):
Claim ceiling: Read-only AUTHORITY_MANIFEST preflight consumer simulation implemented
  with focused tests. It emits reviewer-facing `reuse_candidate`,
  `reload_required`, `cache_unsafe`, and `not_checked` decisions without
  provider cache integration or enforcement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L701-L704)

**M0695 · CHANGELOG Unreleased entries record both AUTHORITY_MANIFEST candidate.** Claim ceiling (verbatim):
Claim ceiling: CHANGELOG Unreleased entries record both AUTHORITY_MANIFEST candidate
  generator and preflight consumer surfaces without version bump, release
  publish, prompt-cache behavior, runtime hooks, CI/pre-push/gates, or
  enforcement claims.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L705-L708)

**M0712 · Retrieval Authority Round A and Cache-Aware Round B design clusters were.** Claim ceiling (verbatim):
Claim ceiling: Retrieval Authority Round A and Cache-Aware Round B design clusters were
  consolidated into summary/index docs with source-note pointer banners and
  classification metadata. Source notes remain preserved; they were not
  archived, invalidated, or reclassified by the pointer update.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L722-L725)

**M0720 · `docs/governance/context-cost-budget-design-2026-07-06.md` separated.** Claim ceiling (verbatim):
Claim ceiling: `docs/governance/context-cost-budget-design-2026-07-06.md` separated
  per-slice context-read budgeting from the decision-change ledger so
  agent-read telemetry does not pollute defense-output classification.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L730-L732)

**M0860 · Decision note keeps the AUTHORITY_MANIFEST preflight path in Unreleased.** Claim ceiling (verbatim):
Claim ceiling: Decision note keeps the AUTHORITY_MANIFEST preflight path in Unreleased
  candidate-only state until a named real harness consumer and evidence
  contract are separately scoped:
  `docs/governance/authority-manifest-preflight-evidence-decision-2026-07-02.md`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L870-L873)

**M0864 · Decision note defines the evidence boundary for v1.3.0 release-prep:.** Claim ceiling (verbatim):
Claim ceiling: Decision note defines the evidence boundary for v1.3.0 release-prep:
  release-surface consistency and consumer-side proof are required before any
  release-prep slice can start:
  `docs/governance/v1.3.0-release-prep-evidence-boundary-2026-07-02.md`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L874-L877)

**M0883 · Claim ceiling for this sprint:.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling for this sprint:
Claim ceiling: CLAIMED: cache-aware planning and the first repo-feasible implementation
  tranche are documented and implemented as read-only candidate tooling:
  AUTHORITY_MANIFEST generation, authority-change invalidation, and preflight
  consumer simulation.
Claim ceiling: CLAIMED: report-only test-signal quality audit visibility exists for domain
  contract repos, with v0.2 fixture-manifest and fixture-runner reporting.
Claim ceiling: CLAIMED: governance-overhead analysis has seed artifacts for decision-change
  classification and context-cost design.
Claim ceiling: CLAIMED: a bounded validator-delegation census fixed snapshot was published
  as a historical artifact pinned to `e737572e` / 197 modules, with no
  delegation, retirement, migration, or adoption authority attached.
Claim ceiling: NOT CLAIMED: prompt cache implementation, cache hit/miss monitoring,
  compaction control, mode/auth/tool-denial receipt tooling, runtime hook/CI
  wiring, enforcement, canonical authority promotion, external harness
  adoption, v1.3.0 release readiness, cross-repo writes, automatic test-quality
  enforcement, industry-grade test proof, noisy-surface retirement, measured
  token savings, context-cost compliance, current-tip census coverage, or any
  actionability derived solely from the census artifact.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L893-L912)

**M1114 · CLAIMED: cache-aware governance surfaces have been classified into.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: cache-aware governance surfaces have been classified into
  HARNESS-only, REPO-feasible, and ENFORCEMENT-limited boundaries.
Claim ceiling: CLAIMED: the first repo-feasible implementation tranche exists as read-only
  candidate tooling: `AUTHORITY_MANIFEST v1` generator, base/head
  authority-change invalidation signal, and AUTHORITY_MANIFEST preflight
  consumer simulation.
Claim ceiling: CLAIMED: generator semantics derive from existing `.governance/baseline.yaml`
  and `governance_drift_checker.py` surfaces instead of creating a competing
  authority map.
Claim ceiling: NOT CLAIMED: prompt cache is implemented, cache hit/miss is monitored,
  compaction is controlled by this repo, candidate receipts are authoritative,
  CI/runtime/pre-push/gate enforcement is wired, external harnesses have
  adopted the cache-aware specs, or v1.3.0 release-prep is justified.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1124-L1136)

**M1283 · eToken composite-workspace report-only census.** Claim ceiling (verbatim):
Claim ceiling: Independently review and approve the eToken-only composite workspace
  authority tech spec while preserving repository sovereignty, discovery-only
  IDE evidence, and repo-local F-7 completion semantics.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1293-L1295)

**M1286 · eToken composite-workspace report-only census.** Claim ceiling (verbatim):
Claim ceiling: Implement the report-only census in `6e4e5439` with an explicit
  coordinator root and sibling allowlist; keep every valid membership
  `unratified` and prohibit consumer writes, F-7 invocation, commit, and push.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1296-L1298)

**M1289 · eToken composite-workspace report-only census.** Claim ceiling (verbatim):
Claim ceiling: Run the census against isolated copies of the three eToken repositories;
  confirm the four-line human conclusion and JSON agree with
  `E2-CONSUMER-03`, with the original consumer repositories unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1299-L1301)

**M1295 · eToken composite-workspace report-only census.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling: the report-only census exists and exposes per-repository gaps.
It does not establish bilateral membership, workspace governance authority,
workspace-wide F-7, G4 operator value, or general fleet demand. The live eToken
census JSON was not retained as a durable tracked receipt.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1305-L1308)

**M1308 · Record that `AUTHORITY_MANIFEST v1` must reuse or extend the existing.** Claim ceiling (verbatim):
Claim ceiling: Record that `AUTHORITY_MANIFEST v1` must reuse or extend the existing
  `.governance/baseline.yaml` plus `governance_drift_checker.py` path.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1318-L1319)

**M1311 · Before implementation, confirm high-rigor review boundary for a read-only.** Claim ceiling (verbatim):
Claim ceiling: Before implementation, confirm high-rigor review boundary for a read-only
  authority manifest generator plus focused tests.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1321-L1322)

**M1318 · Document that the preflight path remains Unreleased candidate-only until.** Claim ceiling (verbatim):
Claim ceiling: Document that the preflight path remains Unreleased candidate-only until
  a named real harness consumer and evidence contract are separately scoped.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1328-L1329)

**M1321 · Non-goals for this pending work:.** Claim ceiling (verbatim):
Claim ceiling: Non-goals for this pending work:
Claim ceiling: Do not implement prompt cache, runtime hooks, CI/pre-push/gate enforcement,
  baseline rewrites, memory behavior, release publishing, or cross-repo writes
  as part of the first tranche.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1331-L1335)

### Decision G4 and observation ceilings — 2026-07-24

Scope: natural-work-item reporting and bounded observer surfaces. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0699 · Hermes no_agent local observer claim ledger updated to.** Claim ceiling (verbatim):
Claim ceiling: Hermes no_agent local observer claim ledger updated to
  `observed_six_scheduled_runs` for job `025890509ebf`, based on six
  scheduled artifacts from 2026-06-25 through 2026-06-30 while preserving
  non-claims for reliability, SLA, provider-free runtime, governance authority,
  enforcement, and future scheduled success.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L709-L713)

**M0704 · Report-only `test_signal_quality_audit` tooling reached v0.2: domain.** Claim ceiling (verbatim):
Claim ceiling: Report-only `test_signal_quality_audit` tooling reached v0.2: domain
  contract repos can be scanned for validator fixture pairing, fixture-manifest
  expected-result mapping, placeholder validator labeling, fixture-runner
  presence, lexical weak-test signals, and explicit cannot-claim boundaries.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L714-L717)

**M0708 · Consumer-facing update instructions now surface semantic test-quality.** Claim ceiling (verbatim):
Claim ceiling: Consumer-facing update instructions now surface semantic test-quality
  expectations: no happy-path-only tests for non-trivial changes, independent
  expected values, regression tests for reproducible bugs when feasible,
  mock-only weakness, and validator pass/fail fixture expectations.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L718-L721)

**M0764 · G4 manual work-item case 001 records that response-readability line as one.** Claim ceiling (verbatim):
Claim ceiling: The exact case-001 artifact and v0.6 failure/replay named below identify "that response-readability line"; this is historical case evidence, not a new observation or grant.
Claim ceiling: G4 manual work-item case 001 records that response-readability line as one
  self-hosted early outcome signal rather than counting its sessions, commits,
  validation, and memory events as separate samples. It binds the natural
  failure, v0.6 response, owner replay acceptance, four owner interventions,
  observable delivery cost, recurrence boundary, and absent transfer evidence
  in `docs/status/g4-work-item-case-001-owner-summary-2026-07-22.md`. G4 remains
  unclaimed; no independent consumer, non-author, cross-repo, sustained, or
  benefit-over-cost conclusion follows from this case.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L774-L781)

**M0772 · The first cross-consumer G4 observation checkpoint groups five natural.** Claim ceiling (verbatim):
Claim ceiling: The first cross-consumer G4 observation checkpoint groups five natural
  work-item candidates across `Bookstore-Scraper`, `meiandraybook`, and
  `Enumd-private-vault` without counting sessions or commits as samples.
Claim ceiling: This is early multi-consumer outcome evidence only: G4, sustained outcomes,
  non-author independence, and benefit-over-cost remain unclaimed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L782-L789)

**M0780 · The 2026-07-24 successor checkpoint preserves the 2026-07-22 snapshot.** Claim ceiling (verbatim):
Claim ceiling: The new Bookstore case retains its `linked_commit=e478409` receipt-anchor
  warning; canonical memory binds the product correction to `c9cd494`.
  Enumd Phase I-R remains one continuing private-vault case, and Mei PR #9
  does not become a new sample from PR volume alone. Qualifying breadth remains
  two consumers; G4, sustained outcomes, independent review, comparable cost,
  and benefit-over-cost remain unclaimed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L790-L800)

**M1066 · Hermes adapter line reached mock-backend smoke coverage:.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Hermes adapter line reached mock-backend smoke coverage:
  adapter scaffold, accepted-input interface doc, deterministic stub runner,
  standard smoke registration, input-driven mock backend fixture, fail-closed
  parse / allowlist behavior, and fixture disclaimer were committed with
  focused tests.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1076-L1080)

**M1077 · Claim ceiling for 2026-06-21 updates: Hermes remains mock-backend /.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling for 2026-06-21 updates: Hermes remains mock-backend /
accepted-input smoke only; no real Hermes model, hosted/local backend,
general code-writing runtime, model reliability, or non-bypassable governance
wrapping is claimed. CI claim-ceiling work is documentation-only; it does not
change workflow behavior, hooks, branch protection, or enforcement level.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1087-L1091)

**M1087 · CLAIMED: report-only domain-contract test-signal audit tooling exists in.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: report-only domain-contract test-signal audit tooling exists in
  `governance_tools/test_signal_quality_audit.py` and can surface validator
  fixture pairing, fixture-manifest expected-result mapping, fixture-runner
  presence, placeholder labeling, and weak lexical test-signal candidates.
Claim ceiling: CLAIMED: consumer-facing update instructions now state semantic test-quality
  expectations for non-trivial work and validator fixture pairs.
Claim ceiling: NOT CLAIMED: the framework proves any consumer repo has industry-grade tests,
  validates fixture truth, enforces test quality, changes readiness gates,
  rewrites consumer tests, or semantically proves behavior protection.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1097-L1105)

**M1099 · CLAIMED: `docs/governance/decision-change-ledger.seed.json` provides a seed.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: `docs/governance/decision-change-ledger.seed.json` provides a seed
  classification model and recent evidence-backed examples for whether
  governance outputs changed later decisions.
Claim ceiling: CLAIMED: `docs/governance/context-cost-budget-design-2026-07-06.md`
  separates per-slice context-read accounting from defense-output
  classification.
Claim ceiling: NOT CLAIMED: the inventory artifact by itself retires or downgrades any
  defense, proves the dispositions are globally complete beyond the recorded
  retire-candidate line, measures context savings, creates context-cost
  companion records, or enforces context-budget rules.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1109-L1120)

**M1164 · CLAIMED: Hermes accepted-input adapter surface, interface documentation,.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: Hermes accepted-input adapter surface, interface documentation,
  deterministic stub runner, standard smoke registration, and input-driven
  mock-backend fixture path with focused tests for fail-closed parse /
  allowlist behavior and response-file contract.
Claim ceiling: CLAIMED: the separate Hermes no_agent local observer line has
  `observed_six_scheduled_runs` for job `025890509ebf`, with six scheduled
  output artifacts from 2026-06-25 through 2026-06-30 and observation-only
  claim ceiling.
Claim ceiling: NOT CLAIMED: verified external Hermes governance compliance, true Hermes
  model integration, hosted/local backend reliability, model-generated
  tool-call reliability, general-purpose code-writing runtime completion,
  provider-free runtime, future scheduled success, or non-bypassable governance
  wrapping.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1174-L1186)

**M1274 · CLAIMED: Class C observation-only surfaces and same-provider visible I/O token.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: Class C observation-only surfaces and same-provider visible I/O token
  summaries where explicitly enabled.
Claim ceiling: NOT CLAIMED: billing truth, efficiency inference, cross-provider comparability,
  or decision-safe cost analysis.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1284-L1287)

### Decision F-7 and adoption limits — 2026-07-30

Scope: framework update skeleton, copy-based classification and bounded named-consumer evidence. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0575 · Close the F-7 update-available truth correction after PR #12 merged.** Claim ceiling (verbatim):
Claim ceiling: Close the F-7 update-available truth correction after PR #12 merged.
Claim ceiling: Preserve the distinction between backend update availability and the
  conservative full-adoption verdict.
Claim ceiling: Stop framework expansion unless a later consumer replay exposes a distinct
  failure.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L585-L589)

**M0596 · Run F-7 against a named real consumer only when the owner explicitly selects.** Claim ceiling (verbatim):
Claim ceiling: Run F-7 against a named real consumer only when the owner explicitly selects
  that consumer and authorizes the applicable report-only or update boundary.
Claim ceiling: Treat a new observed consumer failure as the prerequisite for further F-7
  framework changes.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L606-L609)

**M0601 · Claim ceiling:.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling:
Claim ceiling: CAN CLAIM: PR #12 is merged and the bounded disposable post-merge replay
  preserved truthful `update_available` reporting and the full adoption table.
Claim ceiling: CANNOT CLAIM: any real consumer is updated, full adoption is verified,
  report-only is enforcement, or the framework has reached G4 maturity.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L611-L616)

**M0998 · Consumer .gitignore hygiene: `adopt_governance.py` now ships a managed,.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Consumer .gitignore hygiene: `adopt_governance.py` now ships a managed,
  idempotent, non-destructive artifact/pyc ignore block to consuming repos on
  adopt and `--refresh`, so a consumer no longer goes permanently dirty from
  regenerated runtime artifacts / tracked `.pyc` (root-caused from
  gl_electron_tool F-7 evidence). Memory is intentionally not ignored. Covers
  the adopt/refresh path only; already-adopted repos must re-run refresh + a
  one-time `git rm --cached`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1008-L1014)

**M1005 · F-7 updater hygiene: `external_governance_submodule_updater.py` now also.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: F-7 updater hygiene: `external_governance_submodule_updater.py` now also
  ensures the same managed `.gitignore` block on the managed-updater path
  (dry-run reports a `gitignore_hygiene` field; apply writes + stages
  `.gitignore`), reusing the canonical block from `adopt_governance` (single
  source, no drift). Reported as an advisory field, intentionally NOT folded
  into `final_status` (the 5-layer contract is unchanged). Both adopt/refresh
  and the F-7 updater now carry hygiene; already-dirty repos still need a
  one-time `git rm --cached`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1015-L1022)

**M1147 · CLAIMED: framework-side role-aware orchestrator skeleton and external contract.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: framework-side role-aware orchestrator skeleton and external contract
  apply-path scaffold; submodule consumer apply path refreshes repo-local
  instructions, memory workflow router coverage, and managed hook advisory
  coverage.
Claim ceiling: NOT CLAIMED: fleet rollout, all repo roles verified, all external repos
  upgraded, external readiness completion, validators changed, artifact schema
  changed, or existing memory normalized.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1157-L1163)

**M1240 · CLAIMED: consumer role taxonomy canonicalized in.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: consumer role taxonomy canonicalized in
  `docs/ADOPTION_MODEL.md` (submodule consumer, F-7 consumer, external
  contract repo, copy-based audit-only, unsupported/unknown), each with
  required evidence, allowed claims, prohibited claims, and upgrade
  path; copy-based consumers classified audit-only (classification and
  audit wording supported); classification-precedes-tooling rule.
Claim ceiling: NOT CLAIMED: copy-based update automation (unsupported; ceiling: not
  solved), any new tooling, fleet rollout, F-7 generality, or that
  classification of a class equals evidence of a consumer in it.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1250-L1258)

**M1748 · Classify whether copy-based consumers are supported, audit-only, or.** Claim ceiling (verbatim):
Claim ceiling: Current claim ceiling: not solved.
  Classification first; do not design support tooling before P1-C
  consumer evidence exists. (P2-C 2026-06-12: classified **audit-only**
  for classification/audit wording; automated update **unsupported**
  (zero copy-based consumer evidence). Canonical taxonomy in
  `docs/ADOPTION_MODEL.md`: five consumer classes each with required
  evidence, allowed claims, prohibited claims, upgrade path; sole
  upgrade path to managed updates is migration to submodule consumer;
  classification-precedes-tooling rule stated; aligned to P1-I scope
  sets with PLAN-wins precedence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1758-L1768)

### Decision memory dispatch and advisory scope — 2026-06-21

Scope: deterministic framework-side dispatch, guard reporting and no-write observations. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0964 · Convert repeated instruction-level failures into deterministic dispatch,.** Claim ceiling (verbatim):
Claim ceiling: Convert repeated instruction-level failures into deterministic dispatch,
  evidence, and reviewer-readable state without overclaiming enforcement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L974-L975)

**M0975 · `--fail-on-blocker` provides opt-in selective blocking for current.** Claim ceiling (verbatim):
Claim ceiling: `--fail-on-blocker` provides opt-in selective blocking for current
  completion blockers.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L985-L986)

**M0977 · `session_end_hook` exposes advisory `memory_workflow` surface.** Claim ceiling (verbatim):
Claim ceiling: `session_end_hook` exposes advisory `memory_workflow` surface.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L987-L987)

**M0980 · Managed `pre-commit` hook surfaces memory workflow as advisory only.** Claim ceiling (verbatim):
Claim ceiling: Managed `pre-commit` hook surfaces memory workflow as advisory only.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L990-L990)

**M0984 · F-7 submodule pointer update is demoted to a backend stage, not.** Claim ceiling (verbatim):
Claim ceiling: F-7 submodule pointer update is demoted to a backend stage, not
  full-update completion.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L994-L995)

**M1027 · P1-A selective CI blocker: CI-only current-diff.** Claim ceiling (verbatim):
Claim ceiling: P1-A selective CI blocker: CI-only current-diff
  `active_non_canonical_writer` blocker with `memory/**` workflow triggers
  and anti-bypass tests (`5deb8bb`).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1037-L1039)

**M1032 · Runtime ledger no-write mode: `AI_GOVERNANCE_NO_LEDGER_WRITE` /.** Claim ceiling (verbatim):
Claim ceiling: Runtime ledger no-write mode: `AI_GOVERNANCE_NO_LEDGER_WRITE` /
  `--no-ledger-write`; smoke path no longer writes tracked ledgers; skipped
  writes observable as `skipped_no_write_mode` (`9f7fa1e`).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1042-L1044)

**M1056 · Runtime ledger milestone export, manifest-only (`bf798d4`): BOM-safe,.** Claim ceiling (verbatim):
Claim ceiling: Runtime ledger milestone export, manifest-only (`bf798d4`): BOM-safe,
  advisory by default, `--strict` / `--include-raw` opt-in; export bundles
  are committable.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1066-L1068)

**M1140 · CLAIMED: framework-side implementation, tests, docs, hook advisory, session-end.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: framework-side implementation, tests, docs, hook advisory, session-end
  surface, and closeout receipt persistence.
Claim ceiling: NOT CLAIMED: fleet-wide enforcement, all external repos governed, historical
  memory debt resolved, or CI / hook blocking rollout.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1150-L1153)

**M1157 · CLAIMED: canonical writer, active-window guard summary, dispatcher routing,.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: canonical writer, active-window guard summary, dispatcher routing,
  and opt-in blocker path.
Claim ceiling: NOT CLAIMED: historical debt cleanup, blocking threshold readiness, semantic
  correctness of memory content, or global enforcement closure.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1167-L1170)

### Decision learning-loop freeze — 2026-06-18

Scope: OQ-1/OQ-2 taxonomy/advisory terminus and frozen Gate 3 criteria. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1040 · OQ-2 resolved: learning-loop terminus is advisory-only (record ->.** Claim ceiling (verbatim):
Claim ceiling: OQ-2 resolved: learning-loop terminus is advisory-only (record ->
  taxonomy/memory/eval/claim-boundary linkage -> warning signal); no re-run
  gate / CI / completion blocker.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1050-L1052)

**M1043 · OQ-1 ratified: layered taxonomy framework -- `semantic_failure`.** Claim ceiling (verbatim):
Claim ceiling: OQ-1 ratified: layered taxonomy framework -- `semantic_failure`
  (SF-code) is the primary reviewer-finding taxonomy; `scenario_type` is a
  separate replay-shape axis; `FAILURE_KINDS` is `result_disposition` only;
  cross-walks read-only, no flat merge, no fourth taxonomy.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1053-L1056)

**M1047 · Gate 3 opening criteria + schema-prep boundary defined in.** Claim ceiling (verbatim):
Claim ceiling: Gate 3 opening criteria + schema-prep boundary defined in
  `docs/LEARNING_LOOP_CONSOLIDATION_SPEC_2026-06-16.md`. Gate 3 is NOT opened
  (5 conditions unmet; binding = repeated drift trigger + owner unpause).
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1057-L1059)

**M1050 · Taxonomy-alignment prep advisory implemented (`483b920`) and hardened.** Claim ceiling (verbatim):
Claim ceiling: Taxonomy-alignment prep advisory implemented (`483b920`) and hardened
  for missing/malformed/BOM input (`7472cb2`): advisory-only, exit 0 unless
  `--strict`.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1060-L1062)

### Decision CI and mutation claim limits — 2026-06-21

Scope: in-repo current-diff checks and declared mutation topology. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1071 · CI enforcement claim ceiling documented in.** Claim ceiling (verbatim):
Claim ceiling: CI enforcement claim ceiling documented in
  `docs/governance/ci-enforcement-claim-ceiling.md`: push checks are
  post-facto detection/accountability; PR coverage is stronger; prevention
  claims require verified required checks / branch protection outside the
  workflow file.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1081-L1085)

**M1130 · CLAIMED: canonical mandate that mutation enforcement claims require an.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: canonical mandate that mutation enforcement claims require an
  explicit mutation contract.
Claim ceiling: Rule: No mutation contract = No enforcement claim.
Claim ceiling: A tool, workflow, hook, or validator may not claim mutation enforcement
  unless its mutation contract is explicitly documented, scoped, and testable.
Claim ceiling: NOT CLAIMED: mutation enforcement is implemented for every mutation surface,
  mutation contracts are complete, or mutation catalog presence is enforcement
  by itself.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1140-L1147)

**M1180 · CLAIMED: documentation of the current in-repo GitHub Actions boundary:.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: documentation of the current in-repo GitHub Actions boundary:
  push-triggered checks are post-facto detection/accountability; four heavier
  jobs are PR-only; branch protection / required-check settings are outside
  the workflow file and were not verified here.
Claim ceiling: NOT CLAIMED: prevention-grade enforcement, verified GitHub branch protection,
  required status checks enabled, local hooks installed everywhere, adapters as
  runtime sandboxes, or CI proof of framework correctness.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1190-L1196)

**M1190 · CLAIMED: CI-only current-diff `active_non_canonical_writer` blocker.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: CI-only current-diff `active_non_canonical_writer` blocker
  implemented (`5deb8bb`); hooks remain advisory; historical memory debt
  remains warning-only; reviewed and pushed to both remotes.
Claim ceiling: NOT CLAIMED: full memory workflow enforcement, full mutation protection,
  blocker class expansion, or fleet CI rollout.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1200-L1204)

**M1264 · CLAIMED: reviewer polling is manual / resume-triggered only; bounded.** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: reviewer polling is manual / resume-triggered only; bounded
  polling exists only as a behavior constraint in `.agent` role templates.
Claim ceiling: NOT CLAIMED: automatic reviewer polling, daemon behavior, or automated
  reviewer handoff.
Claim ceiling: Observed confusion (2026-06-12): thread append can create contradictory
  pending/final review states; reviewer protocols must use explicit FINAL
  verdict blocks or read-only extraction.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1274-L1280)

**M1340 · Reviewer polling recorded as explicitly manual / resume-triggered.** Claim ceiling (verbatim):
Claim ceiling: Reviewer polling recorded as explicitly manual / resume-triggered.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1350-L1350)

**M3003 · Delivered P0b CI operational conditions.** Claim ceiling (verbatim):
Claim ceiling: P0b was delivered via #16 / 61111f5f / 7f47b12f. Its one-time test/commit checklist is historical; these operational and preservation conditions remain binding in that slice's scope. No old CI/gate work is reopened and no required branch-protection context is added.
Claim ceiling: the existing canonical drift checker executes inside the required pull
  request `Phase Gate Verification` path and fails closed on critical drift;
Claim ceiling: protected and baseline-only changes trigger the governance workflow;
Claim ceiling: a main-push `Canonical Drift Post-Merge Audit` rechecks merged state without
  being added to branch-protection required contexts;
Claim ceiling: regression tests prove that an unrefreshed protected-file change is critical
  and that canonical refresh restores bookkeeping consistency;
Claim ceiling: the workflow and reviewer language state that hash consistency is not proof
  of owner authorization for a protected-file change;
Claim ceiling: runtime hooks, schemas, memory writer behavior, gate policy, branch
  protection configuration, F-7 behavior, and G4 claims remain unchanged;
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3013-L3031)

### Decision structured-memory freshness — 2026-06-13

Scope: policy-v1 manual structured-surface review and one point-in-time repair. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1706 · Define freshness / rollover policy for structured canonical memory files.** Claim ceiling (verbatim):
Claim ceiling: (Policy v1 canonicalized 2026-06-13:
  `docs/structured-memory-freshness-policy.md` — staleness defined as
  event-driven contradiction against PLAN at HEAD, not age; rollover is
  event-driven with no SLA and no scheduled refresh; repair only in a
  dedicated bookkeeping slice derived from PLAN plus the latest closure
  record, never from session narrative; mandatory pre-repair comparison
  surfaces with stop-at-diagnosis on PLAN/closure disagreement;
  post-repair claim ceiling is point-in-time consistency only.
  Policy-only slice: no writer, hook, validator, or automation change.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1716-L1725)

**M1716 · Define whether `PLAN.md` to structured-memory consistency should become.** Claim ceiling (verbatim):
Claim ceiling: (Decided 2026-06-13 in policy v1 §6:
  manual event-driven comparison now; advisory tooling deferred
  failure-driven; blocking enforcement remains a separate OP-HC-class
  decision with its own mutation contract. Not a validator today.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1726-L1730)

**M1723 · Follow-up (gated on policy v1 being canonical, which it now is):.** Claim ceiling (verbatim):
Claim ceiling: Policy definition and policy application must not share a
  slice. (Applied 2026-06-13: pre-repair comparison ran per §4 — PLAN
  at HEAD `ce6de50` vs closure record 2026-06-13, no disagreement, stop
  rule not triggered; file rewritten from PLAN + closure record only,
  with refresh provenance header; claim recorded as point-in-time
  consistency with PLAN as of `ce6de50` only. Not claimed: freshness
  solved, sync automated, future staleness prevented, writer compliance
  enforced.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1733-L1743)

### Decision Gate 2 process-integrity ceiling — 2026-07-28

Scope: retained formal execution artifacts and corrected process-integrity disposition. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0612 · Record the Evidence-Backed Engineering Skill Program as a review-only plan.** Claim ceiling (verbatim):
Claim ceiling: Record the Evidence-Backed Engineering Skill Program as a review-only plan
  before any Engineering Skill exists. The program is a method for studying
  whether mature engineering methods change agent outcomes; it does not assert
  that any method works.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L622-L625)

**M0626 · The candidate-method appendix classifies further methods as priority.** Claim ceiling (verbatim):
Claim ceiling: The candidate-method appendix classifies further methods as priority
  study, cross-cutting methods, or deferred study. Every appendix entry is a
  deferred candidate, not an implementation commitment or a roadmap.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L636-L638)

**M0629 · Gate 1 freezes the experimental Skill treatment packet as an experiment.** Claim ceiling (verbatim):
Claim ceiling: Gate 1 freezes the experimental Skill treatment packet as an experiment
  input only; a repo-visible provisional Skill may exist no earlier than
  Gate 3, and Gate 3 is a screening decision, not a powered inference.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L639-L641)

**M1940 · Gate 1 COMPLETE** — amendment v2 (verified named-ref bundle isolation;.** Claim ceiling (verbatim):
Claim ceiling: **Gate 1 COMPLETE** — amendment v2 (verified named-ref bundle isolation;
  producer-safe vs designer-only validator split; unified status) owner re-signed
  2026-07-24 and confirmed by a read-only re-review.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1950-L1952)

**M1943 · Gate 2 preflight answer-safe setup (Gate 2 preflight manifest 2026-07-24):.** Claim ceiling (verbatim):
Claim ceiling: Gate 2 preflight answer-safe setup (Gate 2 preflight manifest 2026-07-24):
  baseline bundle artifact built + verified (designer-side rebuild source only;
  the producer receives a sanitized allowlist export in a fresh object DB — tree
  36c346fa, 0 meta objects — NOT the raw bundle), execution order frozen [D,C,A,B]
  from seed 20260724, packet hashes re-verified, validator pins confirmed real,
  producer receipt template prepared.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1953-L1958)

**M1954 · Canonical promotion slice — DONE 2026-07-27.** The Gate 2 preflight.** Claim ceiling (verbatim):
Claim ceiling: Departing from the amendment v3 precedent, the
  amendment v4 status line was **not** edited: amendment v4's own sha256 is
  recorded as `files[1]` in the owner-signed candidate manifest, so editing it
  would invalidate the signature it carries (amendment v4 Section E). Owner
  chose the append-only method.
Claim ceiling: Promotion supersedes scorer-handoff v2 only; producer treatments, arm order,
  budgets, validators and scoring release gates are unchanged.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1964-L1977)

**M1986 · Owner granted destination-specific authorization and two independent live.** Claim ceiling (verbatim):
Claim ceiling: D, C and A
  completed with verified producer packets; B reached the frozen 1800-second
  wall-clock cap without a clean output commit or producer `result.json` and is
  recorded as `failed_timeout`. The runbook treats inability to complete as a
  legitimate result, so B was not retried and no synthetic scorer packet was
  created.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1996-L2006)

**M1997 · Terminal-timeout amendment admitted for a new run — 2026-07-28.** Claim ceiling (verbatim):
Claim ceiling: The old run is not salvageable or reinterpreted by this amendment.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2007-L2015)

**M2006 · Gate 2 execution artifacts preserved; process integrity.** Claim ceiling (verbatim):
Claim ceiling: The 2026-07-27 admission note quoted below is historical and superseded, not current admission or execution status. Its "two completed items above" are the original M1997 timeout-amendment item and M2006 execution-preservation item. Their later record does not establish scorer-before-mapping integrity or authorize another run.
Claim ceiling: **Gate 2 execution artifacts preserved; process integrity
  `NOT_ESTABLISHED`, corrected 2026-07-28.** Fresh master
  `gate2-formal-20260728-115533` passed resource and scorer admission on the
  exact pinned image.
Claim ceiling: Mapping release and all four packet/handoff reverifications are
  preserved, but the retained evidence has no create-once timestamp, digest,
  or receipt chain that independently proves both submissions preceded mapping
  release. The earlier process-integrity `PASS` is therefore withdrawn.
Claim ceiling: The corrected decision records process integrity as `NOT_ESTABLISHED` and
  Skill effectiveness as `NOT_CLAIMED`.
Claim ceiling: **Admission state recorded 2026-07-27 (owner-accepted scope).** The
    2026-07-25 admission canary (`canary-20260725T164626Z`) is a historical PASS
    report for **producer-channel** admission, including nine isolation checks
    (network none, read-only rootfs, all capabilities dropped, no-new-privileges,
    non-root uid, no host bind mount, tmpfs workspace, no docker socket, pinned
    image). Its recorded execution paths are under a `D:` root; this checkout does not
    contain that live JSON evidence and the run was **not reproduced locally**
    (Docker daemon not running at record time). **Scorer-side is NOT RUN**:
    `admission-canary/evidence-live/` contains `capture_scorer_packet.py`,
    `verify_scorer_packet.py` and tests, but zero execution artifacts — tool
    presence is not execution evidence. Therefore **resource admission is NOT
    complete**, Gate 2 has not started, and arm execution remains 0.
    Receipt: `artifacts/evidence/test-results/receipt-gate2-admission-state-20260727.json`.
    Claimable: a historical producer-channel admission report exists.
    This historical note is superseded for current admission status by the two
    completed items above. It remains valid historical evidence about what had
    not yet run at that earlier checkpoint.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2016-L2050)

**M2042 · Claim ceiling: formal master `gate2-formal-20260728-115533` preserves four.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling: formal master `gate2-formal-20260728-115533` preserves four
scorable outcomes, two scorer submissions, mapping release, a corrected
decision, and successful packet/handoff reverification. It does not
independently establish that both submissions preceded mapping release, so Gate
2 process integrity is not established. The product pre-push hook, frozen
baseline, shared runtime, CI, gates, and enforcement are unchanged. This one
pilot does not establish treatment or Skill effectiveness, does not constitute
independent consumer evidence, and does not establish framework-level G4.
Judge engineering-method / external-tool value only in the separately governed
Gate 3 analysis; do not begin bulk tool replacement from this result.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2052-L2061)

### Decision first-Skill principal and funding gate — 2026-08-20

Scope: principal feasibility before scorer-before-mapping engineering. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2803 · The goal remains to complete Gate 3 and test the first Bug Fix Engineering.** Claim ceiling (verbatim):
Claim ceiling: The goal remains to complete Gate 3 and test the first Bug Fix Engineering
Skill. The owner now reconciles the natural pilot's eight-step card with the
later nine-step program method as program Section 3 steps 1–7 and 9; step 8 is
omitted only because it governs Arm-D-only validator treatment and a natural
pilot has no experimental arms. This is a 2026-08-20 owner decision, not a
claim that the later program text caused the 2026-07-17 pilot record.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2813-L2818)

**M2810 · No scorer-before-mapping implementation is funded until a separately controlled.** Claim ceiling (verbatim):
Claim ceiling: No scorer-before-mapping implementation is funded until a separately controlled
external-pin authority is shown feasible for this repository. The decision must
name the chain writer, a genuinely independent pin controller, the durable
append-only surface, pin timing and contents, the mapping-release check, and
inadmissible sources. A second account controlled by the same natural person or
automation agent is not a different principal. The protection state that keeps
the coordinator from modifying, deleting, merging or force-updating the surface
must be checked and retained at pin time.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2820-L2827)

**M2819 · External-record absence, timeout, stale or mismatched bytes, unknown or changed.** Claim ceiling (verbatim):
Claim ceiling: External-record absence, timeout, stale or mismatched bytes, unknown or changed
protection state, a non-independent controller, or a pin created after mapping
release all fail closed. There is no temporary release and no retrospective
pin. If no qualifying principal and surface exist, this work stops with Gate 2
process integrity still `NOT_ESTABLISHED`; a local chain, another file in the
same output tree, same-agent memory or caller-supplied digest cannot replace the
missing authority.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2829-L2835)

**M2827 · First-Skill bounded funding consideration.** Claim ceiling (verbatim):
Claim ceiling: Only after that feasibility gate passes may the owner consider one bounded
tranche: the six create-once previous-digest events from randomization seal
through two scorer submissions and mapping release, plus one non-counted
rehearsal. That is the complete cost ceiling before a new owner decision. It
authorizes no counted pair, Skill promotion or broader runtime/native surface.
The historical Gate 2 run cannot be repaired retrospectively. A first counted
pair would begin, not complete, Gate 3; completion still requires at least three
separately originated natural bugs across two consumer repositories under the
accepted repeat rules.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2837-L2845)

### Decision provenance and quality-measurement limits — 2026-07-27

Scope: local Git commit-object provenance and a report-only mixed-scope observation. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2900 · Canonical memory CLI writer, runtime session-end writer, authority guard,.** Claim ceiling (verbatim):
Claim ceiling: Canonical memory CLI writer, runtime session-end writer, authority guard,
  and checkpoint baseline reader share one local Git commit-object provenance
  decision.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2910-L2912)

**M2903 · Hash-shaped text alone no longer creates `memory_binding: bound`;.** Claim ceiling (verbatim):
Claim ceiling: Hash-shaped text alone no longer creates `memory_binding: bound`;
  explicit invalid Git-worktree commits fail before memory mutation, while
  auto-detect failure and non-Git paths remain writable as unbound.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2913-L2915)

**M2906 · `mixed_scope_memory_binding` reports staged or commit-range closeout.** Claim ceiling (verbatim):
Claim ceiling: `mixed_scope_memory_binding` reports staged or commit-range closeout
  scopes that combine bound canonical memory with non-closeout paths. The
  signal remains report-only and is absent from hook, CI blocker, pre-push, and
  memory blocking policy.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2916-L2919)

**M2910 · Focused replay covers the CFU release-artifact mixed-scope must-fail case.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Focused replay covers the CFU release-artifact mixed-scope must-fail case
  and the product-commit then memory-closeout-commit must-pass case.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2920-L2921)

**M2916 · The causal audit found zero confirmed avoidable memory defects. Three.** Claim ceiling (verbatim):
Claim ceiling: Three
  apparent stale-at-write cases were `record_commit_artifact` false positives:
  `git blame` identifies when a prewritten record was committed, not when it was
  authored.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2926-L2929)

**M2920 · The admission gate was not met. Stop without adding an advisory prompt,.** Claim ceiling (verbatim):
Claim ceiling: The admission gate was not met. Stop without adding an advisory prompt,
  fresh-session replay harness, `governance_tools` validator, hook, CI, schema,
  or blocker.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2930-L2932)

**M2924 · Claim ceiling: Tranche 1 establishes local commit provenance consistency and a.** Claim ceiling (verbatim):
Claim ceiling: Claim ceiling: Tranche 1 establishes local commit provenance consistency and a
report-only mixed-scope observation. It does not prove remote delivery, memory
prose truth, Memory quality improvement, consumer replay outcomes, or G4 value.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2934-L2936)

### Decision expansion and nine retained constraints — 2026-11-16

Scope: existing failure-driven posture and August Kind A constraints. Status: nine August Kind A constraints still awaiting owner adjudication; kept in force unchanged. Claim ceiling: retained verbatim source conditions below.

**M0566 · No Graphiti work without a reproducible retrieval failure.** Claim ceiling (verbatim):
Claim ceiling: No Graphiti work without a reproducible retrieval failure.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L576-L576)

**M0567 · No plugin-framework expansion without a capability-extraction case.** Claim ceiling (verbatim):
Claim ceiling: No plugin-framework expansion without a capability-extraction case.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L577-L577)

**M0568 · No Gate 3 expansion while Gate 2 process integrity remains NOT_ESTABLISHED.** Claim ceiling (verbatim):
Claim ceiling: No Gate 3 expansion while Gate 2 process integrity remains NOT_ESTABLISHED.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L578-L578)

**M0791 · For every other framework-expansion direction, wait for a real consumer; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: For every other framework-expansion direction, wait for a real consumer
  failure or a new product need before opening a slice.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L801-L802)

**M0868 · Do not start v1.3.0 release-prep until the scoped release-surface; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Do not start v1.3.0 release-prep until the scoped release-surface
  consistency packet and named consumer-side proof packet are collected and
  reviewed.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L878-L880)

**M0876 · Use the completed inventory-line results as historical input only. Do; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Use the completed inventory-line results as historical input only. Do
  not merge, downgrade, or retire any governance surface without a separate
  authorized slice and evidence for the specific change.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L886-L888)

**M0879 · Context-cost companion candidate; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Keep any context-cost companion record as a future candidate only until
  there is evidence that per-slice summaries change review, implementation, or
  consolidation decisions without becoming their own governance overhead.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L889-L891)

**M1721 · Do not claim structured memory sync is solved by daily memory writer; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Do not claim structured memory sync is solved by daily memory writer
  completion alone. (Standing constraint; restated in policy v1 §5.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1731-L1732)

**M1836 · Publish a release only after release notes and claim ceiling are; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Publish a release only after release notes and claim ceiling are
  accurate. (P2-E adds: release notes must use the Claim class taxonomy
  and link `docs/REVIEWER_ENTRYPOINT.md`.)
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1846-L1848)

**M1927 · Maintain historical `missing_canonical_memory` / `unbound_memory` debt as; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Maintain historical `missing_canonical_memory` / `unbound_memory` debt as
  warning evidence unless a scoped cleanup is approved.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1937-L1938)

**M1929 · Keep CE-1D historical raw packet disposition separate from current runtime; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Keep CE-1D historical raw packet disposition separate from current runtime
  dirty ledgers.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1939-L1940)

**M1931 · Do not backfill receipts or rewrite memory history without reviewer-approved; still awaiting owner adjudication; kept in force unchanged.** Claim ceiling (verbatim):
Claim ceiling: Do not backfill receipts or rewrite memory history without reviewer-approved
  scope.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1941-L1942)

## Dirty Workspace Policy

### Decision dirty-workspace and Option B — 2026-06-18

Scope: runtime-ledger side effects, generated compatibility snapshot and conditional EOL residual. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M1198 · original no-write-smoke ceiling; ledger-tracking component superseded-by M2971 / Option B (C10).** Claim ceiling (verbatim):
Claim ceiling: CLAIMED: runtime smoke path supports no-write mode for tracked ledgers;
  skipped writes are observable as `skipped_no_write_mode`; explicit
  `session_end` default ledger writes preserved.
Claim ceiling: NOT CLAIMED: runtime ledger side-effect root redesign, workspace clean
  guarantee, tracked ledgers untracked/ignored/deleted, or elimination of
  all hook / pre-push side effects.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L1208-L1213)

**M2942 · `artifacts/governance/version_compatibility.json` is a generated.** Claim ceiling (verbatim):
Claim ceiling: `artifacts/governance/version_compatibility.json` is a generated
  compatibility snapshot, not the canonical source of version truth.
Claim ceiling: Source of truth: rerun `governance_tools.governance_version_check` /
  session-start version compatibility logic when reviewer-facing evidence is
  needed.
Claim ceiling: Ignoring the snapshot does not remove the need to verify version
  compatibility when a task claims version compatibility evidence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2952-L2960)

**M2952 · Known local EOL/status residual:.** Claim ceiling (verbatim):
Claim ceiling: `tests/test_governance_drift_checker.py` may appear modified on this Windows
  workspace because of local Git EOL/status behavior.
Claim ceiling: Treat this as a local hygiene residual, not a source diff, unless new evidence
  shows a real content change.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2962-L2970)

**M2964 · runtime ledgers artifacts/claim-enforcement/claim-enforcement-receipts.ndjson and artifacts/session-index.ndjson (scope source M2937).** Claim ceiling (verbatim):
Claim ceiling: Do not stage these files with documentation, memory workflow, or F-7 commits.
Claim ceiling: Treat them as runtime side effects unless explicitly audited for promotion.
Claim ceiling: Overall workspace remains NOT CLEAN while these files are dirty.
Claim ceiling: Do not claim workspace clean while the EOL/status residual remains visible.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2974-L2977)

**M2971 · the same two runtime ledgers named in M2964 / source M2937.** Claim ceiling (verbatim):
Claim ceiling: Delivered; grant consumed, not reusable. Original-slice behavior follows.
Claim ceiling: Option B selected: these two ledgers should become ignored-by-default runtime
  artifacts.
Claim ceiling: Durable reviewer-facing evidence must come from explicit audit / reviewer
  milestone export, not accidental runtime append commits.
Claim ceiling: Implemented 2026-06-18: ledgers untracked + ignored (`ffd9609`, local files
  kept); manifest-only milestone export tool added (`bf798d4`). No runtime
  writer / hook / validator / closeout change.
Claim ceiling: NOT CLAIMED: raw-snapshot export refinement, reviewer-handoff export
  integration (separate slices), historical evidence migration, workspace
  clean, or Gate 3 opening.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2981-L2990)

## Phase Overview

- [x] Phase A: Core governance tooling and baseline.
- [x] Phase B: Adoption, validators, freshness, and memory foundations.
- [x] Phase C: Runtime governance, DBL, and observation surfaces.
- [x] Phase D: Session workflow, external adoption, and reviewer entrypoints.
- [>] Phase E: Failure decision boundary, exclusion governance, and usage enforcement.

### Decision retained phase posture — 2026-11-16

Scope: existing A–D completed / E in progress and D sign-off. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0184 · Phase A: Core governance tooling and baseline.** Claim ceiling (verbatim):
Claim ceiling: Phase A: Core governance tooling and baseline.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L194-L194)

**M0185 · Phase B: Adoption, validators, freshness, and memory foundations.** Claim ceiling (verbatim):
Claim ceiling: Phase B: Adoption, validators, freshness, and memory foundations.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L195-L195)

**M0186 · Phase C: Runtime governance, DBL, and observation surfaces.** Claim ceiling (verbatim):
Claim ceiling: Phase C: Runtime governance, DBL, and observation surfaces.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L196-L196)

**M0187 · Phase D: Session workflow, external adoption, and reviewer entrypoints.** Claim ceiling (verbatim):
Claim ceiling: Phase D: Session workflow, external adoption, and reviewer entrypoints.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L197-L197)

**M0188 · Phase E: Failure decision boundary, exclusion governance, and usage enforcement.** Claim ceiling (verbatim):
Claim ceiling: Phase E: Failure decision boundary, exclusion governance, and usage enforcement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L198-L198)

**M0212 · Phase D completion note:.** Claim ceiling (verbatim):
Claim ceiling: Phase D completion note:
Claim ceiling: Reviewer closeout artifact was signed by Gavin0099 on 2026-04-28.
Claim ceiling: Later Phase C / runtime reconciliation gaps were tracked as follow-up work,
  not as a reason to inflate current Phase D claims.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L222-L226)

**M0218 · Phase E posture:.** Claim ceiling (verbatim):
Claim ceiling: Phase E posture:
Claim ceiling: Validity before expansion.
Claim ceiling: Failure-driven governance only.
Claim ceiling: No broad enforcement upgrade without observed failure and scoped evidence.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L228-L232)

**M0639 · Keep Phase E in validity-before-expansion posture while reducing governance.** Claim ceiling (verbatim):
Claim ceiling: Keep Phase E in validity-before-expansion posture while reducing governance
  noise and surfacing which defenses actually change decisions.
Claim ceiling: Treat the 2026-07-06 test-signal quality line as report-only visibility for
  consumer/domain-contract test evidence, not as a readiness gate.
Claim ceiling: Use decision-change and context-cost artifacts to decide what to keep,
  merge, downgrade, or investigate before adding more governance surface.
Claim ceiling: Preserve the 2026-06 cache-aware / AUTHORITY_MANIFEST line as candidate-only
  unless a named harness consumer and evidence contract are separately scoped.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L649-L656)

## Work Item Glossary

### Decision label glossary — 2026-11-16

Scope: traceability decoder for the existing work labels. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M0192 · Use this short decoder when reading historical or current PLAN labels.  A code.** Claim ceiling (verbatim):
Claim ceiling: Use this short decoder when reading historical or current PLAN labels.  A code
preserves traceability; the phrase states its purpose.  The checkbox and
nearby status text remain the authority for whether an item is complete.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L202-L204)

**M0196 · | Label | Plain-language purpose |.** Claim ceiling (verbatim):
Claim ceiling: Existing label definitions, verbatim; no status or permission changes.

| Label | Plain-language purpose |
| --- | --- |
| Phase A--E | Major work periods: core baseline; adoption/memory foundations; runtime observation; external adoption/reviewer workflow; and the current failure-boundary/exclusion/usage-enforcement line. |
| P0 / P1 / P2 | Priority groups; the letter identifies a work item within that group. |
| P1-C | First external F-7 verification for `meiandraybook`; the natural-session closeout-receipt check completed read-only on 2026-07-22, while its separate consumer memory blocker remains outside P1-C. |
| P1-D | Structured `plan_reconciliation` declaration for canonical memory records. |
| P1-E | Observation evidence for declaration behavior; it does not by itself authorize enforcement. |
| P1-F | Decision about stronger declaration enforcement. Decided 2026-07-18: keep advisory and do not add a current-diff blocker; reopen only after a natural post-Option-B `not_declared` failure. |
| P1-G / P1-H | Reproducible fleet-matrix generator / future decision about fleet-update freshness. |
| P2-E | Rules for public-facing release surfaces such as topics, badges, and release notes. |
| F-7 | Governed full framework update for a consumer repository, with staged evidence; a pointer update alone is not F-7 completion. |
| E2 | Retrospective external-engineer adoption evidence. It is usability/adoption evidence, not runtime-effectiveness proof. |
| Gate 3 | Frozen learning-loop unpause gate; it opens only under its documented criteria and explicit owner approval. |
| E1-B, E8A, CE-1C/1D, R49.x, Round A/B | Historical experiment, claim-enforcement, or retrieval/cache study labels. Read their linked artifact before treating them as active work. |
| v1 / v2 / v3 | Versions of the no-governance baseline experiment; their individual status and claim boundary are recorded in the current task and status artifacts. |
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L206-L220)

## Historical Milestone Index

This is navigation only. The immutable [history record](docs/status/plan-history-2026-11-16-6c7e24c3.md) contains the exact original 3,433-line / 227,054-byte PLAN at 6c7e24c3161fe80dc4c5bd6bfe1bec5cd04fd8dc behind a 10-line banner, including its NUL at original L2730. Its body SHA-256 is ec43ea501cd160302a328467858b0c09b3945e680dca5b96fbcd17d493b961eb. It must never receive tasks, refreshes, phase decisions or new owner authority.

Claim ceiling: The [preservation mapping](docs/status/plan-information-architecture-2026-11-16-mapping.md) identifies every original unit, retained clause, merged clause, grant source, conflict pair and legacy citation lookup. It is an immutable cutover account, not another backlog. If a Markdown viewer cannot display the NUL-bearing record, retrieve `git show 6c7e24c3:PLAN.md` and use original line numbers; do not replace the raw byte with display escaping.

Claim ceiling / completed orientation: Phase D sign-off; MEM-DISPATCH/P1-A; P1-C bounded natural receipt with separate consumer memory blocker; event-driven fleet taxonomy; advisory P1-F; report-only census/authority-manifest candidates; Gate 2 process integrity NOT_ESTABLISHED; consumed NON_SUCCESS Gate 3 pair; synthetic/native/materialization limits; Solo/Lite decision-support terminal and future-only P3/P5 scopes. These are not current execution instructions.

## Definition Of Done For Current Planning Slice

For the #213 Copilot closeout slice, each of the four reproduced gaps is fixed with a regression test that fails without the fix: a legacy turn Stop routed as session_end runs no generic closeout; missing or invalid agent input is recorded as a closeout audit, not as work; a session is consumed only after its closeout is accepted, the accepted bytes are bound to the validated object, and a changed accepted closeout is refused on replay; CHECKS_RUN treats a tool mention as a claim unless it is a negation, attribution, external evidence or documentation mention. The owner receives the final candidate SHA and change scope, independent review and CI for that SHA, and the old-#213 comparison. Any merge is outside this batch and requires a separate owner decision bound to the exact candidate SHA under [SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md](governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md). Do not automatically start backlog work.

The old P0b one-time delivery checklist is historical (#16, 61111f5f / 7f47b12f; source M3003). Its ongoing PR trigger, fail-closed, post-merge audit, regression and unchanged-surface conditions are retained in M3003 under Active Claim Boundaries; M3025 also preserves the hash-consistency/owner-authorization distinction.

## Cannot Claim From This PLAN Alone

### Decision PLAN-only evidence ceiling — 2026-11-16

Scope: what this planning document can establish. Status: retained source conditions; this round is selected by the first-screen instruction. Claim ceiling: retained verbatim source conditions below.

**M2988 · Claim-enforcement compact receipt boundary CE-1C / CE-1D: implemented with.** Claim ceiling (verbatim):
Claim ceiling: Claim-enforcement compact receipt boundary CE-1C / CE-1D: implemented with
  historical raw packet disposition still separated from current runtime ledgers.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L2998-L2999)

**M2990 · Response Envelope Contract and validator: implemented as structural reporting.** Claim ceiling (verbatim):
Claim ceiling: Response Envelope Contract and validator: implemented as structural reporting
  convention, not semantic enforcement.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3000-L3001)

**M2992 · Fleet governance scope and required-tier verification: implemented with.** Claim ceiling (verbatim):
Claim ceiling: Fleet governance scope and required-tier verification: implemented with
  prior 10/10 required verified evidence, not a permanent future guarantee.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3002-L3003)

**M2994 · F-7 submodule deterministic updater: implemented as a backend stage; full.** Claim ceiling (verbatim):
Claim ceiling: F-7 submodule deterministic updater: implemented as a backend stage; full
  update semantics require role-aware orchestration.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3004-L3005)

**M2996 · Memory canonical writer and memory authority guard: implemented with active.** Claim ceiling (verbatim):
Claim ceiling: Memory canonical writer and memory authority guard: implemented with active
  sentinel and warning-mode historical debt.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3006-L3007)

**M2998 · CodeBurn observation surfaces: implemented as Class C observation-only, not.** Claim ceiling (verbatim):
Claim ceiling: CodeBurn observation surfaces: implemented as Class C observation-only, not
  billing truth.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3008-L3009)

**M3025 · Cannot claim that all historical evidence was migrated into this file.** Claim ceiling (verbatim):
Claim ceiling: Cannot claim that all historical evidence was migrated into this file.
Claim ceiling: Cannot claim that external repos are updated.
Claim ceiling: Cannot claim fleet enforcement completion.
Claim ceiling: Cannot claim memory historical debt cleanup.
Claim ceiling: Cannot claim semantic verification of every historical milestone.
Claim ceiling: Cannot claim GitHub release / README / topics are current.
Claim ceiling: Cannot claim workspace clean while runtime ledgers remain dirty.
Claim ceiling: Cannot claim that a refreshed baseline hash proves owner authorization for
  future protected-file changes.
[source](docs/status/plan-history-2026-11-16-6c7e24c3.md#L3035-L3043)
