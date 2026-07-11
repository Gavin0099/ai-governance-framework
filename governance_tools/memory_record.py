#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

_REAL_HASH = re.compile(r'^[a-f0-9]{5,40}$', re.IGNORECASE)

WRITER_ID = "governance_tools.memory_record"
RECORD_FORMAT_VERSION = "1.0"
MEMORY_TYPE_SESSION_DERIVED = "session-derived"

# Structured PLAN Reconciliation Declaration (P1-D).
# The gate target is silent drift, not deferred drift: a record may defer
# PLAN reconciliation with a named reason, but may not stay silent about it.
# Historical parsing may still represent a missing declaration as
# ``not_declared``. The canonical writer CLI, however, requires an explicit
# declaration so new session-derived records cannot silently omit it.
PLAN_RECONCILIATION_UPDATED = "updated"
PLAN_RECONCILIATION_NOT_APPLICABLE = "not_applicable"
PLAN_RECONCILIATION_NOT_DECLARED = "not_declared"
PLAN_RECONCILIATION_DEFERRED_PREFIX = "deferred:"

# Extend via PR only; reasons must stay reviewable categories, not prose.
DEFERRED_REASON_TAXONOMY = frozenset({
    "requires-human-plan-review",
    "awaiting-reviewer-verdict",
    "scope-split-next-slice",
    "canonical-update-not-authorized",
    "dirty-workspace-prevents-safe-edit",
})

VACUOUS_DEFERRED_REASONS = frozenset({"later", "todo", "pending", "soon", "tbd"})


def validate_plan_reconciliation(value: str | None) -> tuple[str, str | None]:
    """
    Normalize and validate a plan_reconciliation declaration.

    Returns (normalized_value, error). error is None when the value is
    acceptable. An omitted/empty value normalizes to "not_declared" and is
    acceptable (advisory-level, caller may warn); malformed values return
    an error message and must not be written.
    """
    if value is None or not value.strip():
        return PLAN_RECONCILIATION_NOT_DECLARED, None
    candidate = value.strip()
    if candidate in (PLAN_RECONCILIATION_UPDATED, PLAN_RECONCILIATION_NOT_APPLICABLE):
        return candidate, None
    if candidate.startswith(PLAN_RECONCILIATION_DEFERRED_PREFIX):
        reason = candidate[len(PLAN_RECONCILIATION_DEFERRED_PREFIX):].strip()
        if not reason:
            return candidate, "deferred reason must be non-empty"
        if reason.lower() in VACUOUS_DEFERRED_REASONS:
            return candidate, (
                f"deferred reason '{reason}' is vacuous; use a taxonomy reason: "
                + ", ".join(sorted(DEFERRED_REASON_TAXONOMY))
            )
        if reason not in DEFERRED_REASON_TAXONOMY:
            return candidate, (
                f"deferred reason '{reason}' is not in the reason taxonomy: "
                + ", ".join(sorted(DEFERRED_REASON_TAXONOMY))
                + " (extend the taxonomy via PR if a new category is genuinely needed)"
            )
        return f"{PLAN_RECONCILIATION_DEFERRED_PREFIX}{reason}", None
    return candidate, (
        "plan_reconciliation must be 'updated', 'not_applicable', or "
        "'deferred:<taxonomy-reason>'"
    )


def _current_local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def build_session_derived_record(
    *,
    what_changed: str,
    commit: str,
    session_id: str,
    memory_binding: str,
    test_evidence: str,
    next_step: str,
    plan_reconciliation: str = PLAN_RECONCILIATION_NOT_DECLARED,
) -> dict[str, str]:
    return {
        "memory_type": MEMORY_TYPE_SESSION_DERIVED,
        "record_format_version": RECORD_FORMAT_VERSION,
        "writer": WRITER_ID,
        "what_changed": what_changed,
        "commit": commit,
        "commit_hash": commit,
        "session_id": session_id,
        "memory_binding": memory_binding,
        "test_evidence": test_evidence,
        "next_step": next_step,
        "plan_reconciliation": plan_reconciliation,
    }


def render_session_derived_entry(record: dict[str, str]) -> str:
    return (
        f"- memory_type: {record['memory_type']}\n"
        f"  record_format_version: {record['record_format_version']}\n"
        f"  writer: {record['writer']}\n"
        f"  what_changed: {record['what_changed']}\n"
        f"  commit: {record['commit']}\n"
        f"  commit_hash: {record['commit_hash']}\n"
        f"  session_id: {record['session_id']}\n"
        f"  memory_binding: {record['memory_binding']}\n"
        f"  test_evidence: {record['test_evidence']}\n"
        f"  next_step: {record['next_step']}\n"
        f"  plan_reconciliation: {record.get('plan_reconciliation', PLAN_RECONCILIATION_NOT_DECLARED)}\n"
    )


