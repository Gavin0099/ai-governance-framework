# REVIEW_CRITERIA.md
**Code Review and Audit Protocol - v1.2**

> **Version**: 1.2 | **Priority**: 3 (Audit Protocol)
>
> Defines how to audit, critique, and verify code changes.
> Loaded when `SCOPE = review`.

---

## 0. Activation

This document activates when `SCOPE = review`.

When active:
- the agent stays governance-first
- behavioral mode becomes skeptical verifier rather than implementer
- findings must be tied to evidence, not intuition

---

## 1. Review Philosophy

Review goal:
- verify the change is predictable
- verify the change is safe
- verify the change is reviewable under governance

Never assume a change works merely because it is small.
Never issue approval without naming the evidence used.

---

## 2. Verdict Model

| Verdict | Meaning | Use When |
|---|---|---|
| `APPROVED` | Safe enough to accept | No blocking governance or correctness issue remains |
| `CHANGES_REQUESTED` | Fixes required | Concrete blocking issues exist |
| `ESCALATED` | Human decision needed | Risk/trade-off ambiguity remains after review |

### 2.1 Finding Levels

| Level | Meaning |
|---|---|
| `BLOCKING` | Governance, correctness, or safety issue that must be fixed |
| `WARNING` | Risk, debt, or weak evidence that should be called out explicitly |
| `SUGGESTION` | Non-blocking improvement |

Do not confuse `ESCALATED` with `BLOCKING`.  
Escalation is for unresolved material ambiguity, not only for defects.

---

## 3. Mandatory Audit Checklist

### 3.1 Boundary and Architecture

Check:
- does domain code touch forbidden I/O, UI, OS, or native concerns
- is ACL usage appropriate when external/native models are involved
- does the change conflict with an ADR or boundary rule

### 3.2 Physical and Native Safety

When native interop is in scope, check:
- memory ownership is explicit
- ABI layout is explicit where required
- panic/fail-fast vs recoverable error handling is coherent

If native interop is absent, mark this section `N/A`.

### 3.3 Quality and Verification

Check:
- does the evidence match task risk
- are failure paths considered where applicable
- does verification lock behavior rather than implementation trivia
- for legacy refactors, was baseline buildability actually established

### 3.4 Thread Safety and Async Safety

When UI or async paths are touched, check:
- UI-affecting updates stay on the correct thread
- async failure paths are handled

If irrelevant, mark `N/A`.

### 3.5 Dirty Worktree and Scope Hygiene

When the worktree was dirty during implementation or review, check:
- unrelated dirty files were not silently mixed into the reviewed scope
- touched-file overlap was either handled or explicitly escalated
- the commit/review boundary is understandable

---

## 4. Knowledge Base Cross-Check

Before issuing a verdict, scan `memory/03_knowledge_base.md` for:
1. anti-pattern matches
2. previously recorded regression patterns

If a known anti-pattern reappears, call it out explicitly.

---

## 5. Legacy Refactor Review Addendum

For legacy repos, refactors, rollbacks, or baseline resets, review must check:
- was the claimed baseline actually verified with the authoritative build path
- was the canonical toolchain identified
- is the change being presented as a safe refactor despite unstable baseline evidence

If the baseline is unverified:
- do not describe the result as a clean refactor
- issue at least a `WARNING`
- escalate when the conclusion depends on the baseline being stable

---

## 6. Review Output Format

Every review response should include:

```markdown
### [Decision Summary]
**Verdict**: APPROVED | CHANGES_REQUESTED | ESCALATED
**Risk Level**: Low | Medium | High

### Governance Audit
- Architecture: ...
- Native Safety: ... | N/A
- Test Integrity: ...
- Thread Safety: ... | N/A
- Baseline Status: Stable | Unverified | Unstable | N/A

### Technical Findings
1. [BLOCKING|WARNING|SUGGESTION] Title
   - Location: `path:line`
   - Evidence: ...
   - Rule Reference: ...
   - Fix Required / Reasoning: ...

### Knowledge Base Alignment
- Anti-patterns checked: N
- Regression notes checked: N
- Result: Pass | Conflict Found
```

Every non-trivial finding must name:
- location
- evidence
- rule reference

---

## 7. Post-Review Memory Actions

After issuing a verdict:

1. append full review record to `memory/04_review_log.md`
2. add one-line summary to `memory/01_active_task.md`
3. if a new anti-pattern was discovered, record it in `memory/03_knowledge_base.md`

Keep `memory/01_active_task.md` short; do not dump full findings there.

---

## 8. C++ Build Boundary Addendum

Use this addendum when review touches C++ project files, header layout, or build configuration.

Hard checks:
- `AdditionalIncludeDirectories` or equivalent must not point into peer-project private trees
- cross-project private headers must not be normalized as acceptable merely because the build passes
- if a header is shared, it should live in an explicit shared boundary layer

Treat this as a boundary issue, not a style issue.

---

## 9. Final Principle

> **A review without named evidence is not a valid review.**
> **Use escalation when the conclusion depends on ambiguity; use blocking findings when the violation is concrete.**
