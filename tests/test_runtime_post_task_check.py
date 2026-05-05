import sys
from pathlib import Path
import shutil
import textwrap

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.post_task_check import format_human_result, run_post_task_check


def _contract(**overrides) -> str:
    fields = {
        "LANG": "C++",
        "LEVEL": "L2",
        "SCOPE": "feature",
        "PLAN": "PLAN.md",
        "LOADED": "SYSTEM_PROMPT, HUMAN-OVERSIGHT",
        "CONTEXT": "repo -> runtime-governance; NOT: platform rewrite",
        "PRESSURE": "SAFE (20/200)",
        "RULES": "common,python",
        "RISK": "medium",
        "OVERSIGHT": "review-required",
        "MEMORY_MODE": "candidate",
    }
    fields.update(overrides)
    body = "\n".join(f"{k} = {v}" for k, v in fields.items())
    return f"[Governance Contract]\n{body}\n"


@pytest.fixture
def local_memory_root():
    path = Path("tests") / "_tmp_post_task_memory"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_post_task_check_passes_for_compliant_output():
    result = run_post_task_check(_contract(), risk="medium", oversight="review-required")
    assert result["ok"] is True


def test_post_task_check_fails_without_contract():
    result = run_post_task_check("no contract here", risk="medium", oversight="review-required")
    assert result["ok"] is False
    assert any("Missing governance contract" in error for error in result["errors"])


def test_post_task_check_fails_high_risk_auto_oversight():
    result = run_post_task_check(_contract(OVERSIGHT="auto"), risk="high", oversight="auto")
    assert result["ok"] is False
    assert any("High-risk" in error for error in result["errors"])


def test_post_task_check_can_create_candidate_snapshot(local_memory_root):
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        memory_root=local_memory_root,
        snapshot_task="Runtime governance",
        snapshot_summary="Snapshot from post-task check",
        create_snapshot=True,
    )
    assert result["ok"] is True
    assert result["snapshot"] is not None
    assert Path(result["snapshot"]["snapshot_path"]).exists()


def test_post_task_check_blocks_durable_memory_without_oversight():
    result = run_post_task_check(
        _contract(MEMORY_MODE="durable", OVERSIGHT="auto"),
        risk="medium",
        oversight="auto",
    )
    assert result["ok"] is False
    assert any("Durable memory" in error for error in result["errors"])


def test_post_task_check_merges_runtime_check_errors():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "warnings": ["Rollback / cleanup coverage was not detected."],
            "errors": ["Missing required failure-test coverage: failure_path"],
        },
    )
    assert result["ok"] is False
    assert any("runtime-check: Missing required failure-test coverage: failure_path" in error for error in result["errors"])
    assert any("runtime-check: Rollback / cleanup coverage was not detected." in warning for warning in result["warnings"])


def test_post_task_check_applies_refactor_evidence_requirements():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_happy_path",
                "tests/test_service.py::test_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["refactor_evidence"] is not None
    assert any("refactor-evidence: Missing refactor evidence: regression-oriented test signal" in error for error in result["errors"])
    assert any("refactor-evidence: Missing refactor evidence: interface stability signal" in error for error in result["errors"])
    assert any("refactor-evidence: Missing refactor evidence: error_path_inventory missing - hard stop" in error for error in result["errors"])


def test_post_task_check_blocks_missing_error_behavior_diff_for_affected_refactor_case():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_interface_contract_stable",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["refactor_evidence"] is not None
    assert any("error_behavior_diff missing entries for affected error cases: ERR-001" in error for error in result["errors"])


def test_post_task_check_blocks_changed_error_behavior_without_reviewer_note():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_interface_contract_stable",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "returns cached fallback",
                    "status": "changed",
                    "reviewer_note": "",
                }
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert any("reviewer_note is empty" in error for error in result["errors"])


def test_post_task_check_applies_failure_completeness_checks():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": ["tests/test_service.py::test_happy_path"],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["failure_completeness"] is not None
    assert any("failure-completeness: Missing failure completeness evidence: failure-path signal" in error for error in result["errors"])


