"""
Unit tests for governance_tools/violation_triage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.violation_triage import (
    CI_BLOCKING_SEVERITIES,
    SCHEMA_VERSION,
    CIGateResult,
    TriageEntry,
    TriageReport,
    Violation,
    evaluate_ci_gate,
    format_human_gate,
    from_contract_validator_json,
    from_governance_auditor_json,
    merge_triage,
    _parse_rule_id,
    _parse_location,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _violation(
    rule_id: str = "LANG-required",
    severity: str = "CRITICAL",
    category: str = "contract",
    message: str = "LANG field is required",
    location: str = "Governance Contract / LANG",
    triage_type: str | None = None,
    root_cause: str | None = None,
    action: str | None = None,
) -> Violation:
    return Violation(
        id="test-001",
        rule_id=rule_id,
        severity=severity,
        category=category,
        message=message,
        location=location,
        triage=TriageEntry(type=triage_type, root_cause=root_cause, action=action),
    )


def _report(*violations: Violation, tool: str = "contract_validator") -> TriageReport:
    return TriageReport(
        schema_version=SCHEMA_VERSION,
        tool=tool,
        generated_at="2026-03-17T00:00:00+00:00",
        context={},
        violations=list(violations),
    )


# ── TriageEntry ───────────────────────────────────────────────────────────────

class TestTriageEntry:
    def test_defaults(self):
        e = TriageEntry()
        assert e.type is None
        assert e.root_cause is None
        assert e.action is None
        assert e.notes == ""
        assert e.reviewed_by is None
        assert e.reviewed_at is None

    def test_explicit_values(self):
        e = TriageEntry(type="TP", root_cause="contract", action="fix_rule", notes="confirmed")
        assert e.type == "TP"
        assert e.root_cause == "contract"
        assert e.action == "fix_rule"
        assert e.notes == "confirmed"


# ── Violation.fingerprint ─────────────────────────────────────────────────────

class TestViolationFingerprint:
    def test_stable_across_instances(self):
        v1 = _violation(rule_id="LANG-required", location="Contract / LANG")
        v2 = _violation(rule_id="LANG-required", location="Contract / LANG")
        assert v1.fingerprint() == v2.fingerprint()

    def test_different_location_differs(self):
        v1 = _violation(rule_id="LANG-required", location="loc-a")
        v2 = _violation(rule_id="LANG-required", location="loc-b")
        assert v1.fingerprint() != v2.fingerprint()

    def test_different_rule_id_differs(self):
        v1 = _violation(rule_id="LANG-required", location="loc")
        v2 = _violation(rule_id="LEVEL-required", location="loc")
        assert v1.fingerprint() != v2.fingerprint()

    def test_message_change_does_not_change_fingerprint(self):
        v1 = _violation(rule_id="LANG-required", location="loc", message="old message")
        v2 = _violation(rule_id="LANG-required", location="loc", message="updated message")
        assert v1.fingerprint() == v2.fingerprint()

    def test_returns_8_char_hex(self):
        v = _violation()
        fp = v.fingerprint()
        assert len(fp) == 8
        assert all(c in "0123456789abcdef" for c in fp)


# ── TriageReport.stats ────────────────────────────────────────────────────────

class TestTriageReportStats:
    def test_empty(self):
        stats = _report().stats()
        assert stats["total"] == 0
        assert stats["unreviewed_critical"] == 0
        assert stats["by_type"] == {"TP": 0, "FP": 0, "FN": 0, "unreviewed": 0}

    def test_all_triage_types(self):
        report = _report(
            _violation(severity="CRITICAL", triage_type="TP"),
            _violation(rule_id="r2", severity="CRITICAL", triage_type="FP"),
            _violation(rule_id="r3", severity="CRITICAL", triage_type="FN"),
            _violation(rule_id="r4", severity="CRITICAL"),  # unreviewed
        )
        stats = report.stats()
        assert stats["total"] == 4
        assert stats["by_type"]["TP"] == 1
        assert stats["by_type"]["FP"] == 1
        assert stats["by_type"]["FN"] == 1
        assert stats["by_type"]["unreviewed"] == 1

    def test_unreviewed_critical_counts_only_critical(self):
        report = _report(
            _violation(severity="CRITICAL"),         # unreviewed critical
            _violation(rule_id="r2", severity="WARNING"),  # unreviewed warning
        )
        stats = report.stats()
        assert stats["unreviewed_critical"] == 1  # WARNING excluded

    def test_reviewed_fp_not_counted_as_unreviewed_critical(self):
        report = _report(_violation(severity="CRITICAL", triage_type="FP"))
        assert report.stats()["unreviewed_critical"] == 0

    def test_by_severity_counts(self):
        report = _report(
            _violation(severity="CRITICAL"),
            _violation(rule_id="r2", severity="CRITICAL"),
            _violation(rule_id="r3", severity="WARNING"),
        )
        by_sev = report.stats()["by_severity"]
        assert by_sev["CRITICAL"] == 2
        assert by_sev["WARNING"] == 1


# ── TriageReport serialization round-trip ─────────────────────────────────────

class TestTriageReportSerialization:
    def test_round_trip_empty(self):
        original = _report()
        restored = TriageReport.from_dict(original.to_dict())
        assert restored.tool == original.tool
        assert restored.schema_version == SCHEMA_VERSION
        assert len(restored.violations) == 0

    def test_round_trip_with_triage(self):
        original = _report(
            _violation(
                rule_id="LANG-required",
                triage_type="TP",
                root_cause="contract",
                action="fix_rule",
            )
        )
        data = original.to_dict()
        restored = TriageReport.from_dict(data)
        v = restored.violations[0]
        assert v.rule_id == "LANG-required"
        assert v.triage.type == "TP"
        assert v.triage.root_cause == "contract"
        assert v.triage.action == "fix_rule"

    def test_round_trip_unreviewed_triage(self):
        original = _report(_violation())  # triage.type = None
        restored = TriageReport.from_dict(original.to_dict())
        assert restored.violations[0].triage.type is None

    def test_to_dict_includes_stats(self):
        d = _report(_violation()).to_dict()
        assert "stats" in d
        assert d["stats"]["total"] == 1

    def test_from_dict_handles_missing_triage_key(self):
        data = {
            "schema_version": "1.0",
            "tool": "cv",
            "generated_at": "",
            "context": {},
            "violations": [
                {"id": "x-001", "rule_id": "r", "severity": "CRITICAL",
                 "category": "contract", "message": "m"}
                # no "triage" key
            ],
        }
        report = TriageReport.from_dict(data)
        assert report.violations[0].triage.type is None


# ── _parse_rule_id ────────────────────────────────────────────────────────────

class TestParseRuleId:
    @pytest.mark.parametrize("message,expected", [
        ("LANG field is required", "LANG-required"),
        ("LANG invalid: 'X'. Allowed: ...", "LANG-invalid"),
        ("LEVEL field is required", "LEVEL-required"),
        ("LEVEL invalid: 'L9'. Allowed: ...", "LEVEL-invalid"),
        ("SCOPE field is required", "SCOPE-required"),
        ("SCOPE invalid: 'x'.", "SCOPE-invalid"),
        ("LOADED field is required", "LOADED-required"),
        ("LOADED missing required documents: ['SYSTEM_PROMPT']", "LOADED-missing"),
        ("CONTEXT field is required", "CONTEXT-required"),
        ("PRESSURE field is required", "PRESSURE-required"),
        ("PRESSURE invalid: 'X'.", "PRESSURE-invalid"),
        ("RULES field is required", "RULES-required"),
        ("RULES contains unknown rule pack(s): ['x']", "RULES-unknown"),
        ("RISK invalid: 'x'. Allowed:", "RISK-invalid"),
        ("OVERSIGHT invalid: 'x'.", "OVERSIGHT-invalid"),
        ("MEMORY_MODE invalid: 'x'.", "MEMORY_MODE-invalid"),
        ("PLAN missing; recommended to bind", "PLAN-missing"),
        ("[Governance Contract] block not found", "CONTRACT-missing"),
        ("required governance doc is missing", "GOV-doc-missing"),
        ("required runtime enforcement file is missing", "GOV-runtime-missing"),
        ("rule pack directory or markdown content is missing", "GOV-rule-pack-missing"),
        ("workflow does not invoke shared runtime enforcement script", "GOV-workflow-missing"),
        ("build-boundary rule is not aligned across constitution", "GOV-alignment-build-boundary"),
        ("refactor rule pack is incomplete", "GOV-alignment-refactor-incomplete"),
    ])
    def test_known_patterns(self, message, expected):
        assert _parse_rule_id(message) == expected

    def test_fallback_slugifies(self):
        result = _parse_rule_id("some completely unknown error text")
        assert len(result) > 0
        assert "-" in result or result == "unknown"

    def test_empty_string_returns_unknown(self):
        assert _parse_rule_id("") == "unknown"


# ── _parse_location ───────────────────────────────────────────────────────────

class TestParseLocation:
    @pytest.mark.parametrize("message,expected_prefix", [
        ("LANG field is required", "Governance Contract / LANG"),
        ("LEVEL invalid: 'X'.", "Governance Contract / LEVEL"),
        ("SCOPE field is required", "Governance Contract / SCOPE"),
        ("MEMORY_MODE invalid", "Governance Contract / MEMORY_MODE"),
    ])
    def test_governance_contract_fields(self, message, expected_prefix):
        assert _parse_location(message) == expected_prefix

    def test_governance_doc_path(self):
        loc = _parse_location("required governance doc is missing: governance/SYSTEM_PROMPT.md")
        assert "governance/" in loc

    def test_unknown_returns_empty(self):
        assert _parse_location("some other message") == ""


# ── from_contract_validator_json ──────────────────────────────────────────────

class TestFromContractValidatorJson:
    def test_errors_become_critical(self):
        data = {
            "compliant": False,
            "contract_found": True,
            "errors": ["LANG field is required", "LEVEL invalid: 'X'. Allowed: L0, L1, L2"],
            "warnings": [],
        }
        report = from_contract_validator_json(data)
        assert report.tool == "contract_validator"
        assert len(report.violations) == 2
        assert all(v.severity == "CRITICAL" for v in report.violations)
        assert all(v.category == "contract" for v in report.violations)

    def test_warnings_become_warning_severity(self):
        data = {
            "compliant": True,
            "contract_found": True,
            "errors": [],
            "warnings": ["PLAN missing; recommended to bind responses to PLAN.md"],
        }
        report = from_contract_validator_json(data)
        assert len(report.violations) == 1
        assert report.violations[0].severity == "WARNING"
        assert report.violations[0].rule_id == "PLAN-missing"

    def test_mixed_errors_and_warnings(self):
        data = {
            "errors": ["LANG field is required"],
            "warnings": ["PLAN missing; recommended"],
        }
        report = from_contract_validator_json(data)
        assert len(report.violations) == 2
        severities = {v.severity for v in report.violations}
        assert "CRITICAL" in severities
        assert "WARNING" in severities

    def test_no_violations(self):
        data = {"compliant": True, "contract_found": True, "errors": [], "warnings": []}
        report = from_contract_validator_json(data)
        assert len(report.violations) == 0

    def test_all_triage_start_unreviewed(self):
        data = {"errors": ["LANG field is required"], "warnings": []}
        report = from_contract_validator_json(data)
        assert report.violations[0].triage.type is None

    def test_violation_ids_are_unique(self):
        data = {
            "errors": ["LANG field is required", "LEVEL invalid: 'X'."],
            "warnings": ["PLAN missing"],
        }
        report = from_contract_validator_json(data)
        ids = [v.id for v in report.violations]
        assert len(ids) == len(set(ids))

    def test_location_populated_for_field_errors(self):
        data = {"errors": ["LANG field is required"], "warnings": []}
        report = from_contract_validator_json(data)
        assert "LANG" in report.violations[0].location

    def test_custom_context(self):
        data = {"errors": [], "warnings": []}
        report = from_contract_validator_json(data, context={"file": "my_response.md"})
        assert report.context["file"] == "my_response.md"


# ── from_governance_auditor_json ──────────────────────────────────────────────

class TestFromGovernanceAuditorJson:
    def test_failed_checks_become_violations(self):
        data = {
            "ok": False,
            "project_root": "/tmp/test",
            "checks": [
                {"name": "doc:governance/SYSTEM_PROMPT.md", "ok": False,
                 "detail": "required governance doc is missing"},
                {"name": "runtime:runtime_hooks/core/pre_task_check.py", "ok": False,
                 "detail": "required runtime enforcement file is missing"},
                {"name": "workflow:runtime-enforcement", "ok": True, "detail": ""},
            ],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        assert report.tool == "governance_auditor"
        assert len(report.violations) == 2  # ok=True check excluded

    def test_passed_checks_excluded(self):
        data = {
            "ok": True,
            "project_root": "/tmp",
            "checks": [{"name": "doc:x", "ok": True, "detail": ""}],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        assert len(report.violations) == 0

    def test_category_mapping(self):
        data = {
            "ok": False,
            "project_root": "/tmp",
            "checks": [
                {"name": "doc:gov/x.md", "ok": False, "detail": "d"},
                {"name": "runtime:hooks/y.py", "ok": False, "detail": "d"},
                {"name": "alignment:build-boundary", "ok": False, "detail": "d"},
                {"name": "rule-pack:common", "ok": False, "detail": "d"},
                {"name": "workflow:foo", "ok": False, "detail": "d"},
            ],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        cats = {v.location: v.category for v in report.violations}
        assert cats["doc:gov/x.md"] == "doc"
        assert cats["runtime:hooks/y.py"] == "runtime"
        assert cats["alignment:build-boundary"] == "alignment"
        assert cats["rule-pack:common"] == "contract"
        assert cats["workflow:foo"] == "runtime"

    def test_warnings_become_warning_severity(self):
        data = {
            "ok": True,
            "project_root": "/tmp",
            "checks": [],
            "errors": [],
            "warnings": ["Workflow job name 'runtime-enforcement' was not found"],
        }
        report = from_governance_auditor_json(data)
        assert len(report.violations) == 1
        assert report.violations[0].severity == "WARNING"

    def test_all_violations_are_critical_by_default(self):
        data = {
            "ok": False,
            "project_root": "/tmp",
            "checks": [{"name": "doc:x", "ok": False, "detail": "missing"}],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        assert report.violations[0].severity == "CRITICAL"

    def test_rule_id_uses_auditor_prefix(self):
        data = {
            "ok": False,
            "project_root": "/tmp",
            "checks": [{"name": "doc:governance/AGENT.md", "ok": False, "detail": "missing"}],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        assert report.violations[0].rule_id == "auditor:doc:governance/AGENT.md"


# ── merge_triage ──────────────────────────────────────────────────────────────

class TestMergeTriage:
    def _reviewed_violation(self, rule_id: str, location: str, triage_type: str) -> Violation:
        return Violation(
            id="old-001",
            rule_id=rule_id,
            severity="CRITICAL",
            category="contract",
            message="msg",
            location=location,
            triage=TriageEntry(type=triage_type, root_cause="contract", action="fix_rule",
                               notes="reviewed"),
        )

    def test_preserves_reviewed_annotation(self):
        old_v = self._reviewed_violation("LANG-required", "Contract / LANG", "FP")
        new_v = Violation(
            id="new-001", rule_id="LANG-required", severity="CRITICAL",
            category="contract", message="LANG is required", location="Contract / LANG",
        )
        existing = _report(old_v)
        new = _report(new_v)
        merged = merge_triage(existing, new)
        assert merged.violations[0].triage.type == "FP"
        assert merged.violations[0].triage.notes == "reviewed"

    def test_new_violation_stays_unreviewed(self):
        existing = _report()
        new = _report(_violation())
        merged = merge_triage(existing, new)
        assert merged.violations[0].triage.type is None

    def test_null_triage_in_existing_not_preserved(self):
        """Unreviewed entries in existing file should not propagate to new report."""
        old_v = Violation(
            id="old-001", rule_id="LANG-required", severity="CRITICAL",
            category="contract", message="m", location="l",
            triage=TriageEntry(type=None),  # not yet reviewed
        )
        new_v = Violation(
            id="new-001", rule_id="LANG-required", severity="CRITICAL",
            category="contract", message="m", location="l",
        )
        merged = merge_triage(_report(old_v), _report(new_v))
        assert merged.violations[0].triage.type is None

    def test_uses_new_report_metadata(self):
        existing = _report(tool="contract_validator")
        existing.generated_at = "2026-01-01T00:00:00+00:00"
        new = _report(tool="contract_validator")
        new.generated_at = "2026-03-17T00:00:00+00:00"
        merged = merge_triage(existing, new)
        assert merged.generated_at == new.generated_at

    def test_multiple_violations_matched_independently(self):
        existing = _report(
            self._reviewed_violation("LANG-required", "Contract / LANG", "FP"),
            self._reviewed_violation("LEVEL-required", "Contract / LEVEL", "TP"),
        )
        new = _report(
            Violation(id="n1", rule_id="LANG-required", severity="CRITICAL",
                      category="contract", message="m", location="Contract / LANG"),
            Violation(id="n2", rule_id="LEVEL-required", severity="CRITICAL",
                      category="contract", message="m", location="Contract / LEVEL"),
            Violation(id="n3", rule_id="SCOPE-required", severity="CRITICAL",
                      category="contract", message="m", location="Contract / SCOPE"),
        )
        merged = merge_triage(existing, new)
        assert len(merged.violations) == 3
        by_rule = {v.rule_id: v.triage.type for v in merged.violations}
        assert by_rule["LANG-required"] == "FP"
        assert by_rule["LEVEL-required"] == "TP"
        assert by_rule["SCOPE-required"] is None  # new, unreviewed


# ── evaluate_ci_gate ──────────────────────────────────────────────────────────

class TestEvaluateCIGate:
    def test_empty_report_passes(self):
        result = evaluate_ci_gate(_report())
        assert result.ok
        assert result.exit_code == 0

    def test_tp_fails_with_exit_1(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="TP")))
        assert not result.ok
        assert result.exit_code == 1

    def test_fp_passes(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="FP")))
        assert result.ok
        assert result.exit_code == 0

    def test_fn_fails_with_exit_2(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="FN")))
        assert not result.ok
        assert result.exit_code == 2

    def test_fn_takes_priority_over_tp(self):
        result = evaluate_ci_gate(_report(
            _violation(rule_id="r1", triage_type="FN"),
            _violation(rule_id="r2", triage_type="TP"),
        ))
        assert result.exit_code == 2  # FN wins

    def test_unreviewed_critical_fails_with_exit_1(self):
        result = evaluate_ci_gate(_report(_violation(severity="CRITICAL")))
        assert not result.ok
        assert result.exit_code == 1

    def test_unreviewed_warning_passes(self):
        result = evaluate_ci_gate(_report(_violation(severity="WARNING")))
        assert result.ok
        assert result.exit_code == 0

    def test_annotations_level_mapping(self):
        report = _report(
            _violation(rule_id="r1", triage_type="FN"),
            _violation(rule_id="r2", triage_type="TP"),
            _violation(rule_id="r3", triage_type="FP"),
            _violation(rule_id="r4", severity="CRITICAL"),         # unreviewed critical
            _violation(rule_id="r5", severity="WARNING"),          # unreviewed warning
        )
        result = evaluate_ci_gate(report)
        levels = [a["level"] for a in result.annotations]
        assert levels.count("error") == 3    # FN + TP + unreviewed critical
        assert levels.count("warning") == 1  # FP
        assert levels.count("notice") == 1   # unreviewed warning

    def test_annotation_messages_contain_rule_id(self):
        v = _violation(rule_id="LANG-required", triage_type="TP")
        result = evaluate_ci_gate(_report(v))
        assert any("LANG-required" in a["message"] for a in result.annotations)

    def test_summary_contains_tp_count_on_fail(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="TP")))
        assert "TP" in result.summary
        assert "FAIL" in result.summary

    def test_summary_contains_fn_on_exit_2(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="FN")))
        assert "FN" in result.summary
        assert "FAIL" in result.summary

    def test_summary_pass_shows_total(self):
        result = evaluate_ci_gate(_report(_violation(triage_type="FP")))
        assert "PASS" in result.summary
        assert "1" in result.summary  # 1 violation total

    def test_multiple_fp_all_pass(self):
        report = _report(
            _violation(rule_id="r1", triage_type="FP"),
            _violation(rule_id="r2", triage_type="FP"),
            _violation(rule_id="r3", triage_type="FP"),
        )
        result = evaluate_ci_gate(report)
        assert result.ok
        assert result.exit_code == 0


# ── format_human_gate ─────────────────────────────────────────────────────────

class TestFormatHumanGate:
    def test_contains_tool_header(self):
        result = evaluate_ci_gate(_report())
        output = format_human_gate(result, _report())
        assert "[violation_triage]" in output

    def test_contains_summary(self):
        result = evaluate_ci_gate(_report())
        output = format_human_gate(result, _report())
        assert "summary=" in output

    def test_contains_ok_field(self):
        result = evaluate_ci_gate(_report())
        output = format_human_gate(result, _report())
        assert "ok=" in output

    def test_contains_exit_code(self):
        result = evaluate_ci_gate(_report())
        output = format_human_gate(result, _report())
        assert "exit_code=" in output

    def test_contains_type_counts(self):
        result = evaluate_ci_gate(_report())
        output = format_human_gate(result, _report())
        assert "type_TP=" in output
        assert "type_FP=" in output
        assert "type_FN=" in output
        assert "type_unreviewed=" in output

    def test_error_annotation_in_output(self):
        v = _violation(triage_type="TP")
        report = _report(v)
        result = evaluate_ci_gate(report)
        output = format_human_gate(result, report)
        assert "ERROR:" in output

    def test_warning_annotation_in_output(self):
        v = _violation(triage_type="FP")
        report = _report(v)
        result = evaluate_ci_gate(report)
        output = format_human_gate(result, report)
        assert "WARNING:" in output


# ── Integration: full workflow ────────────────────────────────────────────────

class TestIntegration:
    def test_cv_json_to_gate_pass_when_no_violations(self):
        data = {"compliant": True, "contract_found": True, "errors": [], "warnings": []}
        report = from_contract_validator_json(data)
        result = evaluate_ci_gate(report)
        assert result.ok
        assert result.exit_code == 0

    def test_cv_json_unreviewed_critical_blocks_gate(self):
        data = {
            "compliant": False,
            "contract_found": True,
            "errors": ["LANG field is required"],
            "warnings": [],
        }
        report = from_contract_validator_json(data)
        result = evaluate_ci_gate(report)
        assert not result.ok
        assert result.exit_code == 1

    def test_fp_annotation_unblocks_gate(self):
        """After marking a violation FP, gate should pass."""
        data = {"errors": ["LANG field is required"], "warnings": []}
        new_report = from_contract_validator_json(data)

        # Simulate human annotating it as FP
        new_report.violations[0].triage = TriageEntry(
            type="FP", root_cause="contract", action="fix_rule"
        )
        result = evaluate_ci_gate(new_report)
        assert result.ok
        assert result.exit_code == 0

    def test_merge_preserves_fp_across_runs(self):
        """FP annotation from previous run survives a new detection run."""
        # Run 1: detect violation, human marks as FP
        run1 = from_contract_validator_json({"errors": ["LANG field is required"], "warnings": []})
        run1.violations[0].triage = TriageEntry(type="FP", root_cause="contract", action="fix_rule")

        # Run 2: same violation detected again
        run2 = from_contract_validator_json({"errors": ["LANG field is required"], "warnings": []})

        # Merge
        merged = merge_triage(run1, run2)
        result = evaluate_ci_gate(merged)
        assert result.ok  # FP preserved → gate passes

    def test_ga_json_clean_project_passes(self):
        data = {
            "ok": True,
            "project_root": "/tmp",
            "checks": [
                {"name": "doc:governance/SYSTEM_PROMPT.md", "ok": True, "detail": ""},
                {"name": "runtime:runtime_hooks/core/pre_task_check.py", "ok": True, "detail": ""},
            ],
            "errors": [],
            "warnings": [],
        }
        report = from_governance_auditor_json(data)
        result = evaluate_ci_gate(report)
        assert result.ok
        assert result.exit_code == 0
