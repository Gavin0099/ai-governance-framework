# Observability Chain — Reviewer Entrypoint

> This note describes what the E6–E1a chain observes, how the layers divide
> authority, and what each layer does **not** claim.  It is not a spec and does
> not change any code contracts.  Read it when you want to understand the system
> before reading individual component docs.

---

## The problem this chain solves

A governance system that only emits a pass/fail gate is not auditable.  Reviewers
cannot tell:

- whether the correct interpretation path was actually followed
- whether a gap is a one-off or a pattern
- whether a session's result is trustworthy given recent history

The E6–E1a chain builds a layered answer to that question without introducing new
authority or blocking mechanisms.

---

## Layer map

```
E6  ──  bounded replay correctness
E7  ──  single-session canonical footprint signal
E8a ──  multi-session footprint history (persistence substrate)
E8b ──  multi-session trend interpretation (sliding-window advisory)
E1a ──  reviewer-facing synthesis (interpretation layer)
```

Each layer adds observability.  No layer adds enforcement.

---

## E6 — Bounded replay correctness

**What it does:**  
Re-runs a labelled seed corpus through the classifier and gate and checks that
outputs match human analysis on two independent layers: classification correctness
and gate-effect correctness.

**What it produces:**  
`artifacts/runtime/replay-evidence/latest.json` — a re-runnable evidence artifact
with an explicit `evidence_scope` field.

**What it is NOT:**  
- Not a claim that the classifier is correct on inputs outside the seed corpus
- Not a runtime guard — it runs on demand, not during sessions
- Not a substitute for real-world test coverage

**Authority boundary:**  
`evidence_scope` is always written as: *"scope is limited to seed corpus only —
does not assert correctness beyond labelled cases."*  This is intentional and must
not be weakened.

---

## E7 — Single-session canonical footprint signal

**What it does:**  
At the end of every session, inspects the test-result artifact and emits two
possible advisory signal codes:

- `test_result_artifact_absent` — artifact file does not exist at session boundary
- `canonical_interpretation_missing` — artifact exists but the canonical ingestor
  marker key (`failure_disposition`) is absent, meaning the artifact was not
  produced by the canonical path

**What it produces:**  
`canonical_path_audit` key in `run_session_end_hook` result — `signals`,
`artifact_present`, `canonical_key_present`, `audit_note`.

**What it is NOT:**  
- Not proof that the canonical ingestor was called — only that the artifact
  *looks like* canonical ingestor output (marker key present)
- Not a claim about agent reasoning or tool call sequence
- Not a gate — signals go to `warnings`, never to `gate.blocked`

**Authority boundary:**  
Presence of the marker key is **indicator evidence**, not execution proof.  Any
code that reads `canonical_key_present=True` and concludes "ingestor was definitely
called" is over-reading the signal.

---

## E8a — Multi-session footprint history

**What it does:**  
After E7 runs, appends one entry to a repo-local JSONL log:
`artifacts/runtime/canonical-audit-log.jsonl`.

Each entry records: timestamp, session_id, repo_name (best-effort), artifact_state,
E7 signals, gate_blocked status, and policy provenance.

**What it produces:**  
An append-only, rotating (max 500 entries) observability log.  No read path is
defined in E8a itself — it only writes.

**What it is NOT:**  
- Not the authority of truth for any session outcome — the single-session result
  dict from `run_session_end_hook` retains that role
- Not a canonical repo identity system — `repo_name` is `project_root.resolve().name`,
  which does not handle renamed directories, forks, or nested checkouts
- Not a blocking mechanism — write failures are silently swallowed; the log must
  never degrade session_end behaviour

**Authority boundary:**  
`repo_name` is explicitly an **observability hint**.  The log is a substrate for
trend computation (E8b) and nothing else.  Do not use it as a source of truth about
which repo produced which session.

---

## E8b — Multi-session trend interpretation

**What it does:**  
Reads the E8a log, filters to the current repo name (best-effort), takes the most
recent `window_size` entries sorted by timestamp, and computes:

- `signal_ratio` — fraction of window entries that carry at least one E7 advisory signal
- `adoption_risk` — True when `signal_ratio >= signal_threshold_ratio` AND at least
  one entry was read

