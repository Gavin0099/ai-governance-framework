from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import traceback
from uuid import uuid4

import pytest

from governance_tools import solo_r2_blind_scoring_bundle as bundle_module
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_random_domains as random_domains


REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_TEST_ROOT_UNTRUSTED = "SECRET_TEST_ROOT_UNTRUSTED / STOP"
STATE_KEYS = {
    "schema_version",
    "artifact_type",
    "evaluation_id",
    "pair_id",
    "slot",
    "state_phase",
    "realized_order",
    "order_entropy",
    "attempt_bindings",
    "scoring_bindings",
    "presentation_order",
    "attempt_output_refs",
}
PACKAGE_KEYS = {
    "package_schema",
    "artifact_type",
    "key_id",
    "nonce_b64",
    "aad_utf8_b64",
    "ciphertext_b64",
    "tag_b64",
}


def _hex_id(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _state(
    phase: str,
    *,
    evaluation_id: str | None = None,
    pair_id: str = "r2-pair-synthetic",
    slot: str = "R2-SHAKEDOWN",
    output_ref_suffix: str = "",
) -> dict[str, object]:
    entropy = bytes(range(32))
    realized_order = list(random_domains.arm_order_from_entropy(entropy))
    handles = [_hex_id("attempt-0"), _hex_id("attempt-1")]
    labels = [_hex_id("label-0"), _hex_id("label-1")]
    state: dict[str, object] = {
        "schema_version": controller.CONTROLLER_STATE_SCHEMA,
        "artifact_type": controller.CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": evaluation_id or str(uuid4()),
        "pair_id": pair_id,
        "slot": slot,
        "state_phase": phase,
        "realized_order": realized_order,
        "order_entropy": base64.b64encode(entropy).decode("ascii"),
        "attempt_bindings": [],
        "scoring_bindings": [],
        "presentation_order": [],
        "attempt_output_refs": [],
    }
    if phase == controller.ATTEMPT_BOUND:
        state["attempt_bindings"] = [
            {"attempt_handle": handles[0], "arm": realized_order[0]}
        ]
    elif phase == controller.SCORING_BOUND:
        state["attempt_bindings"] = [
            {"attempt_handle": handles[index], "arm": realized_order[index]}
            for index in range(2)
        ]
        state["scoring_bindings"] = [
            {"scoring_label": labels[index], "attempt_handle": handles[index]}
            for index in range(2)
        ]
        state["presentation_order"] = [labels[1], labels[0]]
        state["attempt_output_refs"] = [
            {
                "attempt_handle": handles[index],
                "output_ref": f"controller-only-output-{index}{output_ref_suffix}",
            }
            for index in range(2)
        ]
    return state


def _two_attempt_state(base: dict[str, object]) -> dict[str, object]:
    state = copy.deepcopy(base)
    state["attempt_bindings"] = [
        {
            "attempt_handle": _hex_id(f"attempt-{index}"),
            "arm": state["realized_order"][index],  # type: ignore[index]
        }
        for index in range(2)
    ]
    return state


def _write_key_record(path: Path, key_id: str, key_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": controller.CONTROLLER_KEY_SCHEMA,
        "key_id": key_id,
        "key_b64": base64.b64encode(key_bytes).decode("ascii"),
    }
    path.write_bytes(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _seal_state(
    state: object,
    *,
    key_path: Path,
    custody_boundary: controller.CustodyBoundary,
) -> controller.SealedControllerPackage:
    snapshot = controller.freeze_controller_state(state)
    return controller.seal_controller_state(
        snapshot, key_path=key_path, custody_boundary=custody_boundary
    )


def _assert_outside(path: Path, roots: tuple[Path, ...]) -> None:
    resolved = path.resolve()
    assert all(
        resolved != root.resolve() and root.resolve() not in resolved.parents
        for root in roots
    ), SECRET_TEST_ROOT_UNTRUSTED


@pytest.fixture
def custody(
    tmp_path: Path,
) -> tuple[controller.CustodyBoundary, Path, str, bytes]:
    assert REPO_ROOT.resolve() not in tmp_path.resolve().parents, SECRET_TEST_ROOT_UNTRUSTED
    named_roots = {
        "consumer_root": tmp_path / "consumer",
        "materialization_root": tmp_path / "materialization",
        "execution_root": tmp_path / "execution",
        "scoring_root": tmp_path / "scoring",
    }
    for root in named_roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=REPO_ROOT,
        **named_roots,
    )
    key_path = tmp_path / "controller-custody" / "key.json"
    _assert_outside(key_path.parent, boundary.roots())
    key_id = f"solo-r2-{uuid4().hex}"
    key_bytes = os.urandom(32)
    _write_key_record(key_path, key_id, key_bytes)
    return boundary, key_path, key_id, key_bytes


def _new_key_target(
    tmp_path: Path,
) -> tuple[controller.CustodyBoundary, Path]:
    assert REPO_ROOT.resolve() not in tmp_path.resolve().parents, SECRET_TEST_ROOT_UNTRUSTED
    named_roots = {
        "consumer_root": tmp_path / "new-consumer",
        "materialization_root": tmp_path / "new-materialization",
        "execution_root": tmp_path / "new-execution",
        "scoring_root": tmp_path / "new-scoring",
    }
    for root in named_roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=REPO_ROOT,
        **named_roots,
    )
    custody_root = tmp_path / "new-controller-custody"
    custody_root.mkdir()
    key_path = custody_root / "key.json"
    _assert_outside(key_path.parent, boundary.roots())
    return boundary, key_path