def append_session_derived_entry(*, project_root: Path, record: dict[str, str]) -> Path:
    memory_root = project_root / "memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    daily_path = memory_root / f"{_current_local_date()}.md"
    if not daily_path.exists():
        daily_path.write_text(f"# {_current_local_date()}\n\n", encoding="utf-8")

    entry = render_session_derived_entry(record)
    if _has_equivalent_session_derived_entry(daily_path=daily_path, record=record):
        return daily_path
    with daily_path.open("a", encoding="utf-8") as fh:
        if daily_path.stat().st_size > 0:
            fh.write("\n")
        fh.write(entry)
    return daily_path


def _has_equivalent_session_derived_entry(*, daily_path: Path, record: dict[str, str]) -> bool:
    """
    Deduplicate same-day session-derived noise.

    Equivalence is intentionally strict on commit/test/next_step identity, while
    allowing session_id differences for repeated auto-closeout retries.
    """
    try:
        text = daily_path.read_text(encoding="utf-8")
    except Exception:
        return False

    required_lines = (
        f"- memory_type: {record.get('memory_type', '')}",
        f"  writer: {record.get('writer', '')}",
        f"  commit_hash: {record.get('commit_hash', '')}",
        f"  test_evidence: {record.get('test_evidence', '')}",
        f"  next_step: {record.get('next_step', '')}",
    )
    return all(line in text for line in required_lines)


def _auto_detect_commit(project_root: Path) -> str:
    """Best-effort: read the latest git commit hash. Returns 'UNCOMMITTED' on failure."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h"],
            capture_output=True, text=True, cwd=project_root, timeout=5,
        )
        h = result.stdout.strip()
        return h if h else "UNCOMMITTED"
    except Exception:
        return "UNCOMMITTED"


def build_memory_record_suggestion(
    *,
    what_changed: str,
    commit: str,
    session_id: str,
    plan_reconciliation: str,
    next_step: str = "[fill in]",
    project_root: str = ".",
) -> str:
    """Return a ready-to-paste CLI command that writes a canonical memory entry."""
    return (
        f"python governance_tools/memory_record.py"
        f' --what-changed "{what_changed}"'
        f" --commit {commit}"
        f" --session-id {session_id}"
        f' --plan-reconciliation "{plan_reconciliation}"'
        f' --next-step "{next_step}"'
        f" --project-root {project_root}"
    )


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Append a canonical session-derived memory entry to memory/YYYY-MM-DD.md."
    )
    parser.add_argument("--what-changed", required=True, help="Summary of what changed this session")
    parser.add_argument("--next-step", required=True, help="What to do next")
    parser.add_argument("--commit", default=None, help="Git commit hash (auto-detected if omitted)")
    parser.add_argument("--session-id", default=None, help="Session ID (timestamp-based if omitted)")
    parser.add_argument("--test-evidence", default="", help="Test run evidence")
    parser.add_argument("--project-root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--plan-reconciliation",
        required=True,
        help=(
            "PLAN reconciliation declaration: updated | not_applicable | "
            "deferred:<taxonomy-reason>. This is required for canonical "
            "session-derived memory writes."
        ),
    )
    args = parser.parse_args()

    plan_reconciliation, plan_error = validate_plan_reconciliation(args.plan_reconciliation)
    if plan_error is not None:
        print(f"[memory_record] error: {plan_error}")
        return 2
    project_root = Path(args.project_root).resolve()
    commit = args.commit or _auto_detect_commit(project_root)
    session_id = args.session_id or f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    memory_binding = "bound" if _REAL_HASH.match(commit) else "unbound"

    # Write-time provenance advisory (report-only, never blocks): a success
    # claim without an existing artifacts/ path becomes a new above-baseline
    # test_evidence_provenance_not_found warning at the next closeout, so
    # surface it while the author can still attach a receipt. Fallback import
    # covers file-path invocation, where sys.path[0] is governance_tools/.
    try:
        from governance_tools.memory_authority_guard import evidence_provenance_advisory
    except ImportError:
        try:
            from memory_authority_guard import evidence_provenance_advisory  # type: ignore[no-redef]
        except ImportError as exc:
            evidence_provenance_advisory = None
            print(f"[memory_record] provenance advisory unavailable: {exc}")
    provenance_advisory = (
        evidence_provenance_advisory(args.test_evidence, project_root)
        if evidence_provenance_advisory is not None
        else None
    )
    if provenance_advisory is not None:
        print(
            "[memory_record] advisory: test_evidence claims success without an "
            "existing artifacts/ path; the memory authority guard will flag this "
            "entry as test_evidence_provenance_not_found. Wrap the validation "
            "command in governance_tools.test_evidence_receipt_writer and cite "
            "the receipt path inside --test-evidence."
        )

    record = build_session_derived_record(
        what_changed=args.what_changed,
        commit=commit,
        session_id=session_id,
        memory_binding=memory_binding,
        test_evidence=args.test_evidence,
        next_step=args.next_step,
        plan_reconciliation=plan_reconciliation,
    )
    path = append_session_derived_entry(project_root=project_root, record=record)
    print(f"[memory_record] Written: {path}")
    print(render_session_derived_entry(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
