#!/usr/bin/env python3
"""Create the Solo R2 controller key and canonical V2 genesis, in that order.

This controller-only entrypoint accepts explicit roots and never receives or
returns raw key bytes.  It creates no Pair, order seal, Attempt, score, or
unblinding state.  Actual use requires separate owner authorization.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
from typing import Sequence
from uuid import uuid4

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_pair_creation as pair_creation


BOOTSTRAP_FAILURE = "R2_BOOTSTRAP_FAILURE / STOP"
BOOTSTRAP_PREFLIGHT_PASS = "R2_BOOTSTRAP_PREFLIGHT_PASS"
BOOTSTRAP_COMPLETE = "R2_BOOTSTRAP_COMPLETE"
REPLACEMENT_PREFLIGHT_PASS = "R2_REPLACEMENT_PREFLIGHT_PASS"
REPLACEMENT_CREATION_COMPLETE = "R2_REPLACEMENT_EVALUATION_CREATED"

REPLACEMENT_OWNER_DECISION_PATH = Path(
    "docs/governance/"
    "solo-evaluation-revision-2-replacement-owner-decision-20260905.md"
)
REPLACEMENT_OWNER_DECISION_COMMIT = (
    "b4ae9777c820a3d3ce5ed671f4ebed314f789143"
)
REPLACEMENT_OWNER_DECISION_BLOB = "74c4d74e7720ae1c57c6ade6ac8791e767721bfd"
REPLACEMENT_OWNER_DECISION_SHA256 = (
    "7e452f64a8b4983661f6481901dabd989cd07a893fdc06a6bf836b9c99439327"
)

V1_LEDGER_PATH = Path(
    "artifacts/evidence/solo-evaluation-20260831/attempt-ledger.ndjson"
)


class BootstrapError(RuntimeError):
    """Fail-closed bootstrap error carrying only one fixed public code."""

    def __init__(self, code: str = BOOTSTRAP_FAILURE) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class BootstrapResult:
    ledger_path: Path
    evaluation_id: str
    event_id: str
    genesis_sha256: str


@dataclass(frozen=True)
class ReplacementCreationResult:
    """Public identifiers only; commitment and custody locations stay private."""

    ledger_path: Path
    evaluation_id: str
    genesis_event_id: str
    genesis_sha256: str
    pair_id: str
    pair_event_id: str
    ledger_sha256: str


def _fail() -> None:
    raise BootstrapError() from None


def _path_entry_exists(path: Path) -> bool:
    try:
        return os.path.lexists(path)
    except (OSError, TypeError, ValueError):
        _fail()


def _validate_project_root(project_root: Path | str) -> Path:
    try:
        supplied = Path(project_root)
    except (TypeError, ValueError):
        _fail()
    if not supplied.is_absolute():
        _fail()
    try:
        root = supplied.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if (
        not root.is_dir()
        or not (root / "AGENTS.md").is_file()
        or not (root / "governance").is_dir()
    ):
        _fail()
    return root


def _validate_v1_predecessor(root: Path) -> None:
    predecessor = root / V1_LEDGER_PATH
    try:
        data = predecessor.read_bytes()
    except OSError:
        _fail()
    if hashlib.sha256(data).hexdigest() != ledger.V1_LEDGER_SHA256:
        _fail()


def _validate_replacement_owner_decision(root: Path) -> None:
    decision = root / REPLACEMENT_OWNER_DECISION_PATH
    try:
        data = decision.read_bytes()
    except OSError:
        _fail()
    if hashlib.sha256(data).hexdigest() != REPLACEMENT_OWNER_DECISION_SHA256:
        _fail()


def _validate_publication_target(root: Path, relative_path: Path) -> Path:
    public_path = root / relative_path
    try:
        parent = public_path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if not parent.is_dir() or root not in parent.parents:
        _fail()
    temporary = public_path.with_name(f".{public_path.name}.tmp")
    if _path_entry_exists(public_path) or _path_entry_exists(temporary):
        _fail()
    return public_path


def _validate_replacement_publication_target(root: Path) -> Path:
    """Validate the one fixed, not-yet-created replacement namespace."""

    relative_path = ledger.REPLACEMENT_PUBLIC_LEDGER_PATH
    lexical_namespace = root / relative_path.parent
    try:
        base = lexical_namespace.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if not base.is_dir() or root not in base.parents:
        _fail()
    namespace = base / lexical_namespace.name
    public_path = namespace / relative_path.name
    temporary = public_path.with_name(f".{public_path.name}.tmp")
    if (
        _path_entry_exists(namespace)
        or _path_entry_exists(public_path)
        or _path_entry_exists(temporary)
    ):
        _fail()
    return public_path


def _create_replacement_namespace(public_path: Path) -> None:
    """Create only the fixed replacement directory and verify it is empty."""

    namespace = public_path.parent
    try:
        namespace.mkdir()
        resolved = namespace.resolve(strict=True)
        if resolved != namespace or next(resolved.iterdir(), None) is not None:
            raise OSError("replacement namespace is not canonical and empty")
    except OSError:
        _fail()


def validate_bootstrap_preconditions(
    *,
    project_root: Path | str,
    key_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> Path:
    """Validate every filesystem precondition without generating or writing state."""

    root = _validate_project_root(project_root)
    if type(custody_boundary) is not controller.CustodyBoundary:
        _fail()
    try:
        governance_root = Path(custody_boundary.governance_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        _fail()
    if governance_root != root:
        _fail()

    _validate_v1_predecessor(root)
    public_path = _validate_publication_target(root, ledger.PUBLIC_LEDGER_PATH)
    controller.validate_controller_key_target(
        key_path, custody_boundary=custody_boundary
    )
    return public_path


def validate_replacement_preconditions(
    *,
    project_root: Path | str,
    controller_root: Path | str,
    key_path: Path | str,
    commitment_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> Path:
    """Validate the sole owner-authorized V1-sibling replacement without writes."""

    root = _validate_project_root(project_root)
    if type(custody_boundary) is not controller.CustodyBoundary:
        _fail()
    try:
        governance_root = Path(custody_boundary.governance_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        _fail()
    if governance_root != root:
        _fail()

    _validate_v1_predecessor(root)
    _validate_replacement_owner_decision(root)
    public_path = _validate_replacement_publication_target(root)
    controller.validate_controller_key_target(
        key_path, custody_boundary=custody_boundary
    )
    pair_creation.validate_replacement_targets(
        controller_root=controller_root,
        key_path=key_path,
        commitment_path=commitment_path,
        custody_boundary=custody_boundary,
    )
    return public_path


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def build_genesis_event(
    *, evaluation_id: str, event_id: str, timestamp_utc: str
) -> dict[str, object]:
    """Build and validate the exact adopted V2 genesis object in memory."""

    event: dict[str, object] = {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": 1,
        "event_type": "V2_GENESIS",
        "event_id": event_id,
        "timestamp_utc": timestamp_utc,
        "evaluation_id": evaluation_id,
        "predecessor_digest": ledger.V1_LEDGER_SHA256,
        "adopted_protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
        "adopted_contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
        "adopted_schema_id": ledger.ADOPTED_SCHEMA_ID,
        "legacy_pair_id": ledger.LEGACY_PAIR_ID,
        "legacy_pair_state_at_v1": "PAIR_CREATED",
        "legacy_pair_attempts_used": 0,
        "legacy_pair_disposition": "PRE_ATTEMPT_TERMINATION",
        "attempt_ceiling_total": ledger.ATTEMPT_CEILING_TOTAL,
        "attempt_ceiling_breakdown": dict(ledger.ATTEMPT_CEILING_BREAKDOWN),
    }
    ledger.validate_ledger_events([event])
    return event


def bootstrap_evaluation(
    *,
    project_root: Path | str,
    key_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> BootstrapResult:
    """Create the key first, then publish exactly one canonical genesis event."""

    public_path = validate_bootstrap_preconditions(
        project_root=project_root,
        key_path=key_path,
        custody_boundary=custody_boundary,
    )
    try:
        evaluation_id = str(uuid4())
        event_id = str(uuid4())
        timestamp_utc = _timestamp_utc()
    except Exception:
        _fail()
    genesis = build_genesis_event(
        evaluation_id=evaluation_id,
        event_id=event_id,
        timestamp_utc=timestamp_utc,
    )
    encoded = ledger.encode_event(genesis)

    controller.create_controller_key(
        key_path, custody_boundary=custody_boundary
    )
    ledger.create_genesis_ledger(public_path, genesis)
    return BootstrapResult(
        ledger_path=public_path,
        evaluation_id=evaluation_id,
        event_id=event_id,
        genesis_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def create_replacement_evaluation(
    *,
    project_root: Path | str,
    controller_root: Path | str,
    key_path: Path | str,
    commitment_path: Path | str,
    custody_boundary: controller.CustodyBoundary,
) -> ReplacementCreationResult:
    """Create exactly one owner-authorized V1-sibling evaluation and Pair.

    The fixed replacement ledger is a bounded sibling of the original V2
    evaluation under the same V1 predecessor.  The caller supplies custody
    locations, but cannot supply a namespace, evaluation identity, Pair
    identity, genesis digest or sealed-package digest.
    """

    public_path = validate_replacement_preconditions(
        project_root=project_root,
        controller_root=controller_root,
        key_path=key_path,
        commitment_path=commitment_path,
        custody_boundary=custody_boundary,
    )
    try:
        evaluation_id = str(uuid4())
        event_id = str(uuid4())
        timestamp_utc = _timestamp_utc()
    except Exception:
        _fail()
    genesis = build_genesis_event(
        evaluation_id=evaluation_id,
        event_id=event_id,
        timestamp_utc=timestamp_utc,
    )
    encoded = ledger.encode_event(genesis)
    genesis_sha256 = hashlib.sha256(encoded).hexdigest()

    controller.create_controller_key(
        key_path, custody_boundary=custody_boundary
    )
    _create_replacement_namespace(public_path)
    ledger.create_genesis_ledger(public_path, genesis)
    pair = pair_creation._create_replacement_shakedown_pair(
        project_root=project_root,
        controller_root=controller_root,
        key_path=key_path,
        commitment_path=commitment_path,
        expected_genesis_sha256=genesis_sha256,
        expected_evaluation_id=evaluation_id,
        custody_boundary=custody_boundary,
    )

    try:
        events = ledger.read_ledger(public_path)
        summary = ledger.validate_ledger_events(events)
        ledger_bytes = public_path.read_bytes()
    except (ledger.LedgerError, OSError):
        _fail()
    if (
        len(events) != 2
        or events[0] != genesis
        or events[1].get("event_type") != "PAIR_CREATED"
        or events[1].get("pair_id") != pair.pair_id
        or summary.pair_count != 1
        or summary.admitted_attempt_count != 0
        or summary.initiated_attempt_count != 0
        or summary.terminal_execution_count != 0
        or summary.scoring_record_count != 0
        or summary.unblinding_record_count != 0
        or hashlib.sha256(ledger_bytes).hexdigest() != pair.ledger_sha256
    ):
        _fail()
    return ReplacementCreationResult(
        ledger_path=public_path,
        evaluation_id=evaluation_id,
        genesis_event_id=event_id,
        genesis_sha256=genesis_sha256,
        pair_id=pair.pair_id,
        pair_event_id=pair.event_id,
        ledger_sha256=pair.ledger_sha256,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight or execute the owner-authorized Solo R2 bootstrap."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key-path", required=True)
    parser.add_argument("--replacement", action="store_true")
    parser.add_argument("--controller-root")
    parser.add_argument("--commitment-path")
    parser.add_argument("--consumer-root", required=True)
    parser.add_argument("--materialization-root", required=True)
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--scoring-root", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
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
    boundary = _boundary_from_args(args)
    try:
        if args.replacement and args.check:
            validate_replacement_preconditions(
                project_root=args.project_root,
                controller_root=args.controller_root,
                key_path=args.key_path,
                commitment_path=args.commitment_path,
                custody_boundary=boundary,
            )
            print(REPLACEMENT_PREFLIGHT_PASS)
        elif args.replacement:
            result = create_replacement_evaluation(
                project_root=args.project_root,
                controller_root=args.controller_root,
                key_path=args.key_path,
                commitment_path=args.commitment_path,
                custody_boundary=boundary,
            )
            print(
                f"{REPLACEMENT_CREATION_COMPLETE} "
                f"evaluation_id={result.evaluation_id} pair_id={result.pair_id} "
                f"ledger_sha256={result.ledger_sha256}"
            )
        elif args.check:
            validate_bootstrap_preconditions(
                project_root=args.project_root,
                key_path=args.key_path,
                custody_boundary=boundary,
            )
            print(BOOTSTRAP_PREFLIGHT_PASS)
        else:
            result = bootstrap_evaluation(
                project_root=args.project_root,
                key_path=args.key_path,
                custody_boundary=boundary,
            )
            print(f"{BOOTSTRAP_COMPLETE} genesis_sha256={result.genesis_sha256}")
    except ledger.GenesisPublicationError as exc:
        print(
            f"{exc.code} publication_state={exc.publication_state}",
            file=sys.stderr,
        )
        return 2
    except (
        BootstrapError,
        pair_creation.PairCreationError,
        controller.ControllerStateError,
        ledger.LedgerError,
    ) as exc:
        print(exc.code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
