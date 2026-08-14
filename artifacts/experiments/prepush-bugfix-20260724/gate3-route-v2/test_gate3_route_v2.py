from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route


RUN_ID = "gate3-v2-synthetic-0001"
PROMPT = b"Produce the synthetic result."
SCHEMA = {
    "additionalProperties": False,
    "properties": {"status": {"enum": ["ok"], "type": "string"}},
    "required": ["status"],
    "type": "object",
}
EXPECTED = {"result.txt": b"synthetic result\n"}


class Runner:
    def __init__(self, result: route.SyntheticResult | None = None) -> None:
        self.calls = 0
        self.result = result or _result()

    def __call__(self) -> route.SyntheticResult:
        self.calls += 1
        return self.result


def _result(
    *,
    exit_code: int = 0,
    stdout: bytes | None = b'{"type":"turn.completed"}\n',
    final_message: bytes | None = b'{"status":"ok"}',
    workspace: dict[str, bytes] | None = None,
    exit_classification: str | None = None,
    stdout_capture: str | None = None,
    final_capture: str | None = None,
    workspace_capture: str | None = None,
) -> route.SyntheticResult:
    return route.SyntheticResult(
        exit_code=exit_code,
        stdout=stdout,
        final_message=final_message,
        workspace=(
            None
            if workspace_capture == "capture_failed"
            else EXPECTED
            if workspace is None
            else workspace
        ),
        exit_classification=exit_classification,
        stdout_capture=stdout_capture,
        final_capture=final_capture,
        workspace_capture=workspace_capture,
    )


def _paths(tmp_path: Path) -> dict[str, Path]:
    roots = {
        "output": tmp_path / "public" / RUN_ID,
        "private": tmp_path / "private",
        "locator": tmp_path / "locators",
        "external": tmp_path / "external",
        "final_pin": tmp_path / "final.sha256",
        "terminal_pin": tmp_path / "terminal.sha256",
    }
    roots["private"].mkdir(parents=True)
    return roots


def _run(
    tmp_path: Path,
    runner: Runner,
    *,
    plan: route.FaultPlan | None = None,
    acl=route._current_user_only,
) -> tuple[route.RouteResult, dict[str, Path]]:
    roots = _paths(tmp_path)
    result = route.orchestrate(
        roots["output"],
        locator_root=roots["locator"],
        external_root=roots["external"],
        run_id=RUN_ID,
        authorization=route.AUTHORIZATION,
        prompt=PROMPT,
        output_schema=SCHEMA,
        expected_workspace=EXPECTED,
        runner=runner,
        fault_plan=plan,
        _acl=acl,
        _trusted_route_root=roots["private"].parent,
    )
    if result.final_receipt is not None:
        roots["final_pin"].write_text(
            route._sha256_file(result.final_receipt), encoding="ascii"
        )
    return result, roots


def _reconcile(
    roots: dict[str, Path], *, plan: route.FaultPlan | None = None
) -> route.RouteResult:
    result = route.reconcile(
        roots["output"],
        locator_root=roots["locator"],
        external_root=roots["external"],
        run_id=RUN_ID,
        authorization=route.AUTHORIZATION,
        fault_plan=plan,
        _trusted_route_root=roots["private"].parent,
    )
    if result.final_receipt is not None and not roots["final_pin"].exists():
        roots["final_pin"].write_text(
            route._sha256_file(result.final_receipt), encoding="ascii"
        )
    if result.external_terminal is not None and not roots["terminal_pin"].exists():
        roots["terminal_pin"].write_text(
            route._sha256_file(result.external_terminal), encoding="ascii"
        )
    return result


def _locator(roots: dict[str, Path]) -> Path:
    return roots["locator"] / RUN_ID / "locator.json"


def _locator_residue(roots: dict[str, Path]) -> bool:
    locator = _locator(roots)
    return locator.exists() or locator.parent.exists()


def _private(roots: dict[str, Path]) -> Path:
    return roots["private"] / f"gate3-v2-{RUN_ID}"


def _action_sha256() -> str:
    return route._sha256_bytes(
        route.action_bytes(
            run_id=RUN_ID,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
        )
    )


def _verify(roots: dict[str, Path]) -> dict[str, object]:
    return route.verify(
        roots["output"],
        locator_root=roots["locator"],
        external_root=roots["external"],
        run_id=RUN_ID,
        expected_action_sha256=_action_sha256(),
        expected_final_sha256=roots["final_pin"].read_text(encoding="ascii"),
        _trusted_route_root=roots["private"].parent,
    )


