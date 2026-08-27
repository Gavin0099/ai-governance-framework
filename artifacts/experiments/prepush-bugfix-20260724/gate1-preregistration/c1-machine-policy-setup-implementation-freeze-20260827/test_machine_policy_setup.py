from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = next(path for path in BASE.parents if (path / ".git").exists())
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
setup = importlib.import_module("machine_policy_setup")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _state(*, target_exists: bool = False) -> setup.MachineState:
    return setup.MachineState(
        account_present=True,
        account_enabled=True,
        password_required=True,
        sid_sha256=setup.EXPECTED_SID_SHA256,
        domain_profile_enabled=True,
        private_profile_enabled=True,
        public_profile_enabled=True,
        relevant_outbound_rule_count=2,
        outbound_block_rule_count=1,
        outbound_allow_rule_count=1,
        rule_summary_bytes=367,
        rule_summary_sha256=setup.EXPECTED_RULE_SUMMARY_SHA256,
        account_block_relation_verified=True,
        security_descriptor_sha256=setup.EXPECTED_SECURITY_DESCRIPTOR_SHA256,
        target_exists=target_exists,
        legacy_target_exists=False,
        user_target_exists=False,
    )


class FakeAdapter:
    def __init__(self) -> None:
        self.target_path = Path("C:/ProgramData/OpenAI/Codex/requirements.toml")
        self.safe = True
        self.state = _state()
        self.after = _state(target_exists=True)
        self.published = b""
        self.write_count = 0
        self.rollback_result = "COMPLETE"
        self.channel = True
        self.regular = True
        self.publication_error = False

    def path_is_safe(self) -> bool:
        return self.safe

    def observe(self) -> setup.MachineState:
        return self.after if self.write_count else self.state

    def publish(self, payload: bytes) -> tuple[str, ...]:
        self.write_count += 1
        if self.publication_error:
            raise OSError("synthetic publication failure")
        self.published = payload
        return ("Codex",)

    def read_target(self) -> bytes:
        return self.published

    def target_is_regular_file(self) -> bool:
        return self.regular

    def rollback(self, created_directories: tuple[str, ...]) -> str:
        return self.rollback_result

    def rollback_channel_available(self) -> bool:
        return self.channel


def _precheck(freeze: str, rollback_sha: str, **changes: object) -> bytes:
    value = {
        "schema": setup.PRECHECK_SCHEMA,
        "setup_freeze_commit": freeze,
        "rollback_script_sha256": rollback_sha,
        "powershell_executable_sha256": setup.EXPECTED_POWERSHELL_SHA256,
        "owner_shell_independent_from_codex": True,
        "administrator_role_enabled": True,
        "target_absent": True,
        "rollback_script_outside_policy_and_scratch_roots": True,
        "shell_held_open_until_terminal": True,
        "observed_at_utc": "2026-08-27T06:00:00Z",
        "status": "INDEPENDENT_ELEVATED_ROLLBACK_CHANNEL_READY",
        "diagnostic": "ready",
    }
    value.update(changes)
    return setup.canonical_json(value)


def _execute(adapter: FakeAdapter, **changes: object):
    freeze = "1" * 40
    rollback = (BASE / "independent_owner_rollback.ps1").read_bytes()
    kwargs = {
        "freeze_commit": freeze,
        "executing_commit": freeze,
        "owner_authorized_setup_commit": freeze,
        "frozen_plan_sha256": "2" * 64,
        "owner_authorized_setup_plan_sha256": "2" * 64,
        "requirements_payload": (BASE / "requirements.toml").read_bytes(),
        "rollback_script_payload": rollback,
        "precheck_payload": _precheck(freeze, _sha(rollback)),
        "adapter": adapter,
        "now": datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc),
    }
    kwargs.update(changes)
    return setup.execute_setup(**kwargs)


