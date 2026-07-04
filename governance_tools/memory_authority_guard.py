#!/usr/bin/env python3
"""
Memory Authority Guard — Phase 1 (warning mode, non-blocking)

Checks that memory entries are properly bound to traceable sources.

Two memory types:
  - session-derived (daily files: memory/YYYY-MM-DD.md)
      Binding requirement: commit_hash (resolves to a git commit when a git
      worktree is available) OR session_id with runtime artifact provenance
  - structural long-term (memory/00_long_term.md)
      Binding requirement: promoted_by marker in each ## section

Checks:
  1. unbound_memory              — daily entry lacks commit_hash + session_id
  2. structural_memory_auto_write — 00_long_term.md section lacks promoted_by
  3. private_memory_cited        — closeout artifact cites .claude private memory path
  4. missing_canonical_memory   — commits in git log but no daily memory file
  5. test_evidence_provenance_not_found — success evidence lacks artifact provenance
  6. session_like_non_session_memory_type — session-shaped entry uses a non-session memory_type
     (active-window daily files always; pre-window daily files only when diff
     context marks them as modified, to catch backdated appends without
     reclassifying untouched historical entries)
  7. non_daily_session_shaped_memory_entry — non-daily memory/*.md contains a
     session-shaped entry block (report-only placement warning)

Phase 1 default: warnings only. Exit code always 0. JSON to stdout.
Selective blocking: run_guard accepts an opt-in blocking_codes policy input; the
default (empty) keeps exact Phase 1 semantics and is the kill switch. Gate
consumers load the versioned policy file; non-blockable warning codes stay
report-only.

See: governance/MEMORY_AUTHORITY_CONTRACT.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── regex patterns ────────────────────────────────────────────────────────────

# Match both human-written ("commit hash:") and auto-generated ("commit:") entry formats.
# A commit anchor is 5-40 hex chars; when a git worktree is available, it must
# resolve to a commit object before it counts as bound.
_ENTRY_SPLIT = re.compile(r'(?m)^(?=- (?:memory_type|what[_ ]changed):)')
_COMMIT_RESOLVED = re.compile(
    r'commit(?:\s+hash)?:\s*`?([a-f0-9]{5,40})`?', re.IGNORECASE
)
_COMMIT_PENDING = re.compile(
    r'commit(?:\s+hash)?:\s*pending', re.IGNORECASE
)
_COMMIT_UNCOMMITTED = re.compile(
    r'commit(?:\s+hash)?:\s*UNCOMMITTED', re.IGNORECASE
)
_SESSION_ID = re.compile(r'session[_\s]id:\s*(\S+)', re.IGNORECASE)
_MEMORY_TYPE = re.compile(r'memory_type:\s*(\S+)', re.IGNORECASE)
_WRITER = re.compile(r'writer:\s*(\S+)', re.IGNORECASE)
_RECORD_FORMAT_VERSION = re.compile(r'record_format_version:\s*(\S+)', re.IGNORECASE)
_TEST_EVIDENCE = re.compile(r'(?m)^\s*test_evidence:\s*(.+)$', re.IGNORECASE)
_TEST_EVIDENCE_SUCCESS = re.compile(
    r'\b(?:PASS|passed|success(?:ful|fully)?)\b', re.IGNORECASE
)
_TEST_EVIDENCE_ARTIFACT_PATH = re.compile(
    r'(?P<path>(?:\.?[\\/])?artifacts[\\/][^\s,;]+)', re.IGNORECASE
)
_MEMORY_BINDING = re.compile(r'(?m)^\s*memory_binding:\s*\S+', re.IGNORECASE)
_AUTHORITY_OVERRIDE = re.compile(r'(?m)^\s*authority_override:\s*(.+)$', re.IGNORECASE)
_NEXT_STEP = re.compile(r'(?m)^\s*next_step:\s*.+$', re.IGNORECASE)
_PLAN_RECONCILIATION = re.compile(r'(?m)^\s*plan_reconciliation:\s*\S+', re.IGNORECASE)
_PROMOTED_BY = re.compile(r'promoted_by:', re.IGNORECASE)
_PROMOTION_STATUS = re.compile(r'<!--\s*promotion_status:\s*(\w+)', re.IGNORECASE)
_SECTION_H2 = re.compile(r'^## ', re.MULTILINE)
_PRIVATE_MEMORY_PATH = re.compile(
    r'[Cc]:\\[Uu]sers\\[^\\]+\\.claude\\projects', re.IGNORECASE
)
_CANONICAL_MEMORY_WRITER = "governance_tools.memory_record"

# Daily files dated on or after this date are required to use canonical writer format.
# Before this date, old-format entries (- what changed:) are grandfathered.
# Set to the day after canonical writer was committed (2026-04-30 commit 6d77f2d).
_CANONICAL_WRITER_REQUIRED_FROM = "2026-05-01"
_ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM = "2026-06-02"
_SESSION_DERIVED_MEMORY_TYPES = {"session-derived", "session_derived"}
_NON_DAILY_SESSION_SHAPED_CODE = "non_daily_session_shaped_memory_entry"
_PRE_WINDOW_REASON_PREFIX = (
    "non_session_memory_type_with_session_fields_in_modified_pre_window_file:"
)
_SESSION_LIKE_FIELD_PATTERNS = (
    ("record_format_version", _RECORD_FORMAT_VERSION),
    ("writer", _WRITER),
    ("commit", _COMMIT_RESOLVED),
    ("commit_pending", _COMMIT_PENDING),
    ("commit_uncommitted", _COMMIT_UNCOMMITTED),
    ("session_id", _SESSION_ID),
    ("memory_binding", _MEMORY_BINDING),
    ("test_evidence", _TEST_EVIDENCE),
    ("next_step", _NEXT_STEP),
    ("plan_reconciliation", _PLAN_RECONCILIATION),
)
# Violation category policy (as classified 2026-06-01):
#   Cat1 (pre-2026-05-13, 32 entries): early Codex writer path — grandfathered, no action
#   Cat2+3 (2026-05-18 to 05-30, 46 entries): old-format established pattern — historical debt, no backfill
#   Cat4 (>= 2026-06-01): active violations — AGENTS.md prohibits direct write; use canonical CLI

# ── helpers ───────────────────────────────────────────────────────────────────

_DATE_FILENAME = re.compile(r'^\d{4}-\d{2}-\d{2}\.md$')


def _is_daily_file(path: Path) -> bool:
    return _DATE_FILENAME.match(path.name) is not None


def _project_has_git_worktree(project_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _git_commit_exists(project_root: Path, commit_hash: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "cat-file", "-e", f"{commit_hash}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _json_session_id_matches(path: Path, session_id: str) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return str(payload.get("session_id") or "").strip() == session_id


def _session_id_has_artifact_provenance(project_root: Path, session_id: str) -> bool:
    if not session_id or "/" in session_id or "\\" in session_id or session_id in {".", ".."}:
        return False

    runtime_root = project_root / "artifacts" / "runtime"
    closeout_path = runtime_root / "closeouts" / f"{session_id}.json"
    if closeout_path.is_file() and _json_session_id_matches(closeout_path, session_id):
        return True

    verdict_path = runtime_root / "verdicts" / f"{session_id}.json"
    if verdict_path.is_file() and _json_session_id_matches(verdict_path, session_id):
        return True

    claim_paths = (
        project_root / "artifacts" / "session" / "claim-enforcement" / session_id / "claim-enforcement-check.json",
        project_root / "artifacts" / "claim-enforcement" / session_id / "claim-enforcement-check.json",
    )
    return any(path.is_file() for path in claim_paths)


def _entry_is_bound(block: str, project_root: Path | None = None) -> tuple[bool, str]:
    """
    Returns (is_bound, reason).

    Binding rules (Memory Authority Contract v1.0.0):
      - Real commit hash (git commit object, when git is available) → bound
      - session_id with runtime artifact provenance      → bound (valid fallback)
      - commit hash: pending, no session_id             → unbound (VIOLATION)
      - commit: UNCOMMITTED, no session_id              → unbound (VIOLATION)
      - no hash field, no session_id                    → unbound (VIOLATION)
    """
    commit_matches = _COMMIT_RESOLVED.findall(block)
    session_ids = [match.strip().strip("`") for match in _SESSION_ID.findall(block)]
    has_pending = bool(_COMMIT_PENDING.search(block))
    has_uncommitted = bool(_COMMIT_UNCOMMITTED.search(block))

    # Real hash takes precedence
    if commit_matches and (
        project_root is None
        or not _project_has_git_worktree(project_root)
        or any(_git_commit_exists(project_root, commit_hash) for commit_hash in commit_matches)
    ):
        return True, "ok"
    # session_id is a valid fallback only when an existing runtime artifact
    # anchors that session_id; an arbitrary non-empty token is not provenance.
    if project_root is not None and any(
        _session_id_has_artifact_provenance(project_root, session_id)
        for session_id in session_ids
    ):
        return True, "ok"
    if session_ids:
        if commit_matches:
            return False, "commit_hash_not_found_session_id_provenance_not_found"
        return False, "session_id_provenance_not_found"
    if commit_matches:
        return False, "commit_hash_not_found_no_session_id"
    # Distinguish why there's no binding
    if has_pending:
        return False, "commit_hash_pending_no_session_id"
    if has_uncommitted:
        return False, "commit_uncommitted_no_session_id"
    return False, "no_anchor"


def _snippet(block: str, length: int = 80) -> str:
    first_line = block.strip().split('\n')[0]
    return first_line[:length]


def _normalize_artifact_token(token: str) -> str:
    return token.strip().strip('`"\'()[]{}<>').rstrip(".:")


def _artifact_path_exists(project_root: Path, token: str) -> bool:
    normalized = _normalize_artifact_token(token)
    if not normalized:
        return False

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = project_root / candidate

    try:
        resolved_project_root = project_root.resolve()
        resolved_candidate = candidate.resolve()
    except OSError:
        return False

    try:
        resolved_candidate.relative_to(resolved_project_root)
    except ValueError:
        return False

    return resolved_candidate.is_file()


def _test_evidence_provenance_violation(
    block: str,
    project_root: Path | None,
) -> str | None:
    if project_root is None:
        return None

    match = _TEST_EVIDENCE.search(block)
    if not match:
        return None

    evidence = match.group(1).strip()
    if not _TEST_EVIDENCE_SUCCESS.search(evidence):
        return None

    artifact_tokens = [
        artifact_match.group("path")
        for artifact_match in _TEST_EVIDENCE_ARTIFACT_PATH.finditer(evidence)
    ]
    if not artifact_tokens:
        return "test_evidence_success_claim_without_artifact"

    if any(_artifact_path_exists(project_root, token) for token in artifact_tokens):
        return None

    return "test_evidence_artifact_not_found"


_BLOCKING_POLICY_RELPATH = "governance/memory_blocking_policy.json"
_BLOCKING_POLICY_SCHEMA = "memory_blocking_policy.v0.1"
# Codes a policy may enable. authority_override_used is deliberately absent:
# it is an audit record, never blockable.
_BLOCKABLE_VIOLATION_CODES = frozenset({
    "unbound_memory",
    "non_canonical_writer",
    "structural_memory_auto_write",
    "private_memory_cited",
    "missing_canonical_memory",
    "test_evidence_provenance_not_found",
    "session_like_non_session_memory_type",
})


def load_blocking_policy(project_root: Path) -> dict[str, Any]:
    """
    Load the versioned selective-blocking policy file (RFC rollout step 4).

    Returns {'enabled_codes': [...], 'source': str, 'error': str | None}.
    Missing file or `enabled: false` is the kill switch: blocking stays off
    with no error. A present-but-invalid policy also disables blocking but
    surfaces an error string so a broken policy can never silently pass as an
    intentionally disabled one. No environment variable can influence this.
    """
    path = project_root / _BLOCKING_POLICY_RELPATH
    off = {'enabled_codes': [], 'source': _BLOCKING_POLICY_RELPATH, 'error': None}
    if not path.is_file():
        return {**off, 'source': 'default_off_no_policy_file'}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {**off, 'error': f'blocking_policy_unreadable: {exc}'}
    if not isinstance(payload, dict):
        return {**off, 'error': 'blocking_policy_not_an_object'}
    if payload.get('policy_schema') != _BLOCKING_POLICY_SCHEMA:
        return {**off, 'error': 'blocking_policy_schema_mismatch'}
    if payload.get('enabled') is not True:
        return off
    codes = payload.get('blocking_codes')
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        return {**off, 'error': 'blocking_policy_codes_invalid'}
    cleaned = sorted({c.strip() for c in codes if c.strip()})
    unknown = [c for c in cleaned if c not in _BLOCKABLE_VIOLATION_CODES]
    if unknown:
        # A typo'd code would otherwise enable selective-blocking claims while
        # blocking nothing (claim inflation) — fail visibly instead.
        return {**off, 'error': f"blocking_policy_unknown_code:{','.join(unknown)}"}
    return {
        'enabled_codes': cleaned,
        'source': _BLOCKING_POLICY_RELPATH,
        'error': None,
    }


def _authority_override_value(block: str) -> str | None:
    match = _AUTHORITY_OVERRIDE.search(block)
    return match.group(1).strip() if match else None


def _session_like_field_names(block: str) -> list[str]:
    return [
        name
        for name, pattern in _SESSION_LIKE_FIELD_PATTERNS
        if pattern.search(block)
    ]


def _session_like_non_session_memory_reason(
    block: str,
    *,
    memory_type: str,
    filename: str,
    active_from: str = _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
) -> str | None:
    if (
        not memory_type
        or memory_type in _SESSION_DERIVED_MEMORY_TYPES
        or filename < f"{active_from}.md"
    ):
        return None

    matched_fields = _session_like_field_names(block)
    if not matched_fields:
        return None

    field_list = ",".join(matched_fields)
    return f"non_session_memory_type_with_session_fields:{memory_type}:{field_list}"


# ── check functions ───────────────────────────────────────────────────────────

def check_modified_pre_window_daily_files(
    memory_root: Path,
    changed_files: Sequence[str],
    *,
    active_from: str = _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
) -> list[dict[str, Any]]:
    """
    Check 6 extension: session-shaped non-session entries in *modified*
    pre-window daily files.

    The regular daily scan classifies the active window by filename date, so a
    session-shaped entry backdated into a pre-window file evades it. When the
    caller provides diff context (pre-commit / CI changed files), a pre-window
    daily file being modified now is itself the recency signal: scan it with
    the same field-shape logic and report matches under the same violation
    code with a pre-window reason.

    Untouched historical files are never scanned here, so existing pre-window
    debt stays silent. In-window files are skipped to avoid double-reporting
    entries the regular scan already covers.
    """
    cutoff = f"{active_from}.md"
    violations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in changed_files:
        normalized = str(raw).strip().replace("\\", "/").lstrip("./")
        name = normalized.rsplit("/", 1)[-1]
        if normalized != f"memory/{name}":
            continue
        if not _DATE_FILENAME.match(name) or name >= cutoff or name in seen:
            continue
        seen.add(name)
        fpath = memory_root / name
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(encoding='utf-8')
        except Exception:
            # Unreadable files are already reported by the regular daily scan.
            continue
        for block in _ENTRY_SPLIT.split(text):
            stripped = block.strip()
            if not (
                stripped.startswith('- what changed:')
                or stripped.startswith('- what_changed:')
                or stripped.startswith('- memory_type:')
            ):
                continue
            memory_type_match = _MEMORY_TYPE.search(block)
            memory_type = (
                memory_type_match.group(1).strip().lower() if memory_type_match else ""
            )
            if not memory_type or memory_type in _SESSION_DERIVED_MEMORY_TYPES:
                continue
            matched_fields = _session_like_field_names(block)
            if not matched_fields:
                continue
            violations.append({
                'code': 'session_like_non_session_memory_type',
                'severity': 'warning',
                'file': name,
                'entry': _snippet(block),
                'reason': (
                    f'{_PRE_WINDOW_REASON_PREFIX}'
                    f'{memory_type}:{",".join(matched_fields)}'
                ),
                'authority_override': _authority_override_value(block),
            })
    return violations


def check_non_daily_session_shaped_memory_files(
    memory_root: Path,
    changed_files: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """
    F6 report-only detector: session-shaped entry blocks in non-daily memory
    files.

    Non-daily memory files are valid structural surfaces, so this intentionally
    ignores prose and comment metadata. A warning requires a Markdown list block
    that looks like an entry and carries at least two session-shaped fields.
    """
    violations: list[dict[str, Any]] = []
    if changed_files is None:
        candidates = sorted(memory_root.glob("*.md"))
    else:
        candidates = []
        seen: set[str] = set()
        for raw in changed_files:
            normalized = str(raw).strip().replace("\\", "/").lstrip("./")
            name = normalized.rsplit("/", 1)[-1]
            if normalized != f"memory/{name}" or name in seen:
                continue
            seen.add(name)
            candidates.append(memory_root / name)
        candidates.sort()

    for fpath in candidates:
        if _is_daily_file(fpath):
            continue
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception as exc:
            violations.append({
                "code": _NON_DAILY_SESSION_SHAPED_CODE,
                "severity": "warning",
                "file": str(fpath.name),
                "entry": None,
                "reason": f"read_error: {exc}",
            })
            continue
        for block in _ENTRY_SPLIT.split(text):
            stripped = block.strip()
            if not (
                stripped.startswith("- what changed:")
                or stripped.startswith("- what_changed:")
                or stripped.startswith("- memory_type:")
            ):
                continue
            matched_fields = _session_like_field_names(block)
            if len(matched_fields) < 2:
                continue
            violations.append({
                "code": _NON_DAILY_SESSION_SHAPED_CODE,
                "severity": "warning",
                "file": str(fpath.name),
                "entry": _snippet(block),
                "reason": (
                    "non_daily_memory_file_contains_session_shaped_entry:"
                    f"{','.join(matched_fields)}"
                ),
            })
    return violations


def check_daily_memory(
    memory_root: Path,
    project_root: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Check 1: unbound_memory
    Scan all daily memory files; report entries lacking commit_hash + session_id.

    Returns (violations, coverage_stats).
    coverage_stats: {"total_entries": N, "bound_entries": M}
    """
    violations: list[dict[str, Any]] = []
    total_entries = 0
    bound_entries = 0

    daily_files = sorted(
        p for p in memory_root.glob('*.md') if _is_daily_file(p)
    )
    for fpath in daily_files:
        try:
            text = fpath.read_text(encoding='utf-8')
        except Exception as exc:
            violations.append({
                'code': 'unbound_memory',
                'severity': 'warning',
                'file': str(fpath.name),
                'entry': None,
                'reason': f'read_error: {exc}',
            })
            continue

        entries = _ENTRY_SPLIT.split(text)
        for block in entries:
            stripped = block.strip()
            if not (
                stripped.startswith('- what changed:')
                or stripped.startswith('- what_changed:')
                or stripped.startswith('- memory_type:')
            ):
                continue
            total_entries += 1
            bound, reason = _entry_is_bound(block, project_root)
            if bound:
                bound_entries += 1
            else:
                violations.append({
                    'code': 'unbound_memory',
                    'severity': 'warning',
                    'file': str(fpath.name),
                    'entry': _snippet(block),
                    'reason': reason,
                })

            evidence_reason = _test_evidence_provenance_violation(block, project_root)
            if evidence_reason:
                violations.append({
                    'code': 'test_evidence_provenance_not_found',
                    'severity': 'warning',
                    'file': str(fpath.name),
                    'entry': _snippet(block),
                    'reason': evidence_reason,
                })

            memory_type_match = _MEMORY_TYPE.search(block)
            memory_type = (memory_type_match.group(1).strip().lower() if memory_type_match else "")
            writer_match = _WRITER.search(block)
            writer = (writer_match.group(1).strip() if writer_match else "")
            has_format_version = bool(_RECORD_FORMAT_VERSION.search(block))

            if memory_type in _SESSION_DERIVED_MEMORY_TYPES:
                # Explicit canonical format: verify writer and version.
                if writer != _CANONICAL_MEMORY_WRITER or not has_format_version:
                    violations.append({
                        'code': 'non_canonical_writer',
                        'severity': 'warning',
                        'file': str(fpath.name),
                        'entry': _snippet(block),
                        'reason': 'session_derived_entry_not_written_by_memory_record',
                    })
            elif not memory_type and fpath.name >= _CANONICAL_WRITER_REQUIRED_FROM:
                # Old-format entry (- what changed:) in a file after the canonical writer
                # cutoff date. These bypass the canonical writer and evade non_canonical_writer
                # detection because they lack the memory_type header.
                # Grandfathered for files before _CANONICAL_WRITER_REQUIRED_FROM.
                violations.append({
                    'code': 'non_canonical_writer',
                    'severity': 'warning',
                    'file': str(fpath.name),
                    'entry': _snippet(block),
                    'reason': 'old_format_entry_after_canonical_writer_cutoff — use memory_record.append_session_derived_entry()',
                })

            bypass_reason = _session_like_non_session_memory_reason(
                block,
                memory_type=memory_type,
                filename=fpath.name,
            )
            if bypass_reason:
                violations.append({
                    'code': 'session_like_non_session_memory_type',
                    'severity': 'warning',
                    'file': str(fpath.name),
                    'entry': _snippet(block),
                    'reason': bypass_reason,
                    'authority_override': _authority_override_value(block),
                })

    coverage = {'total_entries': total_entries, 'bound_entries': bound_entries}
    return violations, coverage


