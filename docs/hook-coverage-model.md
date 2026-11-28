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
| Codex (OpenAI) | **A (unverified)** | `.codex/hooks.json` Stop hook | Mechanism configured (machine-local, gitignored); coverage unverified — pending first real session confirmation |
| GitHub Copilot | **B** | VS Code task (`.vscode/tasks.json`) | Must be run manually by the operator; no native session-end event |
| Gemini CLI | **B** | CLI wrapper or manual command | No native hook surface; requires wrapper integration |
| ChatGPT | **C** | Manual only | No local hook surface available |

Source: `governance_tools/manage_agent_closeout.py` AGENT_MANIFEST.

> **Codex note**: Tier A classification is based on the existence of a `.codex/hooks.json` Stop hook
> mechanism (configured 2026-06-06, machine-local, not committed to repo).  Coverage is not yet
> confirmed.  Once a real Codex session fires the hook successfully, this entry should be updated to
> `A (verified)` and the verification date recorded.

---

## Codex Stop configuration: verify before install or repair

Run from the framework checkout with the consumer root explicitly supplied:

```sh
python -m governance_tools.manage_agent_closeout --project-root <repo> verify --agent codex
python -m governance_tools.manage_agent_closeout --project-root <repo> install --agent codex
python -m governance_tools.manage_agent_closeout --project-root <repo> repair --agent codex
```

`verify`, `install` and `repair` share the same configuration classification.
Do not interpret every `installed=false` as permission to add a direct entry.

| `configuration_state` | Meaning | `verify.installed` | Install / repair |
| --- | --- | --- | --- |
| `missing` | No formal closeout candidate or adapter declaration identified | false | Add one framework entry |
| `standard` | Exactly one current framework entry bound to the requested root | true | No change |
| `standard_stale` | Exactly one framework-owned entry with an obsolete command or wrong root | false | Replace that owned entry, without increasing the entry count |
| `standard_duplicate` | Multiple entries, all framework-owned, with no project adapter declaration | false | Consolidate to one entry bound to the requested framework root |
| `project_adapter_unverified` | Possible project closeout entry, or an invalid / mismatched declaration | false | Preserve configuration; return `blocked` |
| `project_adapter_verified` | Exactly one adapter matches the explicit declaration and framework target | true only with correct SessionStart wiring; configuration only | Add missing SessionStart wiring; with correct wiring, install returns `already_configured`, repair returns `no_repair_needed`; CLI exit 0 |
| `conflict` | Multiple possible formal entries with a project / unknown entry or adapter declaration participating | false | Preserve configuration; return `blocked` |
| `invalid` | Unreadable / malformed hooks JSON, duplicate keys, or malformed Stop containers | false | Preserve configuration; return `blocked` |

`blocked` is a non-success result (CLI exit 1). A human decides which entry to
retain, corrects or declares the project adapter, or removes a conflict. Neither
install nor repair makes that choice. Repeated calls do not accumulate entries.
They install and verify SessionStart while preserving existing SessionStart and
unrelated Stop handlers byte-identically, including their JSON spelling and
whitespace. A single stale framework entry can still be
rebound. Pure framework duplicates are consolidated without bypassing any project
entry. If a project adapter, declared adapter or unknown formal candidate
participates, the configuration remains a conflict and is preserved. A verified
project adapter also needs correct SessionStart wiring for `verify` to report
installed. Install and repair add missing SessionStart wiring while preserving
the adapter; with correct wiring, both succeed without changing any bytes.
Differing SessionStart bindings block both operations. That success verifies
only a configuration match, not execution, hook trust or formal closeout.

### What counts as a possible formal entry

The manager distinguishes ownership from a closeout candidate. Its existing
framework-owned command forms remain recognized for stale/wrong-root replacement.
An invoked command carrying both `--agent-id codex` and
`--trigger-mode native_hook` (also accepting `--flag=value`) is a closeout
candidate even when its executable or script name is unknown. The same applies
to Python invoking `-m governance_tools.session_closeout_entry`, or inline Python
importing that module. Both command fields are inspected, including encoded
PowerShell. Shell alternatives within one hook object count as one configured
entry; the count is not a measurement of runtime calls.

These syntax signals reserve a possible entry for verification; they never
prove delegation. Diagnostic `echo` / `printf` / `Write-Output` / `Write-Host`
commands, textual mentions, similarly named scripts with other arguments, and
handlers for another purpose are left alone and do not count as conflicts.
The manager does not execute hooks or inspect arbitrary project script bodies.
An opaque adapter without these signals must use the explicit declaration below;
absence of a detected candidate cannot establish that arbitrary code never calls
closeout. Review opaque Stop handlers before asking the manager to install.

### Minimal project adapter declaration

There was no existing Codex project adapter declaration in the manager. A project
can now maintain `.codex/closeout-adapter.json` alongside its hooks file. This is
a configuration binding contract, not a plugin API, execution proof or trust
setting. The manager never creates or updates the declaration.

```json
{
  "command": "repo_root=\"$(git rev-parse --show-toplevel)\" && python3 \"$repo_root/scripts/turn_adapter.py\" --project-root \"$repo_root\" --format json --agent-id codex --trigger-mode native_hook",
  "delegates_to": "framework/governance_tools/session_closeout_entry.py"
}
```

Copy the actual hook's complete `command` string. If the hook has
`commandWindows`, declare that complete string too, including encoded transport;
omitting or changing either platform command leaves the adapter unverified.
`delegates_to` names the framework entry the project declares it delegates to.
Relative paths resolve from the consumer root; the resolved path must equal the
requested framework root's `governance_tools/session_closeout_entry.py` and exist
as a file. Unknown fields and malformed declarations are unverified. A declaration
that does not match the hooks file blocks installation even for an opaque adapter.

The project owns reviewing the adapter's actual delegation and extra checks.
`project_adapter_verified` only means the declaration matches one configured
entry and the requested framework target. It does not verify the adapter's
implementation, native execution, execution order or hook trust. A direct entry
alongside even a declared adapter remains a conflict; install/repair preserve both.

Configuration is not execution. After preparation, retain the existing
`PREPARED` / `PENDING_HOOK` distinction. Formal completion still requires the
existing same-session / same-SHA canonical closeout and released ownership
evidence. R1/R2 identity, receipt and ownership rules are unchanged. A declaration
does not admit manual fallback for a prepared R2 candidate or automatically trust
a hook. Re-evaluate the declaration whenever either command or the framework
target changes; remove it only when the project deliberately retires the adapter.

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

**Cross-tier comparison:** Signal ratios are not directly comparable across tiers
due to differing coverage characteristics.  A Tier B repo with signal_ratio=10%
and a Tier A repo with signal_ratio=10% are not equivalent findings — the Tier B
value reflects only the fraction of hook-observed sessions, while the Tier A value
reflects the actual session population.  Always identify the tier before comparing
or ranking repos by metric.

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