def _verify_external(roots: dict[str, Path]) -> dict[str, object]:
    return route.verify_external_terminal(
        roots["external"],
        output_root=roots["output"],
        locator_root=roots["locator"],
        run_id=RUN_ID,
        expected_terminal_sha256=roots["terminal_pin"].read_text(encoding="ascii"),
        _trusted_route_root=roots["private"].parent,
    )


def _capture_terminal_pin(roots: dict[str, Path]) -> None:
    terminal = roots["external"] / f"{RUN_ID}.terminal.json"
    roots["terminal_pin"].write_text(route._sha256_file(terminal), encoding="ascii")


def test_success_runs_once_cleans_raw_and_verifies_linkage(tmp_path: Path) -> None:
    runner = Runner()
    result, roots = _run(tmp_path, runner)
    assert runner.calls == 1
    assert result.decision == "SUCCESS"
    assert not _private(roots).exists()
    assert not _locator_residue(roots)
    verification = _verify(roots)
    assert verification == {
        "claim": "synthetic_layer0_only",
        "decision": "SUCCESS",
        "raw_content_revalidated": False,
        "run_id": RUN_ID,
        "status": "PASS",
    }


def test_public_artifacts_exclude_raw_prompt_content_and_private_paths(
    tmp_path: Path,
) -> None:
    _, roots = _run(tmp_path, Runner())
    public = b"".join(path.read_bytes() for path in roots["output"].iterdir())
    assert PROMPT not in public
    assert b"turn.completed" not in public
    assert b'{"status":"ok"}' not in public
    assert str(roots["private"]).encode() not in public
    assert b"stdout.ndjson" not in public
    assert b"final-message.json" not in public


@pytest.mark.parametrize(
    ("result", "failed_check"),
    [
        (_result(exit_code=7), "exit_zero"),
        (_result(stdout=b""), "stdout_ndjson"),
        (_result(stdout=b"not-json\n"), "stdout_ndjson"),
        (_result(final_message=None), "final_schema"),
        (_result(final_message=b'{"status":"wrong"}'), "final_schema"),
        (_result(workspace={"result.txt": b"wrong\n"}), "workspace_matches_expected"),
    ],
)
def test_invalid_observation_publishes_verifiable_negative_receipt(
    tmp_path: Path,
    result: route.SyntheticResult,
    failed_check: str,
) -> None:
    outcome, roots = _run(tmp_path, Runner(result))
    assert outcome.decision == "FAILURE"
    assert not _locator_residue(roots)
    packet = json.loads((roots["output"] / "packet.json").read_bytes())
    assert packet["checks"][failed_check] is False
    assert _verify(roots)["decision"] == "FAILURE"


def test_runner_exception_still_produces_a_closed_negative_seal(
    tmp_path: Path,
) -> None:
    class RaisingRunner:
        calls = 0

        def __call__(self) -> route.SyntheticResult:
            self.calls += 1
            raise RuntimeError("private synthetic detail")

    runner = RaisingRunner()
    result, roots = _run(tmp_path, runner)
    assert runner.calls == 1
    assert result.decision == "FAILURE"
    seal = json.loads((roots["output"] / "seal.json").read_bytes())
    assert seal["observations"] == {
        "exit_classification": "unavailable",
        "final_message": "absent",
        "final_schema": "not_attempted",
        "packet_assembly": "PASS",
        "process_launch": "attempted",
        "stdout_capture": "absent",
        "stdout_ndjson": "not_attempted",
        "workspace_capture": "not_attempted",
        "workspace_validation": "not_attempted",
    }
    public = b"".join(path.read_bytes() for path in roots["output"].glob("*.json"))
    assert b"private synthetic detail" not in public
    assert _verify(roots)["decision"] == "FAILURE"


@pytest.mark.parametrize(
    ("result", "observation", "expected"),
    [
        (
            _result(exit_code=-9, exit_classification="signal_or_termination"),
            "exit_classification",
            "signal_or_termination",
        ),
        (
            _result(stdout=None, stdout_capture="capture_failed"),
            "stdout_capture",
            "capture_failed",
        ),
        (
            _result(final_message=None, final_capture="read_failed"),
            "final_message",
            "read_failed",
        ),
        (
            _result(workspace_capture="capture_failed"),
            "workspace_capture",
            "FAIL",
        ),
    ],
)
def test_acquisition_failure_classes_remain_distinct_and_verifiable(
    tmp_path: Path,
    result: route.SyntheticResult,
    observation: str,
    expected: str,
) -> None:
    outcome, roots = _run(tmp_path, Runner(result))
    assert outcome.decision == "FAILURE"
    seal = json.loads((roots["output"] / "seal.json").read_bytes())
    assert seal["observations"][observation] == expected
    assert _verify(roots)["decision"] == "FAILURE"


