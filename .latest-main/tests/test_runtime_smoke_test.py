import json
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.smoke_test import format_human_envelope
from runtime_hooks.smoke_test import run_shared_smoke
from runtime_hooks.smoke_test import run_smoke
from runtime_hooks.smoke_test import write_outputs


def test_smoke_test_claude_pre_runs():
    envelope = run_smoke("claude_code", "pre_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "pre_task"


def test_smoke_test_claude_session_start_runs():
    envelope = run_smoke("claude_code", "session_start")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "session_start"


def test_smoke_test_codex_post_runs_and_creates_snapshot():
    envelope = run_smoke("codex", "post_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "post_task"
    assert envelope["result"]["snapshot"] is not None


def test_smoke_test_gemini_post_runs():
    envelope = run_smoke("gemini", "post_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["metadata"]["harness"] == "gemini"


def test_smoke_test_codex_session_start_runs():
    envelope = run_smoke("codex", "session_start")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "session_start"


def test_smoke_test_session_start_shared_runs():
    envelope = run_shared_smoke("session_start")
    assert envelope["result"]["ok"] is True
    assert envelope["event_type"] == "session_start"
    assert envelope["result"]["suggested_agent"] == "python-agent"


def test_smoke_test_session_start_human_output_surfaces_handoff_summary():
    envelope = run_shared_smoke("session_start")
    output = format_human_envelope(envelope)
    assert "event_type=session_start" in output
    assert "rules=common" in output
    assert "expected_validators=architecture_drift_checker,public_api_diff_checker" in output
    assert "required_evidence=architecture-review,public-api-review" in output


def test_smoke_test_session_start_can_use_explicit_contract():
    contract_file = Path("examples/usb-hub-contract/contract.yaml").resolve()
    envelope = run_shared_smoke("session_start", contract_file=contract_file)
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["contract_resolution"]["source"] == "explicit"
    assert envelope["result"]["domain_contract"]["name"] == "usb-hub-firmware-contract"


def test_smoke_test_session_start_can_infer_project_root_and_plan_from_contract(tmp_path):
    contract_file = tmp_path / "contract.yaml"
    plan_path = tmp_path / "PLAN.md"
    contract_file.write_text("name: local-contract\n", encoding="utf-8")
    plan_path.write_text(
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Validate runtime smoke overrides\n",
        encoding="utf-8",
    )

    envelope = run_shared_smoke("session_start", contract_file=contract_file)

    assert envelope["result"]["ok"] is True
    assert envelope["result"]["project_root"] == str(tmp_path.resolve())
    assert envelope["result"]["contract_resolution"]["source"] == "explicit"


def test_smoke_test_adapter_session_start_human_output_uses_normalized_event_type():
    envelope = run_smoke("claude_code", "session_start")
    output = format_human_envelope(envelope, harness="claude_code")
    assert "harness=claude_code" in output
    assert "event_type=session_start" in output
    assert "suggested_agent=python-agent" in output


def test_smoke_test_pre_task_can_use_explicit_contract_and_surface_it_in_output():
    contract_file = Path("examples/usb-hub-contract/contract.yaml").resolve()
    envelope = run_smoke("claude_code", "pre_task", contract_file=contract_file)
    output = format_human_envelope(envelope, harness="claude_code")
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["contract_resolution"]["source"] == "explicit"
    assert "contract_source=explicit" in output
    assert "domain_contract=usb-hub-firmware-contract" in output


def test_smoke_test_post_task_can_use_checks_file_with_usb_hub_contract(tmp_path):
    contract_file = Path("examples/usb-hub-contract/contract.yaml").resolve()
    response_file = Path("examples/usb-hub-contract/fixtures/post_task_response.txt").resolve()
    checks_file = Path("examples/usb-hub-contract/fixtures/interrupt_regression.checks.json").resolve()

    envelope = run_shared_smoke(
        "post_task",
        payload_file=Path("runtime_hooks/examples/shared/post_task.shared.json"),
        project_root=tmp_path,
        contract_file=contract_file,
        response_file=response_file,
        checks_file=checks_file,
    )

    assert envelope["result"]["ok"] is True
    assert envelope["result"]["contract_resolution"]["source"] == "explicit"
    assert any("domain-validator:interrupt_safety_validator" in warning for warning in envelope["result"]["warnings"])
    assert envelope["result"]["domain_validator_results"][0]["name"] == "interrupt_safety_validator"
    assert "HUB-ISR-001" in envelope["result"]["domain_validator_results"][0]["warnings"][0]


def test_smoke_test_handoff_summary_can_be_written(tmp_path):
    envelope = run_shared_smoke("session_start")
    output_file = tmp_path / "session_start.txt"
    json_output = tmp_path / "session_start.json"
    write_outputs(
        envelope=envelope,
        rendered=format_human_envelope(envelope),
        output=output_file,
        json_output=json_output,
    )
    assert output_file.exists()
    assert json_output.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "event_type=session_start" in content
    envelope_payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert envelope_payload["event_type"] == "session_start"
