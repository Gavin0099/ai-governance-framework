"""Focused contract tests for the consumer's compact F-7 instruction router.

These assertions protect the always-visible, fail-closed boundary. They are
not evidence that a model actually loaded the on-demand documents: that needs
an independent agent-session test before claiming behavioral equivalence.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "baselines/repo-min/AGENTS.md"
PROTOCOL = ROOT / "governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md"
F7 = ROOT / "governance/F7_FULL_UPDATE.md"
RESPONSE = ROOT / "governance/RESPONSE_ENVELOPE_CONTRACT.md"
TESTING = ROOT / "governance/TESTING.md"


def test_compact_router_references_existing_canonical_documents() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert text.count("## AI Governance Update Intent Rule") == 1
    assert "## AI Governance Memory Workflow Router" in text
    assert "<!-- governance:key=memory_workflow -->" in text

    for document in (PROTOCOL, F7, RESPONSE, TESTING):
        assert document.is_file()
        assert f"governance/{document.name}" in text
    assert "read both documents" in text or "load the canonical update and F-7 documents" in text
    assert "active, pinned framework checkout" in text


def test_f7_status_truthfulness_survives_without_on_demand_load() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "not_verified" in text
    assert "blocked" in text
    assert "already_current" in text
    assert "updated" in text
    assert "manual_update" in text
    assert "destructive_manual_update" in text
    assert "update_available" in text
    assert "partially_updated" in text
    assert "full_update_completed" in text
    assert "human_readable_adoption_summary: NOT REPORTED" in text
    assert "update_report_complete=false" in text
    assert "completion_claim_allowed=false" in text
    assert "Never fabricate" in text or "Never fabricate" in text.capitalize()
    assert "owner" in text.lower()


def test_original_f7_evidence_and_false_completion_cases_remain_inline() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "Invalid conclusion:" in text
    assert "Valid partial conclusion:" in text
    assert "AI Governance update check: not_verified" in text
    assert "Manual update conclusion template:" in text
    assert "Destructive manual update conclusion template:" in text
    assert "discarded_modified_paths" in text
    assert "discarded_untracked_paths" in text
    assert "F-7 Full Update Semantics" in text
    assert "suggested actions do not grant\nauthorization" in text
