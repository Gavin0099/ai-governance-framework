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

### Rule 4: Structured Report Format

When reporting task completion, use this exact format. Fixed vocabulary only — no free-form narrative in these fields.

```
Validation:
- structural:    PASS | FAIL | NOT RUN
- build:         PASS | FAIL | NOT RUN
- semantic:      NOT CLAIMED | PASS (human review only)
- behavioral:    NOT PRESENT | verified
- ext evidence:  NOT PRESENT | [source]

Risk:
- scope drift:        none | [description]
- claim inflation:    none | [description]
- evidence maturity:  [one line]

Incidental cleanup:   none | file=[path] reason=[why] semantic_change=no

Cannot claim this session:
- [list what was NOT validated, NOT verified, NOT proven]
```

Do NOT omit `Cannot claim`. It is required in every completion report.
