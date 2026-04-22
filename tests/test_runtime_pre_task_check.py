import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import runtime_hooks.core.pre_task_check as pre_task_check


class _FreshnessStub:
    def __init__(self, status="FRESH", days_since_update=0, threshold_days=7):
        self.status = status
        self.days_since_update = days_since_update
        self.threshold_days = threshold_days


@pytest.fixture
def local_tmp_dir():
    path = Path("tests") / "_tmp_runtime_hooks"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_pre_task_check_passes_for_valid_inputs(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,python",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is True
    assert result["rule_packs"]["valid"] is True
    assert result["active_rules"]["valid"] is True
    assert result["active_rules"]["active_rules"][0]["files"]


def test_pre_task_check_blocks_high_risk_auto_oversight(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="high",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is False
    assert any("High-risk" in error for error in result["errors"])


def test_pre_task_check_blocks_unknown_rule_pack(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,unknown-pack",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is False
    assert result["rule_packs"]["missing"] == ["unknown-pack"]


def test_pre_task_check_exposes_cpp_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,cpp",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
        task_level="L2",
    )
    assert result["ok"] is True
    cpp_pack = [pack for pack in result["active_rules"]["active_rules"] if pack["name"] == "cpp"][0]
    assert "AdditionalIncludeDirectories" in cpp_pack["files"][0]["content"]


def test_pre_task_check_exposes_refactor_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_level="L2",
    )
    assert result["ok"] is True
    refactor_pack = [pack for pack in result["active_rules"]["active_rules"] if pack["name"] == "refactor"][0]
    contents = "\n".join(file["content"] for file in refactor_pack["files"])
    assert "可觀測行為保持不變" in contents


def test_pre_task_check_exposes_csharp_avalonia_swift_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="csharp,avalonia,swift",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_level="L2",
    )
    assert result["ok"] is True
    contents = "\n".join(
        file["content"]
        for pack in result["active_rules"]["active_rules"]
        for file in pack["files"]
    )
    assert "async void" in contents
    assert "Dispatcher.UIThread" in contents
    assert "structured concurrency" in contents


