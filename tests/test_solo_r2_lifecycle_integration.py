from __future__ import annotations

import ast
import base64
from dataclasses import fields
import hashlib
import inspect
import json
import os
from pathlib import Path
from unittest import mock
from uuid import uuid4

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_blind_scoring_bundle as scoring_bundle
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_lifecycle_integration as integration


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LEDGER = REPO_ROOT / ledger.PUBLIC_LEDGER_PATH


def _write_key_record(path: Path, key_id: str, key_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(
            {
                "schema_version": controller.CONTROLLER_KEY_SCHEMA,
                "key_id": key_id,
                "key_b64": base64.b64encode(key_bytes).decode("ascii"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _frozen_identities() -> dict[str, str]:
    return {
        "protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
        "contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
        "schema_id": ledger.ADOPTED_SCHEMA_ID,
        "qualification_record_sha256": "a" * 64,
        "historical_base_commit": "b" * 40,
        "historical_fix_commit": "c" * 40,
        "oracle_blob_sha256": "d" * 64,
    }


def _correctness() -> dict[str, object]:
    return {
        "oracle_status": "PASS",
        "required_case_count": 7,
        "passed_case_count": 7,
        "regression_status": "NONE",
        "scope_status": "WITHIN_SCOPE",
    }


def _make_coordinator(
    tmp_path: Path,
) -> tuple[
    integration.SyntheticLifecycleCoordinator,
    controller.CustodyBoundary,
    Path,
    Path,
    Path,
]:
    assert REPO_ROOT.resolve() not in tmp_path.resolve().parents
    roots = {
        name: tmp_path / name
        for name in (
            "consumer",
            "materialization",
            "execution",
            "scoring",
            "ledger",
            "controller-packages",
        )
    }
    for root in roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=REPO_ROOT,
        consumer_root=roots["consumer"],
        materialization_root=roots["materialization"],
        execution_root=roots["execution"],
        scoring_root=roots["scoring"],
    )
    key_path = tmp_path / "controller-custody" / "key.json"
    _write_key_record(key_path, f"solo-r2-{uuid4().hex}", os.urandom(32))
    ledger_path = roots["ledger"] / "synthetic-ledger.ndjson"
    coordinator = integration.SyntheticLifecycleCoordinator.start(
        ledger_path=ledger_path,
        controller_root=roots["controller-packages"],
        scoring_root=roots["scoring"],
        key_path=key_path,
        custody_boundary=boundary,
        evaluation_id=str(uuid4()),
        pair_id="synthetic-r2-shakedown-pair",
        category="bugfix",
        repository="synthetic-consumer",
        frozen_identities=_frozen_identities(),
        preflight_ids=["synthetic-preflight-v2"],
        rubric_id="synthetic-rubric-v1",
    )
    return (
        coordinator,
        boundary,
        key_path,
        roots["controller-packages"],
        roots["scoring"],
    )


def _complete_attempt(
    coordinator: integration.SyntheticLifecycleCoordinator, index: int
) -> str:
    handle = coordinator.admit_attempt()
    coordinator.expose_task(handle)
    coordinator.record_terminal(
        handle,
        correctness_result=_correctness(),
        cost_metrics={"elapsed_ms": 10 + index, "tool_calls": 2},
        output_ref=f"controller-only-output-{index}",
        output_payload=f"identity stripped synthetic output {index}",
    )
    return handle


def _prepare_scoring(
    coordinator: integration.SyntheticLifecycleCoordinator,
) -> integration.ScorerDelivery:
    _complete_attempt(coordinator, 0)
    _complete_attempt(coordinator, 1)
    return coordinator.prepare_scoring()


def test_complete_synthetic_lifecycle_composes_all_three_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_before = CANONICAL_LEDGER.read_bytes()
    observed_nonces: list[str] = []
    original_seal = controller.seal_controller_state

    def capture_seal(*args, **kwargs):
        package = original_seal(*args, **kwargs)
        envelope = controller.parse_sealed_package(package.package_bytes)
        observed_nonces.append(envelope["nonce_b64"])
        return package

    monkeypatch.setattr(controller, "seal_controller_state", capture_seal)
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    bundle = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)
    assert coordinator.acknowledge_score(bundle["presentation_order"][0]) == 1
    assert coordinator.acknowledge_score(bundle["presentation_order"][1]) == 2
    result = coordinator.authenticate_synthetic_unblinding()

    summary = ledger.validate_ledger_file(coordinator.ledger_path)
    assert summary.ledger_event_count == 11
    assert summary.pair_count == 1
    assert summary.admitted_attempt_count == 2
    assert summary.initiated_attempt_count == 2
    assert summary.terminal_execution_count == 2
    assert summary.scoring_record_count == 1
    assert summary.unblinding_record_count == 1
    assert len(result.scoring_label_to_arm) == 2
    assert {arm for _, arm in result.scoring_label_to_arm} == {
        "CONTROL",
        "TREATMENT",
    }
    assert len(observed_nonces) == 4
    assert len(set(observed_nonces)) == 4
    assert len(list(controller_root.glob("*.sealed.json"))) == 3
    assert CANONICAL_LEDGER.read_bytes() == canonical_before


def test_attempt_bound_uses_one_atomic_current_checkpoint_path(tmp_path: Path) -> None:
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    first = _complete_attempt(coordinator, 0)
    attempt_paths = list(controller_root.glob("*.attempt-bound.sealed.json"))
    assert len(attempt_paths) == 1
    path = attempt_paths[0]
    first_bytes = path.read_bytes()

    second = coordinator.admit_attempt()
    second_bytes = path.read_bytes()
    assert first != second
    assert second_bytes != first_bytes
    assert list(controller_root.glob("*.attempt-bound.sealed.json")) == [path]
    assert all(
        token not in path.name
        for token in (first, second, "CONTROL", "TREATMENT", "ordinal")
    )


def test_scorer_delivery_is_the_exact_minimum_capability(tmp_path: Path) -> None:
    coordinator, _, key_path, controller_root, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    assert [field.name for field in fields(delivery)] == [
        "bundle_path",
        "bundle_bytes",
    ]
    assert delivery.bundle_path.read_bytes() == delivery.bundle_bytes
    assert delivery.bundle_path.parent != controller_root
    assert str(key_path) not in repr(delivery)
    assert str(coordinator.ledger_path) not in repr(delivery)
    parsed = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)
    assert set(parsed) == {
        "schema_version",
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "rubric_id",
        "presentation_order",
        "outputs",
    }


def test_public_ledger_is_revalidated_instead_of_trusting_memory(tmp_path: Path) -> None:
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    events = ledger.read_ledger(coordinator.ledger_path)
    events[1]["category"] = "changed-after-start"
    coordinator.ledger_path.write_bytes(b"".join(ledger.encode_event(e) for e in events))

    with pytest.raises(integration.LifecycleIntegrationError) as caught:
        coordinator.admit_attempt()
    assert caught.value.code == integration.V2_CONFORMANCE_FAILURE
    assert not list(controller_root.glob("*.attempt-bound.sealed.json"))


def test_existing_ledger_cannot_be_resumed_or_replaced(tmp_path: Path) -> None:
    coordinator, boundary, key_path, controller_root, scoring_root = _make_coordinator(
        tmp_path
    )
    assert not hasattr(integration.SyntheticLifecycleCoordinator, "resume")
    original = coordinator.ledger_path.read_bytes()

    with pytest.raises(integration.LifecycleIntegrationError) as caught:
        integration.SyntheticLifecycleCoordinator.start(
            ledger_path=coordinator.ledger_path,
            controller_root=controller_root,
            scoring_root=scoring_root,
            key_path=key_path,
            custody_boundary=boundary,
            evaluation_id=str(uuid4()),
            pair_id="replacement-pair",
            category="bugfix",
            repository="synthetic-consumer",
            frozen_identities=_frozen_identities(),
            preflight_ids=["synthetic-preflight-v2"],
            rubric_id="synthetic-rubric-v1",
        )
    assert caught.value.code == integration.V2_CONFORMANCE_FAILURE
    assert coordinator.ledger_path.read_bytes() == original


def test_admitted_not_exposed_reserves_without_consuming_and_stops(
    tmp_path: Path,
) -> None:
    coordinator, _, _, _, _ = _make_coordinator(tmp_path)
    handle = coordinator.admit_attempt()
    summary = coordinator.record_admitted_not_exposed(handle)
    assert summary.admitted_attempt_count == 1
    assert summary.initiated_attempt_count == 0
    assert ledger.read_ledger(coordinator.ledger_path)[-1]["event_type"] == (
        "ADMITTED_NOT_EXPOSED"
    )
    with pytest.raises(integration.LifecycleIntegrationError):
        coordinator.expose_task(handle)


def test_second_attempt_requires_first_terminal(tmp_path: Path) -> None:
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    first = coordinator.admit_attempt()
    before = next(controller_root.glob("*.attempt-bound.sealed.json")).read_bytes()
    with pytest.raises(integration.LifecycleIntegrationError):
        coordinator.admit_attempt()
    after = next(controller_root.glob("*.attempt-bound.sealed.json")).read_bytes()
    assert before == after
    assert [
        event["attempt_handle"]
        for event in ledger.read_ledger(coordinator.ledger_path)
        if event["event_type"] == "ATTEMPT_ADMITTED"
    ] == [first]


def test_prepare_scoring_requires_two_terminal_outputs(tmp_path: Path) -> None:
    coordinator, _, _, _, scoring_root = _make_coordinator(tmp_path)
    _complete_attempt(coordinator, 0)
    with pytest.raises(integration.LifecycleIntegrationError):
        coordinator.prepare_scoring()
    assert not list(scoring_root.iterdir())


def test_duplicate_score_acknowledgement_is_terminal_and_records_no_score(
    tmp_path: Path,
) -> None:
    coordinator, _, _, _, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    labels = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)[
        "presentation_order"
    ]
    assert coordinator.acknowledge_score(labels[0]) == 1
    with pytest.raises(integration.LifecycleIntegrationError):
        coordinator.acknowledge_score(labels[0])
    summary = ledger.validate_ledger_file(coordinator.ledger_path)
    assert summary.scoring_record_count == 0
    assert ledger.read_ledger(coordinator.ledger_path)[-1]["event_type"] == (
        "CONTROLLER_STATE_SEALED"
    )


