# External Repo Functional Test Checklist

> Version: 2026-04-05 rev2 (post first-run corrections)
> Framework status: Beta (Beta Gate passed 2026-03-28)
> Use this checklist to verify that this framework's core features work correctly
> when applied to your own repository.
>
> First run recorded: `docs/` — see test report 2026-04-05 for full findings.

---

## Prerequisites

```bash
git clone https://github.com/Gavin0099/ai-governance-framework.git ai-gov
cd ai-gov
pip install -r requirements.txt
```

Your test repo must be:
- A git repository (`git init` if needed)
- Accessible as a local path
- Memory files must be UTF-8 encoded (non-UTF-8 bytes will be replaced, not error)

**Cross-repo environment note:** If your framework checkout and test repo are on
different drives or paths, always pass `--framework-root <path-to-ai-gov>` to
`adopt_governance.py` and `governance_drift_checker.py`. Omitting it can cause
the tools to resolve the wrong baseline source.

---

## F1 — Onboarding adoption

Tests that `adopt_governance.py` can scaffold governance files into a new repo.

```bash
# Dry run (no files written)
python governance_tools/adopt_governance.py \
  --target <your-repo-path> \
  --framework-root <path-to-ai-gov> \
  --dry-run

# Live run
python governance_tools/adopt_governance.py \
  --target <your-repo-path> \
  --framework-root <path-to-ai-gov>
```

**Pass criteria:**
- [ ] Dry run prints `[dry-run] PLAN.md — would copy from template`
- [ ] Dry run prints `[dry-run] Would write: .../.governance/baseline.yaml`
- [ ] Dry run exits with code 0 and prints `Dry-run complete. No files were written.`
- [ ] Live run writes `contract.yaml`, `AGENTS.md`, `.governance/baseline.yaml` into target repo
- [ ] Live run also scaffolds `memory/` files (01–04)

**Known prerequisite:** target must be a git repo. If you see "not a git repo", run `git init` in the target first.

---

## F2 — Governance drift check

Tests that `governance_drift_checker.py` can detect drift between the framework baseline and a consuming repo.

```bash
# On framework repo itself
python governance_tools/governance_drift_checker.py \
  --repo . \
  --framework-root .

# On an adopted external repo
python governance_tools/governance_drift_checker.py \
  --repo <your-repo-path> \
  --framework-root <path-to-ai-gov>
```

**Pass criteria:**
- [ ] Returns structured output with `ok`, `severity`, `findings`, `errors`
- [ ] `ok=True` means no critical drift; `ok=False` means blocking findings

**Exit code contract (actual behavior):**

| Exit code | Meaning |
|-----------|---------|
| `0` | ok — no findings |
| `1` | warning — findings present, not blocking |
| `2` | critical — blocking drift detected |

Note: `ok=True` with `severity=warning` still exits `1`. This is expected behavior,
not a test failure.

**Note:** A freshly adopted repo will typically show `source_commit_recorded` and
`expansion_boundary` warnings (exit 1, ok=True). This is not a failure.

---

## F3 — Quickstart smoke

Tests that the framework's minimum runtime (session_start + pre_task) works end-to-end.

```bash
# Framework repo default (most reliable)
python governance_tools/quickstart_smoke.py

# With explicit project root and contract
python governance_tools/quickstart_smoke.py \
  --project-root <your-repo-path> \
  --plan <your-repo-path>/PLAN.md \
  --contract <your-repo-path>/contract.yaml
```

**Pass criteria:**
- [ ] `ok=True`
- [ ] `pre_task_ok=True`
- [ ] `session_start_ok=True`
- [ ] Prints `contract_mode=repo-default` (default run) or `contract_mode=explicit`

**Note:** Run without `--contract` on the framework repo is the most reliable path.
Explicit external contract runs require the contract's domain/rules to align with
available rule packs (`governance/rules/`). Available packs: `avalonia`, `common`,
`cpp`, `csharp`, `gl-hub-vendor-cmd`, `kernel-driver`, `python`, `refactor`, `swift`.
If session_start fails with "Unknown rule packs", the contract references a rule
pack that does not exist locally.

---

## F4 — Session lifecycle (pre_task + post_task)

Tests that runtime hooks process a task correctly.

