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


def load_cost_amendment_authority(
    *, git: PinnedExecutable, repository: RepositoryBinding, temp_root: Path,
) -> ledger.CostAmendmentAuthority:
    """Resolve only the exact committed adoption, never a worktree candidate."""
    _root(repository)
    verify_repository_binding(git, repository, temp_root=temp_root)
    values = []
    for path in (profile.COST_AMENDMENT_PATH, profile.COST_ADOPTION_PATH):
        ref = f"{profile.COST_ADOPTION_COMMIT}:{path}"
        if _run_git(git, repository, ("--no-replace-objects", "cat-file", "-t", ref),
                    temp_root=temp_root).strip() != b"blob":
            _fail()
        values.append(_run_git(git, repository, ("--no-replace-objects", "cat-file", "blob", ref),
                               temp_root=temp_root))
    authority = ledger.CostAmendmentAuthority(*values)
    authority.binding()
    return authority


def _validate_failure_cost_observations(event, evidence, prefix: bytes) -> None:
    """Verify controller observations before writing supplemental public costs.

    Exception classification/timing observations remain controller evidence,
    not facts a public ledger parser can independently observe.
    """
    from governance_tools.solo_r2_codex_runner import derive_trace_metrics

    if type(evidence) is not dict or set(evidence) != {
        "ledger_prefix_sha256", "attempt_handle", "classification", "exception_type",
        "trace_jsonl", "observed_costs", "measurement_failures", "token_components",
        "aggregation_rule", "tokens_total_omission_reason",
    }:
        _fail()
    if (evidence["ledger_prefix_sha256"] != _sha(prefix)
            or evidence["attempt_handle"] != event["attempt_handle"]
            or evidence["classification"] != "HARNESS_FAILURE"
            or type(evidence["exception_type"]) is not str
            or not evidence["exception_type"].isidentifier()):
        _fail()
    observed = evidence["observed_costs"]
    if (type(observed) is not dict or not observed.keys() <= ledger._COST_KEYS
            or any(not ledger._is_non_negative_int(v) for v in observed.values())):
        _fail()
    known = dict(observed)
    components = {}
    trace = evidence["trace_jsonl"]
    if trace is not None:
        if type(trace) is not str:
            _fail()
        metrics = derive_trace_metrics(trace.encode("utf-8"))
        if "tool_calls" in known and known["tool_calls"] != metrics.tool_call_count:
            _fail()
        known["tool_calls"] = metrics.tool_call_count
        rows = [_json(row.encode("utf-8")) for row in trace.splitlines() if row.strip()]
        usages = [row["usage"] for row in rows if row.get("type") == "turn.completed" and "usage" in row]
        if len(usages) > 1:
            _fail()
        if usages:
            components = usages[0]
            if (type(components) is not dict
                    or any(not ledger._is_non_negative_int(v) for v in components.values())):
                _fail()
    if evidence["token_components"] != components:
        _fail()
    # No aggregation rule is adopted for this profile. Never invent or infer one.
    if (evidence["aggregation_rule"] is not None or "tokens_total" in known
            or evidence["tokens_total_omission_reason"] != "NO_ADOPTED_AGGREGATION_RULE"):
        _fail()
    missing = evidence["measurement_failures"]
    if (type(missing) is not dict or not missing or not missing.keys() <= ledger._COST_KEYS
            or any(reason != ledger.MEASUREMENT_EXCEPTION for reason in missing.values())
            or missing.keys() & known.keys()):
        _fail()
    expected = {**known, **{key: ledger.UNAVAILABLE_COST for key in missing}}
    if (not ledger._REQUIRED_COST_KEYS <= expected.keys()
            or event["cost_metrics"] != expected
            or event["unavailable_cost_reasons"] != missing
            or event["terminal_classification"] != evidence["classification"]):
        _fail()


