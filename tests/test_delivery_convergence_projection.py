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
    assert "if those rules are not in your context, ask" in section


def test_copilot_rule_3a_sits_between_rule_3_and_rule_4() -> None:
    text = _text(COPILOT)
    rule3 = text.index("### Rule 3: Dirty Tree Allowlist")
    rule3a = text.index("### Rule 3a: Product Slice First, Failure-Driven Only")
    rule4 = text.index("### Rule 4")
    assert rule3 < rule3a < rule4
    assert "never relaxes owner-gated actions" in text[rule3a:rule4]
