from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_CONTRACT = REPO_ROOT / "governance" / "agent-contract-template.md"
COPILOT = REPO_ROOT / "governance" / "copilot-instructions-template.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_delivery_convergence_sits_last_in_agent_contract_block() -> None:
    # Codex truncates the tail of over-budget project docs. Keeping this section
    # last means overflow can only cut it, never the checkpoint projection or the
    # UNAVAILABLE notice before it.
    text = _text(AGENT_CONTRACT)
    projection_end = text.index("<!-- ai-governance:checkpoint-projection END -->")
    unavailable = text.index("[Governance Contract: UNAVAILABLE]")
    section = text.index("## Delivery Convergence (MANDATORY)")
    block_end = text.index("<!-- AI Governance Framework: agent-contract END -->")
    assert projection_end < unavailable < section < block_end
    assert "\n## " not in text[section + 1:block_end]


def test_agent_contract_guard_keeps_owner_gates_and_does_not_grant_commit() -> None:
    # The same block is installed into CLAUDE.md, where consumer authority tiers
    # in AGENTS.md are not loaded by default; the guard must stay restrictive.
    text = _text(AGENT_CONTRACT)
    section = text[text.index("## Delivery Convergence (MANDATORY)"):]
    assert "never relaxes owner-gated actions" in section
    assert "explicitly require, or session-end closeout" in section
    # Owner ruling C4 (2026-10-30): commit/push authority lives in the Agent Core
    # Rules projected earlier in the same block; this guard defers to it.
    assert "commit and push authority (Agent Core Rules above)" in section
    core = text[text.index("## Agent Core Rules (MANDATORY)"):text.index("## Delivery Convergence (MANDATORY)")]
    assert "If neither is in your context, ask." in core


def test_both_templates_share_the_finding_disposition_semantics() -> None:
    # Codex/Claude and Copilot must make the same call on a finding: continue on a
    # confirmed-unrelated, non-blocking one; escalate on unknown impact or real risk.
    agent = _text(AGENT_CONTRACT)
    agent_rules = agent[agent.index("## Delivery Convergence (MANDATORY)"):]
    copilot = _text(COPILOT)
    copilot_rule = copilot[copilot.index("### Rule 3a"):copilot.index("### Rule 4")]
    for section in (agent_rules, copilot_rule):
        assert "confirmed unrelated" in section
        assert "one-line disposition under next options" in section
        assert "remains unknown after a bounded check" in section
        assert "credible safety, authority or data-integrity risk exists" in section


def test_copilot_rule_3a_sits_between_rule_3_and_rule_4() -> None:
    text = _text(COPILOT)
    rule3 = text.index("### Rule 3: Dirty Tree Allowlist")
    rule3a = text.index("### Rule 3a: Product Slice First, Failure-Driven Only")
    rule4 = text.index("### Rule 4")
    assert rule3 < rule3a < rule4
    assert "never relaxes owner-gated actions" in text[rule3a:rule4]