def test_cleanup_failure_publishes_immutable_negative_and_retains_locator(
    tmp_path: Path,
) -> None:
    outcome, roots = _run(
        tmp_path, Runner(), plan=route.FaultPlan(cleanup_failures=1)
    )
    original = (roots["output"] / "final.json").read_bytes()
    assert outcome.decision == "FAILURE"
    assert _locator_residue(roots)
    with pytest.raises(route.RouteV2Error, match="locator still exists"):
        _verify(roots)
    recovered = _reconcile(roots)
    assert recovered.decision == "FAILURE"
    assert (roots["output"] / "final.json").read_bytes() == original
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    assert _verify(roots)["decision"] == "FAILURE"


def test_reconcile_does_not_remove_locator_for_a_tampered_final(
    tmp_path: Path,
) -> None:
    _, roots = _run(tmp_path, Runner(), plan=route.FaultPlan(cleanup_failures=1))
    final_path = roots["output"] / "final.json"
    final = json.loads(final_path.read_bytes())
    final["decision"] = "SUCCESS"
    final_path.write_bytes(route._json_bytes(final))
    with pytest.raises(route.RouteV2Error, match="recovery final identity"):
        _reconcile(roots)
    assert _locator_residue(roots)


def test_crash_after_seal_recovers_to_negative_receipt(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="seal"),
        )
    assert _locator_residue(roots)
    assert _private(roots).exists()
    assert not (roots["output"] / "final.json").exists()
    recovered = _reconcile(roots)
    assert recovered.decision == "FAILURE"
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    assert _verify(roots)["decision"] == "FAILURE"


def test_crash_after_cleanup_before_final_recovers_to_verifiable_negative(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash, match="after cleanup"):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="cleanup"),
            _trusted_route_root=roots["private"].parent,
        )
    assert not _private(roots).exists()
    assert _locator_residue(roots)
    assert (roots["output"] / "seal.json").is_file()
    assert not (roots["output"] / "final.json").exists()
    recovered = _reconcile(roots)
    assert recovered.decision == "FAILURE"
    assert not _locator_residue(roots)
    assert _verify(roots)["decision"] == "FAILURE"


def test_crash_before_seal_uses_external_no_admissible_closeout(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="runner"),
        )
    recovered = _reconcile(roots)
    assert recovered.decision == "NO_ADMISSIBLE"
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    assert _verify_external(roots)["admissible_route_result"] is False
    assert not (roots["output"] / "final.json").exists()


@pytest.mark.parametrize("artifact", ["attestation.json", "seal.json"])
def test_preseal_publication_failure_closes_externally_without_route_receipt(
    tmp_path: Path, artifact: str
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.RouteV2Error, match="before seal"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(publication_failures=frozenset({artifact})),
        )
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    assert not (roots["output"] / "final.json").exists()
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_preseal_privacy_failure_closes_externally_without_route_receipt(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.RouteV2Error, match="before seal"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(
                privacy_failures=frozenset({"attestation.json"})
            ),
        )
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_public_privacy_gate_rejects_private_schema_value_before_invocation(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    runner = Runner()
    private_schema = {
        **SCHEMA,
        "properties": {
            "status": {"enum": [r"C:\Users\private\secret"], "type": "string"}
        },
    }
    with pytest.raises(route.RouteV2Error, match="action publication failed"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=private_schema,
            expected_workspace=EXPECTED,
            runner=runner,
        )
    assert runner.calls == 0
    assert not _locator_residue(roots)
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_action_publication_failure_is_an_external_no_admissible_terminal(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    runner = Runner()
    with pytest.raises(route.RouteV2Error, match="action publication failed"):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=runner,
            fault_plan=route.FaultPlan(
                publication_failures=frozenset({"action.json"})
            ),
            _trusted_route_root=roots["private"].parent,
        )
    assert runner.calls == 0
    assert not roots["output"].exists()
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_final_publication_failure_closes_externally_after_cleanup(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.RouteV2Error, match="final receipt publication failed"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(
                publication_failures=frozenset({"final.json"})
            ),
        )
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    assert not (roots["output"] / "final.json").exists()
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_exhausted_final_publication_after_crash_uses_external_closeout(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="seal"),
        )
    outcome = _reconcile(
        roots,
        plan=route.FaultPlan(publication_failures=frozenset({"final.json"})),
    )
    assert outcome.decision == "NO_ADMISSIBLE"
    assert not _locator_residue(roots)
    assert not _private(roots).exists()
    _verify_external(roots)


