from __future__ import annotations

import io
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route
import gate3_route_v2_ab as pair
import gate3_route_v2_ab_checkout as checkout


EVIDENCE_COMMIT = "53fc93f727124e7084dadaaee5d864f16c613252"
EVIDENCE_RELATIVE = Path(
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "evidence-live-once-7d035c1d/gate3-route-v2-ab-live-v2-20260809"
)
CONTRACT_PATH = HERE / "gate3-route-v2-ab-contract-manifest-candidate.json"


def _exact_git_tree(tmp_path: Path) -> Path:
    completed = subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            EVIDENCE_COMMIT,
            EVIDENCE_RELATIVE.as_posix(),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        archive.extractall(tmp_path, filter="data")
    return tmp_path / EVIDENCE_RELATIVE


def _expected_pins(output_root: Path) -> dict[str, str]:
    return {
        "arm_a_final_sha256": (output_root / "arm-a-final.sha256").read_text().strip(),
        "arm_b_final_sha256": (output_root / "arm-b-final.sha256").read_text().strip(),
        "attempt_ledger_final_sha256": (
            output_root / "attempt-ledger.sha256"
        ).read_text().strip(),
        "pair_action_sha256": route._sha256_file(output_root / "pair-action.json"),
        "pair_preflight_attestation_sha256": route._sha256_file(
            output_root / "pair-preflight-attestation.json"
        ),
    }


def test_exact_git_tree_materializes_and_reconstructs_non_success(
    tmp_path: Path,
) -> None:
    source = _exact_git_tree(tmp_path / "checkout")
    assert all(not (source / relative).exists() for relative in checkout.GIT_OMITTED_EMPTY_DIRS)
    contract = CONTRACT_PATH.read_bytes()

    report = checkout.verify_git_pair_tree(
        source,
        tmp_path / "materialized",
        contract_manifest=contract,
        expected_manifest_sha256=route._sha256_bytes(contract),
        expected_pins=_expected_pins(source),
    )

    assert report == {
        "claim": "live_non_counted_route_qualification_only",
        "decision": "NON_SUCCESS",
        "pair_id": "gate3-route-v2-ab-live-v2-20260809",
        "status": "PASS",
    }


@pytest.mark.parametrize("relative", checkout.GIT_OMITTED_EMPTY_DIRS)
def test_source_runtime_directory_fails_before_copy(
    tmp_path: Path, relative: Path
) -> None:
    source = _exact_git_tree(tmp_path / "checkout")
    (source / relative).mkdir(parents=True)
    destination = tmp_path / "materialized"

    with pytest.raises(
        route.RouteV2Error, match="Git pair source contains runtime-only directory"
    ):
        checkout.materialize_git_pair_tree(source, destination)

    assert not destination.exists()


@pytest.mark.parametrize("relative", checkout.GIT_OMITTED_EMPTY_DIRS)
def test_materialized_runtime_residue_still_fails_closed(
    tmp_path: Path, relative: Path
) -> None:
    source = _exact_git_tree(tmp_path / "checkout")
    materialized = checkout.materialize_git_pair_tree(
        source, tmp_path / "materialized"
    )
    (materialized / relative / "residue.bin").write_bytes(b"residue")
    contract = CONTRACT_PATH.read_bytes()

    with pytest.raises(route.RouteV2Error, match="pair artifact tree is not closed"):
        pair.verify_pair(
            materialized,
            contract_manifest=contract,
            expected_manifest_sha256=route._sha256_bytes(contract),
            expected_pins=_expected_pins(source),
        )
