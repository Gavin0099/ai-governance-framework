#!/usr/bin/env python3
"""Verified archive + replacement-state cutover for ``memory/01_active_task.md``.

This turns the manual cutover recorded in commit ``f42e49d4`` (2026-10-23,
``memory/archive/active_task_20261023_124358_*``) into a reusable tool. It
keeps that cutover's four-artifact shape and the boundaries of the two
2026-08-30 findings (``docs/governance/memory-janitor-destructive-compression-
finding-20260830.md`` and ``memory-replacement-semantic-fidelity-finding-
20260830.md``):

``prepare``
    Archive the active file byte-exact and write a manifest with its hashes
    and §7.4 pressure. Active memory is not modified.
``verify``
    Check an agent-authored replacement candidate and write a mechanical
    preservation matrix. The tool never writes or shortens the candidate.
``cutover``
    Replace the active file with the candidate only when verification passes,
    the owner authorization names the candidate's SHA-256
    (``--authorized-candidate-sha256``), lines the candidate adds are accepted
    explicitly (``--accept-unreviewed-additions``), and neither the active
    file nor the candidate changed since; re-measure.
``rollback``
    Restore the archived bytes.

Verification is deliberately narrow. Every non-blank predecessor line that is
not a ``memory_record`` active-task-summary projection must appear verbatim
and in the same order in the candidate. A projection line may be left out only
when its record identity is recoverable from another memory file (a canonical
daily record, a review-log projection, or the projection history kept by the
converging writer) and it is not an endpoint of a supersession relation. Lines
the candidate adds are listed as unreviewed additions (verify reports
``PASS_WITH_UNREVIEWED_ADDITIONS``, exit 3); an added line with an unbalanced
HTML comment marker could hide retained lines and is UNRESOLVED. Any other
change is UNRESOLVED and
blocks cutover: rewriting agent-authored state still needs the manual,
independently reviewed path described in the fidelity finding.

The preservation matrix records measurement only. It is not a semantic review
and the tool never marks a replacement as reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from governance_tools import memory_record
    from governance_tools.memory_janitor import MemoryJanitor
except ImportError:  # file-path invocation: sys.path[0] is governance_tools/
    import memory_record  # type: ignore[no-redef]
    from memory_janitor import MemoryJanitor  # type: ignore[no-redef]

TOOL_ID = "governance_tools.active_task_cutover"
ACTIVE_RELATIVE = Path("memory") / "01_active_task.md"
ARCHIVE_RELATIVE = Path("memory") / "archive"
STATUS_PREPARED = "prepared"
STATUS_VERIFIED = "verified"
STATUS_VERIFICATION_FAILED = "verification_failed"
STATUS_CUTOVER_COMPLETE = "cutover_complete"
STATUS_ROLLED_BACK = "rolled_back"
RESULT_PASS = "PASS"
RESULT_PASS_WITH_ADDITIONS = "PASS_WITH_UNREVIEWED_ADDITIONS"
RESULT_FAIL = "FAIL"

_STAMP = re.compile(r"^\d{8}_\d{6}$")
_PROJECTION_LINE = re.compile(
    r"^- (.+) <!-- memory_record_projection:active-task-summary:([0-9a-f]{64}) -->$"
)
_RELATION_LINE = re.compile(
    r"^<!-- memory_runtime_supersession:active-task-summary:"
    r"([0-9a-f]{64}):([0-9a-f]{64}):([0-9a-f]{64}):([0-9a-f]{64}) -->$"
)
_DAILY_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")

MATRIX_NON_CLAIM = (
    "This matrix records mechanical measurement only: verbatim, in-order presence "
    "of every predecessor line that is not a writer projection, and independent "
    "recoverability of every removed projection. It is **not** a semantic-fidelity "
    "review and does not certify that the replacement is faithful. Lines the "
    "candidate adds are agent-authored and unreviewed."
)


class CutoverError(RuntimeError):
    """A cutover step refused to proceed; nothing in active memory was changed."""


def artifact_paths(project_root: Path, stamp: str) -> dict[str, Path]:
    if not _STAMP.fullmatch(stamp):
        raise CutoverError(f"stamp must look like YYYYMMDD_HHMMSS: {stamp!r}")
    base = project_root / ARCHIVE_RELATIVE / f"active_task_{stamp}"
    return {
        "active": project_root / ACTIVE_RELATIVE,
        "archive": base.with_name(base.name + ".md"),
        "manifest": base.with_name(base.name + "_cutover_manifest.json"),
        "candidate": base.with_name(base.name + "_replacement_candidate.md"),
        "matrix": base.with_name(base.name + "_preservation_matrix.md"),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def measure_file(path: Path) -> dict[str, object]:
    """§7.4 pressure of ``path`` using the memory janitor's own thresholds."""
    janitor = MemoryJanitor(path.parent)
    janitor.active_task_file = path
    lines, chars, status = janitor.check_hot_memory_status()
    pressure = janitor.describe_pressure(lines, chars, status)
    return {
        "status": status,
        "lines": lines,
        "chars": chars,
        "triggered_by": pressure["triggered_by"],
        "summary": pressure["summary"],
    }


