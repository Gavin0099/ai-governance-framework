# Closeout Readiness Rollout

> Version: 1.0
> Related: docs/closeout-readiness-spectrum.md, docs/closeout-repo-readiness.md

---

## Problem

The Session Closeout Obligation was added to `baselines/repo-min/AGENTS.base.md`
after some repos were already adopted. Those repos correctly report Level 0 in the
readiness audit because their `AGENTS.base.md` predates the obligation.

The wrong fix: re-adopt all repos at once. This risks:
- Overwriting uncommitted changes in `AGENTS.md` / `AGENTS.base.md`
- Triggering full re-adoption logic when only one section needs to change
- No diff review before write

The right fix: observable, incremental, rollback-safe.

---

## Three-phase rollout

### Phase 1 — Audit: understand before fixing

```bash
# Single repo
python -m governance_tools.readiness_audit --repo /path/to/repo

# Multiple repos
python -m governance_tools.readiness_audit --repo /path/a /path/b /path/c

# Scan a workspace directory for all git repos
python -m governance_tools.readiness_audit --scan-dir /workspace

# JSON output for scripting
python -m governance_tools.readiness_audit --repo /path --format json
```

Output: a table showing each repo's level, limiting factor, and suggested next step.

**Rule:** Run Phase 1 before Phase 2. Do not start patching repos whose level
you don't know yet. Level 2 or Level 3 repos need no closeout patch — patching
them anyway is waste and risk.

---

### Phase 2 — Patch: opt-in, diff-first, single file only

```bash
# Preview (no writes)
python -m governance_tools.upgrade_closeout --repo /path/to/repo --dry-run

# Apply after reviewing diff
python -m governance_tools.upgrade_closeout --repo /path/to/repo

# Multiple repos
python -m governance_tools.upgrade_closeout --repo /path/a /path/b
```

What it touches: **only `AGENTS.base.md` (or `AGENTS.md`)**.
What it does: appends the `## Session Closeout Obligation` section.
What it skips: repos that already have the obligation (idempotent).

**Rollback:**
```bash
cd /path/to/repo
git checkout HEAD -- AGENTS.base.md
```

Or manually: remove everything from `## Session Closeout Obligation` to end of file.

---

### Phase 3 — Verify: re-audit after patching

```bash
# Re-run audit to confirm level has advanced
python -m governance_tools.readiness_audit --repo /path/to/repo
```

Expected after Phase 2: Level 0 → Level 1 (if schema_doc and artifacts are present).

If still Level 0 after patching: check `limiting_factor` — the diff may have
introduced a non-UTF-8 encoding or the `suggested_next_step` points at something
else.

---

## What `suggested_next_step` means

Every `readiness_audit` and `session_end_hook` output includes a
`suggested_next_step` keyed to the specific `limiting_factor`.

| Limiting factor | Suggested next step |
|----------------|---------------------|
| `artifacts_not_writable` | `mkdir -p artifacts/runtime && chmod -R u+w artifacts/` |
| `agents_base_has_obligation` | `python -m governance_tools.upgrade_closeout --repo <repo>` |
| `agents_base_has_anchor_guidance` | `python -m governance_tools.upgrade_closeout --repo <repo>` (re-run) |
| `prior_verdict_artifacts_exist` | Run one compliant session to produce first verdict |
| `schema_doc_present` | Ensure `docs/session-closeout-schema.md` exists in framework repo |

`suggested_next_step` is advisory, not automated. It requires human review
and opt-in execution.

---

## Framework repo self-upgrade

The framework repo itself (`d:/ai-governance-framework`) reports Level 0 because
its root `AGENTS.base.md` predates the closeout obligation update to
`baselines/repo-min/AGENTS.base.md`.

To upgrade:
```bash
python -m governance_tools.upgrade_closeout --repo .
```

This is intentionally not done automatically. The framework repo's own governance
files are under active development. Patching them in an automated rollout risks
overwriting work in progress.

---

## What this rollout does NOT do

- Does not re-adopt repos (no contract.yaml changes, no .governance/ changes)
- Does not modify memory/ files
- Does not automatically advance repos past Level 1 (anchor guidance and
  prior verdict artifacts require active session work, not just a patch)
- Does not guarantee that AI agents will write valid closeouts after patching —
  the obligation section is instruction, not enforcement

The stop hook provides enforcement. The patch provides instruction.
Both are required for Level 1 to be meaningful.

---

## Observable signals that the rollout is working

After patching a repo and running at least one session:

1. `readiness_audit` reports Level 1 (or higher) for that repo
2. `session_end_hook` verdict artifacts appear in `artifacts/runtime/verdicts/`
3. Closeout status advances from `closeout_missing` to `schema_valid` or better
4. `repo_readiness_level` in verdict metadata matches the audit output

If verdict status is still `closeout_missing` after multiple sessions, the AI
has not internalized the obligation. Review the `AGENTS.base.md` content and
confirm the stop hook is configured (see `docs/stop-hook-setup.md`).
