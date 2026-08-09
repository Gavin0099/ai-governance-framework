from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import gate3_route_v2 as route
import gate3_route_v2_ab as pair
import gate3_route_v2_ab_live as live
import gate3_route_v2_codex as codex


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
SOURCE_COMMIT = "f1e00ae6072e935e8e2ec632ded7660a6a6518fd"
PREFLIGHT_SHA256 = "95ad495e4021a8cf7a7c5524f2bcdeffb7951c4c67e06a9887254d21b5f3cda3"
PAIR_ID = "gate3-route-v2-ab-live-v2-20260809"
MODEL_ID = "gpt-5.2"
RUN_IDS = (
    "gate3-route-v2-ab-live-v2-20260809-arm-a",
    "gate3-route-v2-ab-live-v2-20260809-arm-b",
)
CONTEXT_TOKENS = ("ARM_A_CONTEXT", "ARM_B_CONTEXT")
PREFLIGHT_PATH = HERE / "gate3-route-v2-ab-preflight-f1e00ae6-20260810.json"
CONTRACT_PATH = HERE / "gate3-route-v2-ab-contract-manifest-candidate.json"
CANDIDATE_PATH = HERE / "gate3-route-v2-ab-candidate-set.json"
ATTRIBUTES_PATH = REPO_ROOT / ".gitattributes"
TREATMENT_PATH = REPO_ROOT / (
    "artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md"
)
CANDIDATE_SCHEMA = "gate3-route-v2-ab.candidate-set.v1"
BYTE_PRESERVATION_PATHS = (pair.DESIGN_PATH.resolve(), TREATMENT_PATH)
SOURCE_COMMIT_INPUTS = (
    Path(route.__file__).resolve(),
    Path(pair.__file__).resolve(),
    Path(live.__file__).resolve(),
    Path(codex.__file__).resolve(),
    *BYTE_PRESERVATION_PATHS,
)


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "path": _relative(path),
        "sha256": route._sha256_bytes(payload),
    }


def _source_commit_bytes(path: Path) -> bytes:
    relative = _relative(path)
    completed = subprocess.run(
        ["git", "show", f"{SOURCE_COMMIT}:{relative}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise route.RouteV2Error("candidate source commit is unreadable")
    return completed.stdout


def _verify_source_commit_inputs() -> None:
    for path in SOURCE_COMMIT_INPUTS:
        if path.read_bytes() != _source_commit_bytes(path):
            raise route.RouteV2Error("candidate source differs from source commit")


def _verify_byte_preservation_attributes() -> None:
    for path in BYTE_PRESERVATION_PATHS:
        relative = _relative(path)
        completed = subprocess.run(
            ["git", "check-attr", "-z", "text", "--", relative],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        expected = b"\0".join(
            (relative.encode("utf-8"), b"text", b"unset", b"")
        )
        if completed.returncode != 0 or completed.stdout != expected:
            raise route.RouteV2Error(
                "candidate reconstruction input is not byte-preserved"
            )


def _staged_inputs(treatment: bytes) -> dict[str, dict[str, bytes]]:
    digest = route._sha256_bytes(treatment)
    common = dict(codex.BASELINE_WORKSPACE)
    return {
        "A": {
            **common,
            "treatment-manifest.json": pair.treatment_manifest("absent", "absent"),
        },
        "B": {
            **common,
            "skill.packet": treatment,
            "treatment-manifest.json": pair.treatment_manifest("present", digest),
        },
    }


def build_contract_manifest() -> bytes:
    preflight = PREFLIGHT_PATH.read_bytes()
    if route._sha256_bytes(preflight) != PREFLIGHT_SHA256:
        raise route.RouteV2Error("candidate preflight identity differs")
    preflight_value = json.loads(preflight)
    _, identity = route._validate_preflight(
        preflight, preflight_value.get("run_id"), route.LIVE_AUTHORIZATION
    )
    if (
        identity.get("kind") != "codex_exec"
        or preflight_value.get("required_flags") != sorted(codex.AB_REQUIRED_FLAGS)
    ):
        raise route.RouteV2Error("candidate preflight profile is invalid")
    treatment = TREATMENT_PATH.read_bytes()
    staged = _staged_inputs(treatment)
    model_identity = {
        "cli_version": identity["cli_version"],
        "command_contract_sha256": identity["command_contract_sha256"],
        "executable_sha256": identity["executable_sha256"],
        "model_id": MODEL_ID,
        "runner_sha256": identity["runner_sha256"],
    }
    manifest = pair.build_contract_manifest(
        pair_id=PAIR_ID,
        model_id=MODEL_ID,
        run_ids=RUN_IDS,
        context_tokens=CONTEXT_TOKENS,
        prompt=codex.PROMPT,
        output_schema=codex.OUTPUT_SCHEMA,
        baseline_workspace=codex.BASELINE_WORKSPACE,
        expected_workspace=codex.EXPECTED_WORKSPACE,
        arm_a_files=staged["A"],
        arm_b_files=staged["B"],
        treatment_packet_sha256=route._sha256_bytes(treatment),
        pair_authorization=pair.LIVE_AUTHORIZATION,
        single_arm_authorization=route.LIVE_AUTHORIZATION,
        model_build_identity=model_identity,
        single_arm_runner_sha256=identity["runner_sha256"],
        live_adapter_sha256=live._implementation_sha256(),
    )
    pair._validate_manifest(manifest, route._sha256_bytes(manifest))
    return manifest


def build_candidate_set(contract_manifest: bytes) -> bytes:
    pair._validate_manifest(contract_manifest, route._sha256_bytes(contract_manifest))
    files = [
        ATTRIBUTES_PATH,
        PREFLIGHT_PATH,
        CONTRACT_PATH,
        TREATMENT_PATH,
        Path(route.__file__).resolve(),
        Path(pair.__file__).resolve(),
        Path(live.__file__).resolve(),
        Path(codex.__file__).resolve(),
        pair.DESIGN_PATH.resolve(),
        Path(__file__).resolve(),
    ]
    value = {
        "authorization": "pending_independent_review_and_owner_signature",
        "files": [_file_record(path) for path in files],
        "frozen_execution": {
            "context_tokens": list(CONTEXT_TOKENS),
            "model_id": MODEL_ID,
            "pair_id": PAIR_ID,
            "run_ids": list(RUN_IDS),
        },
        "not_claimed": [
            "independent approval",
            "owner signature",
            "canonical promotion",
            "live A/B authorization",
            "live A/B execution",
            "Gate 3 counted execution",
            "Skill effectiveness",
        ],
        "qualification_preflight_sha256": PREFLIGHT_SHA256,
        "schema": CANDIDATE_SCHEMA,
        "source_base_commit": SOURCE_COMMIT,
    }
    return route._json_bytes(value)


def verify_candidate() -> dict[str, str]:
    _verify_byte_preservation_attributes()
    _verify_source_commit_inputs()
    contract = CONTRACT_PATH.read_bytes()
    if contract != build_contract_manifest():
        raise route.RouteV2Error("candidate contract reconstruction differs")
    candidate = CANDIDATE_PATH.read_bytes()
    if candidate != build_candidate_set(contract):
        raise route.RouteV2Error("candidate set reconstruction differs")
    return {
        "candidate_manifest_sha256": route._sha256_bytes(candidate),
        "contract_manifest_sha256": route._sha256_bytes(contract),
        "status": "PASS",
    }
