from __future__ import annotations

import inspect
import json
from pathlib import Path
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_bootstrap as bootstrap
from governance_tools import solo_r2_controller_state as controller


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
    assert not CANONICAL_LEDGER.exists()


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
    assert not CANONICAL_LEDGER.exists()
