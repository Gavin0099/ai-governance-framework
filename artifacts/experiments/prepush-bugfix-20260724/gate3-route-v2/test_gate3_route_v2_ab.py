from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route
import gate3_route_v2_ab as ab


PAIR_ID = "gate3-v2-ab-synthetic-0001"
RUN_IDS = ("gate3-v2-ab-arm-a-0001", "gate3-v2-ab-arm-b-0001")
PROMPT = b"Produce the synthetic result."
SCHEMA = {
    "additionalProperties": False,
    "properties": {"status": {"enum": ["ok"], "type": "string"}},
    "required": ["status"],
    "type": "object",
}
EXPECTED = {"result.txt": b"synthetic result\n"}
TREATMENT = b"synthetic bug-fix skill packet\n"
ARM_FILES = {
    "A": {
        "auth.json": b"synthetic-auth\n",
        "task.txt": b"same-task\n",
        "treatment-manifest.json": ab.treatment_manifest("absent", "absent"),
    },
    "B": {
        "auth.json": b"synthetic-auth\n",
        "skill.packet": TREATMENT,
        "task.txt": b"same-task\n",
        "treatment-manifest.json": ab.treatment_manifest(
            "present", route._sha256_bytes(TREATMENT)
        ),
    },
}


def _result() -> route.SyntheticResult:
    return route.SyntheticResult(
        exit_code=0,
        stdout=b'{"type":"turn.completed"}\n',
        final_message=b'{"status":"ok"}',
        workspace=EXPECTED,
    )


def _manifest(**overrides: object) -> bytes:
    values: dict[str, object] = {
        "pair_id": PAIR_ID,
        "model_id": "synthetic-model-v1",
        "run_ids": RUN_IDS,
        "context_tokens": ("ARM_A_CONTEXT", "ARM_B_CONTEXT"),
        "prompt": PROMPT,
        "output_schema": SCHEMA,
        "baseline_workspace": {"calc.py": b"def add(a,b): return a-b\n"},
        "expected_workspace": EXPECTED,
        "arm_a_files": ARM_FILES["A"],
        "arm_b_files": ARM_FILES["B"],
        "treatment_packet_sha256": route._sha256_bytes(TREATMENT),
    }
    values.update(overrides)
    return ab.build_contract_manifest(**values)  # type: ignore[arg-type]


def _run(
    tmp_path: Path, *, execution_order: tuple[str, str] = ("A", "B")
) -> tuple[
    Path, bytes, dict[str, ab.SyntheticABArmRunner], dict[str, str]
]:
    manifest = _manifest(execution_order=execution_order)
    digest = route._sha256_bytes(manifest)
    runners = {
        arm_id: ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES[arm_id],
            result=_result(),
        )
        for arm_id in ("A", "B")
    }
    output = tmp_path / "pair-public"
    result = ab.orchestrate_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=digest,
        prompt=PROMPT,
        output_schema=SCHEMA,
        expected_workspace=EXPECTED,
        credential_fixture=b"synthetic-auth\n",
        arm_runners=runners,
    )
    assert result.decision == "SUCCESS"
    return output, manifest, runners, dict(result.pins)


def _rewrite(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_bytes(route._json_bytes(value))


def test_synthetic_pair_builds_two_verified_arms_and_fixed_ledger(
    tmp_path: Path,
) -> None:
    output, manifest, runners, pins = _run(tmp_path)
    report = ab.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=pins,
    )
    assert report == {
        "claim": "synthetic_non_counted_route_qualification_only",
        "decision": "SUCCESS",
        "pair_id": PAIR_ID,
        "status": "PASS",
    }
    assert {arm: runner.calls for arm, runner in runners.items()} == {"A": 1, "B": 1}
    assert len(list((output / "attempt-ledger").glob("*.json"))) == 6
    assert sorted(path.name for path in (output / "arm-runtime" / "public").iterdir()) == sorted(RUN_IDS)
    for run_id in RUN_IDS:
        assert (output / "arm-runtime" / "public" / run_id / "input-attestation.json").is_file()


