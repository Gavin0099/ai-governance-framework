from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_final_message_diagnostic_integration as integration


REVIEWED_MODULE_BYTES = Path(integration.__file__).read_bytes()
integration.configure_reviewed_implementation_source(REVIEWED_MODULE_BYTES)


def _captured(files: dict[str, bytes]) -> integration.CapturedByteSet:
    return integration.captured_package(files)


def _authority(files: dict[str, bytes]) -> integration.VerificationAuthority:
    return integration.VerificationAuthority(
        expected_tree_manifest_sha256=integration.sha256(files["tree-manifest.json"]),
        expected_verifier_sha256=integration.sha256(
            REVIEWED_MODULE_BYTES
        ),
        expected_execution_command_contract_sha256=integration.sha256(
            integration.EXECUTION_COMMAND_CONTRACT_BYTES
        ),
    )


def _verify(files: dict[str, bytes]) -> dict[str, object]:
    return integration.verify_captured_package(_captured(files), _authority(files))


def _operational_store(files: dict[str, bytes]) -> integration.CreateOnceStore:
    return integration.CreateOnceStore(
        {
            path: payload
            for path, payload in files.items()
            if path.endswith(".json")
            and path != "tree-manifest.json"
            and not path.startswith(("schemas/", "contracts/", "fixtures/", "implementation-identities/"))
        }
    )


def _rewrite_manifest(files: dict[str, bytes], profile: str) -> None:
    payloads = {k: v for k, v in files.items() if k != "tree-manifest.json"}
    files["tree-manifest.json"] = integration._manifest(profile, payloads)


def _mutate_json(files: dict[str, bytes], path: str, mutate: object) -> None:
    value = json.loads(files[path])
    mutate(value)
    files[path] = integration.canonical_bytes(value)


@pytest.mark.parametrize("profile", ["FINALIZED_CHAIN", "RECOVERY_REQUIRED_NEGATIVE"])
def test_route_profiles_reconstruct_from_retained_bytes(profile: str) -> None:
    files = integration.build_complete_route(profile)
    result = _verify(files)
    assert result == {
        "evidence_level": "CAPTURED_BYTE_SET_RECONSTRUCTED",
        "profile": profile,
        "verified": True,
    }
    assert "locator-snapshot.json" in files
    assert "recovery-transition-projection.json" in files
    assert any(path.startswith("recovery-transitions/") for path in files)
    assert ("finalization.json" in files) is (profile == "FINALIZED_CHAIN")


@pytest.mark.parametrize("profile", ["EXTERNAL_RECOVERY_OPEN", "EXTERNAL_RECOVERY_CLOSED"])
def test_external_profiles_reconstruct(profile: str) -> None:
    files = integration.build_external(profile)
    result = _verify(files)
    assert result["verified"] is True
    assert ("external-recovery-finalization.json" in files) is (
        profile == "EXTERNAL_RECOVERY_CLOSED"
    )


@pytest.mark.parametrize(
    "profile",
    [
        "SETUP_TERMINAL_BEFORE_LOCATOR",
        "SETUP_TEMP_RESIDUE_OPEN",
        "SETUP_TEMP_ATTEMPT_UNKNOWN",
    ],
)
def test_setup_external_profiles_reconstruct(profile: str) -> None:
    files = integration.build_setup_external(profile)
    result = _verify(files)
    assert result["profile"] == profile
    assert result["verified"] is True
    assert "locator-snapshot.json" not in files
    assert "recovery-transition-projection.json" not in files


def test_setup_unknown_has_authorization_but_no_result_and_no_retry() -> None:
    files = integration.build_setup_external("SETUP_TEMP_ATTEMPT_UNKNOWN")
    authorization = json.loads(files["setup-temp-removal-authorization.json"])
    assert authorization["retry_permitted"] is False
    assert "setup-temp-removal-result.json" not in files
    terminal = json.loads(files["external-terminal.json"])
    assert terminal["result"] == "UNKNOWN"
    assert terminal["residue"] == "UNKNOWN"


def test_setup_successfully_removed_temp_is_disjoint_from_no_temp_terminal() -> None:
    files = integration.build_setup_external(
        "SETUP_TERMINAL_BEFORE_LOCATOR", temp_removed=True
    )
    assert _verify(files)["verified"] is True
    terminal = json.loads(files["external-terminal.json"])
    assert terminal["code"] == "LOCATOR_PUBLICATION_FAILED"
    assert terminal["result"] == "PASS"
    assert terminal["residue"] == "ZERO_RESIDUE"
    assert "setup-temp-removal-result.json" in files