def test_premature_unblinding_records_only_pair_level_count_and_never_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, _, _, _, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    label = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)[
        "presentation_order"
    ][0]
    coordinator.acknowledge_score(label)
    opened = mock.Mock()
    monkeypatch.setattr(controller, "open_controller_package", opened)

    with pytest.raises(integration.LifecycleIntegrationError) as caught:
        coordinator.authenticate_synthetic_unblinding()
    assert caught.value.code == integration.PREMATURE_UNBLINDING_STOP
    opened.assert_not_called()
    event = ledger.read_ledger(coordinator.ledger_path)[-1]
    assert event["event_type"] == "PREMATURE_UNBLINDING"
    assert event["score_count"] == 1
    assert "attempt_handle" not in event


def test_checkpoint_replace_failure_preserves_old_bytes_and_public_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    _complete_attempt(coordinator, 0)
    checkpoint = next(controller_root.glob("*.attempt-bound.sealed.json"))
    old_bytes = checkpoint.read_bytes()

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("synthetic replacement failure")

    monkeypatch.setattr(integration.os, "replace", fail_replace)
    with pytest.raises(controller.ControllerStateError) as caught:
        coordinator.admit_attempt()
    assert caught.value.code == controller.SEALING_FAILURE
    assert checkpoint.read_bytes() == old_bytes
    assert not list(controller_root.glob(".*.tmp"))
    assert ledger.validate_ledger_file(coordinator.ledger_path).admitted_attempt_count == 1


