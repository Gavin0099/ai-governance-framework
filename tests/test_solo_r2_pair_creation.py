from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_pair_creation as pair_creation


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LEDGER = REPO_ROOT / ledger.PUBLIC_LEDGER_PATH
SECRET_TEST_ROOT_UNTRUSTED = "SECRET_TEST_ROOT_UNTRUSTED / STOP"


def _genesis_bytes() -> bytes:
    current = CANONICAL_LEDGER.read_bytes()
    genesis = current.split(b"\n", 1)[0] + b"\n"
    assert hashlib.sha256(genesis).hexdigest() == pair_creation.EXPECTED_GENESIS_SHA256
    return genesis


def _environment(
    tmp_path: Path,
) -> tuple[
    Path,
    controller.CustodyBoundary,
    Path,
    Path,
    dict[str, Path],
]:
    assert REPO_ROOT.resolve() not in tmp_path.resolve().parents, SECRET_TEST_ROOT_UNTRUSTED
    project_root = tmp_path / "governance-root"
    project_root.mkdir()
    (project_root / "AGENTS.md").write_text("# synthetic root\n", encoding="utf-8")
    (project_root / "governance").mkdir()
    public_path = project_root / ledger.PUBLIC_LEDGER_PATH
    public_path.parent.mkdir(parents=True)
    public_path.write_bytes(_genesis_bytes())

    roots = {
        name: tmp_path / name
        for name in (
            "consumer",
            "materialization",
            "execution",
            "scoring",
            "controller-state",
            "controller-custody",
        )
    }
    for root in roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=project_root,
        consumer_root=roots["consumer"],
        materialization_root=roots["materialization"],
        execution_root=roots["execution"],
        scoring_root=roots["scoring"],
    )
    key_path = roots["controller-custody"] / "key.json"
    controller.create_controller_key(key_path, custody_boundary=boundary)
    return project_root, boundary, key_path, public_path, roots


def _create(
    project_root: Path,
    boundary: controller.CustodyBoundary,
    key_path: Path,
    roots: dict[str, Path],
) -> pair_creation.PairCreationResult:
    return pair_creation.create_shakedown_pair(
        project_root=project_root,
        controller_root=roots["controller-state"],
        key_path=key_path,
        custody_boundary=boundary,
    )


def test_pair_creation_seals_order_before_public_pair_and_stops_without_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    real_append = ledger.append_event
    append_observations: list[tuple[str, ...]] = []

    def observe_append(path: Path | str, event: dict[str, object]):
        checkpoints = tuple(
            candidate.name
            for candidate in roots["controller-state"].glob("*.sealed.json")
        )
        assert len(checkpoints) == 1
        assert event["event_type"] == "PAIR_CREATED"
        append_observations.append(checkpoints)
        return real_append(path, event)

    monkeypatch.setattr(pair_creation.ledger, "append_event", observe_append)
    canonical_before = CANONICAL_LEDGER.read_bytes()
    result = _create(project_root, boundary, key_path, roots)

    assert len(append_observations) == 1
    assert result.checkpoint_path.parent == roots["controller-state"]
    assert result.checkpoint_path.read_bytes().endswith(b"\n")
    assert hashlib.sha256(result.checkpoint_path.read_bytes()).hexdigest() == (
        result.sealed_package_digest
    )
    UUID(result.pair_id, version=4)
    UUID(result.event_id, version=4)

    events = ledger.read_ledger(public_path)
    summary = ledger.validate_ledger_events(events)
    assert [event["event_type"] for event in events] == [
        "V2_GENESIS",
        "PAIR_CREATED",
    ]
    assert events[1]["pair_id"] == result.pair_id
    assert events[1]["slot"] == pair_creation.SHAKEDOWN_SLOT
    assert events[1]["category"] == pair_creation.SHAKEDOWN_CATEGORY
    assert events[1]["repository"] == pair_creation.SHAKEDOWN_REPOSITORY
    assert events[1]["frozen_identities"] == dict(pair_creation._FROZEN_IDENTITIES)
    assert summary.pair_count == 1
    assert summary.initiated_attempt_count == 0
    assert summary.admitted_attempt_count == 0
    assert summary.terminal_execution_count == 0
    assert summary.scoring_record_count == 0
    assert summary.unblinding_record_count == 0
    assert result.ledger_sha256 == hashlib.sha256(public_path.read_bytes()).hexdigest()
    assert CANONICAL_LEDGER.read_bytes() == canonical_before

    state = controller.open_controller_package(
        result.checkpoint_path.read_bytes(),
        key_path=key_path,
        custody_boundary=boundary,
        expected_digest=result.sealed_package_digest,
        expected_evaluation_id=pair_creation.EXPECTED_EVALUATION_ID,
        expected_pair_id=result.pair_id,
        expected_slot=pair_creation.SHAKEDOWN_SLOT,
    )
    assert state["state_phase"] == controller.ORDER_FROZEN
    assert state["pair_id"] == result.pair_id
    assert set(state["realized_order"]) == {"CONTROL", "TREATMENT"}
    assert len(state["order_entropy"]) > 0
    assert state["attempt_bindings"] == []


