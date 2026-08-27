from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "amendment-manifest.json"
CONTRACT = ROOT / "reproducer-contract.json"
AMENDMENT = ROOT / "common-input-amendment.json"
VALIDATION = ROOT / "baseline-validation.json"
REPRODUCER = ROOT / "producer-visible-bulk-import-reproducer.test.ts"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def test_frozen_files_bind_every_file_except_manifest() -> None:
    manifest = _json(MANIFEST)
    frozen = manifest["frozen_files"]
    assert isinstance(frozen, list)

    actual = sorted(path.name for path in ROOT.iterdir() if path.is_file())
    declared = sorted(item["path"] for item in frozen)
    assert actual == sorted([*declared, MANIFEST.name])

    for item in frozen:
        path = ROOT / item["path"]
        raw = path.read_bytes()
        assert len(raw) == item["bytes"]
        assert _sha256(raw) == item["sha256"]


@pytest.mark.parametrize(
    "name",
    [
        "amendment-manifest.json",
        "baseline-validation.json",
        "common-input-amendment.json",
        "reproducer-contract.json",
    ],
)
def test_json_is_canonical_utf8_lf(name: str) -> None:
    raw = (ROOT / name).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    parsed = json.loads(raw)
    canonical = (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode()
    assert raw == canonical


def test_preregistration_amendment_is_additive_and_bounded() -> None:
    amendment = _json(AMENDMENT)
    assert amendment["schema"] == "c1-gate1-preregistration-common-input-amendment.v1"
    assert amendment["status"] == "COMMON_INPUT_REPRODUCER_FROZEN_NOT_EXECUTED"
    assert amendment["original_preregistration"] == {
        "freeze_commit": "7109f3c24f9e38df161e4fd93c729820a151f0eb",
        "manifest_path": "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/c1-20260825/preregistration-manifest.json",
        "git_blob_oid": "911382a0205aae9abc3081442ac173a1eada11da",
        "bytes": 9190,
        "sha256": "8515cea0b62a8df1bb806782913ca4543f6699f53743ded3edd5fab42b3d67b7",
        "immutable": True,
    }
    assert amendment["decision"]["applies_to_arms"] == ["A", "B"]
    assert amendment["decision"]["identical_bytes_and_command_required_across_arms"] is True
    assert all(amendment["preserved_decisions"].values())
    assert not any(amendment["authority"].values())


def test_baseline_source_bindings_are_exact_literals() -> None:
    contract = _json(CONTRACT)
    assert contract["baseline"] == {
        "commit": "15d5d51356b4808e5fb12782961a94d9985b2ae6",
        "tree": "a6946a0ba48f161f40e7ae7e3a4322bdef704e9a",
    }
    entrypoint = contract["product_entrypoint"]
    assert entrypoint == {
        "kind": "public_http_route_handler",
        "method": "POST",
        "repo_relative_path": "src/app/api/admin/import-books/route.ts",
        "git_blob_oid": "0c84326019374051992803957f7adfdeba5b9fd0",
        "bytes": 14187,
        "sha256": "0d54ee1ce2627cc8145075f67aac4ace83b5a9f306cf61c0be11585c14c5ec87",
    }
    for binding in [entrypoint, *contract["baseline_support_bindings"]]:
        assert HEX40.fullmatch(binding["git_blob_oid"])
        assert HEX64.fullmatch(binding["sha256"])
        assert binding["bytes"] > 0


def test_command_is_single_file_shell_free_and_network_free() -> None:
    command = _json(CONTRACT)["command"]
    assert command == {
        "cwd": "owned_disposable_baseline_root",
        "argv": [
            "node",
            "node_modules/vitest/vitest.mjs",
            "run",
            "src/__tests__/c1-gate1-black-box-reproducer.test.ts",
            "--config",
            "vitest.config.ts",
            "--reporter",
            "verbose",
        ],
        "shell": False,
        "network_allowed": False,
        "expected_exit_code": 0,
        "expected_test_file_count": 1,
        "stdout_prefix": "C1_REPRODUCER_OBSERVATION=",
    }
    assert "*" not in " ".join(command["argv"])
    assert "npx" not in command["argv"]


def test_only_reproducer_and_exact_command_are_producer_visible() -> None:
    contract = _json(CONTRACT)
    visibility = contract["producer_visibility"]
    assert visibility == {
        "visible": True,
        "shared_arms": ["A", "B"],
        "only_visible_files": ["producer-visible-bulk-import-reproducer.test.ts"],
        "visible_command_source": "command.argv",
        "scorer_surface_visible": False,
    }
    raw = REPRODUCER.read_bytes()
    assert contract["materialization"]["source_bytes"] == len(raw)
    assert contract["materialization"]["source_sha256"] == _sha256(raw)
    amendment = _json(AMENDMENT)["decision"]
    assert amendment["producer_visible_artifact_bytes"] == len(raw)
    assert amendment["producer_visible_artifact_sha256"] == _sha256(raw)


def test_reproducer_uses_public_route_and_has_no_correction_assertion() -> None:
    text = REPRODUCER.read_text(encoding="utf-8")
    assert "import { POST } from '@/app/api/admin/import-books/route'" in text
    assert "await POST(request)" in text
    assert "expect(response.status).toBe(200)" in text
    assert "expect(fixture.captured).toHaveLength(2)" in text
    assert "C1_REPRODUCER_OBSERVATION=" in text
    assert "toEqual(['catalog-existing', 'catalog-distinct'])" not in text
    assert "toStrictEqual(['catalog-existing', 'catalog-distinct'])" not in text


def test_producer_visible_bytes_do_not_name_forbidden_provenance() -> None:
    text = REPRODUCER.read_text(encoding="utf-8").lower()
    forbidden = (
        "bulk_" + "import_integrity",
        "hidden " + "scorer",
        "historical " + "fix",
        "candidate " + "diff",
        "a607" + "5643",
        "c:" + "\\users\\",
        "d:" + "\\",
        "/ho" + "me/",
    )
    assert not [token for token in forbidden if token in text]


def test_canonical_observation_digest_is_reproducible() -> None:
    line = (
        'C1_REPRODUCER_OBSERVATION={"input_ids":["input-existing","input-distinct"],'
        '"linked_catalog_ids":["catalog-existing","catalog-existing"],'
        '"schema":"c1-public-bulk-import-observation.v1"}\n'
    ).encode()
    observation = _json(CONTRACT)["observation"]
    validation = _json(VALIDATION)
    assert len(line) == observation["canonical_line_utf8_lf_bytes"] == 185
    assert _sha256(line) == observation["canonical_line_utf8_lf_sha256"]
    assert validation["canonical_observation_line_utf8_lf_sha256"] == _sha256(line)


def test_validation_receipt_is_aggregate_only_and_non_counted() -> None:
    validation = _json(VALIDATION)
    assert validation["status"] == "BASELINE_BEHAVIOR_OBSERVED"
    assert validation["exit_code"] == 0
    assert validation["passed_test_count"] == 1
    assert validation["failed_test_count"] == 0
    assert validation["scratch_cleanup_completed"] is True
    assert validation["private_consumer_bytes_retained"] is False
    assert validation["raw_process_output_retained"] is False
    assert validation["bulk_tree_inventory_retained"] is False
    assert validation["candidate_or_oracle_accessed"] is False
    assert validation["hosted_model_request_performed"] is False
    assert validation["claim_ceiling"] == "PINNED_BASELINE_BLACK_BOX_OBSERVATION_ONLY"


def test_authoring_boundary_forbids_execution_state() -> None:
    manifest = _json(MANIFEST)
    assert manifest["status"] == "COMMON_INPUT_REPRODUCER_FROZEN_NOT_EXECUTED"
    assert not any(manifest["authoring_boundary"].values())
    assert manifest["next_authority"] == (
        "independent review of this freeze before producer pre-run implementation"
    )
