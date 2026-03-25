import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.session_start import build_session_start_context, format_human_result


@pytest.fixture
def local_session_start_root():
    path = Path("tests") / "_tmp_session_start"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_session_start_context_merges_state_and_pre_task(local_session_start_root):
    plan = local_session_start_root / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor Avalonia boundary\n",
        encoding="utf-8",
    )
    (local_session_start_root / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_session_start_root / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )
    before_file = local_session_start_root / "application" / "before.cs"
    after_file = local_session_start_root / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    result = build_session_start_context(
        project_root=local_session_start_root,
        plan_path=plan,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
        impact_before_files=[before_file],
        impact_after_files=[after_file],
    )

    assert result["runtime_contract"]["rules"] == ["common"]
    assert result["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert result["suggested_skills"] == ["code-style", "governance-runtime"]
    assert result["suggested_agent"] == "advanced-agent"
    assert result["proposal_guidance"]["recommended_risk"] == "medium"
    assert "public_api_diff_checker" in result["proposal_guidance"]["expected_validators"]
    assert result["change_proposal"]["requested_rules"] == ["common"]
    assert result["change_proposal"]["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert result["proposal_summary"]["recommended_risk"] == "medium"


def test_session_start_human_output_is_actionable(local_session_start_root):
    plan = local_session_start_root / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    (local_session_start_root / "tool.py").write_text("print('ok')", encoding="utf-8")

    result = build_session_start_context(
        project_root=local_session_start_root,
        plan_path=plan,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Improve CLI human output",
    )

    output = format_human_result(result)
    assert "[session_start]" in output
    assert "summary=ok=False | rules=common" in output
    assert "suggested_skills=code-style,governance-runtime,python,human-readable-cli" in output
    assert "suggested_agent=cli-agent" in output
    assert "proposal_rules=common" in output


def test_session_start_can_load_domain_contract_with_external_rules(local_session_start_root):
    plan = local_session_start_root / "PLAN.md"
    plan.write_text(
        "> **最後更新**: 2026-03-24\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    contract_root = local_session_start_root / "usb_hub_contract"
    (contract_root / "docs").mkdir(parents=True)
    (contract_root / "rules" / "firmware").mkdir(parents=True)
    (contract_root / "validators").mkdir(parents=True)
    (contract_root / "docs" / "start_session.md").write_text("# Start\nRead board map.\n", encoding="utf-8")
    (contract_root / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    (contract_root / "validators" / "firmware_validator.py").write_text("def validate():\n    return True\n", encoding="utf-8")
    contract_file = contract_root / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "documents:\n"
        "  - docs/start_session.md\n"
        "rule_roots:\n"
        "  - rules\n"
        "validators:\n"
        "  - validators/firmware_validator.py\n",
        encoding="utf-8",
    )

    result = build_session_start_context(
        project_root=local_session_start_root,
        plan_path=plan,
        rules="common,firmware",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Validate firmware rollback boundary",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["pre_task_check"]["active_rules"]["active_rules"][1]["name"] == "firmware"
    assert "Read board map." in result["domain_contract"]["documents"][0]["content"]
    assert result["domain_contract"]["validators"][0]["name"] == "firmware_validator"


def test_session_start_can_auto_discover_domain_contract(local_session_start_root):
    plan = local_session_start_root / "PLAN.md"
    plan.write_text(
        "> **最後更新**: 2026-03-24\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    (local_session_start_root / "rules" / "firmware").mkdir(parents=True)
    (local_session_start_root / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    (local_session_start_root / "contract.yaml").write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = build_session_start_context(
        project_root=local_session_start_root,
        plan_path=plan,
        rules="common,firmware",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Validate firmware rollback boundary",
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["contract_resolution"]["source"] == "discovery"
    assert result["resolved_contract_file"].replace("\\", "/").endswith("/tests/_tmp_session_start/contract.yaml")
    output = format_human_result(result)
    assert "contract=firmware/medium" in output or "contract=usb-hub-firmware/medium" in output
