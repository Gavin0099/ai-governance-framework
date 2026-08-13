"""Offline-only synthetic integration for Gate 3 final-message diagnostics.

The module deliberately has no filesystem, process, credential, network,
preflight, or live-session adapters.  Its public evidence is canonical bytes
held by an in-memory create-once store.  It implements the accepted design's
smallest synthetic tranche and never upgrades evidence beyond
``CAPTURED_BYTE_SET_RECONSTRUCTED``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

import gate3_final_message_diagnostic as diagnostic


EVIDENCE_LEVEL = "CAPTURED_BYTE_SET_RECONSTRUCTED"
SHA256_ZERO = "0" * 64
MAX_CLEANUP_ATTEMPTS = 2


class IntegrationError(ValueError):
    """Closed-code fail-closed error; rejected values are never echoed."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SyntheticCrash(RuntimeError):
    """Deterministic interruption injected before or after durability."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii") + b"\n"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_canonical(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationError("JSON_INVALID") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != payload:
        raise IntegrationError("JSON_NOT_CANONICAL")
    return value


def _schema(name: str, required: Iterable[str], optional: Iterable[str] = ()) -> dict[str, object]:
    return {
        "additional_properties": False,
        "name": name,
        "optional": sorted(optional),
        "required": sorted(required),
        "schema": "gate3.synthetic.closed-schema.v1",
    }


SCHEMAS: dict[str, dict[str, object]] = {
    "action": _schema(
        "action",
        (
            "schema",
            "fixture_id",
            "max_cleanup_attempts",
            "classifier_api",
            "implementation_identities",
            "execution_command_contract_sha256",
            "privacy_contract_sha256",
            "recovery_contract_sha256",
        ),
    ),
    "locator-snapshot": _schema(
        "locator-snapshot",
        ("schema", "action_sha256", "locator_id", "private_root_id"),
    ),
    "transition": _schema(
        "transition",
        ("schema", "ordinal", "previous_sha256", "class", "locator_sha256", "data"),
    ),
    "transition-projection": _schema(
        "transition-projection", ("schema", "entries")
    ),
    "lifecycle-projection": _schema(
        "lifecycle-projection", ("schema", "coverage", "events", "nodes")
    ),
    "lifecycle-fixture": _schema(
        "lifecycle-fixture",
        (
            "schema",
            "fixture_id",
            "capacity",
            "topology",
            "initial_parent_id",
            "target_id",
            "events",
        ),
    ),
    "seal": _schema(
        "seal",
        (
            "schema",
            "action_sha256",
            "locator_sha256",
            "lifecycle_sha256",
            "raw_script_sha256",
            "topology_sha256",
            "observer_implementation_sha256",
            "observer_contract_sha256",
            "classification",
            "cleanup_state",
            "receipt_state",
        ),
    ),
    "cleanup-result": _schema(
        "cleanup-result",
        (
            "schema",
            "action_sha256",
            "observation_seal_sha256",
            "attempted",
            "attempt_count",
            "result",
            "residue",
            "failure_code",
            "locator_disposition",
        ),
    ),
    "receipt": _schema(
        "receipt",
        (
            "schema",
            "action_sha256",
            "observation_seal_sha256",
            "cleanup_result_sha256",
            "implementation_identities",
            "classification",
            "overall_result",
            "cleanup_disposition",
            "residue",
            "locator_state",
            "counted",
            "claim_ceiling",
            "terminal_disposition",
        ),
    ),
    "finalization": _schema(
        "finalization",
        (
            "schema",
            "action_sha256",
            "observation_seal_sha256",
            "cleanup_result_sha256",
            "final_receipt_sha256",
            "recovery_finalizer_sha256",
            "verifier_sha256",
            "residue",
            "locator_before",
            "transition_projection_sha256",
            "locator_after",
            "terminal_class",
        ),
    ),
    "external-terminal": _schema(
        "external-terminal",
        (
            "schema",
            "action_sha256",
            "origin_stage",
            "code",
            "attempted",
            "attempt_count",
            "result",
            "residue",
        ),
        (
            "locator_disposition",
            "transition_projection_sha256",
            "setup_temp_snapshot_sha256",
            "removal_authorization_sha256",
            "removal_result_sha256",
            "locator_snapshot_sha256",
        ),
    ),
    "external-finalization": _schema(
        "external-finalization",
        (
            "schema",
            "terminal_sha256",
            "action_sha256",
            "locator_sha256",
            "transition_projection_sha256",
            "recovery_finalizer_sha256",
            "verifier_sha256",
            "locator_after",
            "terminal_class",
        ),
    ),
    "setup-temp-snapshot": _schema(
        "setup-temp-snapshot", ("schema", "action_sha256", "temp_id", "purpose")
    ),
    "setup-temp-removal-authorization": _schema(
        "setup-temp-removal-authorization",
        (
            "schema",
            "snapshot_sha256",
            "attempt_ordinal",
            "operation",
            "retry_permitted",
        ),
    ),
    "setup-temp-removal-result": _schema(
        "setup-temp-removal-result",
        (
            "schema",
            "authorization_sha256",
            "attempt_ordinal",
            "result",
            "absence_observation",
        ),
    ),
    "manifest": _schema("manifest", ("schema", "profile", "entries")),
}


SCHEMA_IDS = {
    name: f"gate3.final-message-diagnostic.{name}.v1" for name in SCHEMAS
}


def schema_bytes(name: str) -> bytes:
    return canonical_bytes(SCHEMAS[name])


EXECUTION_COMMAND_CONTRACT_BYTES = canonical_bytes(
    {
        "schema": "gate3.synthetic.execution-command-contract.v1",
        "argv": ["python", "-B", "offline_verifier.py"],
        "capabilities": [],
        "mode": "SYNTHETIC_OFFLINE_ONLY",
    }
)
RETAINED_IMPLEMENTATIONS: dict[str, bytes] = {
    "lifecycle_observer.py": b"gate3 synthetic lifecycle observer v1\n",
    "diagnostic_classifier.py": b"gate3 bound public classifier adapter v1\n",
    "canonical_publisher.py": b"gate3 synthetic create-once publisher v1\n",
    "cleanup_adapter.py": b"gate3 synthetic cleanup adapter v1\n",
    "recovery_finalizer.py": b"gate3 synthetic recovery finalizer v1\n",
    "offline_verifier.py": b"gate3 captured-byte-set verifier v1\n",
}
REVIEWED_IMPLEMENTATION_SOURCE_BYTES: bytes | None = None
COMMON_RETAINED_FILES: dict[str, bytes] = {
    "contracts/execution-command-contract.json": EXECUTION_COMMAND_CONTRACT_BYTES,
    "contracts/lifecycle-observer-contract.json": canonical_bytes(
        {"schema": "gate3.synthetic.lifecycle-contract.v1", "version": 1}
    ),
    "contracts/privacy-contract.json": canonical_bytes(
        {"schema": "gate3.synthetic.privacy-contract.v1", "deny_by_default": True}
    ),
    "contracts/recovery-state-contract.json": canonical_bytes(
        {"schema": "gate3.synthetic.recovery-contract.v1", "retry": False}
    ),
    "fixtures/fixture-manifest.json": canonical_bytes(
        {
            "schema": "gate3.synthetic.fixture-manifest.v1",
            "fixture_ids": ["synthetic-no-final-message-v1"],
        }
    ),
}
for _implementation_name, _implementation_bytes in RETAINED_IMPLEMENTATIONS.items():
    COMMON_RETAINED_FILES[f"implementations/{_implementation_name}"] = _implementation_bytes
    COMMON_RETAINED_FILES[
        f"implementation-identities/{_implementation_name}.identity.json"
    ] = canonical_bytes(
        {
            "schema": "gate3.synthetic.implementation-identity.v1",
            "implementation": _implementation_name,
            "source_sha256": sha256(_implementation_bytes),
            "execution_command_contract_sha256": sha256(
                EXECUTION_COMMAND_CONTRACT_BYTES
            ),
            "claim": "BYTE_IDENTITY_ONLY",
        }
    )


def configure_reviewed_implementation_source(payload: bytes) -> None:
    """Inject caller-retained exact module bytes; never discovers a host path."""

    global REVIEWED_IMPLEMENTATION_SOURCE_BYTES
    if not isinstance(payload, bytes) or not payload:
        raise IntegrationError("REVIEWED_IMPLEMENTATION_SOURCE_INVALID")
    REVIEWED_IMPLEMENTATION_SOURCE_BYTES = bytes(payload)


def retained_common_files() -> dict[str, bytes]:
    if REVIEWED_IMPLEMENTATION_SOURCE_BYTES is None:
        raise IntegrationError("REVIEWED_IMPLEMENTATION_SOURCE_MISSING")
    files = dict(COMMON_RETAINED_FILES)
    for name in RETAINED_IMPLEMENTATIONS:
        files[f"implementations/{name}"] = REVIEWED_IMPLEMENTATION_SOURCE_BYTES
        files[f"implementation-identities/{name}.identity.json"] = canonical_bytes(
            {
                "schema": "gate3.synthetic.implementation-identity.v1",
                "implementation": name,
                "source_sha256": sha256(REVIEWED_IMPLEMENTATION_SOURCE_BYTES),
                "execution_command_contract_sha256": sha256(
                    EXECUTION_COMMAND_CONTRACT_BYTES
                ),
                "claim": "CAPTURED_SOURCE_BYTES_ONLY",
            }
        )
    return files


@dataclass(frozen=True)
class VerificationAuthority:
    expected_tree_manifest_sha256: str
    expected_verifier_sha256: str
    expected_execution_command_contract_sha256: str
    requested_evidence_level: str = EVIDENCE_LEVEL


def validate_shape(name: str, value: Mapping[str, object]) -> None:
    document = SCHEMAS[name]
    required = set(document["required"])
    optional = set(document["optional"])
    if set(value) != required | (set(value) & optional):
        raise IntegrationError("SCHEMA_FIELDS_INVALID")
    if not required.issubset(value):
        raise IntegrationError("SCHEMA_REQUIRED_MISSING")
    if value.get("schema") != SCHEMA_IDS[name]:
        raise IntegrationError("SCHEMA_ID_INVALID")


FORBIDDEN_KEY_FRAGMENTS = (
    "credential",
    "secret",
    "token",
    "prompt",
    "model_text",
    "raw_content",
    "skill_text",
    "stderr",
    "content_digest",
    "event_payload",
    "absolute_path",
    "username",
)
FORBIDDEN_VALUE_FRAGMENTS = ("live_", "user-controlled", "authorization: bearer")


def validate_privacy(value: object) -> None:
    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS):
                    raise IntegrationError("PRIVACY_KEY_FORBIDDEN")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            lowered = node.lower()
            if any(fragment in lowered for fragment in FORBIDDEN_VALUE_FRAGMENTS):
                raise IntegrationError("PRIVACY_VALUE_FORBIDDEN")

    walk(value)


@dataclass
class CreateOnceStore:
    """Byte-preserving create-once durable store simulator."""

    files: dict[str, bytes] = field(default_factory=dict)
    crash_plan: tuple[str, str] | None = None

    def arm_crash(self, path: str, phase: str) -> None:
        if phase not in {"before", "after"}:
            raise IntegrationError("CRASH_PHASE_INVALID")
        self.crash_plan = (path, phase)

    def publish(
        self, path: str, value: object | bytes, *, crash: str | None = None
    ) -> str:
        payload = value if isinstance(value, bytes) else canonical_bytes(value)
        if self.crash_plan is not None and self.crash_plan[0] == path:
            crash = self.crash_plan[1]
            self.crash_plan = None
        if crash == "before":
            raise SyntheticCrash("BEFORE_DURABILITY")
        existing = self.files.get(path)
        if existing is not None and existing != payload:
            raise IntegrationError("CREATE_ONCE_COLLISION")
        self.files.setdefault(path, payload)
        if self.files[path] != payload:
            raise IntegrationError("DURABLE_REOPEN_MISMATCH")
        digest = sha256(payload)
        if crash == "after":
            raise SyntheticCrash("AFTER_DURABILITY")
        return digest

    def read(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError as exc:
            raise IntegrationError("ARTIFACT_MISSING") from exc

    def clone(self) -> "CreateOnceStore":
        return CreateOnceStore(copy.deepcopy(self.files))


@dataclass
class WorldEntry:
    identity: str
    payload: bytes
    kind: str = "file"


@dataclass
class SyntheticWorld:
    root_identity: str = "synthetic-root-v1"
    entries: dict[str, WorldEntry] = field(default_factory=dict)

    def put(
        self, path: str, payload: bytes, *, identity: str | None = None, kind: str = "file"
    ) -> None:
        self.entries[path] = WorldEntry(identity or f"id-{path}", payload, kind)

    def remove(self, path: str) -> None:
        self.entries.pop(path, None)

    def switch_root(self) -> None:
        self.root_identity = "synthetic-root-replaced"


@dataclass(frozen=True)
class CapturedByteSet:
    root_identity: str
    entries: Mapping[str, bytes]
    identities: Mapping[str, str]
    evidence_level: str = EVIDENCE_LEVEL


CaptureAttack = Callable[[str, SyntheticWorld, str], None]


def capture_world(
    world: SyntheticWorld, expected_paths: Iterable[str], attack: CaptureAttack | None = None
) -> CapturedByteSet:
    expected = tuple(sorted(expected_paths))
    initial_root = world.root_identity
    if tuple(sorted(world.entries)) != expected:
        raise IntegrationError("TREE_INVENTORY_MISMATCH")
    if len({path.casefold() for path in expected}) != len(expected):
        raise IntegrationError("TREE_CASE_COLLISION")
    if len({world.entries[path].identity for path in expected}) != len(expected):
        raise IntegrationError("TREE_IDENTITY_ALIAS")
    initial_entries = {path: world.entries[path] for path in expected}
    initial_identities = {path: world.entries[path].identity for path in expected}
    payloads: dict[str, bytes] = {}
    identities: dict[str, str] = {}
    for path in expected:
        if attack:
            attack("before_open", world, path)
        entry = world.entries.get(path)
        if entry is None or entry.kind != "file":
            raise IntegrationError("PATH_INVALID")
        opened_identity = entry.identity
        if entry is not initial_entries[path] or opened_identity != initial_identities[path]:
            raise IntegrationError("TOCTOU_IDENTITY_CHANGED")
        if attack:
            attack("during_read", world, path)
        current = world.entries.get(path)
        if current is not entry or current.identity != opened_identity:
            raise IntegrationError("TOCTOU_IDENTITY_CHANGED")
        payloads[path] = bytes(entry.payload)
        identities[path] = opened_identity
        if attack:
            attack("after_read", world, path)
        current = world.entries.get(path)
        if current is None or current.identity != opened_identity:
            raise IntegrationError("TOCTOU_IDENTITY_CHANGED")
    if world.root_identity != initial_root:
        raise IntegrationError("TOCTOU_ROOT_CHANGED")
    if tuple(sorted(world.entries)) != expected:
        raise IntegrationError("TREE_INVENTORY_CHANGED")
    return CapturedByteSet(initial_root, payloads, identities)


@dataclass
class ObserverNode:
    node_id: str
    parent_id: str | None
    started: bool = False
    terminated: bool = False


@dataclass
class LifecycleObserver:
    capacity: int = 64
    started: bool = False
    stopped: bool = False
    coverage: str = "COMPLETE"
    nodes: dict[str, ObserverNode] = field(default_factory=dict)
    events: list[dict[str, object]] = field(default_factory=list)
    coverage_started: bool = False
    launch_started: bool = False
    tree_terminated: bool = False
    final_snapshot: bool = False

    def start(self) -> None:
        if self.started:
            raise IntegrationError("OBSERVER_START_DUPLICATE")
        self.started = True

    def emit(self, marker: str, node_id: str, parent_id: str | None = None) -> None:
        if not self.started or self.stopped:
            raise IntegrationError("OBSERVER_NOT_ACTIVE")
        if len(self.events) >= self.capacity:
            self.coverage = "OVERFLOW"
            raise IntegrationError("OBSERVER_OVERFLOW")
        projected: dict[str, object] = {"marker": marker, "ordinal": len(self.events)}
        if marker == "coverage_started":
            if self.events:
                raise IntegrationError("COVERAGE_START_ORDER_INVALID")
            self.coverage_started = True
        elif marker == "launch_started":
            if not self.coverage_started or self.launch_started:
                raise IntegrationError("LAUNCH_BARRIER_INVALID")
            self.launch_started = True
        elif marker == "process_node_started":
            if not self.launch_started:
                raise IntegrationError("LAUNCH_NOT_STARTED")
            if node_id in self.nodes:
                raise IntegrationError("NODE_START_DUPLICATE")
            if parent_id is not None:
                parent = self.nodes.get(parent_id)
                if parent is None or not parent.started:
                    raise IntegrationError("PARENT_NOT_STARTED")
            self.nodes[node_id] = ObserverNode(node_id, parent_id, started=True)
            projected["node_id"] = node_id
        elif marker == "process_node_terminated":
            node = self.nodes.get(node_id)
            if node is None or node.terminated:
                raise IntegrationError("NODE_TERMINATION_INVALID")
            if any(
                child.parent_id == node_id and not child.terminated
                for child in self.nodes.values()
            ):
                raise IntegrationError("CHILD_OUTLIVES_PARENT")
            node.terminated = True
            projected["node_id"] = node_id
        elif marker == "process_tree_terminated":
            if not self.nodes or any(not node.terminated for node in self.nodes.values()):
                raise IntegrationError("TREE_TERMINATION_INVALID")
            self.tree_terminated = True
        elif marker == "final_snapshot_acquired":
            if not self.tree_terminated:
                raise IntegrationError("FINAL_SNAPSHOT_ORDER_INVALID")
            self.final_snapshot = True
        elif marker == "coverage_stopped":
            if not self.final_snapshot:
                raise IntegrationError("COVERAGE_STOP_ORDER_INVALID")
            self.stopped = True
        elif marker in {
            "target_created",
            "target_replaced",
            "target_removed",
            "target_type_changed",
            "parent_identity_changed",
        }:
            projected["target_id"] = node_id
        elif marker in {"observer_gap", "observer_overflow"}:
            self.coverage = "INCOMPLETE"
        else:
            raise IntegrationError("OBSERVER_MARKER_UNKNOWN")
        self.events.append(projected)

    def stop(self) -> None:
        if not self.started:
            raise IntegrationError("OBSERVER_STOP_INVALID")
        if self.coverage != "COMPLETE" or not self.stopped or not self.tree_terminated or not self.final_snapshot:
            self.coverage = "INCOMPLETE"
            raise IntegrationError("OBSERVER_COVERAGE_INCOMPLETE")

    def projection(self) -> dict[str, object]:
        if not self.stopped or self.coverage != "COMPLETE":
            raise IntegrationError("OBSERVER_SEAL_FORBIDDEN")
        value = {
            "schema": SCHEMA_IDS["lifecycle-projection"],
            "coverage": self.coverage,
            "events": copy.deepcopy(self.events),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "parent_id": node.parent_id,
                    "started": node.started,
                    "terminated": node.terminated,
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.node_id)
            ],
        }
        validate_shape("lifecycle-projection", value)
        return value


def default_observer() -> LifecycleObserver:
    return replay_lifecycle_fixture(build_lifecycle_fixture())


def build_lifecycle_fixture() -> dict[str, object]:
    value = {
        "schema": SCHEMA_IDS["lifecycle-fixture"],
        "fixture_id": "synthetic-final-created-v1",
        "capacity": 64,
        "topology": [
            {"node_id": "parent_0", "parent_id": None},
            {"node_id": "child_0", "parent_id": "parent_0"},
        ],
        "initial_parent_id": "parent_0",
        "target_id": "final_message",
        "events": [
            {"sequence": 0, "marker": "coverage_started", "node_id": "", "parent_id": None},
            {"sequence": 1, "marker": "launch_started", "node_id": "", "parent_id": None},
            {"sequence": 2, "marker": "process_node_started", "node_id": "parent_0", "parent_id": None},
            {"sequence": 3, "marker": "process_node_started", "node_id": "child_0", "parent_id": "parent_0"},
            {"sequence": 4, "marker": "target_created", "node_id": "final_message", "parent_id": None},
            {"sequence": 5, "marker": "process_node_terminated", "node_id": "child_0", "parent_id": "parent_0"},
            {"sequence": 6, "marker": "process_node_terminated", "node_id": "parent_0", "parent_id": None},
            {"sequence": 7, "marker": "process_tree_terminated", "node_id": "", "parent_id": None},
            {"sequence": 8, "marker": "final_snapshot_acquired", "node_id": "", "parent_id": None},
            {"sequence": 9, "marker": "coverage_stopped", "node_id": "", "parent_id": None},
        ],
    }
    validate_shape("lifecycle-fixture", value)
    return value


INDEPENDENT_EXPECTED_LIFECYCLE: dict[str, object] = {
    "schema": SCHEMA_IDS["lifecycle-projection"],
    "coverage": "COMPLETE",
    "events": [
        {"marker": "coverage_started", "ordinal": 0},
        {"marker": "launch_started", "ordinal": 1},
        {"marker": "process_node_started", "node_id": "parent_0", "ordinal": 2},
        {"marker": "process_node_started", "node_id": "child_0", "ordinal": 3},
        {"marker": "target_created", "target_id": "final_message", "ordinal": 4},
        {"marker": "process_node_terminated", "node_id": "child_0", "ordinal": 5},
        {"marker": "process_node_terminated", "node_id": "parent_0", "ordinal": 6},
        {"marker": "process_tree_terminated", "ordinal": 7},
        {"marker": "final_snapshot_acquired", "ordinal": 8},
        {"marker": "coverage_stopped", "ordinal": 9},
    ],
    "nodes": [
        {"node_id": "child_0", "parent_id": "parent_0", "started": True, "terminated": True},
        {"node_id": "parent_0", "parent_id": None, "started": True, "terminated": True},
    ],
}


def build_absent_lifecycle_fixture() -> dict[str, object]:
    value = copy.deepcopy(build_lifecycle_fixture())
    value["fixture_id"] = "synthetic-no-final-message-v1"
    value["events"] = [
        event for event in value["events"] if event["marker"] != "target_created"
    ]
    for sequence, event in enumerate(value["events"]):
        event["sequence"] = sequence
    return value


INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE: dict[str, object] = copy.deepcopy(
    INDEPENDENT_EXPECTED_LIFECYCLE
)
INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE["events"] = [
    event
    for event in INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE["events"]
    if event["marker"] != "target_created"
]
for _ordinal, _event in enumerate(INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE["events"]):
    _event["ordinal"] = _ordinal

_RAW_LIFECYCLE_FIXTURE_BYTES = canonical_bytes(build_lifecycle_fixture())
_EXPECTED_LIFECYCLE_BYTES = canonical_bytes(INDEPENDENT_EXPECTED_LIFECYCLE)
_RAW_ABSENT_LIFECYCLE_FIXTURE_BYTES = canonical_bytes(build_absent_lifecycle_fixture())
_EXPECTED_ABSENT_LIFECYCLE_BYTES = canonical_bytes(
    INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE
)
_EXPECTED_RECOVERY_BYTES = canonical_bytes(
    {
        "schema": "gate3.synthetic.expected-recovery.v1",
        "profiles": [
            "SETUP_TERMINAL_BEFORE_LOCATOR",
            "SETUP_TEMP_RESIDUE_OPEN",
            "SETUP_TEMP_ATTEMPT_UNKNOWN",
            "EXTERNAL_RECOVERY_CLOSED",
            "EXTERNAL_RECOVERY_OPEN",
        ],
    }
)
COMMON_RETAINED_FILES.update(
    {
        "fixtures/raw/synthetic-final-created-v1.json": _RAW_LIFECYCLE_FIXTURE_BYTES,
        "fixtures/expected-lifecycle/synthetic-final-created-v1.json": _EXPECTED_LIFECYCLE_BYTES,
        "fixtures/raw/synthetic-no-final-message-v1.json": _RAW_ABSENT_LIFECYCLE_FIXTURE_BYTES,
        "fixtures/expected-lifecycle/synthetic-no-final-message-v1.json": _EXPECTED_ABSENT_LIFECYCLE_BYTES,
        "fixtures/expected-recovery/synthetic-recovery-matrix-v1.json": _EXPECTED_RECOVERY_BYTES,
        "fixtures/fixture-manifest.json": canonical_bytes(
            {
                "schema": "gate3.synthetic.fixture-manifest.v1",
                "fixtures": [
                    {
                        "fixture_id": "synthetic-final-created-v1",
                        "raw_path": "fixtures/raw/synthetic-final-created-v1.json",
                        "raw_sha256": sha256(_RAW_LIFECYCLE_FIXTURE_BYTES),
                        "expected_lifecycle_path": "fixtures/expected-lifecycle/synthetic-final-created-v1.json",
                        "expected_lifecycle_sha256": sha256(_EXPECTED_LIFECYCLE_BYTES),
                    },
                    {
                        "fixture_id": "synthetic-no-final-message-v1",
                        "raw_path": "fixtures/raw/synthetic-no-final-message-v1.json",
                        "raw_sha256": sha256(_RAW_ABSENT_LIFECYCLE_FIXTURE_BYTES),
                        "expected_lifecycle_path": "fixtures/expected-lifecycle/synthetic-no-final-message-v1.json",
                        "expected_lifecycle_sha256": sha256(_EXPECTED_ABSENT_LIFECYCLE_BYTES),
                    },
                ],
                "expected_recovery_path": "fixtures/expected-recovery/synthetic-recovery-matrix-v1.json",
                "expected_recovery_sha256": sha256(_EXPECTED_RECOVERY_BYTES),
                "topology": [
                    {"node_id": "parent_0", "parent_id": None},
                    {"node_id": "child_0", "parent_id": "parent_0"},
                ],
                "initial_parent_id": "parent_0",
                "target_id": "final_message",
                "max_cleanup_attempts": MAX_CLEANUP_ATTEMPTS,
            }
        ),
    }
)


def replay_lifecycle_fixture(fixture: Mapping[str, object]) -> LifecycleObserver:
    validate_shape("lifecycle-fixture", fixture)
    capacity = fixture["capacity"]
    events = fixture["events"]
    topology = fixture["topology"]
    if not isinstance(capacity, int) or capacity < 1 or not isinstance(events, list) or not isinstance(topology, list):
        raise IntegrationError("LIFECYCLE_FIXTURE_INVALID")
    expected_topology: dict[str, object] = {}
    for node in topology:
        if not isinstance(node, dict) or set(node) != {"node_id", "parent_id"}:
            raise IntegrationError("LIFECYCLE_TOPOLOGY_INVALID")
        node_id = node["node_id"]
        parent_id = node["parent_id"]
        if not isinstance(node_id, str) or node_id in expected_topology:
            raise IntegrationError("LIFECYCLE_TOPOLOGY_INVALID")
        expected_topology[node_id] = parent_id
    observer = LifecycleObserver(capacity=capacity)
    observer.start()
    for expected_sequence, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != {"sequence", "marker", "node_id", "parent_id"}:
            raise IntegrationError("LIFECYCLE_FIXTURE_EVENT_INVALID")
        if event["sequence"] != expected_sequence:
            raise IntegrationError("LIFECYCLE_SEQUENCE_INVALID")
        marker = event["marker"]
        node_id = event["node_id"]
        parent_id = event["parent_id"]
        if not isinstance(marker, str) or not isinstance(node_id, str):
            raise IntegrationError("LIFECYCLE_FIXTURE_EVENT_INVALID")
        if parent_id is not None and not isinstance(parent_id, str):
            raise IntegrationError("LIFECYCLE_FIXTURE_EVENT_INVALID")
        observer.emit(marker, node_id, parent_id)
    observer.stop()
    actual_topology = {node.node_id: node.parent_id for node in observer.nodes.values()}
    if actual_topology != expected_topology:
        raise IntegrationError("LIFECYCLE_TOPOLOGY_MISMATCH")
    return observer


def build_action() -> dict[str, object]:
    retained = retained_common_files()
    value = {
        "schema": SCHEMA_IDS["action"],
        "fixture_id": "synthetic-integration-v1",
        "max_cleanup_attempts": MAX_CLEANUP_ATTEMPTS,
        "classifier_api": "classify_public_input",
        "implementation_identities": {
            name: sha256(
                retained[
                    f"implementation-identities/{name}.identity.json"
                ]
            )
            for name in sorted(RETAINED_IMPLEMENTATIONS)
        },
        "execution_command_contract_sha256": sha256(
            retained["contracts/execution-command-contract.json"]
        ),
        "privacy_contract_sha256": sha256(
            retained["contracts/privacy-contract.json"]
        ),
        "recovery_contract_sha256": sha256(
            retained["contracts/recovery-state-contract.json"]
        ),
    }
    validate_shape("action", value)
    return value


def classify_synthetic(
    lifecycle: Mapping[str, object] | None = None,
) -> dict[str, object]:
    final_output = "CAPTURED_VALID"
    if lifecycle is not None:
        validate_shape("lifecycle-projection", lifecycle)
        events = lifecycle["events"]
        if lifecycle["coverage"] != "COMPLETE" or not isinstance(events, list):
            raise IntegrationError("CLASSIFIER_LIFECYCLE_INADMISSIBLE")
        created = any(
            isinstance(event, dict)
            and event.get("marker") == "target_created"
            and event.get("target_id") == "final_message"
            for event in events
        )
        final_output = (
            "CAPTURED_VALID"
            if created
            else "NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE"
        )
    return diagnostic.classify_public_input(
        diagnostic.build_synthetic_input(final_output=final_output)
    )


@dataclass
class TransitionChain:
    store: CreateOnceStore
    locator_sha256: str
    digests: list[str] = field(default_factory=list)

    def append(self, transition_class: str, data: Mapping[str, object]) -> str:
        ordinal = len(self.digests)
        value = {
            "schema": SCHEMA_IDS["transition"],
            "ordinal": ordinal,
            "previous_sha256": self.digests[-1] if self.digests else SHA256_ZERO,
            "class": transition_class,
            "locator_sha256": self.locator_sha256,
            "data": dict(data),
        }
        validate_shape("transition", value)
        digest = self.store.publish(f"recovery-transitions/{ordinal:04d}.json", value)
        self.digests.append(digest)
        return digest

    def projection(self) -> dict[str, object]:
        entries = []
        for ordinal, digest in enumerate(self.digests):
            path = f"recovery-transitions/{ordinal:04d}.json"
            payload = self.store.read(path)
            entries.append(
                {
                    "ordinal": ordinal,
                    "path": path,
                    "byte_count": len(payload),
                    "sha256": digest,
                    "previous_sha256": self.digests[ordinal - 1]
                    if ordinal
                    else SHA256_ZERO,
                }
            )
        value = {
            "schema": SCHEMA_IDS["transition-projection"],
            "entries": entries,
        }
        validate_shape("transition-projection", value)
        return value


@dataclass
class SyntheticIntegration:
    store: CreateOnceStore = field(default_factory=CreateOnceStore)
    action_sha256: str | None = None
    locator_sha256: str | None = None
    chain: TransitionChain | None = None
    recovered: bool = False

    @classmethod
    def reopen(cls, retained: CreateOnceStore) -> "SyntheticIntegration":
        store = retained.clone()
        subject = cls(store=store, recovered=True)
        if "action.json" not in store.files:
            if store.files:
                raise IntegrationError("RESTART_ACTION_MISSING")
            return subject
        action = parse_canonical(store.read("action.json"))
        validate_shape("action", action)
        subject.action_sha256 = sha256(store.read("action.json"))
        if "locator-snapshot.json" not in store.files:
            return subject
        locator = parse_canonical(store.read("locator-snapshot.json"))
        validate_shape("locator-snapshot", locator)
        if locator["action_sha256"] != subject.action_sha256:
            raise IntegrationError("RESTART_LOCATOR_LINK_INVALID")
        subject.locator_sha256 = sha256(store.read("locator-snapshot.json"))
        chain = TransitionChain(store, subject.locator_sha256)
        paths = sorted(
            path for path in store.files if path.startswith("recovery-transitions/")
        )
        previous = SHA256_ZERO
        for ordinal, path in enumerate(paths):
            if path != f"recovery-transitions/{ordinal:04d}.json":
                raise IntegrationError("RESTART_TRANSITION_INVENTORY_INVALID")
            value = parse_canonical(store.read(path))
            validate_shape("transition", value)
            if (
                value["ordinal"] != ordinal
                or value["previous_sha256"] != previous
                or value["locator_sha256"] != subject.locator_sha256
            ):
                raise IntegrationError("RESTART_TRANSITION_LINK_INVALID")
            previous = sha256(store.read(path))
            chain.digests.append(previous)
        subject.chain = chain
        return subject

    def publish_action(self) -> str:
        self.action_sha256 = self.store.publish("action.json", build_action())
        return self.action_sha256

    def publish_locator(self) -> str:
        if self.action_sha256 is None:
            raise IntegrationError("ACTION_REQUIRED")
        locator = {
            "schema": SCHEMA_IDS["locator-snapshot"],
            "action_sha256": self.action_sha256,
            "locator_id": "synthetic-locator-v1",
            "private_root_id": "synthetic-private-root-v1",
        }
        validate_shape("locator-snapshot", locator)
        validate_privacy(locator)
        self.locator_sha256 = self.store.publish("locator-snapshot.json", locator)
        self.chain = TransitionChain(self.store, self.locator_sha256)
        return self.locator_sha256

    def authorize_creation(self) -> str:
        if self.chain is None:
            raise IntegrationError("LOCATOR_REQUIRED")
        if self.chain.digests:
            raise IntegrationError("CREATION_AUTH_ALREADY_DURABLE")
        return self.chain.append(
            "PRIVATE_ROOT_CREATION_AUTHORIZED",
            {
                "attempt_ordinal": 1,
                "operation": "CREATE_EXACT_PRIVATE_ROOT",
                "private_root_id": "synthetic-private-root-v1",
                "retry_permitted": False,
            },
        )

    def record_creation(self, authorization_sha256: str, result: str) -> str:
        if self.chain is None or result not in {"SUCCEEDED", "FAILED"}:
            raise IntegrationError("CREATION_RESULT_INVALID")
        if self.recovered and len(self.chain.digests) == 1:
            raise IntegrationError("CREATION_RESULT_RECALL_FORBIDDEN")
        transition_class = f"PRIVATE_ROOT_CREATION_{result}"
        data: dict[str, object] = {
            "attempt_ordinal": 1,
            "authorization_sha256": authorization_sha256,
            "result": result,
        }
        if result == "SUCCEEDED":
            data["private_root_id"] = "synthetic-private-root-v1"
        return self.chain.append(transition_class, data)

    def creation_unknown_terminal(self, authorization_sha256: str) -> dict[str, object]:
        return self._external_terminal(
            "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE",
            "PRIVATE_ROOT_CREATION",
            False,
            0,
            "NOT_ATTEMPTED",
            "UNKNOWN",
            "RETAINED",
            authorization_sha256,
        )

    def publish_lifecycle(self, fixture: Mapping[str, object]) -> str:
        validate_shape("lifecycle-fixture", fixture)
        validate_privacy(fixture)
        self.store.publish("lifecycle-fixture.json", fixture)
        projection = replay_lifecycle_fixture(fixture).projection()
        fixture_id = fixture["fixture_id"]
        expected = {
            "synthetic-final-created-v1": INDEPENDENT_EXPECTED_LIFECYCLE,
            "synthetic-no-final-message-v1": INDEPENDENT_EXPECTED_ABSENT_LIFECYCLE,
        }.get(str(fixture_id))
        if expected is None or projection != expected:
            raise IntegrationError("INDEPENDENT_EXPECTED_LIFECYCLE_MISMATCH")
        self.store.publish(
            "expected-lifecycle-projection.json", expected
        )
        return self.store.publish("lifecycle-projection.json", projection)

    def publish_seal(self, lifecycle_sha256: str) -> str:
        if self.action_sha256 is None or self.locator_sha256 is None:
            raise IntegrationError("SETUP_INCOMPLETE")
        lifecycle = parse_canonical(self.store.read("lifecycle-projection.json"))
        if sha256(self.store.read("lifecycle-projection.json")) != lifecycle_sha256:
            raise IntegrationError("LIFECYCLE_DIGEST_ARGUMENT_INVALID")
        classification = classify_synthetic(lifecycle)
        retained = retained_common_files()
        value = {
            "schema": SCHEMA_IDS["seal"],
            "action_sha256": self.action_sha256,
            "locator_sha256": self.locator_sha256,
            "lifecycle_sha256": lifecycle_sha256,
            "raw_script_sha256": sha256(self.store.read("lifecycle-fixture.json")),
            "topology_sha256": sha256(
                canonical_bytes(parse_canonical(self.store.read("lifecycle-fixture.json"))["topology"])
            ),
            "observer_implementation_sha256": sha256(
                retained["implementations/lifecycle_observer.py"]
            ),
            "observer_contract_sha256": sha256(
                retained["contracts/lifecycle-observer-contract.json"]
            ),
            "classification": classification,
            "cleanup_state": "PENDING",
            "receipt_state": "PENDING",
        }
        validate_shape("seal", value)
        validate_privacy(value)
        return self.store.publish("observation-seal.json", value)

    def publish_cleanup(self, seal_sha256: str, result: str, residue: str) -> str:
        if self.action_sha256 is None:
            raise IntegrationError("ACTION_REQUIRED")
        if result not in {"PASS", "FAIL", "PARTIAL", "NOT_ATTEMPTED"}:
            raise IntegrationError("CLEANUP_RESULT_INVALID")
        attempted = result != "NOT_ATTEMPTED"
        if result == "PASS" and residue != "ZERO_RESIDUE":
            raise IntegrationError("CLEANUP_RESIDUE_CONTRADICTION")
        if result != "PASS" and residue == "ZERO_RESIDUE":
            raise IntegrationError("CLEANUP_RESIDUE_CONTRADICTION")
        if result == "NOT_ATTEMPTED" and residue != "UNKNOWN":
            raise IntegrationError("CLEANUP_RESIDUE_CONTRADICTION")
        value = {
            "schema": SCHEMA_IDS["cleanup-result"],
            "action_sha256": self.action_sha256,
            "observation_seal_sha256": seal_sha256,
            "attempted": attempted,
            "attempt_count": 1 if attempted else 0,
            "result": result,
            "residue": residue,
            "failure_code": (
                "NONE"
                if result == "PASS"
                else (
                    "IDENTITY_UNAVAILABLE"
                    if result == "NOT_ATTEMPTED"
                    else (
                        "SYNTHETIC_CLEANUP_PARTIAL"
                        if result == "PARTIAL"
                        else "SYNTHETIC_CLEANUP_FAILED"
                    )
                )
            ),
            "locator_disposition": (
                "RETAINED_PENDING_FINALIZATION"
                if result == "PASS"
                else "RETAINED"
            ),
        }
        validate_shape("cleanup-result", value)
        return self.store.publish("cleanup-result.json", value)

    def publish_receipt(
        self, seal_sha256: str, cleanup_sha256: str, *, negative: bool | None = None
    ) -> str:
        cleanup = parse_canonical(self.store.read("cleanup-result.json"))
        seal = parse_canonical(self.store.read("observation-seal.json"))
        classification = seal["classification"]
        if not isinstance(classification, dict):
            raise IntegrationError("RECEIPT_CLASSIFICATION_INVALID")
        classes = classification.get("diagnostic_classes")
        classification_negative = isinstance(classes, list) and (
            "CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED" in classes
        )
        cleanup_negative = (
            cleanup["result"] in {"FAIL", "PARTIAL"}
            and cleanup["residue"] in {"RESIDUE_PRESENT", "UNKNOWN"}
        ) or (
            cleanup["result"] == "NOT_ATTEMPTED"
            and cleanup["residue"] == "UNKNOWN"
        )
        derived_negative = classification_negative or cleanup_negative
        if negative is not None and negative is not derived_negative:
            raise IntegrationError("RECEIPT_DISPOSITION_OVERRIDE_FORBIDDEN")
        if not derived_negative and (
            cleanup["result"] != "PASS" or cleanup["residue"] != "ZERO_RESIDUE"
        ):
            raise IntegrationError("RECEIPT_FORBIDDEN")
        if derived_negative and not (
            (cleanup["result"] == "PASS" and cleanup["residue"] == "ZERO_RESIDUE")
            or (
                cleanup["result"] in {"FAIL", "PARTIAL"}
                and cleanup["residue"] in {"RESIDUE_PRESENT", "UNKNOWN"}
            )
            or (cleanup["result"] == "NOT_ATTEMPTED" and cleanup["residue"] == "UNKNOWN")
        ):
            raise IntegrationError("NEGATIVE_RECEIPT_MATRIX_INVALID")
        value = {
            "schema": SCHEMA_IDS["receipt"],
            "action_sha256": self.action_sha256,
            "observation_seal_sha256": seal_sha256,
            "cleanup_result_sha256": cleanup_sha256,
            "implementation_identities": build_action()["implementation_identities"],
            "classification": classification,
            "overall_result": "DIAGNOSTIC_NEGATIVE" if derived_negative else "DIAGNOSTIC_COMPLETE",
            "cleanup_disposition": cleanup["result"],
            "residue": cleanup["residue"],
            "locator_state": (
                "RETAINED_PENDING_FINALIZATION"
                if cleanup["residue"] == "ZERO_RESIDUE"
                else "RETAINED"
            ),
            "counted": False,
            "claim_ceiling": EVIDENCE_LEVEL,
            "terminal_disposition": "NEGATIVE_RECEIPT" if derived_negative else "DIAGNOSTIC_RECEIPT",
        }
        validate_shape("receipt", value)
        return self.store.publish("final-receipt.json", value)

    def publish_transition_projection(self) -> str:
        if self.chain is None:
            raise IntegrationError("TRANSITIONS_REQUIRED")
        return self.store.publish(
            "recovery-transition-projection.json", self.chain.projection()
        )

    def finalize_route(self, receipt_sha256: str) -> str:
        if self.chain is None or self.locator_sha256 is None:
            raise IntegrationError("LOCATOR_REQUIRED")
        receipt_payload = self.store.read("final-receipt.json")
        receipt = parse_canonical(receipt_payload)
        validate_shape("receipt", receipt)
        cleanup_payload = self.store.read("cleanup-result.json")
        cleanup = parse_canonical(cleanup_payload)
        validate_shape("cleanup-result", cleanup)
        if (
            sha256(receipt_payload) != receipt_sha256
            or receipt["cleanup_result_sha256"] != sha256(cleanup_payload)
            or receipt["cleanup_disposition"] != "PASS"
            or receipt["residue"] != "ZERO_RESIDUE"
            or receipt["locator_state"] != "RETAINED_PENDING_FINALIZATION"
            or cleanup["result"] != "PASS"
            or cleanup["residue"] != "ZERO_RESIDUE"
            or cleanup["locator_disposition"] != "RETAINED_PENDING_FINALIZATION"
        ):
            raise IntegrationError("ROUTE_FINALIZATION_RECEIPT_INELIGIBLE")
        transitions = [
            parse_canonical(
                self.store.read(f"recovery-transitions/{ordinal:04d}.json")
            )
            for ordinal in range(len(self.chain.digests))
        ]
        removals = [item for item in transitions if item["class"] == "LOCATOR_REMOVAL_AUTHORIZED"]
        absences = [item for item in transitions if item["class"] == "LOCATOR_ABSENT_CONFIRMED"]
        if removals:
            if len(removals) != 1 or removals[0]["data"] != {"receipt_sha256": receipt_sha256}:
                raise IntegrationError("ROUTE_REMOVAL_RESUME_INVALID")
            removal = self.chain.digests[removals[0]["ordinal"]]
        else:
            removal = self.chain.append(
                "LOCATOR_REMOVAL_AUTHORIZED", {"receipt_sha256": receipt_sha256}
            )
        if absences:
            if len(absences) != 1 or absences[0]["data"] != {"authorization_sha256": removal}:
                raise IntegrationError("ROUTE_ABSENCE_RESUME_INVALID")
        else:
            self.chain.append(
                "LOCATOR_ABSENT_CONFIRMED", {"authorization_sha256": removal}
            )
        projection_sha256 = self.publish_transition_projection()
        retained = retained_common_files()
        value = {
            "schema": SCHEMA_IDS["finalization"],
            "action_sha256": self.action_sha256,
            "observation_seal_sha256": receipt["observation_seal_sha256"],
            "cleanup_result_sha256": receipt["cleanup_result_sha256"],
            "final_receipt_sha256": receipt_sha256,
            "recovery_finalizer_sha256": sha256(retained["implementations/recovery_finalizer.py"]),
            "verifier_sha256": sha256(retained["implementations/offline_verifier.py"]),
            "residue": "ZERO_RESIDUE",
            "locator_before": "RETAINED_PENDING_FINALIZATION",
            "transition_projection_sha256": projection_sha256,
            "locator_after": "ABSENT_CONFIRMED",
            "terminal_class": (
                "FINALIZED_NEGATIVE"
                if receipt["terminal_disposition"] == "NEGATIVE_RECEIPT"
                else "FINALIZED_DIAGNOSTIC"
            ),
        }
        validate_shape("finalization", value)
        return self.store.publish("finalization.json", value)

    def _external_terminal(
        self,
        code: str,
        origin: str,
        attempted: bool,
        count: int,
        result: str,
        residue: str,
        disposition: str,
        projection_sha256: str,
    ) -> dict[str, object]:
        if self.action_sha256 is None:
            raise IntegrationError("ACTION_REQUIRED")
        value = {
            "schema": SCHEMA_IDS["external-terminal"],
            "action_sha256": self.action_sha256,
            "origin_stage": origin,
            "code": code,
            "attempted": attempted,
            "attempt_count": count,
            "result": result,
            "residue": residue,
            "locator_disposition": disposition,
            "transition_projection_sha256": projection_sha256,
            "locator_snapshot_sha256": self.locator_sha256,
        }
        validate_shape("external-terminal", value)
        return value

    def publish_external_terminal(
        self,
        code: str,
        *,
        result: str = "FAIL",
        residue: str = "UNKNOWN",
        attempted: bool = True,
        count: int = 1,
    ) -> str:
        if self.chain is None:
            raise IntegrationError("TRANSITIONS_REQUIRED")
        projection_value = self.chain.projection()
        projection = sha256(canonical_bytes(projection_value))
        disposition = "RETAINED_PENDING_REMOVAL" if residue == "ZERO_RESIDUE" else "RETAINED"
        value = self._external_terminal(
            code,
            "LOCATOR_BOUND_RECOVERY",
            attempted,
            count,
            result,
            residue,
            disposition,
            projection,
        )
        terminal = self.store.publish("external-terminal.json", value)
        if disposition == "RETAINED":
            self.store.publish("recovery-transition-projection.json", projection_value)
        return terminal

    def finalize_external(self, terminal_sha256: str) -> str:
        if self.chain is None or self.locator_sha256 is None:
            raise IntegrationError("LOCATOR_REQUIRED")
        terminal = parse_canonical(self.store.read("external-terminal.json"))
        if terminal["residue"] != "ZERO_RESIDUE":
            raise IntegrationError("EXTERNAL_FINALIZATION_FORBIDDEN")
        transitions = [
            parse_canonical(
                self.store.read(f"recovery-transitions/{ordinal:04d}.json")
            )
            for ordinal in range(len(self.chain.digests))
        ]
        removals = [item for item in transitions if item["class"] == "LOCATOR_REMOVAL_AUTHORIZED"]
        absences = [item for item in transitions if item["class"] == "LOCATOR_ABSENT_CONFIRMED"]
        if removals:
            if len(removals) != 1 or removals[0]["data"] != {"terminal_sha256": terminal_sha256}:
                raise IntegrationError("EXTERNAL_REMOVAL_RESUME_INVALID")
            removal = self.chain.digests[removals[0]["ordinal"]]
        else:
            removal = self.chain.append(
                "LOCATOR_REMOVAL_AUTHORIZED", {"terminal_sha256": terminal_sha256}
            )
        if absences:
            if len(absences) != 1 or absences[0]["data"] != {"authorization_sha256": removal}:
                raise IntegrationError("EXTERNAL_ABSENCE_RESUME_INVALID")
        else:
            self.chain.append(
                "LOCATOR_ABSENT_CONFIRMED", {"authorization_sha256": removal}
            )
        projection = self.publish_transition_projection()
        retained = retained_common_files()
        value = {
            "schema": SCHEMA_IDS["external-finalization"],
            "terminal_sha256": terminal_sha256,
            "action_sha256": self.action_sha256,
            "locator_sha256": self.locator_sha256,
            "transition_projection_sha256": projection,
            "recovery_finalizer_sha256": sha256(retained["implementations/recovery_finalizer.py"]),
            "verifier_sha256": sha256(retained["implementations/offline_verifier.py"]),
            "locator_after": "ABSENT_CONFIRMED",
            "terminal_class": "EXTERNAL_RECOVERY_CLOSED",
        }
        validate_shape("external-finalization", value)
        return self.store.publish("external-recovery-finalization.json", value)


def _add_schemas(files: dict[str, bytes], artifact_names: Iterable[str]) -> None:
    names = set(artifact_names) | {"manifest"}
    for name in sorted(names):
        files[f"schemas/{name}.schema.json"] = schema_bytes(name)


def _manifest(profile: str, files: Mapping[str, bytes]) -> bytes:
    entries = [
        {"path": path, "byte_count": len(payload), "sha256": sha256(payload)}
        for path, payload in sorted(files.items())
    ]
    value = {"schema": SCHEMA_IDS["manifest"], "profile": profile, "entries": entries}
    validate_shape("manifest", value)
    return canonical_bytes(value)


ROUTE_BASE = {
    "action.json": "action",
    "locator-snapshot.json": "locator-snapshot",
    "lifecycle-fixture.json": "lifecycle-fixture",
    "expected-lifecycle-projection.json": "lifecycle-projection",
    "lifecycle-projection.json": "lifecycle-projection",
    "observation-seal.json": "seal",
    "cleanup-result.json": "cleanup-result",
    "final-receipt.json": "receipt",
    "recovery-transition-projection.json": "transition-projection",
}
EXTERNAL_BASE = {
    "action.json": "action",
    "locator-snapshot.json": "locator-snapshot",
    "external-terminal.json": "external-terminal",
    "recovery-transition-projection.json": "transition-projection",
}
SETUP_NO_TEMP_BASE = {
    "action.json": "action",
    "external-terminal.json": "external-terminal",
}
SETUP_TEMP_UNKNOWN_BASE = {
    **SETUP_NO_TEMP_BASE,
    "setup-temp-snapshot.json": "setup-temp-snapshot",
    "setup-temp-removal-authorization.json": "setup-temp-removal-authorization",
}
SETUP_TEMP_RESIDUE_BASE = {
    **SETUP_TEMP_UNKNOWN_BASE,
    "setup-temp-removal-result.json": "setup-temp-removal-result",
}


def _profile_mapping(
    profile: str, files: Mapping[str, bytes] | None = None
) -> dict[str, str]:
    if profile in {"FINALIZED_CHAIN", "RECOVERY_REQUIRED_NEGATIVE"}:
        mapping = dict(ROUTE_BASE)
        if profile == "FINALIZED_CHAIN":
            mapping["finalization.json"] = "finalization"
        return mapping
    if profile in {"EXTERNAL_RECOVERY_CLOSED", "EXTERNAL_RECOVERY_OPEN"}:
        mapping = dict(EXTERNAL_BASE)
        if profile == "EXTERNAL_RECOVERY_CLOSED":
            mapping["external-recovery-finalization.json"] = "external-finalization"
        return mapping
    if profile == "SETUP_TERMINAL_BEFORE_LOCATOR":
        if files is not None and "setup-temp-snapshot.json" in files:
            return dict(SETUP_TEMP_RESIDUE_BASE)
        return dict(SETUP_NO_TEMP_BASE)
    if profile == "SETUP_TEMP_RESIDUE_OPEN":
        return dict(SETUP_TEMP_RESIDUE_BASE)
    if profile == "SETUP_TEMP_ATTEMPT_UNKNOWN":
        return dict(SETUP_TEMP_UNKNOWN_BASE)
    raise IntegrationError("PROFILE_UNKNOWN")


def build_package(store: CreateOnceStore, profile: str) -> dict[str, bytes]:
    mapping = _profile_mapping(profile, store.files)
    files = {path: store.read(path) for path in mapping}
    for path, payload in store.files.items():
        if path.startswith("recovery-transitions/"):
            files[path] = payload
    files.update(retained_common_files())
    _add_schemas(files, mapping.values())
    files["tree-manifest.json"] = _manifest(profile, files)
    return files


def captured_package(files: Mapping[str, bytes]) -> CapturedByteSet:
    world = SyntheticWorld()
    for path, payload in files.items():
        world.put(path, payload)
    return capture_world(world, files)


def _load_schema(files: Mapping[str, bytes], name: str) -> None:
    path = f"schemas/{name}.schema.json"
    payload = files.get(path)
    if payload is None or payload != schema_bytes(name):
        raise IntegrationError("SCHEMA_BYTES_MISMATCH")


def _verify_transition_chain(files: Mapping[str, bytes]) -> list[dict[str, object]]:
    payload = files.get("recovery-transition-projection.json")
    if payload is None:
        raise IntegrationError("TRANSITION_PROJECTION_MISSING")
    projection = parse_canonical(payload)
    validate_shape("transition-projection", projection)
    entries = projection["entries"]
    if not isinstance(entries, list):
        raise IntegrationError("TRANSITION_PROJECTION_INVALID")
    transitions = []
    previous = SHA256_ZERO
    for ordinal, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("ordinal") != ordinal:
            raise IntegrationError("TRANSITION_ORDINAL_INVALID")
        path = f"recovery-transitions/{ordinal:04d}.json"
        payload = files.get(path)
        if payload is None:
            raise IntegrationError("TRANSITION_RECORD_MISSING")
        if (
            entry.get("path") != path
            or entry.get("byte_count") != len(payload)
            or entry.get("sha256") != sha256(payload)
            or entry.get("previous_sha256") != previous
        ):
            raise IntegrationError("TRANSITION_PROJECTION_MISMATCH")
        value = parse_canonical(payload)
        validate_shape("transition", value)
        if value["ordinal"] != ordinal or value["previous_sha256"] != previous:
            raise IntegrationError("TRANSITION_LINK_INVALID")
        previous = sha256(payload)
        _validate_transition_payload(value)
        transitions.append(value)
    actual_paths = sorted(
        path for path in files if path.startswith("recovery-transitions/")
    )
    expected_paths = [f"recovery-transitions/{i:04d}.json" for i in range(len(entries))]
    if actual_paths != expected_paths:
        raise IntegrationError("TRANSITION_INVENTORY_INVALID")
    return transitions


def _validate_transition_payload(value: Mapping[str, object]) -> None:
    transition_class = value["class"]
    data = value["data"]
    if not isinstance(data, dict):
        raise IntegrationError("TRANSITION_DATA_INVALID")
    allowed_shapes = {
        "PRIVATE_ROOT_CREATION_AUTHORIZED": {
            "attempt_ordinal",
            "operation",
            "private_root_id",
            "retry_permitted",
        },
        "PRIVATE_ROOT_CREATION_SUCCEEDED": {
            "attempt_ordinal",
            "authorization_sha256",
            "result",
            "private_root_id",
        },
        "PRIVATE_ROOT_CREATION_FAILED": {
            "attempt_ordinal",
            "authorization_sha256",
            "result",
        },
        "PRIVATE_ROOT_ABSENCE_OBSERVED": {
            "creation_result_sha256",
            "observation",
            "private_root_id",
        },
        "RECOVERY_ENTERED": {"creation_result_sha256", "reason"},
        "RECOVERY_CLEANUP_ATTEMPT": {"attempt_ordinal", "result", "residue"},
        "LOCATOR_REMOVAL_AUTHORIZED": None,
        "LOCATOR_ABSENT_CONFIRMED": {"authorization_sha256"},
    }
    if transition_class not in allowed_shapes:
        raise IntegrationError("TRANSITION_CLASS_INVALID")
    expected = allowed_shapes[transition_class]
    if transition_class == "LOCATOR_REMOVAL_AUTHORIZED":
        if set(data) not in ({"receipt_sha256"}, {"terminal_sha256"}):
            raise IntegrationError("TRANSITION_DATA_FIELDS_INVALID")
    elif set(data) != expected:
        raise IntegrationError("TRANSITION_DATA_FIELDS_INVALID")
    if transition_class == "PRIVATE_ROOT_CREATION_AUTHORIZED" and data != {
        "attempt_ordinal": 1,
        "operation": "CREATE_EXACT_PRIVATE_ROOT",
        "private_root_id": "synthetic-private-root-v1",
        "retry_permitted": False,
    }:
        raise IntegrationError("CREATION_AUTH_VALUES_INVALID")
    if transition_class == "PRIVATE_ROOT_CREATION_SUCCEEDED" and (
        data.get("attempt_ordinal") != 1
        or data.get("result") != "SUCCEEDED"
        or data.get("private_root_id") != "synthetic-private-root-v1"
    ):
        raise IntegrationError("CREATION_SUCCESS_VALUES_INVALID")
    if transition_class == "PRIVATE_ROOT_CREATION_FAILED" and (
        data.get("attempt_ordinal") != 1 or data.get("result") != "FAILED"
    ):
        raise IntegrationError("CREATION_FAILURE_VALUES_INVALID")
    if transition_class == "PRIVATE_ROOT_ABSENCE_OBSERVED" and (
        data.get("observation") != "ABSENT_CONFIRMED"
        or data.get("private_root_id") != "synthetic-private-root-v1"
    ):
        raise IntegrationError("PRIVATE_ROOT_ABSENCE_VALUES_INVALID")
    if transition_class == "RECOVERY_ENTERED" and data.get("reason") != "OBSERVATION_OR_SETUP_FAILED":
        raise IntegrationError("RECOVERY_ENTERED_VALUES_INVALID")


def _transition(transitions: Iterable[Mapping[str, object]], name: str) -> Mapping[str, object]:
    matches = [value for value in transitions if value.get("class") == name]
    if len(matches) != 1:
        raise IntegrationError("TRANSITION_CLASS_CARDINALITY_INVALID")
    return matches[0]


def _projection_prefix_sha256(
    files: Mapping[str, bytes], end_ordinal: int
) -> str:
    projection = parse_canonical(files["recovery-transition-projection.json"])
    entries = projection.get("entries")
    if not isinstance(entries, list) or not 0 <= end_ordinal <= len(entries):
        raise IntegrationError("TRANSITION_PREFIX_INVALID")
    prefix = {
        "schema": SCHEMA_IDS["transition-projection"],
        "entries": copy.deepcopy(entries[:end_ordinal]),
    }
    validate_shape("transition-projection", prefix)
    return sha256(canonical_bytes(prefix))


def verify_captured_package(
    captured: CapturedByteSet, authority: VerificationAuthority
) -> dict[str, object]:
    if captured.evidence_level != EVIDENCE_LEVEL:
        raise IntegrationError("EVIDENCE_LEVEL_INVALID")
    files = dict(captured.entries)
    manifest_payload = files.get("tree-manifest.json")
    if manifest_payload is None:
        raise IntegrationError("MANIFEST_MISSING")
    if not isinstance(authority, VerificationAuthority):
        raise IntegrationError("VERIFICATION_AUTHORITY_MISSING")
    if authority.requested_evidence_level != EVIDENCE_LEVEL:
        raise IntegrationError("STRONGER_EVIDENCE_REQUEST_FORBIDDEN")
    if authority.expected_tree_manifest_sha256 != sha256(manifest_payload):
        raise IntegrationError("REVIEWED_MANIFEST_DIGEST_MISMATCH")
    retained_verifier = files.get("implementations/offline_verifier.py")
    command_contract = files.get("contracts/execution-command-contract.json")
    if retained_verifier is None or command_contract is None:
        raise IntegrationError("BOOTSTRAP_BYTES_MISSING")
    if authority.expected_verifier_sha256 != sha256(retained_verifier):
        raise IntegrationError("REVIEWED_VERIFIER_DIGEST_MISMATCH")
    if authority.expected_execution_command_contract_sha256 != sha256(command_contract):
        raise IntegrationError("REVIEWED_COMMAND_CONTRACT_DIGEST_MISMATCH")
    for path, expected_payload in COMMON_RETAINED_FILES.items():
        if path.startswith(("implementations/", "implementation-identities/")):
            continue
        if files.get(path) != expected_payload:
            raise IntegrationError("RETAINED_BOOTSTRAP_BYTES_MISMATCH")
    for name in RETAINED_IMPLEMENTATIONS:
        source_path = f"implementations/{name}"
        identity_path = f"implementation-identities/{name}.identity.json"
        source = files.get(source_path)
        identity_payload = files.get(identity_path)
        if source is None or identity_payload is None:
            raise IntegrationError("RETAINED_IMPLEMENTATION_BYTES_MISSING")
        identity = parse_canonical(identity_payload)
        if identity != {
            "schema": "gate3.synthetic.implementation-identity.v1",
            "implementation": name,
            "source_sha256": sha256(source),
            "execution_command_contract_sha256": sha256(command_contract),
            "claim": "CAPTURED_SOURCE_BYTES_ONLY",
        }:
            raise IntegrationError("RETAINED_IMPLEMENTATION_IDENTITY_INVALID")
    manifest = parse_canonical(manifest_payload)
    _load_schema(files, "manifest")
    validate_shape("manifest", manifest)
    profile = manifest["profile"]
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise IntegrationError("MANIFEST_ENTRIES_INVALID")
    expected = {
        entry["path"]: (entry["byte_count"], entry["sha256"])
        for entry in entries
        if isinstance(entry, dict) and set(entry) == {"path", "byte_count", "sha256"}
    }
    actual = set(files) - {"tree-manifest.json"}
    if set(expected) != actual or len(expected) != len(entries):
        raise IntegrationError("MANIFEST_INVENTORY_MISMATCH")
    for path, (count, digest) in expected.items():
        payload = files[path]
        if count != len(payload) or digest != sha256(payload):
            raise IntegrationError("MANIFEST_ENTRY_MISMATCH")
    mapping = _profile_mapping(str(profile), files)
    expected_inventory = set(mapping) | {
        f"schemas/{name}.schema.json" for name in set(mapping.values()) | {"manifest"}
    } | set(COMMON_RETAINED_FILES)
    if profile in {
        "FINALIZED_CHAIN",
        "RECOVERY_REQUIRED_NEGATIVE",
        "EXTERNAL_RECOVERY_CLOSED",
        "EXTERNAL_RECOVERY_OPEN",
    }:
        expected_inventory |= {
            path for path in files if path.startswith("recovery-transitions/")
        }
    if actual != expected_inventory:
        raise IntegrationError("PROFILE_INVENTORY_MISMATCH")
    parsed: dict[str, dict[str, object]] = {}
    for path, payload in files.items():
        if not path.endswith(".json") or path.startswith("schemas/") or path == "tree-manifest.json":
            continue
        value = parse_canonical(payload)
        validate_privacy(value)
        parsed[path] = value
    action = parsed.get("action.json")
    if action is None:
        raise IntegrationError("ACTION_MISSING")
    _load_schema(files, "action")
    validate_shape("action", action)
    action_digest = sha256(files["action.json"])
    expected_implementation_identities = {
        name: sha256(
            files[f"implementation-identities/{name}.identity.json"]
        )
        for name in sorted(RETAINED_IMPLEMENTATIONS)
    }
    if action["implementation_identities"] != expected_implementation_identities:
        raise IntegrationError("ACTION_IMPLEMENTATION_IDENTITIES_INVALID")
    if (
        action["execution_command_contract_sha256"]
        != sha256(files["contracts/execution-command-contract.json"])
        or action["privacy_contract_sha256"]
        != sha256(files["contracts/privacy-contract.json"])
        or action["recovery_contract_sha256"]
        != sha256(files["contracts/recovery-state-contract.json"])
    ):
        raise IntegrationError("ACTION_CONTRACT_LINK_INVALID")
    if profile in {
        "SETUP_TERMINAL_BEFORE_LOCATOR",
        "SETUP_TEMP_RESIDUE_OPEN",
        "SETUP_TEMP_ATTEMPT_UNKNOWN",
    }:
        terminal = parsed.get("external-terminal.json")
        if terminal is None:
            raise IntegrationError("EXTERNAL_TERMINAL_MISSING")
        _load_schema(files, "external-terminal")
        validate_shape("external-terminal", terminal)
        if terminal["action_sha256"] != action_digest:
            raise IntegrationError("EXTERNAL_ACTION_LINK_INVALID")
        forbidden = {
            "locator_disposition",
            "transition_projection_sha256",
        } & set(terminal)
        if forbidden:
            raise IntegrationError("SETUP_LOCATOR_FIELD_FORBIDDEN")
        if profile == "SETUP_TERMINAL_BEFORE_LOCATOR" and "setup-temp-snapshot.json" not in parsed:
            if terminal != {
                "schema": SCHEMA_IDS["external-terminal"],
                "action_sha256": action_digest,
                "origin_stage": "SETUP_BEFORE_LOCATOR",
                "code": "ACTION_PUBLISHED_LOCATOR_NOT_CREATED",
                "attempted": False,
                "attempt_count": 0,
                "result": "NOT_ATTEMPTED",
                "residue": "NOT_APPLICABLE",
            }:
                raise IntegrationError("SETUP_NO_TEMP_TERMINAL_INVALID")
        else:
            snapshot = parsed.get("setup-temp-snapshot.json")
            authorization = parsed.get("setup-temp-removal-authorization.json")
            if snapshot is None or authorization is None:
                raise IntegrationError("SETUP_TEMP_AUTHORITY_MISSING")
            for path, name in SETUP_TEMP_UNKNOWN_BASE.items():
                _load_schema(files, name)
                validate_shape(name, parsed[path])
            snapshot_digest = sha256(files["setup-temp-snapshot.json"])
            authorization_digest = sha256(
                files["setup-temp-removal-authorization.json"]
            )
            if snapshot["action_sha256"] != action_digest:
                raise IntegrationError("SETUP_TEMP_ACTION_LINK_INVALID")
            if authorization["snapshot_sha256"] != snapshot_digest:
                raise IntegrationError("SETUP_TEMP_AUTH_SNAPSHOT_LINK_INVALID")
            if authorization["attempt_ordinal"] != 1 or authorization["retry_permitted"] is not False:
                raise IntegrationError("SETUP_TEMP_AUTH_INVALID")
            if terminal.get("setup_temp_snapshot_sha256") != snapshot_digest or terminal.get(
                "removal_authorization_sha256"
            ) != authorization_digest:
                raise IntegrationError("SETUP_TEMP_TERMINAL_LINK_INVALID")
            if profile in {"SETUP_TERMINAL_BEFORE_LOCATOR", "SETUP_TEMP_RESIDUE_OPEN"}:
                result = parsed.get("setup-temp-removal-result.json")
                if result is None:
                    raise IntegrationError("SETUP_TEMP_RESULT_MISSING")
                _load_schema(files, "setup-temp-removal-result")
                validate_shape("setup-temp-removal-result", result)
                observation = result["absence_observation"]
                removed = profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
                expected_result = "PASS" if removed else "FAIL"
                expected_observation = "ABSENT_CONFIRMED" if removed else "PRESENT_CONFIRMED"
                expected_code = "LOCATOR_PUBLICATION_FAILED" if removed else "LOCATOR_TEMP_REMOVAL_FAILED"
                expected_residue = "ZERO_RESIDUE" if removed else "SETUP_TEMP_PRESENT"
                if (
                    result["authorization_sha256"] != authorization_digest
                    or result["attempt_ordinal"] != 1
                    or result["result"] != expected_result
                    or not isinstance(observation, dict)
                    or observation
                    != {
                        "observation": expected_observation,
                        "observed_temp_fixture_id": snapshot["temp_id"],
                    }
                    or terminal.get("removal_result_sha256")
                    != sha256(files["setup-temp-removal-result.json"])
                    or terminal["code"] != expected_code
                    or terminal["result"] != expected_result
                    or terminal["residue"] != expected_residue
                ):
                    raise IntegrationError("SETUP_TEMP_RESULT_INVALID")
            elif (
                "removal_result_sha256" in terminal
                or terminal["code"] != "LOCATOR_TEMP_REMOVAL_RESULT_UNAVAILABLE"
                or terminal["result"] != "UNKNOWN"
                or terminal["residue"] != "UNKNOWN"
            ):
                raise IntegrationError("SETUP_TEMP_UNKNOWN_INVALID")
        return {"evidence_level": EVIDENCE_LEVEL, "profile": profile, "verified": True}
    locator = parsed.get("locator-snapshot.json")
    if locator is None:
        raise IntegrationError("ROUTE_AUTHORITY_MISSING")
    _load_schema(files, "locator-snapshot")
    validate_shape("locator-snapshot", locator)
    locator_digest = sha256(files["locator-snapshot.json"])
    if locator["action_sha256"] != action_digest:
        raise IntegrationError("LOCATOR_ACTION_LINK_INVALID")
    transitions = _verify_transition_chain(files)
    auth = _transition(transitions, "PRIVATE_ROOT_CREATION_AUTHORIZED")
    auth_data = auth["data"]
    if not isinstance(auth_data, dict) or auth["locator_sha256"] != locator_digest:
        raise IntegrationError("CREATION_AUTH_LOCATOR_LINK_INVALID")
    if auth_data.get("retry_permitted") is not False or auth_data.get("attempt_ordinal") != 1:
        raise IntegrationError("CREATION_AUTH_INVALID")
    if profile in {"FINALIZED_CHAIN", "RECOVERY_REQUIRED_NEGATIVE"}:
        missing = set(ROUTE_BASE) - set(parsed)
        if missing:
            raise IntegrationError("ROUTE_ARTIFACT_MISSING")
        success = _transition(transitions, "PRIVATE_ROOT_CREATION_SUCCEEDED")
        data = success["data"]
        if not isinstance(data, dict) or data.get("authorization_sha256") != sha256(
            files[f"recovery-transitions/{auth['ordinal']:04d}.json"]
        ):
            raise IntegrationError("CREATION_RESULT_LINK_INVALID")
        if data.get("private_root_id") != locator["private_root_id"]:
            raise IntegrationError("CREATION_ROOT_IDENTITY_INVALID")
        for path, name in ROUTE_BASE.items():
            _load_schema(files, name)
            validate_shape(name, parsed[path])
        fixture = parsed["lifecycle-fixture.json"]
        fixture_id = fixture.get("fixture_id")
        raw_fixture_path = f"fixtures/raw/{fixture_id}.json"
        expected_fixture_path = f"fixtures/expected-lifecycle/{fixture_id}.json"
        if fixture_id not in {
            "synthetic-final-created-v1",
            "synthetic-no-final-message-v1",
        } or files["lifecycle-fixture.json"] != files[raw_fixture_path]:
            raise IntegrationError("RETAINED_RAW_FIXTURE_MISMATCH")
        if files["expected-lifecycle-projection.json"] != files[
            expected_fixture_path
        ]:
            raise IntegrationError("RETAINED_EXPECTED_FIXTURE_MISMATCH")
        expected_lifecycle = canonical_bytes(replay_lifecycle_fixture(fixture).projection())
        if files["expected-lifecycle-projection.json"] != expected_lifecycle:
            raise IntegrationError("EXPECTED_LIFECYCLE_REPLAY_MISMATCH")
        if files["lifecycle-projection.json"] != expected_lifecycle:
            raise IntegrationError("LIFECYCLE_REPLAY_MISMATCH")
        seal = parsed["observation-seal.json"]
        cleanup = parsed["cleanup-result.json"]
        receipt = parsed["final-receipt.json"]
        if seal["action_sha256"] != action_digest or seal["locator_sha256"] != locator_digest:
            raise IntegrationError("SEAL_AUTHORITY_LINK_INVALID")
        if seal["lifecycle_sha256"] != sha256(files["lifecycle-projection.json"]):
            raise IntegrationError("SEAL_LIFECYCLE_LINK_INVALID")
        if (
            seal["raw_script_sha256"] != sha256(files["lifecycle-fixture.json"])
            or seal["topology_sha256"]
            != sha256(canonical_bytes(fixture["topology"]))
            or seal["observer_implementation_sha256"]
            != sha256(files["implementations/lifecycle_observer.py"])
            or seal["observer_contract_sha256"]
            != sha256(files["contracts/lifecycle-observer-contract.json"])
        ):
            raise IntegrationError("SEAL_OBSERVER_BINDING_INVALID")
        if seal["cleanup_state"] != "PENDING" or seal["receipt_state"] != "PENDING":
            raise IntegrationError("SEAL_MUTATED")
        if cleanup["action_sha256"] != action_digest or cleanup["observation_seal_sha256"] != sha256(files["observation-seal.json"]):
            raise IntegrationError("CLEANUP_SEAL_LINK_INVALID")
        if receipt["action_sha256"] != action_digest or receipt["observation_seal_sha256"] != sha256(files["observation-seal.json"]):
            raise IntegrationError("RECEIPT_SEAL_LINK_INVALID")
        if receipt["cleanup_result_sha256"] != sha256(files["cleanup-result.json"]):
            raise IntegrationError("RECEIPT_CLEANUP_LINK_INVALID")
        if (
            type(cleanup["attempted"]) is not bool
            or type(cleanup["attempt_count"]) is not int
            or (
                cleanup["attempted"] is True
                and (
                    not 1 <= cleanup["attempt_count"] <= action["max_cleanup_attempts"]
                    or cleanup["result"] not in {"PASS", "FAIL", "PARTIAL"}
                )
            )
            or (
                cleanup["attempted"] is False
                and not (
                    cleanup["attempt_count"] == 0
                    and cleanup["result"] == "NOT_ATTEMPTED"
                    and cleanup["residue"] == "UNKNOWN"
                    and cleanup["failure_code"] == "IDENTITY_UNAVAILABLE"
                    and cleanup["locator_disposition"] == "RETAINED"
                )
            )
            or (cleanup["result"] == "PASS")
            != (
                cleanup["residue"] == "ZERO_RESIDUE"
                and cleanup["failure_code"] == "NONE"
                and cleanup["locator_disposition"] == "RETAINED_PENDING_FINALIZATION"
            )
            or (
                cleanup["result"] in {"FAIL", "PARTIAL"}
                and (
                    cleanup["residue"] not in {"RESIDUE_PRESENT", "UNKNOWN"}
                    or cleanup["failure_code"]
                    != (
                        "SYNTHETIC_CLEANUP_FAILED"
                        if cleanup["result"] == "FAIL"
                        else "SYNTHETIC_CLEANUP_PARTIAL"
                    )
                    or cleanup["locator_disposition"] != "RETAINED"
                )
            )
        ):
            raise IntegrationError("CLEANUP_MATRIX_INVALID")
        if receipt["counted"] is not False:
            raise IntegrationError("RECEIPT_COUNTED_INVALID")
        if receipt["claim_ceiling"] != EVIDENCE_LEVEL or receipt["implementation_identities"] != action["implementation_identities"]:
            raise IntegrationError("RECEIPT_IDENTITY_OR_CLAIM_INVALID")
        expected_classification = classify_synthetic(parsed["lifecycle-projection.json"])
        if seal["classification"] != expected_classification or receipt["classification"] != expected_classification:
            raise IntegrationError("CLASSIFICATION_RECONSTRUCTION_MISMATCH")
        expected_classes = expected_classification["diagnostic_classes"]
        classification_negative = (
            "CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED" in expected_classes
        )
        cleanup_negative = (
            cleanup["result"] in {"FAIL", "PARTIAL"}
            and cleanup["residue"] in {"RESIDUE_PRESENT", "UNKNOWN"}
        ) or (
            cleanup["result"] == "NOT_ATTEMPTED"
            and cleanup["residue"] == "UNKNOWN"
        )
        expected_negative = classification_negative or cleanup_negative
        expected_disposition = (
            "NEGATIVE_RECEIPT" if expected_negative else "DIAGNOSTIC_RECEIPT"
        )
        if (
            receipt["terminal_disposition"] != expected_disposition
            or receipt["overall_result"]
            != ("DIAGNOSTIC_NEGATIVE" if expected_negative else "DIAGNOSTIC_COMPLETE")
            or receipt["cleanup_disposition"] != cleanup["result"]
            or receipt["residue"] != cleanup["residue"]
        ):
            raise IntegrationError("RECEIPT_CLASSIFICATION_DISPOSITION_MISMATCH")
        if profile == "FINALIZED_CHAIN":
            if (
                cleanup["result"] != "PASS"
                or cleanup["residue"] != "ZERO_RESIDUE"
                or receipt["locator_state"] != "RETAINED_PENDING_FINALIZATION"
            ):
                raise IntegrationError("DIAGNOSTIC_RECEIPT_MATRIX_INVALID")
            finalization = parsed.get("finalization.json")
            if finalization is None:
                raise IntegrationError("FINALIZATION_MISSING")
            _load_schema(files, "finalization")
            validate_shape("finalization", finalization)
            if finalization["final_receipt_sha256"] != sha256(files["final-receipt.json"]):
                raise IntegrationError("FINALIZATION_RECEIPT_LINK_INVALID")
            if (
                finalization["action_sha256"] != action_digest
                or finalization["observation_seal_sha256"] != sha256(files["observation-seal.json"])
                or finalization["cleanup_result_sha256"] != sha256(files["cleanup-result.json"])
                or finalization["residue"] != "ZERO_RESIDUE"
                or finalization["locator_before"] != "RETAINED_PENDING_FINALIZATION"
                or finalization["terminal_class"]
                != (
                    "FINALIZED_NEGATIVE"
                    if expected_negative
                    else "FINALIZED_DIAGNOSTIC"
                )
            ):
                raise IntegrationError("FINALIZATION_MATRIX_INVALID")
            if finalization["transition_projection_sha256"] != sha256(
                files["recovery-transition-projection.json"]
            ):
                raise IntegrationError("FINALIZATION_TRANSITION_LINK_INVALID")
            if finalization["locator_after"] != "ABSENT_CONFIRMED":
                raise IntegrationError("FINALIZATION_STATE_INVALID")
            removal = _transition(transitions, "LOCATOR_REMOVAL_AUTHORIZED")
            absent = _transition(transitions, "LOCATOR_ABSENT_CONFIRMED")
            removal_data = removal.get("data")
            absent_data = absent.get("data")
            if not isinstance(removal_data, dict) or removal_data.get("receipt_sha256") != sha256(
                files["final-receipt.json"]
            ):
                raise IntegrationError("REMOVAL_AUTH_RECEIPT_LINK_INVALID")
            if not isinstance(absent_data, dict) or absent_data.get("authorization_sha256") != sha256(
                files[f"recovery-transitions/{removal['ordinal']:04d}.json"]
            ):
                raise IntegrationError("ABSENCE_AUTH_LINK_INVALID")
        elif "finalization.json" in files:
            raise IntegrationError("NEGATIVE_FINALIZATION_FORBIDDEN")
        elif (
            receipt["terminal_disposition"] != "NEGATIVE_RECEIPT"
            or receipt["locator_state"] != "RETAINED"
            or cleanup["result"] not in {"FAIL", "PARTIAL", "NOT_ATTEMPTED"}
            or cleanup["residue"] not in {"RESIDUE_PRESENT", "UNKNOWN"}
        ):
            raise IntegrationError("NEGATIVE_RECEIPT_MATRIX_INVALID")
    elif profile in {"EXTERNAL_RECOVERY_CLOSED", "EXTERNAL_RECOVERY_OPEN"}:
        terminal = parsed.get("external-terminal.json")
        if terminal is None:
            raise IntegrationError("EXTERNAL_TERMINAL_MISSING")
        for path, name in EXTERNAL_BASE.items():
            _load_schema(files, name)
            validate_shape(name, parsed[path])
        if terminal["action_sha256"] != action_digest:
            raise IntegrationError("EXTERNAL_ACTION_LINK_INVALID")
        if terminal.get("locator_snapshot_sha256") != locator_digest:
            raise IntegrationError("EXTERNAL_LOCATOR_LINK_INVALID")
        attempts = [
            item for item in transitions if item.get("class") == "RECOVERY_CLEANUP_ATTEMPT"
        ]
        creation_results = [
            item
            for item in transitions
            if item.get("class")
            in {"PRIVATE_ROOT_CREATION_SUCCEEDED", "PRIVATE_ROOT_CREATION_FAILED"}
        ]
        auth_digest = sha256(
            files[f"recovery-transitions/{auth['ordinal']:04d}.json"]
        )
        if len(creation_results) > 1:
            raise IntegrationError("CREATION_RESULT_CARDINALITY_INVALID")
        if not creation_results:
            if attempts or terminal["code"] != "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE":
                raise IntegrationError("CREATION_UNKNOWN_CLEANUP_FORBIDDEN")
        else:
            creation_result = creation_results[0]
            result_data = creation_result.get("data")
            if (
                not isinstance(result_data, dict)
                or result_data.get("authorization_sha256") != auth_digest
                or result_data.get("attempt_ordinal") != 1
            ):
                raise IntegrationError("CREATION_RESULT_LINK_INVALID")
            if creation_result["class"] == "PRIVATE_ROOT_CREATION_FAILED" and attempts:
                raise IntegrationError("CREATION_FAILED_CLEANUP_FORBIDDEN")
            recovery_entries = [
                item for item in transitions if item.get("class") == "RECOVERY_ENTERED"
            ]
            if creation_result["class"] == "PRIVATE_ROOT_CREATION_SUCCEEDED":
                if len(recovery_entries) != 1:
                    raise IntegrationError("RECOVERY_ENTRY_CARDINALITY_INVALID")
                recovery_data = recovery_entries[0].get("data")
                creation_result_digest = sha256(
                    files[
                        f"recovery-transitions/{creation_result['ordinal']:04d}.json"
                    ]
                )
                if (
                    not isinstance(recovery_data, dict)
                    or recovery_data.get("creation_result_sha256")
                    != creation_result_digest
                    or recovery_entries[0]["ordinal"] >= (
                        attempts[0]["ordinal"] if attempts else len(transitions)
                    )
                    or terminal["code"]
                    not in {
                        "NO_ADMISSIBLE_SEAL_CLEANED",
                        "NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED",
                        "RECOVERY_IDENTITY_UNAVAILABLE",
                    }
                ):
                    raise IntegrationError("RECOVERY_ENTRY_OR_SUCCESS_CODE_INVALID")
            elif recovery_entries:
                raise IntegrationError("RECOVERY_ENTRY_FORBIDDEN")
            if creation_result["class"] == "PRIVATE_ROOT_CREATION_FAILED":
                absences = [
                    item
                    for item in transitions
                    if item.get("class") == "PRIVATE_ROOT_ABSENCE_OBSERVED"
                ]
                if len(absences) > 1:
                    raise IntegrationError("PRIVATE_ROOT_ABSENCE_CARDINALITY_INVALID")
                if absences:
                    absence_data = absences[0].get("data")
                    result_digest = sha256(
                        files[
                            f"recovery-transitions/{creation_result['ordinal']:04d}.json"
                        ]
                    )
                    if (
                        not isinstance(absence_data, dict)
                        or absence_data.get("creation_result_sha256") != result_digest
                        or terminal["code"]
                        != "LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED"
                    ):
                        raise IntegrationError("PRIVATE_ROOT_ABSENCE_LINK_INVALID")
                elif terminal["code"] != "PRIVATE_ROOT_ABSENCE_UNCONFIRMED":
                    raise IntegrationError("PRIVATE_ROOT_ABSENCE_TERMINAL_INVALID")
        if (
            len(attempts) != terminal["attempt_count"]
            or bool(attempts) is not terminal["attempted"]
            or not isinstance(terminal["attempt_count"], int)
            or terminal["attempt_count"] > action["max_cleanup_attempts"]
        ):
            raise IntegrationError("EXTERNAL_ATTEMPT_COUNT_INVALID")
        for expected_ordinal, attempt in enumerate(attempts, 1):
            data = attempt.get("data")
            if not isinstance(data, dict) or data.get("attempt_ordinal") != expected_ordinal:
                raise IntegrationError("EXTERNAL_ATTEMPT_ORDINAL_INVALID")
        if attempts:
            last_data = attempts[-1].get("data")
            if not isinstance(last_data, dict) or last_data.get("result") != terminal["result"] or last_data.get("residue") != terminal["residue"]:
                raise IntegrationError("EXTERNAL_ATTEMPT_RESULT_MISMATCH")
        code_rows: dict[str, tuple[bool, object, str, str, str]] = {
            "NO_ADMISSIBLE_SEAL_CLEANED": (
                True,
                "positive",
                "PASS",
                "ZERO_RESIDUE",
                "RETAINED_PENDING_REMOVAL",
            ),
            "NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED": (
                True,
                "positive",
                "FAIL_OR_PARTIAL",
                "NONZERO_OR_UNKNOWN",
                "RETAINED",
            ),
            "RECOVERY_IDENTITY_UNAVAILABLE": (
                False,
                0,
                "NOT_ATTEMPTED",
                "UNKNOWN",
                "RETAINED",
            ),
            "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE": (
                False,
                0,
                "NOT_ATTEMPTED",
                "UNKNOWN",
                "RETAINED",
            ),
            "PRIVATE_ROOT_ABSENCE_UNCONFIRMED": (
                False,
                0,
                "NOT_ATTEMPTED",
                "UNKNOWN",
                "RETAINED",
            ),
            "LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED": (
                False,
                0,
                "NOT_ATTEMPTED",
                "ZERO_RESIDUE",
                "RETAINED_PENDING_REMOVAL",
            ),
        }
        row = code_rows.get(str(terminal["code"]))
        if row is None:
            raise IntegrationError("EXTERNAL_TERMINAL_CODE_INVALID")
        expected_attempted, count_rule, result_rule, residue_rule, disposition = row
        if terminal["attempted"] is not expected_attempted:
            raise IntegrationError("EXTERNAL_TERMINAL_ROW_INVALID")
        if (count_rule == 0 and terminal["attempt_count"] != 0) or (
            count_rule == "positive" and terminal["attempt_count"] < 1
        ):
            raise IntegrationError("EXTERNAL_TERMINAL_ROW_INVALID")
        if (
            (result_rule == "FAIL_OR_PARTIAL" and terminal["result"] not in {"FAIL", "PARTIAL"})
            or (result_rule != "FAIL_OR_PARTIAL" and terminal["result"] != result_rule)
            or (
                residue_rule == "NONZERO_OR_UNKNOWN"
                and terminal["residue"] not in {"RESIDUE_PRESENT", "UNKNOWN"}
            )
            or (
                residue_rule != "NONZERO_OR_UNKNOWN"
                and terminal["residue"] != residue_rule
            )
            or terminal["locator_disposition"] != disposition
        ):
            raise IntegrationError("EXTERNAL_TERMINAL_ROW_INVALID")
        if profile == "EXTERNAL_RECOVERY_CLOSED":
            finalization = parsed.get("external-recovery-finalization.json")
            if finalization is None:
                raise IntegrationError("EXTERNAL_FINALIZATION_MISSING")
            _load_schema(files, "external-finalization")
            validate_shape("external-finalization", finalization)
            if (
                terminal["code"]
                not in {
                    "NO_ADMISSIBLE_SEAL_CLEANED",
                    "LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED",
                }
                or terminal["locator_disposition"] != "RETAINED_PENDING_REMOVAL"
            ):
                raise IntegrationError("EXTERNAL_CLOSED_MATRIX_INVALID")
            removal = _transition(transitions, "LOCATOR_REMOVAL_AUTHORIZED")
            absent = _transition(transitions, "LOCATOR_ABSENT_CONFIRMED")
            removal_data = removal.get("data")
            absent_data = absent.get("data")
            if not isinstance(removal_data, dict) or removal_data.get("terminal_sha256") != sha256(
                files["external-terminal.json"]
            ):
                raise IntegrationError("EXTERNAL_REMOVAL_AUTH_LINK_INVALID")
            if not isinstance(absent_data, dict) or absent_data.get("authorization_sha256") != sha256(
                files[f"recovery-transitions/{removal['ordinal']:04d}.json"]
            ):
                raise IntegrationError("EXTERNAL_ABSENCE_LINK_INVALID")
            if terminal["transition_projection_sha256"] != _projection_prefix_sha256(
                files, removal["ordinal"]
            ):
                raise IntegrationError("EXTERNAL_TRANSITION_PREFIX_LINK_INVALID")
            if finalization["terminal_sha256"] != sha256(files["external-terminal.json"]):
                raise IntegrationError("EXTERNAL_FINALIZATION_TERMINAL_LINK_INVALID")
            if finalization["locator_sha256"] != locator_digest:
                raise IntegrationError("EXTERNAL_FINALIZATION_LOCATOR_LINK_INVALID")
            if (
                finalization["action_sha256"] != action_digest
                or finalization["recovery_finalizer_sha256"]
                != sha256(files["implementations/recovery_finalizer.py"])
                or finalization["verifier_sha256"]
                != sha256(files["implementations/offline_verifier.py"])
                or finalization["terminal_class"] != "EXTERNAL_RECOVERY_CLOSED"
            ):
                raise IntegrationError("EXTERNAL_FINALIZATION_IDENTITY_INVALID")
            if finalization["transition_projection_sha256"] != sha256(
                files["recovery-transition-projection.json"]
            ):
                raise IntegrationError("EXTERNAL_FINALIZATION_TRANSITION_LINK_INVALID")
            if finalization["locator_after"] != "ABSENT_CONFIRMED":
                raise IntegrationError("EXTERNAL_FINALIZATION_STATE_INVALID")
        elif "external-recovery-finalization.json" in files:
            raise IntegrationError("EXTERNAL_OPEN_FINALIZATION_FORBIDDEN")
        elif (
            terminal["code"]
            not in {
                "NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED",
                "RECOVERY_IDENTITY_UNAVAILABLE",
                "PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE",
                "PRIVATE_ROOT_ABSENCE_UNCONFIRMED",
                "LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED",
            }
            or terminal["result"] not in {"FAIL", "PARTIAL", "NOT_ATTEMPTED"}
            or terminal["residue"] not in {"RESIDUE_PRESENT", "UNKNOWN"}
            or terminal["locator_disposition"] != "RETAINED"
            or terminal["transition_projection_sha256"]
            != sha256(files["recovery-transition-projection.json"])
        ):
            raise IntegrationError("EXTERNAL_OPEN_MATRIX_INVALID")
    else:
        raise IntegrationError("PROFILE_UNKNOWN")
    return {"evidence_level": EVIDENCE_LEVEL, "profile": profile, "verified": True}


def verify_public(
    value: object, authority: VerificationAuthority | None = None
) -> dict[str, object]:
    """Never-raises fail-closed verifier envelope for untrusted inputs."""

    try:
        if not isinstance(value, CapturedByteSet):
            raise IntegrationError("CAPTURE_DESCRIPTOR_INVALID")
        if authority is None:
            raise IntegrationError("VERIFICATION_AUTHORITY_MISSING")
        return verify_captured_package(value, authority)
    except BaseException as exc:
        code = exc.code if isinstance(exc, IntegrationError) else "VERIFICATION_INPUT_INVALID"
        if code in {
            "VERIFICATION_AUTHORITY_MISSING",
            "STRONGER_EVIDENCE_REQUEST_FORBIDDEN",
            "REVIEWED_MANIFEST_DIGEST_MISMATCH",
            "REVIEWED_VERIFIER_DIGEST_MISMATCH",
            "REVIEWED_COMMAND_CONTRACT_DIGEST_MISMATCH",
            "BOOTSTRAP_BYTES_MISSING",
        }:
            code = "VERIFICATION_UNAVAILABLE"
        return {
            "code": code,
            "evidence_level": EVIDENCE_LEVEL,
            "verified": False,
        }


def build_complete_route(profile: str = "FINALIZED_CHAIN") -> dict[str, bytes]:
    integration = SyntheticIntegration()
    integration.publish_action()
    integration.publish_locator()
    authorization = integration.authorize_creation()
    integration.record_creation(authorization, "SUCCEEDED")
    lifecycle_fixture = (
        build_absent_lifecycle_fixture()
        if profile == "RECOVERY_REQUIRED_NEGATIVE"
        else build_lifecycle_fixture()
    )
    lifecycle = integration.publish_lifecycle(lifecycle_fixture)
    seal = integration.publish_seal(lifecycle)
    if profile == "FINALIZED_CHAIN":
        cleanup = integration.publish_cleanup(seal, "PASS", "ZERO_RESIDUE")
        receipt = integration.publish_receipt(seal, cleanup)
        integration.finalize_route(receipt)
    elif profile == "RECOVERY_REQUIRED_NEGATIVE":
        cleanup = integration.publish_cleanup(seal, "FAIL", "UNKNOWN")
        integration.publish_receipt(seal, cleanup, negative=True)
        integration.publish_transition_projection()
    else:
        raise IntegrationError("PROFILE_UNKNOWN")
    return build_package(integration.store, profile)


def build_external(profile: str = "EXTERNAL_RECOVERY_OPEN") -> dict[str, bytes]:
    integration = SyntheticIntegration()
    integration.publish_action()
    integration.publish_locator()
    authorization = integration.authorize_creation()
    creation_result = integration.record_creation(authorization, "SUCCEEDED")
    if integration.chain is None:
        raise IntegrationError("TRANSITIONS_REQUIRED")
    integration.chain.append(
        "RECOVERY_ENTERED",
        {
            "creation_result_sha256": creation_result,
            "reason": "OBSERVATION_OR_SETUP_FAILED",
        },
    )
    if profile == "EXTERNAL_RECOVERY_CLOSED":
        integration.chain.append(
            "RECOVERY_CLEANUP_ATTEMPT",
            {"attempt_ordinal": 1, "result": "PASS", "residue": "ZERO_RESIDUE"},
        )
        terminal = integration.publish_external_terminal(
            "NO_ADMISSIBLE_SEAL_CLEANED", result="PASS", residue="ZERO_RESIDUE"
        )
        integration.finalize_external(terminal)
    elif profile == "EXTERNAL_RECOVERY_OPEN":
        integration.chain.append(
            "RECOVERY_CLEANUP_ATTEMPT",
            {"attempt_ordinal": 1, "result": "FAIL", "residue": "UNKNOWN"},
        )
        integration.publish_external_terminal("NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED")
    else:
        raise IntegrationError("PROFILE_UNKNOWN")
    return build_package(integration.store, profile)


def build_setup_external(
    profile: str, *, temp_removed: bool = False, store: CreateOnceStore | None = None
) -> dict[str, bytes]:
    integration = SyntheticIntegration(store=store or CreateOnceStore())
    action_sha256 = integration.publish_action()
    if profile == "SETUP_TERMINAL_BEFORE_LOCATOR" and not temp_removed:
        terminal = {
            "schema": SCHEMA_IDS["external-terminal"],
            "action_sha256": action_sha256,
            "origin_stage": "SETUP_BEFORE_LOCATOR",
            "code": "ACTION_PUBLISHED_LOCATOR_NOT_CREATED",
            "attempted": False,
            "attempt_count": 0,
            "result": "NOT_ATTEMPTED",
            "residue": "NOT_APPLICABLE",
        }
    elif profile in {
        "SETUP_TERMINAL_BEFORE_LOCATOR",
        "SETUP_TEMP_RESIDUE_OPEN",
        "SETUP_TEMP_ATTEMPT_UNKNOWN",
    }:
        snapshot = {
            "schema": SCHEMA_IDS["setup-temp-snapshot"],
            "action_sha256": action_sha256,
            "temp_id": "synthetic-setup-temp-v1",
            "purpose": "LOCATOR_PUBLICATION_TEMP",
        }
        validate_shape("setup-temp-snapshot", snapshot)
        snapshot_sha256 = integration.store.publish("setup-temp-snapshot.json", snapshot)
        authorization = {
            "schema": SCHEMA_IDS["setup-temp-removal-authorization"],
            "snapshot_sha256": snapshot_sha256,
            "attempt_ordinal": 1,
            "operation": "REMOVE_EXACT_SETUP_TEMP",
            "retry_permitted": False,
        }
        validate_shape("setup-temp-removal-authorization", authorization)
        authorization_sha256 = integration.store.publish(
            "setup-temp-removal-authorization.json", authorization
        )
        terminal = {
            "schema": SCHEMA_IDS["external-terminal"],
            "action_sha256": action_sha256,
            "origin_stage": (
                "SETUP_BEFORE_LOCATOR"
                if profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
                else (
                    "SETUP_TEMP_RESIDUE"
                    if profile == "SETUP_TEMP_RESIDUE_OPEN"
                    else "SETUP_TEMP_ATTEMPT_UNKNOWN"
                )
            ),
            "code": (
                "LOCATOR_PUBLICATION_FAILED"
                if profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
                else (
                    "LOCATOR_TEMP_REMOVAL_FAILED"
                    if profile == "SETUP_TEMP_RESIDUE_OPEN"
                    else "LOCATOR_TEMP_REMOVAL_RESULT_UNAVAILABLE"
                )
            ),
            "attempted": True,
            "attempt_count": 1,
            "result": (
                "PASS"
                if profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
                else ("FAIL" if profile == "SETUP_TEMP_RESIDUE_OPEN" else "UNKNOWN")
            ),
            "residue": (
                "ZERO_RESIDUE"
                if profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
                else (
                    "SETUP_TEMP_PRESENT"
                    if profile == "SETUP_TEMP_RESIDUE_OPEN"
                    else "UNKNOWN"
                )
            ),
            "setup_temp_snapshot_sha256": snapshot_sha256,
            "removal_authorization_sha256": authorization_sha256,
        }
        if profile in {"SETUP_TERMINAL_BEFORE_LOCATOR", "SETUP_TEMP_RESIDUE_OPEN"}:
            removed = profile == "SETUP_TERMINAL_BEFORE_LOCATOR"
            removal_result = {
                "schema": SCHEMA_IDS["setup-temp-removal-result"],
                "authorization_sha256": authorization_sha256,
                "attempt_ordinal": 1,
                "result": "PASS" if removed else "FAIL",
                "absence_observation": {
                    "observation": "ABSENT_CONFIRMED" if removed else "PRESENT_CONFIRMED",
                    "observed_temp_fixture_id": "synthetic-setup-temp-v1",
                },
            }
            validate_shape("setup-temp-removal-result", removal_result)
            terminal["removal_result_sha256"] = integration.store.publish(
                "setup-temp-removal-result.json", removal_result
            )
    else:
        raise IntegrationError("PROFILE_UNKNOWN")
    validate_shape("external-terminal", terminal)
    validate_privacy(terminal)
    integration.store.publish("external-terminal.json", terminal)
    return build_package(integration.store, profile)


def reconstruct_restart_state(retained: CreateOnceStore) -> dict[str, object]:
    """Derive the only admissible restart disposition from retained bytes."""

    subject = SyntheticIntegration.reopen(retained)
    files = subject.store.files
    if subject.action_sha256 is None:
        return {"state": "BEFORE_ACTION", "next": "PUBLISH_ACTION"}
    if "external-terminal.json" in files and subject.locator_sha256 is None:
        terminal = parse_canonical(files["external-terminal.json"])
        validate_shape("external-terminal", terminal)
        if terminal["action_sha256"] != subject.action_sha256:
            raise IntegrationError("RESTART_TERMINAL_LINK_INVALID")
        if terminal["origin_stage"] == "SETUP_TEMP_ATTEMPT_UNKNOWN":
            return {"state": "SETUP_TEMP_ATTEMPT_UNKNOWN", "next": "NO_RETRY"}
        if terminal["origin_stage"] == "SETUP_TEMP_RESIDUE":
            return {"state": "SETUP_TEMP_RESIDUE_OPEN", "next": "NO_RETRY"}
        return {"state": "SETUP_TERMINAL_BEFORE_LOCATOR", "next": "TERMINAL"}
    if subject.locator_sha256 is None:
        if "setup-temp-removal-result.json" in files and "external-terminal.json" not in files:
            return {"state": "SETUP_TEMP_RESULT_DURABLE", "next": "PUBLISH_TERMINAL_ONCE"}
        if "setup-temp-removal-authorization.json" in files and "setup-temp-removal-result.json" not in files:
            return {"state": "SETUP_TEMP_AUTHORIZED_RESULT_UNKNOWN", "next": "NO_RETRY"}
        if "setup-temp-snapshot.json" in files:
            return {"state": "SETUP_TEMP_SNAPSHOT_DURABLE", "next": "AUTHORIZE_REMOVAL_ONCE"}
        return {"state": "ACTION_DURABLE", "next": "PUBLISH_LOCATOR_ONCE"}
    if subject.chain is None or not subject.chain.digests:
        return {"state": "LOCATOR_READY", "next": "AUTHORIZE_CREATION_ONCE"}
    transitions = [
        parse_canonical(files[f"recovery-transitions/{ordinal:04d}.json"])
        for ordinal in range(len(subject.chain.digests))
    ]
    classes = [str(item["class"]) for item in transitions]
    if classes == ["PRIVATE_ROOT_CREATION_AUTHORIZED"]:
        return {"state": "CREATION_RESULT_UNKNOWN", "next": "NO_RETRY"}
    if "PRIVATE_ROOT_CREATION_FAILED" in classes:
        return {"state": "CREATION_FAILED", "next": "OBSERVE_ABSENCE_ONLY"}
    if "PRIVATE_ROOT_CREATION_SUCCEEDED" not in classes:
        raise IntegrationError("RESTART_CREATION_RESULT_MISSING")
    if "external-terminal.json" in files:
        if "external-recovery-finalization.json" in files:
            return {"state": "EXTERNAL_RECOVERY_CLOSED", "next": "TERMINAL"}
        if "recovery-transition-projection.json" not in files:
            return {"state": "EXTERNAL_TERMINAL_DURABLE", "next": "PUBLISH_PROJECTION_ONCE"}
        return {"state": "EXTERNAL_RECOVERY_OPEN", "next": "TERMINAL"}
    if "lifecycle-fixture.json" not in files:
        return {"state": "CREATION_SUCCEEDED", "next": "START_OBSERVER"}
    if "observation-seal.json" not in files:
        return {"state": "OBSERVATION_CAPTURED", "next": "PUBLISH_SEAL_ONCE"}
    if "cleanup-result.json" not in files:
        return {"state": "SEALED", "next": "CLEANUP_ONCE"}
    if "final-receipt.json" not in files:
        return {"state": "CLEANUP_RECORDED", "next": "PUBLISH_RECEIPT_ONCE"}
    receipt = parse_canonical(files["final-receipt.json"])
    validate_shape("receipt", receipt)
    if "finalization.json" in files:
        return {"state": "FINALIZED_CHAIN", "next": "TERMINAL"}
    if receipt["terminal_disposition"] == "NEGATIVE_RECEIPT":
        return {"state": "RECOVERY_REQUIRED_NEGATIVE", "next": "NO_ROUTE_FINALIZATION"}
    return {"state": "RECEIPT_PENDING_FINALIZATION", "next": "FINALIZE_ONCE"}
