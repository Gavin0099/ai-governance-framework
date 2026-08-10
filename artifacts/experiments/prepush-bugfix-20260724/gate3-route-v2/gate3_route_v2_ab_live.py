from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import gate3_route_v2 as route
import gate3_route_v2_ab as pair
import gate3_route_v2_codex as codex


AUTHORIZATION = pair.LIVE_AUTHORIZATION
PREFLIGHT_AUTHORIZATION = "gate3_route_v2_ab_zero_session_preflight_only"
PREFLIGHT_RECEIPT_SCHEMA = "gate3-route-v2-ab.zero-session-preflight.v1"
OWNER_PIN_SCHEMA = "gate3-route-v2-ab.owner-manifest-pin.v1"
OWNER_PIN_PATH = Path(__file__).with_name("gate3-route-v2-ab-owner-pin.json")
_OWNER_PIN_TOKEN = object()


class OwnerManifestPin:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("OwnerManifestPin cannot be subclassed")

    def __init__(self, manifest_sha256: str, *, _token: object) -> None:
        if _token is not _OWNER_PIN_TOKEN:
            raise route.RouteV2Error("owner manifest pin is invalid")
        if route.SHA256_RE.fullmatch(manifest_sha256) is None:
            raise route.RouteV2Error("owner manifest pin is invalid")
        self.manifest_sha256 = manifest_sha256


def _lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_reparse_stat(value: os.stat_result) -> bool:
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _reject_reparse_chain(path: Path, label: str, *, require_exists: bool) -> Path:
    lexical = _lexical_path(path)
    cursor = lexical
    while True:
        if os.path.lexists(cursor):
            try:
                value = os.lstat(cursor)
            except OSError as exc:
                raise route.RouteV2Error(f"{label} is invalid") from exc
            if _is_reparse_stat(value):
                raise route.RouteV2Error(f"{label} contains a reparse point")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    if require_exists and not os.path.lexists(lexical):
        raise route.RouteV2Error(f"{label} is invalid")
    return lexical


def _checked_file(path: Path, label: str) -> Path:
    lexical = _reject_reparse_chain(path, label, require_exists=True)
    try:
        value = os.lstat(lexical)
    except OSError as exc:
        raise route.RouteV2Error(f"{label} is invalid") from exc
    if not stat.S_ISREG(value.st_mode):
        raise route.RouteV2Error(f"{label} is invalid")
    return lexical


def _owner_pin_from_bytes(payload: bytes) -> OwnerManifestPin:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise route.RouteV2Error("owner manifest pin is invalid") from exc
    if (
        not isinstance(value, dict)
        or payload != route._json_bytes(value)
        or set(value) != {"manifest_sha256", "schema", "status"}
        or value.get("schema") != OWNER_PIN_SCHEMA
        or value.get("status") != "SIGNED_AND_PROMOTED"
        or not isinstance(value.get("manifest_sha256"), str)
    ):
        raise route.RouteV2Error("owner manifest pin is invalid")
    return OwnerManifestPin(value["manifest_sha256"], _token=_OWNER_PIN_TOKEN)


def _owner_pin_loader(fixed_path: Path = OWNER_PIN_PATH) -> Callable[[], OwnerManifestPin]:
    def load() -> OwnerManifestPin:
        return _owner_pin_from_bytes(
            _checked_file(fixed_path, "owner manifest pin").read_bytes()
        )

    return load


_load_owner_pin = _owner_pin_loader()


def _implementation_sha256() -> str:
    return route._sha256_file(Path(__file__))