@pytest.mark.parametrize(
    ("phase", "attempts", "scoring", "presentation", "outputs"),
    [
        (controller.ORDER_FROZEN, 0, 0, 0, 0),
        (controller.ATTEMPT_BOUND, 1, 0, 0, 0),
        (controller.SCORING_BOUND, 2, 2, 2, 2),
    ],
)
def test_closed_phase_keysets_and_cardinality(
    phase: str, attempts: int, scoring: int, presentation: int, outputs: int
) -> None:
    state = _state(phase)
    validated = controller.validate_controller_state(state)

    assert set(validated) == STATE_KEYS
    assert len(validated["attempt_bindings"]) == attempts
    assert len(validated["scoring_bindings"]) == scoring
    assert len(validated["presentation_order"]) == presentation
    assert len(validated["attempt_output_refs"]) == outputs


def test_attempt_bound_accepts_exactly_two_immutable_bindings() -> None:
    state = _two_attempt_state(_state(controller.ATTEMPT_BOUND))
    assert len(controller.validate_controller_state(state)["attempt_bindings"]) == 2


@pytest.mark.parametrize(
    "mutation",
    [
        lambda state: state.update({"unknown": "value"}),
        lambda state: state.pop("slot"),
        lambda state: state.update({"state_phase": "UNKNOWN"}),
        lambda state: state.update({"realized_order": ["CONTROL", "CONTROL"]}),
        lambda state: state.update({"realized_order": [{}, "CONTROL"]}),
        lambda state: state.update({"order_entropy": "not-base64"}),
        lambda state: state.update(
            {
                "attempt_bindings": [
                    {
                        "attempt_handle": _hex_id("x"),
                        "arm": "CONTROL",
                        "extra": 1,
                    }
                ]
            }
        ),
    ],
)
def test_controller_state_rejects_unknown_missing_or_malformed_fields(mutation) -> None:
    state = _state(controller.ORDER_FROZEN)
    mutation(state)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.validate_controller_state(state)
    assert caught.value.code == controller.CONTROLLER_STATE_SCHEMA_FAILURE


def test_state_transitions_preserve_bindings_and_realized_order() -> None:
    frozen = _state(controller.ORDER_FROZEN)
    first = copy.deepcopy(frozen)
    first["state_phase"] = controller.ATTEMPT_BOUND
    first["attempt_bindings"] = _state(controller.ATTEMPT_BOUND)["attempt_bindings"]
    second = _two_attempt_state(first)
    scoring = _state(
        controller.SCORING_BOUND,
        evaluation_id=frozen["evaluation_id"],  # type: ignore[arg-type]
        pair_id=frozen["pair_id"],  # type: ignore[arg-type]
        slot=frozen["slot"],  # type: ignore[arg-type]
    )
    scoring["order_entropy"] = frozen["order_entropy"]
    scoring["realized_order"] = frozen["realized_order"]

    first_snapshot = controller.validate_state_transition(frozen, first)
    second_snapshot = controller.validate_state_transition(first, second)
    scoring_snapshot = controller.validate_state_transition(second, scoring)
    assert json.loads(first_snapshot.canonical_state_bytes) == first
    assert json.loads(second_snapshot.canonical_state_bytes) == second
    assert json.loads(scoring_snapshot.canonical_state_bytes) == scoring

    rebound = copy.deepcopy(second)
    rebound["attempt_bindings"][0]["attempt_handle"] = _hex_id("rebound")  # type: ignore[index]
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.validate_state_transition(first, rebound)
    assert caught.value.code == controller.CONTROLLER_STATE_SCHEMA_FAILURE


