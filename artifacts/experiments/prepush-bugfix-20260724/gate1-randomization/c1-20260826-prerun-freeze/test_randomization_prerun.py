from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXECUTOR = _load(HERE / "randomization_prerun_executor.py", "c1_randomization_prerun")
DIST = _load(HERE / "codex_distribution.py", "c1_codex_distribution_test")
CHAIN = _load(
    REPO_ROOT
    / "artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3_evidence_chain.py",
    "c1_randomization_chain",
)


def _runtime() -> dict[str, object]:
    return {
        "client_runtime_projection_sha256": "1" * 64,
    }


class DeterministicRng:
    def __init__(self, values: list[bytes]) -> None:
        self.values = list(values)
        self.calls: list[int] = []

    def __call__(self, count: int) -> bytes:
        self.calls.append(count)
        assert self.values
        return self.values.pop(0)


def _treatments() -> dict[str, dict[str, str]]:
    return json.loads((HERE / "treatment-input-bindings.json").read_text(encoding="utf-8"))[
        "treatment_inputs"
    ]


def _patch_frozen_roots(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    evidence_root = tmp_path / "c1-skill-primary-pair-02"
    final_root = evidence_root / "repeat-01"
    monkeypatch.setattr(
        EXECUTOR,
        "_frozen_publication_roots",
        lambda repo_root, manifest: (evidence_root, final_root),
    )
    return evidence_root, final_root


def _patch_static_preconditions(monkeypatch) -> None:
    monkeypatch.setattr(EXECUTOR, "_validate_frozen_files", lambda manifest: None)
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda root, manifest: None)
    monkeypatch.setattr(
        EXECUTOR,
        "validate_authority",
        lambda root, manifest, authority: "f" * 40,
    )
    monkeypatch.setattr(
        EXECUTOR,
        "validate_executable_launch",
        lambda root: {
            "executable": Path(sys.executable),
            "scratch_root": Path("synthetic-scratch"),
            "version_stdout": b"test\n",
        },
    )
    monkeypatch.setattr(EXECUTOR, "cleanup_executable_launch", lambda observation: None)
    monkeypatch.setattr(EXECUTOR, "measure_client_identity", lambda root, launch: _runtime())