def test_classifier_is_reused_through_public_api(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = integration.diagnostic.classify_public_input

    def wrapper(value: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(integration.diagnostic, "classify_public_input", wrapper)
    files = integration.build_complete_route()
    _verify(files)
    assert calls == 2


def test_create_once_identical_reopen_and_collision() -> None:
    store = integration.CreateOnceStore()
    first = store.publish("x.json", {"a": 1})
    assert store.publish("x.json", {"a": 1}) == first
    with pytest.raises(integration.IntegrationError, match="CREATE_ONCE_COLLISION"):
        store.publish("x.json", {"a": 2})


@pytest.mark.parametrize("crash", ["before", "after"])
def test_create_once_crash_boundary(crash: str) -> None:
    store = integration.CreateOnceStore()
    with pytest.raises(integration.SyntheticCrash):
        store.publish("x.json", {"a": 1}, crash=crash)
    assert ("x.json" in store.files) is (crash == "after")


def test_create_once_after_durability_crash_reopens_identical_bytes() -> None:
    store = integration.CreateOnceStore()
    with pytest.raises(integration.SyntheticCrash):
        store.publish("x.json", {"a": 1}, crash="after")
    reopened = store.clone()
    digest = reopened.publish("x.json", {"a": 1})
    assert digest == integration.sha256(reopened.read("x.json"))


def test_restart_state_is_reconstructed_only_from_retained_bytes() -> None:
    subject = integration.SyntheticIntegration()
    assert integration.reconstruct_restart_state(subject.store)["state"] == "BEFORE_ACTION"
    subject.publish_action()
    assert integration.reconstruct_restart_state(subject.store)["state"] == "ACTION_DURABLE"
    subject.publish_locator()
    assert integration.reconstruct_restart_state(subject.store)["state"] == "LOCATOR_READY"
    authorization = subject.authorize_creation()
    state = integration.reconstruct_restart_state(subject.store)
    assert state == {"state": "CREATION_RESULT_UNKNOWN", "next": "NO_RETRY"}
    reopened = integration.SyntheticIntegration.reopen(subject.store)
    with pytest.raises(integration.IntegrationError, match="CREATION_RESULT_RECALL_FORBIDDEN"):
        reopened.record_creation(authorization, "SUCCEEDED")
    subject.record_creation(authorization, "SUCCEEDED")
    assert integration.reconstruct_restart_state(subject.store)["state"] == "CREATION_SUCCEEDED"
    lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    assert integration.reconstruct_restart_state(subject.store)["state"] == "OBSERVATION_CAPTURED"
    seal = subject.publish_seal(lifecycle)
    assert integration.reconstruct_restart_state(subject.store)["state"] == "SEALED"
    cleanup = subject.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
    assert integration.reconstruct_restart_state(subject.store)["state"] == "CLEANUP_RECORDED"
    receipt = subject.publish_receipt(seal, cleanup)
    assert integration.reconstruct_restart_state(subject.store)["state"] == "RECEIPT_PENDING_FINALIZATION"
    subject.finalize_route(receipt)
    assert integration.reconstruct_restart_state(subject.store)["state"] == "FINALIZED_CHAIN"


@pytest.mark.parametrize(
    ("profile", "builder", "state"),
    [
        ("RECOVERY_REQUIRED_NEGATIVE", integration.build_complete_route, "RECOVERY_REQUIRED_NEGATIVE"),
        ("EXTERNAL_RECOVERY_OPEN", integration.build_external, "EXTERNAL_RECOVERY_OPEN"),
        ("EXTERNAL_RECOVERY_CLOSED", integration.build_external, "EXTERNAL_RECOVERY_CLOSED"),
        ("SETUP_TERMINAL_BEFORE_LOCATOR", integration.build_setup_external, "SETUP_TERMINAL_BEFORE_LOCATOR"),
        ("SETUP_TEMP_RESIDUE_OPEN", integration.build_setup_external, "SETUP_TEMP_RESIDUE_OPEN"),
        ("SETUP_TEMP_ATTEMPT_UNKNOWN", integration.build_setup_external, "SETUP_TEMP_ATTEMPT_UNKNOWN"),
    ],
)
def test_all_recovery_profiles_have_retained_only_restart_disposition(
    profile: str, builder: object, state: str
) -> None:
    files = builder(profile)
    assert integration.reconstruct_restart_state(_operational_store(files))["state"] == state


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize(
    ("stage", "path", "before_state", "after_state"),
    [
        ("action", "action.json", "BEFORE_ACTION", "ACTION_DURABLE"),
        ("locator", "locator-snapshot.json", "ACTION_DURABLE", "LOCATOR_READY"),
        ("authorization", "recovery-transitions/0000.json", "LOCATOR_READY", "CREATION_RESULT_UNKNOWN"),
        ("seal", "observation-seal.json", "OBSERVATION_CAPTURED", "SEALED"),
        ("cleanup", "cleanup-result.json", "SEALED", "CLEANUP_RECORDED"),
        ("receipt", "final-receipt.json", "CLEANUP_RECORDED", "RECEIPT_PENDING_FINALIZATION"),
        ("finalization", "finalization.json", "RECEIPT_PENDING_FINALIZATION", "FINALIZED_CHAIN"),
    ],
)
def test_actual_state_machine_crash_reopens_to_matrix_defined_state(
    stage: str, path: str, before_state: str, after_state: str, phase: str
) -> None:
    subject = integration.SyntheticIntegration()
    authorization = lifecycle = seal = cleanup = receipt = None
    if stage != "action":
        subject.publish_action()
    if stage not in {"action", "locator"}:
        subject.publish_locator()
    if stage not in {"action", "locator", "authorization"}:
        authorization = subject.authorize_creation()
        subject.record_creation(authorization, "SUCCEEDED")
        lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    if stage in {"cleanup", "receipt", "finalization"}:
        assert lifecycle is not None
        seal = subject.publish_seal(lifecycle)
    if stage in {"receipt", "finalization"}:
        assert seal is not None
        cleanup = subject.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
    if stage == "finalization":
        assert seal is not None and cleanup is not None
        receipt = subject.publish_receipt(seal, cleanup)
    subject.store.arm_crash(path, phase)
    with pytest.raises(integration.SyntheticCrash):
        if stage == "action":
            subject.publish_action()
        elif stage == "locator":
            subject.publish_locator()
        elif stage == "authorization":
            subject.authorize_creation()
        elif stage == "seal":
            assert lifecycle is not None
            subject.publish_seal(lifecycle)
        elif stage == "cleanup":
            assert seal is not None
            subject.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
        elif stage == "receipt":
            assert seal is not None and cleanup is not None
            subject.publish_receipt(seal, cleanup)
        else:
            assert receipt is not None
            subject.finalize_route(receipt)
    state = integration.reconstruct_restart_state(subject.store)
    assert state["state"] == (after_state if phase == "after" else before_state)


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize(
    ("path", "before_state", "after_state"),
    [
        ("setup-temp-snapshot.json", "ACTION_DURABLE", "SETUP_TEMP_SNAPSHOT_DURABLE"),
        (
            "setup-temp-removal-authorization.json",
            "SETUP_TEMP_SNAPSHOT_DURABLE",
            "SETUP_TEMP_AUTHORIZED_RESULT_UNKNOWN",
        ),
        (
            "setup-temp-removal-result.json",
            "SETUP_TEMP_AUTHORIZED_RESULT_UNKNOWN",
            "SETUP_TEMP_RESULT_DURABLE",
        ),
        ("external-terminal.json", "SETUP_TEMP_RESULT_DURABLE", "SETUP_TEMP_RESIDUE_OPEN"),
    ],
)
def test_setup_recovery_actual_crash_matrix_is_retained_only(
    path: str, before_state: str, after_state: str, phase: str
) -> None:
    store = integration.CreateOnceStore()
    store.arm_crash(path, phase)
    with pytest.raises(integration.SyntheticCrash):
        integration.build_setup_external("SETUP_TEMP_RESIDUE_OPEN", store=store)
    state = integration.reconstruct_restart_state(store)
    assert state["state"] == (after_state if phase == "after" else before_state)


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize(
    ("stage", "path", "before_state", "after_state"),
    [
        ("terminal", "external-terminal.json", "CREATION_SUCCEEDED", "EXTERNAL_TERMINAL_DURABLE"),
        (
            "finalization",
            "external-recovery-finalization.json",
            "EXTERNAL_RECOVERY_OPEN",
            "EXTERNAL_RECOVERY_CLOSED",
        ),
    ],
)
def test_locator_bound_external_actual_crash_matrix(
    stage: str, path: str, before_state: str, after_state: str, phase: str
) -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    creation_result = subject.record_creation(authorization, "SUCCEEDED")
    assert subject.chain is not None
    subject.chain.append(
        "RECOVERY_ENTERED",
        {
            "creation_result_sha256": creation_result,
            "reason": "OBSERVATION_OR_SETUP_FAILED",
        },
    )
    subject.chain.append(
        "RECOVERY_CLEANUP_ATTEMPT",
        {"attempt_ordinal": 1, "result": "PASS" if stage == "finalization" else "FAIL", "residue": "ZERO_RESIDUE" if stage == "finalization" else "UNKNOWN"},
    )
    terminal = None
    if stage == "finalization":
        terminal = subject.publish_external_terminal(
            "NO_ADMISSIBLE_SEAL_CLEANED", result="PASS", residue="ZERO_RESIDUE"
        )
    subject.store.arm_crash(path, phase)
    with pytest.raises(integration.SyntheticCrash):
        if stage == "terminal":
            subject.publish_external_terminal("NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED")
        else:
            assert terminal is not None
            subject.finalize_external(terminal)
    state = integration.reconstruct_restart_state(subject.store)
    assert state["state"] == (after_state if phase == "after" else before_state)


def test_route_finalization_resume_executes_without_duplicate_transitions() -> None:
    files = integration.build_complete_route("FINALIZED_CHAIN")
    store = _operational_store(files)
    store.files.pop("finalization.json")
    reopened = integration.SyntheticIntegration.reopen(store)
    receipt = integration.sha256(store.read("final-receipt.json"))
    before = len(reopened.chain.digests) if reopened.chain is not None else 0
    reopened.finalize_route(receipt)
    assert len(reopened.chain.digests) == before
    assert integration.reconstruct_restart_state(reopened.store)["state"] == "FINALIZED_CHAIN"


def test_external_finalization_resume_executes_without_duplicate_transitions() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_CLOSED")
    store = _operational_store(files)
    store.files.pop("external-recovery-finalization.json")
    reopened = integration.SyntheticIntegration.reopen(store)
    terminal = integration.sha256(store.read("external-terminal.json"))
    before = len(reopened.chain.digests) if reopened.chain is not None else 0
    reopened.finalize_external(terminal)
    assert len(reopened.chain.digests) == before
    assert integration.reconstruct_restart_state(reopened.store)["state"] == "EXTERNAL_RECOVERY_CLOSED"


def test_creation_authorization_precedes_result_and_binds_no_retry() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    value = integration.parse_canonical(
        subject.store.read("recovery-transitions/0000.json")
    )
    assert value["class"] == "PRIVATE_ROOT_CREATION_AUTHORIZED"
    assert value["data"]["retry_permitted"] is False
    result = subject.record_creation(authorization, "SUCCEEDED")
    assert result != authorization


def test_authorization_without_result_is_permanent_unknown() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    terminal = subject.creation_unknown_terminal(authorization)
    assert terminal["code"] == "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE"
    assert terminal["result"] == "NOT_ATTEMPTED"
    assert terminal["residue"] == "UNKNOWN"
    assert terminal["locator_disposition"] == "RETAINED"


def test_observer_requires_parent_order_and_complete_termination() -> None:
    observer = integration.LifecycleObserver()
    observer.start()
    observer.emit("coverage_started", "")
    observer.emit("launch_started", "")
    with pytest.raises(integration.IntegrationError, match="PARENT_NOT_STARTED"):
        observer.emit("process_node_started", "child", "parent")
    observer.emit("process_node_started", "root")
    with pytest.raises(integration.IntegrationError, match="OBSERVER_COVERAGE_INCOMPLETE"):
        observer.stop()
    with pytest.raises(integration.IntegrationError, match="OBSERVER_SEAL_FORBIDDEN"):
        observer.projection()


def test_observer_overflow_fails_closed() -> None:
    observer = integration.LifecycleObserver(capacity=1)
    observer.start()
    observer.emit("coverage_started", "")
    with pytest.raises(integration.IntegrationError, match="OBSERVER_OVERFLOW"):
        observer.emit("launch_started", "")
    assert observer.coverage == "OVERFLOW"


def test_retained_lifecycle_fixture_is_replayed_not_trusted() -> None:
    files = integration.build_complete_route()
    _mutate_json(
        files,
        "lifecycle-fixture.json",
        lambda value: value["events"].pop(),
    )
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError):
        _verify(files)


def test_retained_absent_lifecycle_reconstructs_no_creation_class() -> None:
    fixture = integration.build_absent_lifecycle_fixture()
    observer = integration.replay_lifecycle_fixture(fixture)
    projection = observer.projection()
    assert projection == integration.INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE
    assert not any(
        event["marker"] == "target_created" for event in projection["events"]
    )
    classification = integration.classify_synthetic(projection)
    assert classification["axes"]["final_output"] == (
        "NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE"
    )
    assert "CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED" in classification[
        "diagnostic_classes"
    ]


def test_negative_route_retains_absent_raw_and_independent_expected_fixture() -> None:
    files = integration.build_complete_route("RECOVERY_REQUIRED_NEGATIVE")
    assert files["lifecycle-fixture.json"] == files[
        "fixtures/raw/synthetic-no-final-message-v1.json"
    ]
    assert files["expected-lifecycle-projection.json"] == files[
        "fixtures/expected-lifecycle/synthetic-no-final-message-v1.json"
    ]
    assert _verify(files)["verified"] is True


def test_absent_classification_forces_negative_receipt_and_can_finalize() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    subject.record_creation(authorization, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_absent_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    cleanup = subject.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
    receipt = subject.publish_receipt(seal, cleanup)
    receipt_value = integration.parse_canonical(subject.store.read("final-receipt.json"))
    assert receipt_value["terminal_disposition"] == "NEGATIVE_RECEIPT"
    subject.finalize_route(receipt)
    finalization = integration.parse_canonical(subject.store.read("finalization.json"))
    assert finalization["terminal_class"] == "FINALIZED_NEGATIVE"
    files = integration.build_package(subject.store, "FINALIZED_CHAIN")
    assert _verify(files)["verified"] is True


def test_absent_classification_rejects_diagnostic_receipt_override() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    subject.record_creation(authorization, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_absent_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    cleanup = subject.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
    with pytest.raises(
        integration.IntegrationError, match="RECEIPT_DISPOSITION_OVERRIDE_FORBIDDEN"
    ):
        subject.publish_receipt(seal, cleanup, negative=False)


def test_lifecycle_fixture_sequence_gap_fails_closed() -> None:
    fixture = integration.build_lifecycle_fixture()
    fixture["events"][4]["sequence"] = 9
    with pytest.raises(integration.IntegrationError, match="LIFECYCLE_SEQUENCE_INVALID"):
        integration.replay_lifecycle_fixture(fixture)


def test_child_outlives_parent_fails_closed() -> None:
    fixture = integration.build_lifecycle_fixture()
    fixture["events"][5], fixture["events"][6] = (
        fixture["events"][6],
        fixture["events"][5],
    )
    fixture["events"][5]["sequence"] = 5
    fixture["events"][6]["sequence"] = 6
    with pytest.raises(integration.IntegrationError, match="CHILD_OUTLIVES_PARENT"):
        integration.replay_lifecycle_fixture(fixture)


def test_cleanup_precedes_receipt_and_contradictions_fail() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    auth = subject.authorize_creation()
    subject.record_creation(auth, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    with pytest.raises(integration.IntegrationError, match="CLEANUP_RESIDUE_CONTRADICTION"):
        subject.publish_cleanup(seal, "PASS", "UNKNOWN")
    cleanup = subject.publish_cleanup(seal, "FAIL", "UNKNOWN")
    subject.publish_receipt(seal, cleanup)
    receipt = integration.parse_canonical(subject.store.read("final-receipt.json"))
    assert receipt["terminal_disposition"] == "NEGATIVE_RECEIPT"
    assert receipt["locator_state"] == "RETAINED"


def test_not_attempted_cleanup_produces_unfinalizable_negative_receipt() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    auth = subject.authorize_creation()
    subject.record_creation(auth, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    cleanup = subject.publish_cleanup(seal, "NOT_ATTEMPTED", "UNKNOWN")
    cleanup_value = integration.parse_canonical(subject.store.read("cleanup-result.json"))
    assert cleanup_value["attempted"] is False
    assert cleanup_value["attempt_count"] == 0
    subject.publish_receipt(seal, cleanup)
    receipt = integration.parse_canonical(subject.store.read("final-receipt.json"))
    assert receipt["terminal_disposition"] == "NEGATIVE_RECEIPT"
    assert receipt["locator_state"] == "RETAINED"


def test_not_attempted_cleanup_cannot_claim_attempted_true() -> None:
    files = integration.build_complete_route("RECOVERY_REQUIRED_NEGATIVE")
    _mutate_json(
        files,
        "cleanup-result.json",
        lambda value: value.update(
            {
                "attempted": True,
                "attempt_count": 1,
                "result": "NOT_ATTEMPTED",
                "residue": "UNKNOWN",
                "failure_code": "IDENTITY_UNAVAILABLE",
            }
        ),
    )
    _mutate_json(
        files,
        "final-receipt.json",
        lambda value: value.update(
            {
                "cleanup_result_sha256": integration.sha256(files["cleanup-result.json"]),
                "cleanup_disposition": "NOT_ATTEMPTED",
                "residue": "UNKNOWN",
            }
        ),
    )
    _rewrite_manifest(files, "RECOVERY_REQUIRED_NEGATIVE")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_cleanup_attempted_must_be_boolean_and_failure_codes_are_closed() -> None:
    for mutation in (
        {"attempted": "yes"},
        {"attempt_count": True},
        {"failure_code": "ARBITRARY_FAILURE"},
    ):
        files = integration.build_complete_route("RECOVERY_REQUIRED_NEGATIVE")
        _mutate_json(
            files,
            "cleanup-result.json",
            lambda value, mutation=mutation: value.update(mutation),
        )
        _mutate_json(
            files,
            "final-receipt.json",
            lambda value: value.update(
                {
                    "cleanup_result_sha256": integration.sha256(
                        files["cleanup-result.json"]
                    )
                }
            ),
        )
        _rewrite_manifest(files, "RECOVERY_REQUIRED_NEGATIVE")
        assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_partial_cleanup_uses_distinct_closed_code() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    auth = subject.authorize_creation()
    subject.record_creation(auth, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    subject.publish_cleanup(seal, "PARTIAL", "UNKNOWN")
    cleanup = integration.parse_canonical(subject.store.read("cleanup-result.json"))
    assert cleanup["failure_code"] == "SYNTHETIC_CLEANUP_PARTIAL"


def test_receipt_summary_fields_must_match_reconstructed_cleanup() -> None:
    files = integration.build_complete_route("RECOVERY_REQUIRED_NEGATIVE")
    _mutate_json(
        files,
        "final-receipt.json",
        lambda value: value.update(
            {
                "overall_result": "DIAGNOSTIC_COMPLETE",
                "cleanup_disposition": "PASS",
                "residue": "ZERO_RESIDUE",
            }
        ),
    )
    _rewrite_manifest(files, "RECOVERY_REQUIRED_NEGATIVE")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_unfinalizable_negative_receipt_cannot_append_removal_transitions() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    subject.record_creation(authorization, "SUCCEEDED")
    lifecycle = subject.publish_lifecycle(integration.build_lifecycle_fixture())
    seal = subject.publish_seal(lifecycle)
    cleanup = subject.publish_cleanup(seal, "FAIL", "UNKNOWN")
    receipt = subject.publish_receipt(seal, cleanup)
    assert subject.chain is not None
    before = len(subject.chain.digests)
    with pytest.raises(
        integration.IntegrationError, match="ROUTE_FINALIZATION_RECEIPT_INELIGIBLE"
    ):
        subject.finalize_route(receipt)
    assert len(subject.chain.digests) == before
    assert "finalization.json" not in subject.store.files


@pytest.mark.parametrize(
    "mutation",
    [
        lambda files: files.pop("locator-snapshot.json"),
        lambda files: files.__setitem__("locator-snapshot.json", b"{}\n"),
        lambda files: _mutate_json(
            files, "locator-snapshot.json", lambda value: value.update({"credential": "x"})
        ),
        lambda files: _mutate_json(
            files, "locator-snapshot.json", lambda value: value.update({"locator_id": "changed"})
        ),
    ],
)
def test_locator_snapshot_omission_or_mutation_fails_closed(mutation: object) -> None:
    files = integration.build_complete_route()
    mutation(files)
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError):
        _verify(files)


def test_authorization_locator_digest_substitution_fails_closed() -> None:
    files = integration.build_complete_route()
    _mutate_json(
        files,
        "recovery-transitions/0000.json",
        lambda value: value.update({"locator_sha256": integration.SHA256_ZERO}),
    )
    projection = json.loads(files["recovery-transition-projection.json"])
    payload = files["recovery-transitions/0000.json"]
    projection["entries"][0]["byte_count"] = len(payload)
    projection["entries"][0]["sha256"] = integration.sha256(payload)
    files["recovery-transition-projection.json"] = integration.canonical_bytes(projection)
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError):
        _verify(files)


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("observation-seal.json", "ARTIFACT_MISSING"),
        ("recovery-transitions/0000.json", "TRANSITION_RECORD_MISSING"),
        ("recovery-transition-projection.json", "ARTIFACT_MISSING"),
        ("finalization.json", "FINALIZATION_MISSING"),
    ],
)
def test_required_artifact_omission_fails_closed(path: str, code: str) -> None:
    files = integration.build_complete_route()
    files.pop(path)
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError):
        _verify(files)


def test_negative_profile_rejects_finalization() -> None:
    files = integration.build_complete_route("RECOVERY_REQUIRED_NEGATIVE")
    finalized = integration.build_complete_route("FINALIZED_CHAIN")
    files["finalization.json"] = finalized["finalization.json"]
    files["schemas/finalization.schema.json"] = finalized[
        "schemas/finalization.schema.json"
    ]
    _rewrite_manifest(files, "RECOVERY_REQUIRED_NEGATIVE")
    with pytest.raises(integration.IntegrationError):
        _verify(files)


def test_manifest_rejects_extra_and_missing_files() -> None:
    files = integration.build_complete_route()
    files["extra.json"] = integration.canonical_bytes({"schema": "x"})
    with pytest.raises(integration.IntegrationError, match="MANIFEST_INVENTORY_MISMATCH"):
        _verify(files)


def test_noncanonical_json_fails_closed() -> None:
    files = integration.build_complete_route()
    value = json.loads(files["action.json"])
    files["action.json"] = json.dumps(value, indent=2).encode() + b"\n"
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError, match="JSON_NOT_CANONICAL"):
        _verify(files)


