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
    assert "Before acting, read" in text
    assert "active, pinned framework checkout" in text


def test_f7_status_truthfulness_survives_without_on_demand_load() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "not_verified" in text
    assert "blocked" in text
    assert "verify only; do not update the framework pointer" in text
    assert "governance_tools.f7_full_update" in text
    assert "幫我更新最新版 AI Governance" in text
    assert "human_readable_adoption_summary: NOT REPORTED" in text
    assert "update_report_complete=false" in text
    assert "completion_claim_allowed=false" in text
    assert "never claim completion or fabricate table rows" in text


def test_original_f7_rules_remain_in_canonical_documents() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")
    for rule in (
        "Invalid conclusion:", "Valid partial conclusion:",
        "AI Governance update check: not_verified", "Manual update conclusion template:",
        "Destructive manual update conclusion template:", "discarded_modified_paths",
        "discarded_untracked_paths", "suggested actions do not authorize",
        "F-7 updates must preserve existing repo-specific AGENTS.md rules",
        "Required external contract surfaces", "real-session hook execution",
        "happy-path-only tests", "mock-only assertions", "test_signal_quality_audit",
    ):
        assert rule in protocol, rule
    assert "every required stage" in F7.read_text(encoding="utf-8")
    assert "mode_source" in RESPONSE.read_text(encoding="utf-8")
    # The router stays small as detailed rules grow in the on-demand sources.
    section = text.split("## AI Governance Update Intent Rule", 1)[1].split(
        "## AI Governance Memory Workflow Router", 1
    )[0]
    assert len(section.encode("utf-8")) < 1300
    assert "Invalid conclusion:" not in section
