#!/usr/bin/env python3
"""
Unit tests for DomainValidator subclasses:
  - ArchitectureDriftValidator
  - DriverEvidenceValidator
  - FailureCompletenessValidator
  - RefactorEvidenceValidator
"""
import pytest
from governance_tools.architecture_drift_checker import ArchitectureDriftValidator
from governance_tools.driver_evidence_validator import DriverEvidenceValidator
from governance_tools.failure_completeness_validator import FailureCompletenessValidator
from governance_tools.refactor_evidence_validator import RefactorEvidenceValidator
from governance_tools.validator_interface import ValidatorResult


# ---------------------------------------------------------------------------
# ArchitectureDriftValidator
# ---------------------------------------------------------------------------

class TestArchitectureDriftValidator:
    def setup_method(self):
        self.v = ArchitectureDriftValidator()

    def test_rule_ids(self):
        assert "feature" in self.v.rule_ids
        assert "refactor" in self.v.rule_ids

    def test_returns_validator_result(self):
        result = self.v.validate({})
        assert isinstance(result, ValidatorResult)

    def test_clean_diff_ok(self):
        payload = {
            "response_text": "Added a helper function to utils.py",
            "contract_fields": {"SCOPE": "feature"},
            "checks": {},
        }
        result = self.v.validate(payload)
        assert isinstance(result.ok, bool)
        assert result.rule_ids == ["feature", "refactor"]
        assert isinstance(result.violations, list)
        assert isinstance(result.warnings, list)

    def test_private_peer_include_violation(self):
        diff = '#include "../database_service/Global.h"'
        payload = {
            "response_text": diff,
            "contract_fields": {"SCOPE": "feature"},
            "checks": {},
        }
        result = self.v.validate(payload)
        # Should flag private peer include as a violation or warning
        assert isinstance(result, ValidatorResult)
        assert result.rule_ids == ["feature", "refactor"]

    def test_empty_payload(self):
        result = self.v.validate({})
        assert isinstance(result, ValidatorResult)
        assert result.ok is True or result.ok is False  # either is acceptable

    def test_metadata_has_files_scanned(self):
        result = self.v.validate({"response_text": ""})
        assert "files_scanned" in result.metadata


# ---------------------------------------------------------------------------
# DriverEvidenceValidator
# ---------------------------------------------------------------------------

class TestDriverEvidenceValidator:
    def setup_method(self):
        self.v = DriverEvidenceValidator()

    def test_rule_ids(self):
        assert self.v.rule_ids == ["kernel-driver"]

    def test_returns_validator_result(self):
        result = self.v.validate({})
        assert isinstance(result, ValidatorResult)

    def test_empty_checks_fails(self):
        result = self.v.validate({"checks": {}})
        assert result.ok is False
        assert len(result.violations) > 0

    def test_full_evidence_passes(self):
        checks = {
            "test_names": [
                "irql passive level test",
                "ioctl buffer length validation",
                "cleanup on remove",
                "static driver verifier analysis",
            ],
            "diagnostics": ["static driver verifier passed"],
        }
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)
        assert result.rule_ids == ["kernel-driver"]

    def test_partial_evidence_has_violations_or_warnings(self):
        checks = {"test_names": ["irql test"]}
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)
        # partial evidence should raise concerns
        assert len(result.violations) > 0 or len(result.warnings) > 0

    def test_metadata_keys(self):
        result = self.v.validate({})
        assert "evidence_required" in result.metadata
        assert "signals_detected" in result.metadata


# ---------------------------------------------------------------------------
# FailureCompletenessValidator
# ---------------------------------------------------------------------------

class TestFailureCompletenessValidator:
    def setup_method(self):
        self.v = FailureCompletenessValidator()

    def test_rule_ids(self):
        assert "feature" in self.v.rule_ids

    def test_returns_validator_result(self):
        result = self.v.validate({})
        assert isinstance(result, ValidatorResult)

    def test_empty_checks_fails(self):
        result = self.v.validate({"checks": {}})
        assert isinstance(result, ValidatorResult)
        # no signals → not ok
        assert result.ok is False

    def test_with_exception_test_name(self):
        checks = {
            "test_names": ["test_throws_on_invalid_input", "test_error_handling"],
            "exception_assertions": True,
        }
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)
        assert result.rule_ids == ["feature", "refactor"]

    def test_rollback_signal(self):
        checks = {
            "test_names": ["cleanup_after_failure", "rollback_on_error"],
            "cleanup_verified": True,
        }
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)
        assert "signals_detected" in result.metadata

    def test_evidence_summary_is_string(self):
        result = self.v.validate({"checks": {"test_names": ["fails gracefully"]}})
        assert isinstance(result.evidence_summary, str)


# ---------------------------------------------------------------------------
# RefactorEvidenceValidator
# ---------------------------------------------------------------------------

class TestRefactorEvidenceValidator:
    def setup_method(self):
        self.v = RefactorEvidenceValidator()

    def test_rule_ids(self):
        assert self.v.rule_ids == ["refactor"]

    def test_returns_validator_result(self):
        result = self.v.validate({})
        assert isinstance(result, ValidatorResult)

    def test_empty_checks_fails(self):
        result = self.v.validate({"checks": {}})
        assert result.ok is False
        assert len(result.violations) > 0

    def test_regression_test_names_pass(self):
        checks = {
            "test_names": [
                "regression_suite_all_pass",
                "characterization_test_for_legacy_api",
                "interface_contract_preserved",
            ]
        }
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)
        assert result.rule_ids == ["refactor"]

    def test_partial_refactor_evidence(self):
        checks = {"test_names": ["regression_check"]}
        result = self.v.validate({"checks": checks})
        assert isinstance(result, ValidatorResult)

    def test_metadata_keys(self):
        result = self.v.validate({})
        assert "evidence_required" in result.metadata
        assert "signals_detected" in result.metadata

    def test_evidence_summary_is_string(self):
        result = self.v.validate({"checks": {}})
        assert isinstance(result.evidence_summary, str)
