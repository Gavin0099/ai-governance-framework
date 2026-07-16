"""Receipt runtime binding (schema 1.4) and validator signal registry tests.

Agent Runtime Evaluation tranche 1, Phase 2. Binding rules under test:
missing/unreadable profile degrades to unknown; a profile written by another
session (session_id conflict) is stale and must not be bound; sample_origin
derives from trigger context, never agent self-report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.session_closeout_entry import (
    CLOSEOUT_RECEIPT_SCHEMA_VERSION,
    RUNTIME_PROFILE_RELPATH,
    _load_runtime_binding,
    _write_closeout_receipt,
)
from governance_tools.validator_signal_registry import (
    load_registry,
    resolve_validator_signal,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

SESSION_ID = "e4333b54-c3fa-42bf-afd7-8fbe32e863cb"


def _write_profile(root: Path, session_id: str = SESSION_ID,
                   detection_status: str = "full",
                   coarse_id: str = "rp_coarse111111",
                   full_id: str = "rp_full22222222") -> Path:
    profile_path = root / RUNTIME_PROFILE_RELPATH
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps({
        "schema_version": "1.0",
        "detection_status": detection_status,
        "session_id": {"value": session_id, "detection": "verified"},
        "fingerprint": {
            "fingerprint_schema_version": "1.0",
            "coarse_id": coarse_id,
            "full_id": full_id,
        },
    }), encoding="utf-8")
    return profile_path


def _emit_receipt(root: Path, trigger_mode: str = "native_hook",
                  session_id: str = SESSION_ID) -> dict:
    receipt_path = _write_closeout_receipt(
        root,
        agent_id="test",
        trigger_mode=trigger_mode,
        entrypoint="test",
        exit_code=0,
        closeout_artifact_path=None,
        memory_eligibility_evaluated=False,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="test",
        session_id=session_id,
    )
    return json.loads(receipt_path.read_text(encoding="utf-8"))


class TestRuntimeBinding:
    def test_receipt_binds_matching_profile(self, tmp_path: Path) -> None:
        _write_profile(tmp_path)
        payload = _emit_receipt(tmp_path)
        assert payload["schema_version"] == CLOSEOUT_RECEIPT_SCHEMA_VERSION
        assert payload["runtime_profile_id"] == "rp_full22222222"
        assert payload["runtime_profile_coarse_id"] == "rp_coarse111111"
        assert payload["runtime_detection_status"] == "full"

    def test_missing_profile_degrades_to_unknown(self, tmp_path: Path) -> None:
        payload = _emit_receipt(tmp_path)
        assert payload["runtime_profile_id"] == "unknown"
        assert payload["runtime_profile_coarse_id"] == "unknown"
        assert payload["runtime_detection_status"] == "unknown"

    def test_stale_profile_from_other_session_is_not_bound(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, session_id="another-session-entirely")
        payload = _emit_receipt(tmp_path)
        assert payload["runtime_profile_id"] == "unknown"
        assert payload["runtime_detection_status"] == "unknown"

    def test_profile_without_session_id_still_binds(self, tmp_path: Path) -> None:
        # A profile with unknown session id cannot be proven stale; binding
        # proceeds and detection_status carries the profile's own claim.
        _write_profile(tmp_path, session_id="")
        binding = _load_runtime_binding(tmp_path, SESSION_ID)
        assert binding["runtime_profile_id"] == "rp_full22222222"

    def test_unreadable_profile_degrades_to_unknown(self, tmp_path: Path) -> None:
        profile_path = tmp_path / RUNTIME_PROFILE_RELPATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("{not json", encoding="utf-8")
        payload = _emit_receipt(tmp_path)
        assert payload["runtime_profile_id"] == "unknown"

    def test_invalid_detection_status_degrades_to_unknown(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, detection_status="excellent")
        payload = _emit_receipt(tmp_path)
        assert payload["runtime_detection_status"] == "unknown"


class TestSampleOrigin:
    @pytest.mark.parametrize("trigger,expected", [
        ("native_hook", "natural_task"),
        ("manual_fallback", "natural_task"),
        ("wrapper", "natural_task"),
        ("synthetic_smoke", "synthetic"),
        ("nonsense_mode", "unknown"),
    ])
    def test_sample_origin_derived_from_trigger(self, tmp_path: Path,
                                                trigger: str, expected: str) -> None:
        payload = _emit_receipt(tmp_path, trigger_mode=trigger)
        assert payload["sample_origin"] == expected


class TestSchema14Conformance:
    def test_emitted_receipt_satisfies_1_4_conditional_requirements(self, tmp_path: Path) -> None:
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json")
            .read_text(encoding="utf-8"))
        payload = _emit_receipt(tmp_path)
        properties = schema["properties"]
        assert set(payload) <= set(properties)
        for key in schema["required"]:
            assert key in payload
        # schema 1.4 conditional: runtime_detection_status and sample_origin required
        for clause in schema["allOf"]:
            if clause["if"]["properties"].get("schema_version", {}).get("const") == "1.4":
                for key in clause["then"]["required"]:
                    assert key in payload, f"1.4 receipt missing {key}"
                break
        else:
            pytest.fail("schema has no 1.4 conditional clause")
        assert (payload["runtime_detection_status"]
                in properties["runtime_detection_status"]["enum"])
        assert payload["sample_origin"] in properties["sample_origin"]["enum"]


class TestValidatorSignalRegistry:
    def test_registered_validator_resolves_registry_tier(self) -> None:
        signal = resolve_validator_signal("pytest_suite", _REPO_ROOT)
        assert signal["tier"] == "test_backed"
        assert signal["tier_source"] == "governance-validator-registry-v1"
        assert signal["validator_id"] == "pytest_suite"

    def test_unregistered_validator_resolves_unknown(self) -> None:
        signal = resolve_validator_signal("no_such_validator", _REPO_ROOT)
        assert signal["tier"] == "unknown"
        assert signal["tier_source"] == "governance-validator-registry-v1"

    def test_agent_supplied_tier_cannot_leak_through(self) -> None:
        # A malicious/enthusiastic entry with an out-of-vocabulary tier must
        # resolve to unknown, not pass through.
        registry = {"registry_id": "r-test",
                    "entries": {"v1": {"tier": "high"}}}
        signal = resolve_validator_signal("v1", _REPO_ROOT, registry=registry)
        assert signal["tier"] == "unknown"

    def test_missing_registry_file_degrades(self, tmp_path: Path) -> None:
        registry = load_registry(tmp_path)
        signal = resolve_validator_signal("pytest_suite", tmp_path,
                                          registry=registry)
        assert signal["tier"] == "unknown"
        assert signal["tier_source"] == "registry-unavailable"

    def test_signal_shape_matches_receipt_schema(self) -> None:
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json")
            .read_text(encoding="utf-8"))
        spec = schema["properties"]["validator_signal"]
        signal = resolve_validator_signal("pytest_suite", _REPO_ROOT,
                                          validator_version="framework-1.2.0")
        assert set(signal) <= set(spec["properties"])
        for key in spec["required"]:
            assert key in signal
        assert signal["tier"] in spec["properties"]["tier"]["enum"]