def test_transition_snapshot_cannot_be_changed_through_caller_alias(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    frozen = _state(controller.ORDER_FROZEN)
    current = copy.deepcopy(frozen)
    current["state_phase"] = controller.ATTEMPT_BOUND
    current["attempt_bindings"] = _state(controller.ATTEMPT_BOUND)[
        "attempt_bindings"
    ]
    original_handle = current["attempt_bindings"][0]["attempt_handle"]  # type: ignore[index]
    snapshot = controller.validate_state_transition(frozen, current)
    frozen_bytes = snapshot.canonical_state_bytes

    current["attempt_bindings"][0]["attempt_handle"] = _hex_id("replacement")  # type: ignore[index]
    sealed = controller.seal_controller_state(
        snapshot, key_path=key_path, custody_boundary=boundary
    )
    opened = controller.open_controller_package(
        sealed.package_bytes,
        key_path=key_path,
        custody_boundary=boundary,
        expected_digest=sealed.sealed_package_digest,
        expected_evaluation_id=frozen["evaluation_id"],  # type: ignore[arg-type]
        expected_pair_id=frozen["pair_id"],  # type: ignore[arg-type]
        expected_slot=frozen["slot"],  # type: ignore[arg-type]
    )

    assert snapshot.canonical_state_bytes == frozen_bytes
    assert snapshot.state_sha256 == hashlib.sha256(frozen_bytes).hexdigest()
    assert opened["attempt_bindings"][0]["attempt_handle"] == original_handle
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.seal_controller_state(
            current,  # type: ignore[arg-type]
            key_path=key_path,
            custody_boundary=boundary,
        )
    assert caught.value.code == controller.CONTROLLER_STATE_SCHEMA_FAILURE


def test_key_custody_requires_explicit_external_absolute_path(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.ORDER_FROZEN)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    assert controller.parse_sealed_package(sealed.package_bytes)["key_id"]

    rejected = [
        Path("relative-key.json"),
        key_path.parent / "missing.json",
        REPO_ROOT / "requirements.txt",
    ]
    materialization_file = boundary.materialization_root / "not-secret.json"
    materialization_file.write_text("{}", encoding="utf-8")
    rejected.append(materialization_file)
    for path in rejected:
        with pytest.raises(controller.ControllerStateError) as caught:
            _seal_state(
                state, key_path=path, custody_boundary=boundary
            )
        assert caught.value.code == controller.KEY_CUSTODY_FAILURE


def test_key_custody_rejects_forbidden_root_hardlink_alias(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    tmp_path: Path,
) -> None:
    boundary, _, key_id, key_bytes = custody
    forbidden_key = boundary.materialization_root / "controller-key.json"
    _write_key_record(forbidden_key, key_id, key_bytes)
    alias = tmp_path / "controller-custody" / "hardlink-key.json"
    alias.parent.mkdir(parents=True, exist_ok=True)
    os.link(forbidden_key, alias)

    assert forbidden_key.samefile(alias)
    assert alias.stat().st_nlink > 1
    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            _state(controller.ORDER_FROZEN),
            key_path=alias,
            custody_boundary=boundary,
        )
    assert caught.value.code == controller.KEY_CUSTODY_FAILURE


def test_key_custody_rejects_any_git_worktree_even_outside_governance_repo(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    tmp_path: Path,
) -> None:
    boundary, _, _, _ = custody
    fake_worktree = tmp_path / "other-git-worktree"
    (fake_worktree / ".git").mkdir(parents=True)
    placeholder = fake_worktree / "not-secret.json"
    placeholder.write_text("{}", encoding="utf-8")

    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            _state(controller.ORDER_FROZEN),
            key_path=placeholder,
            custody_boundary=boundary,
        )
    assert caught.value.code == controller.KEY_CUSTODY_FAILURE


