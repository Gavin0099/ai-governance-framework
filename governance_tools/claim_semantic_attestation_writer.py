#!/usr/bin/env python3
"""Emit a claim_semantic_attestation.v0.1 receipt.

Producer side of R2 Option B
(docs/governance/self-governance-claim-semantic-attestation-design-2026-07-05.md).

The receipt records that a reviewer / agent attested to a claim boundary. It is
durable review evidence, not proof that the attestation is true.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.claim_enforcement_checker import (
    CLAIM_LEVEL_ORDER,
    CLAIM_SEMANTIC_ATTESTATION_SCHEMA,
    validate_claim_semantic_attestation_receipt,
)


_DEFAULT_OUTPUT_DIR = "artifacts/evidence/claim-attestations"
_DEFAULT_CANNOT_CLAIM = [
    "receipt does not prove the reviewer was correct",
    "receipt does not prove evidence truth",
    "receipt does not prove semantic correctness of the claim",
    "receipt authenticity: every field is fabricatable by a direct writer",
]


def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_head(project_root: Path) -> str | None:
    toplevel = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if toplevel.returncode != 0:
        return None
    try:
        if Path(toplevel.stdout.strip()).resolve() != project_root.resolve():
            return None
    except OSError:
        return None

    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    head = completed.stdout.strip()
    return head if completed.returncode == 0 and head else None


def _relpath(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _ensure_inside_project_root(path: Path, project_root: Path, label: str) -> None:
    try:
        path.resolve().relative_to(project_root.resolve())
    except (ValueError, OSError):
        raise SystemExit(f"error: {label} must be inside the project root, got: {path}")


def write_receipt(
    project_root: Path,
    *,
    reviewed_claim: str,
    reviewed_claim_level: str,
    attested_support_level: str,
    attestation_result: str,
    evidence_refs: list[str],
    attested_by: str,
    linked_commit: str | None = None,
    output: Path | None = None,
    scope_boundaries: list[str] | None = None,
    residual_risks: list[str] | None = None,
    cannot_claim: list[str] | None = None,
) -> Path:
    project_root = project_root.resolve()
    if output is None:
        output = project_root / _DEFAULT_OUTPUT_DIR / f"claim-attestation-{_utc_stamp()}.json"
    elif not output.is_absolute():
        output = project_root / output

    _ensure_inside_project_root(output, project_root, "receipt output")
    output.parent.mkdir(parents=True, exist_ok=True)

    commit = linked_commit or _git_head(project_root)
    if commit is None:
        raise SystemExit(
            "error: linked_commit is required when project_root is not a git worktree root"
        )

    payload = {
        "receipt_schema": CLAIM_SEMANTIC_ATTESTATION_SCHEMA,
        "status": "report_only",
        "reviewed_claim": reviewed_claim,
        "reviewed_claim_level": reviewed_claim_level,
        "evidence_refs": list(evidence_refs),
        "attested_support_level": attested_support_level,
        "attestation_result": attestation_result,
        "attested_by": attested_by,
        "linked_commit": commit,
        "scope_boundaries": list(scope_boundaries or []),
        "residual_risks": list(residual_risks or []),
        "cannot_claim": list(cannot_claim or _DEFAULT_CANNOT_CLAIM),
    }

    error = validate_claim_semantic_attestation_receipt(
        payload,
        project_root=project_root,
    )
    if error is not None:
        raise SystemExit(f"error: produced receipt failed self-validation: {error}")

    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Emit a claim_semantic_attestation.v0.1 receipt.",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Receipt path relative to project root "
            f"(default: {_DEFAULT_OUTPUT_DIR}/claim-attestation-<utc>.json)"
        ),
    )
    parser.add_argument("--reviewed-claim", required=True)
    parser.add_argument(
        "--reviewed-claim-level",
        required=True,
        choices=sorted(CLAIM_LEVEL_ORDER),
    )
    parser.add_argument(
        "--attested-support-level",
        required=True,
        choices=sorted(CLAIM_LEVEL_ORDER),
    )
    parser.add_argument(
        "--attestation-result",
        required=True,
        choices=("aligned", "overstated", "unclear"),
    )
    parser.add_argument("--evidence-ref", action="append", required=True)
    parser.add_argument("--attested-by", required=True)
    parser.add_argument("--linked-commit", default=None)
    parser.add_argument("--scope-boundary", action="append", default=[])
    parser.add_argument("--residual-risk", action="append", default=[])
    parser.add_argument(
        "--cannot-claim",
        action="append",
        default=None,
        help="Override the default cannot_claim list; pass multiple times.",
    )
    args = parser.parse_args(argv)

    output = Path(args.output) if args.output else None
    receipt_path = write_receipt(
        Path(args.project_root),
        reviewed_claim=args.reviewed_claim,
        reviewed_claim_level=args.reviewed_claim_level,
        attested_support_level=args.attested_support_level,
        attestation_result=args.attestation_result,
        evidence_refs=list(args.evidence_ref),
        attested_by=args.attested_by,
        linked_commit=args.linked_commit,
        output=output,
        scope_boundaries=list(args.scope_boundary),
        residual_risks=list(args.residual_risk),
        cannot_claim=args.cannot_claim,
    )

    project_root = Path(args.project_root).resolve()
    print(f"[claim_semantic_attestation] receipt={_relpath(receipt_path, project_root)}")


if __name__ == "__main__":
    main()
