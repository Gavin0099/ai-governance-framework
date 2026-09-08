from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_bootstrap as bootstrap
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_pair_creation as pair_creation


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LEDGER = REPO_ROOT / ledger.PUBLIC_LEDGER_PATH
SECRET_TEST_ROOT_UNTRUSTED = "SECRET_TEST_ROOT_UNTRUSTED / STOP"


def _uuid(number: int) -> UUID:
    return UUID(int=number, version=4)


def _synthetic_environment(
    tmp_path: Path,
) -> tuple[Path, controller.CustodyBoundary, Path, Path]:
    assert REPO_ROOT.resolve() not in tmp_path.resolve().parents, SECRET_TEST_ROOT_UNTRUSTED
    project_root = tmp_path / "governance-root"
    project_root.mkdir()
    (project_root / "AGENTS.md").write_text("# synthetic root\n", encoding="utf-8")
    (project_root / "governance").mkdir()
    predecessor = project_root / bootstrap.V1_LEDGER_PATH
    predecessor.parent.mkdir(parents=True)
    predecessor.write_bytes((REPO_ROOT / bootstrap.V1_LEDGER_PATH).read_bytes())

    named_roots = {
        "consumer_root": tmp_path / "consumer",
        "materialization_root": tmp_path / "materialization",
        "execution_root": tmp_path / "execution",
        "scoring_root": tmp_path / "scoring",
    }
    for root in named_roots.values():
        root.mkdir()
    boundary = controller.CustodyBoundary(
        governance_root=project_root,
        **named_roots,
    )
    custody_root = tmp_path / "controller-custody"
    custody_root.mkdir()
    key_path = custody_root / "key.json"
    public_path = project_root / ledger.PUBLIC_LEDGER_PATH
    return project_root, boundary, key_path, public_path


def _bootstrap_args(
    project_root: Path,
    boundary: controller.CustodyBoundary,
    key_path: Path,
    mode: str,
) -> list[str]:
    return [
        "--project-root",
        str(project_root),
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
        mode,
    ]


def _replacement_environment(
    tmp_path: Path,
) -> tuple[
    Path,
    controller.CustodyBoundary,
    Path,
    Path,
    Path,
    Path,
]:
    project_root, boundary, key_path, _original_target = _synthetic_environment(
        tmp_path
    )
    decision = project_root / bootstrap.REPLACEMENT_OWNER_DECISION_PATH
    decision.parent.mkdir(parents=True, exist_ok=True)
    decision.write_bytes(
        (REPO_ROOT / bootstrap.REPLACEMENT_OWNER_DECISION_PATH).read_bytes()
    )
    replacement_ledger = project_root / ledger.REPLACEMENT_PUBLIC_LEDGER_PATH
    controller_root = tmp_path / "replacement-controller-state"
    controller_root.mkdir()
    commitment_root = tmp_path / "replacement-owner-commitment"
    commitment_root.mkdir()
    commitment_path = commitment_root / "sealed-package-commitment.json"
    return (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    )


def _replacement_args(
    project_root: Path,
    boundary: controller.CustodyBoundary,
    key_path: Path,
    controller_root: Path,
    commitment_path: Path,
    mode: str,
) -> list[str]:
    return [
        "--project-root",
        str(project_root),
        "--key-path",
        str(key_path),
        "--replacement",
        "--controller-root",
        str(controller_root),
        "--commitment-path",
        str(commitment_path),
        "--consumer-root",
        str(boundary.consumer_root),
        "--materialization-root",
        str(boundary.materialization_root),
        "--execution-root",
        str(boundary.execution_root),
        "--scoring-root",
        str(boundary.scoring_root),
        mode,
    ]


def test_preflight_is_read_only_and_requires_exact_v1_and_absent_targets(
    tmp_path: Path,
) -> None:
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)

    resolved = bootstrap.validate_bootstrap_preconditions(
        project_root=project_root,
        key_path=key_path,
        custody_boundary=boundary,
    )

    assert resolved == public_path
    assert not key_path.exists()
    assert not public_path.exists()
    assert not key_path.with_name(f".{key_path.name}.tmp").exists()
    assert not public_path.with_name(f".{public_path.name}.tmp").exists()

    (project_root / bootstrap.V1_LEDGER_PATH).write_bytes(b"mutated-v1")
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.validate_bootstrap_preconditions(
            project_root=project_root,
            key_path=key_path,
            custody_boundary=boundary,
        )
    assert caught.value.code == bootstrap.BOOTSTRAP_FAILURE
    assert not key_path.exists()
    assert not public_path.exists()