def test_gitattributes_is_checkout_stable() -> None:
    lines = (HERE / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ".gitattributes -text -whitespace"


def test_manifest_freezes_one_repo_relative_evidence_and_attempt_root() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    evidence_root, final_root = EXECUTOR._frozen_publication_roots(
        REPO_ROOT, manifest
    )
    expected_evidence = REPO_ROOT / (
        "artifacts/experiments/prepush-bugfix-20260724/gate1-randomization/"
        "c1-skill-primary-pair-02"
    )
    assert evidence_root == expected_evidence.resolve()
    assert final_root == (expected_evidence / "repeat-01").resolve()
    assert final_root.parent == evidence_root


def test_source_bindings_include_the_superseded_freeze_lineage() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["framework_base"] == {
        "d5_admission_commit": EXECUTOR.D5_ADMISSION_COMMIT,
        "source_main_commit": EXECUTOR.SOURCE_MAIN_COMMIT,
        "superseded_freeze_commit": EXECUTOR.SUPERSEDED_FREEZE_COMMIT,
    }
    EXECUTOR._validate_source_bindings(REPO_ROOT, manifest)


def test_manifest_pins_the_qualified_two_layer_npm_distribution() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    npm = manifest["npm_distribution"]
    assert npm["main"]["sha256"] == DIST.MAIN.sha256
    assert npm["main"]["integrity"] == DIST.MAIN.integrity
    assert npm["windows_x64"]["sha256"] == DIST.WINDOWS_X64.sha256
    assert npm["windows_x64"]["integrity"] == DIST.WINDOWS_X64.integrity
    assert npm["native"] == {
        "member": DIST.NATIVE_MEMBER,
        "bytes": DIST.NATIVE_BYTES,
        "sha256": DIST.NATIVE_SHA256,
    }
    assert npm["download_attempts_each"] == 1
    assert npm["raw_tarballs_retained"] is False
    assert npm["cleanup_required_before_rng"] is True


def test_archive_verifier_checks_sha1_sha256_and_sri(tmp_path: Path) -> None:
    raw = b"synthetic npm archive"
    archive = tmp_path / "package.tgz"
    archive.write_bytes(raw)
    binding = DIST.ArchiveBinding(
        name="synthetic",
        url="https://example.invalid/package.tgz",
        size=len(raw),
        sha1=hashlib.sha1(raw).hexdigest(),
        sha256=hashlib.sha256(raw).hexdigest(),
        integrity="sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode("ascii"),
        package_json_size=0,
        package_json_sha256="0" * 64,
    )
    DIST._verify_archive(archive, binding)
    archive.write_bytes(raw + b"x")
    with pytest.raises(DIST.DistributionError, match="byte count"):
        DIST._verify_archive(archive, binding)


def test_failed_distribution_materialization_removes_scratch(tmp_path: Path) -> None:
    scratch = tmp_path / "distribution"

    def corrupt_download(url: str, destination: Path, maximum: int) -> None:
        destination.write_bytes(b"corrupt")

    with pytest.raises(DIST.DistributionError):
        DIST.materialize_exact_distribution(scratch, downloader=corrupt_download)
    assert not scratch.exists()


def test_exact_identity_rebinds_native_preflight_and_command_contract() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    exact = manifest["exact_distribution_identity"]
    assert exact["cli_executable_sha256"] == DIST.NATIVE_SHA256
    assert exact["preflight_sha256"] == "c348e7aef08fe3addebeb7663501ed0058288e5f5cfb49bdda5476954336f8a3"
    assert exact["command_contract_sha256"] == "4aa350abd4eb3575fd0319d349091ed1180199423fd72719c7b5e22f6e2690e1"
    assert exact["runner_accepted_preflight"] is True
    assert manifest["client_runtime_projection_sha256"] == "87c99bb72ca3a07488186f219edb1184b406eb305d23ccb92a6023f83093bce8"


def test_treatment_bindings_use_complete_digests_and_no_absent_literal() -> None:
    document = json.loads(
        (HERE / "treatment-input-bindings.json").read_text(encoding="utf-8")
    )
    assert set(document["treatment_inputs"]) == {"A", "B"}
    assert "absent" not in json.dumps(document)
    for treatment in document["treatment_inputs"].values():
        assert set(treatment) == set(CHAIN.TREATMENT_INPUT_DIGEST_FIELDS)
        assert all(CHAIN.HEX64.fullmatch(value) for value in treatment.values())


def test_randomization_vectors_match_shipped_contract() -> None:
    rng = DeterministicRng(
        [bytes(range(6)), bytes(range(6, 12)), bytes(range(32)), b"\x00"]
    )
    record, reveal = EXECUTOR.build_randomization_documents(
        chain=CHAIN, treatment_inputs=_treatments(), rng=rng
    )
    assert rng.calls == [6, 6, 32, 1]
    assert record["anonymous_ids"] == ["OUT-000102030405", "OUT-060708090a0b"]
    assert reveal["schema"] == "gate3-mapping-release.v1"
    assert reveal["mapping"] == {
        "OUT-000102030405": "A",
        "OUT-060708090a0b": "B",
    }
    assert reveal["nonce_hex"] == bytes(range(32)).hex()
    assert record["mapping_commitment_sha256"] == CHAIN._mapping_commitment(
        reveal["mapping"], reveal["study_kind"], reveal["nonce_hex"]
    )


def test_selector_changes_only_the_private_mapping() -> None:
    even = DeterministicRng([b"\x00" * 6, b"\x01" * 6, b"\x02" * 32, b"\x00"])
    odd = DeterministicRng([b"\x00" * 6, b"\x01" * 6, b"\x02" * 32, b"\x01"])
    even_record, even_reveal = EXECUTOR.build_randomization_documents(
        chain=CHAIN, treatment_inputs=_treatments(), rng=even
    )
    odd_record, odd_reveal = EXECUTOR.build_randomization_documents(
        chain=CHAIN, treatment_inputs=_treatments(), rng=odd
    )
    assert even_record["anonymous_ids"] == odd_record["anonymous_ids"]
    assert even_reveal["mapping"] != odd_reveal["mapping"]
    assert even_record["mapping_commitment_sha256"] != odd_record["mapping_commitment_sha256"]


def test_duplicate_anonymous_id_fails_without_redraw() -> None:
    rng = DeterministicRng([b"x" * 6, b"x" * 6, b"n" * 32, b"\x00"])
    with pytest.raises(EXECUTOR.BindingError, match="duplicate"):
        EXECUTOR.build_randomization_documents(
            chain=CHAIN, treatment_inputs=_treatments(), rng=rng
        )
    assert rng.calls == [6, 6, 32, 1]


@pytest.mark.parametrize(
    "values",
    [
        [b"x" * 5, b"y" * 6, b"n" * 32, b"\x00"],
        [b"x" * 6, b"y" * 6, b"n" * 31, b"\x00"],
        [b"x" * 6, b"y" * 6, b"n" * 32, b""],
    ],
)
def test_rng_length_mismatch_fails(values: list[bytes]) -> None:
    with pytest.raises(EXECUTOR.BindingError, match="unexpected byte count"):
        EXECUTOR.build_randomization_documents(
            chain=CHAIN, treatment_inputs=_treatments(), rng=DeterministicRng(values)
        )


def test_batch_admission_defines_exact_twelve_hour_window() -> None:
    now = datetime(2026, 8, 26, 1, 2, 3, 456789, tzinfo=timezone.utc)
    batch = EXECUTOR.build_batch_admission(
        runtime=_runtime(), freeze_commit="f" * 40, now=now
    )
    assert batch["admission_at_utc"] == "2026-08-26T01:02:03.456789Z"
    assert batch["window_expires_at_utc"] == "2026-08-26T13:02:03.456789Z"
    assert batch["identity_evidence_level"] == "CLIENT_SIDE_INVOCATION_ONLY"
    assert batch["server_executed_model_observed"] is False
    assert batch["provider_attestation_available"] is False


def test_batch_admission_rejects_non_utc_time() -> None:
    with pytest.raises(EXECUTOR.WindowError, match="not UTC"):
        EXECUTOR.build_batch_admission(
            runtime=_runtime(), freeze_commit="f" * 40, now=datetime.now()
        )


@pytest.mark.parametrize(
    "field",
    ["mapping", "nonce", "nonce_hex", "provider_response_model", "server_model_id"],
)
def test_public_retention_rejects_private_or_provider_fields(field: str) -> None:
    with pytest.raises(EXECUTOR.BindingError, match="forbidden"):
        EXECUTOR._walk_forbidden({field: "x"})


def test_full_synthetic_execution_commits_only_event_one(tmp_path: Path, monkeypatch) -> None:
    _patch_static_preconditions(monkeypatch)
    now = datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc)
    rng = DeterministicRng(
        [bytes(range(6)), bytes(range(6, 12)), bytes(range(32)), b"\x00"]
    )
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root, launch: _runtime(),
        rng=rng,
        now=lambda: now,
    )
    assert terminal["status"] == EXECUTOR.STATUS_COMMITTED, terminal
    assert terminal["randomization_created"] is True
    assert terminal["event_count"] == 1
    assert sorted(path.relative_to(final_root).as_posix() for path in final_root.rglob("*") if path.is_file()) == [
        "batch-admission.json",
        "control/mapping-reveal.json",
        "evidence/chain/0001-randomization-committed.json",
        "evidence/randomization-record.json",
        "terminal.json",
    ]
    report = CHAIN.verify_chain(
        final_root / "evidence/chain", EXECUTOR._contract_path(REPO_ROOT)
    )
    assert report["event_count"] == 1
    assert report["state"] == "randomization_committed"
    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            final_root / "batch-admission.json",
            final_root / "evidence/randomization-record.json",
                final_root / "evidence/chain/0001-randomization-committed.json",
            final_root / "terminal.json",
        ]
    )
    assert '"mapping"' not in public_text
    assert '"nonce_hex"' not in public_text


