from __future__ import annotations

import json
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import gate3_route_v2 as route


AUTHORIZATION = "gate3_route_v2_ab_synthetic_non_counted_only"
MANIFEST_SCHEMA = "gate3-route-v2-ab.contract-manifest.v1"
PREFLIGHT_SCHEMA = "gate3-route-v2-ab.pair-preflight-attestation.v1"
PAIR_ACTION_SCHEMA = "gate3-route-v2-ab.pair-action.v1"
LEDGER_SCHEMA = "gate3-route-v2-ab.attempt-ledger-event.v1"
PAIR_RECEIPT_SCHEMA = "gate3-route-v2-ab.final-receipt.v1"
DESIGN_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "governance"
    / "gate3-route-v2-ab-design-candidate-20260808.md"
)
PASS_FIELDS = (
    "credential_acl",
    "model_selector_match",
    "only_auth_inventory",
    "staged_acl",
    "staged_content_match",
    "staged_inventory_match",
)
EVENTS = (
    ("pair_action_pinned", "not_applicable"),
    ("first_arm_started", "not_applicable"),
    ("first_arm_terminal", None),
    ("second_arm_started", "not_applicable"),
    ("second_arm_terminal", None),
    ("pair_closed", "not_applicable"),
)


@dataclass(frozen=True)
class PairResult:
    output_root: Path
    receipt: Path
    decision: str
    pins: Mapping[str, str]


def _validate_expected_pins(value: object) -> dict[str, str]:
    keys = {
        "arm_a_final_sha256",
        "arm_b_final_sha256",
        "attempt_ledger_final_sha256",
        "pair_action_sha256",
        "pair_preflight_attestation_sha256",
    }
    return _digest_map(value, keys, "external pair pins")


_PREFLIGHT_OBSERVATION_TOKEN = object()


class PairPreflightObservation:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("PairPreflightObservation cannot be subclassed")

    def __init__(self, *, _token: object) -> None:
        if _token is not _PREFLIGHT_OBSERVATION_TOKEN:
            raise route.RouteV2Error("pair preflight observation is invalid")
        self._token = _token


def _observe_pair_preflight(
    arm_a_root: Path, arm_b_root: Path
) -> PairPreflightObservation:
    roots = (arm_a_root.resolve(), arm_b_root.resolve())
    if roots[0] == roots[1]:
        raise route.RouteV2Error("pair private roots are not distinct")
    credentials: list[bytes] = []
    for root in roots:
        route._verify_current_user_only(root, True)
        entries = list(root.iterdir()) if root.is_dir() else []
        if (
            len(entries) != 1
            or entries[0].name != "auth.json"
            or entries[0].is_symlink()
            or not entries[0].is_file()
        ):
            raise route.RouteV2Error("pair auth inventory is invalid")
        route._verify_current_user_only(entries[0], False)
        credentials.append(entries[0].read_bytes())
    if credentials[0] != credentials[1]:
        raise route.RouteV2Error("credential seeds differ")
    return PairPreflightObservation(_token=_PREFLIGHT_OBSERVATION_TOKEN)


def _implementation_sha256() -> str:
    return route._sha256_file(Path(__file__))


def _canonical_digest(value: object) -> str:
    return route._sha256_bytes(route._json_bytes(value))


def _pin_bytes(digest: str) -> bytes:
    if route.SHA256_RE.fullmatch(digest) is None:
        raise route.RouteV2Error("pin identity is invalid")
    return (digest + "\n").encode("ascii")


