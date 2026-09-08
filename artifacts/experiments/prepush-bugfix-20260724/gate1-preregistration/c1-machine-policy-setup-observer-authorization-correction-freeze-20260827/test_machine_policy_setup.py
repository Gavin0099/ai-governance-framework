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
OWNER_SID_SHA256 = "a" * 64


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


def _identity(
    *,
    sid_sha256: str = OWNER_SID_SHA256,
    account_class: str = "owner_candidate",
    administrator_role_enabled: bool = True,
) -> setup.ExecutionIdentity:
    return setup.ExecutionIdentity(
        sid_sha256=sid_sha256,
        account_class=account_class,
        administrator_role_enabled=administrator_role_enabled,
    )


class FakeAdapter:
    def __init__(self) -> None:
        self.target_path = Path("C:/ProgramData/OpenAI/Codex/requirements.toml")
        self.safe = True
        self.state = _state()
        self.after = _state(target_exists=True)
        self.identity = _identity()
        self.published = b""
        self.write_count = 0
        self.rollback_result = "COMPLETE"
        self.channel = True
        self.regular = True
        self.publication_error = False
        self.identity_error: setup.SetupError | None = None
        self.observer_error: setup.SetupError | None = None
        self.observation_calls: list[str] = []

    def path_is_safe(self) -> bool:
        return self.safe

    def observe_identity(self) -> setup.ExecutionIdentity:
        self.observation_calls.append("identity")
        if self.identity_error:
            raise self.identity_error
        return self.identity

    def observe(self) -> setup.MachineObservation:
        self.observation_calls.append("full")
        if self.observer_error:
            raise self.observer_error
        return setup.MachineObservation(
            identity=self.identity,
            state=self.after if self.write_count else self.state,
        )

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
        "owner_sid_sha256": OWNER_SID_SHA256,
        "owner_account_class": "owner_administrator",
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
    assert adapter.observation_calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("administrator_role_enabled", False),
        ("owner_shell_independent_from_codex", False),
        ("target_absent", False),
        ("shell_held_open_until_terminal", False),
        ("rollback_script_sha256", "0" * 64),
        ("owner_account_class", "sandbox_account"),
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


def test_owner_precheck_sid_mismatch_is_zero_write() -> None:
    adapter = FakeAdapter()
    freeze = "1" * 40
    rollback = (BASE / "independent_owner_rollback.ps1").read_bytes()
    terminal, _, _ = _execute(
        adapter,
        precheck_payload=_precheck(
            freeze, _sha(rollback), owner_sid_sha256="0" * 64
        ),
    )
    assert terminal["status"] == "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE"
    assert adapter.write_count == 0


@pytest.mark.parametrize(
    "identity",
    [
        _identity(sid_sha256="b" * 64),
        _identity(account_class="sandbox_account"),
        _identity(administrator_role_enabled=False),
    ],
)
def test_wrong_or_non_elevated_setup_identity_is_zero_write(
    identity: setup.ExecutionIdentity,
) -> None:
    adapter = FakeAdapter()
    adapter.identity = identity
    terminal, evidence, receipt = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE"
    assert terminal["execution_identity"] == setup.bounded_identity(identity)
    assert terminal["observer_failure"] == {
        "stage": "identity",
        "error_class": "INSUFFICIENT_PRIVILEGE",
    }
    assert adapter.write_count == 0
    assert evidence is receipt is None
    assert adapter.observation_calls == ["identity"]


def test_observer_launch_failure_is_distinct_and_zero_write() -> None:
    adapter = FakeAdapter()
    adapter.identity_error = setup.SetupError(
        "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
        "bounded observer process did not complete",
        observer_stage="launch",
        observer_error_class="PERMISSIONERROR",
    )
    terminal, _, _ = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED"
    assert terminal["observer_failure"] == {
        "stage": "launch",
        "error_class": "PERMISSIONERROR",
    }
    assert terminal["execution_identity"] is None
    assert adapter.write_count == 0


