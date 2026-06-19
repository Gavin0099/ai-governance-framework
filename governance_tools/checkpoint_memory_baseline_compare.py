#!/usr/bin/env python3
"""Advisory checkpoint-memory baseline comparison report.

Loads a frozen checkpoint-memory baseline, reruns the advisory audit for the
same window, and reports new findings without blocking.

CLAIM CEILING: advisory comparison only. This module does not change
checkpoint_memory_audit behavior, does not define hook/CI/blocker behavior, and
does not rewrite memory or enforce the commit-memory binding contract.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from governance_tools.checkpoint_memory_audit import FINDING_CODES, PLACEHOLDER_COMMITS, audit

SCHEMA_VERSION = "0.1"
CLAIM_CLASS = "advisory"


@dataclass(frozen=True)
class ComparedFinding:
    code: str
    subject: str
    disposition: str
    baseline_status: str
    evidence: str
    suggested_action: str
    severity: str = "advisory"


@dataclass(frozen=True)
class MemoryEntry:
    file: str
    line: int
    commit_hash: str
    memory_binding: str
    what_changed: str


ENTRY_SPLIT_RE = re.compile(r"(?m)^(?=- memory_type:)")
FIELD_RE = re.compile(r"^\s*([a-zA-Z0-9_]+):\s*(.*)$")
MEMORY_SUBJECT_RE = re.compile(r"^(?P<file>20\d{2}-\d{2}-\d{2}\.md):(?P<line>\d+)$")


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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_window(window: str) -> tuple[str, int | None]:
    if window.startswith("--last "):
        try:
            return "origin/main..HEAD", int(window.split(None, 1)[1])
        except (IndexError, ValueError):
            return "origin/main..HEAD", None
    return window, None


def _finding_key(finding: dict) -> tuple[str, str]:
    return (str(finding["code"]), str(finding["subject"]))


def _field_value(block: str, key: str) -> str:
    for line in block.splitlines():
        match = FIELD_RE.match(line)
        if match and match.group(1) == key:
            return match.group(2).strip()
    return ""


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _memory_entries(memory_root: Path) -> list[MemoryEntry]:
    entries: list[MemoryEntry] = []
    if not memory_root.is_dir():
        return entries
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
            commit_hash = _field_value(block, "commit_hash") or _field_value(block, "commit")
            entries.append(
                MemoryEntry(
                    file=path.name,
                    line=_line_number(text, start),
                    commit_hash=commit_hash,
                    memory_binding=_field_value(block, "memory_binding"),
                    what_changed=_field_value(block, "what_changed"),
                )
            )
    return entries


def _memory_entry_by_subject(entries: Sequence[MemoryEntry], subject: str) -> MemoryEntry | None:
    match = MEMORY_SUBJECT_RE.match(subject)
    if not match:
        return None
    target_file = match.group("file")
    target_line = int(match.group("line"))
    for entry in entries:
        if entry.file == target_file and entry.line == target_line:
            return entry
    return None


def _baseline_dispositions(baseline: dict) -> dict[tuple[str, str], str]:
    dispositions: dict[tuple[str, str], str] = {}
    for group in baseline.get("dispositions", []):
        code = str(group.get("code", ""))
        disposition = str(group.get("disposition", "baseline_debt"))
        for subject in group.get("subjects", []):
            dispositions[(code, str(subject))] = disposition
    return dispositions


def _commit_subject(repo: Path, commit: str) -> str:
    code, stdout, _stderr = _run_git(repo, ["show", "-s", "--format=%s", commit])
    if code != 0:
        return ""
    return stdout


def _is_bound_entry(entry: MemoryEntry) -> bool:
    return (
        entry.memory_binding == "bound"
        and entry.commit_hash.strip()
        and entry.commit_hash.strip().upper() not in PLACEHOLDER_COMMITS
    )


def _has_later_bound_entry(entries: Sequence[MemoryEntry], entry: MemoryEntry) -> bool:
    return any(
        candidate.file == entry.file
        and candidate.line > entry.line
        and _is_bound_entry(candidate)
        for candidate in entries
    )


def _is_post_push_bound_entry(entry: MemoryEntry) -> bool:
    return _is_bound_entry(entry) and entry.what_changed.lower().startswith("post-push record:")


def _default_disposition(
    repo: Path,
    finding: dict,
    *,
    commit_subject_lookup: Callable[[Path, str], str] = _commit_subject,
    memory_entries: Sequence[MemoryEntry] = (),
) -> str:
    if finding.get("code") == "commit_without_memory":
        subject = str(finding.get("subject", ""))
        commit_subject = commit_subject_lookup(repo, subject)
        if commit_subject.startswith("docs(memory):"):
            return "expected_noise"
    if finding.get("code") == "stale_no_commit_memory":
        entry = _memory_entry_by_subject(memory_entries, str(finding.get("subject", "")))
        if entry and _has_later_bound_entry(memory_entries, entry):
            return "workflow_residue"
    if finding.get("code") == "unreceipted_validation":
        entry = _memory_entry_by_subject(memory_entries, str(finding.get("subject", "")))
        if entry and _is_post_push_bound_entry(entry):
            return "receipt_shape_residue"
    return "new_drift"


def compare_payloads(
    *,
    baseline: dict,
    current: dict,
    repo: Path,
    commit_subject_lookup: Callable[[Path, str], str] = _commit_subject,
) -> dict:
    baseline_lookup = _baseline_dispositions(baseline)
    baseline_keys = set(baseline_lookup)
    current_findings = current.get("findings", [])
    memory_entries = _memory_entries(repo / "memory")
    compared: list[ComparedFinding] = []

    for finding in current_findings:
        key = _finding_key(finding)
        if key in baseline_keys:
            disposition = baseline_lookup[key]
            baseline_status = "baseline"
        else:
            disposition = _default_disposition(
                repo,
                finding,
                commit_subject_lookup=commit_subject_lookup,
                memory_entries=memory_entries,
            )
            baseline_status = "new"
        compared.append(
            ComparedFinding(
                code=str(finding.get("code", "")),
                subject=str(finding.get("subject", "")),
                disposition=disposition,
                baseline_status=baseline_status,
                evidence=str(finding.get("evidence", "")),
                suggested_action=str(finding.get("suggested_action", "")),
                severity="advisory",
            )
        )

    by_code = {code: 0 for code in FINDING_CODES}
    by_disposition: dict[str, int] = {}
    new_by_code = {code: 0 for code in FINDING_CODES}
    for finding in compared:
        by_code[finding.code] = by_code.get(finding.code, 0) + 1
        by_disposition[finding.disposition] = by_disposition.get(finding.disposition, 0) + 1
        if finding.baseline_status == "new":
            new_by_code[finding.code] = new_by_code.get(finding.code, 0) + 1

    new_findings = [finding for finding in compared if finding.baseline_status == "new"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "claim_class": CLAIM_CLASS,
        "blocking": False,
        "baseline": {
            "baseline_id": baseline.get("baseline_id"),
            "source_head": baseline.get("source_head"),
            "source_window": baseline.get("source_window"),
            "summary": baseline.get("summary", {}),
        },
        "current": {
            "scope": current.get("scope", {}),
            "summary": current.get("summary", {}),
        },
        "delta": {
            "total_current": len(compared),
            "total_baseline": baseline.get("summary", {}).get("total", 0),
            "new_total": len(new_findings),
            "new_by_code": new_by_code,
            "by_code": by_code,
            "by_disposition": by_disposition,
        },
        "new_findings": [asdict(finding) for finding in new_findings],
        "non_claims": [
            "Does not block.",
            "Does not change checkpoint_memory_audit behavior.",
            "Does not rewrite memory.",
            "Does not enforce commit-memory binding.",
        ],
    }


def compare_baseline(project_root: Path, baseline_path: Path) -> dict:
    baseline = _load_json(baseline_path)
    window, last = _parse_window(str(baseline.get("source_window", "origin/main..HEAD")))
    current = audit(project_root, window=window, last=last)
    return compare_payloads(baseline=baseline, current=current, repo=project_root.resolve())


def format_human(payload: dict) -> str:
    lines = [
        "[checkpoint_memory_baseline_compare]",
        f"claim_class={payload['claim_class']}",
        f"blocking={str(payload['blocking']).lower()}",
        f"baseline_id={payload['baseline'].get('baseline_id')}",
        f"baseline_window={payload['baseline'].get('source_window')}",
        f"current_window={payload['current'].get('scope', {}).get('window')}",
        f"baseline_total={payload['delta']['total_baseline']}",
        f"current_total={payload['delta']['total_current']}",
        f"new_total={payload['delta']['new_total']}",
    ]
    lines.append("[current_by_code]")
    for code in FINDING_CODES:
        lines.append(f"{code}={payload['delta']['by_code'].get(code, 0)}")
    lines.append("[by_disposition]")
    for disposition, count in sorted(payload["delta"]["by_disposition"].items()):
        lines.append(f"{disposition}={count}")
    if payload["new_findings"]:
        lines.append("[new_findings]")
        for finding in payload["new_findings"]:
            lines.append(
                f"{finding['code']}: {finding['subject']} "
                f"({finding['disposition']}) -- {finding['suggested_action']}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory checkpoint-memory baseline comparison report."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("artifacts/governance/checkpoint-memory-baseline-2026-06-19.json"),
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    payload = compare_baseline(args.project_root, args.baseline)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_human(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