def test_privacy_rejection_does_not_echo_secret() -> None:
    files = integration.build_complete_route()
    _mutate_json(
        files,
        "action.json",
        lambda value: value.update({"secret_token": "must-not-appear"}),
    )
    _rewrite_manifest(files, "FINALIZED_CHAIN")
    with pytest.raises(integration.IntegrationError) as failure:
        _verify(files)
    assert "must-not-appear" not in str(failure.value)


@pytest.mark.parametrize("phase", ["before_open", "during_read", "after_read"])
def test_toctou_identity_replacement_fails_closed(phase: str) -> None:
    world = integration.SyntheticWorld()
    world.put("x", b"safe", identity="one")

    def attack(current: str, target: integration.SyntheticWorld, path: str) -> None:
        if current == phase:
            target.put(path, b"changed", identity="two")

    with pytest.raises(integration.IntegrationError):
        integration.capture_world(world, ["x"], attack)


def test_toctou_root_switch_and_insertion_fail_closed() -> None:
    for change in ("root", "insert"):
        world = integration.SyntheticWorld()
        world.put("x", b"safe")

        def attack(phase: str, target: integration.SyntheticWorld, path: str) -> None:
            if phase == "after_read":
                target.switch_root() if change == "root" else target.put("extra", b"x")

        with pytest.raises(integration.IntegrationError):
            integration.capture_world(world, ["x"], attack)


