"""One adopted disposable evaluation: committed inputs, genesis, pre-Pair gate.

No import, preflight or verifier generates an ID. The explicit creation function
requires separate owner authorization to call. It is not exposed as a CLI and
does not create a key, Pair or Attempt. Human authorization is not inferred from
an adoption record, hash or caller boolean.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_bootstrap as bootstrap
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_pair_creation as pairs
from governance_tools.solo_r2_attempt_materialization import (
    PinnedExecutable, RepositoryBinding, _run_git, verify_repository_binding,
)


class DisposableBindingError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("R2_DISPOSABLE_BINDING_FAILURE / STOP")


def _fail() -> None:
    raise DisposableBindingError() from None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=ledger._pairs_without_duplicate_keys)
    except (ValueError, UnicodeError, ledger.LedgerError):
        _fail()
    if type(value) is not dict:
        _fail()
    return value


@dataclass(frozen=True)
class ExperimentInputAuthority:
    """Exact-byte view. Re-parse into fresh objects; never expose mutable aliases."""

    raw: bytes

    def document(self) -> dict[str, Any]:
        if type(self.raw) is not bytes or _sha(self.raw) != profile.INPUT_SHA256:
            _fail()
        return _json(self.raw)

    @property
    def repository(self) -> str:
        return self.document()["base_snapshot"]["source_repository"]

    def pair_identities(self) -> dict[str, str]:
        self.document()
        return {
            "protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
            "contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
            "schema_id": profile.SCHEMA_ID,
            "input_authority_sha256": profile.INPUT_SHA256,
        }


def _root(repository: RepositoryBinding) -> Path:
    root = pairs._canonical_directory(repository.root, reject_alias=True)
    if root != profile.ROOT or repository.root != profile.ROOT:
        _fail()
    return root


def _fixed_path(root: Path, relative: Path) -> Path:
    path = root / relative
    try:
        if path.resolve(strict=False) != path or pairs._has_reparse_or_symlink_component(path):
            _fail()
        if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
            _fail()
    except (OSError, RuntimeError):
        _fail()
    return path


def load_input_authority(
    *, git: PinnedExecutable, repository: RepositoryBinding, temp_root: Path,
) -> ExperimentInputAuthority:
    """Read committed objects using the existing pinned, closed-environment Git."""
    _root(repository)
    verify_repository_binding(git, repository, temp_root=temp_root)

    def run(*args: str) -> bytes:
        return _run_git(git, repository, ("--no-replace-objects", *args), temp_root=temp_root)

    def blob(commit: str, path: str) -> bytes:
        if run("cat-file", "-t", commit).strip() != b"commit":
            _fail()
        ref = f"{commit}:{path}"
        if run("cat-file", "-t", ref).strip() != b"blob":
            _fail()
        return run("cat-file", "blob", ref)

    for commit, path, digest in profile.ADOPTED_DOCUMENTS:
        if _sha(blob(commit, path)) != digest:
            _fail()
    authority = ExperimentInputAuthority(blob(profile.INPUT_COMMIT, profile.INPUT_PATH))
    data = authority.document()
    objects = [data[k] for k in ("source_candidate", "task_prompt", "rubric", "oracle", "reference_repair", "qualification")]
    objects += [data["rubric_reuse"]["adopted_source"], *data["base_snapshot"]["files"]]
    verified: dict[str, bytes] = {}
    for obj in objects:
        raw = blob(obj.get("commit", profile.INPUT_COMMIT), obj["path"])
        oid = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if len(raw) != obj["bytes"] or _sha(raw) != obj["sha256"] or oid != obj["git_blob_oid"]:
            _fail()
        verified[obj["path"]] = raw
    snapshot = data["base_snapshot"]
    tree_ref = f"{snapshot['commit']}:{snapshot['subdirectory']}"
    if run("cat-file", "-t", tree_ref).strip() != b"tree":
        _fail()
    if run("rev-parse", "--verify", tree_ref).decode("ascii").strip() != snapshot["tree_oid"]:
        _fail()
    # Qualification bytes are pinned; its declared object bindings must agree too.
    qualification = _json(verified[data["qualification"]["path"]])
    prefix = str(Path(profile.INPUT_PATH).parent).replace("\\", "/") + "/"
    for path, raw in verified.items():
        if path.startswith(prefix) and path != data["qualification"]["path"]:
            key = path[len(prefix):]
            item = qualification["input_identities"].get(key)
            if item is not None and (item["bytes"] != len(raw) or item["sha256"] != _sha(raw)):
                _fail()
    return authority


def _existing_evaluations(root: Path) -> set[str]:
    """Original/replacement are read only, never publication targets."""
    identities = set()
    for relative in (ledger.PUBLIC_LEDGER_PATH, ledger.REPLACEMENT_PUBLIC_LEDGER_PATH):
        path = _fixed_path(root, relative)
        events = ledger.read_ledger(path)
        ledger.validate_ledger_events(events)
        if events[0]["schema_version"] != ledger.LEDGER_SCHEMA:
            _fail()
        identities.add(events[0]["evaluation_id"])
    return identities


@dataclass(frozen=True)
class DisposableCreationResult:
    evaluation_id: str
    genesis_sha256: str
    binding_sha256: str


def _binding(root: Path, event: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "binding_version": "solo_r2_disposable_genesis_binding.v1",
        "repository_root": str(root),
        "ledger_path": profile.LEDGER_PATH.as_posix(),
        "evaluation_id": event["evaluation_id"],
        "event_id": event["event_id"],
        "genesis_bytes": len(raw),
        "genesis_sha256": _sha(raw),
        "schema_id": profile.SCHEMA_ID,
        "input_authority_sha256": profile.INPUT_SHA256,
        "allocation_sha256": profile.ALLOCATION_SHA256,
        "placement_sha256": profile.PLACEMENT_SHA256,
    }


def _write_once(path: Path, raw: bytes) -> None:
    # No replace/cleanup retry: an interrupted publication reserves the allocation.
    with path.open("xb", buffering=0) as stream:
        if stream.write(raw) != len(raw):
            _fail()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        _fail()


def create_disposable_evaluation(
    *, git: PinnedExecutable, repository: RepositoryBinding, temp_root: Path,
) -> DisposableCreationResult:
    """OWNER-CREATION-ONLY: publish one genesis and its independent binding.

    This operation must never be used as a preflight. Tests use isolated roots;
    implementation/adoption authorization alone is not authorization to call it.
    """
    load_input_authority(git=git, repository=repository, temp_root=temp_root)
    root = _root(repository)
    old_ids = _existing_evaluations(root)
    public = _fixed_path(root, profile.LEDGER_PATH)
    binding_path = _fixed_path(root, profile.BINDING_PATH)
    for target in (public, binding_path):
        if os.path.lexists(target.parent) or not target.parent.parent.is_dir():
            _fail()
    # All identity/path checks precede both UUID generation and publication.
    evaluation_id, event_id = str(uuid4()), str(uuid4())
    if evaluation_id in old_ids or event_id == evaluation_id:
        _fail()
    event = bootstrap.build_genesis_event(
        evaluation_id=evaluation_id, event_id=event_id, timestamp_utc=bootstrap._timestamp_utc(),
    )
    event["schema_version"] = profile.SCHEMA
    event["adopted_schema_id"] = profile.SCHEMA_ID
    ledger.validate_ledger_events([event])
    raw = ledger.encode_event(event)
    binding_bytes = ledger.encode_event(_binding(root, event, raw))
    try:
        public.parent.mkdir()
        binding_path.parent.mkdir()
        _fixed_path(root, profile.LEDGER_PATH)
        _fixed_path(root, profile.BINDING_PATH)
        _write_once(public, raw)
        _write_once(binding_path, binding_bytes)
    except (OSError, RuntimeError):
        _fail()
    return DisposableCreationResult(evaluation_id, _sha(raw), _sha(binding_bytes))


def validate_disposable_pair_preconditions(
    *, git: PinnedExecutable, repository: RepositoryBinding, temp_root: Path,
    expected_binding_sha256: str, expected_evaluation_id: str,
) -> tuple[Path, dict[str, Any], ExperimentInputAuthority]:
    """No writes/IDs. Expected binding digest must come from later owner custody."""
    authority = load_input_authority(git=git, repository=repository, temp_root=temp_root)
    root = _root(repository)
    if not ledger._is_uuid4(expected_evaluation_id) or expected_evaluation_id in _existing_evaluations(root):
        _fail()
    public = _fixed_path(root, profile.LEDGER_PATH)
    binding_path = _fixed_path(root, profile.BINDING_PATH)
    try:
        raw = public.read_bytes()
        binding_raw = binding_path.read_bytes()
    except OSError:
        _fail()
    if _sha(binding_raw) != expected_binding_sha256:
        _fail()
    events = ledger.read_ledger(public)
    ledger.validate_ledger_events(events)
    if len(events) != 1 or events[0]["schema_version"] != profile.SCHEMA:
        _fail()
    event = events[0]
    if event["evaluation_id"] != expected_evaluation_id:
        _fail()
    if _json(binding_raw) != _binding(root, event, raw):
        _fail()
    return public, event, authority