```bash
# pre_task with a contract
python runtime_hooks/core/pre_task_check.py \
  --project-root . \
  --rules common \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate \
  --task-text "Implement user authentication" \
  --contract examples/decision-boundary/minimal-preconditions/contract.yaml \
  --format json

# post_task (run from stdin or a file)
echo "" | python runtime_hooks/core/post_task_check.py \
  --project-root . \
  --contract examples/decision-boundary/minimal-preconditions/contract.yaml \
  --format json
```

**Pass criteria (pre_task):**
- [ ] Returns JSON with `"ok": true` or `"ok": false` (either is valid — it means the hook ran)
- [ ] `decision_boundary.preconditions_checked` array is present
- [ ] `boundary_effect` is one of: `pass`, `escalate`, `restrict_code_generation_and_escalate`

**Pass criteria (post_task):**
- [ ] Returns structured JSON without unhandled exception
- [ ] Exit code is 0 or 1 (not a Python traceback)

**Note:** `post_task_check` without a `[Governance Contract]` block in the response
will return `ok=false` with `"Missing governance contract in task output"`. This is
correct behavior — not a framework bug. A real compliant post-task payload must
include that block.

---

## F5 — Decision Boundary Layer (DBL) enforcement

Tests that the pre_task hook actually enforces precondition rules, not just documents them.

```bash
# This task matches protocol_implementation but provides no spec — should escalate
python runtime_hooks/core/pre_task_check.py \
  --project-root . \
  --rules common \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate \
  --task-text "Implement protocol handling for firmware packets" \
  --contract examples/decision-boundary/minimal-preconditions/contract.yaml \
  --format json
```

**Pass criteria:**
- [ ] `missing_spec.applies = true`
- [ ] `missing_spec.action = restrict_code_generation_and_escalate`
- [ ] `boundary_effect = escalate`

This confirms the framework enforces rules at runtime, not just at read time.

---

## F6 — Domain-specific rule packs

Tests that domain rule packs are loaded when a contract specifies a domain.

```bash
# List available rule packs
ls governance/rules/

# Run smoke with a domain contract
python governance_tools/quickstart_smoke.py \
  --project-root <your-repo-path> \
  --plan <your-repo-path>/PLAN.md \
  --contract <your-repo-path>/contract.yaml
```

**Pass criteria:**
- [ ] `governance/rules/<domain>/core.md` exists for the domain named in the contract
- [ ] quickstart_smoke exits with `ok=True` and `session_start_ok=True`

**Requirements for pass:**
1. The contract's `rules:` field must only reference packs that exist in `governance/rules/`
2. The contract's `domain:` value must match an available rule pack directory name, or be empty
3. If `session_start_ok=False` with "Unknown rule packs" error, the contract references
   a non-existent pack — update the contract's `rules:` field

---

## F7 — External repo readiness check

Tests that the framework can assess whether an external repo is ready for onboarding.

```bash
python governance_tools/external_repo_readiness.py --repo <your-repo-path>
```

**Pass criteria:**
- [ ] Returns structured output
- [ ] `ready=True` or `ready=False` is present
- [ ] Output identifies missing governance files explicitly (not silently skipping them)

**Note:** A newly adopted repo will show warnings about `framework version metadata`,
`plan freshness`, and `expansion_boundary`. These are expected. `ready=True` with
warnings is a pass.

---

## F8 — Project facts intake

Tests that the framework can capture project metadata from an adopted repo.

```bash
# Use module invocation (direct script invocation is broken — do not use python governance_tools/external_project_facts_intake.py)
python -m governance_tools.external_project_facts_intake \
  --repo <your-repo-path> \
  --project-root <path-to-ai-gov>
```

**Pass criteria:**
- [ ] Exits with code 0
- [ ] Writes artifact to `artifacts/external-project-facts/<repo-name>.json`
- [ ] Artifact contains `fact_sources` array listing which memory files were found
- [ ] `memory_schema_status` is `complete` or `partial` (not absent)

**Note on output shape:** The artifact does not expose top-level `tech_stack` and
`domain` fields. The actual structure is:

```json
{
  "fact_source": { "logical_name": "tech_stack", ... },
  "fact_sources": [...],
  "memory_schema_status": "complete|partial",
  "missing_logical_names": [...]
}
```

**Known limitation:** If repo memory files contain non-UTF-8 bytes, they are read
with replacement characters (not a crash). Check `content_sha256` in the artifact
to verify integrity.

---

## Summary table