def _cost_evidence_paths(handle):
    if not ledger._is_lower_hex(handle, ledger._LOWER_HEX_64):
        _fail()
    root = pairs._canonical_directory(profile.COST_CONTROLLER_ROOT, reject_alias=True)
    if root != profile.COST_CONTROLLER_ROOT or pairs._contains_git_marker(root):
        _fail()
    attempt = pairs._canonical_directory(root / handle, reject_alias=True)
    return (_fixed_path(attempt, Path("codex-trace.jsonl")),
            _fixed_path(attempt, Path("unavailable-cost.json")))


def _verify_retained_trace(handle, evidence):
    trace_path, _ = _cost_evidence_paths(handle)
    raw = trace_path.read_bytes() if trace_path.exists() else None
    supplied = evidence.get("trace_jsonl")
    if raw is None:
        if supplied is not None:
            _fail()
    elif type(supplied) is not str or supplied.encode("utf-8") != raw:
        _fail()
    return None if raw is None else {"bytes":len(raw), "sha256":_sha(raw)}


@dataclass(frozen=True)
class RetainedFailureCostEvidence:
    """Digest of a create-once controller record; every consumer re-reads it."""
    attempt_handle: str
    sha256: str


def persist_failure_cost_evidence(event, evidence, prefix: bytes) -> RetainedFailureCostEvidence:
    """Controller-only; independently checks the actual retained trace before fsync."""
    _validate_failure_cost_observations(event, evidence, prefix)
    identity = _verify_retained_trace(event["attempt_handle"], evidence)
    _, path = _cost_evidence_paths(event["attempt_handle"])
    raw = json.dumps({"observations":evidence, "trace_identity":identity},
                     sort_keys=True, ensure_ascii=True).encode()+b"\n"
    _write_once(path, raw)
    receipt = RetainedFailureCostEvidence(event["attempt_handle"], _sha(raw))
    validate_failure_cost_evidence(event, receipt, prefix)
    return receipt


def validate_failure_cost_evidence(event, receipt, prefix: bytes) -> None:
    if (type(receipt) is not RetainedFailureCostEvidence
            or receipt.attempt_handle != event["attempt_handle"]):
        _fail()
    _, path = _cost_evidence_paths(receipt.attempt_handle)
    raw = path.read_bytes()
    if _sha(raw) != receipt.sha256:
        _fail()
    record = _json(raw)
    if set(record) != {"observations", "trace_identity"}:
        _fail()
    _validate_failure_cost_observations(event, record["observations"], prefix)
    if _verify_retained_trace(receipt.attempt_handle, record["observations"]) != record["trace_identity"]:
        _fail()


def available_cost_total(cost_rows, metric):
    """Scalar cost reduction: absent optional aggregates propagate UNAVAILABLE."""
    if metric not in ledger._COST_KEYS:
        _fail()
    values = [row.get(metric, ledger.UNAVAILABLE_COST) for row in cost_rows]
    if not values or ledger.UNAVAILABLE_COST in values:
        return ledger.UNAVAILABLE_COST
    if any(not ledger._is_non_negative_int(value) for value in values):
        _fail()
    return sum(values)


@dataclass(frozen=True)
class DisposableCreationResult:
    evaluation_id: str
    genesis_sha256: str
    binding_sha256: str


