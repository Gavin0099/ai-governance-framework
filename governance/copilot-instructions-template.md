# Copilot Workspace Instructions
<!-- AI Governance Framework: copilot-instructions v1.0 -->
<!-- Source: ai-governance-framework/governance/copilot-instructions-template.md -->
<!-- Deploy via: bash scripts/install-hooks.sh --target /path/to/repo -->

## DONE Boundary Rules (MANDATORY)

### Rule 1: Hard Stop After DONE

When the defined DONE condition is met, stop immediately.

Do NOT automatically continue into:
- full regression or broad smoke validation
- governance artifact chains (triage → decision → contract → gate → acceptance → freeze)
- commit, push, closeout, or status rollup
- inspection of unrelated dirty or untracked files

Report next options only. Wait for explicit instruction.

### Rule 2: Scope-Matched Validation

Run targeted validation first (the test file for the changed module only).

Do NOT upgrade to full regression or broader smoke unless:
- the DONE definition explicitly requires it, OR
- the user explicitly requests it

When broader validation fails: report the failure and classification in ONE message, then stop.
Do not build triage/decision/contract chains from a broader validation failure.

### Rule 3: Dirty Tree Allowlist

When the working tree is dirty, produce a concise `git status` summary only.

Stage only files explicitly listed by the user or required by the DONE scope.
Do not read, explain, stage, or modify unrelated dirty or untracked files.

### Rule 4: Result-First Rendering

When reporting task completion, follow `governance/RESPONSE_ENVELOPE_CONTRACT.md`.
The complete machine envelope remains the canonical record. Keep
`mode_source`, `task_authority`, `scope`, `done`, `claim_ceiling`,
`not_claimed`, `evidence_refs`, `risk`, and `next_action` separate and
traceable; compact human text is only a projection and never replaces that
record.

### Compact by default

For a complete task with supporting evidence, use the first three lines in the
session language. Add one `注意：` line when dirty state, high-risk scope, or a
decision-relevant limitation needs to be visible but can still be stated
without changing the claim boundary:

```text
Result: <what is complete>
Reason: <the supporting evidence and claim boundary>
Next step: <one concrete action, or a complete sentence saying none is needed>
注意：<one decision-relevant limitation, when applicable>
```

In Chinese, use `完成：`, `原因：`, and `下一步：`. Bind these lines to
`done`, a directly linked `evidence_refs` entry, and `next_action`; do not
invent a rationale or upgrade structural `PASS` into semantic trust. A
non-decision-relevant `not_claimed` item may remain machine-side without a
visible Cannot claim section. Keep the event/session traceability path,
`task_authority`, and `claim_ceiling` available even when they remain in the
machine record.

### Expanded by trigger

Use expanded reporting only when one of these three conditions applies:

- `full_evidence_request`（要求完整證據）：使用者明確要求完整證據；
- `owner_decision_required`（需要負責人決定）：目前需要負責人回覆或授權；
- `failed_or_partial`（失敗或只完成一部分）：工作失敗、只完成一部分，或必要驗證無法取得、互相矛盾、無法保留宣稱界線。

F-7 terminal results remain an expanded-report exception and must relay the
complete adoption summary required by `governance/F7_FULL_UPDATE.md`, including
the unavailable-summary fallback when applicable.

Expanded output keeps all decision-relevant `not_claimed` items, risks, claim
boundaries, evidence references, and the exact or traceable machine
`next_action`. Emit the primary expansion reason first, then other matching
reasons once in contract priority order. Preserve the machine envelope even
when the human report is expanded.

### Language and progress

Use the current session language for prose and labels. In a Chinese session,
translate conceptual terms such as ordinary expansion policy（一般展開規則）、
dirty state（工作樹未乾淨）、authority surface（治理或權限面）、limitation
（限制）、compact（精簡版）、progress update（進度更新）、adoption summary
（導入摘要）、fallback（退路）、scoped diff（本次範圍差異）與 diagnostics
（靜態檢查）. Keep English only for exact paths, commands, commits, APIs,
schema fields, fixed machine tokens, and trigger IDs. When an exact token is
shown, add its plain-language meaning once.

Keep `注意：` for one decision-relevant limitation. Do not put test commands,
test counts, `git diff --check`, diagnostics, or general worktree status in it;
put those under `驗證：` or the machine `evidence_refs`. Report commands with
complete repository-root paths such as `tests/test_response_envelope_validator.py`,
and use actual workspace-relative file links and verified line numbers.

Progress updates must contain at least one new discovery, root-cause convergence,
or plan change. Omit updates that only narrate routine commands, searches, or
repeated validation; there is no hard maximum number of updates.

Fixed vocabulary remains exact where it is part of machine evidence:
`NOT PRESENT`, `NOT CLAIMED`, `PASS`, `FAIL`, and `NOT RUN`. `PASS` must include
a command, artifact, or source; bare `PASS` is invalid. Do not replace claim
ceiling, risk, authority, or evidence maturity with confidence scores or broad
impact prose.