def test_post_task_check_can_use_public_api_diff_for_refactor_interface_stability():
    root = Path("tests") / "_tmp_public_api_runtime"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        before_file = root / "before.cs"
        after_file = root / "after.cs"
        before_file.write_text(
            "public class Service\n{\n    public int Run(int value) => value;\n}\n",
            encoding="utf-8",
        )
        after_file.write_text(
            "public class Service\n{\n    public int Run(int value) => value;\n    public int Ping() => 0;\n}\n",
            encoding="utf-8",
        )

        result = run_post_task_check(
            _contract(RULES="common,refactor"),
            risk="medium",
            oversight="review-required",
            checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "raises TimeoutError",
                    "status": "unchanged",
                    "reviewer_note": "",
                }
            ],
            "warnings": [],
            "errors": [],
        },
        api_before_files=[before_file],
        api_after_files=[after_file],
        )

        assert result["public_api_diff"] is not None
        assert result["public_api_diff"]["ok"] is True
        assert result["refactor_evidence"]["signals_detected"]["interface_stability_evidence"] is True
        assert all("interface stability signal" not in error for error in result["errors"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_task_check_blocks_removed_public_api_for_refactor():
    root = Path("tests") / "_tmp_public_api_runtime_removed"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        before_file = root / "before.cs"
        after_file = root / "after.cs"
        before_file.write_text("public class Service { public int Run(int value) => value; }", encoding="utf-8")
        after_file.write_text("public class Service { internal int Run(int value) => value; }", encoding="utf-8")

        result = run_post_task_check(
            _contract(RULES="common,refactor"),
            risk="medium",
            oversight="review-required",
            checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "raises TimeoutError",
                    "status": "unchanged",
                    "reviewer_note": "",
                }
            ],
            "warnings": [],
            "errors": [],
        },
        api_before_files=[before_file],
        api_after_files=[after_file],
        )

        assert result["ok"] is False
        assert any("public-api-diff: Public API surface removed or changed." in error for error in result["errors"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_task_check_applies_kernel_driver_evidence_requirements():
    result = run_post_task_check(
        _contract(RULES="common,cpp,kernel-driver", RISK="high", OVERSIGHT="human-approval"),
        risk="high",
        oversight="human-approval",
        checks={
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_cleanup_unwind_on_partial_init_failure",
            ],
            "diagnostics": ["WDK compile output only"],
            "summary": {"failed": 0},
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["driver_evidence"] is not None
    assert any("driver-evidence: Missing kernel-driver evidence: static analysis result" in error for error in result["errors"])
    assert any("driver-evidence: Missing kernel-driver evidence: IRQL / pageable-context verification" in error for error in result["errors"])


def test_post_task_check_passes_kernel_driver_evidence_with_sdv_signal():
    result = run_post_task_check(
        _contract(RULES="common,cpp,kernel-driver", RISK="high", OVERSIGHT="human-approval"),
        risk="high",
        oversight="human-approval",
        checks={
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_cleanup_unwind_on_partial_init_failure",
                "driver_tests::test_irql_passive_level_contract",
            ],
            "diagnostics": [
                "Static Driver Verifier: ruleset passed",
                "SAL analysis confirms pageable path is passive_level only",
            ],
            "summary": {"failed": 0},
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is True
    assert result["driver_evidence"] is not None
    assert result["driver_evidence"]["ok"] is True


def test_post_task_check_human_output_includes_evidence_summary():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": False,
                }
            ],
            "public_api_diff": {
                "ok": True,
                "removed": [],
                "added": ["public int Ping() => 0;"],
                "warnings": ["Public API surface added or changed."],
                "breaking_changes": [],
                "non_breaking_changes": ["public int Ping() => 0;"],
                "compatibility_risk": "low",
                "errors": [],
            },
            "warnings": [],
            "errors": [],
        },
    )

    output = format_human_result(result)
    assert "[post_task_check]" in output
    assert "summary=ok=False | compliant=True | memory_mode=candidate" in output
    assert "public_api_added=1" in output
    assert "public_api_ok=True" in output
    assert "failure_completeness_ok=" in output
    assert "refactor_evidence_ok=" in output