def _binding(root: Path, event: dict[str, Any], raw: bytes, *, replacement=False, final=False) -> dict[str, Any]:
    return {
        "binding_version": "solo_r2_disposable_genesis_binding.v1",
        "repository_root": str(root),
        "ledger_path": (profile.FINAL_LEDGER_PATH if final else profile.REPLACEMENT_LEDGER_PATH if replacement else profile.LEDGER_PATH).as_posix(),
        "evaluation_id": event["evaluation_id"],
        "event_id": event["event_id"],
        "genesis_bytes": len(raw),
        "genesis_sha256": _sha(raw),
        "schema_id": profile.SCHEMA_ID,
        "input_authority_sha256": profile.INPUT_SHA256,
        "allocation_sha256": profile.FINAL_DECISION_SHA256 if final else profile.REPLACEMENT_DECISION_SHA256 if replacement else profile.ALLOCATION_SHA256,
        "placement_sha256": profile.FINAL_DECISION_SHA256 if final else profile.REPLACEMENT_DECISION_SHA256 if replacement else profile.PLACEMENT_SHA256,
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
    return _create_evaluation(git=git, repository=repository, temp_root=temp_root)


def _create_evaluation(*, git, repository, temp_root, replacement_authority=None, final_authority=None):
    load_input_authority(git=git, repository=repository, temp_root=temp_root)
    root = _root(repository)
    old_ids = _existing_evaluations(root)
    replacement = replacement_authority is not None
    final = final_authority is not None
    if final:
        if replacement:
            _fail()
        _require_final_authority(final_authority)
        old_ids.update(_final_historical_evaluations(root))
    if replacement:
        _require_replacement_authority(replacement_authority)
        old_ids.add(_failed_evaluation(root))
    public_rel = profile.FINAL_LEDGER_PATH if final else profile.REPLACEMENT_LEDGER_PATH if replacement else profile.LEDGER_PATH
    binding_rel = profile.FINAL_BINDING_PATH if final else profile.REPLACEMENT_BINDING_PATH if replacement else profile.BINDING_PATH
    public = _fixed_path(root, public_rel)
    binding_path = _fixed_path(root, binding_rel)
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
    binding_bytes = ledger.encode_event(_binding(root, event, raw, replacement=replacement, final=final))
    try:
        public.parent.mkdir()
        binding_path.parent.mkdir()
        _fixed_path(root, public_rel)
        _fixed_path(root, binding_rel)
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


@dataclass(frozen=True)
class ReplacementAuthority:
    """Committed exact decision/adoptions; no creation or execution permission."""

    documents: tuple[bytes, ...]

    def verify(self):
        if type(self.documents) is not tuple or len(self.documents) != len(profile.REPLACEMENT_DOCUMENTS):
            _fail()
        for raw, (_, _, digest) in zip(self.documents, profile.REPLACEMENT_DOCUMENTS):
            if type(raw) is not bytes or _sha(raw) != digest:
                _fail()


def _require_replacement_authority(authority):
    if type(authority) is not ReplacementAuthority:
        _fail()
    authority.verify()


def load_replacement_authority(*, git, repository, temp_root) -> ReplacementAuthority:
    _root(repository)
    verify_repository_binding(git, repository, temp_root=temp_root)
    documents = []
    for commit, path, _ in profile.REPLACEMENT_DOCUMENTS:
        ref = f"{commit}:{path}"
        if _run_git(git, repository, ("--no-replace-objects", "cat-file", "-t", ref),
                    temp_root=temp_root).strip() != b"blob":
            _fail()
        documents.append(_run_git(git, repository, ("--no-replace-objects", "cat-file", "blob", ref),
                                  temp_root=temp_root))
    result = ReplacementAuthority(tuple(documents))
    result.verify()
    return result


def _failed_evaluation(root):
    # Exact historical bytes suffice for collision/isolation. Do not transfer
    # the old cost-extension authority into a new evaluation's validation.
    raw = _fixed_path(root, profile.LEDGER_PATH).read_bytes()
    if _sha(raw) != profile.FAILED_LEDGER_SHA256:
        _fail()
    return _json(raw.splitlines()[0])["evaluation_id"]


@dataclass(frozen=True)
class ReplacementLedgerBinding:
    """Externally expected genesis identity, carried unchanged to each append."""

    authority: ReplacementAuthority
    raw: bytes
    evaluation_id: str
    genesis: bytes
    input_authority: ExperimentInputAuthority

    def verify(self, path, prefix):
        final = type(self) is FinalLedgerBinding
        if final:
            _require_final_authority(self.authority)
        elif type(self) is ReplacementLedgerBinding:
            _require_replacement_authority(self.authority)
        else:
            _fail()
        if type(self.input_authority) is not ExperimentInputAuthority:
            _fail()
        self.input_authority.document()
        root = profile.ROOT
        if Path(path) != _fixed_path(root, self.ledger_relative_path):
            _fail()
        if type(self.raw) is not bytes or type(self.genesis) is not bytes:
            _fail()
        if not ledger._is_uuid4(self.evaluation_id):
            _fail()
        if self.evaluation_id in (_existing_evaluations(root) | (_final_historical_evaluations(root) if final else {_failed_evaluation(root)})):
            _fail()
        if not prefix or prefix.splitlines(keepends=True)[0] != self.genesis:
            _fail()
        event = _json(self.genesis)
        ledger.validate_ledger_events([event])
        if event['schema_version'] != profile.SCHEMA or event['evaluation_id'] != self.evaluation_id:
            _fail()
        actual = _fixed_path(root, self.binding_relative_path).read_bytes()
        if actual != self.raw or _json(self.raw) != _binding(root, event, self.genesis, replacement=not final, final=final):
            _fail()

    @property
    def ledger_relative_path(self):
        if type(self) is FinalLedgerBinding:
            return profile.FINAL_LEDGER_PATH
        if type(self) is ReplacementLedgerBinding:
            return profile.REPLACEMENT_LEDGER_PATH
        _fail()

    @property
    def binding_relative_path(self):
        if type(self) is FinalLedgerBinding:
            return profile.FINAL_BINDING_PATH
        if type(self) is ReplacementLedgerBinding:
            return profile.REPLACEMENT_BINDING_PATH
        _fail()

    def verify_append(self, path, prefix, event):
        self.verify(path, prefix)
        existing = [_json(line) for line in prefix.splitlines()]
        if type(self) is FinalLedgerBinding and event.get('pair_id') in _final_historical_pairs(profile.ROOT):
            _fail()
        # Other slots in the shared schema are not part of this allocation.
        if any(e.get('slot') != 'R2-SHAKEDOWN' for e in [*existing[1:], event]):
            _fail()
        if any(ledger._COST_EXTENSION_KEYS & e.keys() for e in [*existing, event]):
            _fail()
        for item in [*existing[1:], event]:
            if item.get('event_type') == 'PAIR_CREATED' and (
                item.get('repository') != self.input_authority.repository
                or item.get('frozen_identities') != self.input_authority.pair_identities()
            ):
                _fail()


def create_replacement_disposable_evaluation(*, git, repository, temp_root):
    """OWNER-CREATION-ONLY. No CLI or automatic allocation from an adoption."""
    authority = load_replacement_authority(git=git, repository=repository, temp_root=temp_root)
    return _create_evaluation(git=git, repository=repository, temp_root=temp_root,
                              replacement_authority=authority)


def load_replacement_ledger_binding(*, git, repository, temp_root,
                                    expected_binding_sha256, expected_evaluation_id):
    """Read-only; expected digest/ID must come from creation owner custody."""
    authority = load_replacement_authority(git=git, repository=repository, temp_root=temp_root)
    inputs = load_input_authority(git=git, repository=repository, temp_root=temp_root)
    root = _root(repository)
    public = _fixed_path(root, profile.REPLACEMENT_LEDGER_PATH)
    raw = _fixed_path(root, profile.REPLACEMENT_BINDING_PATH).read_bytes()
    if _sha(raw) != expected_binding_sha256:
        _fail()
    prefix = public.read_bytes()
    if not prefix:
        _fail()
    bound = ReplacementLedgerBinding(authority, raw, expected_evaluation_id,
                                      prefix.splitlines(keepends=True)[0], inputs)
    bound.verify(public, prefix)
    ledger.validate_ledger_events(ledger.read_ledger(public))
    return bound


def verify_replacement_custody(*, controller_root, key_path, custody_boundary,
                               commitment_path=None):
    _verify_fixed_custody(profile.REPLACEMENT_RUNTIME_ROOT, controller_root=controller_root,
        key_path=key_path, custody_boundary=custody_boundary, commitment_path=commitment_path)


def _verify_fixed_custody(base, *, controller_root, key_path, custody_boundary, commitment_path=None):
    expected = [(Path(controller_root), base / 'controller'),
                (Path(key_path), base / 'keys/controller-key.json'),
                (custody_boundary.governance_root, profile.ROOT)]
    for name in ('consumer', 'materialization', 'execution', 'scoring'):
        expected.append((getattr(custody_boundary, name + '_root'), base / name))
    if commitment_path is not None:
        expected.append((Path(commitment_path), base / 'commitments/sealed-package-digest.commitment'))
    for actual, fixed in expected:
        if actual != fixed or actual.resolve(strict=False) != fixed or pairs._has_reparse_or_symlink_component(actual):
            _fail()


@dataclass(frozen=True)
class FinalAuthority:
    """Only the exact committed final allocation and owner adoption."""
    documents: tuple[bytes, ...]

    def verify(self):
        if type(self.documents) is not tuple or len(self.documents) != len(profile.FINAL_DOCUMENTS):
            _fail()
        for raw, (_, _, digest) in zip(self.documents, profile.FINAL_DOCUMENTS):
            if type(raw) is not bytes or _sha(raw) != digest:
                _fail()


def _require_final_authority(authority):
    if type(authority) is not FinalAuthority:
        _fail()
    authority.verify()


def load_final_authority(*, git, repository, temp_root):
    _root(repository)
    verify_repository_binding(git, repository, temp_root=temp_root)
    documents = []
    for commit, path, _ in profile.FINAL_DOCUMENTS:
        ref = f"{commit}:{path}"
        if _run_git(git, repository, ("--no-replace-objects", "cat-file", "-t", ref),
                    temp_root=temp_root).strip() != b"blob":
            _fail()
        documents.append(_run_git(git, repository, ("--no-replace-objects", "cat-file", "blob", ref),
                                  temp_root=temp_root))
    authority = FinalAuthority(tuple(documents))
    _require_final_authority(authority)
    return authority


def _final_historical_evaluations(root):
    first = _failed_evaluation(root)
    raw = _fixed_path(root, profile.REPLACEMENT_LEDGER_PATH).read_bytes()
    if _sha(raw) != profile.FINAL_PRIOR_LEDGER_SHA256:
        _fail()
    return {first, _json(raw.splitlines()[0])["evaluation_id"]}


@dataclass(frozen=True)
class FinalLedgerBinding(ReplacementLedgerBinding):
    authority: FinalAuthority


def create_final_disposable_evaluation(*, git, repository, temp_root):
    """OWNER-CREATION-ONLY: one final allocation; never run as preflight."""
    authority = load_final_authority(git=git, repository=repository, temp_root=temp_root)
    return _create_evaluation(git=git, repository=repository, temp_root=temp_root,
                              final_authority=authority)


def load_final_ledger_binding(*, git, repository, temp_root,
                              expected_binding_sha256, expected_evaluation_id):
    """Expected identities come from owner creation custody, not untrusted files."""
    authority = load_final_authority(git=git, repository=repository, temp_root=temp_root)
    inputs = load_input_authority(git=git, repository=repository, temp_root=temp_root)
    root = _root(repository)
    public = _fixed_path(root, profile.FINAL_LEDGER_PATH)
    raw = _fixed_path(root, profile.FINAL_BINDING_PATH).read_bytes()
    if _sha(raw) != expected_binding_sha256:
        _fail()
    prefix = public.read_bytes()
    if not prefix:
        _fail()
    bound = FinalLedgerBinding(authority, raw, expected_evaluation_id,
                               prefix.splitlines(keepends=True)[0], inputs)
    bound.verify(public, prefix)
    ledger.validate_ledger_events(ledger.read_ledger(public))
    return bound


def verify_final_custody(*, controller_root, key_path, custody_boundary, commitment_path=None):
    _verify_fixed_custody(profile.FINAL_RUNTIME_ROOT, controller_root=controller_root,
        key_path=key_path, custody_boundary=custody_boundary, commitment_path=commitment_path)


def _final_historical_pairs(root):
    _final_historical_evaluations(root)  # Validate both exact histories first.
    return {_json(_fixed_path(root, path).read_bytes().splitlines()[1])["pair_id"]
            for path in (profile.LEDGER_PATH, profile.REPLACEMENT_LEDGER_PATH)}