def _load_staged(root: Path) -> dict[str, bytes]:
    root = _reject_reparse_chain(root, "staged input root", require_exists=True)
    try:
        root_stat = os.lstat(root)
    except OSError as exc:
        raise route.RouteV2Error("staged input root is invalid") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise route.RouteV2Error("staged input root is invalid")
    files: dict[str, bytes] = {}
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as exc:
            raise route.RouteV2Error("staged input is unreadable") from exc
        for entry in entries:
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise route.RouteV2Error("staged input is unreadable") from exc
            if _is_reparse_stat(entry_stat):
                raise route.RouteV2Error("staged input contains a reparse point")
            path = Path(entry.path)
            if stat.S_ISDIR(entry_stat.st_mode):
                pending.append(path)
            elif stat.S_ISREG(entry_stat.st_mode):
                artifact_id = path.relative_to(root).as_posix()
                files[artifact_id] = path.read_bytes()
            else:
                raise route.RouteV2Error("staged input contains an unsupported entry")
    return route._validate_artifacts(files)


def build_live_contract_manifest(
    *,
    pair_id: str,
    model_id: str,
    run_ids: tuple[str, str],
    context_tokens: tuple[str, str],
    preflight: bytes,
    prompt: bytes,
    output_schema: dict[str, Any],
    baseline_workspace: Mapping[str, bytes],
    expected_workspace: Mapping[str, bytes],
    arm_a_files: Mapping[str, bytes],
    arm_b_files: Mapping[str, bytes],
    treatment_packet_sha256: str,
    execution_order: tuple[str, str] = ("A", "B"),
) -> bytes:
    _, identity = route._validate_preflight(
        preflight, run_ids[0], route.LIVE_AUTHORIZATION
    )
    if identity["kind"] != "codex_exec":
        raise route.RouteV2Error("live A/B execution identity is invalid")
    preflight_value = json.loads(preflight)
    if (
        preflight_value.get("required_flags") != sorted(codex.AB_REQUIRED_FLAGS)
        or identity["command_contract_sha256"] != codex._ab_command_contract_sha256()
    ):
        raise route.RouteV2Error("live A/B preflight profile is invalid")
    model_identity = {
        "cli_version": identity["cli_version"],
        "command_contract_sha256": identity["command_contract_sha256"],
        "executable_sha256": identity["executable_sha256"],
        "model_id": route._validate_public_token(model_id, "model identity"),
        "runner_sha256": identity["runner_sha256"],
    }
    manifest = pair.build_contract_manifest(
        pair_id=pair_id,
        model_id=model_id,
        run_ids=run_ids,
        context_tokens=context_tokens,
        prompt=prompt,
        output_schema=output_schema,
        baseline_workspace=baseline_workspace,
        expected_workspace=expected_workspace,
        arm_a_files=arm_a_files,
        arm_b_files=arm_b_files,
        treatment_packet_sha256=treatment_packet_sha256,
        execution_order=execution_order,
        pair_authorization=pair.LIVE_AUTHORIZATION,
        single_arm_authorization=route.LIVE_AUTHORIZATION,
        model_build_identity=model_identity,
        single_arm_runner_sha256=identity["runner_sha256"],
        live_adapter_sha256=_implementation_sha256(),
    )
    pair._validate_manifest(manifest, route._sha256_bytes(manifest))
    return manifest


