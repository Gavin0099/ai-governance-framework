# Governance artifact write-boundary — root-cause design

Status:

```text
design-only
no implementation
canonical-root contract: RATIFIED (owner, 2026-06-23) = explicit project root + fail-closed
hygiene .gitignore defense applied separately (not the fix)
no change to runtime writer behavior in this document
```

## Problem

A full governance runtime `artifacts/` tree was found inside a sub-directory of
the repo:

```text
docs/governance/hermes_no_agent_checklist/artifacts/
```

It is generated runtime output, not hand-authored evidence. Observed contents
(preserved in place, NOT moved/deleted — see "Preserved evidence" below):

- `artifacts/runtime/closeout-receipts/closeout_receipt_20260623T102316607125Z.json`
- `artifacts/runtime/canonical-audit-log.jsonl`, `runtime/closeouts/`, `runtime/candidates/`, `runtime/curated/`, `runtime/advisory/`
- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson`
- `artifacts/governance/runtime_phase_summary.json`
- `artifacts/session/`, `artifacts/session-index.ndjson`
- `artifacts/codeburn_closeout_ingest.db` (~272 KB)

Timestamps cluster at 2026-06-23T10:23Z (≈18:23 local).

## Root cause

The governance closeout/session writers anchor artifacts to `project_root`:

```text
project_root / "artifacts" / "runtime" / "closeout-receipts" / ...   (manage_agent_closeout.py:833)
project_root / "artifacts" / ...                                     (multiple writers)
```

and `project_root` defaults to the current working directory:

```text
manage_agent_closeout.py:979   --project-root default="."  -> Path(".").resolve()
session_end_hook.py:2245        --project-root default="."
session_closeout_entry.py:338   --project-root default="."
```

So a session-end / closeout that runs while the shell's cwd is inside a
sub-directory writes the whole canonical artifact tree **into that
sub-directory**. This is evidence-substrate drift: the *location of canonical
governance evidence depends on where the process happened to be invoked*.

Why `.gitignore` did not catch it: the existing `artifacts/...` patterns contain
an internal slash and are therefore **anchored to the repo root**; they do not
match a nested `docs/.../artifacts/...`, so the stray tree showed as untracked
and was one `git add` away from being committed.

## Two fix candidates

| Candidate | What it changes | Role | Risk |
|---|---|---|---|
| **A. Tool self-resolves the canonical root** | writers resolve the root deterministically (e.g. git toplevel / framework marker) instead of `Path(".")` | long-term correctness | framework-wide; touches where canonical evidence is written |
| **B. Hook/CLI wiring passes `--project-root` explicitly** | every invocation (session_end hook command, CLI callers) is required to pass the consuming-repo root | short-term containment | lower; configuration/wiring change |

Sequencing: **B is containment** (make today's callers correct), **A is the
real correction** (a canonical-evidence writer must never silently fall back to
cwd). `default="."` for an evidence writer is the defect itself, because it
binds canonical artifact location to invocation cwd.

## The question this design must answer [OP-HC]

> Is the canonical root for governance artifacts **"the repo root"** or **"an
> explicit project root"**?

The answer fixes the rule:

- **If the canonical root is the repo root** → `Path(".").resolve()` as a silent
  default is forbidden. The writer must resolve the repo root deterministically
  (and if it cannot, it must fail-closed — see below), never write to cwd.
- **If the canonical root is an explicit project root** → the hook/CLI must
  **fail-closed**: with no `--project-root` supplied, the writer must *refuse to
  write canonical artifacts*, not silently write to cwd.

## Decision (owner-ratified, 2026-06-23) [OP-HC]

> **Canonical artifact root is an explicit contract, not an ambient
> cwd-derived property.**

The canonical root is an **explicit project root + fail-closed**:

- CLI / hook callers **must** supply `--project-root` (the consuming-repo /
  framework root they intend).
- The writer **normalizes and validates** the supplied root.
- If no root is supplied, the writer **refuses to write canonical artifacts** —
  it does not guess, and it **never falls back to cwd**.
- A git-toplevel / framework-marker check is allowed **only as auxiliary
  validation** of the supplied root, never as the deciding/deriving mechanism.

Rejected: `git rev-parse --show-toplevel` as the *sole* root. It carries hidden
governance risks — in nested repo / submodule / worktree it can resolve a root
that is *technically correct but governance-wrong*; when governance tools run
inside a consuming repo it may write to the consuming repo rather than the
framework-intended root; and it turns "who decides the artifact trust root" into
an environment-derived property instead of a call contract.

Consequence for implementation: `--project-root default="."` (and any silent
`Path(".").resolve()`) is **removed** from
`manage_agent_closeout.py` / `session_end_hook.py` / `session_closeout_entry.py`;
the missing-root path becomes a fail-closed refusal.

Classification: this changes where canonical evidence is written → it touches the
evidence substrate / trust root → **[OP-HC]** (high-cost; needs rollback path,
multi-repo adoption consideration, reviewer agreement). The hook-wiring
containment (B) is ordinary **[OP]** and is the short-term step toward the
fail-closed end state.

## Hygiene defense already applied (NOT the fix)

`.gitignore` gained any-depth patterns (`**/artifacts/runtime/`,
`**/artifacts/claim-enforcement/`, `**/artifacts/*.db`, …) so a stray nested
`artifacts/` cannot be committed. This is hygiene only; it does not stop the
writer from polluting, and it is explicitly labelled as such in `.gitignore`.

## Preserved evidence (do not touch until the fix lands)

The misplaced tree at `docs/governance/hermes_no_agent_checklist/artifacts/` is
**left in place on purpose**: moving or deleting it would itself mutate evidence
state and destroy the original site for root-cause confirmation. It is now
gitignored (won't be committed) and recorded here (path, ≈18:23 local /
2026-06-23T10:23Z, content types above). Decision on quarantine vs cleanup is
deferred until the root resolution is fixed.

## Claim ceiling

```text
This design names the defect and the decision. It does NOT change any writer's
project_root resolution, does NOT move/delete the preserved artifacts, and the
.gitignore defense does NOT fix the root cause.
```

## Evidence plan for the eventual fix

1. Ratify the canonical-root answer (repo-root-with-fail-closed vs explicit-with-fail-closed).
2. Implement so that no writer can resolve `project_root` to cwd silently; assert a fail-closed path.
3. Reproduce the original trigger (run a closeout from a sub-directory) and prove no artifacts land in cwd.
4. Confirm existing consumers/hook wiring still write to the correct repo-root artifacts/.
5. Then decide quarantine vs cleanup for the preserved misplaced tree.

## Non-goals

- no writer behavior change in this cut;
- no move/delete of the preserved artifacts;
- no claim that the `.gitignore` defense fixes the root cause;
- no change to session_end hook scheduling or to the Hermes checklist line.