def test_locator_acl_failure_prevents_invocation_and_removes_partial_locator(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    runner = Runner()

    def reject_acl(_: Path, __: bool) -> None:
        raise route.RouteV2Error("ACL rejected")

    with pytest.raises(route.RouteV2Error, match="prelaunch"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=runner,
            _acl=reject_acl,
        )
    assert runner.calls == 0
    assert not _locator_residue(roots)
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_private_root_acl_failure_is_visible_and_prevents_invocation(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    runner = Runner()

    def reject_private(path: Path, container: bool) -> None:
        if path.name == f"gate3-v2-{RUN_ID}":
            raise route.RouteV2Error("current-user-only ACL verification failed")
        route._current_user_only(path, container)

    with pytest.raises(route.RouteV2Error, match="before seal: private_acl"):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=runner,
            _acl=reject_private,
            _trusted_route_root=roots["private"].parent,
        )
    assert runner.calls == 0
    assert not _private(roots).exists()
    assert not _locator_residue(roots)
    _capture_terminal_pin(roots)
    _verify_external(roots)


def test_locator_tamper_cannot_redirect_cleanup(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    outside = tmp_path / "must-survive.txt"
    outside.write_text("safe", encoding="utf-8")
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="seal"),
        )
    locator = _locator(roots)
    value = json.loads(locator.read_bytes())
    value["cleanup_path"] = str(outside)
    locator.write_bytes(route._json_bytes(value))
    with pytest.raises(route.RouteV2Error, match="locator identity"):
        _reconcile(roots)
    assert outside.read_text(encoding="utf-8") == "safe"
    assert _private(roots).exists()


def test_reconcile_rejects_a_different_cleanup_authority(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="runner"),
            _trusted_route_root=roots["private"].parent,
        )
    alternate = tmp_path / "alternate-private"
    alternate.mkdir()
    with pytest.raises(route.RouteV2Error, match="trusted layout"):
        route.reconcile(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            _trusted_route_root=alternate,
        )
    assert _private(roots).exists()
    assert alternate.exists()
    assert _locator_residue(roots)


def test_reconcile_revalidates_locator_acl_before_cleanup(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="seal"),
        )

    def reject_acl(_: Path, __: bool) -> None:
        raise route.RouteV2Error("current-user-only ACL verification failed")

    with pytest.raises(route.RouteV2Error, match="ACL verification"):
        route.reconcile(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            _acl_verify=reject_acl,
        )
    assert _private(roots).exists()
    assert _locator_residue(roots)


def test_locator_removal_failure_blocks_verification_until_reconciled(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.RouteV2Error, match="locator removal failed"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(locator_removal_failures=1),
        )
    assert _locator_residue(roots)
    roots["final_pin"].write_text(
        route._sha256_file(roots["output"] / "final.json"), encoding="ascii"
    )
    with pytest.raises(route.RouteV2Error, match="locator still exists"):
        _verify(roots)
    _reconcile(roots)
    assert not _locator_residue(roots)
    assert _verify(roots)["decision"] == "SUCCESS"


def test_external_terminal_is_permanent_after_locator_removal_retry(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.RouteV2Error, match="locator removal failed"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(
                publication_failures=frozenset({"final.json"}),
                locator_removal_failures=1,
            ),
        )
    assert _locator_residue(roots)
    assert (roots["external"] / f"{RUN_ID}.terminal.json").is_file()
    recovered = _reconcile(roots)
    assert recovered.decision == "NO_ADMISSIBLE"
    assert not _locator_residue(roots)
    assert not (roots["output"] / "final.json").exists()
    _verify_external(roots)


def test_external_terminal_blocks_a_later_same_run(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    first = Runner()
    with pytest.raises(route.RouteV2Error):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=first,
            fault_plan=route.FaultPlan(
                publication_failures=frozenset({"attestation.json"})
            ),
            _trusted_route_root=roots["private"].parent,
        )
    _capture_terminal_pin(roots)
    second = Runner()
    with pytest.raises(route.RouteV2Error, match="collision"):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=second,
            _trusted_route_root=roots["private"].parent,
        )
    assert first.calls == 1
    assert second.calls == 0
    _verify_external(roots)


