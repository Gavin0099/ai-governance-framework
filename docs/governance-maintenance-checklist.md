# Governance Maintenance Checklist

> This checklist is for periodic maintenance of the runtime governance layer —
> not for individual session review.  Run it when things feel stale or before a
> significant consuming-repo change.
>
> **Operator** (you, running this checklist) ≠ **Reviewer** (reading individual
> session output).  The reviewer-facing doc is `reviewer-interpretation-guide.md`.

### Run this checklist when:

- `adoption_risk=True` persists across multiple sessions
- `canonical_usage_audit` shows repeated `missing` or `trend_risk_context` status
- `drift_checker` reports unexpected changes
- A new E-level feature has shipped (E7, E8a, E8b, E1a, E9a…)
- A consuming repo is being onboarded or significantly restructured
- Something "looks wrong" but you are not sure where to start

Frequency is event-driven, not calendar-driven.  The table below is a fallback
guide only — use the trigger list above to decide when to actually open this doc.

---

## Frequency Guide

| Section | Suggested frequency |
|---------|---------------------|
| Gate Policy Review | Per consuming repo / after structural change |
| Canonical Audit Log Health | Monthly or when trend signals look wrong |
| Advisory Signal Calibration | After accumulating ≥20 new log entries |
| E6 Seed Corpus | Quarterly or when classifier taxonomy changes |
| Framework–Consumer Sync | After framework major change (new E-level feature) |

---

## 1. Gate Policy Review

For each consuming repo that runs `session_end_hook`:

- [ ] Does `governance/gate_policy.yaml` exist?
  - If absent: repo receives `repo_local_policy_missing` warning every session.
  - Add a minimal policy (see `docs/consuming-repo-adoption-checklist.md` Step 8).

- [ ] Is `fail_mode` appropriate for this repo's stage?
  - `strict` — production repos; gate blocks on absent/malformed artifact
  - `permissive` — repos not yet running `test_result_ingestor`
  - `audit` — observation-only; gate never triggers

- [ ] For C++ / firmware / doc-only repos: is `skip_test_result_check: true` set?
  - If the repo structurally cannot produce a test-result artifact, declare it.
  - Do NOT use `signal_threshold_ratio: 0.95` as a workaround — that masks the
    structural fact instead of declaring it.

- [ ] Are `blocking_actions` correct?
  - `production_fix_required` should be present for any repo where agent-produced
    failures that require production code fixes should block closeout.

- [ ] Is `artifact_stale_seconds` appropriate?
  - `86400` (24 h) is a reasonable default; CI repos may need shorter windows.
  - Set to `0` to disable stale detection entirely (skip repos).

---

## 2. Canonical Audit Log Health

For each consuming repo's `artifacts/runtime/canonical-audit-log.jsonl`:

- [ ] Does the log file exist?
  - Absent log = no sessions have run `session_end_hook` to completion.
  - If sessions are being run but file is absent, check for disk/permission issues.

- [ ] Is the log growing (not stuck at size 0)?
  - Compare line count before and after a session run.
  - Silent write failures do not surface in result keys — this is the only way to
    detect E8a degradation.

- [ ] Are `repo_name` values consistent across log entries?
  - Inconsistent names indicate the working directory was renamed, forked, or
    accessed from two different parent paths (repo_name collision).
  - Use `scope_note` in E8b results as an acknowledgement surface, not a fix.

- [ ] Is the log below the 500-entry rotation ceiling?
  - The log auto-rotates at 500 entries; old entries are dropped.
  - If you need longer history, increase `_CANONICAL_AUDIT_LOG_MAX_ENTRIES` in
    `session_end_hook.py` — but note that larger logs slow E8b reads.

- [ ] Has the log been unexpectedly reset (sudden drop in line count)?
  - Possible causes: rotation bug, CI clean-workspace policy, path misconfiguration,
    artifact directory deleted and recreated.
  - Effect: E8b trend is recomputed against a much smaller history window — signal_ratio
    may suddenly drop to 0.0 even if real gaps exist.  Trend results look clean but are
    based on near-empty history.
  - No automated detection exists.  Compare current line count to previous known count
    or check `entries_read` vs `window_size` in the `canonical_audit_trend` result.

---

## 3. Advisory Signal Calibration

Once a consuming repo has ≥20 entries in its canonical audit log:

- [ ] What is the current `signal_ratio` from E8b?
  - Go to any recent `run_session_end_hook` result → `canonical_audit_trend`.
  - A ratio above the configured `signal_threshold_ratio` emits `adoption_risk=True`.
  - This is advisory only — it never affects `gate.blocked`.

- [ ] Is `adoption_risk=True` reflecting a real gap or a false signal?
  - Real gap examples: ingestor not integrated, artifact not written to correct path.
  - False signal examples (window dilution): `skip_test_result_check` newly added
    or hook recently integrated — window still contains pre-integration entries that
    carry gap signals.  Early post-integration windows legitimately overstate adoption
    risk until pre-integration entries age out of the entry-count window.
  - False signal examples (other): repo_name collision mixing unrelated data,
    structural-absence repo without `skip_test_result_check`.

