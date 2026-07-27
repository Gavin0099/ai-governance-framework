"""Build a fixed-HEAD context dataset for the recent-20 memory retrospective.

This is a one-time measurement artifact, not a governance validator.  It reads
only committed blobs from HEAD and emits history context for later semantic
classification of each canonical memory entry's ``next_step``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_PATH_RE = re.compile(r"^memory/2026-\d{2}-\d{2}\.md$")
FIELD_RE = re.compile(r"^  ([a-z_]+):(?: (.*))?$")
FIRST_FIELD_RE = re.compile(r"^- ([a-z_]+):(?: (.*))?$")

# Manual semantic labels over the generated fixed-HEAD commit context.  These
# are observations for this one sample, not executable policy.
ANNOTATIONS: dict[int, dict[str, str | None]] = {
    1: {
        "classification": "deferred_match",
        "matched_commit_prefix": "eab44eeb",
        "rationale": (
            "The immediate work made the adapter parallel-safe; the first later "
            "commit carrying a real live-canary run review was eab44eeb."
        ),
        "confidence": "high",
    },
    2: {
        "classification": "immediate_match",
        "matched_commit_prefix": "eab44eeb",
        "rationale": (
            "The next commit added the live-canary run review and byte-exact "
            "evidence requested by the entry."
        ),
        "confidence": "high",
    },
    3: {
        "classification": "immediate_match",
        "matched_commit_prefix": "e8979673",
        "rationale": (
            "The next commit revised the live-canary runbook and isolated "
            "evidence transport as requested."
        ),
        "confidence": "high",
    },
    4: {
        "classification": "immediate_match",
        "matched_commit_prefix": "e8979673",
        "rationale": (
            "The next commit corrected live-canary provenance, answer logic, "
            "identity evidence, tests, and launch isolation."
        ),
        "confidence": "high",
    },
    5: {
        "classification": "immediate_match",
        "matched_commit_prefix": "9a96c2e7",
        "rationale": (
            "The next commit contains the final isolated run-4 NO-GO receipt "
            "and the bounded follow-up correction."
        ),
        "confidence": "high",
    },
    6: {
        "classification": "never_observed",
        "matched_commit_prefix": None,
        "rationale": (
            "No later commit in the fixed-HEAD history records the authorized "
            "revision-7 canary; work moved to scorer-packet construction."
        ),
        "confidence": "high",
    },
    7: {
        "classification": "never_observed",
        "matched_commit_prefix": None,
        "rationale": (
            "The requested scorer-packet commit was already the record commit "
            "ac9dab87, so the entry described completed work as a future step."
        ),
        "confidence": "high",
    },
    8: {
        "classification": "deferred_match",
        "matched_commit_prefix": "3bea5287",
        "rationale": (
            "Several review-driven remediation commits intervened before the "
            "independent approval and owner re-sign were recorded."
        ),
        "confidence": "high",
    },
    9: {
        "classification": "deferred_match",
        "matched_commit_prefix": "3bea5287",
        "rationale": (
            "Independent review triggered further remediation; owner re-sign "
            "was eventually recorded in 3bea5287."
        ),
        "confidence": "high",
    },
    10: {
        "classification": "deferred_match",
        "matched_commit_prefix": "3bea5287",
        "rationale": (
            "The review and later owner re-sign occurred only after additional "
            "scorer-handoff remediation."
        ),
        "confidence": "high",
    },
    11: {
        "classification": "deferred_match",
        "matched_commit_prefix": "3bea5287",
        "rationale": (
            "Re-review produced another implementation fix before approval and "
            "owner re-sign were finally recorded."
        ),
        "confidence": "high",
    },
    12: {
        "classification": "deferred_match",
        "matched_commit_prefix": "b596153b",
        "rationale": (
            "Push recording happened first; the requested independent review "
            "was only evidenced later through review-driven remediation."
        ),
        "confidence": "medium",
    },
    13: {
        "classification": "deferred_match",
        "matched_commit_prefix": "b596153b",
        "rationale": (
            "This corrective duplicate had the same next step: push was recorded "
            "before later evidence of independent review."
        ),
        "confidence": "medium",
    },
    14: {
        "classification": "deferred_match",
        "matched_commit_prefix": "b596153b",
        "rationale": (
            "Unrelated memory cleanup came next; GitLab delivery and independent "
            "review evidence appeared only in later commits."
        ),
        "confidence": "medium",
    },
    15: {
        "classification": "unassessable",
        "matched_commit_prefix": None,
        "rationale": (
            "The primary action is an external GitHub job result, while the "
            "conditional GitLab restoration was already complete at record time."
        ),
        "confidence": "high",
    },
    16: {
        "classification": "never_observed",
        "matched_commit_prefix": None,
        "rationale": (
            "The requested BLOCKER/WARN remediation was already implemented by "
            "the record commit b596153b, making the next step stale on arrival."
        ),
        "confidence": "high",
    },
    17: {
        "classification": "immediate_match",
        "matched_commit_prefix": "3bea5287",
        "rationale": (
            "The next commit records independent approval followed by the "
            "separately authorized owner re-sign."
        ),
        "confidence": "high",
    },
    18: {
        "classification": "unassessable",
        "matched_commit_prefix": None,
        "rationale": (
            "The receipt commit was the record commit itself and the remaining "
            "push action is not represented by a subsequent Git commit."
        ),
        "confidence": "high",
    },
    19: {
        "classification": "unassessable",
        "matched_commit_prefix": None,
        "rationale": (
            "The corrected receipts were committed in the record commit; remote "
            "delivery cannot be temporally established from later commits alone."
        ),
        "confidence": "high",
    },
    20: {
        "classification": "unassessable",
        "matched_commit_prefix": None,
        "rationale": (
            "The newest entry is right-censored at the fixed HEAD and has no "
            "subsequent committed work to compare."
        ),
        "confidence": "high",
    },
}


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def parse_entries(path: str) -> list[dict[str, Any]]:
    text = git("show", f"HEAD:{path}")
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if line.startswith("- memory_type:")
    ]
    entries: list[dict[str, Any]] = []
    for ordinal, start in enumerate(starts, start=1):
        stop = starts[ordinal] if ordinal < len(starts) else len(lines)
        fields: dict[str, str] = {}
        for line in lines[start:stop]:
            match = FIRST_FIELD_RE.match(line) or FIELD_RE.match(line)
            if match:
                fields[match.group(1)] = match.group(2) or ""
        entries.append(
            {
                "path": path,
                "entry_ordinal_in_file": ordinal,
                "start_line": start + 1,
                "fields": fields,
            }
        )
    return entries


def introducing_commit(path: str, line: int) -> str:
    blame = git(
        "blame",
        "--porcelain",
        "-L",
        f"{line},{line}",
        "HEAD",
        "--",
        path,
    )
    return blame.splitlines()[0].split()[0]


def resolve_commit(value: str) -> str | None:
    if not value or value.lower() in {
        "local-uncommitted",
        "uncommitted",
        "unbound",
    }:
        return None
    result = git("rev-parse", "--verify", f"{value}^{{commit}}", check=False).strip()
    return result or None


def future_commits(record_commit: str, limit: int = 12) -> list[dict[str, Any]]:
    hashes = git(
        "rev-list",
        "--first-parent",
        "--reverse",
        f"{record_commit}..HEAD",
        check=False,
    ).splitlines()
    if not hashes:
        hashes = git(
            "rev-list",
            "--ancestry-path",
            "--reverse",
            f"{record_commit}..HEAD",
            check=False,
        ).splitlines()

    contexts: list[dict[str, Any]] = []
    for commit_hash in hashes[:limit]:
        header = git("show", "-s", "--format=%H%x1f%s", commit_hash).strip()
        full_hash, subject = header.split("\x1f", maxsplit=1)
        paths = [
            line
            for line in git(
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                full_hash,
            ).splitlines()
            if line
        ]
        contexts.append(
            {
                "commit": full_hash,
                "subject": subject,
                "paths": paths,
            }
        )
    return contexts


def build_dataset() -> dict[str, Any]:
    head = git("rev-parse", "HEAD").strip()
    memory_paths = sorted(
        path
        for path in git("ls-tree", "-r", "--name-only", "HEAD", "memory").splitlines()
        if MEMORY_PATH_RE.match(path)
    )
    entries = [
        entry
        for path in memory_paths
        for entry in parse_entries(path)
        if entry["fields"].get("memory_type") == "session-derived"
    ][-20:]

    records: list[dict[str, Any]] = []
    for sequence, entry in enumerate(entries, start=1):
        fields = entry["fields"]
        record_commit = introducing_commit(entry["path"], entry["start_line"])
        future_context = future_commits(record_commit)
        annotation = ANNOTATIONS[sequence]
        matched_prefix = annotation["matched_commit_prefix"]
        matched_commit = next(
            (
                item["commit"]
                for item in future_context
                if matched_prefix and item["commit"].startswith(matched_prefix)
            ),
            None,
        )
        if matched_prefix and matched_commit is None:
            raise RuntimeError(
                f"annotation {sequence} matched commit {matched_prefix} "
                "is absent from generated future context"
            )
        records.append(
            {
                "sequence": sequence,
                "source": {
                    "path": entry["path"],
                    "entry_ordinal_in_file": entry["entry_ordinal_in_file"],
                    "start_line": entry["start_line"],
                },
                "session_id": fields.get("session_id"),
                "what_changed": fields.get("what_changed"),
                "next_step": fields.get("next_step"),
                "memory_binding": fields.get("memory_binding"),
                "linked_commit_input": (
                    fields.get("commit_hash") or fields.get("commit") or ""
                ),
                "linked_commit": resolve_commit(
                    fields.get("commit_hash") or fields.get("commit") or ""
                ),
                "record_commit": record_commit,
                "future_commit_context": future_context,
                "classification": annotation["classification"],
                "matched_commit": matched_commit,
                "rationale": annotation["rationale"],
                "confidence": annotation["confidence"],
            }
        )

    return {
        "schema_version": "0.1",
        "measurement_type": "retrospective_observation_only",
        "fixed_head": head,
        "sample_size": len(records),
        "selection": (
            "Last 20 session-derived entries in lexicographic memory/2026-*.md "
            "path order and in-file record order, read from HEAD blobs only."
        ),
        "comparison_anchor": (
            "The next_step is compared with commits after the blame-derived "
            "record_commit, while linked_commit is retained as provenance context."
        ),
        "classification_vocabulary": [
            "immediate_match",
            "deferred_match",
            "never_observed",
            "unassessable",
        ],
        "claim_ceiling": (
            "This dataset measures retrospective alignment only. It does not "
            "prove memory quality improvement, fresh-session handoff success, "
            "causality, or G4 outcome value."
        ),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    dataset = build_dataset()
    output = args.json_out
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "fixed_head": dataset["fixed_head"],
                "sample_size": dataset["sample_size"],
                "json_out": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