def _verify_pre_session_inputs(
    output_root: Path,
    *,
    contract_manifest: bytes,
    owner_pin: OwnerManifestPin,
    executable_snapshots: Mapping[str, Path],
    measured_preflights: Mapping[str, bytes],
    staged_files: Mapping[str, Mapping[str, bytes]],
) -> tuple[dict[str, Any], str, dict[str, dict[str, str]]]:
    if type(owner_pin) is not OwnerManifestPin:
        raise route.RouteV2Error("owner manifest pin is invalid")
    expected_manifest_sha256 = owner_pin.manifest_sha256
    manifest = pair._validate_manifest(contract_manifest, expected_manifest_sha256)
    if manifest["authorization"] != pair.LIVE_AUTHORIZATION:
        raise route.RouteV2Error("live A/B manifest authorization is invalid")
    if set(executable_snapshots) != {"A", "B"} or set(measured_preflights) != {
        "A",
        "B",
    } or set(staged_files) != {"A", "B"}:
        raise route.RouteV2Error("live A/B arm inputs are invalid")
    output_root = _reject_reparse_chain(
        output_root, "pair output root", require_exists=False
    )
    if output_root.exists():
        raise route.RouteV2Error("pair output collision")
    if manifest["implementations"]["live_adapter_sha256"] != _implementation_sha256():
        raise route.RouteV2Error("live A/B adapter differs from signed manifest")
    expected_model = manifest["model_build_identity"]
    if (
        codex._ab_command_contract_sha256()
        != expected_model["command_contract_sha256"]
    ):
        raise route.RouteV2Error("live A/B interpreter differs from signed manifest")

    identities: dict[str, dict[str, str]] = {}
    arm_by_id = {arm["arm_id"]: arm for arm in manifest["ordered_arms"]}
    for arm_id in ("A", "B"):
        run_id = arm_by_id[arm_id]["run_id"]
        _, identity = route._validate_preflight(
            measured_preflights[arm_id], run_id, route.LIVE_AUTHORIZATION
        )
        snapshot = _checked_file(
            executable_snapshots[arm_id], f"arm {arm_id} executable snapshot"
        )
        if (
            not snapshot.is_file()
            or route._sha256_file(snapshot) != identity["executable_sha256"]
        ):
            raise route.RouteV2Error("live A/B executable snapshot differs")
        identities[arm_id] = identity
    if identities["A"] != identities["B"]:
        raise route.RouteV2Error("live A/B execution identities differ")
    if any(
        identities["A"][key] != expected_model[key]
        for key in (
            "cli_version",
            "command_contract_sha256",
            "executable_sha256",
            "runner_sha256",
        )
    ):
        raise route.RouteV2Error("live A/B execution identity differs from manifest")
    for arm_id in ("A", "B"):
        if pair._canonical_digest(pair.staged_manifest(staged_files[arm_id])) != arm_by_id[
            arm_id
        ]["staged_input_manifest_sha256"]:
            raise route.RouteV2Error("live A/B staged input differs from manifest")

    return manifest, expected_manifest_sha256, identities


def verify_live_pair_preflight(
    output_root: Path,
    *,
    contract_manifest: bytes,
    executable_snapshots: Mapping[str, Path],
    measured_preflights: Mapping[str, bytes],
    staged_files: Mapping[str, Mapping[str, bytes]],
) -> dict[str, object]:
    """Verify every live-pair input that precedes credential access or execution."""
    manifest, expected_manifest_sha256, identities = _verify_pre_session_inputs(
        output_root,
        contract_manifest=contract_manifest,
        owner_pin=_load_owner_pin(),
        executable_snapshots=executable_snapshots,
        measured_preflights=measured_preflights,
        staged_files=staged_files,
    )
    receipt: dict[str, object] = {
        "authorization": PREFLIGHT_AUTHORIZATION,
        "checks": {
            "cross_arm_identity": "PASS",
            "executable_snapshots": "PASS",
            "manifest_identity": "PASS",
            "output_collision": "PASS",
            "staged_inputs": "PASS",
        },
        "contract_manifest_sha256": expected_manifest_sha256,
        "execution_identity": identities["A"],
        "pair_id": manifest["pair_id"],
        "run_ids": [arm["run_id"] for arm in manifest["ordered_arms"]],
        "schema": PREFLIGHT_RECEIPT_SCHEMA,
    }
    route._validate_public_payload(route._json_bytes(receipt))
    return receipt


