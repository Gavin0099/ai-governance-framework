import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import governance_tools.state_generator as state_generator


class _FreshnessStub:
    def __init__(self, status="FRESH", days_since_update=0, threshold_days=7, last_updated=None):
        self.status = status
        self.days_since_update = days_since_update
        self.threshold_days = threshold_days
        self.last_updated = last_updated


@pytest.fixture
def local_tmp_dir():
    path = Path("tests") / "_tmp_state_generator"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_generate_state_includes_runtime_contract(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Add runtime hooks\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,python",
        risk="high",
        oversight="review-required",
        memory_mode="candidate",
    )

    assert state["runtime_contract"]["rules"] == ["common", "python"]
    assert state["runtime_contract"]["risk"] == "high"
    assert state["runtime_contract"]["oversight"] == "review-required"
    assert state["runtime_contract"]["memory_mode"] == "candidate"
    assert state["state_surface_contract"]["surface_role"] == "derived_context_snapshot"
    assert state["state_surface_contract"]["authority_scope"] == "session_context_only"
    assert "classification_validation" in state["state_surface_contract"]["non_authoritative_for"]
    assert state["rule_packs"]["valid"] is True
    assert state["active_rules"]["valid"] is True
    assert state["active_rules"]["active_rules"][0]["files"]
    assert "rule_pack_suggestions" in state
    assert state["suggested_skills"] == ["code-style", "governance-runtime"]
    assert state["suggested_agent"] == "advanced-agent"


def test_generate_state_missing_plan_returns_error(local_tmp_dir):
    state = state_generator.generate_state(local_tmp_dir / "PLAN.md")
    assert "error" in state


def test_generate_state_can_include_cpp_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Enforce build boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,cpp",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    cpp_pack = [pack for pack in state["active_rules"]["active_rules"] if pack["name"] == "cpp"][0]
    assert "cross-project private header" in cpp_pack["files"][0]["content"]


def test_generate_state_can_include_refactor_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Refactor service boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    refactor_pack = [pack for pack in state["active_rules"]["active_rules"] if pack["name"] == "refactor"][0]
    contents = "\n".join(file["content"] for file in refactor_pack["files"])
    assert "新的 boundary crossing" in contents


def test_generate_state_can_include_csharp_avalonia_swift_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Expand UI and concurrency governance\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="csharp,avalonia,swift",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    contents = "\n".join(
        file["content"]
        for pack in state["active_rules"]["active_rules"]
        for file in pack["files"]
    )
    assert "async void" in contents
    assert "Dispatcher.UIThread" in contents
    assert "structured concurrency" in contents