@pytest.mark.parametrize(
    ("key_id", "key_bytes"),
    [
        ("bad-key-id", bytes(32)),
        ("solo-r2-" + "a" * 32, bytes(31)),
    ],
)
def test_key_material_is_exactly_key_id_plus_32_byte_key(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    key_id: str,
    key_bytes: object,
) -> None:
    boundary, key_path, _, _ = custody
    _write_key_record(key_path, key_id, bytes(key_bytes))
    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            _state(controller.ORDER_FROZEN),
            key_path=key_path,
            custody_boundary=boundary,
        )
    assert caught.value.code == controller.KEY_MATERIAL_FAILURE


def test_load_rejects_key_id_mismatch(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, key_bytes = custody
    state = _state(controller.ORDER_FROZEN)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    _write_key_record(key_path, "solo-r2-" + "f" * 32, key_bytes)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            sealed.package_bytes,
            key_path=key_path,
            custody_boundary=boundary,
            expected_digest=sealed.sealed_package_digest,
            expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
            expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
            expected_slot=state["slot"],  # type: ignore[arg-type]
        )
    assert caught.value.code == controller.KEY_MATERIAL_FAILURE


def test_key_loader_rejects_malformed_key_record_with_fixed_error(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    key_path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            _state(controller.ORDER_FROZEN),
            key_path=key_path,
            custody_boundary=boundary,
        )
    assert caught.value.code == controller.KEY_MATERIAL_FAILURE
    assert str(caught.value) == controller.KEY_MATERIAL_FAILURE