@pytest.mark.parametrize("phase", ["before_open", "during_read"])
def test_same_identity_replacement_before_completed_read_fails_closed(phase: str) -> None:
    world = integration.SyntheticWorld()
    world.put("x", b"safe", identity="same")

    def attack(current: str, target: integration.SyntheticWorld, path: str) -> None:
        if current == phase:
            target.put(path, b"changed", identity="same")

    with pytest.raises(integration.IntegrationError, match="TOCTOU_IDENTITY_CHANGED"):
        integration.capture_world(world, ["x"], attack)


def test_case_collision_and_identity_alias_fail_closed() -> None:
    case_world = integration.SyntheticWorld()
    case_world.put("A", b"one")
    case_world.put("a", b"two")
    with pytest.raises(integration.IntegrationError, match="TREE_CASE_COLLISION"):
        integration.capture_world(case_world, ["A", "a"])

    alias_world = integration.SyntheticWorld()
    alias_world.put("a", b"one", identity="same")
    alias_world.put("b", b"two", identity="same")
    with pytest.raises(integration.IntegrationError, match="TREE_IDENTITY_ALIAS"):
        integration.capture_world(alias_world, ["a", "b"])


def test_symlink_or_directory_is_never_opened() -> None:
    for kind in ("symlink", "directory", "reparse"):
        world = integration.SyntheticWorld()
        world.put("x", b"", kind=kind)
        with pytest.raises(integration.IntegrationError, match="PATH_INVALID"):
            integration.capture_world(world, ["x"])


