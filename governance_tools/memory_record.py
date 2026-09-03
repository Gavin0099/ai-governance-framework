#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from governance_tools.memory_provenance import (
        is_git_worktree,
        is_unbound_commit_token,
        resolve_memory_binding,
    )
except ImportError:
    from memory_provenance import (  # type: ignore[no-redef]
        is_git_worktree,
        is_unbound_commit_token,
        resolve_memory_binding,
    )

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

_NO_VALIDATION_EVIDENCE_PREFIXES = ("NOT RUN:", "NOT CLAIMED:")
MEMORY_WRITE_STATUS_WRITTEN = "written"
MEMORY_WRITE_STATUS_ALREADY_PRESENT = "already_present"

SURFACE_DAILY = "daily"
SURFACE_REVIEW_LOG = "review-log"
SURFACE_ACTIVE_TASK_SUMMARY = "active-task-summary"
SURFACE_CHOICES = (
    SURFACE_DAILY,
    SURFACE_REVIEW_LOG,
    SURFACE_ACTIVE_TASK_SUMMARY,
)

_RECORD_IDENTITY_FIELDS = (
    "record_format_version",
    "memory_type",
    "writer",
    "commit_hash",
    "test_evidence",
    "next_step",
)


@dataclass(frozen=True)
class MemoryWriteOutcome:
    path: Path
    status: str
    record_identity: str
    writer: str


def validate_test_evidence(value: str | None) -> tuple[str, str | None]:
    """Normalize required test evidence without interpreting its truth."""
    if value is None or not value.strip():
        return "", (
            "test_evidence must be non-empty; use 'NOT RUN: <reason>' when no "
            "validation ran or 'NOT CLAIMED: <boundary>' when no validation "
            "claim is being made"
        )

    candidate = value.strip()
    for prefix in _NO_VALIDATION_EVIDENCE_PREFIXES:
        if candidate == prefix[:-1] or (
            candidate.startswith(prefix) and not candidate[len(prefix):].strip()
        ):
            return candidate, f"{prefix[:-1]} evidence must include a reason or boundary"
    return candidate, None


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
    normalized_test_evidence, evidence_error = validate_test_evidence(test_evidence)
    if evidence_error is not None:
        raise ValueError(evidence_error)
    record = {
        "memory_type": MEMORY_TYPE_SESSION_DERIVED,
        "record_format_version": RECORD_FORMAT_VERSION,
        "writer": WRITER_ID,
        "what_changed": what_changed,
        "commit": commit,
        "commit_hash": commit,
        "session_id": session_id,
        "memory_binding": memory_binding,
        "test_evidence": normalized_test_evidence,
        "next_step": next_step,
        "plan_reconciliation": plan_reconciliation,
    }
    record["record_identity"] = build_record_identity(record)
    return record


def build_record_identity(record: dict[str, str]) -> str:
    """Return the stable identity used by canonical same-day deduplication."""
    identity_payload = {
        field: str(record.get(field, ""))
        for field in _RECORD_IDENTITY_FIELDS
    }
    encoded = json.dumps(
        identity_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
        f"  record_identity: {record.get('record_identity') or build_record_identity(record)}\n"
    )


_SINGLE_LINE_BOUNDARIES = (
    "\n",
    "\r",
    "\v",
    "\f",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    "\u2028",
    "\u2029",
)


def _validate_single_line(value: str | None, *, field_name: str) -> str:
    raw_value = value or ""
    if any(boundary in raw_value for boundary in _SINGLE_LINE_BOUNDARIES):
        raise ValueError(f"{field_name} must be exactly one line")
    candidate = raw_value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must be non-empty")
    return candidate


def _validate_projection_field(value: str | None, *, field_name: str) -> str:
    candidate = _validate_single_line(
        value,
        field_name=field_name,
    )
    forbidden_tokens = ("memory_record_projection:", "<!--", "-->")
    for token in forbidden_tokens:
        if token in candidate:
            raise ValueError(
                f"{field_name} contains reserved projection syntax: {token}"
            )
    return candidate


def _validate_active_task_summary(value: str | None) -> str:
    return _validate_projection_field(
        value,
        field_name="active_task_summary",
    )


def render_review_log_projection(record: dict[str, str]) -> str:
    """Render a non-session-shaped review-log projection of a canonical record."""
    identity = record.get("record_identity") or build_record_identity(record)
    return (
        f"<!-- memory_record_projection:{SURFACE_REVIEW_LOG}:{identity} -->\n"
        f"### Canonical memory checkpoint — {record['session_id']}\n\n"
        f"- Writer: `{record['writer']}`\n"
        f"- Record identity: `{identity}`\n"
        f"- Commit binding: `{record['commit_hash']}` ({record['memory_binding']})\n"
        f"- Record: {record['what_changed']}\n"
        f"- Validation boundary: {record['test_evidence']}\n"
        f"- Next action: {record['next_step']}\n"
        f"- PLAN reconciliation: `{record['plan_reconciliation']}`\n"
    )


