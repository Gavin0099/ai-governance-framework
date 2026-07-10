# Active Task

> Refreshed 2026-07-10 after the v3 offline dress rehearsal. Source surfaces:
> v1/v2 void chains, qualified v2 execution chain through `ddb6cf7b`, v3
> dress-rehearsal receipts, and synchronized `PLAN.md`.
> Claim: offline setup evidence only; no experiment outcome is claimed.

## Current Focus

- **Voided experiment line: No-Governance Baseline Runs Slice B.** Pre-registered
  at `docs/governance/no-governance-baseline-preregistration-2026-07-10.md`
  (`af22e2df`, corrected `7a3f906d`). Slice A (pre-registration) is closed.
  Slice B is owner-authorized: option-A architecture-drift mutation, the
  single compliant fixture as task file set, Codex CLI harness, and model
  `gpt-5.6-terra`. Instantiation and amendments are committed through
  Pre-Run Amendment 2 (FINAL). The first A1 attempt is excluded under the
  protocol-fidelity clause: writes/validation were blocked by the effective
  Codex sandbox/policy despite the frozen `workspace-write` spec, and the
  scratch repo stayed at seed `dd34ac3` with no scoreable output; receipts
  retained. Its voluntary `AGENTS.md` read is recorded as an observation and
  handled intent-to-treat going forward (Arm A = no harness-injected
  governance; `voluntary_governance_doc_reads` recorded per run). The Arm B
  entrypoint is frozen (hook_installer --hooks-only + validator valid=true).
  The mandatory pre-run write-capability probe then failed under the same
  Codex configuration: the harness reported a read-only workspace, policy
  rejected the write command, `write-probe.txt` was absent, and the disposable
  repo remained clean at seed `a619e13`. Under Amendment 2's hard lock, this
  further protocol gap voids Slice B. A1/A2/A3 were not run after the failed
  probe; no valid run, metric, score, or attribution conclusion exists. Any
  continuation requires a separately pre-registered v2 line.
- **v2 Pre-0 execution surface qualified; v2 is void before Run 1
  (2026-07-10).** The final capped attempt used a fresh disposable repo whose root
  was created by launcher user `daish`, plus the identical package-context
  launcher: `Invoke-CommandInDesktopPackage`, PFN
  `OpenAI.Codex_2p2nqsd0c76g0`, AppId `App`, `-PreventBreakaway`, package
  `26.707.3748.0`, native `elevated`, and `workspace-write`. Helper setup
  completed with `errors=[]`; `apply_patch` created the sole changed file with
  exact bytes `workspace-write-ok\n`, and readback/status succeeded. This
  resolves the prior package-identity and reused-scratch ownership blockers.
  Qualification is bound to this launcher/package version. All future v2
  scratch repos must be created by the launcher user outside sandbox context.
  The v2 line is now recorded as void at
  `docs/status/no-governance-baseline-v2-void-2026-07-10.md`: its first fresh
  Arm A scratch root lacked the task file and seed commit, which exposed that
  v2 did not bind seed construction/tree hash. No Codex session or API
  transmission started. Zero-amendment rules prohibit repairing or reusing it.
- **v3 offline dress rehearsal completed; v3 is preregistered.** The
  rehearsal created a fresh launcher-user-owned scratch root, demonstrated the
  literal JSON seed mutation, recorded tree/task hashes, and confirmed the
  frozen one-mismatch mutation probe with a clean post-probe state. It assembled
  but did not execute the package-context launcher (`api_call_performed=false`).
  Two setup/serialization failures are retained. The preregistration is frozen;
  owner transmission authority covers Run 1 only, not later runs or scoring.
- **v3 Arm B offline rehearsal completed; package-context hook behavior remains
  untested.** A fresh clone matched the demonstrated seed tree; hooks-only
  installation and validator passed, and a host-side local commit trace showed
  pre-commit invocation with a clean poststate. The first trace-capture attempt
  is retained; a fresh retry root succeeded. No API call, sandbox session, or
  run has occurred.
- **v3 preregistration frozen; Arm A Run 1 archived without scoring.** The protocol copies both
  rehearsed arm procedures and hashes, locks launcher/package/provenance, and
  pre-declares an Arm B package-context hook-environment exclusion only for
  zero scoreable output. Explicit v3 transmission authorization now covers the
  task prompt and scratch-repo content for Run 1 only. The owner executed the
  frozen launcher: raw output and poststate are archived at
  `docs/status/no-governance-baseline-v3-a1-archive-2026-07-11.md`. No metric
  values, score, ledger, or attribution conclusion exists.
- No other active autonomous implementation slice. The retire-candidate
  cleanup line is fully resolved as of pushed commit `81124cec`; the
  closeout memory-authority fixture carry-forward is resolved as of pushed
  commit `25243d1a`; the decision-change observation workline continues.
- Standing principle: **Validity before Expansion**. Do not add gates,
  enforcement, schema changes, or consumer-repo writes unless an observed
  failure or explicit user scope justifies them.