def test_completed_nonzero_arm_keeps_exactly_two_and_publishes_non_success(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    digest = route._sha256_bytes(manifest)
    runners = {
        "A": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES["A"],
            result=_result(),
        ),
        "B": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES["B"],
            result=route.SyntheticResult(
                exit_code=2,
                stdout=b'{"type":"turn.failed"}\n',
                final_message=b'{"status":"ok"}',
                workspace=EXPECTED,
            ),
        ),
    }
    output = tmp_path / "pair-public"
    result = ab.orchestrate_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=digest,
        prompt=PROMPT,
        output_schema=SCHEMA,
        expected_workspace=EXPECTED,
        credential_fixture=b"synthetic-auth\n",
        arm_runners=runners,
    )
    assert result.decision == "NON_SUCCESS"
    assert ab.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=digest,
        expected_pins=result.pins,
    )["decision"] == "NON_SUCCESS"
    assert {arm: runner.calls for arm, runner in runners.items()} == {"A": 1, "B": 1}


def test_cross_arm_mismatch_publishes_offline_verifiable_non_success(
    tmp_path: Path,
) -> None:
    output, manifest, _, pins = _run(tmp_path)
    arm_root = output / "arm-runtime" / "public" / RUN_IDS[1]

    preflight_path = arm_root / "preflight.json"
    _rewrite(
        preflight_path,
        lambda value: value.__setitem__("environment_projection_sha256", "0" * 64),
    )
    action_path = arm_root / "action.json"
    _rewrite(
        action_path,
        lambda value: value.__setitem__(
            "preflight_sha256", route._sha256_file(preflight_path)
        ),
    )
    input_path = arm_root / "input-attestation.json"
    _rewrite(
        input_path,
        lambda value: value.__setitem__(
            "action_sha256", route._sha256_file(action_path)
        ),
    )
    packet_path = arm_root / "packet.json"

    def update_packet(value: dict[str, object]) -> None:
        value["action_sha256"] = route._sha256_file(action_path)
        value["input_attestation_sha256"] = route._sha256_file(input_path)

    _rewrite(packet_path, update_packet)
    seal_path = arm_root / "seal.json"
    _rewrite(
        seal_path,
        lambda value: value.__setitem__(
            "packet_sha256", route._sha256_file(packet_path)
        ),
    )
    final_path = arm_root / "final.json"

    def update_final(value: dict[str, object]) -> None:
        value["packet_sha256"] = route._sha256_file(packet_path)
        value["seal_sha256"] = route._sha256_file(seal_path)

    _rewrite(final_path, update_final)
    final_digest = route._sha256_file(final_path)
    (output / "arm-b-final.sha256").write_bytes(ab._pin_bytes(final_digest))
    pins["arm_b_final_sha256"] = final_digest

    (output / "pair-final.json").unlink()
    receipt = ab._rebuild_receipt(
        output,
        manifest=json.loads(manifest),
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=pins,
    )
    assert receipt["checks"]["cross_arm_equality"] == "FAIL"
    assert receipt["decision"] == "NON_SUCCESS"
    route._publish_create_once(output / "pair-final.json", route._json_bytes(receipt))

    assert ab.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=pins,
    )["decision"] == "NON_SUCCESS"

    _rewrite(
        output / "pair-final.json",
        lambda value: value.__setitem__("decision", "SUCCESS"),
    )
    with pytest.raises(route.RouteV2Error, match="pair receipt differs"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["model_build_identity"].__setitem__("model_id", "other-model"),
        lambda value: value["ordered_arms"][0].__setitem__("context_token", "ARM_B_CONTEXT"),
        lambda value: value["ordered_arms"][0].__setitem__("run_id", RUN_IDS[1]),
        lambda value: value["ordered_arms"][0].__setitem__(
            "treatment_projection",
            {
                "state": "present",
                "treatment_manifest_sha256": route._sha256_bytes(
                    ARM_FILES["B"]["treatment-manifest.json"]
                ),
                "treatment_packet_sha256": route._sha256_bytes(TREATMENT),
            },
        ),
    ],
)
def test_manifest_mutations_fail_before_pair_execution(mutation) -> None:
    payload = _manifest()
    pinned_digest = route._sha256_bytes(payload)
    value = json.loads(payload)
    mutation(value)
    mutated = route._json_bytes(value)
    with pytest.raises(route.RouteV2Error):
        ab._validate_manifest(mutated, pinned_digest)