def render_active_task_projection(record: dict[str, str], *, summary: str) -> str:
    """Render the deliberately one-line active-task projection."""
    normalized_summary = _validate_active_task_summary(summary)
    identity = record.get("record_identity") or build_record_identity(record)
    return (
        f"- {normalized_summary} "
        f"<!-- memory_record_projection:{SURFACE_ACTIVE_TASK_SUMMARY}:{identity} -->\n"
    )


def _projection_marker_line_present(
    *,
    existing: str,
    surface: str,
    identity: str,
) -> bool:
    marker = f"<!-- memory_record_projection:{surface}:{identity} -->"
    for line in existing.splitlines():
        if surface == SURFACE_REVIEW_LOG and line == marker:
            return True
        if (
            surface == SURFACE_ACTIVE_TASK_SUMMARY
            and line.startswith("- ")
            and line.endswith(f" {marker}")
            and line.count("<!--") == 1
            and line.count("-->") == 1
        ):
            return True
    return False


def append_projection_with_outcome(
    *,
    project_root: Path,
    record: dict[str, str],
    surface: str,
    active_task_summary: str | None = None,
) -> MemoryWriteOutcome:
    """Append to one of the two fixed non-daily memory projection surfaces."""
    normalized_test_evidence, evidence_error = validate_test_evidence(record.get("test_evidence"))
    if evidence_error is not None:
        raise ValueError(evidence_error)
    record = dict(record)
    record["test_evidence"] = normalized_test_evidence
    identity = build_record_identity(record)
    record["record_identity"] = identity
    for field_name in (
        "writer",
        "what_changed",
        "commit_hash",
        "session_id",
        "memory_binding",
        "test_evidence",
        "next_step",
        "plan_reconciliation",
    ):
        record[field_name] = _validate_projection_field(
            str(record.get(field_name, "")),
            field_name=field_name,
        )

    if surface == SURFACE_REVIEW_LOG:
        path = project_root / "memory" / "04_review_log.md"
        rendered = render_review_log_projection(record)
    elif surface == SURFACE_ACTIVE_TASK_SUMMARY:
        path = project_root / "memory" / "01_active_task.md"
        rendered = render_active_task_projection(
            record,
            summary=active_task_summary or "",
        )
    else:
        raise ValueError(
            "projection surface must be 'review-log' or 'active-task-summary'"
        )

    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _projection_marker_line_present(
        existing=existing,
        surface=surface,
        identity=identity,
    ):
        return MemoryWriteOutcome(
            path=path,
            status=MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=identity,
            writer=WRITER_ID,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        if existing and not existing.endswith(("\n", "\r")):
            fh.write("\n")
        if existing:
            fh.write("\n")
        fh.write(rendered)
    return MemoryWriteOutcome(
        path=path,
        status=MEMORY_WRITE_STATUS_WRITTEN,
        record_identity=identity,
        writer=WRITER_ID,
    )


def append_session_derived_entry(*, project_root: Path, record: dict[str, str]) -> Path:
    """Backward-compatible Path-returning wrapper around the outcome API."""
    return append_session_derived_entry_with_outcome(
        project_root=project_root,
        record=record,
    ).path


def append_session_derived_entry_with_outcome(
    *,
    project_root: Path,
    record: dict[str, str],
) -> MemoryWriteOutcome:
    normalized_test_evidence, evidence_error = validate_test_evidence(record.get("test_evidence"))
    if evidence_error is not None:
        raise ValueError(evidence_error)
    record = dict(record)
    record["test_evidence"] = normalized_test_evidence
    record_identity = build_record_identity(record)
    record["record_identity"] = record_identity

    memory_root = project_root / "memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    daily_path = memory_root / f"{_current_local_date()}.md"
    if not daily_path.exists():
        daily_path.write_text(f"# {_current_local_date()}\n\n", encoding="utf-8")

    entry = render_session_derived_entry(record)
    if _has_equivalent_session_derived_entry(
        daily_path=daily_path,
        record_identity=record_identity,
    ):
        return MemoryWriteOutcome(
            path=daily_path,
            status=MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=record_identity,
            writer=WRITER_ID,
        )
    with daily_path.open("a", encoding="utf-8") as fh:
        if daily_path.stat().st_size > 0:
            fh.write("\n")
        fh.write(entry)
    return MemoryWriteOutcome(
        path=daily_path,
        status=MEMORY_WRITE_STATUS_WRITTEN,
        record_identity=record_identity,
        writer=WRITER_ID,
    )


def _iter_session_derived_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.startswith("- memory_type:"):
            if current is not None:
                records.append(current)
            current = {"memory_type": line.split(":", 1)[1].strip()}
            continue
        if current is None or not line.startswith("  ") or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        current[key.strip()] = value.strip()
    if current is not None:
        records.append(current)
    return records


def daily_memory_contains_record_identity(
    *,
    daily_path: Path,
    record_identity: str,
) -> bool:
    try:
        text = daily_path.read_text(encoding="utf-8")
    except Exception:
        return False
    return any(
        build_record_identity(record) == record_identity
        for record in _iter_session_derived_records(text)
        if record.get("memory_type") == MEMORY_TYPE_SESSION_DERIVED
    )


def _has_equivalent_session_derived_entry(
    *,
    daily_path: Path,
    record_identity: str,
) -> bool:
    """
    Deduplicate same-day session-derived noise.

    Equivalence is intentionally strict on commit/test/next_step identity, while
    allowing session_id differences for repeated auto-closeout retries.
    """
    return daily_memory_contains_record_identity(
        daily_path=daily_path,
        record_identity=record_identity,
    )


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
    test_evidence: str,
    next_step: str = "[fill in]",
    project_root: str = ".",
) -> str:
    """Return a ready-to-paste CLI command that writes a canonical memory entry."""
    normalized_test_evidence, evidence_error = validate_test_evidence(test_evidence)
    if evidence_error is not None:
        raise ValueError(evidence_error)
    return (
        f"python governance_tools/memory_record.py"
        f' --what-changed "{what_changed}"'
        f" --commit {commit}"
        f" --session-id {session_id}"
        f' --test-evidence "{normalized_test_evidence}"'
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
    parser.add_argument(
        "--test-evidence",
        required=True,
        help=(
            "Non-empty validation evidence. When no validation ran, use "
            "'NOT RUN: <reason>' or 'NOT CLAIMED: <boundary>'."
        ),
    )
    parser.add_argument("--project-root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--surface",
        action="append",
        choices=SURFACE_CHOICES,
        help=(
            "Fixed memory surface to write. Repeat for multiple surfaces. "
            "Defaults to daily; arbitrary paths are not accepted."
        ),
    )
    parser.add_argument(
        "--active-task-summary",
        default=None,
        help=(
            "Required one-line summary when --surface active-task-summary is used."
        ),
    )
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

    surfaces = list(dict.fromkeys(args.surface or [SURFACE_DAILY]))
    if SURFACE_ACTIVE_TASK_SUMMARY in surfaces:
        try:
            _validate_active_task_summary(args.active_task_summary)
        except ValueError as exc:
            print(f"[memory_record] error: {exc}")
            return 2
    elif args.active_task_summary is not None:
        print(
            "[memory_record] error: --active-task-summary requires "
            "--surface active-task-summary"
        )
        return 2

    plan_reconciliation, plan_error = validate_plan_reconciliation(args.plan_reconciliation)
    if plan_error is not None:
        print(f"[memory_record] error: {plan_error}")
        return 2
    test_evidence, evidence_error = validate_test_evidence(args.test_evidence)
    if evidence_error is not None:
        print(f"[memory_record] error: {evidence_error}")
        return 2
    project_root = Path(args.project_root).resolve()
    explicit_commit = args.commit is not None
    commit = args.commit or _auto_detect_commit(project_root)
    session_id = args.session_id or f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    memory_binding = resolve_memory_binding(
        project_root,
        commit,
        session_id,
        allow_session_fallback=False,
    )
    if (
        explicit_commit
        and is_git_worktree(project_root)
        and not is_unbound_commit_token(commit)
        and memory_binding != "bound"
    ):
        print(
            "[memory_record] error: explicit --commit does not resolve to a "
            f"local Git commit object: {commit}"
        )
        return 2

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
        evidence_provenance_advisory(test_evidence, project_root)
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
        test_evidence=test_evidence,
        next_step=args.next_step,
        plan_reconciliation=plan_reconciliation,
    )
    outcomes: list[MemoryWriteOutcome] = []
    for surface in surfaces:
        if surface == SURFACE_DAILY:
            outcomes.append(
                append_session_derived_entry_with_outcome(
                    project_root=project_root,
                    record=record,
                )
            )
        else:
            outcomes.append(
                append_projection_with_outcome(
                    project_root=project_root,
                    record=record,
                    surface=surface,
                    active_task_summary=args.active_task_summary,
                )
            )
    for outcome in outcomes:
        status_label = (
            "Written"
            if outcome.status == MEMORY_WRITE_STATUS_WRITTEN
            else "Already present"
        )
        print(
            f"[memory_record] {status_label}: {outcome.path} "
            f"(surface identity={outcome.record_identity})"
        )
    print(render_session_derived_entry(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
