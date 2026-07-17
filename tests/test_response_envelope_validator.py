from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from governance_tools.response_envelope_validator import (
    validate_response_envelope_paths,
    validate_response_envelope_text,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "response_envelopes"
QUALITY_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "response_quality"


def test_passes_minimal_valid_response_envelope() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is True
    assert result["signals"]["has_valid_evidence_ref"] is True
    assert result["signals"]["placeholder_evidence_entry_count"] == 0


def test_fails_when_required_field_missing() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert "missing_required_field:task_authority" in result["findings"]


def test_fails_when_evidence_refs_empty() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert "evidence_refs_empty" in result["findings"]


def test_fails_when_evidence_refs_contains_placeholder_only() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - see above
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert "evidence_refs_placeholder_only" in result["findings"]
    assert "placeholder_evidence_ref:see above" in result["findings"]


def test_fails_on_high_risk_wording_without_support() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - runtime enforced
not_claimed:
evidence_refs:
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert "high_risk_authority_wording_without_support" in result["findings"]


def test_allows_high_risk_wording_when_downgraded() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - runtime enforced wording discussed only
not_claimed:
  - runtime enforcement
summary: NOT CLAIMED
evidence_refs:
  - none
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert "high_risk_authority_wording_without_support" not in result["findings"]
    assert "evidence_refs_placeholder_only" in result["findings"]


def test_allows_high_risk_wording_when_supported_by_valid_evidence() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - validated structurally
not_claimed:
  - semantic correctness
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is True
    assert "high_risk_authority_wording_without_support" not in result["findings"]


def test_fails_when_evidence_ref_missing_result() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
"""

    result = validate_response_envelope_text(text)

    assert result["ok"] is False
    assert result["signals"]["invalid_evidence_shape_count"] == 1
    assert any(
        finding.startswith("invalid_evidence_ref_shape:")
        for finding in result["findings"]
    )


def test_validates_representative_fixture_corpus() -> None:
    expectations = {
        "valid_minimal.md": True,
        "invalid_missing_mode_source.md": False,
        "invalid_placeholder_evidence.md": False,
        "invalid_high_risk_without_downgrade.md": False,
        "invalid_missing_evidence_result.md": False,
        "valid_high_risk_with_not_claimed.md": True,
    }

    for name, expected_ok in expectations.items():
        result = validate_response_envelope_text((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
        assert result["ok"] is expected_ok, name


def test_cli_passes_for_valid_fixture() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(FIXTURE_ROOT / "valid_minimal.md"),
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


def test_cli_fails_for_invalid_fixture() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(FIXTURE_ROOT / "invalid_placeholder_evidence.md"),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "evidence_refs_placeholder_only" in completed.stdout


def test_batch_validation_summarizes_fixture_directory() -> None:
    result = validate_response_envelope_paths([FIXTURE_ROOT])

    assert result["ok"] is False
    assert result["total_files"] == 6
    assert result["valid_files"] == 2
    assert result["invalid_files"] == 4
    assert result["path_errors"] == []


def test_cli_passes_for_multiple_valid_files() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(FIXTURE_ROOT / "valid_minimal.md"),
            str(FIXTURE_ROOT / "valid_high_risk_with_not_claimed.md"),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert '"ok": true' in completed.stdout
    assert '"total_files": 2' in completed.stdout


def test_quality_check_off_by_default_for_quality_invalid_fixtures() -> None:
    for name in (
        "invalid_quality_missing_next_action.md",
        "invalid_quality_after_evidence.md",
        "invalid_quality_placeholder_conclusion.md",
    ):
        text = (QUALITY_FIXTURE_ROOT / name).read_text(encoding="utf-8")
        result = validate_response_envelope_text(text)
        assert result["ok"] is True, name
        assert not any(
            finding.startswith("quality_") for finding in result["findings"]
        ), name
        assert "quality_fields_present" not in result["signals"], name


def test_quality_check_passes_english_and_chinese_fixtures() -> None:
    for name in ("valid_quality_minimal.md", "valid_quality_zh.md"):
        text = (QUALITY_FIXTURE_ROOT / name).read_text(encoding="utf-8")
        result = validate_response_envelope_text(text, check_quality=True)
        assert result["ok"] is True, name
        assert result["signals"]["quality_fields_present"] == [
            "conclusion",
            "recommended_action",
            "next_action",
        ], name
        assert result["signals"]["quality_ordered_before_evidence"] is True, name


def test_quality_check_flags_each_missing_field() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    for field in ("conclusion", "recommended_action", "next_action"):
        assert f"quality_missing_field:{field}" in result["findings"]


def test_quality_check_flags_placeholder_conclusion_and_recommended_action() -> None:
    text = (
        QUALITY_FIXTURE_ROOT / "invalid_quality_placeholder_conclusion.md"
    ).read_text(encoding="utf-8")

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    assert "quality_empty_field:conclusion" in result["findings"]
    assert "quality_empty_field:recommended_action" in result["findings"]
    assert "quality_empty_field:next_action" not in result["findings"]


def test_quality_check_allows_none_next_action_only() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion: Done and reviewed.
recommended_action: can merge — focused tests pass
next_action: none
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is True


def test_quality_check_flags_field_positioned_after_evidence() -> None:
    text = (QUALITY_FIXTURE_ROOT / "invalid_quality_after_evidence.md").read_text(
        encoding="utf-8"
    )

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    assert "quality_field_after_evidence:conclusion" in result["findings"]
    assert result["signals"]["quality_ordered_before_evidence"] is False


def test_quality_check_rejects_empty_label_satisfied_by_duplicate_after_evidence() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion:
recommended_action: needs review — validator change awaits human review
next_action: run the focused pytest module before commit
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
conclusion: The real content only appears after the technical evidence.
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    assert "quality_duplicate_field:conclusion" in result["findings"]


def test_quality_check_flags_list_style_placeholder_value() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion:
  - TBD
recommended_action: needs review — validator change awaits human review
next_action: run the focused pytest module before commit
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    assert "quality_empty_field:conclusion" in result["findings"]


def test_quality_check_flags_single_empty_label_before_evidence() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion:
recommended_action: needs review — validator change awaits human review
next_action: run the focused pytest module before commit
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is False
    assert "quality_empty_field:conclusion" in result["findings"]


def test_quality_check_accepts_list_style_real_content() -> None:
    text = """
mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion:
  - 本次切片已完成，預設行為未改變。
recommended_action: needs review — 驗證器變更需人工審查
next_action: 提交前先跑 focused pytest 模組
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: pytest
    result: PASS
"""

    result = validate_response_envelope_text(text, check_quality=True)

    assert result["ok"] is True


def test_cli_quality_flag_fails_quality_invalid_fixture() -> None:
    fixture = QUALITY_FIXTURE_ROOT / "invalid_quality_missing_next_action.md"

    without_flag = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(fixture),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    with_flag = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(fixture),
            "--format",
            "json",
            "--check-response-quality",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert without_flag.returncode == 0
    assert with_flag.returncode == 1
    assert "quality_missing_field" in with_flag.stdout


def test_quality_batch_validation_over_quality_fixture_directory() -> None:
    result = validate_response_envelope_paths(
        [QUALITY_FIXTURE_ROOT], check_quality=True
    )

    assert result["ok"] is False
    assert result["total_files"] == 5
    assert result["valid_files"] == 2
    assert result["invalid_files"] == 3


def test_cli_fails_for_fixture_directory_with_invalid_examples() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.response_envelope_validator",
            str(FIXTURE_ROOT),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert '"invalid_files": 4' in completed.stdout