def test_staged_input_mismatch_fails_before_runner_invocation(tmp_path: Path) -> None:
    manifest = _manifest()
    digest = route._sha256_bytes(manifest)
    runners = {
        "A": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files={"auth.json": b"wrong\n"},
            result=_result(),
        ),
        "B": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES["B"],
            result=_result(),
        ),
    }
    with pytest.raises(route.RouteV2Error, match="staged admission"):
        ab.orchestrate_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            expected_manifest_sha256=digest,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            credential_fixture=b"synthetic-auth\n",
            arm_runners=runners,
        )
    assert runners["A"].calls == 0
    assert runners["B"].calls == 0


def test_model_and_credential_mismatches_fail_before_any_invocation(tmp_path: Path) -> None:
    manifest = _manifest()
    digest = route._sha256_bytes(manifest)
    runners = {
        "A": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"different-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES["A"],
            result=_result(),
        ),
        "B": ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="different-model",
            staged_files=ARM_FILES["B"],
            result=_result(),
        ),
    }
    with pytest.raises(route.RouteV2Error, match="credential fixtures"):
        ab.orchestrate_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            expected_manifest_sha256=digest,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            credential_fixture=b"synthetic-auth\n",
            arm_runners=runners,
        )
    assert not (tmp_path / "pair-public").exists()
    assert all(runner.calls == 0 for runner in runners.values())

    runners = {
        arm_id: ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="different-model" if arm_id == "B" else "synthetic-model-v1",
            staged_files=ARM_FILES[arm_id],
            result=_result(),
        )
        for arm_id in ("A", "B")
    }
    with pytest.raises(route.RouteV2Error, match="staged admission"):
        ab.orchestrate_pair(
            tmp_path / "pair-public-model",
            contract_manifest=manifest,
            expected_manifest_sha256=digest,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            credential_fixture=b"synthetic-auth\n",
            arm_runners=runners,
        )
    assert all(runner.calls == 0 for runner in runners.values())


def test_prompt_mismatch_fails_before_artifact_publication(tmp_path: Path) -> None:
    manifest = _manifest()
    digest = route._sha256_bytes(manifest)
    runners = {
        arm_id: ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES[arm_id],
            result=_result(),
        )
        for arm_id in ("A", "B")
    }
    with pytest.raises(route.RouteV2Error, match="invocation inputs"):
        ab.orchestrate_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            expected_manifest_sha256=digest,
            prompt=b"different prompt",
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            credential_fixture=b"synthetic-auth\n",
            arm_runners=runners,
        )
    assert not (tmp_path / "pair-public").exists()


@pytest.mark.parametrize(
    ("target", "mutate"),
    [
        ("pair-action.json", lambda value: value.__setitem__("model_build_identity", {**value["model_build_identity"], "model_id": "mutated"})),
        ("pair-preflight-attestation.json", lambda value: value.__setitem__("credential_seed_equal", "FAIL")),
        ("pair-final.json", lambda value: value.__setitem__("decision", "NON_SUCCESS")),
        ("arm-runtime/public/gate3-v2-ab-arm-a-0001/input-attestation.json", lambda value: value.__setitem__("treatment_state", "present")),
    ],
)
def test_published_json_mutations_fail_offline_verification(
    tmp_path: Path, target: str, mutate
) -> None:
    output, manifest, _, pins = _run(tmp_path)
    _rewrite(output / target, mutate)
    with pytest.raises(route.RouteV2Error):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