def _orchestrate_pinned_pair(
    output_root: Path,
    *,
    contract_manifest: bytes,
    owner_pin: OwnerManifestPin,
    executable_snapshots: Mapping[str, Path],
    measured_preflights: Mapping[str, bytes],
    staged_files: Mapping[str, Mapping[str, bytes]],
    auth_file: Path,
) -> pair.PairResult:
    manifest, expected_manifest_sha256, _ = _verify_pre_session_inputs(
        output_root,
        contract_manifest=contract_manifest,
        owner_pin=owner_pin,
        executable_snapshots=executable_snapshots,
        measured_preflights=measured_preflights,
        staged_files=staged_files,
    )
    arm_by_id = {arm["arm_id"]: arm for arm in manifest["ordered_arms"]}
    expected_model = manifest["model_build_identity"]

    auth_file = _checked_file(auth_file, "credential seed")
    route._verify_current_user_only(auth_file, False)
    auth_payload = auth_file.read_bytes()
    model_id = expected_model["model_id"]
    runners = {
        arm_id: codex.CodexABArmRunner(
            run_id=arm_by_id[arm_id]["run_id"],
            contract_manifest_sha256=expected_manifest_sha256,
            executable_snapshot=executable_snapshots[arm_id],
            auth_payload=auth_payload,
            measured_preflight=measured_preflights[arm_id],
            model_id=model_id,
            staged_files=staged_files[arm_id],
            expected_artifact_ids=tuple(codex.EXPECTED_WORKSPACE),
            prompt=codex.PROMPT,
            output_schema=codex.OUTPUT_SCHEMA,
        )
        for arm_id in ("A", "B")
    }
    return pair.orchestrate_pair(
        output_root,
        contract_manifest=contract_manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        prompt=codex.PROMPT,
        output_schema=codex.OUTPUT_SCHEMA,
        expected_workspace=codex.EXPECTED_WORKSPACE,
        credential_fixture=auth_payload,
        arm_runners=runners,
    )


def orchestrate_live_pair(
    output_root: Path,
    *,
    contract_manifest: bytes,
    executable_snapshots: Mapping[str, Path],
    measured_preflights: Mapping[str, bytes],
    staged_files: Mapping[str, Mapping[str, bytes]],
    auth_file: Path,
) -> pair.PairResult:
    """Run only against the independently pinned owner manifest identity."""
    return _orchestrate_pinned_pair(
        output_root,
        contract_manifest=contract_manifest,
        owner_pin=_load_owner_pin(),
        executable_snapshots=executable_snapshots,
        measured_preflights=measured_preflights,
        staged_files=staged_files,
        auth_file=auth_file,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one authorized non-counted Gate 3 route v2 A/B pair."
    )
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--auth-file", type=Path)
    for arm in ("a", "b"):
        parser.add_argument(f"--arm-{arm}-executable", type=Path, required=True)
        parser.add_argument(f"--arm-{arm}-preflight", type=Path, required=True)
        parser.add_argument(f"--arm-{arm}-staged", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.preflight_only:
        if args.authorization != PREFLIGHT_AUTHORIZATION:
            raise route.RouteV2Error("zero-session preflight authorization is invalid")
        if args.auth_file is not None:
            raise route.RouteV2Error("zero-session preflight must not receive credentials")
    elif args.authorization != AUTHORIZATION:
        raise route.RouteV2Error("live A/B authorization is invalid")
    elif args.auth_file is None:
        raise route.RouteV2Error("credential seed is required")
    manifest = _checked_file(args.manifest, "contract manifest").read_bytes()
    preflights = {
        "A": _checked_file(args.arm_a_preflight, "arm A preflight").read_bytes(),
        "B": _checked_file(args.arm_b_preflight, "arm B preflight").read_bytes(),
    }
    executable_snapshots = {
        "A": args.arm_a_executable,
        "B": args.arm_b_executable,
    }
    staged_files = {
        "A": _load_staged(args.arm_a_staged),
        "B": _load_staged(args.arm_b_staged),
    }
    if args.preflight_only:
        receipt = verify_live_pair_preflight(
            args.output_root,
            contract_manifest=manifest,
            executable_snapshots=executable_snapshots,
            measured_preflights=preflights,
            staged_files=staged_files,
        )
        sys.stdout.buffer.write(route._json_bytes(receipt))
        return 0
    result = orchestrate_live_pair(
        args.output_root,
        contract_manifest=manifest,
        executable_snapshots=executable_snapshots,
        measured_preflights=preflights,
        staged_files=staged_files,
        auth_file=args.auth_file,
    )
    print(json.dumps({"decision": result.decision, "verified": True}))
    return 0 if result.decision == "SUCCESS" else 2


def _entrypoint() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(_entrypoint())
