import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.trust_signal_overview import assess_trust_signal_overview, format_human_result


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