def test_post_task_check_adds_assumption_advisory_for_direct_modification_without_structure():
    response = _contract() + "\nImplemented payload patch and updated parser flow."
    result = run_post_task_check(
        response,
        risk="medium",
        oversight="review-required",
    )

    assert result["ok"] is True
    assert result["assumption_check"]["complete"] is False
    assert result["assumption_advisories"] != []
    assert any("Assumption check missing before modification" in warning for warning in result["warnings"])
    output = format_human_result(result)
    assert "assumption_advisory_count=1" in output
    assert "advisory_signal: assumption_check_missing -> behavioral_advisory;" in output


def test_post_task_check_reads_structured_action_decision_from_response():
    response = _contract() + (
        "\n{\n"
        '  "assumptions": ["payload mismatch"],\n'
        '  "alternative_causes": ["vendor routing mismatch", "library mapping mismatch"],\n'
        '  "evidence": ["single failing payload capture"],\n'
        '  "action_decision": "need_more_info"\n'
        "}\n"
        "Reframe: validate routing table first.\n"
    )
    result = run_post_task_check(
        response,
        risk="medium",
        oversight="review-required",
    )

    assert result["ok"] is True
    assert result["assumption_check"]["action_decision"] == "need_more_info"
    assert result["assumption_check"]["complete"] is True
    assert result["assumption_advisories"] == []


