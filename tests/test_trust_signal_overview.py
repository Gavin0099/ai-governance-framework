import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.trust_signal_overview import (
    assess_trust_signal_overview,
    format_human_result,
    format_markdown_result,
    main,
)


def _write_contract(repo_root: Path, contract_text: str, *, validator_names: list[str] | None = None) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "contract.yaml").write_text(contract_text, encoding="utf-8")
    if validator_names:
        validators_root = repo_root / "validators"
        validators_root.mkdir(parents=True, exist_ok=True)
        for name in validator_names:
            (validators_root / name).write_text("# validator\n", encoding="utf-8")


def test_trust_signal_overview_passes_on_repo_root():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["quickstart"]["ok"] is True
    assert result["examples"]["ok"] is True
    assert result["release"]["ok"] is True
    assert result["auditor"]["ok"] is True


def test_trust_signal_overview_can_include_external_contract_policies(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "kernel-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: kernel-driver-contract",
                "domain: kernel-driver",
                "validators:",
                "  - validators/irql.py",
                "hard_stop_rules:",
                "  - KD-002",
            ]
        ),
        validator_names=["irql.py"],
    )

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )

    assert result["ok"] is True
    assert result["external_contract_policy"]["ok"] is True
    assert result["external_contract_policy"]["entries"][0]["enforcement_profile"] == "mixed"


def test_trust_signal_overview_human_output_is_summary_first():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    output = format_human_result(result)

    assert "[trust_signal_overview]" in output
    assert "summary=ok=True | quickstart=True | examples=True | release=True | auditor=True | contract=firmware/medium" in output
    assert "release_version=v1.0.0-alpha" in output


def test_trust_signal_overview_human_output_can_surface_external_contracts(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "ic-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: ic-verification-contract",
                "domain: ic-verification",
                "validators:",
                "  - validators/signal_map.py",
                "hard_stop_rules:",
                "  - ICV-001",
            ]
        ),
        validator_names=["signal_map.py"],
    )

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )
    output = format_human_result(result)

    assert "external_contracts=True" in output
    assert "[external_contract_policies]" in output
    assert "profile=mixed" in output
    assert "hard_stop_rules=ICV-001" in output


def test_trust_signal_overview_markdown_output_is_dashboard_like():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    output = format_markdown_result(result)

    assert "# Trust Signal Overview" in output
    assert "| Signal | OK | Detail |" in output
    assert "| Quickstart | `True` | contract=`firmware/medium` |" in output


def test_trust_signal_overview_markdown_can_include_external_contracts(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "firmware-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: firmware-contract",
                "domain: firmware",
                "validators:",
                "  - validators/isr.py",
                "hard_stop_rules:",
                "  - HUB-004",
            ]
        ),
        validator_names=["isr.py"],
    )

    result = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )
    output = format_markdown_result(result)

    assert "| External Contracts | `True` | repos=`1` mixed=`1/1 mixed` |" in output
    assert "## External Contract Policies" in output
    assert "`HUB-004`" in output


def test_trust_signal_overview_can_write_output_file(monkeypatch, tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    output_path = tmp_path / "trust_signal_overview.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trust_signal_overview.py",
            "--project-root",
            str(project_root),
            "--plan",
            str(project_root / "PLAN.md"),
            "--release-version",
            "v1.0.0-alpha",
            "--contract",
            str(contract_file),
            "--format",
            "human",
            "--output",
            str(output_path),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    assert output_path.is_file()
    assert "[trust_signal_overview]" in output_path.read_text(encoding="utf-8")