@pytest.mark.parametrize(
    ("error_class", "expected_status"),
    [
        ("INSUFFICIENT_PRIVILEGE", "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE"),
        ("CMDLET_FAILURE", "MACHINE_POLICY_PRECONDITION_FAILED"),
        ("STATE_MISMATCH", "MACHINE_POLICY_PRECONDITION_FAILED"),
    ],
)
def test_bounded_observer_failure_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_class: str,
    expected_status: str,
) -> None:
    identity = setup.bounded_identity(_identity())
    payload = setup.canonical_json(
        {
            "schema": setup.OBSERVATION_SCHEMA,
            "mode": "full",
            "status": "OBSERVATION_FAILED",
            "stage": "firewall_security_filter",
            "error_class": error_class,
            "identity": identity,
            "machine_state": None,
        }
    )
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, payload, b""),
    )
    adapter = setup.WindowsAdapter(
        base=BASE,
        precheck={},
        rollback_request_path=tmp_path / "request.json",
        rollback_receipt_path=tmp_path / "receipt.json",
        rollback_heartbeat_path=tmp_path / "heartbeat.txt",
    )
    with pytest.raises(setup.SetupError) as captured:
        adapter.observe()
    assert captured.value.status == expected_status
    assert captured.value.identity == _identity()
    assert captured.value.observer_stage == "firewall_security_filter"
    assert captured.value.observer_error_class == error_class


def test_malformed_observer_output_is_launch_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, b"not-json", b""),
    )
    adapter = setup.WindowsAdapter(
        base=BASE,
        precheck={},
        rollback_request_path=tmp_path / "request.json",
        rollback_receipt_path=tmp_path / "receipt.json",
        rollback_heartbeat_path=tmp_path / "heartbeat.txt",
    )
    with pytest.raises(setup.SetupError) as captured:
        adapter.observe_identity()
    assert captured.value.status == "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED"
    assert captured.value.observer_error_class == "INVALID_ENVELOPE"


def _passed_identity_payload() -> bytes:
    return setup.canonical_json(
        {
            "schema": setup.OBSERVATION_SCHEMA,
            "mode": "identity",
            "status": "OBSERVATION_PASSED",
            "stage": "identity_complete",
            "error_class": "NONE",
            "identity": setup.bounded_identity(_identity()),
            "machine_state": None,
        }
    )


def _windows_adapter(tmp_path: Path) -> setup.WindowsAdapter:
    return setup.WindowsAdapter(
        base=BASE,
        precheck={},
        rollback_request_path=tmp_path / "request.json",
        rollback_receipt_path=tmp_path / "receipt.json",
        rollback_heartbeat_path=tmp_path / "heartbeat.txt",
    )


def test_default_policy_fails_but_exact_child_bypass_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def authorization_sensitive_runner(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        if "-ExecutionPolicy" not in args:
            return subprocess.CompletedProcess(
                args, 1, b"", b"AuthorizationManager check failed"
            )
        return subprocess.CompletedProcess(args, 0, _passed_identity_payload(), b"")

    default = authorization_sensitive_runner(
        [
            str(setup.EXPECTED_POWERSHELL_PATH),
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(BASE / "machine_policy_observer.ps1"),
            "-Mode",
            "Identity",
        ]
    )
    assert default.returncode == 1
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(setup.subprocess, "run", authorization_sensitive_runner)
    assert _windows_adapter(tmp_path).observe_identity() == _identity()
    child = calls[-1]
    assert child == [
        str(setup.EXPECTED_POWERSHELL_PATH),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BASE / "machine_policy_observer.ps1"),
        "-Mode",
        "Identity",
    ]


