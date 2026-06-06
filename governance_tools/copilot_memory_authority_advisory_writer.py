#!/usr/bin/env python3
"""
#17 Copilot memory authority advisory artifact writer.

Scope: write a single advisory observation artifact for a Copilot session that
triggered the active_non_canonical_writer warning threshold.

This tool is review-only:
- It does not block sessions.
- It must not be auto-invoked; caller must pass all required fields explicitly.
- Output is stored in artifacts/governance/ (git-tracked).
- It does not feed into any blocking gate.

Policy shape: see artifacts/governance/copilot-memory-authority-advisory-threshold-proposal-2026-06-06.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "governance.copilot.memory_authority.advisory.v1"
WRITER_ID = "governance_tools.copilot_memory_authority_advisory_writer"
WRITER_VERSION = "1.0"

VALID_TRISTATE = {"yes", "no", "unknown"}
VALID_EVIDENCE_SOURCES = {"pasted_response", "raw_guard_json", "raw_commit"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_DISPOSITIONS = {"advisory_warning", "observe_only", "escalate"}

# escalate disposition requires a separate scoped approval; warn if used.
_ESCALATE_WARNING = (
    "disposition=escalate selected; this does not authorize blocking enforcement. "
    "Escalation requires all 4 conditions from the advisory threshold proposal to be met."
)


def _validate(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []

    if not args.session_id.strip():
        errors.append("session_id must not be empty")

    try:
        datetime.fromisoformat(args.date)
    except ValueError:
        errors.append(f"date is not valid ISO 8601: {args.date!r}")

    if not args.agent.strip():
        errors.append("agent must not be empty")

    if not args.repo.strip():
        errors.append("repo must not be empty")

    if args.active_non_canonical_writer_count < 0:
        errors.append("active_non_canonical_writer_count must be >= 0")

    if args.canonical_writer_used not in VALID_TRISTATE:
        errors.append(f"canonical_writer_used must be one of {sorted(VALID_TRISTATE)}")

    if args.manual_write_detected not in VALID_TRISTATE:
        errors.append(f"manual_write_detected must be one of {sorted(VALID_TRISTATE)}")

    if args.evidence_source not in VALID_EVIDENCE_SOURCES:
        errors.append(f"evidence_source must be one of {sorted(VALID_EVIDENCE_SOURCES)}")

    if args.confidence not in VALID_CONFIDENCE:
        errors.append(f"confidence must be one of {sorted(VALID_CONFIDENCE)}")

    if args.disposition not in VALID_DISPOSITIONS:
        errors.append(f"disposition must be one of {sorted(VALID_DISPOSITIONS)}")

    return errors


def _build_artifact(args: argparse.Namespace, written_at: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "writer": WRITER_ID,
        "writer_version": WRITER_VERSION,
        "written_at": written_at,
        "session_id": args.session_id,
        "date": args.date,
        "agent": args.agent,
        "repo": args.repo,
        "active_non_canonical_writer": {
            "count": args.active_non_canonical_writer_count,
        },
        "canonical_writer_used": args.canonical_writer_used,
        "manual_write_detected": args.manual_write_detected,
        "evidence_source": args.evidence_source,
        "confidence": args.confidence,
        "disposition": args.disposition,
        "blocking_gate_enabled": False,
        "notes": args.notes or "",
    }


def write_advisory(
    *,
    output_dir: Path,
    session_id: str,
    date: str,
    agent: str,
    repo: str,
    active_non_canonical_writer_count: int,
    canonical_writer_used: str,
    manual_write_detected: str,
    evidence_source: str,
    confidence: str,
    disposition: str,
    notes: str = "",
) -> tuple[bool, Path | None, list[str]]:
    """Write a Copilot memory authority advisory artifact. Returns (ok, path, errors)."""

    class _Args:
        pass

    args = _Args()
    args.session_id = session_id
    args.date = date
    args.agent = agent
    args.repo = repo
    args.active_non_canonical_writer_count = active_non_canonical_writer_count
    args.canonical_writer_used = canonical_writer_used
    args.manual_write_detected = manual_write_detected
    args.evidence_source = evidence_source
    args.confidence = confidence
    args.disposition = disposition
    args.notes = notes

    errors = _validate(args)
    if errors:
        return False, None, errors

    written_at = datetime.now(timezone.utc).isoformat()
    artifact = _build_artifact(args, written_at)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_id = session_id.replace("/", "-").replace("\\", "-")[:80]
    filename = f"copilot-memory-authority-advisory-{safe_id}.json"
    output_path = output_dir / filename

    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True, output_path, []


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Write a Copilot memory authority advisory artifact. "
            "Review-only: does not block sessions or feed blocking gates."
        )
    )
    p.add_argument("--session-id", required=True)
    p.add_argument("--date", required=True, help="Session date (ISO 8601, e.g. 2026-06-06)")
    p.add_argument("--agent", required=True, help="Agent identifier (e.g. copilot, codex)")
    p.add_argument("--repo", required=True, help="Repo identifier")
    p.add_argument(
        "--active-non-canonical-writer-count",
        type=int,
        required=True,
        dest="active_non_canonical_writer_count",
    )
    p.add_argument(
        "--canonical-writer-used",
        required=True,
        choices=sorted(VALID_TRISTATE),
        dest="canonical_writer_used",
    )
    p.add_argument(
        "--manual-write-detected",
        required=True,
        choices=sorted(VALID_TRISTATE),
        dest="manual_write_detected",
    )
    p.add_argument(
        "--evidence-source",
        required=True,
        choices=sorted(VALID_EVIDENCE_SOURCES),
        dest="evidence_source",
    )
    p.add_argument("--confidence", required=True, choices=sorted(VALID_CONFIDENCE))
    p.add_argument("--disposition", required=True, choices=sorted(VALID_DISPOSITIONS))
    p.add_argument("--notes", default="")
    p.add_argument(
        "--output-dir",
        default="artifacts/governance",
        type=Path,
        dest="output_dir",
    )
    p.add_argument("--format", choices=("human", "json"), default="human")
    return p


def main() -> int:
    args = build_parser().parse_args()

    errors = _validate(args)
    if errors:
        for err in errors:
            print(f"[advisory_writer] error: {err}", file=sys.stderr)
        return 1

    if args.disposition == "escalate":
        print(f"[advisory_writer] warning: {_ESCALATE_WARNING}", file=sys.stderr)

    written_at = datetime.now(timezone.utc).isoformat()
    artifact = _build_artifact(args, written_at)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_id = args.session_id.replace("/", "-").replace("\\", "-")[:80]
    filename = f"copilot-memory-authority-advisory-{safe_id}.json"
    output_path = output_dir / filename

    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps({"ok": True, "path": str(output_path), "artifact": artifact}, indent=2))
    else:
        print(f"[advisory_writer] ok=True path={output_path}")
        print(f"  session_id={args.session_id}")
        print(f"  agent={args.agent} repo={args.repo}")
        print(f"  active_non_canonical_writer_count={args.active_non_canonical_writer_count}")
        print(f"  disposition={args.disposition} confidence={args.confidence}")
        print(f"  blocking_gate_enabled=False")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
