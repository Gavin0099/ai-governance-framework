#!/usr/bin/env python3
"""Create exactly one production R2-SHAKEDOWN Pair after canonical genesis.

This entrypoint is intentionally narrower than the synthetic lifecycle
coordinator.  It requires the exact committed genesis, an existing empty
repo-external controller-state root, and the existing custodied key.  It seals
``ORDER_FROZEN`` before appending ``PAIR_CREATED`` and has no Attempt,
execution, scoring, unblinding, resume, or retry surface.

The controller-state root is supplied explicitly and is never created here.
Actual use requires a separate owner authorization for the exact operational
paths.  Importing this module or running it without ``--write`` changes no
state.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Mapping, Sequence
from uuid import UUID, uuid4

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_random_domains as random_domains


PAIR_CREATION_FAILURE = "R2_PAIR_CREATION_FAILURE / STOP"
CONTROLLER_ORDER_FAILURE = "CONTROLLER_ORDER_FAILURE / STOP"
PAIR_CREATION_COMPLETE = "R2_SHAKEDOWN_PAIR_CREATED"
OWNER_COMMITMENT_SCHEMA = "solo_r2_owner_commitment.v1"
OWNER_COMMITMENT_AUTHORITY = "OWNER_ATTESTED_CREATION_TIME_COMMITMENT"

EXPECTED_GENESIS_SHA256 = (
    "f284484a74e5efb9faa62cf09fdd065890cf27d51ee3261eba18646390bbd40c"
)
EXPECTED_EVALUATION_ID = "2fc5fd9b-9283-4d45-8c6a-ed6e2eb525e5"
SHAKEDOWN_SLOT = "R2-SHAKEDOWN"
SHAKEDOWN_CATEGORY = "shakedown/simple"
SHAKEDOWN_REPOSITORY = "Bookstore-Scraper"

_FROZEN_IDENTITIES: Mapping[str, str] = MappingProxyType({
    "protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
    "contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
    "schema_id": ledger.ADOPTED_SCHEMA_ID,
    "qualification_record_sha256": (
        "e526540ec36a7cf306a194800d698549f2580ec1ad31c1ac9543507a54e6710d"
    ),
    "historical_base_commit": "e478409971dd8e72335966350fcfaee2a6cdb8b0",
    "historical_fix_commit": "c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b",
    "oracle_blob_sha256": (
        "65e17f7a496fccdd470365bbf2b57cd2b109d50a94a94eaabc45996cd196ab38"
    ),
})


class PairCreationError(RuntimeError):
    """Fail-closed Pair creation error carrying only one fixed public code."""

    def __init__(self, code: str = PAIR_CREATION_FAILURE) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PairCreationResult:
    """Controller-side result; realized order and entropy are intentionally absent."""

    pair_id: str
    event_id: str
    checkpoint_path: Path
    sealed_package_digest: str
    ledger_sha256: str


def _fail(code: str = PAIR_CREATION_FAILURE) -> None:
    raise PairCreationError(code) from None


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _path_entry_exists(path: Path) -> bool:
    try:
        return os.path.lexists(path)
    except (OSError, TypeError, ValueError):
        _fail()


def _normalized_path(path: Path) -> str:
    try:
        return os.path.normcase(os.path.abspath(path))
    except (OSError, TypeError, ValueError):
        _fail()


def _contains_git_marker(path: Path) -> bool:
    for ancestor in (path, *path.parents):
        marker = ancestor / ".git"
        try:
            marker.stat()
        except FileNotFoundError:
            continue
        except OSError:
            _fail()
        else:
            return True
    return False


def _has_reparse_or_symlink_component(path: Path) -> bool:
    isjunction = getattr(os.path, "isjunction", None)
    for component in (path, *path.parents):
        try:
            if component.is_symlink() or (
                isjunction is not None and isjunction(component)
            ):
                return True
        except OSError:
            _fail()
    return False


def _canonical_directory(value: object, *, reject_alias: bool) -> Path:
    try:
        supplied = Path(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        _fail()
    if not supplied.is_absolute():
        _fail()
    try:
        lexical = supplied.absolute()
        resolved = supplied.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if not resolved.is_dir():
        _fail()
    if reject_alias and (
        _normalized_path(lexical) != _normalized_path(resolved)
        or _has_reparse_or_symlink_component(lexical)
    ):
        _fail()
    return resolved


def _validate_project_root(
    project_root: object, custody_boundary: controller.CustodyBoundary
) -> Path:
    root = _canonical_directory(project_root, reject_alias=False)
    if not (root / "AGENTS.md").is_file() or not (root / "governance").is_dir():
        _fail()
    if type(custody_boundary) is not controller.CustodyBoundary:
        _fail()
    governance_root = _canonical_directory(
        custody_boundary.governance_root, reject_alias=False
    )
    if governance_root != root:
        _fail()
    return root


def _resolved_boundary_roots(
    custody_boundary: controller.CustodyBoundary,
) -> tuple[Path, ...]:
    if type(custody_boundary) is not controller.CustodyBoundary:
        _fail()
    roots = tuple(
        _canonical_directory(raw, reject_alias=False)
        for raw in custody_boundary.roots()
    )
    if len(set(roots)) != len(roots):
        _fail()
    return roots


def _validate_controller_root(
    value: object,
    *,
    key_path: object,
    custody_boundary: controller.CustodyBoundary,
    key_must_exist: bool = True,
) -> Path:
    root = _canonical_directory(value, reject_alias=True)
    boundary_roots = _resolved_boundary_roots(custody_boundary)
    if any(
        _is_within(root, forbidden) or _is_within(forbidden, root)
        for forbidden in boundary_roots
    ):
        _fail()
    try:
        supplied_key = Path(key_path)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        _fail()
    if not supplied_key.is_absolute():
        _fail()
    try:
        if key_must_exist:
            resolved_key = supplied_key.resolve(strict=True)
            if not resolved_key.is_file():
                _fail()
            key_root = resolved_key.parent
        else:
            key_root = supplied_key.parent.resolve(strict=True)
            if _normalized_path(supplied_key.parent) != _normalized_path(key_root):
                _fail()
    except (OSError, RuntimeError):
        _fail()
    if _is_within(root, key_root) or _is_within(key_root, root):
        _fail()
    if _contains_git_marker(root) or not os.access(root, os.W_OK):
        _fail()
    try:
        if next(root.iterdir(), None) is not None:
            _fail()
    except OSError:
        _fail()
    return root


def _validate_commitment_target(
    value: object,
    *,
    controller_root: Path,
    custody_boundary: controller.CustodyBoundary,
) -> Path:
    try:
        supplied = Path(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        _fail()
    if not supplied.is_absolute():
        _fail()
    try:
        parent = supplied.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if (
        not parent.is_dir()
        or _normalized_path(supplied.parent) != _normalized_path(parent)
        or _has_reparse_or_symlink_component(parent)
        or _contains_git_marker(parent)
        or not os.access(parent, os.W_OK)
    ):
        _fail()
    target = parent / supplied.name
    temporary = target.with_name(f".{target.name}.tmp")
    if _path_entry_exists(target) or _path_entry_exists(temporary):
        _fail()
    boundary_roots = _resolved_boundary_roots(custody_boundary)
    if any(
        _is_within(parent, forbidden) or _is_within(forbidden, parent)
        for forbidden in boundary_roots
    ):
        _fail()
    if _is_within(parent, controller_root) or _is_within(controller_root, parent):
        _fail()
    return target


def validate_replacement_targets(
    *,
    controller_root: Path | str,
    key_path: Path | str,
    commitment_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> tuple[Path, Path]:
    """Validate replacement custody targets before key or ledger publication."""

    private_root = _validate_controller_root(
        controller_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
        key_must_exist=False,
    )
    commitment = _validate_commitment_target(
        commitment_path,
        controller_root=private_root,
        custody_boundary=custody_boundary,
    )
    return private_root, commitment


def _validate_exact_genesis_binding(
    project_root: Path,
    *,
    ledger_relpath: Path,
    expected_genesis_sha256: str,
    expected_evaluation_id: str,
) -> tuple[Path, dict[str, object]]:
    lexical = project_root / ledger_relpath
    try:
        public_path = lexical.resolve(strict=True)
        data = public_path.read_bytes()
    except (OSError, RuntimeError):
        _fail()
    if (
        _normalized_path(lexical) != _normalized_path(public_path)
        or hashlib.sha256(data).hexdigest() != expected_genesis_sha256
    ):
        _fail()
    try:
        events = ledger.read_ledger(public_path)
        summary = ledger.validate_ledger_events(events)
    except ledger.LedgerError:
        _fail()
    if (
        len(events) != 1
        or summary.ledger_event_count != 1
        or summary.pair_count != 0
        or summary.initiated_attempt_count != 0
        or summary.admitted_attempt_count != 0
        or summary.terminal_execution_count != 0
        or summary.scoring_record_count != 0
        or summary.unblinding_record_count != 0
        or summary.attempt_ceiling_total != ledger.ATTEMPT_CEILING_TOTAL
        or summary.next_event_seq != 2
    ):
        _fail()
    genesis = events[0]
    if (
        genesis.get("event_type") != "V2_GENESIS"
        or genesis.get("evaluation_id") != expected_evaluation_id
    ):
        _fail()
    return public_path, genesis


def _validate_exact_genesis(project_root: Path) -> tuple[Path, dict[str, object]]:
    return _validate_exact_genesis_binding(
        project_root,
        ledger_relpath=ledger.PUBLIC_LEDGER_PATH,
        expected_genesis_sha256=EXPECTED_GENESIS_SHA256,
        expected_evaluation_id=EXPECTED_EVALUATION_ID,
    )


def _draw_entropy32() -> bytes:
    try:
        entropy = os.urandom(random_domains.ENTROPY_BYTES)
    except Exception:
        _fail(CONTROLLER_ORDER_FAILURE)
    if type(entropy) is not bytes or len(entropy) != random_domains.ENTROPY_BYTES:
        _fail(CONTROLLER_ORDER_FAILURE)
    return entropy


def _new_uuid4() -> str:
    try:
        value = uuid4()
    except Exception:
        _fail(CONTROLLER_ORDER_FAILURE)
    if type(value) is not UUID or value.version != 4:
        _fail(CONTROLLER_ORDER_FAILURE)
    return str(value)


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _checkpoint_path(controller_root: Path, pair_id: str) -> Path:
    token = hashlib.sha256(pair_id.encode("utf-8")).hexdigest()
    return controller_root / f"{token}.order-frozen.sealed.json"


def _atomic_create_checkpoint(path: Path, data: bytes) -> None:
    if type(data) is not bytes or not data:
        _fail(CONTROLLER_ORDER_FAILURE)
    temporary = path.with_name(f".{path.name}.tmp")
    if _path_entry_exists(path) or _path_entry_exists(temporary):
        _fail(CONTROLLER_ORDER_FAILURE)
    try:
        with temporary.open("xb+", buffering=0) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write")
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read() != data:
                raise OSError("read-back mismatch")
        os.replace(temporary, path)
        if path.read_bytes() != data:
            raise OSError("published checkpoint mismatch")
    except OSError:
        _fail(CONTROLLER_ORDER_FAILURE)


def _commitment_bytes(
    *,
    evaluation_id: str,
    pair_id: str,
    sealed_package_digest: str,
    created_at_utc: str,
) -> bytes:
    record = {
        "record_schema": OWNER_COMMITMENT_SCHEMA,
        "evaluation_id": evaluation_id,
        "pair_id": pair_id,
        "slot": SHAKEDOWN_SLOT,
        "sealed_package_digest": sealed_package_digest,
        "created_at_utc": created_at_utc,
        "authority_class": OWNER_COMMITMENT_AUTHORITY,
    }
    try:
        encoded = json.dumps(
            record,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError):
        _fail(CONTROLLER_ORDER_FAILURE)
    if b"\r" in encoded or encoded.startswith(b"\xef\xbb\xbf"):
        _fail(CONTROLLER_ORDER_FAILURE)
    return encoded


def _atomic_create_commitment(path: Path, data: bytes) -> None:
    """Create, flush, no-clobber publish and verify one owner commitment."""

    if type(data) is not bytes or not data:
        _fail(CONTROLLER_ORDER_FAILURE)
    temporary = path.with_name(f".{path.name}.tmp")
    if _path_entry_exists(path) or _path_entry_exists(temporary):
        _fail(CONTROLLER_ORDER_FAILURE)
    publication_started = False
    try:
        with temporary.open("xb+", buffering=0) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write")
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read() != data:
                raise OSError("read-back mismatch")
        # A same-directory hard link makes target creation atomic and refuses
        # an existing target.  Unlike os.replace(), it cannot overwrite a
        # commitment that appears after the preflight absence check.
        os.link(temporary, path, follow_symlinks=False)
        publication_started = True
        temporary.unlink()
        if path.read_bytes() != data:
            raise OSError("published commitment mismatch")
    except OSError:
        if not publication_started:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        _fail(CONTROLLER_ORDER_FAILURE)


def _order_state(*, evaluation_id: str, pair_id: str) -> dict[str, object]:
    order_entropy = _draw_entropy32()
    try:
        realized_order = list(random_domains.arm_order_from_entropy(order_entropy))
    except random_domains.RandomDomainError:
        _fail(CONTROLLER_ORDER_FAILURE)
    return {
        "schema_version": controller.CONTROLLER_STATE_SCHEMA,
        "artifact_type": controller.CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": evaluation_id,
        "pair_id": pair_id,
        "slot": SHAKEDOWN_SLOT,
        "state_phase": controller.ORDER_FROZEN,
        "realized_order": realized_order,
        "order_entropy": base64.b64encode(order_entropy).decode("ascii"),
        "attempt_bindings": [],
        "scoring_bindings": [],
        "presentation_order": [],
        "attempt_output_refs": [],
    }


def _pair_event(*, pair_id: str) -> dict[str, object]:
    return {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": 2,
        "event_type": "PAIR_CREATED",
        "event_id": _new_uuid4(),
        "timestamp_utc": _timestamp_utc(),
        "pair_id": pair_id,
        "slot": SHAKEDOWN_SLOT,
        "category": SHAKEDOWN_CATEGORY,
        "repository": SHAKEDOWN_REPOSITORY,
        "frozen_identities": dict(_FROZEN_IDENTITIES),
    }


def _create_pair_after_validation(
    *,
    public_path: Path,
    genesis: dict[str, object],
    private_root: Path,
    key_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
    commitment_path: Path | None,
) -> PairCreationResult:
    pair_id = _new_uuid4()
    event = _pair_event(pair_id=pair_id)
    try:
        ledger.validate_ledger_events([genesis, event])
    except ledger.LedgerError:
        _fail()
    state = _order_state(
        evaluation_id=str(genesis["evaluation_id"]),
        pair_id=pair_id,
    )
    try:
        snapshot = controller.freeze_controller_state(state)
        package = controller.seal_controller_state(
            snapshot,
            key_path=key_path,
            custody_boundary=custody_boundary,
        )
    except controller.ControllerStateError:
        _fail(CONTROLLER_ORDER_FAILURE)

    checkpoint_path = _checkpoint_path(private_root, pair_id)
    _atomic_create_checkpoint(checkpoint_path, package.package_bytes)
    if commitment_path is not None:
        commitment = _commitment_bytes(
            evaluation_id=str(genesis["evaluation_id"]),
            pair_id=pair_id,
            sealed_package_digest=package.sealed_package_digest,
            created_at_utc=_timestamp_utc(),
        )
        _atomic_create_commitment(commitment_path, commitment)
    try:
        summary = ledger.append_event(public_path, event)
    except ledger.LedgerError:
        raise
    except Exception:
        _fail()

    try:
        persisted_events = ledger.read_ledger(public_path)
        persisted = ledger.validate_ledger_events(persisted_events)
        ledger_bytes = public_path.read_bytes()
    except (ledger.LedgerError, OSError):
        _fail()
    if (
        persisted != summary
        or len(persisted_events) != 2
        or persisted_events[0] != genesis
        or persisted_events[1] != event
        or persisted.pair_count != 1
        or persisted.initiated_attempt_count != 0
        or persisted.admitted_attempt_count != 0
        or persisted.terminal_execution_count != 0
        or persisted.scoring_record_count != 0
        or persisted.unblinding_record_count != 0
        or persisted.next_event_seq != 3
    ):
        _fail()
    return PairCreationResult(
        pair_id=pair_id,
        event_id=str(event["event_id"]),
        checkpoint_path=checkpoint_path,
        sealed_package_digest=package.sealed_package_digest,
        ledger_sha256=hashlib.sha256(ledger_bytes).hexdigest(),
    )


def create_shakedown_pair(
    *,
    project_root: Path | str,
    controller_root: Path | str,
    key_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> PairCreationResult:
    """Seal one new original-evaluation R2-SHAKEDOWN Pair and stop."""

    root = _validate_project_root(project_root, custody_boundary)
    public_path, genesis = _validate_exact_genesis(root)
    private_root = _validate_controller_root(
        controller_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
    )
    return _create_pair_after_validation(
        public_path=public_path,
        genesis=genesis,
        private_root=private_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
        commitment_path=None,
    )


def _create_replacement_shakedown_pair(
    *,
    project_root: Path | str,
    controller_root: Path | str,
    key_path: Path | str,
    commitment_path: Path | str,
    expected_genesis_sha256: str,
    expected_evaluation_id: str,
    custody_boundary: controller.CustodyBoundary,
) -> PairCreationResult:
    """Create the sole owner-authorized sibling Pair with durable commitment."""

    root = _validate_project_root(project_root, custody_boundary)
    public_path, genesis = _validate_exact_genesis_binding(
        root,
        ledger_relpath=ledger.REPLACEMENT_PUBLIC_LEDGER_PATH,
        expected_genesis_sha256=expected_genesis_sha256,
        expected_evaluation_id=expected_evaluation_id,
    )
    private_root = _validate_controller_root(
        controller_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
    )
    commitment = _validate_commitment_target(
        commitment_path,
        controller_root=private_root,
        custody_boundary=custody_boundary,
    )
    return _create_pair_after_validation(
        public_path=public_path,
        genesis=genesis,
        private_root=private_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
        commitment_path=commitment,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one owner-authorized Solo R2-SHAKEDOWN Pair and stop."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--controller-root", required=True)
    parser.add_argument("--key-path", required=True)
    parser.add_argument("--consumer-root", required=True)
    parser.add_argument("--materialization-root", required=True)
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--scoring-root", required=True)
    parser.add_argument("--write", action="store_true", required=True)
    return parser


def _boundary_from_args(args: argparse.Namespace) -> controller.CustodyBoundary:
    return controller.CustodyBoundary(
        governance_root=Path(args.project_root),
        consumer_root=Path(args.consumer_root),
        materialization_root=Path(args.materialization_root),
        execution_root=Path(args.execution_root),
        scoring_root=Path(args.scoring_root),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = create_shakedown_pair(
            project_root=args.project_root,
            controller_root=args.controller_root,
            key_path=args.key_path,
            custody_boundary=_boundary_from_args(args),
        )
    except (
        PairCreationError,
        controller.ControllerStateError,
        ledger.LedgerError,
        random_domains.RandomDomainError,
    ) as exc:
        print(exc.code, file=sys.stderr)
        return 2
    except Exception:
        print(PAIR_CREATION_FAILURE, file=sys.stderr)
        return 2
    print(
        f"{PAIR_CREATION_COMPLETE} pair_id={result.pair_id} "
        f"ledger_sha256={result.ledger_sha256}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