def test_wrong_observer_digest_fails_before_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "freeze"
    base.mkdir()
    (base / "machine_policy_observer.ps1").write_bytes(b"wrong observer")
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("child launched before observer verification"),
    )
    adapter = setup.WindowsAdapter(
        base=base,
        precheck={},
        rollback_request_path=tmp_path / "request.json",
        rollback_receipt_path=tmp_path / "receipt.json",
        rollback_heartbeat_path=tmp_path / "heartbeat.txt",
    )
    with pytest.raises(setup.SetupError) as captured:
        adapter.observe_identity()
    assert captured.value.status == "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED"
    assert captured.value.observer_stage == "authorization"
    assert captured.value.observer_error_class == "OBSERVER_DIGEST_MISMATCH"


@pytest.mark.parametrize(
    ("returncode", "stderr"),
    [(1, b""), (0, b"AuthorizationManager check failed"), (1, b"denied")],
)
def test_nonzero_or_stderr_maps_to_existing_authorization_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncode: int,
    stderr: bytes,
) -> None:
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(
            args, returncode, _passed_identity_payload(), stderr
        ),
    )
    with pytest.raises(setup.SetupError) as captured:
        _windows_adapter(tmp_path).observe_identity()
    assert captured.value.status == "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED"
    assert captured.value.observer_stage == "authorization"
    assert captured.value.observer_error_class == "AUTHORIZATION_MANAGER_DENIED"


def test_authorization_manager_denial_is_zero_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(
            args, 1, b"", b"AuthorizationManager check failed"
        ),
    )
    adapter = _windows_adapter(tmp_path)
    monkeypatch.setattr(adapter, "rollback_channel_available", lambda: True)
    terminal, evidence, receipt = _execute(adapter)
    assert terminal["status"] == "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED"
    assert terminal["observer_failure"] == {
        "stage": "authorization",
        "error_class": "AUTHORIZATION_MANAGER_DENIED",
    }
    assert terminal["machine_mutation_attempted"] is False
    assert evidence is receipt is None
    assert not adapter.policy_root.exists()


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
    assert evidence["execution_identity"] == setup.bounded_identity(_identity())
    assert terminal["execution_identity"] == setup.bounded_identity(_identity())
    assert terminal["observer_failure"] is None
    assert adapter.observation_calls == ["identity", "full", "full"]
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
    for stage in (
        "identity", "sandbox_account", "firewall_profiles", "firewall_rules",
        "firewall_rule_set", "firewall_security_filter", "firewall_projection",
        "target_paths",
    ):
        assert f"'{stage}'" in source
    assert "INSUFFICIENT_PRIVILEGE" in source
    assert "CMDLET_FAILURE" in source
    assert "STATE_MISMATCH" in source


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


def test_attempt04_roots_and_attempt03_terminal_are_frozen() -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    assert manifest["publication"] == {
        "output_root": (
            "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
            "c1-machine-policy-setup-attempt-04"
        ),
        "coordination_root": (
            "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
            ".c1-machine-policy-setup-attempt-04-coordination"
        ),
        "terminal": "terminal.json",
        "setup_evidence": "setup-evidence.json",
        "downstream_receipt": "machine-policy-receipt.json",
        "create_once": True,
    }
    prior = manifest["prior_attempt"]
    assert prior["attempt_id"] == "C1-machine-policy-setup-03"
    assert prior["terminal_bytes"] == 616
    assert prior["terminal_sha256"] == (
        "82111edb99d88f2b8f8999026ee1eb440a849019ddb01a582ff9efb010e70a14"
    )
    assert prior["immutable_and_not_retried"] is True


def test_bypass_is_child_scoped_and_terminal_vocabulary_does_not_grow() -> None:
    source = (BASE / "machine_policy_setup.py").read_text(encoding="utf-8")
    assert source.count('"-ExecutionPolicy"') == 1
    assert source.count('"Bypass"') == 1
    assert "Set-ExecutionPolicy" not in source
    assert "CurrentUser" not in source
    assert "LocalMachine" not in source
    policy = json.loads((BASE / "terminal-policy.json").read_text())
    assert len(policy["allowed_terminals_highest_precedence_first"]) == 13
    assert tuple(policy["allowed_terminals_highest_precedence_first"]) == (
        setup.TERMINAL_PRECEDENCE
    )
    assert policy["observer_authorization_denied_requires"] == [
        "existing_observer_launch_failed_terminal",
        "authorization_stage",
        "authorization_manager_denied_error_class",
        "machine_mutation_attempted_false",
    ]