def test_bootstrap_creates_key_then_exact_genesis_without_pair_or_order_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_before = CANONICAL_LEDGER.read_bytes()
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)
    draws = iter((bytes.fromhex("11" * 16), bytes.fromhex("22" * 32)))
    identifiers = iter((_uuid(101), _uuid(102)))
    monkeypatch.setattr(controller.os, "urandom", lambda _size: next(draws))
    monkeypatch.setattr(bootstrap, "uuid4", lambda: next(identifiers))
    monkeypatch.setattr(bootstrap, "_timestamp_utc", lambda: "2026-09-01T00:00:00Z")

    result = bootstrap.bootstrap_evaluation(
        project_root=project_root,
        key_path=key_path,
        custody_boundary=boundary,
    )

    events = ledger.read_ledger(public_path)
    summary = ledger.validate_ledger_events(events)
    assert result.ledger_path == public_path
    assert result.evaluation_id == str(_uuid(101))
    assert result.event_id == str(_uuid(102))
    assert events == [
        bootstrap.build_genesis_event(
            evaluation_id=str(_uuid(101)),
            event_id=str(_uuid(102)),
            timestamp_utc="2026-09-01T00:00:00Z",
        )
    ]
    assert summary.ledger_event_count == 1
    assert summary.pair_count == 0
    assert summary.admitted_attempt_count == 0
    assert summary.initiated_attempt_count == 0
    assert summary.scoring_record_count == 0
    assert summary.unblinding_record_count == 0
    assert result.genesis_sha256
    assert json.loads(key_path.read_bytes())["key_id"] == "solo-r2-" + "11" * 16
    assert list(tmp_path.rglob("*.sealed.json")) == []
    assert list(tmp_path.rglob("*blind-scoring-bundle*")) == []
    assert CANONICAL_LEDGER.read_bytes() == canonical_before


def test_replacement_creation_is_one_bounded_v1_sibling_with_commitment(
    tmp_path: Path,
) -> None:
    original_before = CANONICAL_LEDGER.read_bytes()
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)

    result = bootstrap.create_replacement_evaluation(
        project_root=project_root,
        controller_root=controller_root,
        key_path=key_path,
        commitment_path=commitment_path,
        custody_boundary=boundary,
    )

    assert result.ledger_path == replacement_ledger
    assert replacement_ledger.parent.is_dir()
    events = ledger.read_ledger(replacement_ledger)
    summary = ledger.validate_ledger_events(events)
    assert [event["event_type"] for event in events] == [
        "V2_GENESIS",
        "PAIR_CREATED",
    ]
    assert events[0]["evaluation_id"] == result.evaluation_id
    assert events[0]["predecessor_digest"] == ledger.V1_LEDGER_SHA256
    assert events[0]["legacy_pair_id"] == ledger.LEGACY_PAIR_ID
    assert events[0]["legacy_pair_disposition"] == "PRE_ATTEMPT_TERMINATION"
    assert events[0]["attempt_ceiling_total"] == 14
    assert events[1]["pair_id"] == result.pair_id
    assert summary.pair_count == 1
    assert summary.admitted_attempt_count == 0
    assert summary.initiated_attempt_count == 0

    commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
    assert set(commitment) == {
        "record_schema",
        "evaluation_id",
        "pair_id",
        "slot",
        "sealed_package_digest",
        "created_at_utc",
        "authority_class",
    }
    assert commitment["record_schema"] == pair_creation.OWNER_COMMITMENT_SCHEMA
    assert commitment["authority_class"] == pair_creation.OWNER_COMMITMENT_AUTHORITY
    assert commitment["evaluation_id"] == result.evaluation_id
    assert commitment["pair_id"] == result.pair_id
    assert commitment["slot"] == pair_creation.SHAKEDOWN_SLOT
    checkpoint = next(controller_root.glob("*.order-frozen.sealed.json"))
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == commitment[
        "sealed_package_digest"
    ]
    assert CANONICAL_LEDGER.read_bytes() == original_before

    before = {
        "ledger": replacement_ledger.read_bytes(),
        "key": key_path.read_bytes(),
        "checkpoint": checkpoint.read_bytes(),
        "commitment": commitment_path.read_bytes(),
    }
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert replacement_ledger.read_bytes() == before["ledger"]
    assert key_path.read_bytes() == before["key"]
    assert checkpoint.read_bytes() == before["checkpoint"]
    assert commitment_path.read_bytes() == before["commitment"]
    assert CANONICAL_LEDGER.read_bytes() == original_before


