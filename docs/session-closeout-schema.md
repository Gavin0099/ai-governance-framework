# Session Closeout Artifact Schema

> Version: 1.0
> Artifact path: `artifacts/session-closeout.txt`
> Written by: AI agent at end of session
> Consumed by: `governance_tools/session_end_hook.py` via stop hook

---

## Purpose

This artifact is the AI agent's **closeout input** to the governance runtime.

It is NOT a truth source. It is a candidate artifact — subject to review.

The governance runtime (session_end_hook → session_end) is responsible for
consuming this artifact, validating its completeness, and producing the
authoritative verdict/trace artifacts. The AI provides the input; the runtime
decides what gets recorded.

---

## Required fields

Every field must be present. Empty values must be stated explicitly.

```
TASK_INTENT: <one sentence — what was the declared goal of this session>
WORK_COMPLETED: <what was actually done — verifiable claims only, no narrative>
FILES_TOUCHED: <comma-separated list of files changed, or NONE>
CHECKS_RUN: <what tests, smoke checks, or validations were actually executed, or NONE>
OPEN_RISKS: <what might be wrong or incomplete — if none, write NONE>
NOT_DONE: <what was not completed this session — if nothing, write NONE>
RECOMMENDED_MEMORY_UPDATE: <what memory/ file should change and why, or NO_UPDATE>
```

---

## Field constraints

| Field | Constraint |
|-------|-----------|
| `TASK_INTENT` | Required, non-empty |
| `WORK_COMPLETED` | Required, non-empty |
| `FILES_TOUCHED` | Required; `NONE` is valid |
| `CHECKS_RUN` | Required; `NONE` is valid |
| `OPEN_RISKS` | Required; `NONE` is valid |
| `NOT_DONE` | Required; `NONE` is valid |
| `RECOMMENDED_MEMORY_UPDATE` | Required; `NO_UPDATE` is valid |

A closeout is considered **insufficient** if:
- Any required field is missing
- `WORK_COMPLETED` is present but contains only vague claims with no verifiable content
  (e.g., "worked on things", "made improvements")
- `CHECKS_RUN` is non-`NONE` but no specific command or check name is listed

A closeout is considered **missing** if the file does not exist at session end.

---

## Example — normal session

```
TASK_INTENT: implement session_end_hook.py for automatic memory closeout
WORK_COMPLETED: wrote governance_tools/session_end_hook.py; updated AGENTS.base.md session closeout section; verified with quickstart smoke ok=True
FILES_TOUCHED: governance_tools/session_end_hook.py, baselines/repo-min/AGENTS.base.md
CHECKS_RUN: python -m governance_tools.quickstart_smoke (ok=True); python -m governance_tools.session_end_hook --project-root . (ok=True, promoted=True)
OPEN_RISKS: stop hook not yet configured in any repo; AGENTS.base.md change not yet re-adopted by existing repos
NOT_DONE: .claude/settings.json stop hook template; checklist F9 section
RECOMMENDED_MEMORY_UPDATE: memory/active_task — update current task to session_end_hook complete, stop hook pending
```

## Example — blocked session

```
TASK_INTENT: fix F8 UTF-8 crash in external_project_facts_intake.py
WORK_COMPLETED: identified root cause at line 47 (missing errors= parameter); applied fix
FILES_TOUCHED: governance_tools/external_project_facts_intake.py
CHECKS_RUN: python -m governance_tools.external_project_facts_intake --repo D:\meiandraybook\artifacts\framework-checklist-scratch (ok, exit 0)
OPEN_RISKS: fix not tested against the actual non-UTF-8 file that caused the original crash (D:\meiandraybook memory files)
NOT_DONE: end-to-end test on real non-UTF-8 repo
RECOMMENDED_MEMORY_UPDATE: NO_UPDATE — risk still open, not a stable state to record
```

## Example — no material progress

```
TASK_INTENT: investigate memory update failure in external repos
WORK_COMPLETED: NONE — session used for analysis only, no code changes
FILES_TOUCHED: NONE
CHECKS_RUN: NONE
OPEN_RISKS: memory pipeline gap confirmed; session_end never called in external repos
NOT_DONE: actual fix — deferred to next session
RECOMMENDED_MEMORY_UPDATE: memory/active_task — add note: memory pipeline gap is confirmed root cause, fix is session_end_hook
```

---

## What the runtime does with this artifact

| Closeout state | Runtime behavior |
|---------------|-----------------|
| Valid and complete | `session_end` runs with content; memory closeout proceeds per policy |
| Missing | `session_end` runs without content; verdict records `closeout_missing`; memory not updated |
| Insufficient (hollow/invalid) | `session_end` runs; verdict records `closeout_insufficient`; memory not updated |

The runtime **always runs** at stop. A missing or invalid closeout does not abort the
stop hook — it produces a degraded verdict that records the gap.
