from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from governance_tools import solo_r2_r1_structural_conformance as conformance


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy(root: Path, relpath: str) -> None:
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / relpath, target)


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "framework"
    root.mkdir()
    (root / "AGENTS.md").write_text("# synthetic root\n", encoding="utf-8")
    (root / "governance").mkdir()
    paths = {
        conformance.INSPECTOR_RELPATH,
        *(binding["path"] for binding in conformance._AUTHORITY_BINDINGS),
        *(binding["path"] for binding in conformance._SOURCE_BINDINGS),
        *conformance._RUNTIME_MODULES,
    }
    for relpath in sorted(paths):
        _copy(root, relpath)
    (root / conformance.EVIDENCE_RELPATH).parent.mkdir(parents=True)
    return root


def _recursive_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if type(value) is dict:
        for key, nested in value.items():
            keys.add(key)
            keys.update(_recursive_keys(nested))
    elif type(value) is list:
        for nested in value:
            keys.update(_recursive_keys(nested))
    return keys


def test_build_is_deterministic_and_binds_exact_sources(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)

    first = conformance.build_evidence(root)
    second = conformance.build_evidence(root)
    first_bytes = conformance.encode_evidence(first)
    second_bytes = conformance.encode_evidence(second)

    assert first_bytes == second_bytes
    assert first_bytes.endswith(b"\n")
    assert not first_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in first_bytes
    assert str(root).encode("utf-8") not in first_bytes
    assert first["machine_disposition"] == conformance.STRUCTURAL_CONFORMANCE_PASS
    assert first["sampling_role"] == "REGRESSION_ONLY_NOT_PROOF"
    assert first["source_snapshot"]["repository_tree_commit"] == (
        "581b37f91d7af318bdd6adc5a1eedb1fd68a1f78"
    )
    assert {
        binding["sha256"]
        for binding in first["source_snapshot"]["source_bindings"]
    } == {binding["sha256"] for binding in conformance._SOURCE_BINDINGS}

    bindings = {
        binding["path"]: binding
        for binding in first["source_snapshot"]["source_bindings"]
    }
    assert bindings["governance_tools/solo_attempt_ledger_v2.py"] == {
        "path": "governance_tools/solo_attempt_ledger_v2.py",
        "sha256": "652e9c8f2fb01cade50c8e712cf0819341f36c4fd14bef43fb90fb606e20c5dc",
        "git_blob": "a1947f59b76832b11b43029b4fac0c88fed801ed",
        "last_change_commit": "581b37f91d7af318bdd6adc5a1eedb1fd68a1f78",
        "role": "atomic_genesis_publication_runtime_surface",
        "bytes": 29138,
    }
    assert bindings["governance_tools/solo_r2_bootstrap.py"] == {
        "path": "governance_tools/solo_r2_bootstrap.py",
        "sha256": "c600126318a687a13f4b51a0aa192f8c1baafe8f76ceefc2185e33318820bdf6",
        "git_blob": "f52ce48b84a95f00e629989e8b25a24fafd7a7f8",
        "last_change_commit": "581b37f91d7af318bdd6adc5a1eedb1fd68a1f78",
        "role": "bootstrap_runtime_participant_and_call_site_closure",
        "bytes": 15739,
    }
    assert bindings["governance_tools/solo_r2_controller_state.py"] == {
        "path": "governance_tools/solo_r2_controller_state.py",
        "sha256": "58275494ac3ecd6dba422300008e0111ad6d8533298c64b7584eb3753d26087f",
        "git_blob": "c73a5515b5024c59a5271bd6b93d11f7d7f97c37",
        "last_change_commit": "33896f224fdf8dba50302756e53b84e82c186d6c",
        "role": "sealed_order_revalidation",
        "bytes": 30061,
    }
    assert bindings["governance_tools/solo_r2_pair_creation.py"] == {
        "path": "governance_tools/solo_r2_pair_creation.py",
        "sha256": "76e8fecf3571c7e5deac9d1437bbbb55b6604fe5262186503701cda490ea43ff",
        "git_blob": "abb6b099f53e56d7bcc626712aeac2da6545ad1d",
        "last_change_commit": "581b37f91d7af318bdd6adc5a1eedb1fd68a1f78",
        "role": "pair_creation_entropy_and_arm_order_call_site_closure",
        "bytes": 22426,
    }


