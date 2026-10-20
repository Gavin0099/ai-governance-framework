# COPILOT-CLOSEOUT-01

Status: local unpublished candidate. VS Code Local A–D was observed for
COPILOT-CLOSEOUT-01; semantic second-round evidence is recorded separately.

The work Agent supplies the goal, completed work, actual checks, unfinished work,
declared risks and concrete next step. Runtime must never infer these from Git,
transcripts or absence of errors. An investigation or review needs no product diff.

## Event authority

`Stop` / `agentStop` ends an execution turn. It returns
`closeout_eligibility=not_yet_eligible`; it does not run canonical closeout or
project daily work memory, including when a candidate is already prepared.
This also protects old installations that route Stop to `session_end`.

A native `sessionEnd` / `SessionEnd` uses the documented terminal reason, or an
Agent invokes `explicit_closeout` after the owner explicitly requests closeout.
Do not infer explicit authorization from task DONE, a final answer or a Stop.
Local VS Code harnesses without a qualified session-end event use the explicit
path. Hook-file compatibility does not establish event support in a harness.

Sources checked 2026-10-20:
- https://docs.github.com/en/copilot/reference/hooks-reference
- https://code.visualstudio.com/docs/agent-customization/hooks

## Agent preparation

COPILOT-CLOSEOUT-02 keeps the same candidate and native identity schemas. Before
preparation, the producer separates completed work/verification from remaining
project work. Its future action must survive successful closeout; it must not
ask the next Agent to redo this closeout's prepare/retry/verify/replay commands.
Explicit action clauses using those lifecycle command names are rejected before
candidate writes. Product actions such as replaying a USB capture or reviewing
the prepare tool documentation are not classified by this bounded check.
When no work remains, state that explicitly. Runtime does not supply a new action.

CHECKS_RUN distinguishes own execution assertions from quoted, external or denied
execution. `supplied pytest evidence was not run by me` and
`I did not run pytest; supplied JUnit reports 38 passed.` do not require a local
runner footprint. Referenced files are still required to exist. Positive own
execution and legacy command/result entries retain the existing artifact checks;
the parser does not authenticate supplied evidence or change policy thresholds.

Failure wording belongs to the producer: missing summary is a closeout input
failure, not a policy gate block when `gate_policy.blocked=false`. Qualification,
test and runtime failures remain distinct. This is guidance, not another gate.

Use the existing native v1.0 Copilot session envelope. Never relabel it as Codex,
upgrade it to v1.1, or synthesize a historical session identity. The Copilot
preparation path reuses the existing candidate renderer and validator, but saves
its text under `artifacts/runtime/sessions/<session_id>/session-closeout.txt`.
It never overwrites the shared Codex `artifacts/session-closeout.txt`.

Save an agent-authored input JSON containing exactly:

```json
{
  "task_intent": "Review the input boundary",
  "work_summary": "Reviewed docs/input-boundary.md; missing input remains UNKNOWN.",
  "tools_used": ["read"],
  "artifacts_referenced": ["docs/input-boundary.md"],
  "open_risks": ["Native host acceptance has not been observed."],
  "checks_run": "NOT RUN: investigation only; inspected docs/input-boundary.md",
  "not_done": "Native host acceptance remains pending.",
  "recommended_memory_update": "Preserve the input-boundary review result.",
  "next_step": "Observe the native Copilot closeout against this boundary."
}
```

From the consumer root, pass native identity/root JSON on stdin to its installed
`.github/hooks/ai-governance-lifecycle.py` bridge. For example in PowerShell:

```powershell
Get-Content -Raw native-session-payload.json | python .github/hooks/ai-governance-lifecycle.py --event-type prepare_closeout --surface auto --summary-input agent-summary.json
# Only after the owner's explicit closeout request:
Get-Content -Raw native-session-payload.json | python .github/hooks/ai-governance-lifecycle.py --event-type explicit_closeout --surface auto
```

The payload contains `session_id` (or `sessionId`) and the actual repository
`cwd`; preparation/explicit actions do not carry a forged native hook event.
Preparation saves a new immutable candidate and matching private text; it does
not claim acceptance. If preparation fails, the Agent corrects the input and
retries. The latest invalid candidate does not fall back to an older success.

## Required failure, retry and replay

Required closeout without a valid candidate returns `ok=false` and
`closeout_eligibility=required`. Existing canonical/audit failure artifacts and
`copilot-closeout-state.json` preserve recovery context. Unavailable risk
assessment has `open_risk_count=null`, not an assessed zero. No invalid or
gate-blocked attempt projects daily work memory or consumes the session.

The Agent corrects/prepares the summary and retries the same native context.
Canonical content, session binding and the existing policy gate all remain
required. A complete result projects agent work/checks/unfinished work/risks/next
step through the canonical writer, then records completion. It does not update
active task, PLAN or reusable knowledge on the consumer's behalf.
This adapter requests daily work projection explicitly; automatic snapshots and
promotion into reusable memory are outside this tranche.

Equivalent missing input reuses its durable failure; changed candidate/text is
eligible for revalidation. Successful replay verifies the existing completion,
canonical digest and daily record binding, then returns the accepted result
without new closeout, audit or memory writes. Unverifiable completed state fails
closed for recovery; it is not replayed as a new success.

Acceptance: `tests/test_copilot_closeout_lifecycle.py` covers A (intermediate
Stop), B (required missing input), C (correction/retry) and D (accepted replay),
plus invalid content, strict policy, identity, start replay and source boundaries.
These are local integration tests using official native payload shapes. They do
not establish native host loading or live event delivery.

Excluded: historical cleanup, event/identity schema redesign, DeviceTraceKit
active-task reconstruction, Markdown restyling, threshold or fail-closed changes.
