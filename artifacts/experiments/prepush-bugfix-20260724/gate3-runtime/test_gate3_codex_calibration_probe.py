from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_calibration as calibration
import gate3_codex_calibration_probe as probe
import gate3_codex_live_canary as live
import test_gate3_codex_live_canary as fixtures


def _identity() -> dict[str, str]:
    return {
        "cli_version": live.DEFAULT_CLI_VERSION,
        "comp_hash": live.DEFAULT_COMP_HASH,
        "effort": live.DEFAULT_REASONING,
        "model": live.DEFAULT_MODEL,
    }


def _implementation() -> dict[str, str]:
    return {
        field: f"{index:064x}"
        for index, field in enumerate(sorted(probe.IMPLEMENTATION_FIELDS), 1)
    }


class SyntheticRunner:
    def __init__(
        self,
        *,
        result: probe.RunnerResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.calls = 0
        self.result = result or probe.RunnerResult(fixtures._rollout(), 0)
        self.error = error

    def __call__(self) -> probe.RunnerResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def _synthetic_acl(calls: list[tuple[Path, bool]]):
    def apply(path: Path, container: bool) -> None:
        assert path.exists()
        calls.append((path, container))

    return apply


def _run(
    public_root: Path,
    private_root: Path,
    runner: SyntheticRunner,
    *,
    authorization: str = calibration.AUTHORIZATION,
    acl_calls: list[tuple[Path, bool]] | None = None,
    publisher=probe._publish_create_once_owned,
) -> probe.ProbeResult:
    if acl_calls is None:
        acl_calls = []
    return probe.orchestrate(
        public_root / "probe.json",
        run_id="gate3-calibration-synthetic",
        authorization=authorization,
        expected_workspace=fixtures.WORKSPACE,
        expected_prompt=b"frozen prompt",
        signed_identity=_identity(),
        implementation_identity=_implementation(),
        private_parent=private_root,
        runner=runner,
        _acl_setter=_synthetic_acl(acl_calls),
        _publisher=publisher,
    )


def test_success_calls_runner_once_and_publishes_two_closed_artifacts(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner()
    acl_calls: list[tuple[Path, bool]] = []
    with tempfile.TemporaryDirectory() as private:
        result = _run(tmp_path, Path(private), runner, acl_calls=acl_calls)
        assert runner.calls == 1
        public = json.loads(result.public_receipt.read_bytes())
        private_value = json.loads(result.private_artifact.read_bytes())
        assert public["schema"] == probe.PUBLIC_SCHEMA
        assert public["execution"] == {
            "runner_invocations": 1,
            "runner_retries_by_orchestrator": 0,
            "runner_status": "PASS",
        }
        assert public["admission_performed"] is False
        assert public["scoreable"] is False
        assert public["success_packet_capable"] is False
        assert public["implementation"] == _implementation()
        assert public["private_artifact_disclosure"] == {
            "digest_published": False,
            "path_published": False,
        }
        public_bytes = result.public_receipt.read_bytes()
        assert str(result.private_artifact).encode() not in public_bytes
        assert b"decision.json" not in public_bytes
        assert fixtures.WORKSPACE.encode() not in public_bytes
        assert private_value["schema"] == probe.PRIVATE_SCHEMA
        assert private_value["open_ruling_values"] == {
            "originator": {"status": "single", "values": ["Codex Desktop"]},
            "source": {"status": "single", "values": ["exec"]},
        }
        assert private_value["ordered_developer_instruction_sha256"] == public[
            "calibration"
        ]["instruction_record_sha256"]["developer"]
        assert private_value["unknown_context_field_census"] == []
        private_bytes = result.private_artifact.read_bytes()
        assert fixtures.WORKSPACE.encode() not in private_bytes
        assert b"frozen prompt" not in private_bytes
        assert set(result.private_artifact.parent.iterdir()) == {
            result.private_artifact
        }
        assert [container for _, container in acl_calls] == [True, False, False]


def test_private_unknown_names_never_cross_the_public_projection(
    tmp_path: Path,
) -> None:
    records = [json.loads(line) for line in fixtures._rollout().splitlines()]
    records[0]["payload"]["private_probe_name"] = "private-probe-value"
    rollout = b"".join(fixtures._line(record) for record in records)
    runner = SyntheticRunner(result=probe.RunnerResult(rollout, 0))
    with tempfile.TemporaryDirectory() as private:
        result = _run(tmp_path, Path(private), runner)
        private_value = json.loads(result.private_artifact.read_bytes())
        public = json.loads(result.public_receipt.read_bytes())
        assert private_value["unknown_context_field_census"] == [
            {
                "class": "session_meta",
                "count": 1,
                "name": "private_probe_name",
            }
        ]
        assert public["calibration"]["unknown_context_class_counts"] == {
            field_class: int(field_class == "session_meta")
            for field_class in calibration.UNKNOWN_CONTEXT_CLASSES
        }
        public_bytes = result.public_receipt.read_bytes()
        assert b"private_probe_name" not in public_bytes
        assert b"private-probe-value" not in public_bytes


def test_wrong_authorization_publishes_zero_invocation_failure(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner()
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError, match="authorization is invalid"):
            _run(
                tmp_path,
                Path(private),
                runner,
                authorization="wrong",
            )
        assert runner.calls == 0
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["failure_stage"] == "authorization"
        assert receipt["execution"]["runner_invocations"] == 0
        assert receipt["cleanup"] == {"residue_classes": [], "status": "PASS"}


def test_runner_failure_is_not_replaced_and_cleans_private_runtime(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner(error=RuntimeError("private raw failure"))
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError, match="orchestration failed"):
            _run(tmp_path, private_parent, runner)
        assert runner.calls == 1
        assert list(private_parent.iterdir()) == []
        receipt_bytes = (tmp_path / "probe.json.failure.json").read_bytes()
        assert b"private raw failure" not in receipt_bytes
        receipt = json.loads(receipt_bytes)
        assert receipt["failure_stage"] == "runner"
        assert receipt["execution"] == {
            "runner_invocations": 1,
            "runner_retries_by_orchestrator": 0,
        }
        assert receipt["cleanup"] == {"residue_classes": [], "status": "PASS"}


def test_runner_cleanup_residue_is_projected_into_negative_receipt(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner(
        error=probe.ProbeError(
            "synthetic runner cleanup failure",
            residue_classes=("runner_private_runtime",),
        )
    )
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError):
            _run(tmp_path, Path(private), runner)
    receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
    assert receipt["cleanup"] == {
        "residue_classes": ["runner_private_runtime"],
        "status": "FAIL",
    }
    assert not (tmp_path / "probe.json").exists()


@pytest.mark.parametrize(
    "result",
    [
        probe.RunnerResult(fixtures._rollout(), True),
        probe.RunnerResult(fixtures._rollout(), 12),
    ],
)
def test_invalid_runner_receipts_fail_closed(
    tmp_path: Path, result: probe.RunnerResult
) -> None:
    runner = SyntheticRunner(result=result)
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError):
            _run(tmp_path, Path(private), runner)
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["failure_stage"] == "runner_receipt"
        assert receipt["scoreable"] is False


def test_malformed_rollout_is_a_collector_failure_not_probe_success(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner(result=probe.RunnerResult(b"not-json\n", 0))
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError, match="rollout source is invalid"):
            _run(tmp_path, Path(private), runner)
        assert not (tmp_path / "probe.json").exists()
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["failure_stage"] == "collector"


def test_collector_failure_publishes_negative_and_removes_private_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = SyntheticRunner()

    def fail_collect(*_args, **_kwargs):
        raise live.CanaryError("synthetic collector failure")

    monkeypatch.setattr(probe.calibration, "collect", fail_collect)
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError, match="orchestration failed"):
            _run(tmp_path, private_parent, runner)
        assert list(private_parent.iterdir()) == []
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["failure_stage"] == "collector"