def test_exact_genesis_is_required_before_any_private_write(tmp_path: Path) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    event = ledger.read_ledger(public_path)[0]
    event["event_id"] = "00000000-0000-4000-8000-000000000001"
    public_path.write_bytes(ledger.encode_event(event))

    with pytest.raises(pair_creation.PairCreationError) as caught:
        _create(project_root, boundary, key_path, roots)
    assert caught.value.code == pair_creation.PAIR_CREATION_FAILURE
    assert not list(roots["controller-state"].iterdir())
    assert ledger.validate_ledger_file(public_path).pair_count == 0


def test_existing_pair_cannot_be_reused_or_replaced(tmp_path: Path) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    _create(project_root, boundary, key_path, roots)
    first_bytes = public_path.read_bytes()
    checkpoint_bytes = {
        path.name: path.read_bytes() for path in roots["controller-state"].iterdir()
    }

    with pytest.raises(pair_creation.PairCreationError):
        _create(project_root, boundary, key_path, roots)
    assert public_path.read_bytes() == first_bytes
    assert {
        path.name: path.read_bytes() for path in roots["controller-state"].iterdir()
    } == checkpoint_bytes
    assert ledger.validate_ledger_file(public_path).pair_count == 1


@pytest.mark.parametrize(
    "root_name",
    ["consumer", "materialization", "execution", "scoring", "controller-custody"],
)
def test_forbidden_or_overlapping_controller_root_is_rejected(
    tmp_path: Path, root_name: str
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()

    with pytest.raises(pair_creation.PairCreationError):
        pair_creation.create_shakedown_pair(
            project_root=project_root,
            controller_root=roots[root_name],
            key_path=key_path,
            custody_boundary=boundary,
        )
    assert public_path.read_bytes() == before
    assert ledger.validate_ledger_file(public_path).pair_count == 0


def test_relative_missing_and_nonempty_controller_roots_are_rejected(
    tmp_path: Path,
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()
    missing = tmp_path / "missing-controller-root"
    roots["controller-state"].joinpath("unexpected.txt").write_text(
        "not empty\n", encoding="utf-8"
    )

    for candidate in (Path("relative-controller"), missing, roots["controller-state"]):
        with pytest.raises(pair_creation.PairCreationError):
            pair_creation.create_shakedown_pair(
                project_root=project_root,
                controller_root=candidate,
                key_path=key_path,
                custody_boundary=boundary,
            )
    assert not missing.exists()
    assert public_path.read_bytes() == before


def test_symlink_or_junction_controller_alias_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()
    real_isjunction = getattr(pair_creation.os.path, "isjunction", None)

    def identify_controller_as_junction(value: object) -> bool:
        if Path(value) == roots["controller-state"]:
            return True
        return bool(real_isjunction is not None and real_isjunction(value))

    monkeypatch.setattr(pair_creation.os.path, "isjunction", identify_controller_as_junction)
    with pytest.raises(pair_creation.PairCreationError):
        _create(project_root, boundary, key_path, roots)
    assert public_path.read_bytes() == before
    assert not list(roots["controller-state"].iterdir())


def test_key_custody_or_sealing_failure_occurs_before_private_or_public_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()

    def fail_seal(*args: object, **kwargs: object) -> object:
        raise controller.ControllerStateError(controller.SEALING_FAILURE)

    monkeypatch.setattr(pair_creation.controller, "seal_controller_state", fail_seal)
    with pytest.raises(pair_creation.PairCreationError) as caught:
        _create(project_root, boundary, key_path, roots)
    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert public_path.read_bytes() == before
    assert not list(roots["controller-state"].iterdir())


def test_rng_failure_occurs_before_private_or_public_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()

    def fail_rng(length: int) -> bytes:
        raise OSError("synthetic rng failure")

    monkeypatch.setattr(pair_creation.os, "urandom", fail_rng)
    with pytest.raises(pair_creation.PairCreationError) as caught:
        _create(project_root, boundary, key_path, roots)
    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert public_path.read_bytes() == before
    assert not list(roots["controller-state"].iterdir())


def test_checkpoint_publication_failure_leaves_genesis_and_no_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(pair_creation.os, "replace", fail_replace)
    with pytest.raises(pair_creation.PairCreationError) as caught:
        _create(project_root, boundary, key_path, roots)
    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert public_path.read_bytes() == before
    assert ledger.validate_ledger_file(public_path).pair_count == 0
    assert not list(roots["controller-state"].glob("*.sealed.json"))
    assert len(list(roots["controller-state"].glob(".*.tmp"))) == 1


def test_ledger_append_failure_preserves_sealed_order_and_genesis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    before = public_path.read_bytes()

    def fail_append(path: object, event: object) -> object:
        raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)

    monkeypatch.setattr(pair_creation.ledger, "append_event", fail_append)
    with pytest.raises(ledger.LedgerError) as caught:
        _create(project_root, boundary, key_path, roots)
    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert public_path.read_bytes() == before
    assert ledger.validate_ledger_file(public_path).pair_count == 0
    assert len(list(roots["controller-state"].glob("*.sealed.json"))) == 1


def test_write_then_report_failure_is_not_retried_or_duplicated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    real_append = ledger.append_event

    def append_then_fail(path: Path | str, event: dict[str, object]):
        real_append(path, event)
        raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)

    monkeypatch.setattr(pair_creation.ledger, "append_event", append_then_fail)
    with pytest.raises(ledger.LedgerError):
        _create(project_root, boundary, key_path, roots)
    first_failure_bytes = public_path.read_bytes()
    assert ledger.validate_ledger_file(public_path).pair_count == 1

    with pytest.raises(pair_creation.PairCreationError):
        _create(project_root, boundary, key_path, roots)
    assert public_path.read_bytes() == first_failure_bytes
    assert ledger.validate_ledger_file(public_path).pair_count == 1


