from __future__ import annotations

from pathlib import Path

from governance_tools.authority_loader import filter_for_session, resolve_conflict

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_resolve_conflict_ranks_but_has_no_runtime_caller() -> None:
    # The ranker itself works (canonical beats reference/derived)...
    entries = [
        {"file": "a.md", "authority": "derived"},
        {"file": "b.md", "authority": "canonical"},
        {"file": "c.md", "authority": "reference"},
    ]
    assert resolve_conflict(entries)["file"] == "b.md"

    # ...but nothing in the runtime path calls it. This pins the VULNERABLE
    # baseline: if precedence enforcement is wired later, this assertion breaks
    # and forces a contract/catalog status update plus its own enforcement
    # mutation contract.
    runtime_dir = _REPO_ROOT / "runtime_hooks"
    callers = [
        py.relative_to(_REPO_ROOT).as_posix()
        for py in runtime_dir.rglob("*.py")
        if "resolve_conflict" in py.read_text(encoding="utf-8")
    ]
    assert callers == [], f"resolve_conflict now referenced in runtime: {callers}"


def test_load_filtering_ignores_authority_precedence() -> None:
    # filter_for_session decides loading by audience/default_load only. Two
    # entries that differ solely in authority level must produce the same
    # filtered result — precedence does not affect what loads.
    high = {
        "file": "high.md", "audience": "agent-runtime",
        "authority": "canonical", "default_load": "always",
    }
    low = {
        "file": "low.md", "audience": "agent-runtime",
        "authority": "derived", "default_load": "always",
    }
    result = filter_for_session([high, low], include_on_demand=False)
    # Both load regardless of authority; ordering is not precedence-ranked.
    assert set(result) == {"high.md", "low.md"}


def test_override_fields_have_no_runtime_decision_consumer() -> None:
    # can_override / overridden_by are parsed + consistency-checked but inert.
    # No runtime module consumes them for a loading/override decision.
    runtime_dir = _REPO_ROOT / "runtime_hooks"
    for field in ("can_override", "overridden_by"):
        refs = [
            py.relative_to(_REPO_ROOT).as_posix()
            for py in runtime_dir.rglob("*.py")
            if field in py.read_text(encoding="utf-8")
        ]
        assert refs == [], f"{field} now referenced in runtime: {refs}"
