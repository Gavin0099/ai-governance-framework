from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
ANCHOR_REL = "artifacts/experiments/prepush-bugfix-20260724/gate1-execution/.gitattributes"
PARENT_REL = "artifacts/experiments/prepush-bugfix-20260724/gate1-execution"
MANIFEST = BASE / "capability-probe-02-manifest.json"
PROBE01_DIR = REPO / "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/c1-nonhosted-sandbox-capability-probe-implementation-freeze-20260828"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


READINESS = load_module("probe02_readiness_test", BASE / "execution_readiness.py")
DRIVER = load_module("probe02_driver_test", BASE / "capability_probe_02_driver.py")
BOOTSTRAP = load_module("probe02_bootstrap_test", BASE / "capability_probe_02_bootstrap.py")
ENGINE = load_module("probe01_engine_test", PROBE01_DIR / "capability_probe_executor.py")


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_manifest(root: Path) -> dict:
    parent = root / "gate1-execution"
    anchor = parent / ".anchor.json"
    parent.mkdir(parents=True)
    anchor.write_bytes(b'{"anchor":true}\n')
    return {
        "required_parent_roots": [
            {
                "repo_relative_path": "gate1-execution",
                "required_type": "directory",
                "anchor_repo_relative_path": "gate1-execution/.anchor.json",
                "anchor_git_blob_oid": "a" * 40,
                "anchor_bytes": anchor.stat().st_size,
                "anchor_sha256": sha256(anchor),
                "expected_child_names": [".anchor.json"],
                "resolved_containment_required": True,
                "reparse_or_symlink_forbidden": True,
                "write_capability_evidence_required": True,
            }
        ]
    }


def test_probe01_stop_is_bound_and_nonretryable() -> None:
    value = json.loads((BASE / "probe01-stop-binding.json").read_text(encoding="utf-8"))
    assert value["execution_commit"] == "9b6d0826c23fae4ccc5a0398cf6f24ddf2a145ac"
    assert value["execution_authorization_packet"]["sha256"] == "b6f4c0e008e12af56319d63d2a2b2292198ef3609d6cbfffb3320866c73f1543"
    assert value["independent_stop_review_session"] == "2026-08-28-64"
    assert value["invocation_count"] == 1
    assert value["output_claim_created"] is False
    assert value["terminal_created"] is False
    assert value["sandbox_helper_launched"] is False
    assert value["repair_allowed"] is False
    assert value["retry_allowed"] is False


def test_probe01_implementation_bytes_are_not_modified() -> None:
    expected = {
        "capability_probe_executor.py": "d20854c00ce60445194df3a594958c4e57a10db24698cd7045aa2272e4626de5",
        "capability_probe_bootstrap.py": "3cb6649324b7ecf34c5e4a361a9f2dd30f632ea99253c12e57953161c4ecf780",
    }
    for name, digest in expected.items():
        assert sha256(PROBE01_DIR / name) == digest


def test_tracked_anchor_materializes_parent() -> None:
    anchor = REPO.joinpath(*ANCHOR_REL.split("/"))
    assert anchor.is_file()
    assert anchor.parent.is_dir()
    tracked = subprocess.check_output(["git", "ls-files", "--error-unmatch", ANCHOR_REL], cwd=REPO, text=True).strip()
    assert tracked == ANCHOR_REL


def test_manifest_parent_contract_is_single_source() -> None:
    value = manifest()
    contracts = value["required_parent_roots"]
    assert len(contracts) == 1
    contract = contracts[0]
    assert contract["repo_relative_path"] == PARENT_REL
    assert contract["anchor_repo_relative_path"] == ANCHOR_REL
    assert contract["expected_child_names"] == [".gitattributes"]
    assert contract["write_capability_evidence_required"] is True


def test_parent_inspection_accepts_exact_synthetic_contract(tmp_path: Path) -> None:
    value = READINESS.inspect_parent(tmp_path, synthetic_manifest(tmp_path))
    assert value["projection"]["children"] == [".anchor.json"]
    assert len(value["projection_sha256"]) == 64


