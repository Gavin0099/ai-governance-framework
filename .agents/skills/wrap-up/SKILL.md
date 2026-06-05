---
name: wrap-up
description: Draft a candidate closeout for the current session and write it to the closeout_candidates directory. Use when the session is ending and you want to record task intent, work summary, tools used, artifacts referenced, and open risks so the system can produce a valid canonical closeout at session end.
---

# Wrap-Up — Candidate Closeout Drafting Surface

This skill drafts a **candidate closeout** and writes it to disk.

**Role**: quality-of-input tool only. This skill does NOT:
- Determine `closeout_status` (that is done by `session_end_hook`)
- Write to `artifacts/runtime/closeouts/` (canonical — system only)
- Evaluate whether the candidate will pass validation

The candidate is untrusted input. The system validates it at session end.

---

## Prerequisite: session_id

`session_id` is required to name the candidate file. It must be available in the
current session context. If unavailable, stop and surface the gap — do not invent
an ID or use a placeholder.

---

## Workflow

### Step 1 — Draft the five fields

Review the current session and draft each field honestly:

**`task_intent`** (string)
One sentence. What did this session aim to accomplish?
- ✅ "Add closeout audit tool to governance_tools/"
- ❌ "Work on the project"

**`work_summary`** (string)
Concrete description of what was done. Name specific files, functions, or test names.
Do not use vague phrases like "completed relevant changes" or "updated code".
- ✅ "Created governance_tools/closeout_audit.py with build_closeout_audit() and format_human_result(). Added tests/test_closeout_audit.py (28 tests). Updated runtime_surface_manifest.py to declare _canonical_closeout and _canonical_closeout_context."
- ❌ "Implemented the audit feature and added tests."

**`tools_used`** (list of strings)
Tools actually invoked during the session. Use exact names.
- ✅ ["read", "edit", "write", "bash", "pytest"]
- ❌ ["various tools", "standard tools"]

**`artifacts_referenced`** (list of strings)
Relative paths from project root for files created or meaningfully modified.
- ✅ ["governance_tools/closeout_audit.py", "tests/test_closeout_audit.py"]
- ❌ ["the audit file", "tests/"]

**`open_risks`** (list of strings)
Unresolved issues, known gaps, or concerns worth surfacing. Empty list is valid if there
are genuinely none.
- ✅ ["_VERIFIABLE_TOOLS normalization not implemented — variant spellings will miss", "PLAN.md is STALE (8d)"]
- ✅ []

### Step 2 — Self-check against checklist

Before writing, verify each item. These are heuristics, not schema validation.
Passing this checklist does NOT guarantee `closeout_status = "valid"`.

- [ ] `task_intent` is one sentence and describes a specific goal
- [ ] `work_summary` names at least one specific filename
- [ ] `work_summary` does not contain "relevant", "related", "various", "some", or "etc."
- [ ] `tools_used` lists actual tool names, not categories
- [ ] `artifacts_referenced` contains relative paths (not directory names or descriptions)
- [ ] `open_risks` is populated or is consciously empty
- [ ] All paths in `artifacts_referenced` are relative to project root

If any checklist item fails, revise the field before writing.

### Step 3 — Write the candidate file

Run the following Python command from the project root:

```python
python -c "
import json, sys
from pathlib import Path
sys.path.insert(0, '.')
from runtime_hooks.core._canonical_closeout import write_candidate

SESSION_ID = '<session_id>'  # replace with actual session_id
PROJECT_ROOT = Path('.')

candidate = {
    'task_intent': '<task_intent>',
    'work_summary': '<work_summary>',
    'tools_used': [<tools_used>],
    'artifacts_referenced': [<artifacts_referenced>],
    'open_risks': [<open_risks>],
}

path = write_candidate(SESSION_ID, PROJECT_ROOT, candidate)
print(f'candidate written: {path}')
"
```

The file is written to:
```
artifacts/runtime/closeout_candidates/{session_id}/{YYYYmmddTHHMMSSffffffZ}.json
```

Calling `/wrap-up` twice creates two timestamped files. The system picks the latest
at session end. This is append-only — earlier candidates are preserved.

---

## Output Expectations

- Confirm the candidate was written and show the path.
- State `closeout_status` is NOT determined here — that happens at session end.
- If any checklist item could not be satisfied, say so explicitly.
- Do not claim the candidate will produce `closeout_status = "valid"`.

---

## What Happens Next

At session end, `run_session_end()` will:
1. Call `pick_latest_candidate()` to load this file
2. Call `build_canonical_closeout()` to validate and normalize it
3. Write the canonical artifact to `artifacts/runtime/closeouts/{session_id}.json`

The canonical `closeout_status` depends on validation results, not on this skill.
`closeout_status = "valid"` requires schema + semantic checks to pass.
