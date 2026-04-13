# Reviewer Interpretation Guide

> How to read the E6–E1a observability signals in practice.
>
> This is not a spec.  It is a calibration aid for reviewers who have read
> [observability-chain.md](observability-chain.md) and want guidance on
> what action, if any, each signal state calls for.

---

## Before you read the signals

**If you only have time to scan one thing:** read the table in the
[Consistent interpretation](#consistent-interpretation-across-reviewers) section
and follow the primary question for the signal state you see.  The rest of this
guide expands on why those questions are the right ones.

Two things to hold in mind:

1. Every signal in this chain is **advisory only**.  None of them cause a gate
   block.  Your interpretation is the action layer — the system provides naming,
   not judgment.

2. Do not make decisions based on a single session.  Interpret signals across
   multiple sessions.  A single `trend_risk_context` has much less weight than
   the same state appearing consistently across sessions with different task types.

3. `canonical_usage_audit.usage_status` is a synthesis.  If you want to
   understand _why_ a session is in a given state, look at the raw
   `canonical_path_audit` (E7) and `canonical_audit_trend` (E8b) signals.
   The synthesis is a convenience, not a primary source.

---

## Reading `usage_status`

### `observed`

Footprint present this session.  No trend concern.

**What this means:**  
The test-result artifact exists and carries the canonical ingestor marker key.
The recent history (within the trend window) does not show a problematic signal
ratio.

**What to do:**  
Nothing required.  Use as positive baseline signal if you are building a picture
of adoption health over time.

**What to watch:**  
This state does not mean the ingestor was definitely called — only that the artifact
looks like ingestor output.  If you have reason to doubt the artifact's provenance,
check the artifact directly.

---

### `missing`

Footprint absent this session.  Trend has not yet flagged a pattern.

**What this means:**  
The test-result artifact is absent or does not carry the ingestor marker key in
this session.  However, the trend window does not yet show this as a recurring gap.

**When this can be ignored:**  
A single `missing` in an otherwise healthy history is likely a one-off — a session
that ran without tests, a deliberate non-test task, or a setup session.  Check the
session's `TASK_INTENT` and `CHECKS_RUN` fields for context.

**When this warrants attention:**  
If `missing` appears repeatedly but below the trend threshold — i.e. you see
multiple recent sessions with `usage_status=missing` without triggering
`adoption_risk=True` — the threshold may need adjusting for this repo, or the
pattern may be approaching the threshold.  Check `entries_with_signals / entries_read`
in `canonical_audit_trend` directly.

**One-off vs pattern rule of thumb:**  
A single `missing` is background noise.  Three or more `missing` states in the
last ten sessions without an `observed_with_trend_risk` or `trend_risk_context`
deserves a closer look — the trend window may not have reached the threshold yet.
This rule of thumb is independent of the configured trend threshold and is intended
as an early signal only; it is not a policy decision.

---

### `observed_with_trend_risk`

Footprint present this session.  Trend context shows recurring gaps nearby.

**What this means:**  
This session is locally healthy (footprint present), but recent history contains
enough sessions with footprint gaps to trigger `adoption_risk=True`.  The current
session is not the problem — the pattern around it is.

**Is this a warning or background information?**  
It is background information with a signal attached.  The correct frame is:

> "This session is fine, but there is evidence that the consuming repo has been
> inconsistently using the canonical path lately."

Do not treat this as a warning about the current session.  Treat it as context
about the repo's recent adoption trajectory.

**What to do:**  
Review the `top_signals` in `canonical_audit_trend` to see which signal code is
most frequent in the window:

- `test_result_artifact_absent` dominates → likely a **test execution gap**: tests
  are not being run in many sessions, so no artifact is produced at all.  This
  suggests a workflow or tooling setup issue.
- `canonical_interpretation_missing` dominates → likely an **integration/ingestion
  path gap**: tests are running and producing an artifact, but not through the
  canonical ingestor path.  This suggests the ingestor is not wired into the
  workflow despite tests being present.

These have different remediation paths.

---

### `trend_risk_context`

Footprint absent this session AND trend shows recurring gaps.

**What this means:**  
Two independent dimensions agree: this session lacks a footprint, and recent history
shows this is not isolated.  This is the strongest advisory state.

**What this is NOT:**  
Not a block.  Not a claim that the agent did something wrong.  Not evidence that
the canonical ingestor was bypassed intentionally.

**When this warrants action:**  
If you see `trend_risk_context` consistently across multiple independent sessions —
not just one after another, but across different task types and different time
periods — this is a meaningful signal that the consuming repo's adoption setup has
a structural gap.  The canonical ingestor is not being reached reliably.

**When to weight this lower:**  
- The `entries_read` count in `canonical_audit_trend` is small (under 5): the
  window is too thin to be reliable
- The repo is newly onboarded and has few sessions in the log
- The `repo_name` collision note applies (CI and local environments share a name):
  the trend may be mixing data from two different usage patterns

**The key interpretive question:**  
Is this trend driven by sessions where tests are genuinely not applicable (setup,
documentation, refactor without test scope), or by sessions where tests should have
been run but the canonical path was not followed?  That distinction determines
whether the gap is expected or unexpected.

---

## Reading `adoption_risk` directly

`adoption_risk=True` in `canonical_audit_trend` means:

> In the most recent `window_size` sessions (entry-count based), the fraction of
> sessions with at least one footprint gap signal meets or exceeds the threshold.

**When this has action significance:**  

The threshold is set at `signal_threshold_ratio=0.5` by default.  In a window of
20 sessions, this means 10 or more sessions had a footprint gap.  That is a
substantial fraction.  At this level, the signal is worth discussing with the team
responsible for the consuming repo's workflow setup.

**When this is just context:**  

If the `entries_read` is low (e.g. 3–5 sessions), a single session with a gap can
push the ratio above threshold.  In that case, treat `adoption_risk=True` as "early
signal, insufficient history to confirm pattern."

**Threshold tuning:**  
If the default threshold produces too many false positives for a particular repo's
workflow (e.g. many sessions legitimately do not run tests), the consuming repo
should lower `signal_threshold_ratio` in `governance/gate_policy.yaml`.  This is
a repo-local decision.

**Hook coverage gap — low ratios may be falsely reassuring:**  
E8b only aggregates sessions that reached `session_end_hook`.  If hook coverage is
incomplete — Tier B (Copilot Wrapper) requires manual trigger; hooks may be wired
in README but not called from actual workflow; CI governance step may be commented
out — the trend reflects only the *observed subset*, not all sessions.

A low `signal_ratio` or `adoption_risk=False` does not mean the canonical path was
followed in all sessions.  It means the canonical path was followed in the sessions
that were observed.  The fraction of sessions that were observed is itself unknown.

**Window dilution — early post-integration ratios may be elevated:**  
When `session_end_hook` is first integrated or `skip_test_result_check` is newly
added, the window will contain pre-integration entries that carry gap signals.
This causes a temporary, self-correcting elevation in `signal_ratio`.  Treat
`adoption_risk=True` in a small early window as "window includes pre-integration
history" until a full window of post-integration sessions has accumulated.

---

## Consistent interpretation across reviewers

To reduce interpretation drift across sessions and reviewers, use this framing:

| Signal state | Primary question | Secondary question |
|---|---|---|
| `missing` | Is this a one-off or part of a pattern? | Check `entries_with_signals/entries_read` |
| `observed_with_trend_risk` | What signal dominates `top_signals`? | Is it artifact absent or interpretation missing? |
| `trend_risk_context` | Is the `entries_read` count reliable? | Is this structural or incidental? |
| `adoption_risk=True` | Is the window large enough to trust? | Is threshold tuning needed for this repo? |

The goal is not to reach a verdict from one session.  It is to accumulate enough
signal across sessions to distinguish **adoption gap** (structural, needs action)
from **workflow variation** (expected, no action).

---

## What this guide does not answer

- Whether the gap was caused by intentional bypass or accidental omission — the
  chain does not observe agent reasoning, only artifact footprints
- Whether the canonical path is the right path for a given task type — that is a
  workflow design question, not an observability question
- When to escalate to E1b-style enforcement — that decision requires real-world
  E8b data and is not yet supported
- What fraction of sessions were actually observed — the hook coverage rate is
  unobserved; E8b cannot report on sessions that never triggered `session_end_hook`
