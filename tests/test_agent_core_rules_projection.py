"""Drift guard for the canonical Agent Core Rules (owner ruling C1-C7, 2026-10-30).

`governance/AGENT_CORE_RULES.md` owns the body between the agent-core-rules
markers. The agent-contract template (installed into AGENTS.md, CLAUDE.md and
GEMINI.md) and the Copilot template must carry that body byte-identical after
newline normalization, so no agent surface can drift from another.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE = REPO_ROOT / "governance" / "AGENT_CORE_RULES.md"
AGENT_CONTRACT = REPO_ROOT / "governance" / "agent-contract-template.md"
COPILOT = REPO_ROOT / "governance" / "copilot-instructions-template.md"
BASELINES = (REPO_ROOT / "baselines" / "repo-min" / "AGENTS.base.md",)
BEGIN = "<!-- ai-governance:agent-core-rules BEGIN"
END = "<!-- ai-governance:agent-core-rules END -->"


def _text(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _region(text: str) -> str:
    assert text.count(BEGIN) == 1 and text.count(END) == 1
    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    assert start < end
    return text[start:end]


def _core() -> str:
    return _region(_text(CORE))


@pytest.mark.parametrize("surface", [AGENT_CONTRACT, COPILOT], ids=["agent-contract", "copilot"])
def test_core_body_is_projected_byte_identical(surface: Path) -> None:
    assert _region(_text(surface)) == _core()


@pytest.mark.parametrize(
    "surface, begin, end",
    [
        (
            AGENT_CONTRACT,
            "<!-- AI Governance Framework: agent-contract BEGIN -->",
            "<!-- AI Governance Framework: agent-contract END -->",
        ),
        (
            COPILOT,
            "<!-- AI Governance Framework: copilot-instructions BEGIN -->",
            "<!-- AI Governance Framework: copilot-instructions END -->",
        ),
    ],
    ids=["agent-contract", "copilot"],
)
def test_core_body_sits_inside_the_managed_block(surface: Path, begin: str, end: str) -> None:
    # The installer copies only the managed block; a core outside it never ships.
    text = _text(surface)
    assert text.index(begin) < text.index(BEGIN) < text.index(END) < text.index(end)


def test_agent_contract_places_core_after_unavailable_and_before_delivery() -> None:
    # Codex truncates the tail; the core must not be the first thing cut.
    text = _text(AGENT_CONTRACT)
    assert (
        text.index("<!-- ai-governance:checkpoint-projection END -->")
        < text.index("[Governance Contract: UNAVAILABLE]")
        < text.index(BEGIN)
        < text.index("## Delivery Convergence (MANDATORY)")
    )


@pytest.mark.parametrize(
    "ruling, sentence",
    [
        ("C1", "Task DONE is not session end."),
        ("C1", "A confirmed session end still requires the existing session-end closeout."),
        ("C1", "An ordinary Stop event, a final answer, or a subagent finishing is not session end."),
        ("C2", "Memory or PLAN updates these events require are part of that delivery, not extra work."),
        ("C2", "After DONE, add no unrelated rollups or new PRs"),
        (
            "C3",
            "| Architecture decision | `memory/02_workflow.md`; `PLAN.md` only when it changes PLAN scope, "
            "phase, anti-goal or another existing PLAN obligation |",
        ),
        (
            "C3",
            "| Bug fixed with root cause identified (new gotcha / solution) | `memory/03_knowledge_base.md` as a "
            "`CANDIDATE / UNREVIEWED` entry (root cause, fix, fix commit, test evidence) paired with a "
            "`memory_record` daily record for the same fix commit; never marked approved, reviewed only "
            "through promotion |",
        ),
        ("C3", "| Review completed |"),
        ("C3", "| Confirmed session end |"),
        ("C3", "never assume an alias that does not exist."),
        ("C3", "Repository-specific record duties still apply."),
        ("C4", "Memory and delivery protocols define order, not git authority."),
        ("C4", "inside an owner-authorized slice they may continue without re-asking."),
        (
            "C5",
            "merging into main, publishing or releasing, deleting branches, closing another person's PR, "
            "any irreversible operation, firmware operations, data-integrity operations, and any high-risk "
            "operation this repository's own rules name.",
        ),
        (
            "C6",
            "Filling `LOADED` or any other contract field by inference, or reusing a stale "
            "`[Governance Contract]` block",
        ),
        ("C7", "Chinese `結果：` / `原因：` / `下一步：`; English `Result:` / `Reason:` / `Next step:`."),
    ],
)
def test_core_states_each_owner_ruling(ruling: str, sentence: str) -> None:
    assert sentence in _core(), ruling


def test_core_secret_rule_copies_the_baseline_sentences() -> None:
    base = _text(BASELINES[0])
    assert "Never commit tokens, API keys, credentials, or secrets to the repo" in base
    assert "Never write tokens or credentials into memory/ files or logs" in base
    core = _core()
    assert "Never commit tokens, API keys, credentials, or secrets to the repo" in core
    assert "never write tokens or credentials into memory/ files or logs" in core


@pytest.mark.parametrize(
    "stale",
    [
        "- commit, push, closeout, or status rollup",
        "(merge, release, branch deletion, irreversible, firmware or data-integrity operations)",
        "In Chinese, use `結果：`, `原因：`, and `下一步：`.",
    ],
)
def test_copilot_conflicting_phrasing_is_gone(stale: str) -> None:
    assert stale not in _text(COPILOT)


def test_copilot_hard_stop_keeps_session_end_and_must_record_exceptions() -> None:
    text = _text(COPILOT)
    rule1 = text[text.index("### Rule 1: Hard Stop After DONE"):text.index("### Rule 2")]
    assert "commit or push outside the owner's current authorization" in rule1
    assert (
        "This never cancels must-record memory or PLAN updates, or the session-end closeout "
        "at a confirmed session end" in rule1
    )


def test_agent_contract_has_no_stale_owner_list_or_commit_rule() -> None:
    text = _text(AGENT_CONTRACT)
    assert "(merging main, release or publish, deleting branches, closing others' PRs" not in text
    assert "Commit and push require authorization from this repository's own rules" not in text


@pytest.mark.parametrize("baseline", BASELINES, ids=["repo-min"])
def test_baseline_memory_triggers_agree_with_core(baseline: Path) -> None:
    text = _text(baseline)
    triggers = text[text.index("## Memory Update Triggers"):text.index("Automatic closeout has one write boundary")]
    assert "PLAN.md decision log" not in triggers
    assert (
        "| Architecture decision made | `memory/02_workflow.md`; PLAN.md only when the decision changes "
        "PLAN scope, phase, anti-goal or another existing PLAN obligation |" in triggers
    )
    assert "| Bug fixed with root cause identified (new gotcha / solution) | `memory/03_knowledge_base.md` |" in triggers
    assert "| Review completed |" in triggers
    assert "| Session end |" in triggers
    assert "never assume an alias that does not exist" in triggers
    dod = text[text.index("## Definition of Done"):]
    assert "- PLAN.md and memory/ reflect the new state" not in dod
    assert "after DONE, add no unrelated rollups or new PRs" in dod
