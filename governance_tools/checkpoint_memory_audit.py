#!/usr/bin/env python3
"""Advisory checkpoint-memory consistency audit.

Reports divergence between selected commits, memory records, optional rollup
surfaces, and optional consumer hook/router state.

Spec: docs/governance/checkpoint-memory-audit-spec.md

CLAIM CEILING: advisory report only. This tool does not define which commits
must have memory, does not block, does not rewrite memory, does not mutate
consumer repos, and is not wired to hooks or CI.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = "0.1"
CLAIM_CLASS = "advisory"
FINDING_CODES = (
    "commit_without_memory",
    "stale_no_commit_memory",
    "unreceipted_validation",
    "rollup_memory_divergence",
    "consumer_uninstalled",
)
PLACEHOLDER_COMMITS = {"NO_COMMIT", "WORKTREE", "PENDING", "UNCOMMITTED", ""}
HASH_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
ENTRY_SPLIT_RE = re.compile(r"(?m)^(?=- memory_type:)")
FIELD_RE = re.compile(r"^\s*([a-zA-Z0-9_]+):\s*(.*)$")
PASS_RE = re.compile(r"\bPASS\b", re.IGNORECASE)
EVIDENCE_PATH_RE = re.compile(
    r"(?i)(receipt|artifact|log|path|\.json|\.jsonl|\.xml|\.txt|\.md|\.sarif|evidence[\\/])"
)
EXPLICIT_NON_RECEIPT_RE = re.compile(
    r"(?i)(no receipt|non-receipt|not applicable|n/a|no runtime validation applicable)"
)


@dataclass(frozen=True)
class Finding:
    code: str
    subject: str
    evidence: str
    suggested_action: str
    severity: str = "advisory"


@dataclass(frozen=True)
class MemoryRecord:
    file: str
    line: int
    commit_hash: str
    session_id: str
    test_evidence: str
    next_step: str
    plan_reconciliation: str


@dataclass(frozen=True)
class CommitInfo:
    hash: str
    date: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(repo: Path, args: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, (completed.stdout or "").strip(), (completed.stderr or "").strip()


def _normalize_hash(value: str) -> str:
    return value.strip().strip("`").lower()


def _selected_commits(repo: Path, *, window: str, last: int | None) -> list[CommitInfo]:
    if last is not None:
        args = ["log", f"-n{last}", "--format=%H%x09%cs"]
    else:
        args = ["log", "--format=%H%x09%cs", window]
    code, stdout, _stderr = _run_git(repo, args)
    if code != 0 or not stdout:
        return []
    commits: list[CommitInfo] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("\t", 1)
        commit_hash = parts[0].lower()
        commit_date = parts[1] if len(parts) > 1 else ""
        commits.append(CommitInfo(hash=commit_hash, date=commit_date))
    return commits


def _field_value(block: str, key: str) -> str:
    for line in block.splitlines():
        match = FIELD_RE.match(line)
        if match and match.group(1) == key:
            return match.group(2).strip()
    return ""


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def parse_memory_records(memory_root: Path) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    if not memory_root.is_dir():
        return records
    for path in sorted(memory_root.glob("20*.md")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        matches = list(ENTRY_SPLIT_RE.finditer(text))
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[start:end]
            records.append(
                MemoryRecord(
                    file=path.name,
                    line=_line_number(text, start),
                    commit_hash=_field_value(block, "commit_hash") or _field_value(block, "commit"),
                    session_id=_field_value(block, "session_id"),
                    test_evidence=_field_value(block, "test_evidence"),
                    next_step=_field_value(block, "next_step"),
                    plan_reconciliation=_field_value(block, "plan_reconciliation"),
                )
            )
    return records


def _memory_commit_refs(records: Sequence[MemoryRecord]) -> set[str]:
    refs: set[str] = set()
    for record in records:
        commit = _normalize_hash(record.commit_hash)
        if commit and commit.upper() not in PLACEHOLDER_COMMITS:
            refs.add(commit)
    return refs


def _commit_is_referenced(commit: str, refs: set[str]) -> bool:
    commit = commit.lower()
    return any(commit.startswith(ref) or ref.startswith(commit[: len(ref)]) for ref in refs)


def _has_evidence_path(text: str) -> bool:
    return bool(EVIDENCE_PATH_RE.search(text))


def _is_explicit_non_receipt_boundary(text: str) -> bool:
    return bool(EXPLICIT_NON_RECEIPT_RE.search(text))


def _hook_is_active(path: Path) -> bool:
    return path.is_file() and not path.name.endswith(".sample")


def _has_memory_router(repo: Path) -> bool:
    candidates = [
        repo / "AGENTS.md",
        repo / ".github" / "copilot-instructions.md",
        repo / ".githooks" / "pre-commit",
        repo / ".git" / "hooks" / "pre-commit",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "memory_workflow" in text and ("memory/**" in text or "MEMORY_WORKFLOW_TOOL" in text):
            return True
    return False


def _consumer_installed(repo: Path) -> bool:
    hook_dirs = [repo / ".git" / "hooks", repo / ".githooks"]
    has_pre_commit = any(_hook_is_active(hook_dir / "pre-commit") for hook_dir in hook_dirs)
    has_pre_push = any(_hook_is_active(hook_dir / "pre-push") for hook_dir in hook_dirs)
    return has_pre_commit and has_pre_push and _has_memory_router(repo)


def _rollup_hashes(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {match.group(0).lower() for match in HASH_RE.finditer(text)}


def audit(
    project_root: Path,
    *,
    window: str = "origin/main..HEAD",
    last: int | None = None,
    rollup_files: Sequence[Path] = (),
    consumer_repos: Sequence[Path] = (),
) -> dict:
    repo = project_root.resolve()
    commits = _selected_commits(repo, window=window, last=last)
    records = parse_memory_records(repo / "memory")
    memory_refs = _memory_commit_refs(records)
    commit_hashes = [commit.hash for commit in commits]
    commit_dates = {commit.date for commit in commits if commit.date}
    findings: list[Finding] = []

    for commit in commit_hashes:
        if not _commit_is_referenced(commit, memory_refs):
            findings.append(
                Finding(
                    code="commit_without_memory",
                    subject=commit[:12],
                    evidence=f"git log {window if last is None else '-n ' + str(last)}",
                    suggested_action="Decide whether this commit required a memory record under a later contract.",
                )
            )

    if commit_hashes:
        for record in records:
            record_date = record.file.removesuffix(".md")
            if (
                record.commit_hash.strip().upper() in PLACEHOLDER_COMMITS
                and record_date in commit_dates
            ):
                findings.append(
                    Finding(
                        code="stale_no_commit_memory",
                        subject=f"{record.file}:{record.line}",
                        evidence=(
                            f"commit_hash={record.commit_hash or '<empty>'}; "
                            f"selected commit date={record_date}"
                        ),
                        suggested_action="Add a corrective canonical memory record if this binding matters.",
                    )
                )

    for record in records:
        evidence = record.test_evidence
        if PASS_RE.search(evidence) and not _has_evidence_path(evidence) and not _is_explicit_non_receipt_boundary(evidence):
            findings.append(
                Finding(
                    code="unreceipted_validation",
                    subject=f"{record.file}:{record.line}",
                    evidence=evidence,
                    suggested_action="Add an evidence path or downgrade the validation claim.",
                )
            )

    for rollup in rollup_files:
        for ref in sorted(_rollup_hashes(rollup)):
            if not _commit_is_referenced(ref, memory_refs):
                findings.append(
                    Finding(
                        code="rollup_memory_divergence",
                        subject=ref,
                        evidence=str(rollup),
                        suggested_action="Reconcile rollup and memory, or mark the rollup as non-authoritative.",
                    )
                )

    for consumer in consumer_repos:
        consumer_path = consumer.resolve()
        if not _consumer_installed(consumer_path):
            findings.append(
                Finding(
                    code="consumer_uninstalled",
                    subject=str(consumer_path),
                    evidence="missing active pre-commit/pre-push hooks or memory workflow router",
                    suggested_action="Run or verify the consumer installation slice before claiming coverage.",
                )
            )

    by_code = {code: 0 for code in FINDING_CODES}
    for finding in findings:
        by_code[finding.code] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "scope": {
            "repo": str(repo),
            "window": f"--last {last}" if last is not None else window,
        },
        "claim_class": CLAIM_CLASS,
        "blocking": False,
        "findings": [asdict(finding) for finding in findings],
        "summary": {
            "by_code": by_code,
            "total": len(findings),
            "clean": len(findings) == 0,
        },
    }


def format_human(payload: dict) -> str:
    lines = [
        "[checkpoint_memory_audit]",
        f"claim_class={payload['claim_class']}",
        f"blocking={str(payload['blocking']).lower()}",
        f"repo={payload['scope']['repo']}",
        f"window={payload['scope']['window']}",
        f"clean={str(payload['summary']['clean']).lower()}",
        f"total_findings={payload['summary']['total']}",
    ]
    if payload["summary"]["by_code"]:
        lines.append("[summary_by_code]")
        for code in FINDING_CODES:
            lines.append(f"{code}={payload['summary']['by_code'].get(code, 0)}")
    if payload["findings"]:
        lines.append("[findings]")
        for finding in payload["findings"]:
            lines.append(
                f"{finding['code']}: {finding['subject']} -- {finding['suggested_action']}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory checkpoint-memory consistency audit."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--window", default="origin/main..HEAD")
    parser.add_argument("--last", type=int, default=None)
    parser.add_argument("--rollup-file", type=Path, action="append", default=[])
    parser.add_argument("--consumer-repo", type=Path, action="append", default=[])
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    payload = audit(
        args.project_root,
        window=args.window,
        last=args.last,
        rollup_files=args.rollup_file,
        consumer_repos=args.consumer_repo,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_human(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
