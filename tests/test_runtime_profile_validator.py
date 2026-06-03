from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from governance_tools.runtime_profile_validator import (
    validate_runtime_profile_paths,
    validate_runtime_profile_text,
)


EXAMPLE_PROFILE = Path("examples/runtime-profiles/governed-coding-agent.yaml")


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