def test_coherent_single_arm_model_rewrite_is_rejected_by_pair_binding(
    tmp_path: Path,
) -> None:
    output, manifest, _, pins = _run(tmp_path)
    arm_root = output / "arm-runtime" / "public" / RUN_IDS[1]
    action_path = arm_root / "action.json"
    input_path = arm_root / "input-attestation.json"
    packet_path = arm_root / "packet.json"
    seal_path = arm_root / "seal.json"
    final_path = arm_root / "final.json"

    action = json.loads(action_path.read_text(encoding="utf-8"))
    action["model_id"] = "coherently-rewritten-model"
    action_path.write_bytes(route._json_bytes(action))
    input_attestation = json.loads(input_path.read_text(encoding="utf-8"))
    input_attestation["action_sha256"] = route._sha256_file(action_path)
    input_attestation["model_id"] = action["model_id"]
    input_path.write_bytes(route._json_bytes(input_attestation))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["action_sha256"] = route._sha256_file(action_path)
    packet["input_attestation_sha256"] = route._sha256_file(input_path)
    packet_path.write_bytes(route._json_bytes(packet))
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["packet_sha256"] = route._sha256_file(packet_path)
    seal_path.write_bytes(route._json_bytes(seal))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final["packet_sha256"] = route._sha256_file(packet_path)
    final["seal_sha256"] = route._sha256_file(seal_path)
    final_path.write_bytes(route._json_bytes(final))
    final_pin = output / "arm-b-final.sha256"
    final_pin.write_bytes(ab._pin_bytes(route._sha256_file(final_path)))

    assert route.verify(
        arm_root,
        locator_root=output / "arm-runtime" / "locators",
        external_root=output / "arm-runtime" / "external",
        run_id=RUN_IDS[1],
        expected_action_sha256=route._sha256_file(action_path),
        expected_final_sha256=route._sha256_file(final_path),
        _trusted_route_root=output / "arm-runtime",
    )["status"] == "PASS"
    with pytest.raises(route.RouteV2Error, match="arm final differs from external pin"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


def test_missing_extra_and_reordered_ledger_fail(tmp_path: Path) -> None:
    output, manifest, _, pins = _run(tmp_path)
    ledger = output / "attempt-ledger"
    first = sorted(ledger.glob("*.json"))[0]
    first.unlink()
    with pytest.raises(route.RouteV2Error, match="artifact tree is not closed"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


def test_third_event_or_duplicate_public_artifact_fails(tmp_path: Path) -> None:
    output, manifest, _, pins = _run(tmp_path)
    (output / "unexpected.json").write_bytes(b"{}\n")
    with pytest.raises(route.RouteV2Error, match="artifact tree is not closed"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


def test_pair_receipt_contains_no_private_bytes_paths_or_skill_text(tmp_path: Path) -> None:
    output, _, _, _ = _run(tmp_path)
    payload = (output / "pair-final.json").read_bytes()
    route._validate_public_payload(payload)
    assert TREATMENT not in payload
    assert str(tmp_path).encode() not in payload
    assert b"synthetic-auth" not in payload


def test_non_treatment_staged_difference_is_rejected_before_manifest_build() -> None:
    arm_b = dict(ARM_FILES["B"])
    arm_b["task.txt"] = b"different-task\n"
    with pytest.raises(route.RouteV2Error, match="non-treatment staged inputs differ"):
        _manifest(arm_b_files=arm_b)


def test_pair_preflight_requires_capability_bound_observation(tmp_path: Path) -> None:
    manifest = ab._validate_manifest(_manifest(), route._sha256_bytes(_manifest()))
    with pytest.raises(route.RouteV2Error, match="preflight observation is invalid"):
        ab._pair_preflight(manifest, object())  # type: ignore[arg-type]

    roots = (tmp_path / "arm-a-auth", tmp_path / "arm-b-auth")
    for root in roots:
        root.mkdir()
        route._current_user_only(root, True)
        auth = root / "auth.json"
        auth.write_bytes(b"same-auth\n")
        route._current_user_only(auth, False)
    observation = ab._observe_pair_preflight(*roots)
    assert ab._pair_preflight(manifest, observation) == ab._expected_pair_preflight(
        manifest
    )

    (roots[1] / "unexpected.txt").write_bytes(b"extra\n")
    with pytest.raises(route.RouteV2Error, match="auth inventory is invalid"):
        ab._observe_pair_preflight(*roots)


def _coherently_rewrite_terminal(
    output: Path, *, ordinal: int, terminal_class: str
) -> str:
    ledger = output / "attempt-ledger"
    paths = sorted(ledger.glob("*.json"))
    previous = "absent"
    for index, path in enumerate(paths):
        event = json.loads(path.read_text(encoding="utf-8"))
        if index == ordinal:
            event["terminal_class"] = terminal_class
        event["previous_event_sha256"] = previous
        payload = route._json_bytes(event)
        path.write_bytes(payload)
        previous = route._sha256_bytes(payload)
    (output / "attempt-ledger.sha256").write_bytes(ab._pin_bytes(previous))
    return previous


def test_coherent_ledger_terminal_rewrite_fails_external_and_arm_binding(
    tmp_path: Path,
) -> None:
    output, manifest, _, pins = _run(tmp_path)
    rewritten = _coherently_rewrite_terminal(
        output, ordinal=2, terminal_class="FAILURE"
    )
    with pytest.raises(route.RouteV2Error, match="ledger differs from external pin"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )

    attacker_pins = dict(pins)
    attacker_pins["attempt_ledger_final_sha256"] = rewritten
    with pytest.raises(route.RouteV2Error, match="ledger terminal differs from arm final"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=attacker_pins,
        )


@pytest.mark.parametrize(
    "relative",
    [
        "arm-runtime/public/gate3-v2-ab-arm-a-0001/nested/extra.bin",
        "attempt-ledger/extra.bin",
    ],
)
def test_recursive_extra_artifact_is_rejected(
    tmp_path: Path, relative: str
) -> None:
    output, manifest, _, pins = _run(tmp_path)
    extra = output / relative
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"\x00\xff")
    with pytest.raises(route.RouteV2Error, match="artifact tree is not closed"):
        ab.verify_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=route._sha256_bytes(manifest),
            expected_pins=pins,
        )


def test_reverse_execution_order_is_verified(tmp_path: Path) -> None:
    output, manifest, runners, pins = _run(tmp_path, execution_order=("B", "A"))
    assert ab.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=pins,
    )["status"] == "PASS"
    ledger = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((output / "attempt-ledger").glob("*.json"))
    ]
    assert (ledger[1]["arm_id"], ledger[3]["arm_id"]) == ("B", "A")
    assert {arm: runner.calls for arm, runner in runners.items()} == {"A": 1, "B": 1}