def test_private_publication_failure_cleans_and_redacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = SyntheticRunner()

    def fail_private(*_args, **_kwargs):
        raise RuntimeError("C:/Users/private/private-decision.json")

    monkeypatch.setattr(probe, "_atomic_private_publish", fail_private)
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError, match="orchestration failed"):
            _run(tmp_path, private_parent, runner)
        assert list(private_parent.iterdir()) == []
        payload = (tmp_path / "probe.json.failure.json").read_bytes()
        assert b"C:/Users/private" not in payload
        assert json.loads(payload)["failure_stage"] == "private_publication"


def test_success_publication_failure_leaves_only_negative_receipt(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner()
    calls = 0

    def fail_success_then_publish_failure(path: Path, payload: bytes) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            probe._publish_create_once_owned(path, payload)
            raise probe.PublicationError(linked_by_this_call=True)
        return probe._publish_create_once_owned(path, payload)

    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.PublicationError):
            _run(
                tmp_path,
                private_parent,
                runner,
                publisher=fail_success_then_publish_failure,
            )
        assert not (tmp_path / "probe.json").exists()
        assert (tmp_path / "probe.json.failure.json").is_file()
        assert list(private_parent.iterdir()) == []


def test_private_artifact_is_create_once_and_never_replaces_collision() -> None:
    calls: list[tuple[Path, bool]] = []
    with tempfile.TemporaryDirectory() as private:
        root = probe._allocate_private_root(Path(private))
        destination = root / "decision.json"
        destination.write_bytes(b"foreign")
        with pytest.raises(probe.ProbeError, match="private artifact collision"):
            probe._atomic_private_publish(
                root,
                b"new\n",
                _synthetic_acl(calls),
            )
        assert destination.read_bytes() == b"foreign"
        assert not (root / "decision.json.tmp").exists()