def test_same_identity_post_read_mutation_does_not_upgrade_claim() -> None:
    world = integration.SyntheticWorld()
    world.put("x", b"safe", identity="same")

    def attack(phase: str, target: integration.SyntheticWorld, path: str) -> None:
        if phase == "after_read":
            target.put(path, b"later", identity="same")

    captured = integration.capture_world(world, ["x"], attack)
    assert captured.entries["x"] == b"safe"
    assert captured.evidence_level == "CAPTURED_BYTE_SET_RECONSTRUCTED"


def test_verifier_never_returns_stronger_evidence_level() -> None:
    files = integration.build_complete_route()
    result = _verify(files)
    assert result["evidence_level"] == "CAPTURED_BYTE_SET_RECONSTRUCTED"
    assert "immutable" not in json.dumps(result).lower()
    assert "closed_tree" not in json.dumps(result).lower()


def test_stronger_snapshot_claim_is_verification_unavailable() -> None:
    files = integration.build_complete_route()
    authority = _authority(files)
    stronger = integration.VerificationAuthority(
        authority.expected_tree_manifest_sha256,
        authority.expected_verifier_sha256,
        authority.expected_execution_command_contract_sha256,
        requested_evidence_level="IMMUTABLE_CLOSED_SNAPSHOT",
    )
    result = integration.verify_public(_captured(files), stronger)
    assert result["code"] == "VERIFICATION_UNAVAILABLE"
    assert result["verified"] is False


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "absolute_path",
        "prompt",
        "model_text",
        "skill_text",
        "credential_value",
        "raw_stderr",
        "content_digest",
        "event_payload",
    ],
)
def test_privacy_contract_rejects_private_or_live_content_classes(
    forbidden_key: str,
) -> None:
    with pytest.raises(integration.IntegrationError, match="PRIVACY_KEY_FORBIDDEN"):
        integration.validate_privacy({forbidden_key: "must-not-echo"})
    result = integration.verify_public({forbidden_key: "must-not-echo"})
    assert "must-not-echo" not in json.dumps(result)