def test_namespace_records_one_exact_self_exclusion(tmp_path: Path) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))
    namespace = evidence["production_namespace_scan"]

    assert namespace["excluded_validation_modules"] == [
        {
            "path": "governance_tools/solo_r2_r1_structural_conformance.py",
            "reason": "structural_conformance_inspector_not_runtime_participant",
        }
    ]
    assert conformance.INSPECTOR_RELPATH in namespace["observed_modules"]
    assert conformance.INSPECTOR_RELPATH not in namespace["runtime_participants"]
    assert set(namespace["runtime_participants"]) == set(
        conformance._RUNTIME_MODULES
    )
    assert "governance_tools/solo_r2_bootstrap.py" in namespace[
        "runtime_participants"
    ]
    assert "governance_tools/solo_r2_pair_creation.py" in namespace[
        "runtime_participants"
    ]


def test_bootstrap_is_bound_and_has_no_generator_call_site(tmp_path: Path) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))

    bootstrap_path = "governance_tools/solo_r2_bootstrap.py"
    assert any(
        binding["path"] == bootstrap_path
        for binding in evidence["source_snapshot"]["source_bindings"]
    )
    assert bootstrap_path not in evidence["generator_surfaces"][
        "random_domain_import_projection"
    ]
    assert all(
        call["path"] != bootstrap_path
        for call in evidence["production_call_sites"]
    )


def test_pair_creation_is_bound_to_zero_argument_order_entropy(
    tmp_path: Path,
) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))
    pair_path = "governance_tools/solo_r2_pair_creation.py"

    assert any(
        binding["path"] == pair_path
        for binding in evidence["source_snapshot"]["source_bindings"]
    )
    assert evidence["generator_surfaces"]["pair_creation"] == {
        "entropy_drawer_signature": [],
        "entropy_source": "os.urandom(random_domains.ENTROPY_BYTES)",
        "order_state_signature": ["evaluation_id", "pair_id"],
        "order_entropy_assignment": "order_entropy = _draw_entropy32()",
        "arm_order_input": "order_entropy",
    }
    assert evidence["generator_surfaces"]["random_domain_import_projection"][
        pair_path
    ] == ["solo_r2_random_domains as random_domains"]
    assert [
        call
        for call in evidence["production_call_sites"]
        if call["path"] == pair_path
    ] == [
        {
            "path": pair_path,
            "scope": "_order_state",
            "line": 466,
            "callee": "_draw_entropy32",
            "args": [],
            "keywords": {},
        },
        {
            "path": pair_path,
            "scope": "_order_state",
            "line": 468,
            "callee": "random_domains.arm_order_from_entropy",
            "args": ["order_entropy"],
            "keywords": {},
        },
    ]


def test_pair_creation_rejects_secret_correlated_order_inputs() -> None:
    source = (REPO_ROOT / "governance_tools/solo_r2_pair_creation.py").read_text(
        encoding="utf-8"
    )
    draw_from_pair = source.replace(
        "order_entropy = _draw_entropy32()",
        "order_entropy = _draw_entropy32(pair_id)",
        1,
    )
    with pytest.raises(conformance.R1ConformanceError):
        conformance._validate_pair_creation(ast.parse(draw_from_pair))

    order_from_pair = source.replace(
        "random_domains.arm_order_from_entropy(order_entropy)",
        "random_domains.arm_order_from_entropy(pair_id)",
        1,
    )
    with pytest.raises(conformance.R1ConformanceError):
        conformance._validate_pair_creation(ast.parse(order_from_pair))