def _file_identity(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "sha256": _sha256(data),
        "lf_normalized_sha256": _sha256(data.replace(b"\r\n", b"\n")),
        "bytes": len(data),
        "crlf": data.count(b"\r\n"),
        "bom": data.startswith(b"\xef\xbb\xbf"),
        "trailing_lf": data.endswith(b"\n"),
    }


def _rel(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _atomic_write(path: Path, data: bytes, *, expected_sha256: str) -> None:
    """Replace ``path`` with ``data`` only if it still hashes to ``expected_sha256``.

    The comparison runs after the temp file is durable and immediately before
    the replace, so a concurrent edit is refused rather than overwritten.
    """
    temp = path.with_name(f"{path.name}.cutover-{os.getpid()}.tmp")
    try:
        with temp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if _sha256(path.read_bytes()) != expected_sha256:
            raise CutoverError("active file changed during the write; nothing replaced")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _load_manifest(paths: dict[str, Path]) -> dict:
    if not paths["manifest"].exists():
        raise CutoverError(f"manifest not found: {paths['manifest']}; run prepare first")
    return json.loads(paths["manifest"].read_text(encoding="utf-8"))


def prepare(project_root: Path, stamp: str | None = None) -> dict:
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = artifact_paths(project_root, stamp)
    active = paths["active"]
    if not active.is_file():
        raise CutoverError(f"active-task file not found: {active}")
    for key in ("archive", "manifest"):
        if paths[key].exists():
            raise CutoverError(f"refusing to overwrite existing {key}: {paths[key]}")
    source_bytes = active.read_bytes()
    paths["archive"].parent.mkdir(parents=True, exist_ok=True)
    paths["archive"].write_bytes(source_bytes)
    archive_bytes = paths["archive"].read_bytes()
    if archive_bytes != source_bytes:
        paths["archive"].unlink()
        raise CutoverError("archive is not byte-equal to the active file; removed it")
    pressure = measure_file(active)
    manifest = {
        "schema_version": "1.0",
        "operation": "verified_archive_replacement_cutover",
        "tool": TOOL_ID,
        "precedent": "f42e49d4 (memory/archive/active_task_20261023_124358_*)",
        "authority_scope": "operational_memory_only",
        "stamp": stamp,
        "status": STATUS_PREPARED,
        "source": {
            "path": _rel(project_root, active),
            **_file_identity(active),
            "pressure": pressure,
        },
        "verified_archive": {
            "path": _rel(project_root, paths["archive"]),
            **_file_identity(paths["archive"]),
            "byte_equal_to_source": True,
        },
        "replacement_candidate": {
            "path": _rel(project_root, paths["candidate"]),
            "author": "agent",
            "written_by_tool": False,
        },
        "rollback": {
            "canonical_source": _rel(project_root, paths["archive"]),
            "expected_restored_sha256": _sha256(source_bytes),
        },
        "boundaries": {
            "automatic_compression": False,
            "semantic_review_performed": False,
            "independently_reviewed": False,
            "uses_legacy_destructive_clean": False,
            "modifies_existing_global_archive_manifest": False,
        },
    }
    _write_json(paths["manifest"], manifest)
    return manifest


def _decode_lines(data: bytes, *, label: str) -> list[str]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CutoverError(f"{label} is not strict UTF-8") from exc
    if text.startswith("﻿"):
        text = text[1:]
    return [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]


def _recoverability_anchor(project_root: Path, identity: str, payload: str) -> str | None:
    """Return a memory file, other than the active file, that keeps ``identity``."""
    memory_root = project_root / "memory"
    for daily in sorted(memory_root.glob("*.md")):
        if _DAILY_NAME.fullmatch(daily.name) and memory_record.daily_memory_contains_record_identity(
            daily_path=daily, record_identity=identity
        ):
            return f"{_rel(project_root, daily)} (canonical daily record)"
    review_log = memory_root / "04_review_log.md"
    marker = f"<!-- memory_record_projection:review-log:{identity} -->"
    if review_log.is_file() and marker in _decode_lines(
        review_log.read_bytes(), label="04_review_log.md"
    ):
        return f"{_rel(project_root, review_log)} (review-log projection)"
    history = project_root / memory_record.ACTIVE_TASK_PROJECTION_HISTORY
    if history.is_file() and payload in _decode_lines(history.read_bytes(), label="history"):
        return f"{_rel(project_root, history)} (byte-exact projection history)"
    return None


def evaluate(project_root: Path, archive_bytes: bytes, candidate_bytes: bytes) -> dict:
    """Mechanically compare a candidate with the frozen predecessor."""
    predecessor = [
        (number, line)
        for number, line in enumerate(_decode_lines(archive_bytes, label="archive"), start=1)
        if line.strip()
    ]
    candidate = [
        (number, line)
        for number, line in enumerate(_decode_lines(candidate_bytes, label="candidate"), start=1)
        if line.strip()
    ]
    candidate_texts = {line for _, line in candidate}
    relation_endpoints: set[str] = set()
    for _, line in predecessor:
        match = _RELATION_LINE.fullmatch(line)
        if match:
            relation_endpoints.update({match.group(1), match.group(3)})

    rows: list[dict] = []
    kept: list[dict] = []
    for number, line in predecessor:
        projection = _PROJECTION_LINE.fullmatch(line)
        row = {
            "line": number,
            "kind": "writer projection" if projection else "non-projection line",
            "text": line,
        }
        rows.append(row)
        if projection and line not in candidate_texts:
            identity = projection.group(2)
            anchor = _recoverability_anchor(project_root, identity, line)
            if identity in relation_endpoints:
                row.update(result="UNRESOLVED", detail="supersession relation endpoint; must be kept")
            elif anchor is None:
                row.update(result="UNRESOLVED", detail="removed projection not recoverable elsewhere")
            else:
                row.update(result="REMOVED - RECOVERABLE", detail=anchor)
            continue
        kept.append(row)

    index = 0
    matched_candidate_lines: set[int] = set()
    for row in kept:
        probe = index
        while probe < len(candidate) and candidate[probe][1] != row["text"]:
            probe += 1
        if probe < len(candidate):
            row.update(result="VERBATIM", detail=f"candidate line {candidate[probe][0]}")
            matched_candidate_lines.add(candidate[probe][0])
            index = probe + 1
        else:
            # Not consumed: later predecessor lines are still matched in order.
            row.update(result="UNRESOLVED", detail="missing, changed or out of order in candidate")

    additions = []
    for number, line in candidate:
        if number in matched_candidate_lines:
            continue
        structured = (
            "memory_record_projection:" in line or "memory_runtime_supersession:" in line
        )
        # An added line that opens or closes an HTML comment without doing both
        # can hide retained predecessor lines from a reader of the cut-over file.
        hides = line.count("<!--") != line.count("-->")
        if structured:
            result, detail = "UNRESOLVED", "candidate may not introduce writer-owned structured lines"
        elif hides:
            result, detail = "UNRESOLVED", "unbalanced HTML comment could hide retained lines"
        else:
            result, detail = "ADDED - UNREVIEWED", "agent-authored addition"
        additions.append({"line": number, "text": line, "result": result, "detail": detail})
    unresolved = [r for r in rows + additions if r["result"] == "UNRESOLVED"]
    added = sum(1 for r in additions if r["result"] == "ADDED - UNREVIEWED")
    if unresolved:
        result = RESULT_FAIL
    elif added:
        result = RESULT_PASS_WITH_ADDITIONS
    else:
        result = RESULT_PASS
    return {
        "result": result,
        "rows": rows,
        "additions": additions,
        "counts": {
            "predecessor_items": len(rows),
            "verbatim": sum(1 for r in rows if r["result"] == "VERBATIM"),
            "projections_removed_recoverable": sum(
                1 for r in rows if r["result"] == "REMOVED - RECOVERABLE"
            ),
            "added": added,
            "unresolved": len(unresolved),
        },
    }


def _cell(text: str, limit: int = 90) -> str:
    shown = text if len(text) <= limit else text[: limit - 3] + "..."
    return shown.replace("|", "\\|").replace("`", "'")


def render_matrix(manifest: dict, evaluation: dict, candidate_identity: dict) -> str:
    counts = evaluation["counts"]
    lines = [
        f"# Active-task replacement preservation matrix - {manifest['stamp']}",
        "",
        "Status: **"
        + {
            RESULT_PASS: "MECHANICALLY VERIFIED",
            RESULT_PASS_WITH_ADDITIONS: (
                f"MECHANICALLY VERIFIED WITH {counts['added']} UNREVIEWED ADDED LINES"
            ),
        }.get(evaluation["result"], "MECHANICALLY REJECTED")
        + " / NOT SEMANTICALLY REVIEWED**",
        "",
        MATRIX_NON_CLAIM,
        "",
        f"- frozen predecessor: `{manifest['verified_archive']['path']}`"
        f" (SHA-256 `{manifest['verified_archive']['sha256']}`)",
        f"- replacement candidate: `{manifest['replacement_candidate']['path']}`"
        f" (SHA-256 `{candidate_identity['sha256']}`)",
        f"- result: **{evaluation['result']}**; predecessor items {counts['predecessor_items']},"
        f" verbatim {counts['verbatim']}, projections removed and recoverable"
        f" {counts['projections_removed_recoverable']}, added {counts['added']},"
        f" unresolved {counts['unresolved']}",
        "",
        "| Predecessor line | Kind | Item | Result | Candidate location / anchor |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in evaluation["rows"]:
        lines.append(
            f"| {row['line']} | {row['kind']} | {_cell(row['text'])} | {row['result']} |"
            f" {_cell(row['detail'], 120)} |"
        )
    lines += ["", "## Lines added by the candidate", ""]
    if evaluation["additions"]:
        lines += ["| Candidate line | Item | Result | Note |", "| --- | --- | --- | --- |"]
        for row in evaluation["additions"]:
            lines.append(
                f"| {row['line']} | {_cell(row['text'])} | {row['result']} | {row['detail']} |"
            )
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def _check_frozen(paths: dict[str, Path], manifest: dict) -> bytes:
    archive_bytes = paths["archive"].read_bytes()
    if _sha256(archive_bytes) != manifest["verified_archive"]["sha256"]:
        raise CutoverError("verified archive no longer matches its manifest hash")
    return archive_bytes


def verify(project_root: Path, stamp: str) -> dict:
    paths = artifact_paths(project_root, stamp)
    manifest = _load_manifest(paths)
    if manifest["status"] in (STATUS_CUTOVER_COMPLETE, STATUS_ROLLED_BACK):
        raise CutoverError(f"manifest is already {manifest['status']}; prepare a new stamp")
    archive_bytes = _check_frozen(paths, manifest)
    if _sha256(paths["active"].read_bytes()) != manifest["source"]["sha256"]:
        raise CutoverError("active file changed since prepare; prepare a new stamp")
    if not paths["candidate"].is_file():
        raise CutoverError(
            f"replacement candidate not found: {paths['candidate']}; the agent writes it"
        )
    candidate_bytes = paths["candidate"].read_bytes()
    evaluation = evaluate(project_root, archive_bytes, candidate_bytes)
    candidate_identity = _file_identity(paths["candidate"])
    matrix_text = render_matrix(manifest, evaluation, candidate_identity)
    paths["matrix"].write_text(matrix_text, encoding="utf-8", newline="\n")
    manifest["status"] = (
        STATUS_VERIFICATION_FAILED if evaluation["result"] == RESULT_FAIL else STATUS_VERIFIED
    )
    manifest["replacement_candidate"].update(
        {
            **candidate_identity,
            "pressure": measure_file(paths["candidate"]),
            "verification": evaluation["result"],
            "added_lines": [
                {"line": r["line"], "text": r["text"]}
                for r in evaluation["additions"]
                if r["result"] == "ADDED - UNREVIEWED"
            ],
            "review_status": "unreviewed",
            "independent_review": None,
        }
    )
    manifest["preservation_matrix"] = {
        "path": _rel(project_root, paths["matrix"]),
        "sha256": _sha256(paths["matrix"].read_bytes()),
        **evaluation["counts"],
        "is_semantic_review": False,
    }
    _write_json(paths["manifest"], manifest)
    return manifest


def cutover(
    project_root: Path,
    stamp: str,
    authorization: str,
    authorized_candidate_sha256: str,
    *,
    accept_additions: bool = False,
) -> dict:
    """Cut over to the candidate the owner authorized, identified by its hash."""
    if not authorization or not authorization.strip():
        raise CutoverError("cutover needs --authorization naming the owner authorization")
    if not re.fullmatch(r"[0-9a-f]{64}", authorized_candidate_sha256 or ""):
        raise CutoverError(
            "cutover needs --authorized-candidate-sha256: the candidate SHA-256 the owner authorized"
        )
    paths = artifact_paths(project_root, stamp)
    manifest = _load_manifest(paths)
    active_sha = _sha256(paths["active"].read_bytes())
    if manifest["status"] == STATUS_CUTOVER_COMPLETE:
        if active_sha == manifest["replacement_candidate"]["sha256"]:
            manifest["noop"] = True
            return manifest
        raise CutoverError("cutover already recorded but active file differs; decide manually")
    if manifest["status"] != STATUS_VERIFIED:
        raise CutoverError(f"manifest status is {manifest['status']}; run verify until PASS")
    archive_bytes = _check_frozen(paths, manifest)
    if active_sha != manifest["source"]["sha256"]:
        raise CutoverError("active file changed since prepare; nothing replaced")
    candidate_bytes = paths["candidate"].read_bytes()
    candidate_sha = _sha256(candidate_bytes)
    if candidate_sha != manifest["replacement_candidate"]["sha256"]:
        raise CutoverError("candidate changed since verify; run verify again")
    if candidate_sha != authorized_candidate_sha256:
        raise CutoverError(
            "candidate SHA-256 differs from the authorized one; the authorization does not cover it"
        )
    verification = evaluate(project_root, archive_bytes, candidate_bytes)["result"]
    if verification == RESULT_FAIL or verification != manifest["replacement_candidate"]["verification"]:
        raise CutoverError("fresh verification no longer matches; nothing replaced")
    if verification == RESULT_PASS_WITH_ADDITIONS and not accept_additions:
        raise CutoverError(
            "candidate adds unreviewed lines (listed by verify); pass --accept-unreviewed-additions "
            "to cut over with them"
        )
    if _sha256(paths["active"].read_bytes()) != manifest["source"]["sha256"]:
        raise CutoverError("active file changed during verification; nothing replaced")
    _atomic_write(paths["active"], candidate_bytes, expected_sha256=manifest["source"]["sha256"])
    if paths["active"].read_bytes() != candidate_bytes:
        raise CutoverError("post-write active file is not byte-equal to the candidate")
    manifest["status"] = STATUS_CUTOVER_COMPLETE
    manifest["cutover"] = {
        "authorization": authorization.strip(),
        "authorized_candidate_sha256": authorized_candidate_sha256,
        "unreviewed_additions_accepted": verification == RESULT_PASS_WITH_ADDITIONS,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "active_sha256_after": _sha256(candidate_bytes),
    }
    manifest["pressure"] = {
        "before": manifest["source"]["pressure"],
        "after": measure_file(paths["active"]),
    }
    _write_json(paths["manifest"], manifest)
    manifest["noop"] = False
    return manifest


def rollback(project_root: Path, stamp: str) -> dict:
    paths = artifact_paths(project_root, stamp)
    manifest = _load_manifest(paths)
    archive_bytes = _check_frozen(paths, manifest)
    active_sha = _sha256(paths["active"].read_bytes())
    if active_sha == manifest["source"]["sha256"]:
        manifest["noop"] = True
        return manifest
    if active_sha != manifest.get("cutover", {}).get("active_sha256_after"):
        raise CutoverError("active file is neither the predecessor nor the cut-over candidate")
    _atomic_write(paths["active"], archive_bytes, expected_sha256=active_sha)
    if _sha256(paths["active"].read_bytes()) != manifest["rollback"]["expected_restored_sha256"]:
        raise CutoverError("restored active file does not match the predecessor hash")
    manifest["status"] = STATUS_ROLLED_BACK
    manifest["rolled_back_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(paths["manifest"], manifest)
    manifest["noop"] = False
    return manifest


def _print_pressure(label: str, pressure: dict) -> None:
    print(f"[active_task_cutover] {label}: {pressure['summary']}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify", "cutover", "rollback"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project-root", default=".")
        cmd.add_argument("--stamp", required=name != "prepare", default=None)
        if name == "cutover":
            cmd.add_argument("--authorization", required=True)
            cmd.add_argument("--authorized-candidate-sha256", required=True)
            cmd.add_argument("--accept-unreviewed-additions", action="store_true")
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    try:
        if args.command == "prepare":
            manifest = prepare(project_root, args.stamp)
            paths = artifact_paths(project_root, manifest["stamp"])
            _print_pressure("source", manifest["source"]["pressure"])
            print(f"[active_task_cutover] archived byte-exact: {paths['archive']}")
            print(f"[active_task_cutover] manifest: {paths['manifest']}")
            print(
                "[active_task_cutover] next: write the replacement candidate yourself at "
                f"{paths['candidate']} (keep every non-projection line verbatim and in "
                "order; drop only recoverable projections), then run verify "
                f"--stamp {manifest['stamp']}"
            )
            return 0
        if args.command == "verify":
            manifest = verify(project_root, args.stamp)
            counts = manifest["preservation_matrix"]
            _print_pressure("candidate", manifest["replacement_candidate"]["pressure"])
            print(
                f"[active_task_cutover] verification {manifest['replacement_candidate']['verification']}:"
                f" verbatim {counts['verbatim']}, projections removed and recoverable"
                f" {counts['projections_removed_recoverable']}, added {counts['added']},"
                f" unresolved {counts['unresolved']}"
            )
            print(f"[active_task_cutover] matrix (not a semantic review): {counts['path']}")
            candidate = manifest["replacement_candidate"]
            for added in candidate["added_lines"]:
                print(f"[active_task_cutover] UNREVIEWED ADDED line {added['line']}: {added['text']}")
            print(f"[active_task_cutover] candidate SHA-256: {candidate['sha256']}")
            if manifest["status"] != STATUS_VERIFIED:
                return 1
            return 3 if candidate["verification"] == RESULT_PASS_WITH_ADDITIONS else 0
        if args.command == "cutover":
            manifest = cutover(
                project_root,
                args.stamp,
                args.authorization,
                args.authorized_candidate_sha256,
                accept_additions=args.accept_unreviewed_additions,
            )
            if manifest["noop"]:
                print("[active_task_cutover] already cut over; nothing changed")
            else:
                _print_pressure("before", manifest["pressure"]["before"])
                _print_pressure("after", manifest["pressure"]["after"])
            return 0
        manifest = rollback(project_root, args.stamp)
        print(
            "[active_task_cutover] "
            + ("already the predecessor; nothing changed" if manifest["noop"] else "restored the predecessor")
        )
        return 0
    except CutoverError as exc:
        print(f"[active_task_cutover] refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