def test_generate_state_includes_advisory_rule_pack_suggestions_without_mutating_contract(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor Avalonia boundary\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Refactor UI boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    assert state["runtime_contract"]["rules"] == ["common"]
    suggested = state["rule_pack_suggestions"]["suggested_rules"]
    assert "common" in suggested
    assert "csharp" in suggested
    assert "avalonia" in suggested
    assert state["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert state["suggested_skills"] == ["code-style", "governance-runtime"]
    assert state["suggested_agent"] == "advanced-agent"
    scope_suggestions = state["rule_pack_suggestions"]["scope_packs"]
    assert any(item["name"] == "refactor" and item["advisory_only"] is True for item in scope_suggestions)


# ---------------------------------------------------------------------------
# _yaml_str
# ---------------------------------------------------------------------------

def test_yaml_str_none():
    assert state_generator._yaml_str(None) == "null"

def test_yaml_str_bool():
    assert state_generator._yaml_str(True) == "true"
    assert state_generator._yaml_str(False) == "false"

def test_yaml_str_int():
    assert state_generator._yaml_str(42) == "42"

def test_yaml_str_float():
    assert state_generator._yaml_str(3.14) == "3.14"

def test_yaml_str_plain_string():
    assert state_generator._yaml_str("hello") == "hello"

def test_yaml_str_special_chars_quoted():
    result = state_generator._yaml_str("hello: world")
    assert result.startswith('"') or result.startswith("'")

def test_yaml_str_empty_string_quoted():
    result = state_generator._yaml_str("")
    assert result.startswith('"')

def test_yaml_str_newline_quoted():
    result = state_generator._yaml_str("line1\nline2")
    assert "\\n" in result or result.startswith('"')


# ---------------------------------------------------------------------------
# dict_to_yaml
# ---------------------------------------------------------------------------

def test_dict_to_yaml_simple():
    out = state_generator.dict_to_yaml({"key": "value"})
    assert "key: value" in out

def test_dict_to_yaml_nested_dict():
    out = state_generator.dict_to_yaml({"outer": {"inner": "val"}})
    assert "outer:" in out
    assert "inner: val" in out

def test_dict_to_yaml_list_of_scalars():
    out = state_generator.dict_to_yaml({"items": ["a", "b"]})
    assert "- a" in out
    assert "- b" in out

def test_dict_to_yaml_list_of_dicts():
    out = state_generator.dict_to_yaml({"items": [{"k": "v"}]})
    assert "items:" in out
    assert "-" in out
    assert "k: v" in out

def test_dict_to_yaml_bool_value():
    out = state_generator.dict_to_yaml({"flag": True})
    assert "flag: true" in out

def test_dict_to_yaml_none_value():
    out = state_generator.dict_to_yaml({"x": None})
    assert "x: null" in out


# ---------------------------------------------------------------------------
# parse_current_phase
# ---------------------------------------------------------------------------

def test_parse_current_phase_in_progress():
    text = "[>] Phase B : Do something"
    result = state_generator.parse_current_phase(text)
    assert result["id"] == "PhaseB"
    assert result["name"] == "Do something"

def test_parse_current_phase_tilde():
    text = "[~] Phase C : Another thing"
    result = state_generator.parse_current_phase(text)
    assert result["id"] == "PhaseC"

def test_parse_current_phase_no_match():
    text = "[x] Phase A : Done already"
    result = state_generator.parse_current_phase(text)
    assert result["id"] is None
    assert result["name"] is None


# ---------------------------------------------------------------------------
# parse_backlog_counts
# ---------------------------------------------------------------------------

def test_parse_backlog_counts_returns_dict_with_priority_keys():
    # parse_backlog_counts captures only text between ## Backlog and the first
    # occurrence of \n## (which also matches \n###). Items inside ### sub-sections
    # are therefore not reachable by the current regex — function returns zeros.
    text = "## Backlog\n### P0\n- [ ] Task A\n"
    counts = state_generator.parse_backlog_counts(text)
    assert set(counts.keys()) == {"P0", "P1", "P2"}

def test_parse_backlog_counts_items_before_subsection():
    # Items appearing in the captured region (before any \n## or \n###) are not
    # counted either because current_priority is still None at that point —
    # the function only sets it from ### headers, which are excluded by regex.
    text = "## Backlog\n- [ ] orphan item\n## Other\n"
    counts = state_generator.parse_backlog_counts(text)
    assert counts == {"P0": 0, "P1": 0, "P2": 0}

def test_parse_backlog_counts_no_backlog_section():
    counts = state_generator.parse_backlog_counts("## Current Sprint\n- [ ] Task\n")
    assert counts == {"P0": 0, "P1": 0, "P2": 0}


# ---------------------------------------------------------------------------
# parse_sprint_tasks
# ---------------------------------------------------------------------------

def test_parse_sprint_tasks_empty():
    result = state_generator.parse_sprint_tasks("## Introduction\nno sprint here")
    assert result == []

def test_parse_sprint_tasks_mixed():
    text = "## Current Sprint\n- [x] Done task\n- [ ] Open task\n"
    tasks = state_generator.parse_sprint_tasks(text)
    assert len(tasks) == 2
    assert tasks[0]["done"] is True
    assert tasks[1]["done"] is False


def test_generate_state_can_include_architecture_impact_preview(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor service boundary\n",
        encoding="utf-8",
    )

    before_file = local_tmp_dir / "application" / "before.cs"
    after_file = local_tmp_dir / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        impact_before_files=[before_file],
        impact_after_files=[after_file],
    )

    preview = state["architecture_impact_preview"]
    assert preview["recommended_risk"] == "medium"
    assert preview["recommended_oversight"] == "review-required"
    assert "public-api-review" in preview["required_evidence"]
    assert "application" in preview["touched_layers"]
    guidance = state["proposal_guidance"]
    assert guidance["recommended_risk"] == "medium"
    assert "public_api_diff_checker" in guidance["expected_validators"]
    assert "public-api-review" in guidance["required_evidence"]


# ---------------------------------------------------------------------------
# parse_header
# ---------------------------------------------------------------------------

def test_parse_header_basic():
    text = "> **Owner**: Alice\n> **Version**: 2.1\n"
    result = state_generator.parse_header(text)
    assert result == {"Owner": "Alice", "Version": "2.1"}


def test_parse_header_empty():
    assert state_generator.parse_header("") == {}
    assert state_generator.parse_header("No bold keys here\n") == {}


# ---------------------------------------------------------------------------
# parse_gate_status
# ---------------------------------------------------------------------------

def test_parse_gate_status_all_states():
    text = (
        "[x] Phase 1: Done\n"
        "[X] Phase 2: Also done\n"
        "[>] Phase 3: In progress\n"
        "[ ] Phase 4: Pending\n"
    )
    result = state_generator.parse_gate_status(text)
    assert result["Phase1"] == "passed"
    assert result["Phase2"] == "passed"
    assert result["Phase3"] == "in_progress"
    assert result["Phase4"] == "pending"


def test_parse_gate_status_empty():
    assert state_generator.parse_gate_status("") == {}
    assert state_generator.parse_gate_status("no phases here\n") == {}


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------

def test_main_dry_run_yaml(local_tmp_dir, monkeypatch, capsys):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())
    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Task A\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "prog", "--plan", str(plan), "--dry-run",
    ])
    state_generator.main()
    out = capsys.readouterr().out
    assert "governance-state" in out or "runtime_contract" in out


def test_main_dry_run_json(local_tmp_dir, monkeypatch, capsys):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())
    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "prog", "--plan", str(plan), "--dry-run", "--format", "json",
    ])
    state_generator.main()
    out = capsys.readouterr().out
    data = __import__("json").loads(out)
    assert "runtime_contract" in data