def test_route_and_external_verifiers_reject_same_run_coexistence(
    tmp_path: Path,
) -> None:
    _, roots = _run(tmp_path, Runner())
    terminal = roots["external"] / f"{RUN_ID}.terminal.json"
    terminal.parent.mkdir(parents=True, exist_ok=True)
    terminal.write_bytes(
        route._json_bytes(
            route._external_terminal(
                run_id=RUN_ID,
                stage="orphan_without_seal",
                cleanup="PASS",
                locator_absent=False,
            )
        )
    )
    _capture_terminal_pin(roots)
    with pytest.raises(route.RouteV2Error, match="external terminal"):
        _verify(roots)
    with pytest.raises(route.RouteV2Error, match="incomplete"):
        _verify_external(roots)


def test_external_terminal_class_is_closed_even_when_repinning(
    tmp_path: Path,
) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="runner"),
            _trusted_route_root=roots["private"].parent,
        )
    _reconcile(roots)
    terminal = roots["external"] / f"{RUN_ID}.terminal.json"
    value = json.loads(terminal.read_bytes())
    value["terminal"] = "fabricated_success"
    terminal.write_bytes(route._json_bytes(value))
    _capture_terminal_pin(roots)
    with pytest.raises(route.RouteV2Error, match="external terminal is invalid"):
        _verify_external(roots)


@pytest.mark.parametrize(
    "artifact",
    [
        "preflight.json",
        "action.json",
        "attestation.json",
        "packet.json",
        "seal.json",
        "final.json",
    ],
)
def test_mutation_of_any_retained_artifact_fails_verification(
    tmp_path: Path, artifact: str
) -> None:
    _, roots = _run(tmp_path, Runner())
    path = roots["output"] / artifact
    value = json.loads(path.read_bytes())
    value["mutation"] = True
    path.write_bytes(route._json_bytes(value))
    with pytest.raises(route.RouteV2Error):
        _verify(roots)


def test_attestation_substitution_is_rejected(tmp_path: Path) -> None:
    _, roots = _run(tmp_path, Runner())
    path = roots["output"] / "attestation.json"
    value = json.loads(path.read_bytes())
    value["stdout"]["sha256"] = "0" * 64
    path.write_bytes(route._json_bytes(value))
    with pytest.raises(route.RouteV2Error, match="seal linkage"):
        _verify(roots)


def test_coherent_action_rewrite_is_rejected_by_external_pin(tmp_path: Path) -> None:
    _, roots = _run(tmp_path, Runner())
    action_path = roots["output"] / "action.json"
    action = json.loads(action_path.read_bytes())
    action["prompt_sha256"] = "0" * 64
    action_path.write_bytes(route._json_bytes(action))
    packet_path = roots["output"] / "packet.json"
    packet = json.loads(packet_path.read_bytes())
    packet["action_sha256"] = route._sha256_file(action_path)
    packet_path.write_bytes(route._json_bytes(packet))
    seal_path = roots["output"] / "seal.json"
    seal = json.loads(seal_path.read_bytes())
    seal["packet_sha256"] = route._sha256_file(packet_path)
    seal_path.write_bytes(route._json_bytes(seal))
    final_path = roots["output"] / "final.json"
    final = json.loads(final_path.read_bytes())
    final["packet_sha256"] = route._sha256_file(packet_path)
    final["seal_sha256"] = route._sha256_file(seal_path)
    final_path.write_bytes(route._json_bytes(final))
    with pytest.raises(route.RouteV2Error, match="pinned identity"):
        _verify(roots)


def test_coherent_preflight_chain_rewrite_is_rejected_by_external_pin(
    tmp_path: Path,
) -> None:
    _, roots = _run(tmp_path, Runner())
    preflight_path = roots["output"] / "preflight.json"
    preflight = json.loads(preflight_path.read_bytes())
    preflight["environment_policy_sha256"] = "0" * 64
    preflight_path.write_bytes(route._json_bytes(preflight))

    action_path = roots["output"] / "action.json"
    action = json.loads(action_path.read_bytes())
    action["preflight_sha256"] = route._sha256_file(preflight_path)
    action_path.write_bytes(route._json_bytes(action))

    packet_path = roots["output"] / "packet.json"
    packet = json.loads(packet_path.read_bytes())
    packet["action_sha256"] = route._sha256_file(action_path)
    packet_path.write_bytes(route._json_bytes(packet))

    seal_path = roots["output"] / "seal.json"
    seal = json.loads(seal_path.read_bytes())
    seal["packet_sha256"] = route._sha256_file(packet_path)
    seal_path.write_bytes(route._json_bytes(seal))

    final_path = roots["output"] / "final.json"
    final = json.loads(final_path.read_bytes())
    final["packet_sha256"] = route._sha256_file(packet_path)
    final["seal_sha256"] = route._sha256_file(seal_path)
    final_path.write_bytes(route._json_bytes(final))

    with pytest.raises(route.RouteV2Error, match="pinned identity"):
        _verify(roots)