def test_acl_setup_failure_keeps_root_visible_to_cleanup_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = SyntheticRunner()

    def fail_acl(_path: Path, _container: bool) -> None:
        raise probe.ProbeError("synthetic ACL failure")

    def leave_residue(_root: Path | None) -> None:
        return None

    monkeypatch.setattr(probe, "_remove_private_root", leave_residue)
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError, match="synthetic ACL failure"):
            probe.orchestrate(
                tmp_path / "probe.json",
                run_id="gate3-calibration-synthetic",
                authorization=calibration.AUTHORIZATION,
                expected_workspace=fixtures.WORKSPACE,
                expected_prompt=b"frozen prompt",
                signed_identity=_identity(),
                implementation_identity=_implementation(),
                private_parent=private_parent,
                runner=runner,
                _acl_setter=fail_acl,
            )
        assert runner.calls == 0
        assert len(list(private_parent.iterdir())) == 1
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["failure_stage"] == "private_setup"
        assert receipt["cleanup"] == {
            "residue_classes": ["private_runtime"],
            "status": "FAIL",
        }


def test_identical_colliding_public_bytes_are_not_treated_as_owned(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner()
    calls = 0

    def collide_then_publish_failure(path: Path, payload: bytes) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            probe._publish_create_once_owned(path, payload)
            raise probe.PublicationError(linked_by_this_call=False)
        return probe._publish_create_once_owned(path, payload)

    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.PublicationError):
            _run(
                tmp_path,
                Path(private),
                runner,
                publisher=collide_then_publish_failure,
            )
    assert (tmp_path / "probe.json").is_file()
    failure = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
    assert failure["cleanup"] == {
        "residue_classes": ["success_output"],
        "status": "FAIL",
    }


def test_failure_receipt_has_closed_privacy_safe_schema(tmp_path: Path) -> None:
    runner = SyntheticRunner(error=RuntimeError("Bearer private-token"))
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError):
            _run(tmp_path, Path(private), runner)
    payload = (tmp_path / "probe.json.failure.json").read_bytes()
    receipt = json.loads(payload)
    assert set(receipt) == {
        "admission_performed",
        "authorization",
        "cleanup",
        "execution",
        "failure_stage",
        "implementation",
        "non_counted",
        "private_artifact_disclosure",
        "run_id",
        "schema",
        "scoreable",
        "success_packet_capable",
    }
    assert b"Bearer" not in payload
    assert live._privacy_violations(payload) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL contract")
def test_default_acl_is_current_user_only() -> None:
    with tempfile.TemporaryDirectory() as private:
        root = probe._allocate_private_root(Path(private))
        try:
            probe._windows_current_user_only_acl(root, True)
            artifact = probe._atomic_private_publish(
                root,
                b"{}\n",
                probe._windows_current_user_only_acl,
            )
            assert artifact.is_file()
        finally:
            probe._remove_private_root(root)