| Feature | Result (first run 2026-04-05) | Notes |
|---------|-------------------------------|-------|
| F1 Onboarding | PASS | Requires `--framework-root` in cross-repo environments |
| F2 Drift check | PASS | Exit code is 0/1/2 (not 0/1 as previously documented) |
| F3 Quickstart smoke | PASS (framework default) | External explicit-contract: requires rule pack alignment |
| F4 pre_task | PASS | — |
| F4 post_task | PASS (structural) | `ok=false` without contract block is expected behavior |
| F5 DBL enforcement | PASS | — |
| F6 Rule packs | CONDITIONAL | Requires contract rules to match available packs |
| F7 Readiness | PASS with warnings | Warnings on freshly adopted repo are expected |
| F8 Facts intake | PASS (module invocation) | Use `-m` form; direct script is broken |

---

## Known limitations (as of 2026-04-05 rev2)

- `reviewer_handoff` and `trust_signal` tests (29 failures) are broken due to a
  release readiness link in README not being updated — this does **not** affect
  runtime governance features F1–F8 above.
- Direct script invocation of `external_project_facts_intake.py` is broken
  (`ModuleNotFoundError`). Use `python -m governance_tools.external_project_facts_intake`.
- `quickstart_smoke.py --contract` fails if the contract references rule packs not
  present in `governance/rules/`. The hardcoded `hub-firmware` rule was removed
  (fixed in this revision); contracts must only reference available packs.
- F8 artifact schema does not expose top-level `tech_stack`/`domain` fields;
  use `fact_source.logical_name` and `fact_sources` instead.

---

## F9 — Session closeout and memory update

Tests that the session end hook runs, consumes the closeout artifact, and
produces a verdict artifact. Memory updates only occur if the closeout is valid.

### F9A — Closeout missing (expected degraded state)

```bash
# Ensure no closeout file exists, then run the hook
rm -f artifacts/session-closeout.txt
python -m governance_tools.session_end_hook --project-root <your-repo-path>
```

**Pass criteria:**
- [ ] Exits with code 1 (degraded, not crash)
- [ ] Prints `closeout_status=closeout_missing`
- [ ] Prints hint to write the file
- [ ] Produces a verdict artifact in `artifacts/runtime/verdicts/`

### F9B — Closeout insufficient (vague content)

```bash
cat > <your-repo-path>/artifacts/session-closeout.txt << 'EOF'
TASK_INTENT: work on stuff
WORK_COMPLETED: made improvements
FILES_TOUCHED: NONE
CHECKS_RUN: NONE
OPEN_RISKS: NONE
NOT_DONE: NONE
RECOMMENDED_MEMORY_UPDATE: NO_UPDATE
EOF
python -m governance_tools.session_end_hook --project-root <your-repo-path>
```

**Pass criteria:**
- [ ] Exits with code 1
- [ ] Prints `closeout_status=closeout_insufficient`
- [ ] Memory NOT updated (`promoted=False`)

### F9C — Closeout valid (memory updates)

```bash
cat > <your-repo-path>/artifacts/session-closeout.txt << 'EOF'
TASK_INTENT: test session closeout contract
WORK_COMPLETED: wrote session-closeout.txt per schema and ran session_end_hook
FILES_TOUCHED: artifacts/session-closeout.txt
CHECKS_RUN: python -m governance_tools.session_end_hook --project-root . (exit 0)
OPEN_RISKS: NONE
NOT_DONE: NONE
RECOMMENDED_MEMORY_UPDATE: memory/active_task — closeout contract verified
EOF
python -m governance_tools.session_end_hook --project-root <your-repo-path>
```

**Pass criteria:**
- [ ] Exits with code 0
- [ ] Prints `closeout_status=valid`
- [ ] Prints `snapshot_created=True`
- [ ] Prints `promoted=True`
- [ ] Verdict artifact written to `artifacts/runtime/verdicts/`

### F9D — Stop hook configured (optional)

Configure `.claude/settings.json` per `docs/stop-hook-setup.md`, then end a session.

**Pass criteria:**
- [ ] New file appears in `artifacts/runtime/verdicts/` after session ends
- [ ] Verdict `closeout_status` matches whether closeout file was present

---

## What this checklist does not cover

- GitHub Actions workflow validation (`governance-drift.yml`)
- Multi-harness session lifecycle (claude_code / codex / gemini)
- Onboarding report generation (`external_repo_onboarding_report.py`)

Those are covered in `docs/beta-gate/` for the reference Hearth run.
