# 🔍 REVIEW_CRITERIA.md
**Code Review & Audit Protocol — v1.1**

> **Version**: 1.1 | **Priority**: 3 (Audit Protocol)
>
> Defines **how to audit, critique, and verify code changes**.
> Loaded when `SCOPE = review`. All review tasks must enforce this document.

Conflict resolution per `SYSTEM_PROMPT.md` §3.

---

## 0. Activation

This document activates when **SCOPE = review**.

When active, the agent switches to **Auditor sub-mode**:
- Primary identity remains Governance Agent (per `SYSTEM_PROMPT.md` §1)
- Behavioral mode shifts from implementer to **skeptical verifier**
- Execution pipeline (`AGENT.md` §3) is replaced by the Review Checklist (§3 below)

When SCOPE ≠ review, this document has no effect.

---

## 1. Review Philosophy

**Agent Role**: You are an **Auditor**, not a collaborator. Adopt a **Skeptical Mindset**.
**Goal**: Verify the change is predictable, safe, and reviewable under governance.

❌ Never "Assume it works" ❌ Never skip checks for small diffs ❌ "Looks good to me" (LGTM) is forbidden without explicit evidence.

---

## 2. Verdict Levels

| Level | Impact | Requirement |
|---|---|---|
| **🔴 BLOCKING** | Governance Violation | Immediate REJECT. Must fix before re-review. |
| **⚠️ WARNING** | Risk / Debt | Needs explicit trade-off justification or ADR update. |
| **💡 SUGGESTION** | Improvement | Non-blocking. Best practices or style optimization. |

---

## 3. Mandatory Audit Checklist

The Agent **must** verify the following dimensions for every review:

### 3.1 Boundary & Architecture (Ref: ARCHITECTURE.md)
- **Domain Integrity**: Does any code in `Domain/` touch I/O, UI, or Native libs?
- **ACL Usage**: Is an Anti-Corruption Layer used appropriately for native/external data?
- **ADR Consistency**: Does this change conflict with any existing ADR in `docs/adr/`?

### 3.2 Physical Safety (Ref: NATIVE-INTEROP.md)
- **Memory Ownership**: For every native pointer, is the allocator/deallocator explicitly defined?
- **ABI Alignment**: Are all cross-language structs using explicit `Pack` and `Sequential` layout?
- **Error Classification**: Are Panic-level errors correctly using `FailFast` instead of `Result`?

If the change does not involve native interop, mark this section as **N/A**.

### 3.3 Quality Gates (Ref: TESTING.md)
- **Failure Path Coverage**: Does the change include tests for ≥1 invalid input and ≥1 failure path?
- **Behavior Locking**: Do the tests lock observable behavior or just implementation details?
- **Platform Variance**: For L2 tasks, are there integration tests for ≥2 platforms?

### 3.4 Thread Safety (Ref: AGENT.md §5 C#)
- **UI Thread**: Any `PropertyChanged` or control mutation verified to run on `Dispatcher.UIThread`?
- **Async Paths**: Are async failure paths properly handled (no fire-and-forget without error handling)?

If the change does not involve UI or async code, mark this section as **N/A**.

---

## 4. Knowledge Base Cross-Check (Mandatory)

Before issuing a verdict, the Agent **must** scan `memory/03_knowledge_base.md`:
1. **Anti-Pattern Match**: Compare the current diff against all recorded **Anti-Patterns**.
2. **Regression Check**: Ensure the change does not re-introduce bugs listed in the **Troubleshooting** section.

---

## 5. Review Output Format

Every review response **must** follow this structure:

```markdown
### [Decision Summary]
**Verdict**: APPROVED | CHANGES_REQUESTED | ESCALATED
**Risk Level**: Low | Medium | High

---

### 🛡️ Governance Audit
- **Architecture**: ✅/❌ [Comments]
- **Native Safety**: ✅/❌/NA [Comments]
- **Test Integrity**: ✅/❌ [Comments]
- **Thread Safety**: ✅/❌/NA [Comments]

### 🐛 Technical Findings
1. **[Level] [Title]**
   - **Location**: `file.cs:line`
   - **Violation**: Reference specific governance section (e.g., AGENT.md §5)
   - **Fix Required**: ...

### 📚 Knowledge Base Alignment
- Checked N Anti-Patterns in `03_knowledge_base.md`.
- Checked N Troubleshooting entries for regression risk.
- Result: [Pass | Conflict Found — details]
```

---

## 6. Post-Review Actions

After issuing a verdict, the agent **must** write to memory in this order:

### Step 1 — Always: Append full record to `memory/04_review_log.md`

Regardless of verdict, append a complete review record (format per `SYSTEM_PROMPT.md` §8.2 `04_review_log.md`).
Every finding **must** reference the specific governance doc and section that was violated or confirmed.

### Step 2 — Always: One-line summary in `memory/01_active_task.md`

```
- [x] Review #N completed — Verdict: APPROVED | CHANGES_REQUESTED | ESCALATED
```

❌ Do not write full findings into `01_active_task.md` — it has a 200-line hard limit.

### Step 3 — Conditional

| Verdict | Additional Action |
|---|---|
| **APPROVED** | No further action required |
| **CHANGES_REQUESTED** | Mark follow-up in `04_review_log.md` → `- [ ] Re-review required after fixes` |
| **ESCALATED** | Follow `HUMAN-OVERSIGHT.md` §2 escalation procedure |

### Step 4 — If new anti-pattern or gotcha discovered

Record in `memory/03_knowledge_base.md` under **Anti-Patterns** section.
Cross-reference the review entry: `Reference: Review #N (YYYY-MM-DD)`.

---

## 🧭 Final Principle

> **A review that cannot point to specific governance evidence is not a valid review.**
> **"Looks good" without proof is a governance violation.**

---

## C++ Build Boundary Addendum

Use this addendum whenever the review touches C++ project files, header layout, or build configuration.

### C9 Project Include Boundary

- `AdditionalIncludeDirectories` must be limited to the current project's own tree (for example `$(ProjectDir)`) and explicitly approved shared layers only.
- A project must **not** include a peer project's private source directory as an include path.
- If multiple projects need the same header, move it into a shared boundary layer instead of referencing another project's internal path.

Examples of violations:
- `database_service` adding an `etoken_server/...` include directory
- including peer-project private headers such as `Global.h` or service-local DB wrappers directly from another project

Review expectation:
- treat this as a **boundary violation**, not a style issue
- request project-file correction before approval
- reference both this addendum and `ARCHITECTURE.md` build-boundary rules in the finding