def test_new_r2_production_module_invalidates_namespace(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    (root / "governance_tools/solo_r2_shadow_caller.py").write_text(
        "# unexpected runtime participant\n", encoding="utf-8"
    )

    with pytest.raises(conformance.R1ConformanceError) as caught:
        conformance.build_evidence(root)
    assert caught.value.code == conformance.R1_CONFORMANCE_FAILURE


def test_bound_source_byte_change_invalidates_evidence(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    target = root / "governance_tools/solo_r2_random_domains.py"
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(conformance.R1ConformanceError) as caught:
        conformance.build_evidence(root)
    assert caught.value.code == conformance.R1_CONFORMANCE_FAILURE


def test_opaque_generator_rejects_extra_or_indirect_forbidden_input() -> None:
    source = (REPO_ROOT / "governance_tools/solo_r2_random_domains.py").read_text(
        encoding="utf-8"
    )
    extra_parameter = source.replace(
        "def derive_opaque_identifier(domain_tag: str, entropy: bytes) -> str:",
        "def derive_opaque_identifier(domain_tag: str, entropy: bytes, pair_id=None) -> str:",
    )
    with pytest.raises(conformance.R1ConformanceError):
        conformance._validate_random_domains(ast.parse(extra_parameter))

    indirect_attribute = source.replace(
        "    _validate_domain(domain_tag, OPAQUE_ID_DOMAINS)\n",
        "    _validate_domain(domain_tag, OPAQUE_ID_DOMAINS)\n"
        "    hidden = context.arm\n",
        1,
    )
    with pytest.raises(conformance.R1ConformanceError):
        conformance._validate_random_domains(ast.parse(indirect_attribute))


def test_presentation_builder_rejects_non_presentation_input() -> None:
    source = (
        REPO_ROOT / "governance_tools/solo_r2_blind_scoring_bundle.py"
    ).read_text(encoding="utf-8")
    mutated = source.replace(
        "presentation_order_bit_from_entropy(presentation_entropy)",
        "presentation_order_bit_from_entropy(outputs_by_label)",
        1,
    )

    with pytest.raises(conformance.R1ConformanceError):
        conformance._validate_bundle(ast.parse(mutated))


def test_production_call_site_projection_is_exact(tmp_path: Path) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))

    assert evidence["production_call_sites"] == sorted(
        (dict(item) for item in conformance._EXPECTED_RELEVANT_CALLS),
        key=lambda item: (item["path"], item["line"], item["callee"]),
    )
    presentation = [
        item
        for item in evidence["production_call_sites"]
        if item["callee"] == "scoring_bundle.build_blind_scoring_bundle"
    ]
    assert presentation == [
        {
            "path": "governance_tools/solo_r2_lifecycle_integration.py",
            "scope": "SyntheticLifecycleCoordinator.prepare_scoring.operation",
            "line": 767,
            "callee": "scoring_bundle.build_blind_scoring_bundle",
            "args": [],
            "keywords": {
                "evaluation_id": "self._evaluation_id",
                "outputs_by_label": "outputs_by_label",
                "pair_id": "self._pair_id",
                "presentation_entropy": "_draw_entropy32()",
                "rubric_id": "self._rubric_id",
                "slot": "SYNTHETIC_SLOT",
            },
        }
    ]


def test_call_site_reuse_of_order_entropy_is_detectably_different() -> None:
    relpath = "governance_tools/solo_r2_lifecycle_integration.py"
    source = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    mutated = source.replace(
        "presentation_entropy=_draw_entropy32()",
        "presentation_entropy=order_entropy",
        1,
    )
    calls = sorted(
        conformance._collect_calls(relpath, ast.parse(mutated)),
        key=lambda item: (item["path"], item["line"], item["callee"]),
    )
    expected = sorted(
        (
            dict(item)
            for item in conformance._EXPECTED_RELEVANT_CALLS
            if item["path"] == relpath
        ),
        key=lambda item: (item["path"], item["line"], item["callee"]),
    )

    assert calls != expected
    build_call = next(
        item
        for item in calls
        if item["callee"] == "scoring_bundle.build_blind_scoring_bundle"
    )
    assert build_call["keywords"]["presentation_entropy"] == "order_entropy"


