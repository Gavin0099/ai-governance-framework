from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "governance" / "AI_GOVERNANCE_UPDATE_PROTOCOL.md"
F7_PROTOCOL = ROOT / "governance" / "F7_FULL_UPDATE.md"
BASELINE_AGENTS = ROOT / "baselines" / "repo-min" / "AGENTS.md"
BASELINE_AGENTS_BASE = ROOT / "baselines" / "repo-min" / "AGENTS.base.md"
ROOT_AGENTS = ROOT / "AGENTS.md"
ROOT_AGENTS_BASE = ROOT / "AGENTS.base.md"


UPDATE_STATUS_LINE = (
    "AI Governance update check: <already_current | update_available | updated | "
    "manual_update | destructive_manual_update | not_submodule_consumer | not_verified>"
)

FINAL_STATUS_LINE = (
    "final_status: full_update_completed | already_current | partially_updated | "
    "manual_update | destructive_manual_update | blocked | not_submodule_consumer | not_verified"
)

MANUAL_TEMPLATE = """AI Governance update check: manual_update
ai_governance_update_result: REPORTED
framework_update_status: manual_update
governance maturity summary: <RUN | NOT RUN | NOT AVAILABLE>
adoption_status: <from maturity summary | unknown>
human_readable_adoption_summary: <REPORTED | NOT REPORTED>
reason: governed updater/F-7 was not used
claim boundary: manual pointer/lock/checkout changes may be reported; do not claim completed/latest/full adoption"""

DESTRUCTIVE_TEMPLATE = """AI Governance update check: destructive_manual_update
ai_governance_update_result: REPORTED
framework_update_status: destructive_manual_update
discarded_modified_paths: <list | none reported>
discarded_untracked_paths: <list | none reported>
governance maturity summary: <RUN | NOT RUN | NOT AVAILABLE>
human_readable_adoption_summary: <REPORTED | NOT REPORTED>
claim boundary: destructive local cleanup occurred; do not claim completed/latest/full adoption"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_update_protocol_and_baseline_share_manual_status_contract() -> None:
    protocol = _read(PROTOCOL)
    baseline = _read(BASELINE_AGENTS)

    assert (
        "This file is the canonical source for the `manual_update` and\n"
        "`destructive_manual_update` reporting vocabulary"
    ) in protocol
    assert (
        "This baseline is a propagated, managed consumer instruction copy of the\n"
        "canonical manual-update reporting vocabulary"
    ) in baseline
    assert UPDATE_STATUS_LINE in protocol
    assert UPDATE_STATUS_LINE in baseline
    assert MANUAL_TEMPLATE in protocol
    assert MANUAL_TEMPLATE in baseline
    assert DESTRUCTIVE_TEMPLATE in protocol
    assert DESTRUCTIVE_TEMPLATE in baseline


def test_f7_protocol_allows_manual_status_without_completed_claim() -> None:
    text = _read(F7_PROTOCOL)

    assert "F-7-specific projection of the canonical manual-update reporting" in text
    assert FINAL_STATUS_LINE in text
    assert "`manual_update`" in text
    assert "`destructive_manual_update`" in text
    assert "must not be reported as" in text
    assert "discarded modified and untracked path inventory" in text


def test_framework_agents_routes_consumer_manual_updates_to_incomplete_status() -> None:
    text = _read(ROOT_AGENTS)

    assert "workspace section is a trigger summary, not the canonical definition" in text
    assert "governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md" in text
    assert "prefer the governed" in text
    assert "`manual_update` path" in text
    assert "`destructive_manual_update`" in text
    assert "discarded-path inventory" in text


def test_all_agent_baselines_route_latest_update_intent_to_f7_and_guard_table_relay() -> None:
    for path in (
        ROOT_AGENTS,
        ROOT_AGENTS_BASE,
        BASELINE_AGENTS,
        BASELINE_AGENTS_BASE,
    ):
        text = _read(path)
        assert "幫我更新最新版 AI Governance" in text, path
        assert "governance_tools.f7_full_update" in text, path
        assert "human_readable_adoption_summary: NOT REPORTED" in text, path
        assert "update_report_complete=false" in text, path
        assert "completion_claim_allowed=false" in text, path


def test_protected_baselines_keep_routing_and_memory_sections_as_siblings() -> None:
    for path in (ROOT_AGENTS_BASE, BASELINE_AGENTS_BASE):
        text = _read(path)
        routing = text.index("## AI Governance Update Routing")
        memory = text.index("## Memory Update Triggers")
        memory_table = text.index("| Event | Required update |")

        assert routing < memory < memory_table, path


def test_update_protocol_requires_table_truth_for_every_terminal_result() -> None:
    protocol = _read(PROTOCOL)
    f7 = _read(F7_PROTOCOL)

    assert "route the request to `governance_tools.f7_full_update`" in protocol
    assert "every terminal update result" in protocol
    assert "agent must not claim a complete AI Governance update report" in protocol
    assert "request routes to F-7 even when the user does not name F-7" in f7
    assert "every terminal F-7 result" in f7
    assert "`completion_claim_allowed=false`" in f7