def test_lifecycle_nonce_collision_fails_before_private_or_public_advance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_urandom = controller.os.urandom
    entropy_counter = 0

    def synthetic_urandom(length: int) -> bytes:
        nonlocal entropy_counter
        if length == 12:
            return b"n" * 12
        if length == 32:
            entropy_counter += 1
            return hashlib.sha256(str(entropy_counter).encode()).digest()
        return original_urandom(length)

    monkeypatch.setattr(controller.os, "urandom", synthetic_urandom)
    coordinator, _, _, controller_root, _ = _make_coordinator(tmp_path)
    with pytest.raises(controller.ControllerStateError) as caught:
        coordinator.admit_attempt()
    assert caught.value.code == controller.SEALING_FAILURE
    assert not list(controller_root.glob("*.attempt-bound.sealed.json"))
    assert ledger.validate_ledger_file(coordinator.ledger_path).admitted_attempt_count == 0


def test_wrong_key_after_scoring_fails_without_unblinding_event(tmp_path: Path) -> None:
    coordinator, _, key_path, _, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    labels = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)[
        "presentation_order"
    ]
    coordinator.acknowledge_score(labels[0])
    coordinator.acknowledge_score(labels[1])
    key_record = json.loads(key_path.read_text(encoding="utf-8"))
    _write_key_record(key_path, key_record["key_id"], os.urandom(32))

    with pytest.raises(controller.ControllerStateError) as caught:
        coordinator.authenticate_synthetic_unblinding()
    assert caught.value.code == controller.AUTHENTICATION_FAILURE
    assert ledger.validate_ledger_file(coordinator.ledger_path).unblinding_record_count == 0