@pytest.mark.parametrize("failure", ["seal", "commitment", "append"])
def test_replacement_failure_never_fabricates_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    original_before = CANONICAL_LEDGER.read_bytes()
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)

    if failure == "seal":
        def fail_seal(*args: object, **kwargs: object) -> object:
            raise controller.ControllerStateError(controller.SEALING_FAILURE)

        monkeypatch.setattr(pair_creation.controller, "seal_controller_state", fail_seal)
    elif failure == "commitment":
        def fail_commitment(path: Path, data: bytes) -> None:
            raise pair_creation.PairCreationError(
                pair_creation.CONTROLLER_ORDER_FAILURE
            )

        monkeypatch.setattr(
            pair_creation, "_atomic_create_commitment", fail_commitment
        )
    else:
        def fail_append(path: object, event: object) -> object:
            raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)

        monkeypatch.setattr(pair_creation.ledger, "append_event", fail_append)

    with pytest.raises((pair_creation.PairCreationError, ledger.LedgerError)):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )

    assert ledger.validate_ledger_file(replacement_ledger).pair_count == 0
    assert ledger.validate_ledger_file(replacement_ledger).initiated_attempt_count == 0
    assert CANONICAL_LEDGER.read_bytes() == original_before
    if failure in {"seal", "commitment"}:
        assert not commitment_path.exists()
    else:
        assert commitment_path.is_file()


def test_replacement_commitment_readback_mismatch_stops_before_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    real_unlink = Path.unlink

    def unlink_then_corrupt(path: Path, *args: object, **kwargs: object) -> None:
        real_unlink(path, *args, **kwargs)
        if path == commitment_path.with_name(f".{commitment_path.name}.tmp"):
            commitment_path.write_bytes(b"corrupt\n")

    monkeypatch.setattr(Path, "unlink", unlink_then_corrupt)
    with pytest.raises(pair_creation.PairCreationError):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert ledger.validate_ledger_file(replacement_ledger).pair_count == 0
    assert commitment_path.read_bytes() == b"corrupt\n"


def test_replacement_commitment_target_race_cannot_overwrite_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    real_link = pair_creation.os.link

    def target_appears_before_link(
        source: object,
        destination: object,
        *,
        src_dir_fd: object = None,
        dst_dir_fd: object = None,
        follow_symlinks: bool = True,
    ) -> None:
        if Path(destination) == commitment_path:
            commitment_path.write_bytes(b"independent-existing-commitment\n")
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(pair_creation.os, "link", target_appears_before_link)
    with pytest.raises(pair_creation.PairCreationError):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert ledger.validate_ledger_file(replacement_ledger).pair_count == 0
    assert commitment_path.read_bytes() == b"independent-existing-commitment\n"