def test_cli_requires_explicit_write_and_emits_no_secret_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    args = [
        "--project-root",
        str(project_root),
        "--controller-root",
        str(roots["controller-state"]),
        "--key-path",
        str(key_path),
        "--consumer-root",
        str(boundary.consumer_root),
        "--materialization-root",
        str(boundary.materialization_root),
        "--execution-root",
        str(boundary.execution_root),
        "--scoring-root",
        str(boundary.scoring_root),
        "--write",
    ]
    assert pair_creation.main(args) == 0
    captured = capsys.readouterr()
    assert pair_creation.PAIR_CREATION_COMPLETE in captured.out
    assert "CONTROL" not in captured.out
    assert "TREATMENT" not in captured.out
    assert str(key_path) not in captured.out
    assert str(roots["controller-state"]) not in captured.out
    assert captured.err == ""
    assert ledger.validate_ledger_file(public_path).pair_count == 1


def test_cli_without_explicit_write_is_rejected_before_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    args = [
        "--project-root",
        str(project_root),
        "--controller-root",
        str(roots["controller-state"]),
        "--key-path",
        str(key_path),
        "--consumer-root",
        str(boundary.consumer_root),
        "--materialization-root",
        str(boundary.materialization_root),
        "--execution-root",
        str(boundary.execution_root),
        "--scoring-root",
        str(boundary.scoring_root),
    ]
    before = public_path.read_bytes()
    with pytest.raises(SystemExit) as caught:
        pair_creation.main(args)
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert "--write" in captured.err
    assert public_path.read_bytes() == before
    assert not list(roots["controller-state"].iterdir())


