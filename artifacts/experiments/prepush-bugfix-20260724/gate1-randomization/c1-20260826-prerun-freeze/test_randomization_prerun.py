from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXECUTOR = _load(HERE / "randomization_prerun_executor.py", "c1_randomization_prerun")
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


def test_gitattributes_is_checkout_stable() -> None:
    lines = (HERE / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ".gitattributes -text -whitespace"


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
    monkeypatch.setattr(EXECUTOR, "_validate_frozen_files", lambda manifest: None)
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda root, manifest: None)
    monkeypatch.setattr(
        EXECUTOR,
        "validate_authority",
        lambda root, manifest, authority: "f" * 40,
    )
    now = datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc)
    rng = DeterministicRng(
        [bytes(range(6)), bytes(range(6, 12)), bytes(range(32)), b"\x00"]
    )
    final_root = tmp_path / "attempt"
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="f" * 40,
        runtime_probe=lambda root: _runtime(),
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
    final_root = tmp_path / "attempt"
    terminal = EXECUTOR.execute_randomization(
        repo_root=REPO_ROOT,
        final_root=final_root,
        owner_authorized_commit="0" * 40,
        runtime_probe=lambda root: (_ for _ in ()).throw(AssertionError("runtime called")),
        rng=rng,
    )
    assert terminal["status"] == EXECUTOR.STATUS_AUTHORITY
    assert terminal["randomization_created"] is False
    assert rng.calls == []
    assert [path.name for path in final_root.iterdir()] == ["terminal.json"]


def test_existing_terminal_is_not_overwritten(tmp_path: Path) -> None:
    final_root = tmp_path / "attempt"
    final_root.mkdir()
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


def test_ambiguous_existing_directory_fails_closed(tmp_path: Path) -> None:
    final_root = tmp_path / "attempt"
    final_root.mkdir()
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
        EXECUTOR.STATUS_IDENTITY,
        EXECUTOR.STATUS_WINDOW,
        EXECUTOR.STATUS_TREATMENT,
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