def test_replacement_preflight_rejects_existing_or_invalid_custody_targets(
    tmp_path: Path,
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    original_before = CANONICAL_LEDGER.read_bytes()

    controller_root.joinpath("unexpected.txt").write_text("occupied\n", encoding="utf-8")
    with pytest.raises(pair_creation.PairCreationError):
        bootstrap.validate_replacement_preconditions(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    controller_root.joinpath("unexpected.txt").unlink()
    key_path.write_text("occupied\n", encoding="utf-8")
    with pytest.raises(controller.ControllerStateError):
        bootstrap.validate_replacement_preconditions(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert not replacement_ledger.exists()
    assert not commitment_path.exists()
    assert CANONICAL_LEDGER.read_bytes() == original_before


def test_replacement_preflight_rejects_existing_commitment_temporary_path(
    tmp_path: Path,
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    original_before = CANONICAL_LEDGER.read_bytes()
    temporary = pair_creation._commitment_temporary_path(commitment_path)
    temporary.write_bytes(b"occupied\n")

    with pytest.raises(pair_creation.PairCreationError):
        bootstrap.validate_replacement_preconditions(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )

    assert not key_path.exists()
    assert not replacement_ledger.exists()
    assert not commitment_path.exists()
    assert temporary.read_bytes() == b"occupied\n"
    assert CANONICAL_LEDGER.read_bytes() == original_before


def test_replacement_capability_probe_precedes_key_and_all_persistent_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    original_before = CANONICAL_LEDGER.read_bytes()
    key_calls = 0

    def fail_probe(_path: object) -> None:
        raise pair_creation.PairCreationError(pair_creation.CONTROLLER_ORDER_FAILURE)

    def observe_key(*_args: object, **_kwargs: object) -> str:
        nonlocal key_calls
        key_calls += 1
        return "unexpected"

    monkeypatch.setattr(
        pair_creation, "_probe_commitment_filesystem_capability", fail_probe
    )
    monkeypatch.setattr(controller, "create_controller_key", observe_key)

    with pytest.raises(pair_creation.PairCreationError) as caught:
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )

    assert caught.value.code == pair_creation.CONTROLLER_ORDER_FAILURE
    assert key_calls == 0
    assert not key_path.exists()
    assert not replacement_ledger.exists()
    assert not commitment_path.exists()
    assert not list(controller_root.iterdir())
    assert CANONICAL_LEDGER.read_bytes() == original_before


def test_replacement_authority_and_public_api_are_frozen() -> None:
    decision = (REPO_ROOT / bootstrap.REPLACEMENT_OWNER_DECISION_PATH).read_bytes()
    assert hashlib.sha256(decision).hexdigest() == (
        bootstrap.REPLACEMENT_OWNER_DECISION_SHA256
    )
    assert bootstrap.REPLACEMENT_OWNER_DECISION_COMMIT == (
        "b4ae9777c820a3d3ce5ed671f4ebed314f789143"
    )
    assert bootstrap.REPLACEMENT_OWNER_DECISION_BLOB == (
        "74c4d74e7720ae1c57c6ade6ac8791e767721bfd"
    )
    assert tuple(
        inspect.signature(bootstrap.create_replacement_evaluation).parameters
    ) == (
        "project_root",
        "controller_root",
        "key_path",
        "commitment_path",
        "custody_boundary",
    )
    signature = inspect.signature(bootstrap.create_replacement_evaluation)
    assert "evaluation_id" not in signature.parameters
    assert "genesis_sha256" not in signature.parameters
    assert "sealed_package_digest" not in signature.parameters


def test_replacement_owner_decision_tamper_fails_before_mutation(
    tmp_path: Path,
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    decision = project_root / bootstrap.REPLACEMENT_OWNER_DECISION_PATH
    decision.write_bytes(b"tampered\n")

    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert not key_path.exists()
    assert not replacement_ledger.exists()
    assert not commitment_path.exists()
    assert not list(controller_root.iterdir())


def test_replacement_genesis_publication_failure_stops_before_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)

    def fail_genesis(path: object, event: object) -> object:
        raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)

    monkeypatch.setattr(bootstrap.ledger, "create_genesis_ledger", fail_genesis)
    with pytest.raises(ledger.LedgerError):
        bootstrap.create_replacement_evaluation(
            project_root=project_root,
            controller_root=controller_root,
            key_path=key_path,
            commitment_path=commitment_path,
            custody_boundary=boundary,
        )
    assert key_path.is_file()
    assert not replacement_ledger.exists()
    assert replacement_ledger.parent.is_dir()
    assert not list(replacement_ledger.parent.iterdir())
    assert not commitment_path.exists()
    assert not list(controller_root.iterdir())


def test_replacement_cli_preflight_and_write_expose_no_custody_or_digest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (
        project_root,
        boundary,
        key_path,
        replacement_ledger,
        controller_root,
        commitment_path,
    ) = _replacement_environment(tmp_path)
    args = _replacement_args(
        project_root,
        boundary,
        key_path,
        controller_root,
        commitment_path,
        "--check",
    )
    assert bootstrap.main(args) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == bootstrap.REPLACEMENT_PREFLIGHT_PASS
    assert captured.err == ""
    assert not replacement_ledger.exists()
    assert not key_path.exists()
    assert not commitment_path.exists()

    args[-1] = "--write"
    assert bootstrap.main(args) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(bootstrap.REPLACEMENT_CREATION_COMPLETE)
    assert str(key_path) not in captured.out + captured.err
    assert str(controller_root) not in captured.out + captured.err
    assert str(commitment_path) not in captured.out + captured.err
    commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
    assert commitment["sealed_package_digest"] not in captured.out + captured.err
    assert ledger.validate_ledger_file(replacement_ledger).pair_count == 1


def test_bootstrap_api_has_no_raw_key_or_pair_order_inputs() -> None:
    parameters = inspect.signature(bootstrap.bootstrap_evaluation).parameters
    assert set(parameters) == {"project_root", "key_path", "custody_boundary"}
    assert not {
        "key",
        "key_bytes",
        "pair_id",
        "arm",
        "order_entropy",
        "realized_order",
    }.intersection(parameters)


def test_key_failure_prevents_genesis_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)

    def fail_key(*_args, **_kwargs) -> str:
        raise controller.ControllerStateError(controller.KEY_CUSTODY_FAILURE)

    monkeypatch.setattr(controller, "create_controller_key", fail_key)
    with pytest.raises(controller.ControllerStateError) as caught:
        bootstrap.bootstrap_evaluation(
            project_root=project_root,
            key_path=key_path,
            custody_boundary=boundary,
        )

    assert caught.value.code == controller.KEY_CUSTODY_FAILURE
    assert not key_path.exists()
    assert not public_path.exists()


def test_identity_generation_failure_is_fixed_and_precedes_all_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)

    def fail_identity() -> UUID:
        raise RuntimeError("secret identity generation detail")

    monkeypatch.setattr(bootstrap, "uuid4", fail_identity)
    result = bootstrap.main(_bootstrap_args(project_root, boundary, key_path, "--write"))
    captured = capsys.readouterr()

    assert result == 2
    assert captured.out == ""
    assert captured.err.strip() == bootstrap.BOOTSTRAP_FAILURE
    assert "secret identity generation detail" not in captured.err
    assert not key_path.exists()
    assert not public_path.exists()