def test_public_surface_has_no_attempt_or_resume_capability() -> None:
    source = inspect.getsource(pair_creation)
    assert "solo_r2_lifecycle_integration" not in source
    assert "solo_r2_blind_scoring_bundle" not in source
    assert not hasattr(pair_creation, "admit_attempt")
    assert not hasattr(pair_creation, "resume")
    assert not hasattr(pair_creation, "score")
    assert not hasattr(pair_creation, "unblind")
    assert tuple(inspect.signature(pair_creation.create_shakedown_pair).parameters) == (
        "project_root",
        "controller_root",
        "key_path",
        "custody_boundary",
    )


def test_frozen_authority_values_match_committed_sources() -> None:
    qualification = (
        REPO_ROOT
        / "artifacts/evidence/solo-qualification-7-of-7-final-checkpoint-20260831/qualification-record.md"
    ).read_bytes()
    assert hashlib.sha256(qualification).hexdigest() == (
        pair_creation._FROZEN_IDENTITIES["qualification_record_sha256"]
    )
    assert pair_creation._FROZEN_IDENTITIES["protocol_sha256"] == (
        ledger.ADOPTED_PROTOCOL_SHA256
    )
    assert pair_creation._FROZEN_IDENTITIES["contract_sha256"] == (
        ledger.ADOPTED_CONTRACT_SHA256
    )
    assert pair_creation._FROZEN_IDENTITIES["schema_id"] == ledger.ADOPTED_SCHEMA_ID
    assert pair_creation._FROZEN_IDENTITIES["historical_base_commit"] == (
        "e478409971dd8e72335966350fcfaee2a6cdb8b0"
    )
    assert pair_creation._FROZEN_IDENTITIES["historical_fix_commit"] == (
        "c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b"
    )


def test_error_surface_is_fixed_and_does_not_echo_invalid_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    secret_sentinel = "SHOULD-NOT-ECHO-CONTROLLER-ROOT"
    invalid = roots["controller-state"] / secret_sentinel
    args = [
        "--project-root",
        str(project_root),
        "--controller-root",
        str(invalid),
        "--key-path",
        str(key_path),
        "--consumer-root",
        str(boundary.consumer_root),
        "--materialization-root",
        str(boundary.materialization_root),
        "--execution-root",
        str(boundary.execution_root),
        "--scoring-root",
        str(boundary.scoring_root),
        "--write",
    ]
    before = public_path.read_bytes()
    assert pair_creation.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == pair_creation.PAIR_CREATION_FAILURE
    assert secret_sentinel not in captured.err
    assert public_path.read_bytes() == before