def test_exact_payload_is_58_bytes() -> None:
    payload = (BASE / "requirements.toml").read_bytes()
    assert len(payload) == 58
    assert _sha(payload) == setup.EXPECTED_REQUIREMENTS_SHA256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner_authorized_setup_commit", "3" * 40),
        ("owner_authorized_setup_plan_sha256", "3" * 64),
    ],
)
def test_authority_mismatch_is_zero_write(field: str, value: str) -> None:
    adapter = FakeAdapter()
    terminal, evidence, receipt = _execute(adapter, **{field: value})
    assert terminal["status"] == "MACHINE_POLICY_AUTHORITY_MISMATCH"
    assert adapter.write_count == 0
    assert evidence is receipt is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("administrator_role_enabled", False),
        ("owner_shell_independent_from_codex", False),
        ("target_absent", False),
        ("shell_held_open_until_terminal", False),
        ("rollback_script_sha256", "0" * 64),
    ],
)
def test_invalid_precheck_is_zero_write(field: str, value: object) -> None:
    adapter = FakeAdapter()
    freeze = "1" * 40
    rollback = (BASE / "independent_owner_rollback.ps1").read_bytes()
    terminal, _, _ = _execute(
        adapter, precheck_payload=_precheck(freeze, _sha(rollback), **{field: value})
    )
    assert terminal["status"] == "MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE"
    assert adapter.write_count == 0


def test_closed_rollback_channel_is_zero_write() -> None:
    adapter = FakeAdapter()
    adapter.channel = False
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE"
    assert adapter.write_count == 0


@pytest.mark.parametrize(
    "state",
    [
        _state(target_exists=True),
        replace(_state(), sid_sha256="0" * 64),
        replace(_state(), outbound_block_rule_count=0),
        replace(_state(), legacy_target_exists=True),
    ],
)
def test_machine_drift_is_zero_write(state: setup.MachineState) -> None:
    adapter = FakeAdapter()
    adapter.state = state
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_DRIFT_REVIEW_REQUIRED"
    assert adapter.write_count == 0


def test_unsafe_or_reparse_path_is_zero_write() -> None:
    adapter = FakeAdapter()
    adapter.safe = False
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_PRECONDITION_FAILED"
    assert adapter.write_count == 0


def test_success_requires_post_verification_and_exact_receipt() -> None:
    adapter = FakeAdapter()
    terminal, evidence, receipt = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_SETUP_APPLIED"
    assert evidence is not None and evidence["terminal_status"] == terminal["status"]
    assert receipt == json.loads((BASE / "downstream-receipt-template.json").read_text())
    assert set(receipt) == {
        "schema", "sandbox_implementation", "managed_requirement_enforced",
        "fallback_observed", "config_sha256", "requirements_sha256",
        "machine_state_change_owner_authorized", "rollback_path_reviewed",
    }


@pytest.mark.parametrize(
    ("rollback", "expected"),
    [
        ("COMPLETE", "MACHINE_POLICY_PUBLICATION_FAILED"),
        ("REVIEW_REQUIRED", "MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED"),
        ("AMBIGUOUS", "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS"),
        ("FAILED", "MACHINE_POLICY_ROLLBACK_FAILED"),
    ],
)
def test_publication_failure_uses_rollback_terminal_precedence(
    rollback: str, expected: str
) -> None:
    adapter = FakeAdapter()
    adapter.publication_error = True
    adapter.rollback_result = rollback
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == expected
    assert adapter.write_count == 1


def test_post_write_mismatch_rolls_back() -> None:
    adapter = FakeAdapter()
    adapter.after = replace(_state(target_exists=True), sid_sha256="0" * 64)
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_DRIFT_REVIEW_REQUIRED"
    assert adapter.write_count == 1


def test_forbidden_retention_is_recursive() -> None:
    with pytest.raises(setup.SetupError, match="forbidden"):
        setup._walk_forbidden({"nested": {"authorization": "secret"}})


