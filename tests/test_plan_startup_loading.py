"""Owner-authorized summary-first loading with full-source fallback.

The real PLAN is read in place; consumer fixtures intentionally have different
layouts. A complete index alone must never qualify an untested layout.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import plan_summary as summary
from governance_tools.adopt_governance import _write_payload_layering_config
from governance_tools.task_level_detector import get_l0_context_limits

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_plan():
    path = ROOT / "PLAN.md"
    return path.read_text(encoding="utf-8"), summary.build_plan_summary(path, ROOT)


def _cli(tmp_path, monkeypatch, capsys, text, *options):
    path = tmp_path / "PLAN.md"
    path.write_bytes(text.encode("utf-8"))
    monkeypatch.setattr(sys, "argv", ["plan_summary", "--startup", "--plan", str(path), *options])
    summary.main()
    return capsys.readouterr()


def test_real_evaluated_plan_is_eligible_only_with_complete_coverage(real_plan):
    text, result = real_plan
    loading = result["startup_loading"]
    assert loading["startup_read"] == "summary"
    assert loading["index_coverage_complete"] is True
    assert loading["layout"] == "framework_plan"
    assert loading["warnings"] == []
    assert summary._complete_index(text, result["section_index"])
    output = summary.format_human(result)
    assert "startup_read=summary" in output and "index_coverage_complete=true" in output
    assert "before editing it" in output and "when the owner asks" in output


@pytest.mark.parametrize("size", [0, 16_383, 16_384, 16_385])
def test_raw_byte_threshold_inclusive_small_plan_boundary(real_plan, size):
    text, result = real_plan
    candidate = copy.deepcopy(result)
    candidate["source"]["bytes"] = size
    loading = summary._startup_loading(text, candidate)
    assert summary.FULL_READ_MAX_BYTES == 16_384
    assert loading["startup_read"] == ("full" if size <= 16_384 else "summary")
    assert loading["reason"] == ("small_plan" if size <= 16_384 else "supported_layout")


@pytest.mark.parametrize("payload", ["x" * 16_384, "中" * 5_461 + "x"], ids=["ascii", "utf8"])
def test_startup_small_plan_reads_full_source_without_compression_sidecar(tmp_path, monkeypatch, capsys, payload):
    assert len(payload.encode("utf-8")) == 16_384
    monkeypatch.setattr(summary, "build_plan_summary", lambda *args: pytest.fail("Small PLAN must not need the summary parser"))
    captured = _cli(tmp_path, monkeypatch, capsys, payload)
    assert "startup_read=full" in captured.out
    assert "reason=small_plan" in captured.out
    assert payload in captured.out
    assert not captured.err
    assert not (tmp_path / summary._PROVENANCE_SIDECAR_PATH).exists()


def test_full_read_leaves_existing_compression_evidence_unchanged(tmp_path, monkeypatch, capsys):
    sidecar = tmp_path / summary._PROVENANCE_SIDECAR_PATH
    sidecar.parent.mkdir(parents=True)
    sidecar.write_bytes(b'{"fidelity":"summarized","origin":"prior-view"}')
    before = sidecar.read_bytes()
    _cli(tmp_path, monkeypatch, capsys, "# Small PLAN\nRead all of this.\n")
    assert sidecar.read_bytes() == before


def test_unknown_large_consumer_layout_is_full_even_with_gap_free_index(tmp_path, monkeypatch, capsys):
    text = "# Product plan\n## Current work\n- [>] Keep the authorization limit.\n  Do not publish.\n\n## Archive\n" + "history\n" * 3_000
    path = tmp_path / "PLAN.md"
    path.write_bytes(text.encode("utf-8"))
    result = summary.build_plan_summary(path, tmp_path)
    assert result["startup_loading"]["index_coverage_complete"] is True
    assert result["startup_loading"]["startup_read"] == "full"
    assert "unverified_layout" in result["startup_loading"]["warnings"]
    captured = _cli(tmp_path, monkeypatch, capsys, text)
    assert text in captured.out
    assert "startup_read=full" in captured.out
    assert "WARNING" in captured.err and "read the full" in captured.err
    assert not (tmp_path / summary._PROVENANCE_SIDECAR_PATH).exists()


@pytest.mark.parametrize("mutation, warning", [
    ("gap", "incomplete_index"), ("overlap", "incomplete_index"),
    ("truncated", "incomplete_index"), ("missing_open", "open_item_coverage_incomplete"),
    ("changed_open", "open_item_coverage_incomplete"),
    ("missing_constraints", "startup_constraints_not_carried"),
    ("changed_constraints", "constraint_text_mismatch"),
])
def test_bad_coverage_never_qualifies_for_summary(real_plan, mutation, warning):
    text, result = real_plan
    candidate = copy.deepcopy(result)
    if mutation == "gap":
        candidate["section_index"][0]["end_line"] -= 1
    elif mutation == "overlap":
        candidate["section_index"][0]["end_line"] += 1
    elif mutation == "truncated":
        candidate["section_index"][-1]["end_line"] -= 1
    elif mutation == "missing_open":
        candidate["open_items"].pop()
    elif mutation == "changed_open":
        candidate["open_items"][0]["text"] = "truncated"
    elif mutation == "missing_constraints":
        candidate["carried_sections"] = []
    else:
        candidate["carried_sections"][0]["content"] = "truncated"
    loading = summary._startup_loading(text, candidate)
    assert loading["startup_read"] == "full"
    assert warning in loading["warnings"]


def test_incomplete_index_cli_falls_back_to_whole_file(real_plan, tmp_path, monkeypatch, capsys):
    text, result = real_plan
    candidate = copy.deepcopy(result)
    candidate["section_index"][0]["end_line"] += 1
    candidate["startup_loading"] = summary._startup_loading(text, candidate)
    monkeypatch.setattr(summary, "build_plan_summary", lambda *args: candidate)
    captured = _cli(tmp_path, monkeypatch, capsys, text)
    assert text in captured.out
    assert "startup_read=full" in captured.out and "incomplete_index" in captured.err


@pytest.mark.parametrize("field, value", [("index_coverage_complete", False), ("warnings", ["warning"]), ("layout", None)])
def test_summary_mode_label_alone_cannot_bypass_loading_checks(real_plan, tmp_path, monkeypatch, capsys, field, value):
    text, result = real_plan
    candidate = copy.deepcopy(result)
    candidate["startup_loading"][field] = value
    monkeypatch.setattr(summary, "build_plan_summary", lambda *args: candidate)
    captured = _cli(tmp_path, monkeypatch, capsys, text)
    assert "startup_read=full" in captured.out and text in captured.out
    assert "invalid_loading_signal" in captured.err


def test_summary_parser_failure_outputs_full_source_and_warning(tmp_path, monkeypatch, capsys):
    text = "# PLAN\n" + "preserved source\n" * 2_000
    def broken(*args):
        raise RuntimeError("parser failure")
    monkeypatch.setattr(summary, "build_plan_summary", broken)
    captured = _cli(tmp_path, monkeypatch, capsys, text)
    assert "reason=summary_failed" in captured.out
    assert text in captured.out
    assert "WARNING" in captured.err
    assert not (tmp_path / summary._PROVENANCE_SIDECAR_PATH).exists()


def test_unreadable_utf8_or_missing_plan_requires_full_read_without_false_context(tmp_path, monkeypatch, capsys):
    path = tmp_path / "PLAN.md"
    path.write_bytes(b"\xff")
    monkeypatch.setattr(sys, "argv", ["plan_summary", "--startup", "--plan", str(path)])
    with pytest.raises(SystemExit) as error:
        summary.main()
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "read the full" in captured.err
    monkeypatch.setattr(sys, "argv", ["plan_summary", "--startup", "--plan", str(tmp_path / "missing.md")])
    with pytest.raises(SystemExit) as missing:
        summary.main()
    assert missing.value.code == 1
    assert "read the full" in capsys.readouterr().err


@pytest.mark.parametrize("suffix, warning", [
    ("\n## Foreign section\nNew scope.\n", "unverified_layout"),
    ("\n```text\nunterminated\n", "unclosed_code_fence"),
    ("\n- [?] Unsupported task state\n", "unsupported_checkbox_marker"),
])
def test_unevaluated_layout_or_syntax_gets_full_read(real_plan, tmp_path, suffix, warning):
    text, _ = real_plan
    path = tmp_path / "PLAN.md"
    path.write_bytes((text + suffix).encode("utf-8"))
    loading = summary.build_plan_summary(path, tmp_path)["startup_loading"]
    assert loading["startup_read"] == "full"
    assert warning in loading["warnings"]


def test_framework_startup_summary_preserves_existing_provenance(real_plan, tmp_path, monkeypatch, capsys):
    text, _ = real_plan
    captured = _cli(tmp_path, monkeypatch, capsys, text, "--format", "json")
    result = json.loads(captured.out)
    assert result["startup_loading"]["startup_read"] == "summary"
    assert len(result["open_items"]) == 17
    sidecar = tmp_path / summary._PROVENANCE_SIDECAR_PATH
    assert json.loads(sidecar.read_text(encoding="utf-8")) == summary._PLAN_CONTEXT_PROVENANCE


def test_l0_runtime_and_new_consumer_config_use_same_canonical_plan_rule(tmp_path):
    limits = get_l0_context_limits()
    assert limits["always_load"] == ["governance/SYSTEM_PROMPT.md", "governance/AGENT.md"]
    assert limits["plan_context"] == "governance/SYSTEM_PROMPT.md#2.2"
    _write_payload_layering_config(tmp_path, "generic")
    text = (tmp_path / ".governance-payload-config.yaml").read_text(encoding="utf-8")
    assert "plan_context: governance/SYSTEM_PROMPT.md#2.2" in text
    assert "- PLAN.md" not in text
    assert "memory_policy: incremental" in text


def test_canonical_rule_commands_and_all_required_rereads_are_visible():
    text = (ROOT / "governance/SYSTEM_PROMPT.md").read_text(encoding="utf-8")
    assert "python -X utf8 scripts/plan_summary.py --startup --plan PLAN.md" in text
    assert "python -X utf8 ai-governance-framework/scripts/plan_summary.py --startup --plan PLAN.md" in text
    for token in ("16,384", "startup_read=summary", "index_coverage_complete=true", "warning", "編輯 PLAN", "owner", "索引指定的 PLAN 行"):
        assert token in text
    assert "| 0 | `PLAN.md` | Every conversation when present |" not in text


@pytest.mark.parametrize("prefix, large", [("ai-governance-framework", False), ("vendor/framework", True)], ids=["small", "unknown_large"])
def test_consumer_submodule_command_reads_consumer_plan_not_framework_plan(tmp_path, prefix, large):
    """Use an actual local submodule; no network or live repository is touched."""
    framework = tmp_path / "source"
    framework.mkdir()
    # Copy current tracked code bytes, including the uncommitted implementation.
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", "scripts", "governance_tools"], cwd=ROOT).decode("utf-8")
    for relative in paths.split("\0"):
        if relative and (ROOT / relative).is_file():
            target = framework / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
    (framework / "PLAN.md").write_text("# Framework's own PLAN must not be loaded\n", encoding="utf-8")
    def git(where, *args):
        return subprocess.run(["git", *args], cwd=where, check=True, capture_output=True, text=True)
    git(framework, "init", "-q")
    git(framework, "add", ".")
    git(framework, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "core.hooksPath=", "commit", "-qm", "Fixture")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    git(consumer, "init", "-q")
    git(consumer, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(framework), prefix)
    text = "# Consumer PLAN\n## Authorization\nDo not publish.\n"
    if large:
        text += "\n## Consumer history\n" + "historical detail\n" * 2_000
    (consumer / "PLAN.md").write_bytes(text.encode("utf-8"))
    result = subprocess.run([sys.executable, "-X", "utf8", f"{prefix}/scripts/plan_summary.py", "--startup", "--plan", "PLAN.md"],
                            cwd=consumer, capture_output=True, text=True, check=True)
    assert "startup_read=full" in result.stdout
    assert text in result.stdout
    assert "Framework's own PLAN" not in result.stdout
    assert not (consumer / summary._PROVENANCE_SIDECAR_PATH).exists()