def test_json_checkpoint_contains_no_public_pair_event_or_attempt_payload(
    tmp_path: Path,
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    result = _create(project_root, boundary, key_path, roots)
    envelope = json.loads(result.checkpoint_path.read_text(encoding="utf-8"))
    assert "PAIR_CREATED" not in envelope
    assert "attempt_handle" not in envelope
    assert "realized_order" not in envelope
    assert "order_entropy" not in envelope
    assert ledger.validate_ledger_file(public_path).initiated_attempt_count == 0


def test_owner_commitment_is_canonical_and_contains_no_mapping_or_key_material() -> None:
    encoded = pair_creation._commitment_bytes(
        evaluation_id="10000000-0000-4000-8000-000000000001",
        pair_id="20000000-0000-4000-8000-000000000002",
        sealed_package_digest="a" * 64,
        created_at_utc="2026-09-05T00:00:00Z",
    )
    assert encoded.endswith(b"\n")
    assert b"\r" not in encoded
    record = json.loads(encoded)
    assert record == {
        "authority_class": pair_creation.OWNER_COMMITMENT_AUTHORITY,
        "created_at_utc": "2026-09-05T00:00:00Z",
        "evaluation_id": "10000000-0000-4000-8000-000000000001",
        "pair_id": "20000000-0000-4000-8000-000000000002",
        "record_schema": pair_creation.OWNER_COMMITMENT_SCHEMA,
        "sealed_package_digest": "a" * 64,
        "slot": pair_creation.SHAKEDOWN_SLOT,
    }
    forbidden = {
        "key",
        "key_path",
        "realized_order",
        "order_entropy",
        "arm_identity",
        "attempt_handle",
    }
    assert forbidden.isdisjoint(record)
    assert b"CONTROL" not in encoded
    assert b"TREATMENT" not in encoded


def test_replacement_commitment_target_is_create_once_and_outside_package_root(
    tmp_path: Path,
) -> None:
    project_root, boundary, key_path, public_path, roots = _environment(tmp_path)
    commitment_root = tmp_path / "owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "commitment.json"

    private_root, target = pair_creation.validate_replacement_targets(
        controller_root=roots["controller-state"],
        key_path=key_path,
        commitment_path=commitment_path,
        custody_boundary=boundary,
    )
    assert private_root == roots["controller-state"]
    assert target == commitment_path

    commitment_path.write_bytes(b"existing\n")
    with pytest.raises(pair_creation.PairCreationError):
        pair_creation.validate_replacement_targets(
            controller_root=roots["controller-state"],
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert commitment_path.read_bytes() == b"existing\n"
    assert ledger.validate_ledger_file(public_path).pair_count == 0


def test_commitment_filesystem_probe_uses_dedicated_names_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commitment_root = tmp_path / "owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "commitment.json"
    temporary = pair_creation._commitment_temporary_path(commitment_path)
    monkeypatch.setattr(
        pair_creation,
        "_new_uuid4",
        lambda: "10000000-0000-4000-8000-000000000001",
    )
    real_link = pair_creation.os.link
    observed_links: list[tuple[Path, Path]] = []

    def observe_link(source: object, destination: object, **kwargs: object) -> None:
        observed_links.append((Path(source), Path(destination)))
        real_link(source, destination, **kwargs)

    monkeypatch.setattr(pair_creation.os, "link", observe_link)

    pair_creation._probe_commitment_filesystem_capability(commitment_path)

    assert len(observed_links) == 2
    assert all(
        source not in {commitment_path, temporary}
        and destination not in {commitment_path, temporary}
        for source, destination in observed_links
    )
    assert all(
        source.name.endswith(".capability-probe.tmp")
        and destination.name.endswith(".capability-probe")
        for source, destination in observed_links
    )
    assert not commitment_path.exists()
    assert not temporary.exists()
    assert not list(commitment_root.iterdir())


def test_commitment_filesystem_probe_requires_second_link_to_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commitment_root = tmp_path / "owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "commitment.json"
    real_link = pair_creation.os.link
    link_count = 0

    def link_without_no_clobber(*args: object, **kwargs: object) -> None:
        nonlocal link_count
        link_count += 1
        if link_count == 1:
            real_link(*args, **kwargs)

    monkeypatch.setattr(pair_creation.os, "link", link_without_no_clobber)
    with pytest.raises(pair_creation.PairCreationError) as caught:
        pair_creation._probe_commitment_filesystem_capability(commitment_path)

    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert link_count == 2
    assert not commitment_path.exists()
    assert not list(commitment_root.iterdir())


@pytest.mark.parametrize("failure", ["first-link", "read-back"])
def test_commitment_filesystem_probe_fails_closed_and_cleans_probe_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    commitment_root = tmp_path / "owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "commitment.json"
    if failure == "first-link":
        def fail_link(*_args: object, **_kwargs: object) -> None:
            raise OSError("unsupported")

        monkeypatch.setattr(
            pair_creation.os,
            "link",
            fail_link,
        )
    else:
        real_read_bytes = Path.read_bytes

        def mismatched_probe_readback(path: Path) -> bytes:
            if path.name.endswith(".capability-probe"):
                return b"mismatched\n"
            return real_read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", mismatched_probe_readback)

    with pytest.raises(pair_creation.PairCreationError) as caught:
        pair_creation._probe_commitment_filesystem_capability(commitment_path)

    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert not commitment_path.exists()
    assert not list(commitment_root.iterdir())


def test_commitment_filesystem_probe_cleanup_failure_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commitment_root = tmp_path / "owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "commitment.json"
    real_unlink = Path.unlink
    failed_once = False

    def fail_first_probe_cleanup(
        path: Path, *args: object, **kwargs: object
    ) -> None:
        nonlocal failed_once
        if path.name.endswith(".capability-probe") and not failed_once:
            failed_once = True
            raise OSError("cleanup denied")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_first_probe_cleanup)
    with pytest.raises(pair_creation.PairCreationError) as caught:
        pair_creation._probe_commitment_filesystem_capability(commitment_path)

    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert failed_once is True
    assert not commitment_path.exists()
    for residue in commitment_root.iterdir():
        real_unlink(residue)