def test_quality_score_values_are_not_an_integration_input_or_public_field(
    tmp_path: Path,
) -> None:
    assert set(inspect.signature(
        integration.SyntheticLifecycleCoordinator.acknowledge_score
    ).parameters) == {"self", "scoring_label"}
    coordinator, _, _, _, _ = _make_coordinator(tmp_path)
    delivery = _prepare_scoring(coordinator)
    labels = scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)[
        "presentation_order"
    ]
    coordinator.acknowledge_score(labels[0])
    coordinator.acknowledge_score(labels[1])
    score_event = ledger.read_ledger(coordinator.ledger_path)[-1]
    assert set(score_event) == {
        "schema_version",
        "event_seq",
        "event_type",
        "event_id",
        "timestamp_utc",
        "pair_id",
        "slot",
        "sealed_package_digest",
        "score_count",
    }
    assert score_event["score_count"] == 2


def test_import_graph_is_one_way_and_existing_boundaries_do_not_import_integration(
) -> None:
    integration_path = REPO_ROOT / "governance_tools/solo_r2_lifecycle_integration.py"
    tree = ast.parse(integration_path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {
        "solo_attempt_ledger_v2",
        "solo_r2_blind_scoring_bundle",
        "solo_r2_controller_state",
        "solo_r2_random_domains",
    }.issubset(imported)

    for name in (
        "solo_attempt_ledger_v2.py",
        "solo_r2_controller_state.py",
        "solo_r2_blind_scoring_bundle.py",
        "solo_r2_random_domains.py",
    ):
        source = (REPO_ROOT / "governance_tools" / name).read_text(encoding="utf-8")
        assert "solo_r2_lifecycle_integration" not in source


def test_canonical_ledger_path_is_rejected_before_any_write(tmp_path: Path) -> None:
    canonical_before = CANONICAL_LEDGER.read_bytes()
    governance_root = tmp_path / "governance-root"
    synthetic_canonical = governance_root / ledger.PUBLIC_LEDGER_PATH
    synthetic_canonical.parent.mkdir(parents=True)
    assert not synthetic_canonical.exists()
    roots = {name: tmp_path / name for name in ("consumer", "materialization", "execution", "scoring", "controller")}
    for root in roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=governance_root,
        consumer_root=roots["consumer"],
        materialization_root=roots["materialization"],
        execution_root=roots["execution"],
        scoring_root=roots["scoring"],
    )
    key_path = tmp_path / "custody" / "key.json"
    _write_key_record(key_path, f"solo-r2-{uuid4().hex}", os.urandom(32))

    with pytest.raises(integration.LifecycleIntegrationError):
        integration.SyntheticLifecycleCoordinator.start(
            ledger_path=synthetic_canonical,
            controller_root=roots["controller"],
            scoring_root=roots["scoring"],
            key_path=key_path,
            custody_boundary=boundary,
            evaluation_id=str(uuid4()),
            pair_id="synthetic-r2-shakedown-pair",
            category="bugfix",
            repository="synthetic-consumer",
            frozen_identities=_frozen_identities(),
            preflight_ids=["synthetic-preflight-v2"],
            rubric_id="synthetic-rubric-v1",
        )
    assert not synthetic_canonical.exists()
    assert CANONICAL_LEDGER.read_bytes() == canonical_before
    assert not list(roots["controller"].iterdir())
    assert not list(roots["scoring"].iterdir())


def test_module_has_no_execution_entrypoint_and_no_real_state(tmp_path: Path) -> None:
    canonical_before = CANONICAL_LEDGER.read_bytes()
    assert not hasattr(integration, "main")
    assert not hasattr(integration.SyntheticLifecycleCoordinator, "resume")
    coordinator, _, _, _, _ = _make_coordinator(tmp_path)
    events = ledger.read_ledger(coordinator.ledger_path)
    assert [event["event_type"] for event in events] == [
        "V2_GENESIS",
        "PAIR_CREATED",
    ]
    assert coordinator.ledger_path != CANONICAL_LEDGER
    assert CANONICAL_LEDGER.read_bytes() == canonical_before
