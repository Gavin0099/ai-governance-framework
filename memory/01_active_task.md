# Active Task

> Refreshed 2026-06-13 per `docs/structured-memory-freshness-policy.md`
> (dedicated bookkeeping slice; source surfaces: PLAN.md at HEAD
> `33f7694` + session closure records 2026-06-13 in `memory/2026-06-13.md`).
> Claim: point-in-time consistency with PLAN as of that commit only.

## Current Focus

- **No active autonomous slice.** All remaining public surfaces and
  enforcement upgrades are gated on explicit user decisions or external
  events.
- Standing principle: **Validity before Expansion** — do not claim
  enforcement, freshness, or adoption beyond the documented, validated
  surface.
- Standing handoff rule (session closure 2026-06-13): do not open GitHub
  topics, badge, or release publish opportunistically; all remaining
  public surfaces require explicit user ratification.
- Canonical claim ceiling (ratified 2026-06-13): this repo makes AI
  governance claims reviewable via contract, artifact, receipt, gate, and
  reviewer entrypoint — it does not provide full automatic runtime
  guarantee; several surfaces remain advisory or selective enforcement.

## Current Status

- **P2 external presentation core CLOSED (2026-06-13, arc a3a5731..d7301ed)**:
  README claim calibration with Claim class axis (P2-A), reviewer entry
  doc `docs/REVIEWER_ENTRYPOINT.md` (P2-B), adoption model taxonomy
  `docs/ADOPTION_MODEL.md` with copy-based classified audit-only (P2-C),
  starter-pack/onboarding-SOP English pass with Step 0 classification
  gate (P2-D), publish-surface decision checkpoint — publish surfaces
  are claim amplifiers (P2-E), GitHub description ratified C3 (P2-F)
  and human-applied, API-verified exact_match=True (P2-G). Agent
  metadata mutation: none; this environment has no GitHub metadata
  write path.
- **2026-06-13 second arc CLOSED (`1673f18`..`2756661`)**: rollback
  procedure doc `docs/fleet/governance-update-rollback.md`
  (observation-derived, never execution-tested), structured memory
  freshness policy v1 `docs/structured-memory-freshness-policy.md`
  (staleness = event-driven contradiction vs PLAN at HEAD, not age),
  first freshness repair of this file (bookkeeping slice at `9acb179`),
  deferred-debt report checkpoint (`ace5a62`, decision-only), deferred-debt
  report implemented (`2756661`, read-only tool + 12 tests; first run:
  281 records, not_declared=14, deferred=0, pre_field=249).
- **2026-06-13 third arc CLOSED (`1924de0`..`33f7694`)**: README English
  review pass — one claim-neutral readability edit, all claim ceilings
  verified intact (`1924de0`); README bilingual content parity — four
  English-only sections mirrored to Chinese half (one-line apply prompt,
  f7 key-documents row, Agent Runtime Governance Profile with all seven
  claim-ceiling clauses, Governance Artifact Discipline Index) plus
  Chinese intro claim calibration (removed 'enforceable') and trust model
  paragraph addition (`2493af9`, `6301918`). Mixed-commit (`a402122`)
  identified and remediated in-session; split into two clean boundary
  commits. Verdict: ACCEPT_WITH_CAVEATS for committed HEAD; workspace
  clean for review/commit purposes after excluding declared runtime
  ledgers.
- **Earlier 2026-06-12 arc remains closed**: P1-A selective CI blocker
  (current-diff `active_non_canonical_writer` only; hooks advisory),
  P1-D `plan_reconciliation` field, P1-G registered fleet matrix
  generator, P1-H event-driven fleet freshness, P1-I scope taxonomy.

## Pause Condition (Active)

Phase E expansion remains paused. Do NOT proceed to E2/E3 or add new
governance surfaces without an observable trigger (reviewer-confusing
ambiguity for E2; production incident for E3; unexplained replay
drift). Topology discovery must not become governance inflation.

## Next Steps (from PLAN at HEAD)

- **P1-E advisory FP/FN window**: passive; started 2026-06-12, matures
  ~2026-06-26 at the earliest. Only then does P1-F (blocking upgrade,
  OP-HC decision with its own mutation contract) become discussable.
- **Receipts schema 1.2 verification**: awaits a natural meiandraybook
  post-update session; explicitly pending, not failed. Do not
  manufacture a session for it.
- **P2-H GitHub topics**: closed-by-default; requires explicit user
  opening plus an independent ceiling check (topics are context-free
  claim surfaces that cannot carry qualifying clauses).
- **README badge / release publish**: badge deferred until the first
  gated release; release gated on Claim-class release notes linking the
  reviewer entrypoint.
- **E2 retrospective adoption evidence**: needs self-reported data from
  the two engineer onboardings (human input, evidence-class).
- **AB Cost Backfill**: frozen as `tooling_ready / evidence_pending`;
  unblock only with real scalar telemetry for 4 runs.
- **version_compatibility artifact promotion policy**: identified as
  governance debt (artifact is `artifacts/governance/version_compatibility.json`,
  classified manual-promotion, unsupported→compatible verdict flip);
  not yet sliced; requires independent governance decision — do not mix
  with docs commits.

## Historical Context Retained

- Phase D `passed` with reviewer closeout artifact signed `Gavin0099`.
- E1-A mutation catalog; E1-B Phase 2: topology discovery found 4/4
  catalog mutation scenarios vulnerable — discovery is not protection
  proof; mutation protection is not claimed.
- P1-C closed as post-apply evidence verification for meiandraybook
  (re-scoped, ratified); rollback chain observation
  `da1d4f3 -> 0eafe10 -> 554607f -> b14c15b` later became the rollback
  procedure doc's evidence basis.
- CodeBurn v1.1 baseline and Runtime Enforcement Attachment v0.1 are
  historical milestones, not active work.
- Mutation mandate canonical in PLAN: "No mutation contract = No
  enforcement claim."