def test_output_collision_refuses_before_runner(tmp_path: Path) -> None:
    target = tmp_path / "probe.json"
    target.write_text("existing", encoding="utf-8")
    runner = SyntheticRunner()
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError, match="output collision"):
            _run(tmp_path, Path(private), runner)
    assert runner.calls == 0
    assert target.read_text(encoding="utf-8") == "existing"
    assert not (tmp_path / "probe.json.failure.json").exists()


def test_invalid_frozen_identity_refuses_before_runner(tmp_path: Path) -> None:
    runner = SyntheticRunner()
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError, match="orchestration failed"):
            probe.orchestrate(
                tmp_path / "probe.json",
                run_id="gate3-calibration-synthetic",
                authorization=calibration.AUTHORIZATION,
                expected_workspace=fixtures.WORKSPACE,
                expected_prompt=b"frozen prompt",
                signed_identity={**_identity(), "model": "contains space"},
                implementation_identity=_implementation(),
                private_parent=Path(private),
                runner=runner,
                _acl_setter=_synthetic_acl([]),
            )
    assert runner.calls == 0
    receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
    assert receipt["failure_stage"] == "frozen_input"
    assert receipt["execution"]["runner_invocations"] == 0


def test_invalid_implementation_identity_refuses_before_runner(
    tmp_path: Path,
) -> None:
    runner = SyntheticRunner()
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(
            probe.ProbeError,
            match="implementation identity is invalid",
        ):
            probe.orchestrate(
                tmp_path / "probe.json",
                run_id="gate3-calibration-synthetic",
                authorization=calibration.AUTHORIZATION,
                expected_workspace=fixtures.WORKSPACE,
                expected_prompt=b"frozen prompt",
                signed_identity=_identity(),
                implementation_identity={**_implementation(), "extra": "0" * 64},
                private_parent=Path(private),
                runner=runner,
                _acl_setter=_synthetic_acl([]),
            )
    assert runner.calls == 0
    assert not (tmp_path / "probe.json").exists()


def test_cleanup_retries_before_negative_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = SyntheticRunner(error=RuntimeError("runner failed"))
    original = probe._remove_private_root
    calls = 0

    def fail_once(root: Path | None) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic cleanup failure")
        original(root)

    monkeypatch.setattr(probe, "_remove_private_root", fail_once)
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError):
            _run(tmp_path, private_parent, runner)
        assert list(private_parent.iterdir()) == []
    receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
    assert receipt["cleanup"] == {"residue_classes": [], "status": "PASS"}


def test_persistent_cleanup_failure_blocks_success_and_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = SyntheticRunner(error=RuntimeError("runner failed"))

    def never_removes(_root: Path | None) -> None:
        raise OSError("synthetic persistent cleanup failure")

    monkeypatch.setattr(probe, "_remove_private_root", never_removes)
    with tempfile.TemporaryDirectory() as private:
        with pytest.raises(probe.ProbeError):
            _run(tmp_path, Path(private), runner)
        receipt = json.loads((tmp_path / "probe.json.failure.json").read_bytes())
        assert receipt["cleanup"] == {
            "residue_classes": ["private_runtime"],
            "status": "FAIL",
        }
        assert not (tmp_path / "probe.json").exists()


def test_public_output_cannot_overlap_private_temp() -> None:
    runner = SyntheticRunner()
    with tempfile.TemporaryDirectory() as private:
        private_parent = Path(private)
        with pytest.raises(probe.ProbeError, match="overlaps private Temp"):
            probe.orchestrate(
                private_parent / "probe.json",
                run_id="gate3-calibration-synthetic",
                authorization=calibration.AUTHORIZATION,
                expected_workspace=fixtures.WORKSPACE,
                expected_prompt=b"frozen prompt",
                signed_identity=_identity(),
                implementation_identity=_implementation(),
                private_parent=private_parent,
                runner=runner,
                _acl_setter=_synthetic_acl([]),
            )
        assert runner.calls == 0
        assert not (private_parent / "probe.json.failure.json").exists()
