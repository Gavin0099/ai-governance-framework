"""Producer-side tests for claim semantic attestation receipts.

Contract: docs/governance/self-governance-claim-semantic-attestation-design-2026-07-05.md

The writer emits durable report-only receipts. It proves a receipt was recorded,
not that the reviewer was correct or that evidence supports the claim.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from governance_tools.claim_enforcement_checker import (
    evaluate,
    validate_claim_semantic_attestation_receipt,
)
from governance_tools.claim_semantic_attestation_writer import write_receipt


def _git_repo(tmp_path: Path) -> tuple[Path, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "seed",
        ],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return tmp_path, head


def _write_aligned_receipt(project_root: Path, **overrides: object) -> Path:
    args = {
        "reviewed_claim": "This resolves the current diff.",
        "reviewed_claim_level": "bounded",
        "attested_support_level": "bounded",
        "attestation_result": "aligned",
        "evidence_refs": ["pytest tests/test_claim_semantic_attestation_writer.py"],
        "attested_by": "agent-reviewer",
    }
    args.update(overrides)
    return write_receipt(project_root, **args)


def test_writer_produces_durable_valid_receipt_at_default_root(tmp_path: Path) -> None:
    project_root, head = _git_repo(tmp_path)

    receipt_path = _write_aligned_receipt(project_root)

    relative = receipt_path.resolve().relative_to(project_root.resolve()).as_posix()
    assert relative.startswith("artifacts/evidence/claim-attestations/")
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["receipt_schema"] == "claim_semantic_attestation.v0.1"
    assert payload["status"] == "report_only"
    assert payload["linked_commit"] == head
    assert validate_claim_semantic_attestation_receipt(
        payload,
        project_root=project_root,
    ) is None


def test_writer_receipt_can_be_consumed_inline_by_claim_checker(tmp_path: Path) -> None:
    project_root, _ = _git_repo(tmp_path)
    receipt_path = _write_aligned_receipt(project_root)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    out = evaluate(
        {
            "project_root": str(project_root),
            "semantic_review_claimed": True,
            "final_claim": receipt["reviewed_claim"],
            "claim_level": receipt["reviewed_claim_level"],
            "publication_scope": "public",
            "claim_semantic_attestation": receipt,
        }
    )

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == []


def test_writer_preserves_overstated_attestation_result_as_report_only(tmp_path: Path) -> None:
    project_root, _ = _git_repo(tmp_path)
    receipt_path = _write_aligned_receipt(
        project_root,
        attestation_result="overstated",
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    out = evaluate(
        {
            "project_root": str(project_root),
            "semantic_review_claimed": True,
            "final_claim": receipt["reviewed_claim"],
            "claim_level": receipt["reviewed_claim_level"],
            "publication_scope": "public",
            "claim_semantic_attestation": receipt,
        }
    )

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == ["claim_semantic_attestation_overstated"]


def test_writer_requires_linked_commit_outside_git_worktree(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="linked_commit is required"):
        _write_aligned_receipt(tmp_path)


def test_writer_rejects_out_of_root_output(tmp_path: Path) -> None:
    project_root, _ = _git_repo(tmp_path / "repo")
    outside = tmp_path / "outside" / "claim.json"

    with pytest.raises(SystemExit, match="receipt output must be inside"):
        _write_aligned_receipt(project_root, output=outside)

    assert not outside.exists()