def test_verifier_independently_rejects_private_cleanup_residue(tmp_path: Path) -> None:
    _, roots = _run(tmp_path, Runner())
    residue = _private(roots)
    residue.mkdir()
    (residue / "raw.txt").write_text("private", encoding="utf-8")
    with pytest.raises(route.RouteV2Error, match="cleanup target"):
        _verify(roots)


def test_external_verifier_rejects_private_cleanup_residue(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    with pytest.raises(route.SyntheticCrash):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
            fault_plan=route.FaultPlan(crash_after="runner"),
        )
    _reconcile(roots)
    _private(roots).mkdir()
    with pytest.raises(route.RouteV2Error, match="incomplete"):
        _verify_external(roots)


def test_extra_packet_classification_is_rejected(tmp_path: Path) -> None:
    _, roots = _run(tmp_path, Runner())
    packet_path = roots["output"] / "packet.json"
    packet = json.loads(packet_path.read_bytes())
    packet["checks"]["unknown"] = True
    packet_path.write_bytes(route._json_bytes(packet))
    seal_path = roots["output"] / "seal.json"
    seal = json.loads(seal_path.read_bytes())
    seal["packet_sha256"] = route._sha256_file(packet_path)
    seal_path.write_bytes(route._json_bytes(seal))
    final_path = roots["output"] / "final.json"
    final = json.loads(final_path.read_bytes())
    final["packet_sha256"] = route._sha256_file(packet_path)
    final["seal_sha256"] = route._sha256_file(seal_path)
    final_path.write_bytes(route._json_bytes(final))
    # Deliberately repin the coherently rewritten receipt so this test reaches
    # the semantic verifier instead of stopping at the external identity gate.
    roots["final_pin"].write_text(route._sha256_file(final_path), encoding="ascii")
    with pytest.raises(route.RouteV2Error, match="workspace decision"):
        _verify(roots)


def test_wrong_authorization_and_collision_prevent_invocation(tmp_path: Path) -> None:
    roots = _paths(tmp_path)
    runner = Runner()
    with pytest.raises(route.RouteV2Error, match="authorization"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization="wrong",
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=runner,
        )
    assert runner.calls == 0
    roots["output"].mkdir(parents=True)
    with pytest.raises(route.RouteV2Error, match="collision"):
        route.orchestrate(
            roots["output"],
            _trusted_route_root=roots["private"].parent,
            locator_root=roots["locator"],
            external_root=roots["external"],
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=runner,
        )
    assert runner.calls == 0


def test_route_paths_cannot_deviate_from_the_trusted_layout(
    tmp_path: Path,
) -> None:
    private_parent = tmp_path / "private"
    private_parent.mkdir()
    private_root = private_parent / f"gate3-v2-{RUN_ID}"
    with pytest.raises(route.RouteV2Error, match="trusted layout"):
        route.orchestrate(
            private_root / "public",
            _trusted_route_root=private_parent,
            locator_root=tmp_path / "locators",
            external_root=tmp_path / "external",
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
        )

    output_root = tmp_path / "outer-public"
    nested_private_parent = output_root / "nested-private"
    nested_private_parent.mkdir(parents=True)
    with pytest.raises(route.RouteV2Error, match="trusted layout"):
        route.orchestrate(
            output_root,
            _trusted_route_root=nested_private_parent,
            locator_root=tmp_path / "other-locators",
            external_root=tmp_path / "other-external",
            run_id=RUN_ID,
            authorization=route.AUTHORIZATION,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            runner=Runner(),
        )


def test_default_acl_backend_protects_file_and_directory(tmp_path: Path) -> None:
    directory = tmp_path / "private"
    directory.mkdir()
    file_path = directory / "locator.json"
    file_path.write_text("{}\n", encoding="utf-8")
    route._current_user_only(directory, True)
    route._current_user_only(file_path, False)