- Current workline: reduce governance overhead by observing which governance
  outputs change decisions before merging, downgrading, retiring, or promoting
  more surfaces.
- Current report-only implementation line: `test_signal_quality_audit` v0.2
  exists for domain contract repos. It surfaces weak test-signal candidates and
  validator fixture-pair visibility; it is not a readiness gate or test-quality
  proof.
- Deferred feature-gate candidate: `test_signal_quality_audit` consuming
  `consumer_fixture_runner` execution results is deferred because the proposed
  failure is not observed at HEAD. Re-trigger only on the first real consumer
  repo case where fixture pairs are present but runner output reports mismatch
  or error.
- Current design line: `decision-change-ledger.seed.json` and
  `context-cost-budget-design-2026-07-06.md` are observation/design artifacts.
  They do not retire defenses, measure token savings, or enforce context-budget
  compliance.

## Current Status

- **Bound memory authority fixture repaired (2026-07-10)**: `25243d1a`
  updated old-format bound-memory fixtures in
  `tests/test_session_end_hook_memory_authority_surface.py` to use a real
  repo commit anchor instead of placeholder hashes. The focused closeout
  memory-authority surface suite now passes (`25 passed`). Memory schema,
  blocking/enforcement semantics, runtime hooks, and guard criteria were not
  changed.
- **AB cost backfill writer retired (2026-07-10)**: `81124cec` removed
  `governance_tools/ab_cost_backfill_apply.py` after focused read-only review
  confirmed it was a deprecated one-off writer with no active caller, no
  dedicated tests, no CI/hook/script wiring, and no current scalar telemetry
  input. Historical backfill data/report/docs remain provenance. Active cost
  observation remains with `ab_cost_hygiene.py` and
  `ab_cost_parity_audit.py`; their semantics were not changed.
- **Feature-worthiness gate deferred (2026-07-10)**: the candidate to make
  `test_signal_quality_audit` consume `consumer_fixture_runner` results did
  not pass gate question 0. Live runner output at HEAD reported expected
  fixture matches, so the failure "fixture pair exists but actual execution
  mismatches" is evidence-needed, not observed.
- **Validator fixture hardening completed (2026-07-10)**: `05a4d8a3`
  fixed `consumer_fixture_runner` routing so manifest `validator` entries take
  precedence over `expected_rule_ids`, active contract fixture discovery does
  not mix nested contract manifests, and `.checks.json` payloads are unpacked
  into `response_text`, `contract_fields`, and `checks`. Focused tests passed
  (`tests/test_consumer_fixture_runner.py` 13 passed); live runner checks
  reported `all_expected` for the multi-validator contract (8/8 matched) and
  root architecture fixtures (2/2 matched). Validator semantics, fixture
  payloads, governance docs, hooks, CI, and enforcement were not changed.
- **Evidence provenance self-noise loop fixed (2026-07-07)**: `398f1a73`
  added a report-only write-time advisory in `memory_record` using the same
  provenance test as `memory_authority_guard`; `9cacc9a7` recorded the fix with
  a durable receipt and re-froze the baseline; `7888c347` tracked the raw
  receipt output. Live closeout high-salience view is now empty
  (`memory_authority_new_since_baseline=0`,
  `memory_authority_new_warning_codes=[]`) when records cite durable receipts.
  Guard, CI, gate, and blocking behavior were not changed.
- **Baseline artifact identity aligned (2026-07-10)**: `8f1657da` updated
  `artifacts/governance/memory-authority-baseline-2026-07-07.json` so its
  internal `baseline_id` is `memory-authority-baseline-2026-07-07`, matching
  the file date. This resolves the carried-forward warning from the
  2026-07-07 provenance review checkpoint. One-line metadata-only change;
  guard criteria, thresholds, schema, hooks, and enforcement were not changed.
  Durable evidence:
  `artifacts/evidence/test-results/receipt-baseline-identity-alignment-20260710.json`.
- **Review checkpoint (2026-07-07)**: provenance loop fix reviewed as
  APPROVED. Both carried-forward items are now resolved: the baseline
  identity mismatch by `8f1657da`, and the old-format bound memory fixture
  failure by `25243d1a`.
- **Decision-change inventory-line pass completed (2026-07-06)**: committed at
  `e30b1576` as `docs/governance/decision-change-ledger.inventory.v0.1.json`.
  All 193 governance_tools modules were compared against wiring and output
  evidence; 40 candidates were escalated, 4 marked retire_candidate.
- **Retire-candidate line fully resolved (2026-07-06)**: all four inventory
  retire candidates are dispositioned and implemented. The owner explicitly
  authorized the final two retirements in session on 2026-07-06.
- **Promotion gate duplicate smoke removed (2026-07-06)**:
  `governance_tools/promotion_gate_receipt_smoke.py` was deleted after focused
  digest regression tests confirmed replacement coverage (`af51e631`).
  Promotion-gate behavior, contract version, gates, hooks, and CI were not
  changed.