def test_aad_exact_bytes_and_field_set() -> None:
    state = _state(
        controller.ORDER_FROZEN,
        evaluation_id="26f4e07c-20da-4d6c-80ed-392fc290ae75",
        pair_id="pair-aad",
        slot="A2",
    )
    expected = {
        "artifact_type": controller.CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": state["evaluation_id"],
        "pair_id": "pair-aad",
        "slot": "A2",
        "schema_version": controller.CONTROLLER_STATE_SCHEMA,
        "protocol_sha256": controller.ADOPTED_PROTOCOL_SHA256,
        "contract_sha256": controller.ADOPTED_CONTRACT_SHA256,
    }
    expected_bytes = json.dumps(
        expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert controller.build_controller_aad(state) == expected_bytes
    assert set(json.loads(expected_bytes)) == {
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "schema_version",
        "protocol_sha256",
        "contract_sha256",
    }


def test_seal_and_open_enforce_key_custody_at_the_public_boundary() -> None:
    seal_parameters = inspect.signature(controller.seal_controller_state).parameters
    open_parameters = inspect.signature(controller.open_controller_package).parameters

    assert set(seal_parameters) == {"snapshot", "key_path", "custody_boundary"}
    assert {"key_path", "custody_boundary"}.issubset(open_parameters)
    assert "state" not in seal_parameters
    assert "key" not in seal_parameters
    assert "key" not in open_parameters
    assert not hasattr(controller, "ControllerKey")
    assert not hasattr(controller, "load_controller_key")


def test_aes_gcm_envelope_dimensions_digest_and_round_trip(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.SCORING_BOUND)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    envelope = controller.parse_sealed_package(sealed.package_bytes)

    assert set(envelope) == PACKAGE_KEYS
    assert len(base64.b64decode(envelope["nonce_b64"])) == 12
    assert len(base64.b64decode(envelope["tag_b64"])) == 16
    assert sealed.sealed_package_digest == hashlib.sha256(
        sealed.package_bytes
    ).hexdigest()
    opened = controller.open_controller_package(
        sealed.package_bytes,
        key_path=key_path,
        custody_boundary=boundary,
        expected_digest=sealed.sealed_package_digest,
        expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
        expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
        expected_slot=state["slot"],  # type: ignore[arg-type]
    )
    assert opened == state


@pytest.mark.parametrize(
    "mutation",
    [
        lambda envelope: envelope.update({"unknown": "value"}),
        lambda envelope: envelope.pop("tag_b64"),
        lambda envelope: envelope.update({"package_schema": "wrong"}),
        lambda envelope: envelope.update({"nonce_b64": base64.b64encode(bytes(11)).decode("ascii")}),
        lambda envelope: envelope.update({"ciphertext_b64": "not-base64"}),
    ],
)
def test_sealed_envelope_is_closed_and_base64_is_canonical(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    mutation,
) -> None:
    boundary, key_path, _, _ = custody
    sealed = _seal_state(
        _state(controller.ORDER_FROZEN),
        key_path=key_path,
        custody_boundary=boundary,
    )
    envelope = json.loads(sealed.package_bytes)
    mutation(envelope)
    malformed = json.dumps(
        envelope, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.parse_sealed_package(malformed)
    assert caught.value.code == controller.SEALED_PACKAGE_SCHEMA_FAILURE


def test_repeated_sealing_uses_fresh_nonce_regression_only(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.ORDER_FROZEN)
    first = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    second = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    first_envelope = controller.parse_sealed_package(first.package_bytes)
    second_envelope = controller.parse_sealed_package(second.package_bytes)

    assert first_envelope["nonce_b64"] != second_envelope["nonce_b64"]
    assert first_envelope["ciphertext_b64"] != second_envelope["ciphertext_b64"]
    assert random_domains.SAMPLING_ROLE == "REGRESSION_ONLY_NOT_PROOF"


def _rewrite_envelope(
    package_bytes: bytes, transform
) -> tuple[bytes, str]:
    envelope = json.loads(package_bytes)
    transform(envelope)
    rewritten = json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    return rewritten, hashlib.sha256(rewritten).hexdigest()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("evaluation_id", "00d26d75-cb2c-4f97-bb0a-f61a6d1af495"),
        ("pair_id", "wrong-pair"),
        ("slot", "A6"),
        ("artifact_type", "blind_scoring_bundle"),
        ("protocol_sha256", "f" * 64),
        ("contract_sha256", "e" * 64),
    ],
)
def test_wrong_aad_binding_fails_authentication(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    field: str,
    replacement: str,
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.SCORING_BOUND)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )

    def mutate(envelope: dict[str, str]) -> None:
        aad = json.loads(base64.b64decode(envelope["aad_utf8_b64"]))
        aad[field] = replacement
        envelope["aad_utf8_b64"] = base64.b64encode(
            json.dumps(aad, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")

    rewritten, digest = _rewrite_envelope(sealed.package_bytes, mutate)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            rewritten,
            key_path=key_path,
            custody_boundary=boundary,
            expected_digest=digest,
            expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
            expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
            expected_slot=state["slot"],  # type: ignore[arg-type]
        )
    assert caught.value.code == controller.AUTHENTICATION_FAILURE


@pytest.mark.parametrize("encrypted_field", ["ciphertext_b64", "tag_b64"])
def test_ciphertext_or_tag_corruption_fails_authentication(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    encrypted_field: str,
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.SCORING_BOUND)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )

    def mutate(envelope: dict[str, str]) -> None:
        raw = bytearray(base64.b64decode(envelope[encrypted_field]))
        raw[0] ^= 1
        envelope[encrypted_field] = base64.b64encode(raw).decode("ascii")

    rewritten, digest = _rewrite_envelope(sealed.package_bytes, mutate)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            rewritten,
            key_path=key_path,
            custody_boundary=boundary,
            expected_digest=digest,
            expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
            expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
            expected_slot=state["slot"],  # type: ignore[arg-type]
        )
    assert caught.value.code == controller.AUTHENTICATION_FAILURE


def test_wrong_key_and_key_id_mismatch_fail_closed(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, key_id, key_bytes = custody
    state = _state(controller.SCORING_BOUND)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    kwargs = {
        "expected_digest": sealed.sealed_package_digest,
        "expected_evaluation_id": state["evaluation_id"],
        "expected_pair_id": state["pair_id"],
        "expected_slot": state["slot"],
    }

    wrong_key_path = key_path.parent / "wrong-same-id.json"
    _write_key_record(wrong_key_path, key_id, os.urandom(32))
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            sealed.package_bytes,
            key_path=wrong_key_path,
            custody_boundary=boundary,
            **kwargs,  # type: ignore[arg-type]
        )
    assert caught.value.code == controller.AUTHENTICATION_FAILURE

    wrong_id_path = key_path.parent / "wrong-id.json"
    _write_key_record(wrong_id_path, "solo-r2-" + "b" * 32, key_bytes)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            sealed.package_bytes,
            key_path=wrong_id_path,
            custody_boundary=boundary,
            **kwargs,  # type: ignore[arg-type]
        )
    assert caught.value.code == controller.KEY_MATERIAL_FAILURE