def test_module_has_no_host_io_or_live_adapters() -> None:
    for forbidden in ("subprocess", "socket", "requests", "credential", "preflight", "live_session"):
        assert not hasattr(integration, forbidden)


@pytest.mark.parametrize("invalid", [None, [], "bad", b"bad", {"x": object()}])
def test_public_verifier_invalid_input_fails_closed(invalid: object) -> None:
    result = integration.verify_public(invalid)
    assert result["verified"] is False
    assert result["evidence_level"] == "CAPTURED_BYTE_SET_RECONSTRUCTED"
    assert invalid is None or str(invalid) not in json.dumps(result)


def test_public_verifier_accepts_valid_captured_package() -> None:
    files = integration.build_complete_route()
    result = integration.verify_public(_captured(files), _authority(files))
    assert result["verified"] is True


@pytest.mark.parametrize("field", ["manifest", "verifier", "command"])
def test_out_of_band_review_authority_is_mandatory(field: str) -> None:
    files = integration.build_complete_route()
    authority = _authority(files)
    values = {
        "expected_tree_manifest_sha256": authority.expected_tree_manifest_sha256,
        "expected_verifier_sha256": authority.expected_verifier_sha256,
        "expected_execution_command_contract_sha256": authority.expected_execution_command_contract_sha256,
    }
    key = {
        "manifest": "expected_tree_manifest_sha256",
        "verifier": "expected_verifier_sha256",
        "command": "expected_execution_command_contract_sha256",
    }[field]
    values[key] = integration.SHA256_ZERO
    result = integration.verify_public(
        _captured(files), integration.VerificationAuthority(**values)
    )
    assert result["verified"] is False


