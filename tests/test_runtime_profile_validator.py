from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from governance_tools.runtime_profile_validator import (
    validate_runtime_profile_paths,
    validate_runtime_profile_text,
)


EXAMPLE_PROFILE = Path("examples/runtime-profiles/governed-coding-agent.yaml")
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "runtime_profiles"


VALID_PROFILE = """
profile_id: test-agent
profile_version: 0.1
profile_authority: reviewer_draft
claim_ceiling:
  - reviewer-facing runtime surface profile only
  - no runtime enforcement claim
not_claimed:
  - runtime enforcement
  - authority correctness validation
  - evidence truthfulness validation
  - semantic correctness validation
surfaces:
  - id: terminal
    type: execution_surface
    boundary_class: load_bearing_boundary_required
    max_side_effect: filesystem_process_side_effect
    controls:
      - workspace sandbox
    control_claim_ceiling: containment claim requires OS-level enforcement evidence
evidence_refs:
  - artifact: docs/governance/agent-runtime-profile.md
    result: PASS
"""


def test_passes_valid_runtime_profile() -> None:
    result = validate_runtime_profile_text(VALID_PROFILE)

    assert result["ok"] is True
    assert result["signals"]["surface_count"] == 1
    assert result["signals"]["evidence_ref_count"] == 1


def test_fails_missing_required_top_level_field() -> None:
    result = validate_runtime_profile_text(VALID_PROFILE.replace("profile_authority: reviewer_draft\n", ""))

    assert result["ok"] is False
    assert {"code": "missing_required_field", "field": "profile_authority"} in result["errors"]


def test_fails_missing_surface_field() -> None:
    result = validate_runtime_profile_text(VALID_PROFILE.replace("    max_side_effect: filesystem_process_side_effect\n", ""))

    assert result["ok"] is False
    assert {
        "code": "missing_required_surface_field",
        "field": "surfaces[0].max_side_effect",
    } in result["errors"]


def test_fails_placeholder_evidence_ref() -> None:
    text = VALID_PROFILE.replace(
        "  - artifact: docs/governance/agent-runtime-profile.md\n    result: PASS\n",
        "  - artifact: none\n    result: PASS\n",
    )

    result = validate_runtime_profile_text(text)

    assert result["ok"] is False
    assert {"code": "missing_command_or_artifact", "field": "evidence_refs[0]"} in result["errors"]


def test_fails_evidence_ref_missing_result() -> None:
    text = VALID_PROFILE.replace("    result: PASS\n", "")

    result = validate_runtime_profile_text(text)

    assert result["ok"] is False
    assert {"code": "missing_or_invalid_result", "field": "evidence_refs[0]"} in result["errors"]


def test_fails_high_risk_claim_without_downgrade() -> None:
    text = """
profile_id: test-agent
profile_version: 0.1
profile_authority: reviewer_draft
claim_ceiling:
  - runtime enforced
not_claimed:
  - evidence truthfulness validation
surfaces:
  - id: terminal
    type: execution_surface
    boundary_class: load_bearing_boundary_required
    max_side_effect: filesystem_process_side_effect
    controls:
      - workspace sandbox
    control_claim_ceiling: operator control
evidence_refs:
  - artifact: docs/governance/agent-runtime-profile.md
    result: PASS
"""

    result = validate_runtime_profile_text(text)

    assert result["ok"] is False
    assert any(
        error["code"] == "high_risk_runtime_claim_without_downgrade"
        for error in result["errors"]
    )


def test_example_profile_passes() -> None:
    result = validate_runtime_profile_paths([EXAMPLE_PROFILE])

    assert result["ok"] is True
    assert result["total_files"] == 1


def test_validates_representative_fixture_corpus() -> None:
    expectations = {
        "valid_minimal.yaml": True,
        "valid_multi_surface.yaml": True,
        "invalid_missing_profile_authority.yaml": False,
        "invalid_missing_surface_field.yaml": False,
        "invalid_placeholder_evidence.yaml": False,
        "invalid_missing_evidence_result.yaml": False,
        "invalid_high_risk_without_downgrade.yaml": False,
        "valid_high_risk_with_downgrade.yaml": True,
    }

    for name, expected_ok in expectations.items():
        result = validate_runtime_profile_paths([FIXTURE_ROOT / name])
        assert result["ok"] is expected_ok, name


def test_cli_passes_example_profile() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.runtime_profile_validator",
            str(EXAMPLE_PROFILE),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert '"ok": true' in completed.stdout
    assert '"total_files": 1' in completed.stdout


def test_cli_directory_mode_scans_yaml() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.runtime_profile_validator",
            "examples/runtime-profiles",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert '"total_files": 1' in completed.stdout


def test_batch_validation_summarizes_fixture_directory() -> None:
    result = validate_runtime_profile_paths([FIXTURE_ROOT])

    assert result["ok"] is False
    assert result["total_files"] == 8
    assert result["valid_files"] == 3
    assert result["invalid_files"] == 5
    assert result["path_errors"] == []


def test_cli_fails_for_fixture_directory_with_invalid_examples() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.runtime_profile_validator",
            str(FIXTURE_ROOT),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert '"total_files": 8' in completed.stdout
    assert '"invalid_files": 5' in completed.stdout