def _parse_promotion_status(section_text: str) -> str:
    """
    Extract promotion_status from HTML comment markers.
    Returns one of: authoritative / candidate / stale / rejected / none
    See: governance/STRUCTURAL_PROMOTION_CONTRACT.md
    """
    m = _PROMOTION_STATUS.search(section_text)
    if not m:
        return 'none'
    return m.group(1).lower().strip()


def check_structural_memory(
    memory_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Check 2: structural_memory_auto_write
    Scan 00_long_term.md for ## sections; classify by promotion_status marker.

    Violation severity per state (STRUCTURAL_PROMOTION_CONTRACT.md):
      none         → warning (missing_marker — section not yet reviewed)
      candidate    → info   (not_yet_authoritative — AI-proposed, awaiting human)
      stale        → warning (stale_section — needs update before use)
      rejected     → info   (rejected_section — do not cite)
      authoritative without promoted_by → warning (missing_promoted_by)
      authoritative with promoted_by    → CLEAR (counts toward coverage rate)

    Returns (violations, coverage_stats).
    coverage_stats: {"total_sections": N, "promoted_sections": M}
    """
    long_term = memory_root / '00_long_term.md'
    if not long_term.exists():
        return [], {'total_sections': 0, 'promoted_sections': 0}

    try:
        text = long_term.read_text(encoding='utf-8')
    except Exception as exc:
        return (
            [{'code': 'structural_memory_auto_write', 'severity': 'info',
              'file': '00_long_term.md', 'section': None,
              'reason': f'read_error: {exc}'}],
            {'total_sections': 0, 'promoted_sections': 0},
        )

    raw_sections = _SECTION_H2.split(text)
    violations: list[dict[str, Any]] = []
    total_sections = 0
    promoted_sections = 0

    for section in raw_sections:
        if not section.strip():
            continue
        # Skip preamble (content before first ## heading)
        first_line = section.split('\n')[0].strip()
        if first_line.startswith('#'):
            continue
        total_sections += 1
        heading_line = '## ' + first_line
        promotion_status = _parse_promotion_status(section)
        has_promoted_by = bool(_PROMOTED_BY.search(section))

        if promotion_status == 'authoritative' and has_promoted_by:
            promoted_sections += 1
            # CLEAR — no violation
        elif promotion_status == 'authoritative' and not has_promoted_by:
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'warning',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'promotion_status': promotion_status,
                'reason': 'missing_promoted_by',
            })
        elif promotion_status == 'candidate':
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'info',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'promotion_status': promotion_status,
                'reason': 'not_yet_authoritative',
            })
        elif promotion_status == 'stale':
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'warning',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'promotion_status': promotion_status,
                'reason': 'stale_section',
            })
        elif promotion_status == 'rejected':
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'info',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'promotion_status': promotion_status,
                'reason': 'rejected_section',
            })
        else:
            # promotion_status == 'none' — no marker at all
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'warning',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'promotion_status': 'none',
                'reason': 'missing_marker',
            })

    coverage = {
        'total_sections': total_sections,
        'promoted_sections': promoted_sections,
    }
    return violations, coverage


def check_private_memory_cited(project_root: Path) -> list[dict[str, Any]]:
    """
    Check 3: private_memory_cited
    Scan closeout artifacts for references to the private .claude memory path.
    """
    violations: list[dict[str, Any]] = []
    artifacts_root = project_root / 'artifacts'
    if not artifacts_root.exists():
        return violations

    for json_file in artifacts_root.rglob('*.json'):
        try:
            text = json_file.read_text(encoding='utf-8')
        except Exception:
            continue
        if _PRIVATE_MEMORY_PATH.search(text):
            violations.append({
                'code': 'private_memory_cited',
                'severity': 'warning',
                'file': str(json_file.relative_to(project_root)),
                'reason': 'closeout_artifact_cites_private_claude_memory_path',
            })
    return violations


def check_missing_canonical_memory(
    memory_root: Path, project_root: Path
) -> list[dict[str, Any]]:
    """
    Check 4: missing_canonical_memory
    Infer dates with git activity; report dates that lack a daily memory file.
    Heuristic — uses git log; may produce false positives on no-commit sessions.
    """
    violations: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            ['git', 'log', '--format=%as', '--since=30 days ago'],
            capture_output=True, text=True, cwd=str(project_root), timeout=10
        )
        if result.returncode != 0:
            return violations
        commit_dates = set(result.stdout.strip().splitlines())
    except Exception:
        return violations  # skip check if git not available

    existing_dates = {
        p.stem for p in memory_root.glob('*.md') if _is_daily_file(p)
    }
    for date_str in sorted(commit_dates):
        if date_str and date_str not in existing_dates:
            violations.append({
                'code': 'missing_canonical_memory',
                'severity': 'warning',
                'date': date_str,
                'reason': 'git_commits_exist_but_no_daily_memory_file',
            })
    return violations


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _authority_integrity_status(violations: list[dict[str, Any]]) -> str:
    if any(v.get("severity", "warning") == "warning" for v in violations):
        return "warnings_present"
    if violations:
        return "info_present"
    return "clean"


def _report_only_not_claimed(authority_status: str) -> list[str]:
    not_claimed = ["blocking_enforcement", "semantic_truth_verification"]
    if authority_status != "clean":
        not_claimed.insert(0, "memory_authority_clean")
    return not_claimed


def _selective_blocking_not_claimed(authority_status: str) -> list[str]:
    # Selective blocking never claims full enforcement: only the enabled
    # codes block, everything else stays report-only.
    not_claimed = ["full_blocking_enforcement", "semantic_truth_verification"]
    if authority_status != "clean":
        not_claimed.insert(0, "memory_authority_clean")
    return not_claimed


def _apply_blocking_policy(
    violations: list[dict[str, Any]],
    enabled_codes: list[str],
) -> list[dict[str, Any]]:
    """
    Select the violations the policy actually blocks and append audit records
    for per-entry overrides. Mutates `violations` by tagging each blocking
    violation with `enforcement: block` and by appending
    `authority_override_used` report-only records.

    Exclusions (see the blocking policy RFC):
      - pre-window reasons: content classified before the activation window
        never blocks (backcompat); the diff-aware pre-window scan is
        whole-file, so it can surface legacy entries that must not block.
      - authority_override: an explicit per-entry override downgrades the
        block to a warning and emits `authority_override_used` so the
        override is auditable, never silent. The override marker is currently
        captured only for session_like_non_session_memory_type entries;
        enabling other codes gives them no override path yet.
    """
    blocking: list[dict[str, Any]] = []
    downgraded: list[dict[str, Any]] = []
    for violation in violations:
        if violation.get('code') not in enabled_codes:
            continue
        reason = str(violation.get('reason') or '')
        if reason.startswith(_PRE_WINDOW_REASON_PREFIX):
            continue
        if violation.get('authority_override'):
            downgraded.append(violation)
            continue
        violation['enforcement'] = 'block'
        blocking.append(violation)
    for violation in downgraded:
        violations.append({
            'code': 'authority_override_used',
            'severity': 'warning',
            'file': violation.get('file'),
            'entry': violation.get('entry'),
            'reason': (
                f"downgraded_from:{violation.get('code')}:"
                f"{violation.get('authority_override')}"
            ),
        })
    return blocking


def filter_active_non_canonical_writer_violations(
    violations: list[dict[str, Any]],
    *,
    active_from: str = _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
) -> list[dict[str, Any]]:
    """Return non-canonical writer violations in the active enforcement window.

    Historical violations are intentionally not migrated or reclassified by this
    helper. The date comparison is filename-based and only applies to daily
    memory files using YYYY-MM-DD.md names.
    """
    cutoff_filename = f"{active_from}.md"
    active: list[dict[str, Any]] = []
    for violation in violations:
        if violation.get("code") != "non_canonical_writer":
            continue
        filename = str(violation.get("file", ""))
        if _DATE_FILENAME.match(filename) and filename >= cutoff_filename:
            active.append(violation)
    return active


# ── aggregate ─────────────────────────────────────────────────────────────────

def run_guard(
    memory_root: Path,
    project_root: Path,
    *,
    skip_git: bool = False,
    changed_files: Sequence[str] | None = None,
    blocking_codes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    Run all four checks and return structured JSON result.
    Default: Phase 1 warning mode; all violations are non-blocking.

    changed_files: optional diff context (repo-relative paths). When provided,
    modified pre-window daily files are additionally scanned for session-shaped
    non-session entries (backdated append detection). Without diff context the
    behavior is unchanged.

    blocking_codes: optional selective blocking policy input (RFC: memory
    blocking policy, rollout step 3). Default None/empty keeps exact Phase 1
    report-only semantics — this default IS the kill switch, and its state is
    always visible in the result under `blocking_policy`. When non-empty,
    violations with an enabled code block (ok=False, enforcement_action=block)
    except pre-window-reason and authority_override entries, which stay
    report-only. No caller in hooks or CI passes this yet; activation is a
    separate policy decision (RFC rollout step 4).
    """
    violations: list[dict[str, Any]] = []

    daily_violations, daily_coverage = check_daily_memory(memory_root, project_root)
    violations.extend(daily_violations)
    if changed_files:
        violations.extend(
            check_modified_pre_window_daily_files(memory_root, changed_files)
        )
    violations.extend(
        check_non_daily_session_shaped_memory_files(memory_root, changed_files)
    )

    structural_violations, structural_coverage = check_structural_memory(memory_root)
    violations.extend(structural_violations)

    violations.extend(check_private_memory_cited(project_root))
    if not skip_git:
        violations.extend(check_missing_canonical_memory(memory_root, project_root))

    enabled_codes = sorted({
        str(code).strip() for code in (blocking_codes or []) if str(code).strip()
    })
    blocking_violations = (
        _apply_blocking_policy(violations, enabled_codes) if enabled_codes else []
    )

    counts: dict[str, int] = {}
    for v in violations:
        counts[v['code']] = counts.get(v['code'], 0) + 1

    # Authority Coverage Rate — key metric: what fraction of memory is actually bound?
    session_total = daily_coverage['total_entries']
    session_bound = daily_coverage['bound_entries']
    struct_total = structural_coverage['total_sections']
    struct_promoted = structural_coverage['promoted_sections']

    authority_coverage_rate = {
        'session_derived': {
            'total_entries': session_total,
            'bound_entries': session_bound,
            'rate': _safe_rate(session_bound, session_total),
        },
        'structural': {
            'total_sections': struct_total,
            'promoted_sections': struct_promoted,
            'rate': _safe_rate(struct_promoted, struct_total),
        },
    }
    authority_status = _authority_integrity_status(violations)

    if enabled_codes:
        blocking_codes_fired = sorted({v['code'] for v in blocking_violations})
        ok = not blocking_violations
        ok_meaning = (
            'guard_executed_selective_blocking_not_authority_clean'
            if ok
            else 'guard_executed_selective_blocking_violation_present'
        )
        enforcement_action = 'allow' if ok else 'block'
        claim_ceiling = 'selective_blocking_phase2'
        not_claimed = _selective_blocking_not_claimed(authority_status)
        policy_mode = 'selective_blocking'
    else:
        blocking_codes_fired = []
        ok = True  # Phase 1: guard executed; findings are report-only.
        ok_meaning = 'guard_executed_report_only_not_authority_clean'
        enforcement_action = 'allow'
        claim_ceiling = 'report_only_phase1'
        not_claimed = _report_only_not_claimed(authority_status)
        policy_mode = 'report_only_default'

    # Per-violation truth: a code with both blocking and report-only
    # instances (e.g. one in-window blocked, one pre-window warned) must
    # appear in both lists.
    report_only_codes = sorted({
        v['code'] for v in violations if v.get('enforcement') != 'block'
    })

    return {
        'guard': 'memory_authority_guard',
        'version': '1.2.0',
        'contract': 'governance/MEMORY_AUTHORITY_CONTRACT.md',
        'phase': 'phase1',
        'mode': 'warning' if not enabled_codes else 'selective_blocking',
        'ok': ok,
        'ok_meaning': ok_meaning,
        'authority_integrity_status': authority_status,
        'enforcement_action': enforcement_action,
        'blocking_violation_codes': blocking_codes_fired,
        'report_only_violation_codes': report_only_codes,
        'claim_ceiling': claim_ceiling,
        'not_claimed': not_claimed,
        'blocking_policy': {
            'enabled_codes': enabled_codes,
            'mode': policy_mode,
        },
        'violation_count': len(violations),
        'violation_counts_by_code': counts,
        'authority_coverage_rate': authority_coverage_rate,
        'violations': violations,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _human_summary(result: dict[str, Any]) -> str:
    n = result['violation_count']
    counts = result['violation_counts_by_code']
    acr = result.get('authority_coverage_rate', {})
    sd = acr.get('session_derived', {})
    st = acr.get('structural', {})
    sd_rate = sd.get('rate')
    st_rate = st.get('rate')
    coverage_str = (
        f"session_authority_rate={sd_rate if sd_rate is not None else 'n/a'} "
        f"structural_authority_rate={st_rate if st_rate is not None else 'n/a'}"
    )
    interpretation = (
        f"authority_integrity_status={result.get('authority_integrity_status', 'unknown')} "
        f"ok_meaning={result.get('ok_meaning', 'unknown')}"
    )
    if n == 0:
        return f'memory authority: clean (phase1=non-blocking) | {coverage_str} | {interpretation}'
    parts = [f"{k}={v}" for k, v in sorted(counts.items())]
    return (
        f'memory authority: {n} finding(s) [{", ".join(parts)}] (phase1=non-blocking; ok!=clean) '
        f'| {coverage_str} | {interpretation}'
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Memory Authority Guard — Phase 1 warning mode'
    )
    parser.add_argument(
        '--memory-root',
        default='memory',
        help='Path to memory/ directory (default: memory)',
    )
    parser.add_argument(
        '--project-root',
        default='.',
        help='Path to project root (default: .)',
    )
    parser.add_argument(
        '--skip-git',
        action='store_true',
        help='Skip missing_canonical_memory check (no git required)',
    )
    parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)',
    )
    parser.add_argument(
        '--fail-on-active-non-canonical-writer',
        action='store_true',
        help='Exit nonzero when active-window non_canonical_writer violations are present.',
    )
    parser.add_argument(
        '--active-from',
        default=_ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
        help='Active non-canonical writer cutoff date, YYYY-MM-DD (default: 2026-06-02).',
    )
    parser.add_argument(
        '--changed-file',
        action='append',
        default=None,
        metavar='PATH',
        help=(
            'Repo-relative changed file (repeatable). Provides diff context so '
            'modified pre-window daily memory files are scanned for backdated '
            'session-shaped entries.'
        ),
    )
    args = parser.parse_args(argv)

    memory_root = Path(args.memory_root)
    project_root = Path(args.project_root)

    if not memory_root.exists():
        print(f'error: memory root not found: {memory_root}', file=sys.stderr)
        sys.exit(1)

    result = run_guard(
        memory_root,
        project_root,
        skip_git=args.skip_git,
        changed_files=args.changed_file,
    )
    active_non_canonical_writer = filter_active_non_canonical_writer_violations(
        result["violations"],
        active_from=args.active_from,
    )
    result["active_non_canonical_writer"] = {
        "active_from": args.active_from,
        "count": len(active_non_canonical_writer),
        "violations": active_non_canonical_writer,
        "mode": (
            "fail_on_active_non_canonical_writer"
            if args.fail_on_active_non_canonical_writer
            else "report_only"
        ),
    }

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        summary = _human_summary(result)
        print(summary)
        if result['violations']:
            for v in result['violations']:
                code = v['code']
                sev = v.get('severity', 'warning')
                detail = v.get('entry') or v.get('section') or v.get('date') or v.get('file', '')
                reason = v.get('reason', '')
                print(f'  [{sev}] {code}: {detail!r} -- {reason}')
        active = result["active_non_canonical_writer"]
        print(
            "active non-canonical writer: "
            f"{active['count']} since {active['active_from']} "
            f"({active['mode']})"
        )

    # Phase 1: always exit 0 (warning mode)
    if (
        args.fail_on_active_non_canonical_writer
        and active_non_canonical_writer
    ):
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