def test_retained_implementation_bytes_are_exact_reviewed_module_bytes() -> None:
    files = integration.build_complete_route()
    for name in integration.RETAINED_IMPLEMENTATIONS:
        assert files[f"implementations/{name}"] == REVIEWED_MODULE_BYTES
    assert _authority(files).expected_verifier_sha256 == integration.sha256(
        Path(integration.__file__).read_bytes()
    )


def test_public_verifier_contains_hostile_mapping_exception() -> None:
    class HostileMapping:
        def keys(self) -> object:
            raise RuntimeError("hostile detail must not escape")

        def __getitem__(self, key: object) -> object:
            raise RuntimeError("hostile detail must not escape")

    files = integration.build_complete_route()
    captured = integration.CapturedByteSet(
        root_identity="synthetic-root-v1",
        entries=HostileMapping(),  # type: ignore[arg-type]
        identities={},
    )
    result = integration.verify_public(captured, _authority(files))
    assert result == {
        "code": "VERIFICATION_INPUT_INVALID",
        "evidence_level": "CAPTURED_BYTE_SET_RECONSTRUCTED",
        "verified": False,
    }


def test_external_closed_terminal_prefix_and_final_projection_are_both_bound() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_CLOSED")
    _mutate_json(
        files,
        "external-terminal.json",
        lambda value: value.update({"transition_projection_sha256": integration.SHA256_ZERO}),
    )
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_CLOSED")
    result = integration.verify_public(_captured(files), _authority(files))
    assert result["verified"] is False
    assert result["code"] == "EXTERNAL_REMOVAL_AUTH_LINK_INVALID"