def test_runtime_secret_sentinel_never_appears_in_package_or_diagnostics(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    capsys: pytest.CaptureFixture[str],
) -> None:
    boundary, key_path, key_id, _ = custody
    sentinel = ("runtime-secret-" + uuid4().hex + "-") * 4
    state = _state(controller.SCORING_BOUND, output_ref_suffix=sentinel)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    assert sentinel.encode("utf-8") not in sealed.package_bytes

    wrong_key_path = key_path.parent / "sentinel-wrong-key.json"
    _write_key_record(wrong_key_path, key_id, os.urandom(32))
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.open_controller_package(
            sealed.package_bytes,
            key_path=wrong_key_path,
            custody_boundary=boundary,
            expected_digest=sealed.sealed_package_digest,
            expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
            expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
            expected_slot=state["slot"],  # type: ignore[arg-type]
        )
    captured = capsys.readouterr()
    assert caught.value.code == controller.AUTHENTICATION_FAILURE
    assert str(caught.value) == controller.AUTHENTICATION_FAILURE
    assert sentinel not in str(caught.value)
    assert sentinel not in captured.out
    assert sentinel not in captured.err


def test_rng_failure_uses_fixed_sealing_code_without_raw_exception(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.ORDER_FROZEN)

    secret_detail = "rng-secret-" + uuid4().hex

    def fail_rng(_: int) -> bytes:
        raise OSError(secret_detail)

    monkeypatch.setattr(controller.os, "urandom", fail_rng)
    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            state, key_path=key_path, custody_boundary=boundary
        )
    assert caught.value.code == controller.SEALING_FAILURE
    assert str(caught.value) == controller.SEALING_FAILURE
    rendered = "".join(traceback.format_exception(caught.value))
    assert secret_detail not in rendered


def test_crypto_library_failure_uses_fixed_sealing_code_without_raw_exception(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.ORDER_FROZEN)
    secret_detail = "library-secret-" + uuid4().hex

    class FailingAESGCM:
        def __init__(self, _: bytes) -> None:
            raise RuntimeError(secret_detail)

    monkeypatch.setattr(controller, "AESGCM", FailingAESGCM)
    with pytest.raises(controller.ControllerStateError) as caught:
        _seal_state(
            state, key_path=key_path, custody_boundary=boundary
        )
    assert caught.value.code == controller.SEALING_FAILURE
    assert str(caught.value) == controller.SEALING_FAILURE
    rendered = "".join(traceback.format_exception(caught.value))
    assert secret_detail not in rendered