def test_tranche4_interface_reconciliation_is_mechanically_bound(
    tmp_path: Path,
) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))
    reconciliation = evidence["tranche4_interface_reconciliation"]

    assert reconciliation["implementation_commit"] == (
        conformance.TRANCHE4_IMPLEMENTATION_COMMIT
    )
    assert reconciliation["scorer_delivery"] == {
        "fields": ["bundle_path", "bundle_bytes"],
        "frozen": True,
        "ledger_path_visible_to_scorer": False,
    }
    narrowing = next(
        item
        for item in reconciliation["mapping"]
        if item["definition"] == "record_pre_attempt_failure()"
    )
    assert narrowing["disposition"] == "ACCEPTED_CAPABILITY_NARROWING"
    assert all(
        item["implementation"] != "record_pre_attempt_failure()"
        for item in reconciliation["mapping"]
    )


def test_candidate_metadata_is_deterministic_and_externally_routed(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    evidence = conformance.build_evidence(root)
    metadata = evidence["metadata_reconciliation"]

    assert metadata["candidate_json_excludes"] == [
        "absolute_local_path",
        "human_review_disposition",
        "review_timestamp",
        "reviewer_identity",
    ]
    assert metadata["external_provenance_layers"] == {
        "human_review_disposition": "read_only_exact_identity_review",
        "review_actor": "review_record",
        "time_and_durability": "git_commit",
        "evidence_identity": "git_blob_and_sha256",
    }
    assert "timestamp" not in _recursive_keys(evidence)
    assert "reviewer" not in _recursive_keys(evidence)
    assert str(root) not in conformance.encode_evidence(evidence).decode("utf-8")


def test_evidence_schema_is_closed(tmp_path: Path) -> None:
    evidence = conformance.build_evidence(_fixture_root(tmp_path))
    evidence["unexpected"] = True

    with pytest.raises(conformance.R1ConformanceError):
        conformance.encode_evidence(evidence)


def test_write_is_create_once_and_preserves_existing_bytes(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    target, written = conformance.write_evidence(root)

    assert target == root / conformance.EVIDENCE_RELPATH
    assert target.read_bytes() == written
    with pytest.raises(conformance.R1ConformanceError) as caught:
        conformance.write_evidence(root)
    assert caught.value.code == conformance.R1_EVIDENCE_WRITE_FAILURE
    assert target.read_bytes() == written


def test_new_generation_write_preserves_previous_evidence(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    previous = root / conformance.PREVIOUS_EVIDENCE_RELPATH
    previous.parent.mkdir(parents=True, exist_ok=True)
    previous_bytes = b'{"generation":"51e9a27c"}\n'
    previous.write_bytes(previous_bytes)

    target, _ = conformance.write_evidence(root)

    assert target == root / conformance.EVIDENCE_RELPATH
    assert target != previous
    assert previous.read_bytes() == previous_bytes


def test_failure_before_write_leaves_no_partial_artifact(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    target = root / conformance.EVIDENCE_RELPATH
    source = root / "governance_tools/solo_r2_random_domains.py"
    source.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(conformance.R1ConformanceError):
        conformance.write_evidence(root)
    assert not target.exists()


def test_project_root_must_be_explicit_absolute_and_governed(
    tmp_path: Path,
) -> None:
    with pytest.raises(conformance.R1ConformanceError):
        conformance.build_evidence(Path("relative-root"))

    bare = tmp_path / "bare"
    bare.mkdir()
    with pytest.raises(conformance.R1ConformanceError):
        conformance.build_evidence(bare)


def test_main_reports_only_fixed_disposition_and_digest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _fixture_root(tmp_path)

    assert conformance.main(["--project-root", str(root), "--check"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("STRUCTURAL_CONFORMANCE_PASS sha256=")
    assert str(root) not in captured.out