def test_git_identity_uses_bounded_repo_root_without_deep_c_option() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")

    repo = Path("C:/bounded/repo")
    assert setup.resolve_git_head(repo, runner=runner) == "a" * 40
    assert calls == [
        (
            ["git", "rev-parse", "HEAD"],
            {
                "cwd": repo,
                "capture_output": True,
                "text": True,
                "timeout": 10,
                "check": False,
            },
        )
    ]


@pytest.mark.parametrize(
    "runner",
    [
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("launch denied")),
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 128, "", "path failed"),
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, "not-a-commit\n", ""),
    ],
)
def test_git_identity_failures_are_bounded(runner: object) -> None:
    with pytest.raises(setup.SetupError) as caught:
        setup.resolve_git_head(Path("C:/bounded/repo"), runner=runner)
    assert caught.value.status == "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE"
    assert "git" not in caught.value.diagnostic.lower() or len(caught.value.diagnostic) <= 80


def test_deep_freeze_path_does_not_enter_git_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo), "-c", "user.name=freeze-test",
            "-c", "user.email=freeze@example.invalid", "commit", "--allow-empty",
            "-m", "fixture",
        ],
        check=True,
        capture_output=True,
    )
    deep = repo
    for index in range(6):
        deep = deep / (f"freeze-segment-{index}-" + "x" * 24)
    deep.mkdir(parents=True)
    expected = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    assert len(str(deep)) > len(str(repo)) + 200
    assert setup.resolve_git_head(repo) == expected


def test_main_terminalizes_git_identity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = json.loads((BASE / "setup-manifest.json").read_text())
    publication = manifest["publication"]
    coordination = tmp_path / publication["coordination_root"]
    coordination.mkdir(parents=True)
    monkeypatch.setattr(setup, "_repo_root", lambda _base: tmp_path)
    monkeypatch.setattr(setup, "validate_frozen_bindings", lambda *_args: None)
    monkeypatch.setattr(setup, "validate_source_bindings", lambda *_args: None)
    monkeypatch.setattr(
        setup,
        "resolve_git_head",
        lambda _repo: (_ for _ in ()).throw(
            setup.SetupError(
                "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE",
                "bounded Git identity check failed",
            )
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "machine_policy_setup.py",
            "--owner-authorized-freeze-commit", "b" * 40,
            "--owner-authorized-setup-plan-sha256", "c" * 64,
            "--rollback-precheck", str(tmp_path / "unused.json"),
        ],
    )
    assert setup.main() == 2
    output_root = tmp_path / publication["output_root"]
    files = list(output_root.iterdir())
    assert [path.name for path in files] == ["terminal.json"]
    terminal = json.loads(files[0].read_text())
    assert terminal["status"] == "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE"
    assert terminal["executing_commit_verified"] is False
    assert terminal["freeze_commit"] == "0" * 40
    assert terminal["machine_mutation_attempted"] is False


def test_identity_unavailable_terminal_contract_is_frozen() -> None:
    policy = json.loads((BASE / "terminal-policy.json").read_text())
    assert policy["identity_unavailable_requires"] == [
        "executing_commit_verified_false",
        "zero_commit_sentinel",
        "machine_mutation_attempted_false",
        "terminal_only_publication",
    ]
    schema = json.loads((BASE / "terminal-schema.json").read_text())
    conditional = schema["allOf"][0]
    assert conditional["if"]["properties"]["status"]["const"] == (
        "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE"
    )
    required = conditional["then"]["properties"]
    assert required["executing_commit_verified"]["const"] is False
    assert required["freeze_commit"]["const"] == "0" * 40
    assert required["machine_mutation_attempted"]["const"] is False