- **R49.x-4 freeze and producer removal completed (2026-07-06)**: the
  generated artifact was recorded as frozen historical evidence at `371d1378`
  (`docs/status/ab-causal-r49x4-metric-ranking-freeze-2026-07-06.md`) and
  `governance_tools/r49x4_metric_ranking.py` was deleted at `b596198f` per the
  deprecate-first disposition. Lineage references to the frozen artifact are
  preserved; R49.x conclusions were not re-validated.
- **Clean-pilot line retired (2026-07-06)**: owner decided the clean-pilot
  policy is no longer needed; `governance_tools/clean_pilot_admissibility.py`
  and `governance/fleet/cleaning_admissibility_policy.yaml` were removed
  together at `642df1bb`. The policy's governance_self_hosting_gap note lives
  on only in git history.
- **Host-agent memory sync line retired (2026-07-06)**: deprecate-first record
  committed at `fa70afba`
  (`docs/status/host-agent-memory-sync-signal-deprecation-2026-07-06.md`),
  then evaluator and dedicated tests removed at `662ed7a5`. Repo-memory
  governance surfaces are unchanged.
- **Planning alignment repaired in this slice**: prior active-task state still
  pointed at 2026-06-18 / `f21350e`; `PLAN.md` now records 2026-07-06 current
  focus, milestone commits, claim ceilings, and non-claims.
- **Governance drift baseline before repair**:
  `governance_drift_checker` reported `ok=true`, `severity=ok`,
  `plan_inventory_current=true`, and `plan_freshness=true`.
- **Test-signal quality audit line**: report-only v0.2 tooling is committed
  through `1c9abeff`; 2026-07-06 memory records cite 19 focused tests, fixture
  manifest hardening, fixture-runner visibility, and dogfood observations.
- **Semantic test-quality guidance**: committed at `a5ae276e`; consumer-facing
  update instructions now state independent expected values, regression tests
  for reproducible bugs when feasible, no happy-path-only tests for
  non-trivial changes, mock-only weakness, and validator fixture expectations.
- **Design-note consolidation line**: retrieval-authority and cache-aware
  design clusters now have summary/index docs, classification metadata, and
  source-note pointer banners. Source notes remain preserved and are not
  archived, invalidated, or reclassified by pointer banners.
- **Decision-change ledger seed**: committed at `023c65c0`; it classifies
  recent governance outputs by decision effect and explicitly leaves the
  inventory-line pass as not run.
- **Context-cost budget design**: committed at `5add91e5` and recorded at
  `86257f97`; it separates agent context-read accounting from the
  decision-change ledger and keeps companion records future-candidate only.

## Pause Conditions

- Do not start v1.3.0 release-prep until scoped release-surface consistency
  and named consumer-side proof packets are collected and reviewed.
- Do not promote `test_signal_quality_audit` into readiness, CI, hook, or gate
  behavior without a separate observed-failure-driven scope.
- Do not retire, merge, or downgrade governance defenses from the seed ledger
  alone. A read-only inventory-line pass and rare-critical safety review are
  required first.
- Do not implement context-cost companion records until there is evidence that
  they change decisions without becoming extra governance noise.

## Next Steps

1. Keep v1 and v2 stopped. Do not use the prior v2 authorization for a
   successor line.
2. Do not start any later run, compute metrics, conduct blind review, or update
   a ledger without a separately authorized slice.

## Historical Context Retained

- Phase E remains in validity-before-expansion posture.
- Cache-aware / AUTHORITY_MANIFEST remains candidate-only without prompt-cache
  control, runtime hook wiring, or harness adoption.
- Learning-loop Gate 3 remains closed; advisory prep does not authorize
  banking, replay generation, CI blockers, or completion gates.
- Public publish surfaces remain gated: GitHub topics require exact-list
  ratification, badge waits for a gated release, and release publish requires
  accurate Claim-class release notes.
- Historical `missing_canonical_memory` / `unbound_memory` debt remains warning
  evidence unless a scoped cleanup is approved.

## Cannot Claim From This Surface

- Cannot claim structured-memory freshness is automated or solved.
- Cannot claim all historical evidence is represented here.
- Cannot claim external repos are updated.
- Cannot claim test quality is enforced or industry-grade.
- Cannot claim fixture expectations are domain truth; `05a4d8a3` only proves
  the tracked fixture expectations execute and match their declared outcomes.
- Cannot claim the deferred `test_signal_quality_audit` runner-consumption
  feature is needed until a real mismatch/error case is observed.
- Cannot claim any governance defense beyond the completed removals
  (`promotion_gate_receipt_smoke.py`, `r49x4_metric_ranking.py`,
  `clean_pilot_admissibility.py`, `host_agent_memory_sync_signal.py`,
  `ab_cost_backfill_apply.py`) has been retired, downgraded, or proven
  useless.
- Cannot claim context savings were measured.