- [ ] Is a low or improving `signal_ratio` evidence of healthy adoption?
  - Not necessarily if hook coverage is incomplete (hook coverage gap).
  - E8b only reflects sessions that reached `session_end_hook`.  Sessions skipped by
    Tier B operators (manual trigger not run), hooks wired in README but not called,
    or CI steps that were commented out are **outside the observable set** and leave
    no entry in the log.
  - The fraction of sessions that were observed is itself unknown.  A clean trend
    does not confirm that the canonical path was followed in all sessions — only in
    the sessions that were observed.
  - Window dilution (temporary bias) vs hook coverage gap (systematic bias) are
    different problems.  Dilution self-corrects; coverage gap does not.

- [ ] Is `signal_threshold_ratio` calibrated for this repo's workflow?
  - Default `0.5` (50% of sessions lack footprint triggers alert).
  - Repos with infrequent test runs may need a higher ratio to avoid noise.
  - Repos with strict canonical-path requirements may want a lower ratio.
  - **Note:** `signal_ratio` is based on entry-count window, not time duration.
    `window_size=20` means the 20 most recent log entries regardless of when they
    were written.  Do not interpret the ratio as a rate per day or per week.

- [ ] Do `top_signals` show one dominant signal or a mix?
  - `test_result_artifact_absent` dominant → test execution / artifact write gap.
  - `canonical_interpretation_missing` dominant → ingestor integration path gap
    (artifact exists but was not produced by `test_result_ingestor`).
  - Mixed → investigate whether two different root causes are present.

---

## 4. E6 Seed Corpus

- [ ] Has the failure taxonomy changed since E6 was last calibrated?
  - New `FailureKind` values added to `failure_disposition.py`?
  - Existing classifications changed?
  - If yes, add seed corpus cases for the new taxonomy and re-run
    `governance_tools/replay_verification.py`.

- [ ] Does `artifacts/runtime/replay-evidence/latest.json` have all cases passing?
  ```powershell
  python governance_tools/replay_verification.py
  ```
  - `all_pass: true` is required.
  - `evidence_scope` must remain: "scope is limited to seed corpus only".

- [ ] Is the seed corpus still representative?
  - Corpus coverage is bounded — it does not guarantee correctness on unseen inputs.
  - Add cases when a real-world classification mistake is found (not periodically).

---

## 5. Framework–Consumer Sync

After a framework E-level feature ships (E7, E8a, E8b, E1a, E9a, etc.):

- [ ] Does the consuming repo need a new gate_policy.yaml field?
  - E9a added `skip_test_result_check` — C++ / no-test repos should declare it.
  - E8b added `canonical_audit_trend` section — repos that want custom window sizes
    should add it.

- [ ] Is the consuming repo's pinned framework version still correct?
  ```powershell
  python ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root ./ai-governance-framework --format human
  ```
  - `framework_source_correct` should be True.
  - `version_pinned` should match the current framework HEAD.

- [ ] Has the `consuming-repo-adoption-checklist.md` been read by the consuming
  repo maintainer since the last framework release?

- [ ] Are the session hooks actually being triggered in the consuming repo workflow?
  - Hooks: `session_start.py`, `pre_task_check.py`, `post_task_check.py`,
    `session_end_hook.py`.
  - Not triggered = no data in `canonical-audit-log.jsonl`, no gate decisions,
    no advisory signals — the governance layer exists but produces no output.
  - Check: does `artifacts/runtime/canonical-audit-log.jsonl` grow after a session
    run?  Does `artifacts/runtime/test-results/latest.json` exist and have a recent
    mtime?  Is there a CI step or agent workflow line that calls these hooks?
  - Common failure modes: hooks wired in README but never called from actual agent
    workflow, CI pipeline has governance step commented out, `session_end_hook`
    called manually only (missed sessions are invisible).

---

## Quick Health Check Command

Run from the consuming repo root:

```powershell
# ── Drift / readiness checks (consuming-repo health vs framework baseline) ──
python ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --framework-root ./ai-governance-framework
python ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root ./ai-governance-framework --format human

# ── Framework self-check (framework internal consistency) ───────────────────
python ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --emit-risk-signal

# ── Runtime enforcement smoke (framework enforcement boundary) ──────────────
python ai-governance-framework/governance_tools/runtime_enforcement_smoke.py
```

- **Drift / readiness**: answers "is this consuming repo still aligned with the framework?"
- **Framework self-check**: answers "is the framework itself internally consistent?"
- **Runtime enforcement smoke**: answers "are the enforcement boundary contracts still intact?"

---

## What This Checklist Does NOT Cover

- Individual session correctness (see `reviewer-interpretation-guide.md`)
- Observability chain signal semantics (see `observability-chain.md`)
- Full onboarding validation (see `consuming-repo-adoption-checklist.md`)
- Gate policy authoring beyond the minimum (see `governance/gate_policy.yaml` comments)
