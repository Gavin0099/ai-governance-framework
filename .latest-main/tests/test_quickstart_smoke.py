import sys
import uuid
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.quickstart_smoke import format_human_result, run_quickstart_smoke


def _make_workspace_temp_repo() -> Path:
    temp_root = Path("scratch_quickstart_smoke")
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_path = temp_root / uuid.uuid4().hex
    temp_path.mkdir(parents=True, exist_ok=False)
    return temp_path.resolve()


def test_quickstart_smoke_runs_without_contract_on_temp_repo():
    tmp_path = _make_workspace_temp_repo()
    plan = tmp_path / "PLAN.md"
    plan.write_text(
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Quickstart validation\n",
        encoding="utf-8",
    )

    result = run_quickstart_smoke(
        project_root=tmp_path,
        plan_path=plan,
    )

    assert result["ok"] is True
    assert result["pre_task_ok"] is True
    assert result["session_start_ok"] is True
    assert result["contract_path"] is None
    assert result["contract_mode"] == "repo-default"


def test_quickstart_smoke_can_use_usb_hub_contract_example():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = run_quickstart_smoke(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        contract_file=contract_file,
        task_text="Validate quickstart contract path",
    )

    assert result["ok"] is True
    assert result["pre_task_ok"] is True
    assert result["session_start_ok"] is True
    assert result["contract_mode"] == "explicit"
    assert result["contract_context"]["domain"] == "firmware"

    output = format_human_result(result)
    assert "[quickstart_smoke]" in output
    assert "contract=firmware/medium" in output


def test_quickstart_smoke_human_output_explains_missing_contract_path():
    tmp_path = _make_workspace_temp_repo()
    plan = tmp_path / "PLAN.md"
    plan.write_text(
        f"> **Updated**: {_date.today().isoformat()}\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Quickstart validation\n",
        encoding="utf-8",
    )

    result = run_quickstart_smoke(
        project_root=tmp_path,
        plan_path=plan,
    )

    output = format_human_result(result)
    assert "contract_path=None" in output
    assert "contract_mode=repo-default" in output
    assert "contract_note=no explicit --contract provided; using repo-local governance defaults" in output
