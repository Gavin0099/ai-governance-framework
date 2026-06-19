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
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from governance_tools.checkpoint_memory_audit import FINDING_CODES, audit

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


def _default_disposition(
    repo: Path,
    finding: dict,
    *,
    commit_subject_lookup: Callable[[Path, str], str] = _commit_subject,
) -> str:
    if finding.get("code") == "commit_without_memory":
        subject = str(finding.get("subject", ""))
        commit_subject = commit_subject_lookup(repo, subject)
        if commit_subject.startswith("docs(memory):"):
            return "expected_noise"
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