def test_post_task_check_can_validate_external_rule_pack_from_contract(tmp_path):
    contract_root = tmp_path / "usb_hub_contract"
    (contract_root / "rules" / "firmware").mkdir(parents=True)
    (contract_root / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    contract_file = contract_root / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,firmware"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["rule_packs"]["valid"] is True


def test_post_task_check_domain_contract_return_has_content_elided(tmp_path):
    """Regression: return payload must not carry full document content.

    Validators receive the full domain_contract during execution; the return
    dict uses _slim_domain_contract() which replaces content with elision
    markers.  This prevents the return payload from ballooning with dead-weight
    file content that no caller needs after execution completes.
    """
    contract_root = tmp_path / "slim_test"
    (contract_root / "rules" / "firmware").mkdir(parents=True)
    (contract_root / "rules" / "firmware" / "safety.md").write_text(
        "# Firmware rule\nValidate rollback.\n", encoding="utf-8"
    )
    doc_content = "A" * 500  # 500-char document; clearly non-empty
    doc_file = contract_root / "CHECKLIST.md"
    doc_file.write_text(doc_content, encoding="utf-8")
    override_content = "B" * 200
    override_file = contract_root / "AGENTS.md"
    override_file.write_text(override_content, encoding="utf-8")
    contract_file = contract_root / "contract.yaml"
    contract_file.write_text(
        "name: slim-test-contract\n"
        "documents:\n"
        "  - CHECKLIST.md\n"
        "ai_behavior_override:\n"
        "  - AGENTS.md\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,firmware"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
    )

    dc = result["domain_contract"]
    assert dc is not None
    assert dc["name"] == "slim-test-contract"

    # Content must be elided in the return payload
    for doc in dc["documents"]:
        assert doc["content"] == "", f"document content must be elided, got {len(doc['content'])} chars"
        assert doc["content_elided_for_return"] is True
        assert doc["content_char_count"] == 500, "char_count must reflect original size"

    for entry in dc["ai_behavior_override"]:
        assert entry["content"] == "", "ai_behavior_override content must be elided"
        assert entry["content_elided_for_return"] is True
        assert entry["content_char_count"] == 200

    # Metadata must be intact
    assert dc["rule_roots"]
    assert result["rule_packs"]["valid"] is True


def test_post_task_check_can_auto_discover_domain_contract_from_project_root(tmp_path):
    (tmp_path / "rules" / "firmware").mkdir(parents=True)
    (tmp_path / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,firmware"),
        risk="medium",
        oversight="review-required",
        project_root=tmp_path,
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["contract_resolution"]["source"] == "discovery"
    assert result["resolved_contract_file"] == str(contract_file.resolve())
    output = format_human_result(result)
    assert "contract=firmware/medium" in output or "contract=usb-hub-firmware/medium" in output


def test_post_task_check_domain_validator_violation_is_advisory_without_hard_stop(tmp_path):
    (tmp_path / "rules" / "temp-domain").mkdir(parents=True)
    (tmp_path / "rules" / "temp-domain" / "safety.md").write_text("# Temp rule\n", encoding="utf-8")
    (tmp_path / "validators").mkdir(parents=True)
    (tmp_path / "validators" / "temp_validator.py").write_text(
        textwrap.dedent(
            """
            from governance_tools.validator_interface import DomainValidator, ValidatorResult

            class TempValidator(DomainValidator):
                @property
                def rule_ids(self):
                    return ["temp-domain", "TMP-001"]

                def validate(self, payload: dict) -> ValidatorResult:
                    return ValidatorResult(
                        ok=False,
                        rule_ids=self.rule_ids,
                        violations=["TMP-VIOLATION-001"],
                        evidence_summary="temp violation",
                    )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: temp-domain\n"
        "domain: temp-domain\n"
        "rule_roots:\n"
        "  - rules\n"
        "validators:\n"
        "  - validators/temp_validator.py\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,temp-domain"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert any("domain-validator:temp_validator: TMP-VIOLATION-001" in warning for warning in result["warnings"])


def test_post_task_check_domain_validator_violation_can_trigger_hard_stop(tmp_path):
    (tmp_path / "rules" / "temp-domain").mkdir(parents=True)
    (tmp_path / "rules" / "temp-domain" / "safety.md").write_text("# Temp rule\n", encoding="utf-8")
    (tmp_path / "validators").mkdir(parents=True)
    (tmp_path / "validators" / "temp_validator.py").write_text(
        textwrap.dedent(
            """
            from governance_tools.validator_interface import DomainValidator, ValidatorResult

            class TempValidator(DomainValidator):
                @property
                def rule_ids(self):
                    return ["temp-domain", "TMP-001"]

                def validate(self, payload: dict) -> ValidatorResult:
                    return ValidatorResult(
                        ok=False,
                        rule_ids=self.rule_ids,
                        violations=["TMP-VIOLATION-001"],
                        evidence_summary="temp violation",
                    )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: temp-domain\n"
        "domain: temp-domain\n"
        "rule_roots:\n"
        "  - rules\n"
        "validators:\n"
        "  - validators/temp_validator.py\n"
        "hard_stop_rules:\n"
        "  - TMP-001\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,temp-domain"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
    )

    assert result["ok"] is False
    assert result["domain_hard_stop_rules"] == ["TMP-001"]
    assert any("domain-validator:temp_validator: TMP-VIOLATION-001" in warning for warning in result["warnings"])
    assert result["policy_violations"] == [
        {
            "violation_type": "domain_contract_violation",
            "policy_type": "domain-contract policy",
            "override_target": "runtime default verdict",
            "source": "hard_stop_rules",
            "validator": "temp_validator",
            "rule_ids": ["TMP-001"],
            "detected_by": "domain validator",
            "verdict_impact": "escalate",
            "message": "Domain policy stop requested by hard_stop_rules: temp_validator -> TMP-VIOLATION-001 (rules: TMP-001)",
        }
    ]
    assert any("runtime-policy: Domain policy stop requested by hard_stop_rules: temp_validator -> TMP-VIOLATION-001" in error for error in result["errors"])
    output = format_human_result(result)
    assert "domain_hard_stop_rules=TMP-001" in output
    assert "policy_violation_count=1" in output


def test_post_task_check_passes_versioned_validator_envelope_to_domain_validator(tmp_path):
    (tmp_path / "rules" / "temp-domain").mkdir(parents=True)
    (tmp_path / "rules" / "temp-domain" / "safety.md").write_text("# Temp rule\n", encoding="utf-8")
    (tmp_path / "validators").mkdir(parents=True)
    (tmp_path / "validators" / "temp_validator.py").write_text(
        textwrap.dedent(
            """
            from governance_tools.validator_interface import DomainValidator, ValidatorResult

            class TempValidator(DomainValidator):
                @property
                def rule_ids(self):
                    return ["temp-domain"]

                def validate(self, payload: dict) -> ValidatorResult:
                    envelope = payload.get("evidence_envelope") or {}
                    provenance = envelope.get("provenance") or {}
                    return ValidatorResult(
                        ok=True,
                        rule_ids=self.rule_ids,
                        metadata={
                            "payload_schema_version": payload.get("schema_version"),
                            "payload_type": payload.get("payload_type"),
                            "envelope_schema_version": envelope.get("schema_version"),
                            "contract_name": provenance.get("contract_name"),
                            "legacy_fields_preserved": payload.get("compatibility", {}).get("legacy_top_level_fields_preserved"),
                        },
                    )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: temp-domain\n"
        "domain: temp-domain\n"
        "rule_roots:\n"
        "  - rules\n"
        "validators:\n"
        "  - validators/temp_validator.py\n"
        "plugin_version: \"1.0.0\"\n"
        "framework_interface_version: \"1\"\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,temp-domain"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
        checks={
            "changed_files": ["src/ui/layout.tsx"],
            "test_names": [
                "tests/test_layout.py::test_failure_path_signal",
                "tests/test_layout.py::test_cleanup_release",
            ],
        },
    )

    assert result["ok"] is True
    assert result["domain_validator_results"][0]["metadata"]["payload_schema_version"] == "1.0"
    assert result["domain_validator_results"][0]["metadata"]["payload_type"] == "domain-validator-payload"
    assert result["domain_validator_results"][0]["metadata"]["envelope_schema_version"] == "1.0"
    assert result["domain_validator_results"][0]["metadata"]["contract_name"] == "temp-domain"
    assert result["domain_validator_results"][0]["metadata"]["legacy_fields_preserved"] is True



def test_post_task_check_classifies_missing_required_runtime_evidence():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "required_runtime_evidence": ["public-api-diff"],
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["evidence_violations"] == [
        {
            "violation_type": "missing_required_evidence",
            "evidence_kind": "public-api-diff",
            "detected_by": "runtime evidence validator",
            "verdict_impact": "escalate",
            "message": "Missing required runtime evidence: public-api-diff",
        }
    ]
    assert any("runtime-evidence: Missing required runtime evidence: public-api-diff" in error for error in result["errors"])
    output = format_human_result(result)
    assert "evidence_violation_count=1" in output
    assert "advisory_signal: required_evidence_missing -> evidence_advisory; required evidence is incomplete for this decision surface; decision distance=enforced_elsewhere; not behavioral compliance proof; already handled by evidence-driven escalation or stop logic" in output



def test_post_task_check_classifies_invalid_public_api_diff_schema():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "required_runtime_evidence": ["public-api-diff"],
            "public_api_diff": {
                "ok": "yes",
            },
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["evidence_violations"] == [
        {
            "violation_type": "invalid_evidence_schema",
            "evidence_kind": "public-api-diff",
            "detected_by": "runtime evidence validator",
            "verdict_impact": "stop",
            "message": "Invalid runtime evidence schema: public-api-diff (public-api-diff evidence missing keys: ['added', 'breaking_changes', 'compatibility_risk', 'errors', 'non_breaking_changes', 'removed', 'warnings'])",
        }
    ]
    assert any("runtime-evidence: Invalid runtime evidence schema: public-api-diff" in error for error in result["errors"])
    assert not any(item["violation_type"] == "missing_required_evidence" for item in result["evidence_violations"])
    output = format_human_result(result)
    assert "evidence_violation_count=1" in output



def test_post_task_check_classifies_policy_conflict_from_precedence_matrix():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "policy_conflicts": [
                {
                    "policy_type": "runtime-safety-policy",
                    "override_target": "domain-policy",
                    "scope": "all protected domains",
                }
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["policy_violations"] == [
        {
            "violation_type": "policy_conflict",
            "policy_type": "runtime-safety-policy",
            "override_target": "domain-policy",
            "scope": "all protected domains",
            "detected_by": "policy precedence resolver",
            "verdict_impact": "escalate",
            "message": "Runtime policy conflict requires precedence resolution: runtime-safety-policy -> domain-policy (runtime-safety-policy wins)",
        }
    ]
    assert any("runtime-policy: Runtime policy conflict requires precedence resolution: runtime-safety-policy -> domain-policy" in error for error in result["errors"])
    output = format_human_result(result)
    assert "policy_violation_count=1" in output



def test_post_task_check_classifies_illegal_policy_override():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "policy_conflicts": [
                {
                    "policy_type": "repo-local workflow preference",
                    "override_target": "runtime-safety-policy",
                    "scope": "non-protected workflow behavior",
                }
            ],
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["policy_violations"] == [
        {
            "violation_type": "illegal_override",
            "policy_type": "repo-local workflow preference",
            "override_target": "runtime-safety-policy",
            "scope": "non-protected workflow behavior",
            "detected_by": "ownership and precedence validator",
            "verdict_impact": "stop",
            "message": "Illegal runtime policy override: repo-local workflow preference -> runtime-safety-policy",
        }
    ]
    assert any("runtime-policy: Illegal runtime policy override: repo-local workflow preference -> runtime-safety-policy" in error for error in result["errors"])



def test_post_task_check_replay_is_deterministic_for_same_policy_and_evidence():
    checks = {
        "required_runtime_evidence": ["public-api-diff"],
        "public_api_diff": {
            "ok": True,
            "removed": [],
            "added": ["public int Ping() => 0;"],
            "compatibility_risk": "low",
            "breaking_changes": [],
            "non_breaking_changes": ["public int Ping() => 0;"],
            "warnings": ["Public API surface added or changed."],
            "errors": [],
        },
        "policy_conflicts": [
            {
                "policy_type": "runtime-safety-policy",
                "override_target": "domain-policy",
                "scope": "all protected domains",
            }
        ],
        "warnings": [],
        "errors": [],
    }

    result_a = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks=checks,
    )
    result_b = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks=checks,
    )

    assert result_a["ok"] == result_b["ok"]
    assert result_a["errors"] == result_b["errors"]
    assert result_a["warnings"] == result_b["warnings"]
    assert result_a["evidence_violations"] == result_b["evidence_violations"]
    assert result_a["policy_violations"] == result_b["policy_violations"]


def test_post_task_check_emits_candidate_violation_for_report_provenance_machine_consumption():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_report.py::test_failure_path_signal",
                "tests/test_report.py::test_cleanup_release",
            ],
            "report_provenance_consumption": [
                {
                    "consumer_path": "gate",
                    "consumer_name": "policy_ranker",
                    "fields": ["provenance_warning"],
                }
            ],
        },
    )

    assert result["ok"] is True
    assert result["provenance_boundary_audit"] == {
        "status": "candidate_violation",
        "advisory_only": True,
        "observed_surface": "post_task_check",
        "suspected_consumer": "policy_ranker",
        "protected_field": "provenance_warning",
        "protected_namespace": "report",
        "basis": "report provenance consumption observation",
        "violation_type": "non_decisional_signal_used_in_decision",
        "usage_note": "Candidate violation: machine-facing logic consumed a protected non-authoritative report field. Advisory only; must not modify gate behavior.",
    }
    output = format_human_result(result)
    assert "provenance_boundary_audit=candidate_violation field=provenance_warning consumer=policy_ranker advisory_only=True" in output


def test_post_task_check_does_not_modify_gate_blocked_when_provenance_audit_present():
    checks = {
        "gate_policy": {"blocked": True, "source": "existing-gate"},
        "test_names": [
            "tests/test_report.py::test_failure_path_signal",
            "tests/test_report.py::test_cleanup_release",
        ],
        "report_provenance_consumption": [
            {
                "consumer_path": "gate",
                "consumer_name": "default_ranker",
                "fields": ["token_source_summary"],
            }
        ],
    }

    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks=checks,
    )

    assert result["provenance_boundary_audit"]["status"] == "candidate_violation"
    assert result["checks"]["gate_policy"]["blocked"] is True
    assert checks["gate_policy"]["blocked"] is True


def test_post_task_check_emits_candidate_violation_for_token_count_machine_consumption():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_report.py::test_failure_path_signal",
                "tests/test_report.py::test_cleanup_release",
            ],
            "report_provenance_consumption": [
                {
                    "consumer_path": "decision",
                    "consumer_name": "cost_ranker",
                    "fields": ["token_count.total_tokens"],
                }
            ],
        },
    )

    assert result["ok"] is True
    assert result["provenance_boundary_audit"]["status"] == "candidate_violation"
    assert result["provenance_boundary_audit"]["violation_type"] == "non_decisional_signal_used_in_decision"
    assert result["provenance_boundary_audit"]["protected_field"] == "token_count.total_tokens"
    assert result["provenance_boundary_audit"]["suspected_consumer"] == "cost_ranker"


def test_candidate_violation_alone_stays_advisory_only():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "report_provenance_consumption": [
                {"consumer_path": "gate", "consumer_name": "ranker", "fields": ["token_observability_level"]}
            ]
        },
    )

    promo = result["candidate_violation_promotion"]
    assert promo["advisory_only"] is True
    assert promo["auto_promotion_allowed"] is False
    assert promo["auto_block_allowed"] is False
    assert promo["promotion_eligible"] is False
    assert promo["promoted_policy_violation"] is None
    assert result["policy_violations"] == []


def test_candidate_violation_high_confidence_still_advisory_only():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "report_provenance_consumption": [
                {"consumer_path": "decision", "consumer_name": "ranker", "fields": ["token_count.total_tokens"]}
            ],
            "candidate_violation_promotion": {
                "detector_confidence": "high",
            },
        },
    )

    promo = result["candidate_violation_promotion"]
    assert promo["promotion_eligible"] is False
    assert "reviewer_confirmed" in promo["missing_requirements"]
    assert promo["promoted_policy_violation"] is None
    assert result["policy_violations"] == []


def test_candidate_violation_missing_authority_ref_cannot_promote():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "report_provenance_consumption": [
                {"consumer_path": "decision", "consumer_name": "ranker", "fields": ["token_source_summary"]}
            ],
            "candidate_violation_promotion": {
                "reviewer_confirmed": True,
                "evidence_ref": "evidence://abc",
                "promoted_at": "2026-05-05T12:00:00+08:00",
                "promotion_reason": "manual reviewer confirmation",
            },
        },
    )

    promo = result["candidate_violation_promotion"]
    assert promo["promotion_eligible"] is False
    assert "authority_ref" in promo["missing_requirements"]
    assert promo["promoted_policy_violation"] is None
    assert result["policy_violations"] == []


def test_candidate_violation_promotes_only_with_authority_path():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "report_provenance_consumption": [
                {"consumer_path": "gate", "consumer_name": "ranker", "fields": ["provenance_warning"]}
            ],
            "candidate_violation_promotion": {
                "reviewer_confirmed": True,
                "authority_ref": "authority://review/123",
                "evidence_ref": "evidence://run/456",
                "promoted_at": "2026-05-05T13:00:00+08:00",
                "promotion_reason": "reviewer validated misuse evidence",
            },
        },
    )

    promo = result["candidate_violation_promotion"]
    assert promo["promotion_eligible"] is True
    assert promo["promotion_decision"] == "promoted_by_authority_path"
    assert promo["promoted_policy_violation"]["violation_type"] == "non_decisional_signal_used_in_decision"
    # Promotion contract does not auto-inject policy violations into gate decisions.
    assert result["policy_violations"] == []
