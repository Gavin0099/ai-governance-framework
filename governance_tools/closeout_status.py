"""Read-only closeout diagnosis. Run: python -B -m governance_tools.closeout_status.

No recovery, scheduling or notification. Lock availability does not prove a dead
process. A RECOVERABLE observation must be revalidated by the actual runner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import subprocess

from governance_tools import closeout_handoff as handoff
from governance_tools import shared_closeout_ownership as r2

_ACTIONS = {
    "BUSY": ["可能有操作正在執行；稍後重查，不要重設或接管 lock。"],
    "RECOVERABLE": ["完整證據通過檢查；可另行執行既有 exact-request recovery，執行時仍須重新驗證。"],
    "FINALIZED": ["該 request 已完成且 immutable proofs 一致；不需 recovery。"],
    "EARLY_HOLD_UNKNOWN": ["保留證據；不要 replay；不要 reset owner；交 operator 判斷。"],
    "PROOF_CONFLICT": ["證據缺失或不一致；保持現狀，不要 reset、replay 或修補 proof。"],
    "UNKNOWN": ["目前無法可靠判定；不要根據本次結果執行 recovery。"],
}


def _observe(root):
    """Detect observed filesystem movement; no writes or content reconstruction.

    This is a cooperative correctness check, not hostile-writer protection.
    Atime is deliberately excluded: reading a file can update access time.
    """
    result = {}
    for directory in (root / "artifacts" / "runtime", root / "memory"):
        if directory.exists():
            for path in [directory, *directory.rglob("*")]:
                info = path.lstat()
                result[str(path)] = (info.st_dev, info.st_ino, info.st_size,
                                     info.st_mtime_ns, info.st_ctime_ns)
    for relative in (r2.TEXT, ".gitmodules", "governance/framework.lock.json"):
        path = root / relative
        if path.exists():
            info = path.stat()
            result[str(path)] = (info.st_dev, info.st_ino, info.st_size,
                                 info.st_mtime_ns, info.st_ctime_ns)
    return result


def _presence(root, relative):
    return "present" if r2._path(root, relative).is_file() else "missing"


def _facts(lease, sid):
    root = lease.root
    facts = {"canonical": _presence(root, f"artifacts/runtime/closeouts/{sid}.json"),
             "completion": _presence(root, f"artifacts/runtime/closeout-completions/{sid}.json")}
    slot = r2._closeout_request_slot(root, sid)
    facts["request"] = "present" if slot.is_file() else "missing"
    facts["finalized"] = _presence(root, slot.parent.relative_to(root).as_posix() + "/finalized.json")
    return facts


def inspect_closeout(consumer_root: Path, session_id: str) -> dict:
    result = {"status": "UNKNOWN", "session_id": session_id, "generation": None,
              "owner": "unknown", "lock": "unknown", "evidence": {},
              "observation_only": True, "process_dead": "not_established"}
    try:
        r2._require(bool(r2._ID.fullmatch(session_id)), "INVALID_OWNER", "unsafe session")
        with r2.execution_exclusion(consumer_root, create=False) as lease:
            result["lock"] = "free_observed"
            before = _observe(lease.root)
            try:
                result["evidence"] = _facts(lease, session_id)
                slot = r2._closeout_request_slot(lease.root, session_id)
                request = handoff._read(slot) if slot.is_file() else None
                if request is not None:
                    binding = handoff._validate_request(request, lease.root)
                    handoff._require(binding["session_id"] == session_id, "REQUEST_SESSION_MISMATCH")
                # Finalized history is independent of the current owner's files.
                if request is not None and handoff._finalized_path(lease.root, request["binding"]).is_file():
                    provider = (handoff.NativeTranscriptProvider if request["schema_version"] == "1.1"
                                else handoff.FixtureTranscriptProvider)(lease.root)
                    result.update(handoff.validate_recovery_readiness(lease, request, provider))
                    result["generation"] = request["binding"]["generation"]
                else:
                    owner = r2._owner(lease)
                    if owner is not None:
                        result.update(owner=owner["state"], owner_session_id=owner["session_id"],
                                      generation=owner["generation"])
                    if owner is None or owner["session_id"] != session_id:
                        result.update(status="UNKNOWN", reason="NO_MATCHING_OWNER")
                    else:
                        area = slot.parent.relative_to(lease.root).as_posix()
                        receipt = r2._receipt_relative(owner) if owner["receipt_identity"] else None
                        result["evidence"].update(receipt=_presence(lease.root, receipt) if receipt else "missing",
                            release=_presence(lease.root, f'{r2.AREA}/releases/{owner["generation"]}.json'))
                        attempts = handoff._attempts(lease.root, request) if request else []
                        bound = [a for _, a in attempts if a["receipt_identity"] is not None]
                        for label, directory in (("checkpoint", "receipt-material"), ("ingestion_proof", "ingestion")):
                            result["evidence"][label] = (_presence(lease.root, f'{area}/{directory}/{bound[0]["attempt_id"]}.json')
                                                          if len(bound) == 1 else "unknown")
                        if request is None:
                            result.update(status="EARLY_HOLD_UNKNOWN" if owner["state"] == "HOLD" else "UNKNOWN",
                                          reason="REQUEST_MISSING")
                        else:
                            provider = (handoff.NativeTranscriptProvider if request["schema_version"] == "1.1"
                                        else handoff.FixtureTranscriptProvider)(lease.root)
                            result.update(handoff.validate_recovery_readiness(lease, request, provider))
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
                result.update(status="UNKNOWN" if isinstance(exc, (OSError, subprocess.SubprocessError)) else "PROOF_CONFLICT", reason=str(exc))
            if before != _observe(lease.root):
                result.update(status="UNKNOWN", reason="UNSTABLE")
                result.pop("recovery_kind", None)
    except FileNotFoundError:
        result.update(status="UNKNOWN", reason="LOCK_OR_ROOT_MISSING")
    except r2.OwnershipError as exc:
        result.update(status="BUSY" if exc.code == "R2_BUSY" else "UNKNOWN", reason=str(exc))
        if exc.code == "R2_BUSY":
            result["lock"] = "busy_observed"
    except (OSError, ValueError) as exc:
        result.update(status="UNKNOWN", reason=str(exc))
    result["safe_action"] = _ACTIONS[result["status"]]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--format", choices=("json", "human"), default="human")
    args = parser.parse_args(argv)
    result = inspect_closeout(args.consumer_root, args.session_id)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for field in ("status", "recovery_kind", "session_id", "generation", "owner", "lock", "reason"):
            if field in result:
                print(f"{field}: {result[field]}")
        for field, value in result["evidence"].items():
            print(f"{field}: {value}")
        print("注意：lock 可取得不代表 process 已死亡；本命令沒有執行 recovery。")
        for action in result["safe_action"]:
            print("- " + action)
    return 0 if result["status"] in {"FINALIZED", "RECOVERABLE"} else 2


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
