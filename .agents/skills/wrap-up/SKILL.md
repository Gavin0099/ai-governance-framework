---
name: wrap-up
description: Draft a candidate closeout for the current session and write it to the closeout_candidates directory. Use when the session is ending and you want to record task intent, work summary, tools used, artifacts referenced, and open risks so the system can produce a valid canonical closeout at session end.
---

# Wrap-Up — Candidate Closeout Drafting Surface

This skill explicitly prepares a **candidate closeout** and matching shared text
for a registered submodule consumer using R1 identity and R2 ownership.

Invoke only for explicit wrap-up or preparation for a defined session end.
Task DONE and per-turn Stop are not session end and do not automatically invoke
this skill. The Agent supplies meaning; the runtime does not infer a summary.

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

### Step 3 — Prepare through the registered submodule entry

Use the existing native session ID and existing Codex v1.1 envelope. Do not
invent an ID, recreate identity for a historical session, or upgrade a v1.0
envelope. Consumer root and framework root are different absolute paths.

Prerequisites checked before payload writes:

- consumer `.gitmodules` and `governance/framework.lock.json` are tracked,
  committed, unchanged regular files;
- framework path equals the registered submodule path, its index gitlink is
  committed, and gitlink OID = checkout HEAD = lock `adopted_commit`;
- framework checkout is clean and the entry executes from that checkout;
- no inherited `GIT_*` overrides (these could change the index/root seen by
  R1/R2); invoke from an ordinary environment, not an inherited Git hook;
- existing v1.1 envelope binds the target consumer; session is not consumed.

Supply the five fields as a UTF-8 JSON object, plus these optional legacy-text
fields when known: `checks_run`, `not_done`, `recommended_memory_update`.
Report actual checks/results; `tools_used` alone is not test evidence. Omitted
legacy fields become `NOT PROVIDED`, which does not qualify closeout or a gate.
Use `NONE` only when the Agent can honestly assert none. Use `NO_UPDATE` only
when that is the actual memory recommendation.

All strings must be nonempty single lines. List items must not contain commas
or equal `NONE`: the existing legacy parser cannot represent those items
unambiguously. Empty lists represent none. Rephrase honestly or report the
representation limit; never silently drop an item.

Example invocation (replace roots and ID with independently verified values):

```powershell
python -B "E:/consumer/SubModule/ai-governance-framework/governance_tools/prepare_closeout_candidate.py" --consumer-root "E:/consumer" --framework-root "E:/consumer/SubModule/ai-governance-framework" --session-id "<existing-session-id>" --input "E:/consumer/preparation-input.json"
```

The JSON can instead arrive on stdin by omitting `--input`. Do not embed summary
text in shell code. The input file is only a transport file, not a candidate or
proof of preparation.

Outputs are under the **consumer**, never the framework submodule:

```
artifacts/runtime/closeout_candidates/{session_id}/{YYYYmmddTHHMMSSffffffZ}.json
artifacts/session-closeout.txt
```

The pure builder fixes generated time, path and UTF-8 LF bytes before R2 reserves
their digests. The same input renders both outputs. Under the existing R2 OS
lock, preparation reserves HOLD, writes both payloads, reads them back exactly,
then confirms OWNED. It does not release ownership or run closeout.

Repeated explicit preparation of the same unconsumed session appends a newer
candidate and refreshes matching text. A clock/path collision rejects. Another
session cannot replace an active owner. Owner missing + legacy shared text
already present rejects as `AMBIGUOUS_LEGACY_STATE`; do not delete historical
text or invent ownership to get past it.

Partial writes remain under HOLD. Explicit retry appends a new candidate;
never edit/delete the previous partial candidate or reset consumption. Latest
invalid candidate does not fall back to an older valid one. R2 release-only
reconciliation remains a separate operation, not a preparation retry.

These are cooperative correctness checks, not protection against hostile local
code, arbitrary filesystem writers or concurrent Git mutations. Preparation
does not install SessionStart, upgrade consumers, enable automatic invocation,
change promotion or restore successful `manual_fallback` closeout.

---

## Output Expectations

- Report PREPARED / OWNED only on exit 0; show the candidate path, generation,
  candidate SHA256 and text digest from the returned JSON.
- On failure, report rejection and any observed HOLD/partial payloads; do not
  claim rollback, successful closeout, or retry success without verification.
- State `closeout_status` is NOT determined here — that happens at session end.
- If any checklist item could not be satisfied, say so explicitly.
- Do not claim the candidate will produce `closeout_status = "valid"`.

---

## What Happens Next

In a separately qualified lifecycle, the R2-protected formal closeout entry will:
1. Call `pick_latest_candidate()` to load this file
2. Call `build_canonical_closeout()` to validate and normalize it
3. Write the canonical artifact to `artifacts/runtime/closeouts/{session_id}.json`

The canonical `closeout_status` depends on validation results, not on this skill.
`closeout_status = "valid"` requires schema + semantic checks to pass.
Preparation PASS is not Consumer Memory E2E PASS. Full E2E additionally needs
the actual lifecycle trigger, receipt, real test evidence, gate and daily memory.
Do not change trigger mode to make that qualification pass.
