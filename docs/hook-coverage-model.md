# Hook Coverage Model — Agent Tier Classification

> This document defines the hook coverage tier model for `session_end_hook`
> and explains how tier classification affects the reliability of E8b trend
> interpretation.
>
> Read this document alongside `observability-chain.md` (E8a hook coverage gap
> section) before interpreting `canonical_audit_trend` results.

---

## Why this model exists

E8b trend interpretation is only meaningful if you know what population of sessions
it represents.  The E8a log records sessions that *reached* `session_end_hook`.
Sessions that did not reach it are outside the observable set.

The fraction of sessions that were observed depends on how the hook is triggered,
which depends on the agent being used.  This model classifies agents by their
triggering mechanism so that interpreters can reason about the likely coverage
level of a repo's E8b trend.

---

## Tier definitions

| Tier | Label | Hook mechanism | Expected coverage |
|------|-------|----------------|-------------------|
| A | `native_auto_closeout` | Agent has a formal stop/exit hook; runs at every session end automatically | High — close to 100% when configured correctly |
| B | `wrapper_based` | No native hook; triggered via launcher script, VS Code task, or CI wrapper | Variable — depends on workflow discipline |
| C | `manual_only` | No automation surface; operator must run the hook command manually | Low — may be near 0% in practice |
| D | `unsupported` | No stable integration path defined | Unknown |

---

## Per-agent classification

| Agent | Tier | Trigger surface | Notes |
|-------|------|-----------------|-------|
| Claude Code | **A** | `.claude/settings.json` Stop hook | Runs automatically at session end; no operator action required after setup |
| GitHub Copilot | **B** | VS Code task (`.vscode/tasks.json`) | Must be run manually by the operator; no native session-end event |
| Gemini CLI | **B** | CLI wrapper or manual command | No native hook surface; requires wrapper integration |
| ChatGPT | **C** | Manual only | No local hook surface available |

Source: `governance_tools/manage_agent_closeout.py` AGENT_MANIFEST.

---

## Critical distinction: tier ≠ coverage rate

**Tier classification describes the observation *mechanism*, not the actual coverage
rate.**

Two repos both using Tier B (Copilot) may have very different actual coverage:

- A disciplined operator who runs the VS Code task after every session → 90% coverage
- An operator who runs it occasionally → 20% coverage

Both are Tier B.  The tier tells you the *type* of gap risk, not its size.

**Actual coverage depends on workflow discipline and may vary significantly within
the same tier.**  There is currently no automated mechanism to measure actual
coverage rate for any tier.

---

## How tier affects E8b trend reliability

| Tier | E8b trend reliability | Interpretation guidance |
|------|----------------------|-------------------------|
| A | High | Trend reflects actual session history with high fidelity; suitable for adoption decisions |
| B | Unknown | Trend reflects observed subset; assess hook execution discipline before interpreting; low signal_ratio may be falsely reassuring |
| C | Low | Trend may reflect only a small, non-representative subset; treat as anecdotal evidence only |

**E1b (canonical usage enforcement) prerequisite:** E1b decisions must not be based
on E8b data from Tier B or C repos where hook coverage rate is unobserved.  Only
Tier A repos have a sufficiently defined observable population to support stronger
enforcement claims.

---

## Declaring tier per consuming repo

Each consuming repo should declare its agent tier in `governance/gate_policy.yaml`
so that reviewers can immediately identify the E8b reliability level.

Add a comment block after the `skip_test_result_check` line:

```yaml
# ── hook coverage tier ─────────────────────────────────────────────────────
# Declares the session_end_hook triggering mechanism for this repo.
# Tier A: native auto-closeout (Claude Code Stop hook)
# Tier B: wrapper-based (Copilot VS Code task, Gemini CLI wrapper)
# Tier C: manual only (ChatGPT or equivalent)
#
# Affects how E8b trend results should be interpreted.
# See: docs/hook-coverage-model.md
#
# hook_coverage_tier: B
```

This is a documentation-only declaration (a comment, not a parsed policy field).
It has no effect on gate behaviour.  Its purpose is to give reviewers the context
to correctly weight E8b trend data.

---

## Relationship to other documents

| Document | What it covers | Relationship |
|----------|---------------|--------------|
| `observability-chain.md` | E8a/E8b layer architecture and authority boundaries | Defines the hook coverage gap; this doc explains the tier model that determines gap severity |
| `reviewer-interpretation-guide.md` | How to read individual session output | Hook coverage gap section links here for tier-level detail |
| `governance-maintenance-checklist.md` | Periodic health checks | Section 5 (Framework-Consumer Sync) includes checking that hooks are triggered |
| `consuming-repo-adoption-checklist.md` | Onboarding new repos | Step 8 (gate policy) includes session hook trigger verification |

---

## What this model does NOT provide

- A way to measure actual coverage rate (that is unobserved for all tiers)
- A guarantee that Tier A coverage is exactly 100% (misconfiguration or early exit
  before hook fires can still create gaps)
- A recommendation on which agent to use — tier is an observation property, not a
  quality judgment about the agent itself
