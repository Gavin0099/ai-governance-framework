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


BOOTSTRAP_FAILURE = "R2_BOOTSTRAP_FAILURE / STOP"
BOOTSTRAP_PREFLIGHT_PASS = "R2_BOOTSTRAP_PREFLIGHT_PASS"
BOOTSTRAP_COMPLETE = "R2_BOOTSTRAP_COMPLETE"

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
    public_path = root / ledger.PUBLIC_LEDGER_PATH
    try:
        parent = public_path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if not parent.is_dir() or root not in parent.parents:
        _fail()
    temporary = public_path.with_name(f".{public_path.name}.tmp")
    if _path_entry_exists(public_path) or _path_entry_exists(temporary):
        _fail()
    controller.validate_controller_key_target(
        key_path, custody_boundary=custody_boundary
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight or execute the owner-authorized Solo R2 bootstrap."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key-path", required=True)
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
        if args.check:
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
        controller.ControllerStateError,
        ledger.LedgerError,
    ) as exc:
        print(exc.code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