def test_terminal_precedence_matches_policy() -> None:
    policy = json.loads((BASE / "terminal-policy.json").read_text())
    assert tuple(policy["allowed_terminals_highest_precedence_first"]) == setup.TERMINAL_PRECEDENCE
    assert setup.select_terminal([
        "MACHINE_POLICY_PUBLICATION_FAILED",
        "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS",
    ]) == "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS"


def test_rollback_script_is_standalone_and_bounded() -> None:
    source = (BASE / "independent_owner_rollback.ps1").read_text(encoding="utf-8")
    assert "CODEX_HOME" not in source
    assert "CodexSandboxOffline" not in source
    assert "Get-NetFirewallRule" not in source
    assert "Remove-LocalUser" not in source
    assert "Remove-NetFirewallRule" not in source
    assert "ExpectedBytes = 58" in source
    assert setup.EXPECTED_REQUIREMENTS_SHA256 in source
    assert "ReparsePoint" in source


def test_observer_is_read_only() -> None:
    source = (BASE / "machine_policy_observer.ps1").read_text(encoding="utf-8")
    for forbidden in (
        "New-LocalUser", "Remove-LocalUser", "New-NetFirewallRule",
        "Remove-NetFirewallRule", "Set-NetFirewallRule", "Set-LocalUser",
        "Set-Content", "Remove-Item",
    ):
        assert forbidden not in source


def test_publication_uses_no_overwrite_atomic_link() -> None:
    source = (BASE / "machine_policy_setup.py").read_text(encoding="utf-8")
    assert "os.link(staging, self.target_path)" in source
    assert "os.replace(staging, self.target_path)" not in source
    assert "--rollback-request" not in source
    assert "--rollback-receipt" not in source
    assert "--rollback-heartbeat" not in source


def test_output_policy_forbids_sensitive_surfaces() -> None:
    policy = json.loads((BASE / "output-policy.json").read_text())
    assert set(policy["forbidden_fields"]) == setup.FORBIDDEN_FIELDS
    assert policy["raw_payload_retained"] is False


def test_manifest_binds_every_frozen_file_except_itself() -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    bindings = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {
        path.name for path in BASE.iterdir()
        if path.is_file() and path.name != "setup-manifest.json"
    }
    assert set(bindings) == actual
    for name, entry in bindings.items():
        payload = (BASE / name).read_bytes()
        assert len(payload) == entry["bytes"]
        assert _sha(payload) == entry["sha256"]


def test_source_bindings_are_git_exact() -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    for entry in manifest["source_bindings"]:
        oid = subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", f'{entry["commit"]}:{entry["path"]}'],
            text=True,
        ).strip()
        assert oid == entry["git_blob_oid"]
        payload = subprocess.check_output(
            ["git", "-C", str(REPO), "cat-file", "blob", oid]
        )
        assert len(payload) == entry["bytes"]
        assert _sha(payload) == entry["sha256"]


def test_repo_external_packet_bindings_are_literals() -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    packets = {item["role"]: item for item in manifest["repo_external_review_packets"]}
    assert packets["setup_pre_run"] == {
        "role": "setup_pre_run", "lines": 430, "bytes": 15786,
        "sha256": "5d90d30e8159cef515c5ed79d66f3385ec847bd96108f33ced5cf8d199106065",
    }
    assert packets["machine_wide_impact"] == {
        "role": "machine_wide_impact", "lines": 512, "bytes": 19584,
        "sha256": "2e47fbb6a7d3332571fa3edd31827076e49d6c8565cc573255a9cc66ffc11ab9",
    }


def test_no_authority_or_execution_claims() -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    assert manifest["execution_authority"]["authorized"] is False
    assert manifest["authoring_boundary"] == {
        "requirements_created_or_deleted": False,
        "account_modified": False,
        "firewall_or_policy_modified": False,
        "hosted_request_executed": False,
        "sandbox_qualification_executed": False,
        "randomization_created": False,
        "arms_executed": False,
    }
