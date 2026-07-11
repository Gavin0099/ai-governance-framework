# Runtime Treatment Census — Final Analysis (33/33, 2026-07-11)

Status: census synthesis. Every unit in the pinned manifest now carries a
census-format evaluation with a per-unit evidence receipt (or an explicit
cross-reference to its dedicated review). This analysis authorizes no
disposition; it hands the owner a candidate list.

## Coverage

All 33 pinned units are evaluated: 14 walkthrough docs existed before this
tranche set; this set added hermes (4), core checks (3), session lifecycle
(2), prompt carriers (2), the templates trio (1 doc, 3 units), and
cross-reference docs for the gemini trio and payload_audit_logger.

## Distribution

| class | units | share |
| --- | --- | --- |
| carrier (adapters, dispatcher, shared runner/normalizer, path overrides, stub) | 17 | 52% |
| audit (closeout chain, evidence gate, loggers, smoke, templates) | 9 | 27% |
| mixed (session_start, pre/post_task_check, decision_policy, closeout context) | 5 | 15% |
| behavior_change (copilot template, AGENTS exemplar) | 2 | 6% |

Disposition outcome: **33 × `keep_observe`, 0 retire, 0 merge** — the census
found no unit meeting a dead-code predicate; every retirement-adjacent
signal is gated on a frozen line, a pending integration, or an owner lane
decision.

## Decision-evidence landscape (the census's core question)

- **observed**: 4 units — the closeout chain (session_end,
  _canonical_closeout: consumed by the F-7 / P1-C external evidence chain),
  the AGENTS exemplar (v3 exposure observation), and payload_audit_logger
  (historical analysis artifacts only).
- **unmeasured / none**: every other evaluable unit. This is the honest
  headline: the framework's runtime layer runs mostly on unmeasured
  justification, and the census makes that visible per unit instead of
  arguable in aggregate.

## Defects and discoveries produced by the walkthrough

1. `tests/test_session_start_risk_signal.py` **hangs** (siblings finish in
   <1s); excluded from the session_start receipt; needs its own
   investigation.
2. **Naming collision**: `governance_tools/payload_audit_logger.py` and
   `runtime_hooks/core/payload_audit_logger.py` are different modules with
   one name; only the former is env-gated, the latter is called
   unconditionally in session_start, and its post-2026-03 silence still
   lacks a verified explanation.
3. `templates/retrieval-authority-advisory-template.yaml` is the strongest
   orphan (zero references outside the census itself).
4. The stale `.gemini/settings.json` was removed mid-census by owner
   decision; the gemini no-real-consumer flag remains open.
5. Cluster rule recorded: the hermes trio + stub must be re-evaluated
   together if the Hermes line is abandoned.

## Owner-decision candidates (none executed)

| # | Candidate | Type | Gate |
| --- | --- | --- | --- |
| A | Investigate the hanging risk-signal test | defect fix | small focused slice |
| B | Rename/merge the two payload_audit_logger modules | hygiene | future owner slice |
| C | Behavior-carrier consolidation (copilot template × AGENTS exemplar overlap) | consolidation | only if owner opens it; burden of proof already raised by v3 recalibration |
| D | Gemini lane decision | lane keep/dispose | needs real consumer evidence or deliberate owner disposal |
| E | Orphan template disposition | diet | gated on frozen-line (Gate C / retrieval-authority / memory-significance) dispositions |
| F | Direct contract tests before any decision_policy vocabulary revision | standing rule | recorded in the unit doc |
| G | Explain runtime-core payload writer silence | open question | separate read-only check |

## Against the maintenance-vs-build weakness frame

- "哪些防線可以合併": candidates B and C — both small, both named.
- "哪些規則其實沒有效": unanswerable from structure alone; the census
  converts the question into a per-unit `decision_evidence` field where the
  dominant value is honestly `none`.
- "哪些 validator 只是形式檢查": none found as pure theater; what was found
  instead is a coverage gap (decision_policy) and one broken test (hanging
  risk-signal).
- "哪些 governance output 真的會改變決策": the closeout/receipt chain is the
  only runtime output with observed downstream decision consumption.

## Claim ceiling

`keep_observe` everywhere means "no disposition evidence", not "all
valuable". Decision-evidence entries marked observed prove consumption, not
counterfactual value. v3 citations remain owner-adopted recalibration,
task-class-scoped. Nothing in this census measures whether any advisory,
injection, or verdict changed an outcome.