def test_distribution_cleanup_completes_before_rng(tmp_path: Path, monkeypatch) -> None:
    _patch_static_preconditions(monkeypatch)
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    cleaned = False
    values = [bytes(range(6)), bytes(range(6, 12)), bytes(range(32)), b"\x00"]

    def cleanup(observation) -> None:
        nonlocal cleaned
        cleaned = True

    def rng(count: int) -> bytes:
        assert cleaned
        return values.pop(0)

    monkeypatch.setattr(EXECUTOR, "cleanup_executable_launch", cleanup)
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root, launch: _runtime(),
        rng=rng,
        now=lambda: datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc),
    )
    assert terminal["status"] == EXECUTOR.STATUS_COMMITTED
    assert cleaned is True


def test_authority_failure_happens_before_rng_and_leaves_one_terminal(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(EXECUTOR, "_validate_frozen_files", lambda manifest: None)
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda root, manifest: None)
    monkeypatch.setattr(
        EXECUTOR,
        "validate_authority",
        lambda root, manifest, authority: (_ for _ in ()).throw(
            EXECUTOR.AuthorityError("wrong commit")
        ),
    )
    rng = DeterministicRng([])
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="0" * 40,
        runtime_probe=lambda root, launch: (_ for _ in ()).throw(AssertionError("runtime called")),
        rng=rng,
    )
    assert terminal["status"] == EXECUTOR.STATUS_AUTHORITY
    assert terminal["randomization_created"] is False
    assert rng.calls == []
    assert [path.name for path in final_root.iterdir()] == ["terminal.json"]