def test_route_raise_writes_terminal_and_does_not_start_second_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest()
    digest = route._sha256_bytes(manifest)
    runners = {
        arm_id: ab.SyntheticABArmRunner(
            contract_manifest_sha256=digest,
            credential_fixture=b"synthetic-auth\n",
            model_id="synthetic-model-v1",
            staged_files=ARM_FILES[arm_id],
            result=_result(),
        )
        for arm_id in ("A", "B")
    }

    def raising_route(*args: object, **kwargs: object) -> None:
        raise route.RouteV2Error("synthetic route failure")

    monkeypatch.setattr(ab.route, "orchestrate", raising_route)
    output = tmp_path / "pair-public"
    with pytest.raises(route.RouteV2Error, match="synthetic route failure"):
        ab.orchestrate_pair(
            output,
            contract_manifest=manifest,
            expected_manifest_sha256=digest,
            prompt=PROMPT,
            output_schema=SCHEMA,
            expected_workspace=EXPECTED,
            credential_fixture=b"synthetic-auth\n",
            arm_runners=runners,
        )
    ledger = sorted((output / "attempt-ledger").glob("*.json"))
    assert [path.name for path in ledger] == [
        "0000-pair_action_pinned.json",
        "0001-first_arm_started.json",
        "0002-first_arm_terminal.json",
    ]
    terminal = json.loads(ledger[-1].read_text(encoding="utf-8"))
    assert terminal["terminal_class"] == "RAISED"
    assert terminal["arm_id"] == "A"
    assert all(runner.calls == 0 for runner in runners.values())