def test_external_closed_final_projection_link_mutation_fails_closed() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_CLOSED")
    _mutate_json(
        files,
        "external-recovery-finalization.json",
        lambda value: value.update({"transition_projection_sha256": integration.SHA256_ZERO}),
    )
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_CLOSED")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_external_open_rejects_unknown_terminal_code() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_OPEN")
    _mutate_json(
        files,
        "external-terminal.json",
        lambda value: value.update({"code": "BOGUS_UNCLOSED_CODE"}),
    )
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_external_attempt_count_cannot_exceed_action_bound() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_OPEN")
    _mutate_json(files, "action.json", lambda value: value.update({"max_cleanup_attempts": 0}))
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_unknown_transition_class_or_data_is_rejected() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_OPEN")
    projection = json.loads(files["recovery-transition-projection.json"])
    ordinal = len(projection["entries"])
    previous = projection["entries"][-1]["sha256"]
    transition = {
        "schema": integration.SCHEMA_IDS["transition"],
        "ordinal": ordinal,
        "previous_sha256": previous,
        "class": "BOGUS_TRANSITION",
        "locator_sha256": integration.sha256(files["locator-snapshot.json"]),
        "data": {"harmless_extra": True},
    }
    path = f"recovery-transitions/{ordinal:04d}.json"
    files[path] = integration.canonical_bytes(transition)
    projection["entries"].append(
        {
            "ordinal": ordinal,
            "path": path,
            "byte_count": len(files[path]),
            "sha256": integration.sha256(files[path]),
            "previous_sha256": previous,
        }
    )
    files["recovery-transition-projection.json"] = integration.canonical_bytes(projection)
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_creation_unknown_code_rejects_actual_cleanup_attempt() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_OPEN")
    _mutate_json(
        files,
        "external-terminal.json",
        lambda value: value.update({"code": "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE"}),
    )
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_creation_authorization_values_are_closed() -> None:
    files = integration.build_external("EXTERNAL_RECOVERY_OPEN")
    _mutate_json(
        files,
        "recovery-transitions/0000.json",
        lambda value: value["data"].update(
            {"operation": "BOGUS_OPERATION", "private_root_id": "wrong-root"}
        ),
    )
    _rewrite_manifest(files, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_authorization_without_result_cannot_enter_cleanup() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    subject.authorize_creation()
    assert subject.chain is not None
    subject.chain.append(
        "RECOVERY_CLEANUP_ATTEMPT",
        {"attempt_ordinal": 1, "result": "FAIL", "residue": "UNKNOWN"},
    )
    subject.publish_external_terminal("NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED")
    files = integration.build_package(subject.store, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_failed_creation_without_absence_requires_unconfirmed_code() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    subject.record_creation(authorization, "FAILED")
    subject.publish_external_terminal(
        "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE",
        attempted=False,
        count=0,
        result="NOT_ATTEMPTED",
        residue="UNKNOWN",
    )
    files = integration.build_package(subject.store, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_failed_creation_with_independent_absence_can_close_zero_residue() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    result = subject.record_creation(authorization, "FAILED")
    assert subject.chain is not None
    subject.chain.append(
        "PRIVATE_ROOT_ABSENCE_OBSERVED",
        {
            "creation_result_sha256": result,
            "observation": "ABSENT_CONFIRMED",
            "private_root_id": "synthetic-private-root-v1",
        },
    )
    terminal = subject.publish_external_terminal(
        "LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED",
        attempted=False,
        count=0,
        result="NOT_ATTEMPTED",
        residue="ZERO_RESIDUE",
    )
    subject.finalize_external(terminal)
    files = integration.build_package(subject.store, "EXTERNAL_RECOVERY_CLOSED")
    assert _verify(files)["verified"] is True


def test_successful_creation_requires_recovery_entry_before_cleanup() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    subject.record_creation(authorization, "SUCCEEDED")
    assert subject.chain is not None
    subject.chain.append(
        "RECOVERY_CLEANUP_ATTEMPT",
        {"attempt_ordinal": 1, "result": "FAIL", "residue": "UNKNOWN"},
    )
    subject.publish_external_terminal("NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED")
    files = integration.build_package(subject.store, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False


def test_successful_creation_rejects_failure_specific_absence_code() -> None:
    subject = integration.SyntheticIntegration()
    subject.publish_action()
    subject.publish_locator()
    authorization = subject.authorize_creation()
    creation_result = subject.record_creation(authorization, "SUCCEEDED")
    assert subject.chain is not None
    subject.chain.append(
        "RECOVERY_ENTERED",
        {
            "creation_result_sha256": creation_result,
            "reason": "OBSERVATION_OR_SETUP_FAILED",
        },
    )
    subject.publish_external_terminal(
        "PRIVATE_ROOT_ABSENCE_UNCONFIRMED",
        attempted=False,
        count=0,
        result="NOT_ATTEMPTED",
        residue="UNKNOWN",
    )
    files = integration.build_package(subject.store, "EXTERNAL_RECOVERY_OPEN")
    assert integration.verify_public(_captured(files), _authority(files))["verified"] is False