def test_executable_permission_error_is_infrastructure_failure(monkeypatch, tmp_path: Path) -> None:
    class FakeDistribution:
        CLI_VERSION_STDOUT = b"test\n"
        NATIVE_BYTES = Path(sys.executable).stat().st_size
        NATIVE_SHA256 = EXECUTOR.sha256_file(Path(sys.executable))

        @staticmethod
        def materialize_exact_distribution(root):
            return {"executable": Path(sys.executable), "scratch_root": tmp_path}

        @staticmethod
        def cleanup_distribution(observation):
            return None

    monkeypatch.setattr(EXECUTOR, "_module", lambda path, name: FakeDistribution)
    monkeypatch.setattr(
        EXECUTOR.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
    )
    with pytest.raises(EXECUTOR.InfrastructureError, match="launch failed"):
        EXECUTOR.validate_executable_launch(REPO_ROOT)


def test_infrastructure_failure_consumes_pair_without_rng(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_static_preconditions(monkeypatch)
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    rng = DeterministicRng([])

    first = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        launch_probe=lambda root: (_ for _ in ()).throw(
            EXECUTOR.InfrastructureError("executable launch denied")
        ),
        runtime_probe=lambda root, launch: (_ for _ in ()).throw(
            AssertionError("runtime called")
        ),
        rng=rng,
    )
    second = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root, launch: (_ for _ in ()).throw(
            AssertionError("runtime called")
        ),
        rng=rng,
    )

    assert first["status"] == EXECUTOR.STATUS_INFRASTRUCTURE
    assert first["randomization_created"] is False
    assert first["event_count"] == 0
    assert second["status"] == EXECUTOR.STATUS_EXISTS
    assert second["randomization_created"] is False
    assert rng.calls == []
    assert [path.name for path in final_root.iterdir()] == ["terminal.json"]


def test_publication_staging_uses_parent_inheriting_directory(
    tmp_path: Path,
) -> None:
    final_root = tmp_path / "evidence-root" / "repeat-01"
    staging = EXECUTOR._create_publication_staging(final_root)
    assert staging == final_root.parent / ".repeat-01.publication-staging"
    assert staging.is_dir()
    if os.name == "nt":
        result = subprocess.run(
            ["icacls", str(staging)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        access_lines = [line for line in result.stdout.splitlines() if ":(" in line]
        assert access_lines
        assert all("(I)" in line for line in access_lines)


def test_wrong_output_root_fails_before_rng(tmp_path: Path, monkeypatch) -> None:
    _patch_static_preconditions(monkeypatch)
    _, expected_root = _patch_frozen_roots(monkeypatch, tmp_path)
    wrong_root = tmp_path / "alternate-attempt"
    rng = DeterministicRng([])
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=wrong_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root, launch: (_ for _ in ()).throw(AssertionError("runtime called")),
        rng=rng,
    )
    assert terminal["status"] == EXECUTOR.STATUS_OUTPUT_ROOT
    assert terminal["randomization_created"] is False
    assert rng.calls == []
    assert not wrong_root.exists()
    assert not expected_root.exists()


@pytest.mark.parametrize(
    "artifact_name",
    [
        "randomization-record.json",
        "0001-randomization-committed.json",
        "terminal.json",
    ],
)
def test_prior_pair_state_at_alternate_path_blocks_before_rng(
    artifact_name: str, tmp_path: Path, monkeypatch
) -> None:
    _patch_static_preconditions(monkeypatch)
    evidence_root, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    prior = evidence_root / "alternate" / "evidence" / artifact_name
    prior.parent.mkdir(parents=True)
    prior.write_text('{"pair_id":"C1-skill-primary-pair-02"}\n', encoding="utf-8")
    rng = DeterministicRng([])
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root, launch: (_ for _ in ()).throw(AssertionError("runtime called")),
        rng=rng,
    )
    assert terminal["status"] == EXECUTOR.STATUS_PRIOR_PAIR
    assert terminal["randomization_created"] is False
    assert rng.calls == []
    assert prior.is_file()
    assert [path.name for path in final_root.iterdir()] == ["terminal.json"]


