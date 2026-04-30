#!/usr/bin/env python3
"""
Memory Authority Guard — Phase 1 (warning mode, non-blocking)

Checks that memory entries are properly bound to traceable sources.

Two memory types:
  - session-derived (daily files: memory/YYYY-MM-DD.md)
      Binding requirement: commit_hash (resolved, not "pending") OR session_id
  - structural long-term (memory/00_long_term.md)
      Binding requirement: promoted_by marker in each ## section

Checks:
  1. unbound_memory         — daily entry lacks commit_hash + session_id
  2. structural_memory_auto_write — 00_long_term.md section lacks promoted_by
  3. private_memory_cited   — closeout artifact cites .claude private memory path
  4. missing_canonical_memory — commits in git log but no daily memory file

Phase 1: warnings only. Exit code always 0. JSON to stdout.

See: governance/MEMORY_AUTHORITY_CONTRACT.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── regex patterns ────────────────────────────────────────────────────────────

_ENTRY_SPLIT = re.compile(r'(?m)^(?=- what changed:)')
_COMMIT_RESOLVED = re.compile(r'commit hash:\s*`?([a-f0-9]{5,40})`?', re.IGNORECASE)
_COMMIT_PENDING = re.compile(r'commit hash:\s*pending', re.IGNORECASE)
_SESSION_ID = re.compile(r'session[_\s]id:\s*(\S+)', re.IGNORECASE)
_PROMOTED_BY = re.compile(r'promoted_by:', re.IGNORECASE)
_SECTION_H2 = re.compile(r'^## ', re.MULTILINE)
_PRIVATE_MEMORY_PATH = re.compile(
    r'[Cc]:\\[Uu]sers\\[^\\]+\\.claude\\projects', re.IGNORECASE
)

# ── helpers ───────────────────────────────────────────────────────────────────

_DATE_FILENAME = re.compile(r'^\d{4}-\d{2}-\d{2}\.md$')


def _is_daily_file(path: Path) -> bool:
    return _DATE_FILENAME.match(path.name) is not None


def _entry_is_bound(block: str) -> tuple[bool, str]:
    """
    Returns (is_bound, reason).
    Bound = has a real commit hash OR a session_id.
    """
    has_pending = bool(_COMMIT_PENDING.search(block))
    has_real = bool(_COMMIT_RESOLVED.search(block))
    has_session = bool(_SESSION_ID.search(block))

    # A real hash AND no pending marker = resolved
    resolved_commit = has_real and not has_pending
    if resolved_commit or has_session:
        return True, "ok"
    if has_pending:
        return False, "commit_hash_pending_no_session_id"
    return False, "no_commit_hash_no_session_id"


def _snippet(block: str, length: int = 80) -> str:
    first_line = block.strip().split('\n')[0]
    return first_line[:length]


# ── check functions ───────────────────────────────────────────────────────────

def check_daily_memory(memory_root: Path) -> list[dict[str, Any]]:
    """
    Check 1: unbound_memory
    Scan all daily memory files; report entries lacking commit_hash + session_id.
    """
    violations: list[dict[str, Any]] = []
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
            if not block.strip().startswith('- what changed:'):
                continue
            bound, reason = _entry_is_bound(block)
            if not bound:
                violations.append({
                    'code': 'unbound_memory',
                    'severity': 'warning',
                    'file': str(fpath.name),
                    'entry': _snippet(block),
                    'reason': reason,
                })
    return violations


def check_structural_memory(memory_root: Path) -> list[dict[str, Any]]:
    """
    Check 2: structural_memory_auto_write
    Scan 00_long_term.md for ## sections without a promoted_by marker.
    Reports aggregate debt count; Phase 1 = info severity.
    """
    long_term = memory_root / '00_long_term.md'
    if not long_term.exists():
        return []

    try:
        text = long_term.read_text(encoding='utf-8')
    except Exception as exc:
        return [{'code': 'structural_memory_auto_write', 'severity': 'info',
                 'file': '00_long_term.md', 'section': None,
                 'reason': f'read_error: {exc}'}]

    # Split on ## headings, keep heading with its body
    raw_sections = _SECTION_H2.split(text)
    violations: list[dict[str, Any]] = []
    for section in raw_sections:
        if not section.strip():
            continue
        heading_line = '## ' + section.split('\n')[0].strip()
        has_promoted = bool(_PROMOTED_BY.search(section))
        if not has_promoted:
            violations.append({
                'code': 'structural_memory_auto_write',
                'severity': 'info',
                'file': '00_long_term.md',
                'section': heading_line[:80],
                'reason': 'missing_promoted_by',
            })
    return violations


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


# ── aggregate ─────────────────────────────────────────────────────────────────

def run_guard(
    memory_root: Path,
    project_root: Path,
    *,
    skip_git: bool = False,
) -> dict[str, Any]:
    """
    Run all four checks and return structured JSON result.
    Phase 1: always warning mode; all violations are non-blocking.
    """
    violations: list[dict[str, Any]] = []
    violations.extend(check_daily_memory(memory_root))
    violations.extend(check_structural_memory(memory_root))
    violations.extend(check_private_memory_cited(project_root))
    if not skip_git:
        violations.extend(check_missing_canonical_memory(memory_root, project_root))

    counts: dict[str, int] = {}
    for v in violations:
        counts[v['code']] = counts.get(v['code'], 0) + 1

    return {
        'guard': 'memory_authority_guard',
        'version': '1.0.0',
        'contract': 'governance/MEMORY_AUTHORITY_CONTRACT.md',
        'phase': 'phase1',
        'mode': 'warning',
        'ok': True,  # Phase 1: always ok (non-blocking)
        'violation_count': len(violations),
        'violation_counts_by_code': counts,
        'violations': violations,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _human_summary(result: dict[str, Any]) -> str:
    n = result['violation_count']
    counts = result['violation_counts_by_code']
    if n == 0:
        return 'memory authority: ok (no violations)'
    parts = [f"{k}={v}" for k, v in sorted(counts.items())]
    return f'memory authority: {n} warning(s) [{", ".join(parts)}] (phase1=non-blocking)'


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
    args = parser.parse_args(argv)

    memory_root = Path(args.memory_root)
    project_root = Path(args.project_root)

    if not memory_root.exists():
        print(f'error: memory root not found: {memory_root}', file=sys.stderr)
        sys.exit(1)

    result = run_guard(memory_root, project_root, skip_git=args.skip_git)

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
                print(f'  [{sev}] {code}: {detail!r} — {reason}')

    # Phase 1: always exit 0 (warning mode)
    sys.exit(0)


if __name__ == '__main__':
    main()