def test_genesis_failure_preserves_orphan_key_and_never_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)
    draws = iter((bytes.fromhex("33" * 16), bytes.fromhex("44" * 32)))
    identifiers = iter((_uuid(301), _uuid(302)))
    monkeypatch.setattr(controller.os, "urandom", lambda _size: next(draws))
    monkeypatch.setattr(bootstrap, "uuid4", lambda: next(identifiers))
    calls = 0

    def fail_genesis(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)

    monkeypatch.setattr(ledger, "create_genesis_ledger", fail_genesis)
    with pytest.raises(ledger.LedgerError) as caught:
        bootstrap.bootstrap_evaluation(
            project_root=project_root,
            key_path=key_path,
            custody_boundary=boundary,
        )

    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert calls == 1
    assert key_path.is_file()
    assert json.loads(key_path.read_bytes())["key_id"] == "solo-r2-" + "33" * 16
    assert not public_path.exists()


@pytest.mark.parametrize("occupied", ["canonical", "temporary"])
def test_existing_publication_state_stops_before_key_creation(
    tmp_path: Path, occupied: str
) -> None:
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)
    target = (
        public_path
        if occupied == "canonical"
        else public_path.with_name(f".{public_path.name}.tmp")
    )
    target.write_bytes(b"preexisting")

    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.bootstrap_evaluation(
            project_root=project_root,
            key_path=key_path,
            custody_boundary=boundary,
        )

    assert caught.value.code == bootstrap.BOOTSTRAP_FAILURE
    assert target.read_bytes() == b"preexisting"
    assert not key_path.exists()


def test_cli_check_is_read_only_and_write_uses_only_synthetic_roots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_before = CANONICAL_LEDGER.read_bytes()
    project_root, boundary, key_path, public_path = _synthetic_environment(tmp_path)
    args = _bootstrap_args(project_root, boundary, key_path, "--check")
    assert bootstrap.main(args) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == bootstrap.BOOTSTRAP_PREFLIGHT_PASS
    assert captured.err == ""
    assert not key_path.exists()
    assert not public_path.exists()

    draws = iter((bytes.fromhex("55" * 16), bytes.fromhex("66" * 32)))
    identifiers = iter((_uuid(201), _uuid(202)))
    monkeypatch.setattr(controller.os, "urandom", lambda _size: next(draws))
    monkeypatch.setattr(bootstrap, "uuid4", lambda: next(identifiers))
    monkeypatch.setattr(bootstrap, "_timestamp_utc", lambda: "2026-09-01T00:00:00Z")
    args[-1] = "--write"
    assert bootstrap.main(args) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(bootstrap.BOOTSTRAP_COMPLETE)
    assert "solo-r2-" not in captured.out + captured.err
    assert key_path.is_file()
    assert ledger.validate_ledger_file(public_path).ledger_event_count == 1
    assert CANONICAL_LEDGER.read_bytes() == canonical_before
