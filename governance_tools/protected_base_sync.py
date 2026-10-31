"""Controlled replacement of a consumer's protected ``AGENTS.base.md`` (F-J).

F-7 replaces the consumer's protected ``AGENTS.base.md`` from the framework's
``baselines/repo-min/AGENTS.base.md``.  The consumer's
``.governance/baseline.yaml`` records the canonical-LF hash of that file
(``sha256.AGENTS.base.md``) and marks it protected, so replacing the file
without the hash makes the drift checker report critical right after a normal
update.  The tempting repair, ``adopt_governance --refresh``, recomputes every
hash and re-trusts whatever else changed.

This module performs the replacement as one controlled step:

1. the current ``AGENTS.base.md`` must still hash (canonical LF) to the recorded
   ``sha256.AGENTS.base.md`` -- otherwise the change is unknown and we HOLD;
2. the new content is the blob ``baselines/repo-min/AGENTS.base.md`` at the
   framework commit F-7 is updating to, and the checked-out source must equal
   that blob;
3. only the ``sha256.AGENTS.base.md`` line of ``baseline.yaml`` is rewritten in
   place; every other byte (other hashes, provenance, comments, line endings)
   is left alone.  Nothing here ever recomputes another hash.

Two files cannot be written atomically.  Before the first write a journal is
stored in the Git directory (outside the work tree) holding the original bytes
of both files.  On an in-process failure both files are restored from memory
and the journal is removed only when the restore is verified.  When a journal
survives (crash, failed restore), the next run inspects it:

* both files byte-identical to the pre-sync originals -> nothing happened;
  the journal is cleared and the step runs normally;
* both files exactly at the synced target -> the step had finished; the
  journal is cleared;
* anything else, *including* the half-done state "AGENTS.base.md already at the
  authorized source, baseline hash still old" -> HOLD.  We deliberately do not
  auto-complete that state: the run that resumes is not the run that verified
  the pre-sync hash, and F-7 must never re-establish trust on its own.  The
  journal keeps the originals for a human to restore.

Consumers without ``.governance/baseline.yaml`` keep the previous behaviour
(plain replacement) and the report says no protected-hash sync applied.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_tools.domain_contract_loader import _parse_contract_yaml
from governance_tools.protected_file_hash import (
    canonical_lf_bytes,
    compatible_worktree_hashes,
    sha256_canonical_lf_bytes,
    sha256_canonical_lf_file,
)

BASE_RELATIVE_PATH = "AGENTS.base.md"
BASELINE_RELATIVE_PATH = ".governance/baseline.yaml"
SOURCE_RELATIVE_PATH = "baselines/repo-min/AGENTS.base.md"
HASH_KEY = "sha256.AGENTS.base.md"
OVERRIDABLE_KEY = "overridable.AGENTS.base.md"
JOURNAL_NAME = "ai-governance-protected-hash-sync.json"
JOURNAL_SCHEMA = "protected_hash_sync_journal.v1"

# Statuses that must keep F-7 from claiming a full update.
BLOCKING_STATUSES = frozenset({"hold", "failed_restored", "incomplete"})

CLAIM_BOUNDARY = (
    "only the sha256.AGENTS.base.md line of .governance/baseline.yaml is synced, and "
    "only after the pre-update hash was verified; other hashes, provenance and PLAN "
    "inventory are never recomputed or re-trusted"
)

_HEX64 = re.compile(rb"^[0-9a-fA-F]{64}$")
_HASH_LINE = re.compile(
    rb"^(?P<prefix>sha256\.AGENTS\.base\.md[ \t]*:[ \t]*)(?P<value>[^ \t\r\n#]*)"
    rb"(?P<suffix>[ \t]*)(?P<eol>\r\n|\n|\r)?$"
)


class ProtectedSyncHold(Exception):
    """A precondition failed; nothing may be written."""


def _new_report(**overrides: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "item": "protected_hash_sync",
        "status": "not_applicable",
        "file": BASE_RELATIVE_PATH,
        "baseline_file": BASELINE_RELATIVE_PATH,
        "hash_key": HASH_KEY,
        "old_hash": None,
        "new_hash": None,
        "framework_commit": None,
        "protection_mode": None,
        "changed_files": [],
        "reason": "",
        "claim_boundary": CLAIM_BOUNDARY,
        "errors": [],
        "notes": [],
    }
    report.update(overrides)
    return report


def _git(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git_text(cwd: Path, args: list[str]) -> str | None:
    result = _git(cwd, args)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace").strip()


def resolve_git_dir(repo: Path) -> Path:
    value = _git_text(repo, ["rev-parse", "--git-dir"])
    if not value:
        return repo / ".git"
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def journal_path(repo: Path, git_dir: Path | None = None) -> Path:
    return (git_dir or resolve_git_dir(repo)) / JOURNAL_NAME


# --- write seams (module-level so tests can inject failures) ---------------


def _write_base_text(path: Path, text: str) -> None:
    # Same write semantics F-7 always used for this file (platform newlines);
    # the recorded hash is canonical LF, so the newline style is not trusted.
    path.write_text(text, encoding="utf-8")


def _write_baseline_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def _restore_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def _write_journal(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --- baseline.yaml line handling --------------------------------------------


def _locate_hash_line(baseline_bytes: bytes) -> tuple[int, re.Match[bytes], list[bytes]]:
    lines = baseline_bytes.splitlines(keepends=True)
    candidates: list[int] = []
    for index, line in enumerate(lines):
        stripped = line.lstrip(b"\xef\xbb\xbf").strip()
        if stripped.startswith(b"#"):
            continue
        if HASH_KEY.encode("ascii") in stripped:
            candidates.append(index)
    if not candidates:
        raise ProtectedSyncHold(
            f"{BASELINE_RELATIVE_PATH} has no {HASH_KEY} line; refusing to create one"
        )
    if len(candidates) > 1:
        raise ProtectedSyncHold(
            f"{BASELINE_RELATIVE_PATH} carries {len(candidates)} {HASH_KEY} lines "
            f"(lines {', '.join(str(i + 1) for i in candidates)}); refusing to pick one"
        )
    index = candidates[0]
    line = lines[index]
    if index == 0:
        line = line.removeprefix(b"\xef\xbb\xbf")
    match = _HASH_LINE.match(line)
    if match is None or not _HEX64.match(match.group("value")):
        raise ProtectedSyncHold(
            f"{BASELINE_RELATIVE_PATH} line {index + 1} is not a plain "
            f"'{HASH_KEY}: <64-hex>' entry; refusing to edit it"
        )
    return index, match, lines


def _replace_hash_line(baseline_bytes: bytes, new_hash: str) -> tuple[bytes, str]:
    index, match, lines = _locate_hash_line(baseline_bytes)
    bom = b"\xef\xbb\xbf" if index == 0 and lines[0].startswith(b"\xef\xbb\xbf") else b""
    lines[index] = (
        bom
        + match.group("prefix")
        + new_hash.encode("ascii")
        + match.group("suffix")
        + (match.group("eol") or b"")
    )
    return b"".join(lines), match.group("value").decode("ascii").lower()


def _recorded_hash(baseline_bytes: bytes) -> str:
    index, match, _lines = _locate_hash_line(baseline_bytes)
    recorded = match.group("value").decode("ascii").lower()
    # Cross-check with the drift checker's own parser, so we never edit a line
    # the checker does not read as the hash we think it is.
    try:
        parsed = _parse_contract_yaml(baseline_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProtectedSyncHold(
            f"{BASELINE_RELATIVE_PATH} is not parseable by the drift checker parser: {exc}"
        ) from exc
    if str(parsed.get(HASH_KEY, "")).strip().lower() != recorded:
        raise ProtectedSyncHold(
            f"{BASELINE_RELATIVE_PATH} line {index + 1} disagrees with the drift "
            f"checker's parsed {HASH_KEY}; refusing to edit it"
        )
    return recorded


def _protection_mode(baseline_bytes: bytes) -> str | None:
    try:
        parsed = _parse_contract_yaml(baseline_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    value = parsed.get(OVERRIDABLE_KEY)
    return None if value is None else str(value)


# --- source binding ----------------------------------------------------------


def _authorized_source(submodule_repo: Path, framework_commit: str) -> bytes:
    head = _git_text(submodule_repo, ["rev-parse", "HEAD"])
    if not head or head != framework_commit:
        raise ProtectedSyncHold(
            f"framework checkout HEAD {head or '<unresolved>'} is not the authorized "
            f"framework commit {framework_commit}; refusing to bind the source"
        )
    blob = _git(submodule_repo, ["cat-file", "blob", f"{framework_commit}:{SOURCE_RELATIVE_PATH}"])
    if blob.returncode != 0:
        raise ProtectedSyncHold(
            f"{SOURCE_RELATIVE_PATH} is not present at framework commit {framework_commit}"
        )
    worktree_source = submodule_repo / SOURCE_RELATIVE_PATH
    if not worktree_source.is_file():
        raise ProtectedSyncHold(f"missing source {SOURCE_RELATIVE_PATH} in framework checkout")
    if canonical_lf_bytes(worktree_source.read_bytes()) != canonical_lf_bytes(blob.stdout):
        raise ProtectedSyncHold(
            f"checked-out {SOURCE_RELATIVE_PATH} differs from the blob at framework "
            f"commit {framework_commit}; refusing an unbound source"
        )
    return blob.stdout


# --- journal -----------------------------------------------------------------


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def inspect_pending_journal(repo: Path, git_dir: Path | None = None) -> dict[str, Any] | None:
    """Resolve a journal left by an earlier interrupted sync.

    Returns ``None`` when there is no journal or it was safely cleared, and a
    HOLD report (status ``incomplete``) when the files are in any other state.
    """

    path = journal_path(repo, git_dir)
    if not path.exists():
        return None
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
        original_base = base64.b64decode(journal["original_base_b64"])
        original_baseline = base64.b64decode(journal["original_baseline_b64"])
        new_hash = str(journal["new_hash"])
        expected_baseline_sha256 = str(journal["expected_baseline_sha256"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _new_report(
            status="incomplete",
            reason=(
                f"unreadable protected-hash sync journal {path}: {exc}; an earlier sync "
                "may be incomplete, refusing to touch AGENTS.base.md or baseline.yaml"
            ),
            journal=str(path),
        )

    base = repo / BASE_RELATIVE_PATH
    baseline = repo / BASELINE_RELATIVE_PATH
    base_bytes = base.read_bytes() if base.is_file() else None
    baseline_bytes = baseline.read_bytes() if baseline.is_file() else None

    if base_bytes == original_base and baseline_bytes == original_baseline:
        path.unlink()
        return None
    if (
        base_bytes is not None
        and baseline_bytes is not None
        and sha256_canonical_lf_bytes(base_bytes) == new_hash
        and _sha256(baseline_bytes) == expected_baseline_sha256
    ):
        path.unlink()
        return None

    if base_bytes is None:
        base_state = "missing"
    elif base_bytes == original_base:
        base_state = "original"
    elif sha256_canonical_lf_bytes(base_bytes) == new_hash:
        base_state = "authorized_source"
    else:
        base_state = "unknown"
    if baseline_bytes is None:
        baseline_state = "missing"
    elif baseline_bytes == original_baseline:
        baseline_state = "original"
    elif _sha256(baseline_bytes) == expected_baseline_sha256:
        baseline_state = "synced"
    else:
        baseline_state = "unknown"
    return _new_report(
        status="incomplete",
        old_hash=journal.get("old_hash"),
        new_hash=new_hash,
        framework_commit=journal.get("framework_commit"),
        reason=(
            "an earlier protected-hash sync did not finish "
            f"(AGENTS.base.md={base_state}, baseline.yaml={baseline_state}); "
            "F-7 will not complete or re-trust it on its own. The pre-sync originals are "
            f"kept in {path}; restore both files to a verified state by hand, then remove "
            "the journal and re-run F-7"
        ),
        journal=str(path),
        incomplete_state={"agents_base": base_state, "baseline": baseline_state},
    )


# --- main entry --------------------------------------------------------------


def sync_protected_agents_base(
    repo: Path,
    submodule_repo: Path,
    *,
    framework_commit: str | None = None,
    git_dir: Path | None = None,
) -> dict[str, Any]:
    """Replace ``AGENTS.base.md`` from the authorized framework source.

    Never raises for precondition failures: they come back as a report with a
    status in :data:`BLOCKING_STATUSES`.  ``BaseException`` subclasses that are
    not ``Exception`` (e.g. ``KeyboardInterrupt``) are re-raised after the
    restore attempt.
    """

    target_base = repo / BASE_RELATIVE_PATH
    baseline = repo / BASELINE_RELATIVE_PATH
    source = submodule_repo / SOURCE_RELATIVE_PATH

    if framework_commit is None:
        framework_commit = _git_text(submodule_repo, ["rev-parse", "HEAD"])

    if not baseline.is_file():
        # Unchanged legacy behaviour: there is no recorded hash to keep in step.
        report = _new_report(
            framework_commit=framework_commit,
            reason=f"no {BASELINE_RELATIVE_PATH}; no protected-hash sync applied",
        )
        if not source.exists():
            report["errors"].append(f"missing source {SOURCE_RELATIVE_PATH}")
            return report
        text = source.read_text(encoding="utf-8")
        if not (target_base.exists() and target_base.read_text(encoding="utf-8") == text):
            target_base.parent.mkdir(parents=True, exist_ok=True)
            _write_base_text(target_base, text)
            report["changed_files"].append(BASE_RELATIVE_PATH)
        return report

    report = _new_report(framework_commit=framework_commit)
    pending = inspect_pending_journal(repo, git_dir)
    if pending is not None:
        pending["errors"].append(pending["reason"])
        return pending

    try:
        if not framework_commit:
            raise ProtectedSyncHold("framework commit could not be resolved")
        baseline_bytes = baseline.read_bytes()
        report["protection_mode"] = _protection_mode(baseline_bytes)
        recorded = _recorded_hash(baseline_bytes)
        report["old_hash"] = recorded
        if not target_base.is_file():
            raise ProtectedSyncHold(
                f"{BASE_RELATIVE_PATH} is missing while {BASELINE_RELATIVE_PATH} records "
                f"{HASH_KEY}; unknown state"
            )
        source_blob = _authorized_source(submodule_repo, framework_commit)
        new_hash = sha256_canonical_lf_bytes(source_blob)
        report["new_hash"] = new_hash
        current = sha256_canonical_lf_file(target_base)
        report["current_hash"] = current

        if current != recorded:
            if recorded in compatible_worktree_hashes(target_base):
                raise ProtectedSyncHold(
                    f"{HASH_KEY} is a legacy (non canonical-LF) hash of the current "
                    f"{BASE_RELATIVE_PATH}; the controlled step only accepts the "
                    "canonical-LF hash and will not convert it"
                )
            if current == new_hash:
                raise ProtectedSyncHold(
                    f"{BASE_RELATIVE_PATH} already equals the authorized source at "
                    f"{framework_commit} but {HASH_KEY} records {recorded}; it cannot be "
                    "proven that the recorded hash is the pre-update value (earlier "
                    "unsynced update or interrupted sync), so trust is not re-established"
                )
            raise ProtectedSyncHold(
                f"pre-existing {BASE_RELATIVE_PATH} hash mismatch: recorded={recorded} "
                f"current={current}; unknown change, refusing to overwrite it"
            )

        if current == new_hash:
            report["status"] = "verified"
            report["reason"] = (
                f"{BASE_RELATIVE_PATH} and {HASH_KEY} already match the authorized "
                f"source at {framework_commit}"
            )
            return report

        new_baseline, previous = _replace_hash_line(baseline_bytes, new_hash)
        if previous != recorded:  # pragma: no cover - same parse, defensive
            raise ProtectedSyncHold("baseline hash line changed while preparing the edit")
        original_base = target_base.read_bytes()
    except ProtectedSyncHold as exc:
        report["status"] = "hold"
        report["reason"] = str(exc)
        report["errors"].append(f"protected-hash sync HOLD: {exc}")
        return report
    except OSError as exc:
        report["status"] = "hold"
        report["reason"] = f"{type(exc).__name__}: {exc}"
        report["errors"].append(f"protected-hash sync HOLD: {report['reason']}")
        return report

    journal = journal_path(repo, git_dir)
    try:
        _write_journal(
            journal,
            {
                "schema": JOURNAL_SCHEMA,
                "file": BASE_RELATIVE_PATH,
                "baseline_file": BASELINE_RELATIVE_PATH,
                "framework_commit": framework_commit,
                "old_hash": recorded,
                "new_hash": new_hash,
                "expected_baseline_sha256": _sha256(new_baseline),
                "original_base_b64": base64.b64encode(original_base).decode("ascii"),
                "original_baseline_b64": base64.b64encode(baseline_bytes).decode("ascii"),
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except OSError as exc:
        report["status"] = "hold"
        report["reason"] = f"cannot write recovery journal {journal}: {exc}"
        report["errors"].append(f"protected-hash sync HOLD: {report['reason']}")
        return report

    new_text = canonical_lf_bytes(source_blob).decode("utf-8")
    try:
        _write_base_text(target_base, new_text)
        if sha256_canonical_lf_file(target_base) != new_hash:
            raise OSError(f"{BASE_RELATIVE_PATH} does not hash to the authorized source after write")
        _write_baseline_bytes(baseline, new_baseline)
        if baseline.read_bytes() != new_baseline:
            raise OSError(f"{BASELINE_RELATIVE_PATH} read-back differs from the single-line edit")
    except BaseException as exc:  # noqa: BLE001 - restore, then decide
        restored = _restore_originals(target_base, original_base, baseline, baseline_bytes)
        detail = f"{type(exc).__name__}: {exc}"
        if restored:
            try:
                journal.unlink()
            except OSError:
                pass
            report["status"] = "failed_restored"
            report["reason"] = (
                f"protected-hash sync failed ({detail}); AGENTS.base.md and baseline.yaml "
                "were restored to their pre-sync bytes"
            )
        else:
            report["status"] = "incomplete"
            report["journal"] = str(journal)
            report["reason"] = (
                f"protected-hash sync failed ({detail}) and the restore could not be "
                f"verified; pre-sync originals are kept in {journal}; the next run fails "
                "closed until a human restores a verified state"
            )
        report["errors"].append(f"protected-hash sync {report['status']}: {report['reason']}")
        if not isinstance(exc, Exception):
            raise
        return report

    try:
        journal.unlink()
    except OSError as exc:
        # The files are at the verified target; the next run recognises this
        # exact state from the journal and clears it.
        report["notes"].append(f"recovery journal not removed ({exc}); next run clears it")
    report["status"] = "synced"
    report["changed_files"] = [BASE_RELATIVE_PATH, BASELINE_RELATIVE_PATH]
    report["reason"] = (
        f"{BASE_RELATIVE_PATH} replaced from {SOURCE_RELATIVE_PATH} at framework commit "
        f"{framework_commit}; only {HASH_KEY} was rewritten in {BASELINE_RELATIVE_PATH}"
    )
    return report


def _restore_originals(
    target_base: Path, original_base: bytes, baseline: Path, original_baseline: bytes
) -> bool:
    ok = True
    for path, payload in ((target_base, original_base), (baseline, original_baseline)):
        try:
            if not path.exists() or path.read_bytes() != payload:
                _restore_bytes(path, payload)
            if path.read_bytes() != payload:
                ok = False
        except OSError:
            ok = False
    return ok


def format_protected_hash_sync(report: dict[str, Any] | None) -> list[str]:
    """Human lines for the dedicated report item."""

    if not report:
        return ["[protected_hash_sync]", "status=not_reported"]
    lines = [
        "[protected_hash_sync]",
        f"status={report.get('status')}",
        f"file={report.get('file')}",
        f"baseline_file={report.get('baseline_file')}",
        f"hash_key={report.get('hash_key')}",
        f"old_hash={report.get('old_hash') or '-'}",
        f"new_hash={report.get('new_hash') or '-'}",
        f"framework_commit={report.get('framework_commit') or '-'}",
        f"reason={report.get('reason') or '-'}",
        f"claim_boundary={report.get('claim_boundary')}",
    ]
    if report.get("journal"):
        lines.append(f"journal={report['journal']}")
    return lines