def test_existing_terminal_is_not_overwritten(tmp_path: Path, monkeypatch) -> None:
    _patch_static_preconditions(monkeypatch)
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    final_root.mkdir(parents=True)
    existing = EXECUTOR._terminal(
        status=EXECUTOR.STATUS_AUTHORITY,
        freeze_commit="f" * 40,
        diagnostic="first terminal",
        randomization_created=False,
    )
    original = EXECUTOR.canonical_json_bytes(existing)
    (final_root / "terminal.json").write_bytes(original)
    result = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
    )
    assert result["status"] == EXECUTOR.STATUS_EXISTS
    assert (final_root / "terminal.json").read_bytes() == original


def test_ambiguous_existing_directory_fails_closed(tmp_path: Path, monkeypatch) -> None:
    _patch_static_preconditions(monkeypatch)
    _, final_root = _patch_frozen_roots(monkeypatch, tmp_path)
    final_root.mkdir(parents=True)
    (final_root / "unknown.json").write_text("{}\n", encoding="utf-8")
    result = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
    )
    assert result["status"] == EXECUTOR.STATUS_AMBIGUOUS
    assert result["randomization_created"] is False


def test_terminal_policy_lists_all_executor_terminals() -> None:
    policy = json.loads((HERE / "terminal-policy.json").read_text(encoding="utf-8"))
    expected = {
        EXECUTOR.STATUS_AUTHORITY,
        EXECUTOR.STATUS_BINDING,
        EXECUTOR.STATUS_INFRASTRUCTURE,
        EXECUTOR.STATUS_IDENTITY,
        EXECUTOR.STATUS_WINDOW,
        EXECUTOR.STATUS_TREATMENT,
        EXECUTOR.STATUS_OUTPUT_ROOT,
        EXECUTOR.STATUS_PRIOR_PAIR,
        EXECUTOR.STATUS_EXISTS,
        EXECUTOR.STATUS_AMBIGUOUS,
        EXECUTOR.STATUS_COMMITTED,
    }
    assert set(policy["allowed_statuses_in_precedence_order"]) == expected
    assert policy["allowed_statuses_in_precedence_order"][-1] == EXECUTOR.STATUS_COMMITTED


def test_design_packet_provenance_is_pinned() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    provenance = manifest["design_packet"]
    assert provenance["original_reviewed_lines"] == 419
    assert provenance["original_reviewed_bytes"] == 18499
    assert provenance["original_reviewed_sha256"] == (
        "04dd05343ca483cb61086dbb60c24fdd05466252da055e025e32977158e4dde0"
    )
    assert provenance["review_status"] == "IMPLEMENTATION_CORRECTIONS_REQUIRE_REVIEW"
    assert provenance["current_sha256"] != provenance["original_reviewed_sha256"]


def test_frozen_files_bind_every_file_except_manifest() -> None:
    manifest = json.loads(
        (HERE / "randomization-prerun-manifest.json").read_text(encoding="utf-8")
    )
    frozen = {entry["path"]: entry for entry in manifest["frozen_files"]}
    expected = {
        path.name
        for path in HERE.iterdir()
        if path.is_file() and path.name != "randomization-prerun-manifest.json"
    }
    assert set(frozen) == expected
    for name, entry in frozen.items():
        raw = (HERE / name).read_bytes()
        assert len(raw) == entry["bytes"]
        assert EXECUTOR.sha256_bytes(raw) == entry["sha256"]