def test_cross_boundary_parsers_reject_the_other_artifact(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    state = _state(controller.SCORING_BOUND)
    sealed = _seal_state(
        state, key_path=key_path, custody_boundary=boundary
    )
    scoring_bundle = bundle_module.build_blind_scoring_bundle(
        evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
        pair_id=state["pair_id"],  # type: ignore[arg-type]
        slot=state["slot"],  # type: ignore[arg-type]
        rubric_id="rubric-v1",
        outputs_by_label={
            _hex_id("bundle-label-0"): "first scorer-visible output",
            _hex_id("bundle-label-1"): "second scorer-visible output",
        },
        presentation_entropy=bytes(reversed(range(32))),
    )
    bundle_bytes = bundle_module.encode_blind_scoring_bundle(scoring_bundle)

    with pytest.raises(controller.ControllerStateError) as caught:
        controller.parse_sealed_package(bundle_bytes)
    assert caught.value.code == controller.SEALED_PACKAGE_SCHEMA_FAILURE
    with pytest.raises(bundle_module.BlindScoringBundleError):
        bundle_module.parse_blind_scoring_bundle(sealed.package_bytes)


def test_failure_paths_create_no_repo_secret_or_package_artifacts(
    custody: tuple[controller.CustodyBoundary, Path, str, bytes],
) -> None:
    boundary, key_path, _, _ = custody
    prospective = (
        REPO_ROOT / "controller-key.synthetic.json",
        REPO_ROOT / "sealed-controller-state.synthetic.json",
        REPO_ROOT / "blind-scoring-bundle.synthetic.json",
    )
    assert all(not path.exists() for path in prospective)
    state = _state(controller.ORDER_FROZEN)
    with pytest.raises(controller.ControllerStateError):
        controller.open_controller_package(
            b"not-a-package\n",
            key_path=key_path,
            custody_boundary=boundary,
            expected_digest="0" * 64,
            expected_evaluation_id=state["evaluation_id"],  # type: ignore[arg-type]
            expected_pair_id=state["pair_id"],  # type: ignore[arg-type]
            expected_slot=state["slot"],  # type: ignore[arg-type]
        )
    assert all(not path.exists() for path in prospective)


def test_create_controller_key_is_create_once_and_never_returns_key_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    state = _state(controller.ORDER_FROZEN)
    draws = iter(
        (
            bytes.fromhex("11" * 16),
            bytes.fromhex("22" * 32),
            bytes.fromhex("33" * 12),
        )
    )
    monkeypatch.setattr(controller.os, "urandom", lambda _size: next(draws))

    key_id = controller.create_controller_key(
        key_path, custody_boundary=boundary
    )

    assert key_id == "solo-r2-" + "11" * 16
    assert set(inspect.signature(controller.create_controller_key).parameters) == {
        "path",
        "custody_boundary",
    }
    assert "key" not in inspect.signature(
        controller.create_controller_key
    ).return_annotation.lower()
    assert key_path.read_bytes() == json.dumps(
        {
            "schema_version": controller.CONTROLLER_KEY_SCHEMA,
            "key_id": key_id,
            "key_b64": base64.b64encode(bytes.fromhex("22" * 32)).decode("ascii"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert not key_path.with_name(f".{key_path.name}.tmp").exists()
    assert key_path.stat().st_nlink == 1

    sealed = _seal_state(
        state,
        key_path=key_path,
        custody_boundary=boundary,
    )
    assert controller.parse_sealed_package(sealed.package_bytes)["key_id"] == key_id


def test_create_controller_key_rejects_existing_target_or_temporary_without_overwrite(
    tmp_path: Path,
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    key_path.write_bytes(b"existing-target")
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)
    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert key_path.read_bytes() == b"existing-target"

    key_path.unlink()
    temporary = key_path.with_name(f".{key_path.name}.tmp")
    temporary.write_bytes(b"existing-temporary")
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)
    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert not key_path.exists()
    assert temporary.read_bytes() == b"existing-temporary"


def test_create_controller_key_fsync_failure_leaves_no_published_or_temporary_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    monkeypatch.setattr(controller.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError()))

    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)

    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert not key_path.exists()
    assert not key_path.with_name(f".{key_path.name}.tmp").exists()


def test_create_controller_key_pre_replace_inspection_failure_cleans_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    real_exists = controller._path_entry_exists
    calls = 0

    def fail_third_inspection(candidate: Path) -> bool:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise controller.ControllerStateError(controller.KEY_CUSTODY_FAILURE)
        return real_exists(candidate)

    monkeypatch.setattr(controller, "_path_entry_exists", fail_third_inspection)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)

    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert not key_path.exists()
    assert not key_path.with_name(f".{key_path.name}.tmp").exists()


def test_create_controller_key_preserves_published_orphan_after_uncertain_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    real_replace = os.replace

    def replace_then_fail(source: Path, target: Path) -> None:
        real_replace(source, target)
        raise OSError("synthetic uncertain replace")

    monkeypatch.setattr(controller.os, "replace", replace_then_fail)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)

    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert key_path.is_file()
    assert key_path.stat().st_nlink == 1
    assert not key_path.with_name(f".{key_path.name}.tmp").exists()


def test_create_controller_key_rejects_forbidden_target_and_rng_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, key_path = _new_key_target(tmp_path)
    forbidden = boundary.materialization_root / "controller-key.json"
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(forbidden, custody_boundary=boundary)
    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert not forbidden.exists()

    def fail_rng(_size: int) -> bytes:
        raise RuntimeError("secret rng detail")

    monkeypatch.setattr(controller.os, "urandom", fail_rng)
    with pytest.raises(controller.ControllerStateError) as caught:
        controller.create_controller_key(key_path, custody_boundary=boundary)
    assert caught.value.code == controller.SEALING_FAILURE
    assert str(caught.value) == controller.SEALING_FAILURE
    assert not key_path.exists()