**What it produces:**  
`canonical_audit_trend` key in `run_session_end_hook` result — `adoption_risk`,
`signal_ratio`, `top_signals`, `entries_read`, `scope_note`.

**What it is NOT:**  
- Not a gate input — `adoption_risk=True` never contributes to `gate.blocked`
- Not a canonical repo identity claim — `scope_note` is always present and always
  states the best-effort limitation
- Not a consecutive-pattern detector — sliding-window ratio is used deliberately
  because silent write failures can create non-consecutive gaps in the log
- Not configurable per session — `window_size` and `signal_threshold_ratio` are
  repo-local policy (via `governance/gate_policy.yaml`), not session-level

**Authority boundary:**  
`advisory_only=True` is hard-coded and literal.  The field name is intentional:
any code path that connects `adoption_risk` to a blocking decision is a contract
violation.

---

## E1a — Reviewer-facing synthesis

**What it does:**  
Takes the already-computed E7 (`canonical_path_audit`) and E8b
(`canonical_audit_trend`) results and names their combination as a single
`usage_status`:

| E7 footprint | E8b adoption_risk | usage_status |
|---|---|---|
| present | False | `observed` |
| absent | False | `missing` |
| present | True | `observed_with_trend_risk` |
| absent | True | `trend_risk_context` |

**What it produces:**  
`canonical_usage_audit` key — `usage_status`, `usage_note`, `canonical_key_present`,
`trend_adoption_risk`, `advisory_only=True`, `basis="E7+E8b synthesis"`.

**What it is NOT:**  
- Not a new signal producer — it introduces no new I/O, no new log entries, no new
  policy parameters
- Not a new authority — `basis: "E7+E8b synthesis"` is present in every output to
  mark this as a derived field, not a primary judgment
- Not enforcement — `trend_risk_context` is the strongest advisory state; it still
  carries `(advisory only — no gate effect)` in `usage_note` and never feeds
  `gate.blocked`
- Not a claim that the ingestor was called — the field is named `canonical_key_present`
  precisely to avoid this over-reading

**Authority boundary:**  
E1a is a **naming layer**.  It answers "what should a reviewer call this situation?"
not "what should the system do about it?".  If `usage_status` is ever used as a
gate input, it is a misuse of the field.

**Fallback behaviour:**  
If `_build_canonical_usage_audit` raises for any reason, the result contains
`internal_error=True` alongside `usage_status="observed"`.  The `internal_error`
flag means "this is a safe default, not a genuine observation."  The fallback does
not silently claim success.

---

## What this chain collectively does NOT do

- Does not enforce exclusive canonical interpretation usage at runtime
- Does not verify that an agent's reasoning path went through the canonical tool
- Does not track which tools were called during a session
- Does not produce any binding gate decisions (all outputs are advisory)
- Does not provide canonical repo identity (repo_name is best-effort throughout)

These limitations are intentional.  The chain is designed to make adoption gaps
*visible* and *named*, not to punish them.

---

## Relationship to E1b (not yet implemented)

E1b would introduce enforcement — the ability to block or escalate based on
canonical usage.  It is not started.

The prerequisite for E1b is not more features; it is **evidence from E8a/E8b data**
showing that:

1. adoption gaps are real and recurring, not measurement noise
2. the `repo_name` grouping is reliable enough to attribute gaps correctly
3. the `canonical_key_present` signal is stable enough to be a control input

None of these conditions have been confirmed by real-world data yet.  E1b should
not be designed until data from E8b has been observed across actual consuming repos.

---

## Reading order for new reviewers

1. This file — to understand the chain and its limits
2. [E6 replay evidence](../artifacts/runtime/replay-evidence/latest.json) — to see
   bounded correctness evidence for the seed corpus
3. `run_session_end_hook` result for the current session — `canonical_path_audit`,
   `canonical_audit_trend`, `canonical_usage_audit` keys
4. [E8b trend config](../governance/gate_policy.yaml) — `canonical_audit_trend`
   section if the consuming repo has customised window or threshold

Do not start from `canonical_usage_audit` alone.  It is a synthesis; reading the
raw E7 and E8b signals first gives you better calibration.
