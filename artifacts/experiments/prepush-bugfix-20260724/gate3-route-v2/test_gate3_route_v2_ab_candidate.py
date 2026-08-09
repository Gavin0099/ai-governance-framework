from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route
import gate3_route_v2_ab as pair
import gate3_route_v2_ab_candidate as candidate


def test_exact_candidate_reconstructs_and_validates() -> None:
    result = candidate.verify_candidate()
    assert result["status"] == "PASS"
    value = pair._validate_manifest(
        candidate.CONTRACT_PATH.read_bytes(), result["contract_manifest_sha256"]
    )
    assert value["pair_id"] == candidate.PAIR_ID
    assert value["model_build_identity"]["model_id"] == candidate.MODEL_ID
    assert [arm["run_id"] for arm in value["ordered_arms"]] == list(
        candidate.RUN_IDS
    )
    assert [arm["context_token"] for arm in value["ordered_arms"]] == list(
        candidate.CONTEXT_TOKENS
    )


def test_candidate_runtime_inputs_match_source_commit() -> None:
    for path in candidate.SOURCE_COMMIT_INPUTS:
        relative = path.relative_to(candidate.REPO_ROOT).as_posix()
        completed = subprocess.run(
            ["git", "show", f"{candidate.SOURCE_COMMIT}:{relative}"],
            cwd=candidate.REPO_ROOT,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0
        assert completed.stdout == path.read_bytes()


def test_coherent_source_and_artifact_rewrite_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path(route.__file__).resolve()
    rewritten = tmp_path / "gate3_route_v2.py"
    rewritten.write_bytes(original.read_bytes() + b"\n# coherent attacker rewrite\n")
    monkeypatch.setattr(
        candidate,
        "SOURCE_COMMIT_INPUTS",
        (rewritten, *candidate.SOURCE_COMMIT_INPUTS[1:]),
    )
    source_commit_bytes = candidate._source_commit_bytes
    monkeypatch.setattr(
        candidate,
        "_source_commit_bytes",
        lambda path: (
            original.read_bytes() if path == rewritten else source_commit_bytes(path)
        ),
    )
    monkeypatch.setattr(
        candidate,
        "build_contract_manifest",
        lambda: candidate.CONTRACT_PATH.read_bytes(),
    )
    monkeypatch.setattr(
        candidate,
        "build_candidate_set",
        lambda contract: candidate.CANDIDATE_PATH.read_bytes(),
    )
    with pytest.raises(route.RouteV2Error, match="source differs from source commit"):
        candidate.verify_candidate()


def test_preflight_mutation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = candidate.PREFLIGHT_PATH.read_bytes()
    value = json.loads(original)
    value["execution_identity"]["executable_sha256"] = "0" * 64
    mutated = tmp_path / "preflight.json"
    mutated.write_bytes(route._json_bytes(value))
    monkeypatch.setattr(candidate, "PREFLIGHT_PATH", mutated)
    with pytest.raises(route.RouteV2Error, match="preflight identity differs"):
        candidate.build_contract_manifest()


def test_candidate_contract_mutation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = candidate.CONTRACT_PATH.read_bytes()
    value = json.loads(original)
    value["pair_id"] = "coherently-rewritten-pair"
    rewritten = route._json_bytes(value)
    mutated = tmp_path / "contract.json"
    mutated.write_bytes(rewritten)
    monkeypatch.setattr(candidate, "CONTRACT_PATH", mutated)
    with pytest.raises(route.RouteV2Error, match="contract reconstruction differs"):
        candidate.verify_candidate()