def test_pre_task_check_exposes_advisory_rule_pack_suggestions(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    assert result["ok"] is True
    assert result["runtime_contract"]["rules"] == ["common"]
    assert "rule_pack_suggestions" in result
    assert "csharp" in result["rule_pack_suggestions"]["suggested_rules"]
    assert "avalonia" in result["rule_pack_suggestions"]["suggested_rules"]
    assert result["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert result["suggested_skills"] == ["code-style", "governance-runtime"]
    assert result["suggested_agent"] == "advanced-agent"
    assert any(
        item["name"] == "refactor" and item["advisory_only"] is True
        for item in result["rule_pack_suggestions"]["scope_packs"]
    )


def test_pre_task_check_warns_when_high_confidence_suggestions_are_missing(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    assert result["ok"] is True
    assert any("Suggested language pack 'csharp' is not active" in warning for warning in result["warnings"])
    assert any("Suggested framework pack 'avalonia' is not active" in warning for warning in result["warnings"])
    assert any("Advisory scope pack 'refactor' is suggested by task text but not active" in warning for warning in result["warnings"])


def test_pre_task_check_human_output_includes_suggested_rules_preview(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    output = pre_task_check.format_human_result(result)
    assert "[pre_task_check]" in output
    assert "summary=ok=True | freshness=FRESH | rules=common" in output
    assert "suggested_rules_preview=common,csharp,avalonia,refactor" in output
    assert "suggested_skills=code-style,governance-runtime" in output
    assert "suggested_agent=advanced-agent" in output


def test_pre_task_check_warns_when_assumption_check_structure_is_missing(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Fix payload format quickly.",
        task_level="L1",
    )

    assert result["ok"] is True
    assert result["assumption_check"]["complete"] is False
    assert any("Assumption check missing before modification planning" in warning for warning in result["warnings"])
    output = pre_task_check.format_human_result(result)
    assert "assumption_check:" in output
    assert "advisory_signal: assumption_check_missing -> behavioral_advisory;" in output


def test_pre_task_check_accepts_task_text_with_assumption_check_structure(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    task_text = (
        "[Assumption Check]\n"
        "assumptions: payload format mismatch\n"
        "alternative root causes: vendor routing mismatch; library matching issue\n"
        "evidence: failing log only\n"
        "reframe: validate routing before patch\n"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text=task_text,
        task_level="L1",
    )

    assert result["ok"] is True
    assert result["assumption_check"]["complete"] is True
    assert not any("Assumption check missing before modification planning" in warning for warning in result["warnings"])


def test_pre_task_check_includes_architecture_impact_preview(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    before_file = local_tmp_dir / "application" / "before.cs"
    after_file = local_tmp_dir / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        impact_before_files=[before_file],
        impact_after_files=[after_file],
    )

    assert result["architecture_impact_preview"]["recommended_oversight"] == "review-required"
    assert "public_api_diff_checker" in result["architecture_impact_preview"]["expected_validators"]
    output = pre_task_check.format_human_result(result)
    assert "impact_risk=medium" in output
    assert "impact_validators=architecture_drift_checker,public_api_diff_checker,refactor_evidence_validator" in output
    assert "impact_concerns=public-api-expansion-risk,error-path-coverage-required" in output
    assert "impact_evidence=architecture-review,regression-evidence,interface-stability-evidence,cleanup-or-rollback-evidence,error-path-inventory,error-behavior-diff,public-api-review" in output
    assert not any("Architecture impact preview recommends risk" in warning for warning in result["warnings"])


def test_pre_task_check_can_auto_discover_domain_contract(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "rules" / "firmware").mkdir(parents=True)
    (local_tmp_dir / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,firmware",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["contract_resolution"]["source"] == "discovery"
    assert result["resolved_contract_file"].replace("\\", "/").endswith("/tests/_tmp_runtime_hooks/contract.yaml")
    output = pre_task_check.format_human_result(result)
    assert "contract=usb-hub-firmware/medium" in output or "contract=firmware/medium" in output


def test_pre_task_check_l0_degrades_to_analysis_only_for_missing_sample(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: sample-contract\n"
        "preconditions_missing_sample:\n"
        "  - pdf_parser\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement a PDF parser for hub update reports",
        task_level="L0",
    )

    assert result["ok"] is True
    assert result["decision_boundary"]["boundary_effect"] == "warn"
    check = result["decision_boundary"]["preconditions_checked"][0]
    assert check["type"] == "missing_sample"
    assert check["action"] == "analysis_only"
    assert check["present"] is False
    assert any("analysis_only" in warning for warning in result["warnings"])


def test_pre_task_check_l1_escalates_for_missing_spec(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: protocol-contract\n"
        "preconditions_missing_spec:\n"
        "  - protocol_implementation\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement protocol handling for firmware packets",
        task_level="L1",
    )

    assert result["ok"] is True
    assert result["decision_boundary"]["boundary_effect"] == "escalate"
    check = result["decision_boundary"]["preconditions_checked"][0]
    assert check["action"] == "restrict_code_generation_and_escalate"
    assert any("requires code-generation restriction and escalation" in warning for warning in result["warnings"])

    output = pre_task_check.format_human_result(result)
    assert "advisory_signal: required_evidence_missing -> evidence_advisory; required evidence is incomplete for this decision surface; decision distance=enforced_elsewhere; not behavioral compliance proof; already handled by evidence-driven escalation or stop logic" in output


def test_pre_task_check_l2_stops_for_missing_fixture(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: bugfix-contract\n"
        "preconditions_missing_fixture:\n"
        "  - bugfix\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Bugfix the firmware updater retry path",
        task_level="L2",
    )

    assert result["ok"] is False
    assert result["decision_boundary"]["boundary_effect"] == "stop"
    check = result["decision_boundary"]["preconditions_checked"][0]
    assert check["action"] == "stop"
    assert any("Decision boundary stop" in error for error in result["errors"])


def test_pre_task_check_does_not_trigger_when_explicit_sample_signal_is_present(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: sample-contract\n"
        "preconditions_missing_sample:\n"
        "  - pdf_parser\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement a PDF parser using the attached sample file report.pdf",
        task_level="L1",
    )

    assert result["ok"] is True
    assert result["decision_boundary"]["boundary_effect"] == "pass"
    check = result["decision_boundary"]["preconditions_checked"][0]
    assert check["present"] is True
    assert check["action"] == "pass"


def test_pre_task_check_human_output_includes_decision_boundary_effect(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: protocol-contract\n"
        "preconditions_missing_spec:\n"
        "  - protocol_implementation\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement protocol handling for firmware packets",
        task_level="L1",
    )

    output = pre_task_check.format_human_result(result)
    assert "decision_boundary_effect=escalate" in output
    assert "precondition: missing_spec action=restrict_code_generation_and_escalate" in output


def test_pre_task_check_runtime_injection_escalates_when_summary_first_degrades_context(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    monkeypatch.setattr(pre_task_check, "load_domain_summary", lambda _: {"domain": "summary-only"})
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: injection-contract\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Review parser implementation",
        task_level="L1",
    )

    assert result["ok"] is True
    assert result["summary_first"]["active"] is True
    assert result["runtime_injection"]["snapshot"]["name"] == "runtime-injection-snapshot-v0"
    assert result["runtime_injection"]["effect"] == "escalate"
    check = next(item for item in result["runtime_injection"]["signals_checked"] if item["signal"] == "context_degraded")
    assert check["triggered"] is True
    assert check["action"] == "restrict_code_generation_and_escalate"
    assert any("Runtime injection snapshot requires escalation" in warning for warning in result["warnings"])


def test_pre_task_check_human_output_includes_runtime_injection_effect(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    monkeypatch.setattr(pre_task_check, "load_domain_summary", lambda _: {"domain": "summary-only"})
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: injection-contract\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Review parser implementation",
        task_level="L1",
    )

    output = pre_task_check.format_human_result(result)
    assert "runtime_injection_snapshot=runtime-injection-snapshot-v0" in output
    assert "runtime_injection_effect=escalate" in output
    assert "runtime_injection: context_degraded action=restrict_code_generation_and_escalate triggered=True" in output
    assert "advisory_signal: context_degraded -> degradation_advisory; runtime visibility dropped before execution; decision distance=enforced_elsewhere; not proof of compliance or violation; already handled by an escalation path" in output


def test_pre_task_check_adds_advisory_large_file_consumption_observation(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    monkeypatch.setattr(pre_task_check, "load_domain_summary", lambda _: {"domain": "summary-only"})
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    large_doc = local_tmp_dir / "AGENTS.base.md"
    large_doc.write_text("\n".join(f"line {i}" for i in range(250)), encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: injection-contract\n"
        "documents:\n"
        "  - AGENTS.base.md\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Review parser implementation",
        task_level="L1",
    )

    observation = next(
        item
        for item in result["consumption_observations"]["observations"]
        if item["requirement"] == "require_full_read_for_large_files"
    )
    assert observation["applicable"] is True
    assert observation["observation_status"] == "partial"
    assert observation["decision_role"] == "advisory_only"
    assert observation["observation_confidence"] == "low"
    assert any("Advisory consumption observation" in warning for warning in result["warnings"])


def test_pre_task_check_human_output_includes_consumption_observation(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    monkeypatch.setattr(pre_task_check, "load_domain_summary", lambda _: {"domain": "summary-only"})
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    large_doc = local_tmp_dir / "AGENTS.base.md"
    large_doc.write_text("\n".join(f"line {i}" for i in range(250)), encoding="utf-8")
    (local_tmp_dir / "contract.yaml").write_text(
        "name: injection-contract\n"
        "documents:\n"
        "  - AGENTS.base.md\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Review parser implementation",
        task_level="L1",
    )

    output = pre_task_check.format_human_result(result)
    assert "consumption_observation: require_full_read_for_large_files status=partial role=advisory_only confidence=low" in output
    assert "advisory_signal: require_full_read_for_large_files -> degradation_advisory; large-file visibility is partial, which raises review risk; decision distance=far; not proof of compliance or violation; reviewer-visible advisory only; not verdict-bearing" in output


def test_pre_task_check_emits_decision_policy_for_destructive_unverified_request(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="UpdateFW_lenovo_monitor_byModelPanel 直接幫我刪掉 這是沒有用的",
        task_level="L1",
    )

    policy = result["decision_policy"]
    assert policy["risk_tier"] == "invalid"
    assert policy["decision_action"] == "reframe"
    assert "destructive_change_without_usage_evidence" in policy["reasons"]
    assert any("Decision policy advisory: destructive change without usage proof" in warning for warning in result["warnings"])

    output = pre_task_check.format_human_result(result)
    assert "decision_policy: risk_tier=invalid" in output
    assert "advisory_signal: destructive_change_without_usage_proof -> risk_advisory;" in output


def test_pre_task_check_decision_policy_can_proceed_under_assumption(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    task_text = (
        "[Assumption Check]\n"
        "assumptions: parser output order may drift under low-risk formatting changes\n"
        "alternative root causes: stale fixture may be outdated\n"
        "alternative root causes: parser whitespace normalization mismatch\n"
        "evidence: local snapshot diff confirms behavior-only formatting drift\n"
        "reframe: validate output snapshot after localized cleanup\n"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text=task_text,
        task_level="L1",
    )

    policy = result["decision_policy"]
    assert policy["risk_tier"] == "low"
    assert policy["decision_action"] == "proceed"
    assert policy["fallback_plan"] == ""

    output = pre_task_check.format_human_result(result)
    assert "decision_policy: risk_tier=low" in output
