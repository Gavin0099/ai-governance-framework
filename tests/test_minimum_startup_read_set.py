"""N4's owner-specified startup boundaries, without changing runtime gates."""

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _section(text, heading, next_heading):
    return text[text.index(heading):text.index(next_heading, text.index(heading))]


def _projection(text, name):
    match = re.search(
        rf"^<!-- ai-governance:{re.escape(name)} BEGIN[^\n]*\n"
        rf".*?^<!-- ai-governance:{re.escape(name)} END -->",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, name
    return match.group()


def test_workspace_startup_routes_by_role_and_task_instead_of_preloading_history():
    startup = _section(_text("AGENTS.md"), "## Every Session", "## Governance Contract Output")

    assert "governance/SYSTEM_PROMPT.md" in startup
    assert "§2.2" in startup and "§3.3–3.4" in startup
    assert "Main Session: read `SYSTEM_PROMPT.md`, `PLAN.md` (when present)" in startup
    assert "`memory/01_active_task.md` or verified session-start state" in startup
    assert "`memory/00_long_term.md` and recent daily logs only when needed" in startup
    assert "L0: no preload of workflow/knowledge memory or Tier-1 docs" in startup
    assert "task scope or escalation. L1/L2 use §3.3 triggers" in startup
    assert "Before doing anything else:" not in startup
    assert "(today + yesterday)" not in startup


def test_main_session_minimum_and_continuity_are_separate():
    sync = _section(_text("governance/SYSTEM_PROMPT.md"), "### 2.2 Memory Sync", "### 2.3")
    main = _section(sync, "**Main Session**", "**Subagents**")

    for path in ("governance/SYSTEM_PROMPT.md", "PLAN.md", "memory/01_active_task.md"):
        assert f"`{path}`" in main
    assert "when present" in main
    assert "or verified session-start state" in main
    assert "repo/branch, active task/checkpoint, and current PLAN boundary" in main
    assert "missing, stale, or conflicting" in main
    assert "memory/00_long_term.md" in main and "memory/YYYY-MM-DD.md" in main
    assert "only when needed for continuity" in main
    assert "not for every trivial lookup" in main


@pytest.mark.parametrize("path", ["memory/02_workflow.md", "memory/03_knowledge_base.md"])
def test_workflow_and_knowledge_memory_are_on_demand_even_for_engineering(path):
    sync = _section(_text("governance/SYSTEM_PROMPT.md"), "### 2.2 Memory Sync", "### 2.2.1")
    row = next(line for line in sync.splitlines() if line.startswith(f"| `{path}` |"))

    assert "Only when" in row
    assert "L1/L2 does not mean preloading every memory file" in sync
    assert "only if this repo has adopted" in sync


@pytest.mark.parametrize("surface", ["AGENTS.md", "governance/SYSTEM_PROMPT.md"])
def test_subagents_use_the_brief_and_cannot_reread_unscoped_history(surface):
    text = _text(surface)
    if surface == "AGENTS.md":
        startup = _section(text, "## Every Session", "## Governance Contract Output")
        subagent = _section(startup, "- Subagents", "- Context reset/compaction")
    else:
        sync = _section(text, "### 2.2 Memory Sync", "### 2.2.1")
        subagent = _section(sync, "**Subagents**", "| File |")
        assert "memory/00_long_term.md" in subagent
        assert "memory/YYYY-MM-DD.md" in subagent
        assert "already present in inherited context" in subagent
        assert "otherwise load it" in subagent
        assert "PLAN boundary" in subagent

    assert "parent's explicit brief" in subagent
    assert "MUST NOT re-read" in subagent
    assert "unrelated governance docs unless explicitly scoped into the task" in " ".join(subagent.split())


def test_loading_triggers_keep_l1_l2_and_safety_documents_conditional():
    triggers = _section(_text("governance/SYSTEM_PROMPT.md"), "### 3.3 Loading Triggers", "### 3.4")
    rows = {
        cells[2].strip(" `"): cells[3].strip()
        for line in triggers.splitlines() if line.startswith("| ")
        for cells in [line.split("|")]
    }

    assert "Every conversation" in rows["SYSTEM_PROMPT.md"]
    assert "Main Session" in rows["PLAN.md"] and "when present" in rows["PLAN.md"]
    assert "brief" in rows["PLAN.md"] and "recovery" in rows["PLAN.md"]
    assert "L1/L2 engineering tasks" in rows["AGENT.md"]
    assert "task scope or escalation" in rows["AGENT.md"]
    assert "boundary changes" in rows["ARCHITECTURE.md"] and "L2" in rows["ARCHITECTURE.md"]
    assert "Behavior, build, regression, or baseline risk" in rows["TESTING.md"]
    assert "test authoring" in rows["TESTING.md"]
    assert "SCOPE = review" in rows["REVIEW_CRITERIA.md"]
    assert "Memory write" in rows["MEMORY_PROTOCOL.md"]
    assert "Final report" in rows["RESPONSE_ENVELOPE_CONTRACT.md"]
    assert "ABI" in rows["NATIVE-INTEROP.md"]
    assert "human-only" in triggers and "not part of the normal agent loading set" in triggers


@pytest.mark.parametrize(
    "document",
    ["memory/02_workflow.md", "memory/03_knowledge_base.md", "memory/00_long_term.md",
     "AGENT.md", "ARCHITECTURE.md", "TESTING.md"],
)
def test_l0_fast_track_does_not_indirectly_preload_heavy_documents(document):
    fast_track = _section(_text("governance/SYSTEM_PROMPT.md"), "### 3.4 L0 Fast-Track", "## 4.")

    assert "Do not preload" in fast_track and f"`{document}`" in fast_track
    assert "task scope or escalation" in fast_track
    assert "presentation-only" in fast_track and "bounded lookup" in fast_track
    assert "behavior, schema, boundary, or trade-off ambiguity" in fast_track
    assert "escalate to L1/L2" in fast_track
    assert "one proportionate lightweight verification" in fast_track
    assert "使用 `AGENT.md` 裡的 lightweight fast-track path" not in fast_track
    assert "verification 只要求 `TESTING.md` 中比例相稱的部分" not in fast_track


@pytest.mark.parametrize("surface", ["AGENTS.md", "governance/SYSTEM_PROMPT.md"])
def test_context_reset_recovers_current_authority_without_replaying_history(surface):
    text = _text(surface)
    if surface == "AGENTS.md":
        startup = _section(text, "## Every Session", "## Governance Contract Output")
        recovery = startup[startup.index("- Context reset/compaction"):]
    else:
        recovery = _section(text, "### 2.2.1 Context Reset / Compaction Recovery", "### 2.3")
        assert "mandatory before emitting" in recovery
        assert "[Governance Contract: UNAVAILABLE]" in recovery
        assert "LOADED" in recovery and "prior contract" in recovery

    normalized = " ".join(recovery.split())
    assert "reload `governance/SYSTEM_PROMPT.md` before" in normalized
    assert "[Governance Contract]" in recovery
    assert "re-anchor active task/checkpoint" in normalized
    assert "re-verify current `PLAN.md` boundary" in normalized
    assert "without full historical logs" in normalized


def test_startup_selection_preserves_owner_and_closeout_obligations():
    fast_track = _section(_text("governance/SYSTEM_PROMPT.md"), "### 3.4 L0 Fast-Track", "## 4.")
    assert "never relaxes" in fast_track
    for rule in ("Owner Gate", "Agent Core Rules", "Session-End Closeout", "Governance Contract output"):
        assert rule in fast_track
    assert _projection(_text("AGENTS.md"), "session-end-closeout") == _projection(
        _text("AGENTS.base.md"), "session-end-closeout",
    )


@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_startup_and_safety_projections_survive_the_frontloaded_byte_budget(ending):
    # #381's safety margin is independent of the platform checking out the file.
    payload = _text("AGENTS.md").replace("\n", ending).encode("utf-8")
    assert payload.index(b"## Governance Contract Output") < 23000
    for name in ("checkpoint-projection", "agent-core-rules", "session-end-closeout"):
        end_marker = f"<!-- ai-governance:{name} END -->".encode("ascii")
        assert payload.index(end_marker) + len(end_marker) < 23000