def test_missing_parent_fails_before_any_repair(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    parent = tmp_path / "gate1-execution"
    for child in parent.iterdir():
        child.unlink()
    parent.rmdir()
    with pytest.raises(READINESS.ReadinessError, match="unavailable or indirect"):
        READINESS.inspect_parent(tmp_path, value)
    assert not parent.exists()


def test_parent_file_is_rejected(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    parent = tmp_path / "gate1-execution"
    for child in parent.iterdir():
        child.unlink()
    parent.rmdir()
    parent.write_bytes(b"not-directory")
    with pytest.raises(READINESS.ReadinessError, match="unavailable or indirect"):
        READINESS.inspect_parent(tmp_path, value)


def test_reparse_or_symlink_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    parent = tmp_path / "gate1-execution"
    monkeypatch.setattr(READINESS, "is_reparse_or_symlink", lambda path: path == parent)
    with pytest.raises(READINESS.ReadinessError, match="unavailable or indirect"):
        READINESS.inspect_parent(tmp_path, value)


def test_unexpected_child_is_rejected(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    (tmp_path / "gate1-execution" / "unexpected").write_bytes(b"x")
    with pytest.raises(READINESS.ReadinessError, match="unexpected children"):
        READINESS.inspect_parent(tmp_path, value)


def test_readiness_sentinel_is_exact_and_fully_cleaned(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    receipt = READINESS.run_readiness_probe(
        repo=tmp_path,
        commit="1" * 40,
        manifest=value,
        identity={"sid_sha256": "2" * 64, "account_class": "fixture"},
    )
    assert receipt["status"] == "PARENT_READINESS_PASSED"
    assert receipt["sentinel_fsync_completed"] is True
    assert receipt["sentinel_readback_exact"] is True
    assert receipt["cleanup_complete"] is True
    assert receipt["formal_attempt_claim_created"] is False
    assert sorted(item.name for item in (tmp_path / "gate1-execution").iterdir()) == [".anchor.json"]


def test_readiness_cleanup_failure_never_emits_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    real_unlink = Path.unlink

    def fail_sentinel(path: Path, *args: object, **kwargs: object) -> None:
        if path.name == ".c1-probe02-parent-readiness-sentinel":
            raise OSError("forced cleanup failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_sentinel)
    with pytest.raises(OSError, match="forced cleanup failure"):
        READINESS.run_readiness_probe(
            repo=tmp_path,
            commit="1" * 40,
            manifest=value,
            identity={"sid_sha256": "2" * 64, "account_class": "fixture"},
        )


def test_reviewed_readiness_requires_exact_digest_identity_and_live_projection(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    identity = {"sid_sha256": "3" * 64, "account_class": "fixture"}
    receipt = READINESS.run_readiness_probe(repo=tmp_path, commit="4" * 40, manifest=value, identity=identity)
    receipt_payload = READINESS.canonical_json(receipt)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(receipt_payload)
    review = {
        "schema": READINESS.REVIEW_SCHEMA,
        "review_verdict": "APPROVED",
        "review_session": "fixture-review",
        "reviewed_receipt_sha256": READINESS.sha256(receipt_payload),
    }
    review_payload = READINESS.canonical_json(review)
    review_path = tmp_path / "review.json"
    review_path.write_bytes(review_payload)
    value["readiness_evidence"] = {
        "receipt_path": str(receipt_path),
        "review_packet_path": str(review_path),
        "receipt_max_bytes": 8192,
        "review_packet_max_bytes": 4096,
    }
    accepted = READINESS.validate_reviewed_readiness(
        repo=tmp_path,
        commit="4" * 40,
        manifest=value,
        owner_authorized_review_sha256=READINESS.sha256(review_payload),
        identity=identity,
    )
    assert accepted["status"] == "PARENT_READINESS_PASSED"
    with pytest.raises(READINESS.ReadinessError, match="digest mismatch"):
        READINESS.validate_reviewed_readiness(
            repo=tmp_path,
            commit="4" * 40,
            manifest=value,
            owner_authorized_review_sha256="0" * 64,
            identity=identity,
        )


def test_reviewed_readiness_rejects_identity_drift(tmp_path: Path) -> None:
    value = synthetic_manifest(tmp_path)
    identity = {"sid_sha256": "5" * 64, "account_class": "fixture"}
    receipt = READINESS.run_readiness_probe(repo=tmp_path, commit="6" * 40, manifest=value, identity=identity)
    receipt_payload = READINESS.canonical_json(receipt)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(receipt_payload)
    review_payload = READINESS.canonical_json({
        "schema": READINESS.REVIEW_SCHEMA,
        "review_verdict": "APPROVED",
        "review_session": "fixture-review",
        "reviewed_receipt_sha256": READINESS.sha256(receipt_payload),
    })
    review_path = tmp_path / "review.json"
    review_path.write_bytes(review_payload)
    value["readiness_evidence"] = {
        "receipt_path": str(receipt_path),
        "review_packet_path": str(review_path),
        "receipt_max_bytes": 8192,
        "review_packet_max_bytes": 4096,
    }
    with pytest.raises(READINESS.ReadinessError, match="does not match"):
        READINESS.validate_reviewed_readiness(
            repo=tmp_path,
            commit="6" * 40,
            manifest=value,
            owner_authorized_review_sha256=READINESS.sha256(review_payload),
            identity={"sid_sha256": "7" * 64, "account_class": "other"},
        )


def test_convergence_policy_reaches_surface_only_with_all_evidence() -> None:
    policy = json.loads((BASE / "execution-convergence-policy.json").read_text(encoding="utf-8"))
    evidence = {field: True for field in policy["probe_02_intended_surface_requires"]}
    evidence["infrastructure_failure_category"] = None
    assert READINESS.evaluate_convergence(policy, READINESS.ATTEMPT_ID, evidence) == "REACHED_INTENDED_SURFACE"
    evidence["absolute_python_control_attempted"] = False
    assert READINESS.evaluate_convergence(policy, READINESS.ATTEMPT_ID, evidence) == "STOP_BEFORE_FURTHER_FORMAL_ATTEMPT"


def test_new_unmodeled_category_triggers_stop() -> None:
    policy = json.loads((BASE / "execution-convergence-policy.json").read_text(encoding="utf-8"))
    evidence = {field: False for field in policy["probe_02_intended_surface_requires"]}
    evidence["infrastructure_failure_category"] = "brand_new_prerequisite"
    assert READINESS.evaluate_convergence(policy, READINESS.ATTEMPT_ID, evidence) == "STOP_BEFORE_FURTHER_FORMAL_ATTEMPT"
    effects = policy["stop_effects"]
    assert effects["probe_03_authorized"] is False
    assert effects["qualification_04_authorized"] is False


def test_modeled_failure_is_not_mislabelled_as_new() -> None:
    policy = json.loads((BASE / "execution-convergence-policy.json").read_text(encoding="utf-8"))
    evidence = {field: False for field in policy["qualification_03_intended_surface_requires"]}
    evidence["infrastructure_failure_category"] = "hosted_transport"
    assert READINESS.evaluate_convergence(policy, "C1-sandboxed-runner-qualification-03", evidence) == "MODELED_INFRASTRUCTURE_FAILURE"


def test_bootstrap_and_driver_direct_file_execution_are_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", [str(BASE / "capability_probe_02_bootstrap.py")])
    with pytest.raises(BOOTSTRAP.BootstrapError, match="streamed"):
        BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit="1" * 40, owner_authorized_readiness_review_sha256="2" * 64)
    monkeypatch.setattr(sys, "argv", [str(BASE / "capability_probe_02_driver.py")])
    with pytest.raises(DRIVER.DriverError, match="streamed"):
        DRIVER.execute(repo_root=tmp_path, owner_authorized_freeze_commit="1" * 40, owner_authorized_readiness_review_sha256="2" * 64)


def test_preclaim_missing_parent_creates_no_claim_or_terminal(tmp_path: Path) -> None:
    output = tmp_path / "missing-parent" / "attempt"
    with pytest.raises(ENGINE.ProbeError, match="evidence root unavailable"):
        ENGINE._claim_attempt(output)
    assert not output.exists()
    assert not (output / "terminal.json").exists()


def test_postclaim_publication_is_unique(tmp_path: Path) -> None:
    output = tmp_path / "attempt"
    output.mkdir()
    payload = b'{"status":"CAPABILITY_PROBE_AMBIGUOUS"}\n'
    assert ENGINE._publish_terminal(output, payload)["status"] == "CAPABILITY_PROBE_AMBIGUOUS"
    with pytest.raises(ENGINE.ProbeError, match="already exists"):
        ENGINE._publish_terminal(output, payload)
    assert [item.name for item in output.iterdir()] == ["terminal.json"]


def test_concurrent_claim_has_exactly_one_owner_and_loser_has_no_side_effect(tmp_path: Path) -> None:
    output = tmp_path / "attempt"
    barrier = threading.Barrier(2)

    def claim() -> bool:
        barrier.wait()
        try:
            ENGINE._claim_attempt(output)
            return True
        except ENGINE.ProbeError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert results.count(True) == 1
    assert results.count(False) == 1
    assert output.is_dir()
    assert list(output.iterdir()) == []


def test_parser_exposes_only_bound_readiness_digest() -> None:
    expected = {"help", "repo_root", "owner_authorized_freeze_commit", "owner_authorized_readiness_review_sha256"}
    assert {action.dest for action in DRIVER._parser()._actions} == expected
    assert {action.dest for action in BOOTSTRAP._parser()._actions} == expected


def test_binding_and_readiness_precede_engine_execution() -> None:
    source = (BASE / "capability_probe_02_driver.py").read_text(encoding="utf-8")
    body = source[source.index("def execute(") :]
    ordered = [
        "_manifest(repo, commit)",
        "_verify_frozen(repo, commit, manifest)",
        "_verify_sources(repo, manifest)",
        "verify_anchor_git_binding(repo, commit, manifest)",
        "validate_reviewed_readiness(",
        "_module_from_verified_bytes(\n        \"c1_probe01_verified_engine\"",
        "engine.execute(",
    ]
    positions = [body.index(token) for token in ordered]
    assert positions == sorted(positions)


def test_probe02_attempt_roots_remain_absent() -> None:
    value = manifest()["derived_paths"]
    for key in ("output_root", "cli_staging_root", "private_root"):
        assert not REPO.joinpath(*value[key].split("/")).exists()


def test_no_hosted_auth_randomization_or_repair_surface() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in BASE.glob("*.py")
        if path.name != Path(__file__).name
    )
    for forbidden in ("auth.json", "urlopen", "requests.", "urllib", "Set-ExecutionPolicy", "mkdir(parents=True, exist_ok=True)"):
        assert forbidden not in sources
    value = manifest()
    assert value["execution_authority"] and all(flag is False for flag in value["execution_authority"].values())
    assert value["authoring_boundary"]["readiness_probe_executed"] is False
    assert value["authoring_boundary"]["capability_probe_executed"] is False


def test_frozen_inventory_matches_files() -> None:
    value = manifest()
    expected = {"capability-probe-02-manifest.json"}
    for item in value["frozen_files"]:
        path = BASE / item["path"]
        expected.add(item["path"])
        assert path.stat().st_size == item["bytes"]
        assert sha256(path) == item["sha256"]
        oid = subprocess.check_output(["git", "hash-object", "--no-filters", str(path)], cwd=REPO, text=True).strip()
        assert oid == item["git_blob_oid"]
    assert {path.name for path in BASE.iterdir() if path.is_file()} == expected


def test_anchor_binding_matches_manifest() -> None:
    value = manifest()["required_parent_roots"][0]
    anchor = REPO.joinpath(*value["anchor_repo_relative_path"].split("/"))
    assert anchor.stat().st_size == value["anchor_bytes"]
    assert sha256(anchor) == value["anchor_sha256"]
    oid = subprocess.check_output(["git", "hash-object", "--no-filters", str(anchor)], cwd=REPO, text=True).strip()
    assert oid == value["anchor_git_blob_oid"]
