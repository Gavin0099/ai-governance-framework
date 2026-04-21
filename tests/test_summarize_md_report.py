from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.summarize_md_report import build_repo_summary_lines, render_summary


def _repo_with_review_required(closure_gate: str) -> dict:
    return {
        "repo": "Enumd",
        "targets_scanned": 3,
        "missing_targets": [],
        "aggregate": {
            "any_clean_fail": False,
            "any_noise_fail": False,
            "closure_gate": closure_gate,
            "scope_filter_compliance": "verified",
            "review_required_sample_count": 2,
            "review_required_sample_ids": ["sample-a", "sample-b"],
            "review_required_advisory_only": True,
        },
    }


def test_summary_exposes_review_required_visibility_block() -> None:
    lines = build_repo_summary_lines(_repo_with_review_required("pass"))
    text = "\n".join(lines)
    assert "review_required_visibility:" in text
    assert "review_required_sample_count: 2" in text
    assert "review_required_sample_ids: ['sample-a', 'sample-b']" in text
    assert "review_required_advisory_only: True" in text


def test_review_required_does_not_change_closure_gate_or_add_escalation_terms() -> None:
    lines = build_repo_summary_lines(_repo_with_review_required("pass"))
    text = "\n".join(lines).lower()
    assert "closure_gate: pass" in text
    assert "escalated" not in text
    assert "blocked" not in text


def test_render_summary_defaults_review_required_to_advisory_only_when_missing() -> None:
    report = {
        "contract_id": "cid",
        "generated_at_utc": "2026-04-21T00:00:00Z",
        "contract_path": "contract.json",
        "tooling": {"runner_sha256": "abc"},
        "repos": [
            {
                "repo": "SpecAuthority",
                "targets_scanned": 1,
                "missing_targets": [],
                "aggregate": {
                    "any_clean_fail": False,
                    "any_noise_fail": False,
                    "closure_gate": "pass",
                    "scope_filter_compliance": "verified",
                },
            }
        ],
    }
    output = render_summary(report)
    assert "review_required_sample_count: 0" in output
    assert "review_required_sample_ids: []" in output
    assert "review_required_advisory_only: True" in output