def _read_pin(path: Path) -> str:
    try:
        payload = path.read_bytes()
        digest = payload.decode("ascii").removesuffix("\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise route.RouteV2Error("pin is invalid") from exc
    if payload != _pin_bytes(digest):
        raise route.RouteV2Error("pin is invalid")
    return digest


def _digest_map(value: object, keys: set[str], label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise route.RouteV2Error(f"{label} is invalid")
    normalized = dict(value)
    if any(
        not isinstance(normalized[key], str)
        or route.SHA256_RE.fullmatch(normalized[key]) is None
        for key in keys
    ):
        raise route.RouteV2Error(f"{label} is invalid")
    return normalized


def staged_manifest(files: Mapping[str, bytes]) -> dict[str, object]:
    return {"artifacts": route._artifact_projection(route._validate_artifacts(files))}


def treatment_manifest(state: str, packet_sha256: str) -> bytes:
    if state == "absent" and packet_sha256 == "absent":
        value = {
            "packet_artifact_id": "absent",
            "packet_sha256": "absent",
            "state": "absent",
        }
    elif (
        state == "present"
        and isinstance(packet_sha256, str)
        and route.SHA256_RE.fullmatch(packet_sha256) is not None
    ):
        value = {
            "packet_artifact_id": "skill.packet",
            "packet_sha256": packet_sha256,
            "state": "present",
        }
    else:
        raise route.RouteV2Error("treatment manifest is invalid")
    return route._json_bytes(value)


def _validate_treatment_files(
    arm_id: str, files: Mapping[str, bytes], packet_sha256: str
) -> dict[str, str]:
    normalized = route._validate_artifacts(files)
    state = "absent" if arm_id == "A" else "present"
    expected_packet = "absent" if arm_id == "A" else packet_sha256
    expected_manifest = treatment_manifest(state, expected_packet)
    if normalized.get("treatment-manifest.json") != expected_manifest:
        raise route.RouteV2Error("canonical treatment manifest differs")
    packet = normalized.get("skill.packet")
    if arm_id == "A" and packet is not None:
        raise route.RouteV2Error("absent treatment contains a packet")
    if arm_id == "B" and (
        packet is None or route._sha256_bytes(packet) != packet_sha256
    ):
        raise route.RouteV2Error("present treatment packet differs")
    return {
        "state": state,
        "treatment_manifest_sha256": route._sha256_bytes(expected_manifest),
        "treatment_packet_sha256": expected_packet,
    }


def _common_staged_projection(files: Mapping[str, bytes]) -> list[dict[str, object]]:
    return [
        item
        for item in staged_manifest(files)["artifacts"]
        if item["artifact_id"] not in {"skill.packet", "treatment-manifest.json"}
    ]


def build_contract_manifest(
    *,
    pair_id: str,
    model_id: str,
    run_ids: tuple[str, str],
    context_tokens: tuple[str, str],
    prompt: bytes,
    output_schema: dict[str, Any],
    baseline_workspace: Mapping[str, bytes],
    expected_workspace: Mapping[str, bytes],
    arm_a_files: Mapping[str, bytes],
    arm_b_files: Mapping[str, bytes],
    treatment_packet_sha256: str,
    execution_order: tuple[str, str] = ("A", "B"),
) -> bytes:
    pair_id = route._validate_public_token(pair_id, "pair identity")
    model_id = route._validate_public_token(model_id, "model identity")
    if len(set(run_ids)) != 2 or len(set(context_tokens)) != 2:
        raise route.RouteV2Error("pair contexts are not distinct")
    for run_id in run_ids:
        route._validate_run_id(run_id)
    for token in context_tokens:
        route._validate_public_token(token, "context token")
    if route.SHA256_RE.fullmatch(treatment_packet_sha256) is None:
        raise route.RouteV2Error("treatment packet identity is invalid")
    if set(execution_order) != {"A", "B"} or len(execution_order) != 2:
        raise route.RouteV2Error("execution order is invalid")
    schema = route._validate_schema_definition(output_schema)
    baseline = staged_manifest(baseline_workspace)
    expected = staged_manifest(expected_workspace)
    a_manifest = staged_manifest(arm_a_files)
    b_manifest = staged_manifest(arm_b_files)
    treatments = {
        "A": _validate_treatment_files(
            "A", arm_a_files, treatment_packet_sha256
        ),
        "B": _validate_treatment_files(
            "B", arm_b_files, treatment_packet_sha256
        ),
    }
    if _common_staged_projection(arm_a_files) != _common_staged_projection(arm_b_files):
        raise route.RouteV2Error("non-treatment staged inputs differ")
    implementation = _implementation_sha256()
    route_implementation = route._implementation_sha256()
    policies = {
        name: route._sha256_bytes((name + ":v1\n").encode("ascii"))
        for name in (
            "common_harness",
            "credential",
            "environment",
            "path_normalization",
            "permissions",
            "schema_set",
            "timeout",
        )
    }
    action_inputs = {
        "baseline_workspace_sha256": _canonical_digest(baseline),
        "expected_workspace_sha256": _canonical_digest(expected),
        "output_schema_sha256": _canonical_digest(schema),
        "prompt_sha256": route._sha256_bytes(prompt),
    }
    implementations = {
        "pair_builder_sha256": implementation,
        "pair_orchestrator_sha256": implementation,
        "pair_verifier_sha256": implementation,
        "single_arm_route_sha256": route_implementation,
        "single_arm_runner_sha256": implementation,
        "single_arm_verifier_sha256": route_implementation,
    }
    arm_sources = {
        "A": {
            "context_token": context_tokens[0],
            "run_id": run_ids[0],
            "staged_input_manifest_sha256": _canonical_digest(a_manifest),
        },
        "B": {
            "context_token": context_tokens[1],
            "run_id": run_ids[1],
            "staged_input_manifest_sha256": _canonical_digest(b_manifest),
        },
    }
    ordered_arms = [
        {
            "arm_id": arm_id,
            **arm_sources[arm_id],
            "single_arm_authorization": route.AUTHORIZATION,
            "treatment_projection": treatments[arm_id],
        }
        for arm_id in execution_order
    ]
    value = {
        "action_inputs": action_inputs,
        "authorization": AUTHORIZATION,
        "design_sha256": route._sha256_file(DESIGN_PATH),
        "implementations": implementations,
        "model_build_identity": {
            "cli_version": "synthetic",
            "command_contract_sha256": route_implementation,
            "executable_sha256": route_implementation,
            "model_id": model_id,
            "runner_sha256": implementation,
        },
        "ordered_arms": ordered_arms,
        "pair_id": pair_id,
        "policies": policies,
        "schema": MANIFEST_SCHEMA,
        "staged_input_projections": {
            "A": a_manifest,
            "B": b_manifest,
        },
    }
    return route._json_bytes(value)


def _validate_manifest(payload: bytes, expected_sha256: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise route.RouteV2Error("contract manifest is invalid") from exc
    if (
        not isinstance(value, dict)
        or payload != route._json_bytes(value)
        or route._sha256_bytes(payload) != expected_sha256
        or set(value)
        != {
            "action_inputs",
            "authorization",
            "design_sha256",
            "implementations",
            "model_build_identity",
            "ordered_arms",
            "pair_id",
            "policies",
            "schema",
            "staged_input_projections",
        }
        or value.get("schema") != MANIFEST_SCHEMA
        or value.get("authorization") != AUTHORIZATION
        or value.get("design_sha256") != route._sha256_file(DESIGN_PATH)
    ):
        raise route.RouteV2Error("contract manifest is invalid")
    route._validate_public_token(value.get("pair_id"), "pair identity")
    _digest_map(
        value.get("action_inputs"),
        {
            "baseline_workspace_sha256",
            "expected_workspace_sha256",
            "output_schema_sha256",
            "prompt_sha256",
        },
        "action inputs",
    )
    implementations = _digest_map(
        value.get("implementations"),
        {
            "pair_builder_sha256",
            "pair_orchestrator_sha256",
            "pair_verifier_sha256",
            "single_arm_route_sha256",
            "single_arm_runner_sha256",
            "single_arm_verifier_sha256",
        },
        "implementation identity",
    )
    if implementations != {
        "pair_builder_sha256": _implementation_sha256(),
        "pair_orchestrator_sha256": _implementation_sha256(),
        "pair_verifier_sha256": _implementation_sha256(),
        "single_arm_route_sha256": route._implementation_sha256(),
        "single_arm_runner_sha256": _implementation_sha256(),
        "single_arm_verifier_sha256": route._implementation_sha256(),
    }:
        raise route.RouteV2Error("implementation identity differs")
    _digest_map(
        value.get("policies"),
        {
            "common_harness",
            "credential",
            "environment",
            "path_normalization",
            "permissions",
            "schema_set",
            "timeout",
        },
        "policy identity",
    )
    model = value.get("model_build_identity")
    if not isinstance(model, Mapping) or set(model) != {
        "cli_version",
        "command_contract_sha256",
        "executable_sha256",
        "model_id",
        "runner_sha256",
    }:
        raise route.RouteV2Error("model build identity is invalid")
    route._validate_public_token(model.get("model_id"), "model identity")
    for key in ("command_contract_sha256", "executable_sha256", "runner_sha256"):
        if not isinstance(model.get(key), str) or route.SHA256_RE.fullmatch(model[key]) is None:
            raise route.RouteV2Error("model build identity is invalid")
    if model.get("cli_version") != "synthetic":
        raise route.RouteV2Error("model build identity is invalid")
    arms = value.get("ordered_arms")
    if not isinstance(arms, list) or len(arms) != 2:
        raise route.RouteV2Error("ordered arms are invalid")
    if {arm.get("arm_id") for arm in arms if isinstance(arm, Mapping)} != {"A", "B"}:
        raise route.RouteV2Error("ordered arms are invalid")
    for arm in arms:
        arm_id = arm.get("arm_id")
        if not isinstance(arm, Mapping) or set(arm) != {
            "arm_id", "context_token", "run_id", "single_arm_authorization",
            "staged_input_manifest_sha256", "treatment_projection",
        } or arm.get("arm_id") != arm_id or arm.get("single_arm_authorization") != route.AUTHORIZATION:
            raise route.RouteV2Error("ordered arms are invalid")
        route._validate_run_id(arm.get("run_id"))
        route._validate_public_token(arm.get("context_token"), "context token")
        if not isinstance(arm.get("staged_input_manifest_sha256"), str) or route.SHA256_RE.fullmatch(arm["staged_input_manifest_sha256"]) is None:
            raise route.RouteV2Error("ordered arms are invalid")
        treatment = route._validate_treatment_projection(arm.get("treatment_projection"))
        if (arm_id == "A") is not (treatment["state"] == "absent"):
            raise route.RouteV2Error("ordered treatment is invalid")
    if len({arm["run_id"] for arm in arms}) != 2 or len({arm["context_token"] for arm in arms}) != 2:
        raise route.RouteV2Error("ordered arm contexts are not distinct")
    projections = value.get("staged_input_projections")
    if not isinstance(projections, Mapping) or set(projections) != {"A", "B"}:
        raise route.RouteV2Error("staged input projections are invalid")
    for arm in arms:
        projection = projections.get(arm["arm_id"])
        if (
            not isinstance(projection, Mapping)
            or set(projection) != {"artifacts"}
            or _canonical_digest(projection)
            != arm["staged_input_manifest_sha256"]
        ):
            raise route.RouteV2Error("staged input projections are invalid")
        route._validate_projection(projection.get("artifacts"))
    common = []
    for arm_id in ("A", "B"):
        common.append(
            [
                item
                for item in projections[arm_id]["artifacts"]
                if item["artifact_id"]
                not in {"skill.packet", "treatment-manifest.json"}
            ]
        )
    if common[0] != common[1]:
        raise route.RouteV2Error("non-treatment staged inputs differ")
    return value


def _expected_pair_preflight(manifest: Mapping[str, Any]) -> dict[str, object]:
    policies = manifest["policies"]
    return {
        "arm_a_acl": "PASS",
        "arm_a_only_auth_inventory": "PASS",
        "arm_b_acl": "PASS",
        "arm_b_only_auth_inventory": "PASS",
        "contract_manifest_sha256": _canonical_digest(manifest),
        "credential_policy_sha256": policies["credential"],
        "credential_seed_equal": "PASS",
        "normalization_policy_sha256": policies["path_normalization"],
        "pair_id": manifest["pair_id"],
        "private_roots_distinct": "PASS",
        "schema": PREFLIGHT_SCHEMA,
        "validator_sha256": _implementation_sha256(),
    }


def _pair_preflight(
    manifest: Mapping[str, Any], observation: PairPreflightObservation
) -> dict[str, object]:
    if (
        type(observation) is not PairPreflightObservation
        or getattr(observation, "_token", None) is not _PREFLIGHT_OBSERVATION_TOKEN
    ):
        raise route.RouteV2Error("pair preflight observation is invalid")
    return _expected_pair_preflight(manifest)


def _pair_action(
    manifest: Mapping[str, Any], preflight_sha256: str, preflight_pin_sha256: str
) -> dict[str, object]:
    action_inputs = manifest["action_inputs"]
    implementations = manifest["implementations"]
    policies = manifest["policies"]
    return {
        "authorization": AUTHORIZATION,
        "baseline_workspace_sha256": action_inputs["baseline_workspace_sha256"],
        "common_harness_sha256": policies["common_harness"],
        "contract_manifest_sha256": _canonical_digest(manifest),
        "credential_policy_sha256": policies["credential"],
        "environment_policy_sha256": policies["environment"],
        "expected_workspace_sha256": action_inputs["expected_workspace_sha256"],
        "model_build_identity": manifest["model_build_identity"],
        "ordered_arms": manifest["ordered_arms"],
        "output_schema_sha256": action_inputs["output_schema_sha256"],
        "pair_builder_sha256": implementations["pair_builder_sha256"],
        "pair_id": manifest["pair_id"],
        "pair_orchestrator_sha256": implementations["pair_orchestrator_sha256"],
        "pair_preflight_attestation_sha256": preflight_sha256,
        "pair_preflight_pin_sha256": preflight_pin_sha256,
        "pair_verifier_sha256": implementations["pair_verifier_sha256"],
        "path_normalization_policy_sha256": policies["path_normalization"],
        "permissions_sha256": policies["permissions"],
        "prompt_sha256": action_inputs["prompt_sha256"],
        "schema": PAIR_ACTION_SCHEMA,
        "schema_set_sha256": policies["schema_set"],
        "single_arm_route_sha256": implementations["single_arm_route_sha256"],
        "single_arm_runner_sha256": implementations["single_arm_runner_sha256"],
        "single_arm_verifier_sha256": implementations["single_arm_verifier_sha256"],
        "timeout_policy_sha256": policies["timeout"],
    }


class SyntheticABArmRunner:
    def __init__(
        self,
        *,
        contract_manifest_sha256: str,
        credential_fixture: bytes,
        model_id: str,
        staged_files: Mapping[str, bytes],
        result: route.SyntheticResult,
    ) -> None:
        if route.SHA256_RE.fullmatch(contract_manifest_sha256) is None:
            raise route.RouteV2Error("contract manifest identity is invalid")
        self._contract = contract_manifest_sha256
        if not isinstance(credential_fixture, bytes):
            raise route.RouteV2Error("credential fixture is invalid")
        self._credential = credential_fixture
        self._model_id = route._validate_public_token(model_id, "model identity")
        self._files = route._validate_artifacts(staged_files)
        self._result = result
        self.calls = 0
        self._prepared = False

    def credential_matches(self, expected: bytes) -> bool:
        return isinstance(expected, bytes) and self._credential == expected

    def admission_matches(self, arm: Mapping[str, object], model_id: str) -> bool:
        treatment = arm.get("treatment_projection")
        if not isinstance(treatment, Mapping):
            return False
        packet = self._files.get("skill.packet")
        packet_match = (
            treatment.get("state") == "absent"
            and treatment.get("treatment_packet_sha256") == "absent"
            and packet is None
        ) or (
            treatment.get("state") == "present"
            and isinstance(packet, bytes)
            and treatment.get("treatment_packet_sha256")
            == route._sha256_bytes(packet)
        )
        manifest = self._files.get("treatment-manifest.json")
        manifest_match = (
            isinstance(manifest, bytes)
            and treatment.get("treatment_manifest_sha256")
            == route._sha256_bytes(manifest)
            and manifest
            == treatment_manifest(
                str(treatment.get("state")),
                str(treatment.get("treatment_packet_sha256")),
            )
        )
        return (
            self._model_id == model_id
            and _canonical_digest(staged_manifest(self._files))
            == arm.get("staged_input_manifest_sha256")
            and packet_match
            and manifest_match
        )

    def capability(self) -> route.TrustedABArmRunner:
        return route._trusted_ab_arm_runner(
            execution_identity=self.execution_identity(),
            prepare=self._prepare,
            invoke=self._invoke,
        )

    def execution_identity(self) -> dict[str, str]:
        return {
            "cli_version": "synthetic",
            "command_contract_sha256": route._implementation_sha256(),
            "executable_sha256": route._implementation_sha256(),
            "kind": "synthetic",
            "runner_sha256": _implementation_sha256(),
        }

    def _prepare(self, private_root: Path, action_payload: bytes) -> bytes:
        if self._prepared or self.calls:
            raise route.RouteV2Error("A/B runner preparation is not create-once")
        action = json.loads(action_payload)
        expected = _canonical_digest(staged_manifest(self._files))
        if expected != action.get("staged_input_manifest_sha256"):
            raise route.RouteV2Error("staged input manifest differs")
        if action.get("model_id") != self._model_id:
            raise route.RouteV2Error("model selector differs")
        treatment = action["treatment_projection"]
        packet = self._files.get("skill.packet")
        if treatment["state"] == "absent":
            if packet is not None:
                raise route.RouteV2Error("absent treatment was staged")
        elif packet is None or route._sha256_bytes(packet) != treatment["treatment_packet_sha256"]:
            raise route.RouteV2Error("treatment packet differs")
        staged = private_root / "staged-input"
        staged.mkdir()
        route._current_user_only(staged, True)
        for name, payload in self._files.items():
            target = staged / name
            target.write_bytes(payload)
            route._current_user_only(target, False)
            route._verify_current_user_only(target, False)
        observed = {path.name: path.read_bytes() for path in staged.iterdir() if path.is_file()}
        if observed != self._files:
            raise route.RouteV2Error("staged input content differs")
        codex_home = private_root / "codex-home"
        codex_home.mkdir()
        route._current_user_only(codex_home, True)
        auth = codex_home / "auth.json"
        auth.write_bytes(self._credential)
        route._current_user_only(auth, False)
        route._verify_current_user_only(codex_home, True)
        route._verify_current_user_only(auth, False)
        if [path.name for path in codex_home.iterdir()] != ["auth.json"]:
            raise route.RouteV2Error("synthetic auth inventory differs")
        self._prepared = True
        return route._json_bytes(
            {
                "action_sha256": route._sha256_bytes(action_payload),
                "arm_id": action["arm_id"],
                "contract_manifest_sha256": self._contract,
                "credential_acl": "PASS",
                "model_id": action["model_id"],
                "model_selector_match": "PASS",
                "only_auth_inventory": "PASS",
                "pair_action_sha256": action["pair_action_sha256"],
                "pair_id": action["pair_id"],
                "run_id": action["run_id"],
                "schema": route.INPUT_ATTESTATION_SCHEMA,
                "staged_acl": "PASS",
                "staged_content_match": "PASS",
                "staged_input_manifest_sha256": expected,
                "staged_inventory_match": "PASS",
                "treatment_packet_sha256": treatment["treatment_packet_sha256"],
                "treatment_state": treatment["state"],
                "validator_sha256": _implementation_sha256(),
            }
        )

    def _invoke(self) -> route.SyntheticResult:
        if not self._prepared or self.calls:
            raise route.RouteV2Error("A/B runner invocation order is invalid")
        self.calls += 1
        return self._result


_TRUSTED_AB_PREPARE = SyntheticABArmRunner._prepare
_TRUSTED_AB_INVOKE = SyntheticABArmRunner._invoke


def _event(
    *, pair_id: str, pair_action_sha256: str, ordinal: int,
    event_type: str, arm_id: str, run_id: str, terminal_class: str,
    previous_event_sha256: str,
) -> dict[str, object]:
    return {
        "arm_id": arm_id,
        "event_type": event_type,
        "ordinal": ordinal,
        "pair_action_sha256": pair_action_sha256,
        "pair_id": pair_id,
        "previous_event_sha256": previous_event_sha256,
        "run_id": run_id,
        "schema": LEDGER_SCHEMA,
        "terminal_class": terminal_class,
    }


def _publish_event(ledger: Path, value: dict[str, object]) -> str:
    payload = route._json_bytes(value)
    route._validate_public_payload(payload)
    route._publish_create_once(
        ledger / f"{value['ordinal']:04d}-{value['event_type']}.json", payload
    )
    return route._sha256_bytes(payload)


def orchestrate_pair(
    output_root: Path,
    *,
    contract_manifest: bytes,
    expected_manifest_sha256: str,
    prompt: bytes,
    output_schema: dict[str, Any],
    expected_workspace: Mapping[str, bytes],
    credential_fixture: bytes,
    arm_runners: Mapping[str, SyntheticABArmRunner],
) -> PairResult:
    manifest = _validate_manifest(contract_manifest, expected_manifest_sha256)
    if set(arm_runners) != {"A", "B"} or not isinstance(credential_fixture, bytes):
        raise route.RouteV2Error("pair runner set is invalid")
    if any(
        type(arm_runners[arm_id]) is not SyntheticABArmRunner
        or not arm_runners[arm_id].credential_matches(credential_fixture)
        for arm_id in ("A", "B")
    ):
        raise route.RouteV2Error("pair credential fixtures differ")
    if (
        route._sha256_bytes(prompt) != manifest["action_inputs"]["prompt_sha256"]
        or _canonical_digest(route._validate_schema_definition(output_schema))
        != manifest["action_inputs"]["output_schema_sha256"]
        or _canonical_digest(staged_manifest(expected_workspace))
        != manifest["action_inputs"]["expected_workspace_sha256"]
    ):
        raise route.RouteV2Error("pair invocation inputs differ from manifest")
    model_id = manifest["model_build_identity"]["model_id"]
    if any(
        not arm_runners[arm["arm_id"]].admission_matches(arm, model_id)
        for arm in manifest["ordered_arms"]
    ):
        raise route.RouteV2Error("pair staged admission differs from manifest")
    output_root = output_root.resolve()
    if output_root.exists():
        raise route.RouteV2Error("pair output collision")
    output_root.mkdir(parents=True)
    private = output_root.parent / f".{manifest['pair_id']}.private"
    if private.exists():
        raise route.RouteV2Error("pair private collision")
    private.mkdir()
    route._current_user_only(private, True)
    try:
        auth_roots: dict[str, Path] = {}
        for arm_id in ("A", "B"):
            arm_home = private / arm_id
            arm_home.mkdir()
            route._current_user_only(arm_home, True)
            auth = arm_home / "auth.json"
            auth.write_bytes(credential_fixture)
            route._current_user_only(auth, False)
            auth_roots[arm_id] = arm_home
        observation = _observe_pair_preflight(auth_roots["A"], auth_roots["B"])
        preflight = _pair_preflight(manifest, observation)
        preflight_payload = route._json_bytes(preflight)
        route._validate_public_payload(preflight_payload)
        route._publish_create_once(output_root / "pair-preflight-attestation.json", preflight_payload)
        preflight_pin = _pin_bytes(route._sha256_bytes(preflight_payload))
        route._publish_create_once(output_root / "pair-preflight-attestation.sha256", preflight_pin)
        action = _pair_action(
            manifest,
            route._sha256_bytes(preflight_payload),
            route._sha256_bytes(preflight_pin),
        )
        action_payload = route._json_bytes(action)
        route._validate_public_payload(action_payload)
        route._publish_create_once(output_root / "pair-action.json", action_payload)
        action_digest = route._sha256_bytes(action_payload)
        route._publish_create_once(output_root / "pair-action.sha256", _pin_bytes(action_digest))
    finally:
        shutil.rmtree(private, ignore_errors=False)
    if private.exists():
        raise route.RouteV2Error("pair private residue remains")

    ledger = output_root / "attempt-ledger"
    ledger.mkdir()
    previous = _publish_event(
        ledger,
        _event(
            pair_id=manifest["pair_id"], pair_action_sha256=action_digest,
            ordinal=0, event_type="pair_action_pinned", arm_id="not_applicable",
            run_id="not_applicable", terminal_class="not_applicable",
            previous_event_sha256="absent",
        ),
    )
    arm_runtime = output_root / "arm-runtime"
    arm_results: dict[str, route.RouteResult] = {}
    for index, arm in enumerate(manifest["ordered_arms"]):
        arm_id = arm["arm_id"]
        run_id = arm["run_id"]
        start_ordinal = 1 if index == 0 else 3
        terminal_ordinal = start_ordinal + 1
        previous = _publish_event(
            ledger,
            _event(
                pair_id=manifest["pair_id"], pair_action_sha256=action_digest,
                ordinal=start_ordinal,
                event_type="first_arm_started" if index == 0 else "second_arm_started",
                arm_id=arm_id, run_id=run_id, terminal_class="not_applicable",
                previous_event_sha256=previous,
            ),
        )
        admission = {
            "arm_id": arm_id,
            "model_id": manifest["model_build_identity"]["model_id"],
            "pair_action_sha256": action_digest,
            "pair_id": manifest["pair_id"],
            "staged_input_manifest_sha256": arm["staged_input_manifest_sha256"],
            "treatment_projection": arm["treatment_projection"],
        }
        try:
            result = route.orchestrate(
                arm_runtime / "public" / run_id,
                locator_root=arm_runtime / "locators",
                external_root=arm_runtime / "external",
                run_id=run_id,
                authorization=route.AUTHORIZATION,
                prompt=prompt,
                output_schema=output_schema,
                expected_workspace=expected_workspace,
                runner=arm_runners[arm_id].capability(),
                ab_admission=admission,
                _trusted_route_root=arm_runtime,
            )
        except BaseException:
            _publish_event(
                ledger,
                _event(
                    pair_id=manifest["pair_id"],
                    pair_action_sha256=action_digest,
                    ordinal=terminal_ordinal,
                    event_type=(
                        "first_arm_terminal"
                        if index == 0
                        else "second_arm_terminal"
                    ),
                    arm_id=arm_id,
                    run_id=run_id,
                    terminal_class="RAISED",
                    previous_event_sha256=previous,
                ),
            )
            raise
        arm_results[arm_id] = result
        previous = _publish_event(
            ledger,
            _event(
                pair_id=manifest["pair_id"], pair_action_sha256=action_digest,
                ordinal=terminal_ordinal,
                event_type="first_arm_terminal" if index == 0 else "second_arm_terminal",
                arm_id=arm_id, run_id=run_id, terminal_class=result.decision,
                previous_event_sha256=previous,
            ),
        )
        final_path = arm_runtime / "public" / run_id / "final.json"
        route._publish_create_once(
            output_root / f"arm-{arm_id.lower()}-final.sha256",
            _pin_bytes(route._sha256_file(final_path)),
        )
    previous = _publish_event(
        ledger,
        _event(
            pair_id=manifest["pair_id"], pair_action_sha256=action_digest,
            ordinal=5, event_type="pair_closed", arm_id="not_applicable",
            run_id="not_applicable", terminal_class="not_applicable",
            previous_event_sha256=previous,
        ),
    )
    route._publish_create_once(output_root / "attempt-ledger.sha256", _pin_bytes(previous))
    pins = {
        "arm_a_final_sha256": _read_pin(output_root / "arm-a-final.sha256"),
        "arm_b_final_sha256": _read_pin(output_root / "arm-b-final.sha256"),
        "attempt_ledger_final_sha256": _read_pin(
            output_root / "attempt-ledger.sha256"
        ),
        "pair_action_sha256": action_digest,
        "pair_preflight_attestation_sha256": route._sha256_bytes(
            preflight_payload
        ),
    }
    receipt = _rebuild_receipt(
        output_root,
        manifest=manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_pins=pins,
    )
    receipt_path = output_root / "pair-final.json"
    route._validate_public_payload(route._json_bytes(receipt))
    route._publish_create_once(receipt_path, route._json_bytes(receipt))
    return PairResult(output_root, receipt_path, str(receipt["decision"]), pins)


def _ledger(output_root: Path, action: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    ledger = output_root / "attempt-ledger"
    expected_names = {
        f"{ordinal:04d}-{event_type}.json"
        for ordinal, (event_type, _) in enumerate(EVENTS)
    }
    entries = list(ledger.iterdir()) if ledger.is_dir() else []
    if (
        {entry.name for entry in entries} != expected_names
        or any(entry.is_symlink() or not entry.is_file() for entry in entries)
    ):
        raise route.RouteV2Error("attempt ledger cardinality is invalid")
    paths = sorted(entries)
    events = [route._load_object(path) for path in paths]
    previous = "absent"
    arms = manifest["ordered_arms"]
    expected_rows = (
        ("pair_action_pinned", "not_applicable", "not_applicable"),
        ("first_arm_started", arms[0]["arm_id"], arms[0]["run_id"]),
        ("first_arm_terminal", arms[0]["arm_id"], arms[0]["run_id"]),
        ("second_arm_started", arms[1]["arm_id"], arms[1]["run_id"]),
        ("second_arm_terminal", arms[1]["arm_id"], arms[1]["run_id"]),
        ("pair_closed", "not_applicable", "not_applicable"),
    )
    for ordinal, (event, expected) in enumerate(zip(events, expected_rows, strict=True)):
        event_type, arm_id, run_id = expected
        if set(event) != {
            "arm_id", "event_type", "ordinal", "pair_action_sha256", "pair_id",
            "previous_event_sha256", "run_id", "schema", "terminal_class",
        } or event.get("schema") != LEDGER_SCHEMA or event.get("ordinal") != ordinal or event.get("event_type") != event_type or event.get("arm_id") != arm_id or event.get("run_id") != run_id or event.get("pair_id") != manifest["pair_id"] or event.get("pair_action_sha256") != _canonical_digest(action) or event.get("previous_event_sha256") != previous:
            raise route.RouteV2Error("attempt ledger is invalid")
        expected_terminal = event_type.endswith("_terminal")
        if (event.get("terminal_class") in {"SUCCESS", "FAILURE"}) is not expected_terminal:
            raise route.RouteV2Error("attempt ledger terminal is invalid")
        previous = _canonical_digest(event)
    if _read_pin(output_root / "attempt-ledger.sha256") != previous:
        raise route.RouteV2Error("attempt ledger pin differs")
    return events


def _assert_closed_pair_tree(
    output_root: Path, manifest: Mapping[str, Any]
) -> None:
    arm_files = {
        "action.json",
        "attestation.json",
        "final.json",
        "input-attestation.json",
        "packet.json",
        "preflight.json",
        "seal.json",
    }
    expected_files = {
        "arm-a-final.sha256",
        "arm-b-final.sha256",
        "attempt-ledger.sha256",
        "pair-action.json",
        "pair-action.sha256",
        "pair-final.json",
        "pair-preflight-attestation.json",
        "pair-preflight-attestation.sha256",
    }
    expected_files |= {
        f"attempt-ledger/{ordinal:04d}-{event_type}.json"
        for ordinal, (event_type, _) in enumerate(EVENTS)
    }
    run_ids = [arm["run_id"] for arm in manifest["ordered_arms"]]
    for run_id in run_ids:
        expected_files |= {
            f"arm-runtime/public/{run_id}/{name}" for name in arm_files
        }
    expected_dirs = {
        "arm-runtime",
        "arm-runtime/external",
        "arm-runtime/locators",
        "arm-runtime/private",
        "arm-runtime/public",
        "attempt-ledger",
    } | {f"arm-runtime/public/{run_id}" for run_id in run_ids}
    observed_files: set[str] = set()
    observed_dirs: set[str] = set()
    for current, directories, files in os.walk(output_root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            relative = path.relative_to(output_root).as_posix()
            attributes = getattr(
                path.stat(follow_symlinks=False), "st_file_attributes", 0
            )
            if path.is_symlink() or attributes & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
            ):
                raise route.RouteV2Error("pair artifact tree contains a link")
            observed_dirs.add(relative)
        for name in files:
            path = current_path / name
            relative = path.relative_to(output_root).as_posix()
            attributes = getattr(
                path.stat(follow_symlinks=False), "st_file_attributes", 0
            )
            if path.is_symlink() or attributes & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
            ):
                raise route.RouteV2Error("pair artifact tree contains a link")
            observed_files.add(relative)
    if observed_files != expected_files or observed_dirs != expected_dirs:
        raise route.RouteV2Error("pair artifact tree is not closed")


def _rebuild_receipt(
    output_root: Path,
    *,
    manifest: Mapping[str, Any],
    expected_manifest_sha256: str,
    expected_pins: Mapping[str, str],
) -> dict[str, object]:
    pins = _validate_expected_pins(expected_pins)
    preflight_path = output_root / "pair-preflight-attestation.json"
    preflight_pin_path = output_root / "pair-preflight-attestation.sha256"
    action_path = output_root / "pair-action.json"
    action_pin_path = output_root / "pair-action.sha256"
    preflight = route._load_object(preflight_path)
    if preflight != _expected_pair_preflight(manifest):
        raise route.RouteV2Error("pair preflight differs from reconstruction")
    if (
        _read_pin(preflight_pin_path) != route._sha256_file(preflight_path)
        or route._sha256_file(preflight_path)
        != pins["pair_preflight_attestation_sha256"]
    ):
        raise route.RouteV2Error("pair preflight pin differs")
    action = route._load_object(action_path)
    expected_action = _pair_action(
        manifest,
        route._sha256_file(preflight_path),
        route._sha256_file(preflight_pin_path),
    )
    if (
        action != expected_action
        or _read_pin(action_pin_path) != route._sha256_file(action_path)
        or route._sha256_file(action_path) != pins["pair_action_sha256"]
    ):
        raise route.RouteV2Error("pair action differs from reconstruction")
    events = _ledger(output_root, action, manifest)
    if _read_pin(output_root / "attempt-ledger.sha256") != pins["attempt_ledger_final_sha256"]:
        raise route.RouteV2Error("attempt ledger differs from external pin")
    arm_runtime = output_root / "arm-runtime"
    arms: list[dict[str, str]] = []
    arm_success = True
    arm_decisions: dict[str, str] = {}
    normalized_actions: list[dict[str, object]] = []
    normalized_preflights: list[dict[str, object]] = []
    for arm in manifest["ordered_arms"]:
        arm_id = arm["arm_id"]
        run_id = arm["run_id"]
        final_pin_path = output_root / f"arm-{arm_id.lower()}-final.sha256"
        final_digest = _read_pin(final_pin_path)
        if final_digest != pins[f"arm_{arm_id.lower()}_final_sha256"]:
            raise route.RouteV2Error("arm final differs from external pin")
        verification = route.verify(
            arm_runtime / "public" / run_id,
            locator_root=arm_runtime / "locators",
            external_root=arm_runtime / "external",
            run_id=run_id,
            expected_action_sha256=route._sha256_file(arm_runtime / "public" / run_id / "action.json"),
            expected_final_sha256=final_digest,
            _trusted_route_root=arm_runtime,
        )
        arm_success = arm_success and verification["decision"] == "SUCCESS"
        arm_decisions[arm_id] = str(verification["decision"])
        arm_root = arm_runtime / "public" / run_id
        arm_action = route._load_object(arm_root / "action.json")
        input_attestation = route._load_object(arm_root / "input-attestation.json")
        arm_preflight = route._load_object(arm_root / "preflight.json")
        expected_arm_fields = {
            "arm_id": arm_id,
            "model_id": manifest["model_build_identity"]["model_id"],
            "pair_action_sha256": route._sha256_file(action_path),
            "pair_id": manifest["pair_id"],
            "staged_input_manifest_sha256": arm["staged_input_manifest_sha256"],
            "treatment_projection": arm["treatment_projection"],
        }
        if any(arm_action.get(key) != expected for key, expected in expected_arm_fields.items()):
            raise route.RouteV2Error("arm action differs from pair action")
        if (
            arm_action.get("prompt_sha256") != action["prompt_sha256"]
            or _canonical_digest({"artifacts": arm_action.get("expected_workspace")})
            != action["expected_workspace_sha256"]
            or _canonical_digest(arm_action.get("output_schema"))
            != action["output_schema_sha256"]
            or input_attestation.get("contract_manifest_sha256")
            != expected_manifest_sha256
            or input_attestation.get("validator_sha256")
            != manifest["implementations"]["pair_verifier_sha256"]
        ):
            raise route.RouteV2Error("arm evidence differs from manifest")
        arm_execution = arm_action.get("execution_identity")
        model_build = manifest["model_build_identity"]
        if not isinstance(arm_execution, Mapping) or any(
            arm_execution.get(key) != model_build[key]
            for key in (
                "cli_version",
                "command_contract_sha256",
                "executable_sha256",
                "runner_sha256",
            )
        ):
            raise route.RouteV2Error("arm execution identity differs from manifest")
        normalized_action = dict(arm_action)
        for key in (
            "arm_id", "pair_action_sha256", "pair_id", "preflight_sha256",
            "run_id", "staged_input_manifest_sha256", "treatment_projection",
        ):
            normalized_action.pop(key)
        normalized_actions.append(normalized_action)
        normalized_preflight = dict(arm_preflight)
        normalized_preflight.pop("run_id")
        normalized_preflights.append(normalized_preflight)
        arms.append(
            {
                "arm_id": arm_id,
                "final_pin_sha256": route._sha256_file(final_pin_path),
                "final_receipt_sha256": final_digest,
                "run_id": run_id,
                "treatment_packet_sha256": arm["treatment_projection"]["treatment_packet_sha256"],
                "treatment_state": arm["treatment_projection"]["state"],
            }
        )
    if normalized_actions[0] != normalized_actions[1] or normalized_preflights[0] != normalized_preflights[1]:
        raise route.RouteV2Error("cross-arm identity differs")
    terminal_events = [event for event in events if event["event_type"].endswith("_terminal")]
    if any(
        event["terminal_class"] != arm_decisions[event["arm_id"]]
        for event in terminal_events
    ):
        raise route.RouteV2Error("ledger terminal differs from arm final")
    checks = {
        "arm_verification": "PASS" if arm_success else "FAIL",
        "cleanup": "PASS" if not (output_root.parent / f".{manifest['pair_id']}.private").exists() else "FAIL",
        "credential_equality": "PASS",
        "cross_arm_equality": "PASS",
        "distinct_contexts": "PASS",
        "exactly_two_no_replacement": "PASS" if len(events) == 6 else "FAIL",
        "treatment_only_difference": "PASS",
    }
    decision = "SUCCESS" if all(value == "PASS" for value in checks.values()) else "NON_SUCCESS"
    return {
        "arms": arms,
        "attempt_ledger_final_sha256": route._sha256_file(output_root / "attempt-ledger.sha256"),
        "checks": checks,
        "claim_ceiling": "synthetic_non_counted_route_qualification_only",
        "contract_manifest_sha256": expected_manifest_sha256,
        "decision": decision,
        "model_build_identity": manifest["model_build_identity"],
        "pair_action_pin_sha256": route._sha256_file(action_pin_path),
        "pair_action_sha256": route._sha256_file(action_path),
        "pair_id": manifest["pair_id"],
        "pair_preflight_attestation_sha256": route._sha256_file(preflight_path),
        "pair_preflight_pin_sha256": route._sha256_file(preflight_pin_path),
        "schema": PAIR_RECEIPT_SCHEMA,
    }


def verify_pair(
    output_root: Path,
    *,
    contract_manifest: bytes,
    expected_manifest_sha256: str,
    expected_pins: Mapping[str, str],
) -> dict[str, object]:
    manifest = _validate_manifest(contract_manifest, expected_manifest_sha256)
    _assert_closed_pair_tree(output_root, manifest)
    rebuilt = _rebuild_receipt(
        output_root,
        manifest=manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_pins=expected_pins,
    )
    proposed = (output_root / "pair-final.json").read_bytes()
    if proposed != route._json_bytes(rebuilt):
        raise route.RouteV2Error("pair receipt differs from reconstruction")
    return {
        "claim": "synthetic_non_counted_route_qualification_only",
        "decision": rebuilt["decision"],
        "pair_id": manifest["pair_id"],
        "status": "PASS",
    }
