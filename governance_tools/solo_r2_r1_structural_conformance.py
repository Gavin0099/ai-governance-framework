#!/usr/bin/env python3
"""Deterministic structural-conformance evidence for Solo Evaluation R2.

This inspector parses source bytes with :mod:`ast`; it never imports or executes
the inspected R2 modules.  Its output records reproducible machine facts only.
Reviewer identity, review time, and human disposition belong to the later
exact-identity review and Git durability layers.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Final, Iterable, Mapping, Sequence


R1_CONFORMANCE_FAILURE: Final = "R1_CONFORMANCE_FAILURE / STOP"
R1_EVIDENCE_WRITE_FAILURE: Final = "R1_EVIDENCE_WRITE_FAILURE / STOP"
STRUCTURAL_CONFORMANCE_PASS: Final = "STRUCTURAL_CONFORMANCE_PASS"

SCHEMA_VERSION: Final = "solo_r2_r1_structural_conformance.v1"
ARTIFACT_TYPE: Final = "r1_structural_conformance_evidence"
SOURCE_SNAPSHOT_COMMIT: Final = "c763e738f754282f19c0e5b794dadaa0a44daa65"
TRANCHE4_IMPLEMENTATION_COMMIT: Final = (
    "99a01342fd530f6cb03ff4d6c5af8de9e755d5c0"
)
SAMPLING_ROLE: Final = "REGRESSION_ONLY_NOT_PROOF"

INSPECTOR_RELPATH: Final = (
    "governance_tools/solo_r2_r1_structural_conformance.py"
)
EVIDENCE_RELPATH: Final = (
    "artifacts/evidence/solo-evaluation-20260831/"
    "r2-r1-structural-conformance-c763e738.json"
)
PREVIOUS_EVIDENCE_RELPATH: Final = (
    "artifacts/evidence/solo-evaluation-20260831/"
    "r2-r1-structural-conformance-de85d2f8.json"
)
EXCLUDED_VALIDATION_MODULES: Final = (INSPECTOR_RELPATH,)
EXCLUSION_REASON: Final = (
    "structural_conformance_inspector_not_runtime_participant"
)

_RUNTIME_MODULES: Final = (
    "governance_tools/solo_attempt_ledger_v2.py",
    "governance_tools/solo_attempt_ledger_v2_safe_verifier.py",
    "governance_tools/solo_r2_attempt_execution.py",
    "governance_tools/solo_r2_attempt_materialization.py",
    "governance_tools/solo_r2_blind_scoring_bundle.py",
    "governance_tools/solo_r2_bootstrap.py",
    "governance_tools/solo_r2_codex_runner.py",
    "governance_tools/solo_r2_controller_state.py",
    "governance_tools/solo_r2_disposable_binding.py",
    "governance_tools/solo_r2_disposable_execution.py",
    "governance_tools/solo_r2_disposable_materialization.py",
    "governance_tools/solo_r2_disposable_profile.py",
    "governance_tools/solo_r2_lifecycle_integration.py",
    "governance_tools/solo_r2_pair_creation.py",
    "governance_tools/solo_r2_random_domains.py",
    "governance_tools/solo_r2_runtime_window.py",
)
_OBSERVED_NAMESPACE: Final = tuple(sorted((*_RUNTIME_MODULES, INSPECTOR_RELPATH)))

_AUTHORITY_BINDINGS: Final = (
    {
        "role": "owner_adoption",
        "path": "docs/governance/solo-evaluation-revision-2-owner-adoption-20260831.md",
        "sha256": "6bf8eed7b4b585db08e0a7f0668ecc67aee41ff63a901095b8aec488c17caf66",
        "git_blob": "23fdbd6e28589f8b6ae43004f801b2bf8bd5560e",
        "commit": "662d5520b67b6acdd0bd714cf0f9ce6889b0233a",
        "anchors": ["Decision", "Authority boundary"],
    },
    {
        "role": "protocol",
        "path": "docs/governance/solo-engineering-skill-evaluation-protocol-revision-2-20260831.md",
        "sha256": "1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff",
        "git_blob": "1e774d9dcf4a4929162caa25822ca54bde7244b0",
        "commit": "4ba542ba11be7a29bb0621e84632cfecaaf58984",
        "anchors": ["P09", "P10", "P15", "P16"],
    },
    {
        "role": "execution_contract",
        "path": "docs/governance/solo-evaluation-execution-contract-revision-2-20260831.md",
        "sha256": "3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea",
        "git_blob": "5eb26f6b0b9229ee43a5ac1cf958eb763a2d6c9b",
        "commit": "4ba542ba11be7a29bb0621e84632cfecaaf58984",
        "anchors": ["E05", "E06", "E11", "E12"],
    },
    {
        "role": "ledger_contract",
        "path": "docs/governance/solo-attempt-ledger-v2-schema-implementation-contract-20260831.md",
        "sha256": "d64d9f881a07947b363ef12d2c53e8628dcd4b4dabbf89ba3cbd42f4131d01bb",
        "git_blob": "56ba6f86dc9e5f58430e8716a6f08188e8985d65",
        "commit": "4ba542ba11be7a29bb0621e84632cfecaaf58984",
        "anchors": ["L07", "L08", "L09", "L13"],
    },
    {
        "role": "design_provenance",
        "path": "docs/governance/solo-ledger-anonymization-revision-2-solo-profile-20260831.md",
        "sha256": "e0cd3d4fca39c37c9baad8b0ef2b976cdff910ce997b95c6b241e644e4178741",
        "git_blob": "210790659e321d116c6061dfe18ae4f199d45ff1",
        "commit": "ffa56857a38d6c7e62cbcb316e62dc92fa405a28",
        "anchors": ["Structural rule", "Join prohibition", "Claim ceiling"],
    },
)

_SOURCE_BINDINGS: Final = (
    {
        "path": "governance_tools/solo_attempt_ledger_v2.py",
        "sha256": "639dd718b7ca265d3ef5ce4a93a004f45378daa35288a1a627777f1acacdf3cd",
        "git_blob": "e4c0121a4a7c443832a9059e15148a4605a3d988",
        "last_change_commit": "c763e738f754282f19c0e5b794dadaa0a44daa65",
        "role": "atomic_genesis_publication_runtime_surface",
    },
    {
        "path": "governance_tools/solo_r2_random_domains.py",
        "sha256": "51f282432d98c9aa444eb6903d95bec544160cdae47a853314eaa7439742d597",
        "git_blob": "b3c9442298f2aba0adcac5c48b5ea436726fc662",
        "last_change_commit": "ed8fad34a3c9dd4c417b947b1bbc564dc1bddffc",
        "role": "domain_separated_generators",
    },
    {
        "path": "governance_tools/solo_r2_blind_scoring_bundle.py",
        "sha256": "8703fcc07d91e54dd9a890ac138dc40b7493922471966f04998f95e0e64dc394",
        "git_blob": "291ef7cf6facb26a0145f7223c3b58b43e427546",
        "last_change_commit": "66b02a832b705f257df59162a66db1cf369704b1",
        "role": "presentation_order_boundary",
    },
    {
        "path": "governance_tools/solo_r2_bootstrap.py",
        "sha256": "4458f0e7cd3775160a8e1300cc2089dea03978a5f0c33c2d26c9bd75ed7db927",
        "git_blob": "fb2f50518fea27c49f671655df6433465b0c9b79",
        "last_change_commit": "182d3965bb65dd4886d70fab003c56fc8fe58c02",
        "role": "bootstrap_runtime_participant_and_call_site_closure",
    },
    {
        "path": "governance_tools/solo_r2_controller_state.py",
        "sha256": "58275494ac3ecd6dba422300008e0111ad6d8533298c64b7584eb3753d26087f",
        "git_blob": "c73a5515b5024c59a5271bd6b93d11f7d7f97c37",
        "last_change_commit": "33896f224fdf8dba50302756e53b84e82c186d6c",
        "role": "sealed_order_revalidation",
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "sha256": "74a7d7948347a9fa61f6d43e97b599ce34c3a96aa92e7d38c07f52d99090e393",
        "git_blob": "4bff27004df6086d9fbcc50b1426128b93346b1c",
        "last_change_commit": "de85d2f8ecf5f1ccb732e09ec4053b74456ab180",
        "role": "production_entropy_and_generator_call_sites",
    },
    {
        "path": "governance_tools/solo_r2_pair_creation.py",
        "sha256": "6eadaa6cdc429f1d80461c48d5ee440e7951f305bcdf52617562322092e0d80b",
        "git_blob": "b4cd9d46d4518d0cabc788b59d10f51263cea691",
        "last_change_commit": "c763e738f754282f19c0e5b794dadaa0a44daa65",
        "role": "pair_creation_entropy_and_arm_order_call_site_closure",
    },
)

_DOMAIN_CONSTANTS: Final = {
    "ATTEMPT_HANDLE_DOMAIN": "solo-r2-attempt-handle-v1",
    "SCORING_LABEL_DOMAIN": "solo-r2-scoring-label-v1",
    "ARM_ORDER_DOMAIN": "solo-r2-arm-order-v1",
    "PRESENTATION_ORDER_DOMAIN": "solo-r2-presentation-order-v1",
}

_EXPECTED_SIGNATURES: Final = {
    "governance_tools/solo_r2_random_domains.py": {
        "_validate_domain": ["domain_tag", "allowed"],
        "_validate_entropy": ["entropy"],
        "_digest_for_domain": ["domain_tag", "entropy"],
        "derive_opaque_identifier": ["domain_tag", "entropy"],
        "derive_order_bit": ["domain_tag", "entropy"],
        "arm_order_from_entropy": ["entropy"],
        "presentation_order_bit_from_entropy": ["entropy"],
        "OpaqueIdentifierRegistry.admit": ["self", "domain_tag", "entropy"],
    },
    "governance_tools/solo_r2_blind_scoring_bundle.py": {
        "build_blind_scoring_bundle": [
            "evaluation_id",
            "pair_id",
            "slot",
            "rubric_id",
            "outputs_by_label",
            "presentation_entropy",
        ],
    },
    "governance_tools/solo_r2_lifecycle_integration.py": {
        "_draw_entropy32": [],
    },
    "governance_tools/solo_r2_pair_creation.py": {
        "_draw_entropy32": [],
        "_order_state": ["evaluation_id", "pair_id"],
    },
}

_EXPECTED_RANDOM_IMPORTS: Final = {
    "governance_tools/solo_r2_blind_scoring_bundle.py": [
        "RandomDomainError",
        "SAMPLING_ROLE",
        "presentation_order_bit_from_entropy",
    ],
    "governance_tools/solo_r2_controller_state.py": ["arm_order_from_entropy"],
    "governance_tools/solo_r2_lifecycle_integration.py": [
        "solo_r2_random_domains as random_domains"
    ],
    "governance_tools/solo_r2_pair_creation.py": [
        "solo_r2_random_domains as random_domains"
    ],
}

_EXPECTED_RELEVANT_CALLS: Final = (
    {
        "path": "governance_tools/solo_r2_random_domains.py",
        "scope": "arm_order_from_entropy",
        "line": 76,
        "callee": "derive_order_bit",
        "args": ["ARM_ORDER_DOMAIN", "entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_random_domains.py",
        "scope": "presentation_order_bit_from_entropy",
        "line": 84,
        "callee": "derive_order_bit",
        "args": ["PRESENTATION_ORDER_DOMAIN", "entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_random_domains.py",
        "scope": "OpaqueIdentifierRegistry.admit",
        "line": 98,
        "callee": "derive_opaque_identifier",
        "args": ["domain_tag", "entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_blind_scoring_bundle.py",
        "scope": "build_blind_scoring_bundle",
        "line": 207,
        "callee": "presentation_order_bit_from_entropy",
        "args": ["presentation_entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_controller_state.py",
        "scope": "validate_controller_state",
        "line": 333,
        "callee": "arm_order_from_entropy",
        "args": ["entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.start",
        "line": 341,
        "callee": "_draw_entropy32",
        "args": [],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.start",
        "line": 342,
        "callee": "random_domains.arm_order_from_entropy",
        "args": ["order_entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.admit_attempt.operation",
        "line": 644,
        "callee": "_draw_entropy32",
        "args": [],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.admit_attempt.operation",
        "line": 645,
        "callee": "self._identifier_registry.admit",
        "args": ["random_domains.ATTEMPT_HANDLE_DOMAIN", "entropy"],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.prepare_scoring.operation",
        "line": 809,
        "callee": "self._identifier_registry.admit",
        "args": [
            "random_domains.SCORING_LABEL_DOMAIN",
            "_draw_entropy32()",
        ],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.prepare_scoring.operation",
        "line": 810,
        "callee": "_draw_entropy32",
        "args": [],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.prepare_scoring.operation",
        "line": 818,
        "callee": "scoring_bundle.build_blind_scoring_bundle",
        "args": [],
        "keywords": {
            "evaluation_id": "self._evaluation_id",
            "outputs_by_label": "outputs_by_label",
            "pair_id": "self._pair_id",
            "presentation_entropy": "_draw_entropy32()",
            "rubric_id": "self._rubric_id",
            "slot": "SYNTHETIC_SLOT",
        },
    },
    {
        "path": "governance_tools/solo_r2_lifecycle_integration.py",
        "scope": "SyntheticLifecycleCoordinator.prepare_scoring.operation",
        "line": 824,
        "callee": "_draw_entropy32",
        "args": [],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_pair_creation.py",
        "scope": "_order_state",
        "line": 549,
        "callee": "_draw_entropy32",
        "args": [],
        "keywords": {},
    },
    {
        "path": "governance_tools/solo_r2_pair_creation.py",
        "scope": "_order_state",
        "line": 551,
        "callee": "random_domains.arm_order_from_entropy",
        "args": ["order_entropy"],
        "keywords": {},
    },
)

_RELEVANT_CALLEES: Final = frozenset(
    {
        "derive_order_bit",
        "derive_opaque_identifier",
        "presentation_order_bit_from_entropy",
        "arm_order_from_entropy",
        "random_domains.arm_order_from_entropy",
        "self._identifier_registry.admit",
        "scoring_bundle.build_blind_scoring_bundle",
        "_draw_entropy32",
    }
)

_PROHIBITED_OPAQUE_INPUT_NAMES: Final = frozenset(
    {
        "arm",
        "treatment_state",
        "realized_order",
        "execution_order",
        "event_seq",
        "timestamp_utc",
        "pair_id",
        "slot",
        "parity",
        "counter",
        "sequence",
        "datetime",
        "time",
        "uuid",
        "os",
        "random",
        "secrets",
    }
)

_TOP_LEVEL_KEYS: Final = frozenset(
    {
        "schema_version",
        "artifact_type",
        "machine_disposition",
        "authority_bindings",
        "source_snapshot",
        "inspector_binding",
        "production_namespace_scan",
        "structural_checks",
        "generator_surfaces",
        "production_call_sites",
        "tranche4_interface_reconciliation",
        "sampling_role",
        "metadata_reconciliation",
        "invalidation_conditions",
        "claim_ceiling",
    }
)


class R1ConformanceError(RuntimeError):
    """Fail-closed error carrying only a frozen public disposition."""

    def __init__(self, code: str = R1_CONFORMANCE_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = R1_CONFORMANCE_FAILURE) -> None:
    raise R1ConformanceError(code) from None


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_project_root(raw_root: object) -> Path:
    if isinstance(raw_root, Path):
        supplied = raw_root
    elif type(raw_root) is str:
        supplied = Path(raw_root)
    else:
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


def _git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _read_bound_bytes(root: Path, binding: Mapping[str, Any]) -> bytes:
    path = root / binding["path"]
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or not _is_within(resolved, root):
            _fail()
        data = resolved.read_bytes()
    except R1ConformanceError:
        raise
    except OSError:
        _fail()
    if (
        hashlib.sha256(data).hexdigest() != binding["sha256"]
        or _git_blob_sha1(data) != binding["git_blob"]
    ):
        _fail()
    return data


def _parse_python(data: bytes, relpath: str) -> ast.Module:
    try:
        text = data.decode("utf-8", errors="strict")
        if text.startswith("\ufeff"):
            _fail()
        return ast.parse(text, filename=relpath)
    except R1ConformanceError:
        raise
    except (UnicodeDecodeError, SyntaxError, ValueError):
        _fail()


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _expression(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except (AttributeError, ValueError):
        _fail()


def _function_map(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            name = ".".join((*self.scope, node.name))
            found[name] = node
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

    Visitor().visit(tree)
    return found


def _signature(node: ast.FunctionDef) -> list[str]:
    if node.args.vararg is not None or node.args.kwarg is not None:
        _fail()
    positional = [
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args)
    ]
    return [*positional, *(argument.arg for argument in node.args.kwonlyargs)]


def _assigned_string_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or type(value.value) is not str:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                constants[target.id] = value.value
    return constants


def _referenced_identifiers(nodes: Iterable[ast.AST]) -> set[str]:
    identifiers: set[str] = set()
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.arg):
                identifiers.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                identifiers.add(node.arg)
            elif isinstance(node, ast.Constant) and type(node.value) is str:
                identifiers.update(
                    token.casefold()
                    for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.value)
                )
    return identifiers


class _CallCollector(ast.NodeVisitor):
    def __init__(self, relpath: str) -> None:
        self.relpath = relpath
        self.scope: list[str] = []
        self.calls: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        callee = _dotted_name(node.func)
        if callee in _RELEVANT_CALLEES:
            self.calls.append(
                {
                    "path": self.relpath,
                    "scope": ".".join(self.scope),
                    "line": node.lineno,
                    "callee": callee,
                    "args": [_expression(argument) for argument in node.args],
                    "keywords": {
                        keyword.arg: _expression(keyword.value)
                        for keyword in node.keywords
                        if keyword.arg is not None
                    },
                }
            )
        self.generic_visit(node)


def _collect_calls(relpath: str, tree: ast.Module) -> list[dict[str, Any]]:
    collector = _CallCollector(relpath)
    collector.visit(tree)
    return collector.calls


def _random_import_projection(
    trees: Mapping[str, ast.Module],
) -> dict[str, list[str]]:
    projection: dict[str, list[str]] = {}
    for relpath, tree in trees.items():
        names: list[str] = []
        for node in tree.body:
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "governance_tools.solo_r2_random_domains"
            ):
                names.extend(
                    alias.name
                    if alias.asname is None
                    else f"{alias.name} as {alias.asname}"
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module == "governance_tools":
                for alias in node.names:
                    if alias.name == "solo_r2_random_domains":
                        names.append(
                            alias.name
                            if alias.asname is None
                            else f"{alias.name} as {alias.asname}"
                        )
        if names:
            projection[relpath] = sorted(names)
    return projection


def _scan_namespace(root: Path) -> list[str]:
    tools = root / "governance_tools"
    try:
        observed = sorted(
            path.relative_to(root).as_posix()
            for path in tools.iterdir()
            if path.is_file()
            and (
                path.name.startswith("solo_r2_")
                or path.name.startswith("solo_attempt_ledger_v2")
            )
            and path.suffix == ".py"
        )
    except OSError:
        _fail()
    if tuple(observed) != _OBSERVED_NAMESPACE:
        _fail()
    return observed


def _validate_random_domains(tree: ast.Module) -> dict[str, Any]:
    functions = _function_map(tree)
    for name, expected in _EXPECTED_SIGNATURES[
        "governance_tools/solo_r2_random_domains.py"
    ].items():
        if name not in functions or _signature(functions[name]) != expected:
            _fail()
    constants = _assigned_string_constants(tree)
    if any(constants.get(name) != value for name, value in _DOMAIN_CONSTANTS.items()):
        _fail()
    if len(set(_DOMAIN_CONSTANTS.values())) != len(_DOMAIN_CONSTANTS):
        _fail()

    opaque_closure = [
        functions[name]
        for name in (
            "_validate_domain",
            "_validate_entropy",
            "_digest_for_domain",
            "derive_opaque_identifier",
            "OpaqueIdentifierRegistry.admit",
        )
    ]
    observed_names = _referenced_identifiers(opaque_closure)
    prohibited = sorted(observed_names & _PROHIBITED_OPAQUE_INPUT_NAMES)
    if prohibited:
        _fail()

    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    if imports != {"__future__", "hashlib", "typing"}:
        _fail()
    return {
        "opaque_generator_signature": ["domain_tag", "entropy"],
        "registry_signature": ["self", "domain_tag", "entropy"],
        "order_generator_signatures": {
            "derive_order_bit": ["domain_tag", "entropy"],
            "arm_order_from_entropy": ["entropy"],
            "presentation_order_bit_from_entropy": ["entropy"],
        },
        "domain_tags": dict(sorted(_DOMAIN_CONSTANTS.items())),
        "opaque_closure_prohibited_identifiers": prohibited,
        "imports": sorted(imports),
    }


def _validate_bundle(tree: ast.Module) -> dict[str, Any]:
    functions = _function_map(tree)
    function = functions.get("build_blind_scoring_bundle")
    expected = _EXPECTED_SIGNATURES[
        "governance_tools/solo_r2_blind_scoring_bundle.py"
    ]["build_blind_scoring_bundle"]
    if function is None or _signature(function) != expected:
        _fail()
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and _dotted_name(node.func) == "presentation_order_bit_from_entropy"
    ]
    if (
        len(calls) != 1
        or len(calls[0].args) != 1
        or _expression(calls[0].args[0]) != "presentation_entropy"
        or calls[0].keywords
    ):
        _fail()
    sort_lines = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and _dotted_name(node.func) == "labels.sort"
    ]
    if sort_lines != [205] or sort_lines[0] >= calls[0].lineno:
        _fail()
    return {
        "builder_signature": expected,
        "presentation_order_input": "presentation_entropy",
        "labels_canonicalized_before_order_draw": True,
    }


def _validate_controller(tree: ast.Module) -> dict[str, Any]:
    functions = _function_map(tree)
    function = functions.get("validate_controller_state")
    if function is None:
        _fail()
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and _dotted_name(node.func) == "arm_order_from_entropy"
    ]
    if (
        len(calls) != 1
        or len(calls[0].args) != 1
        or _expression(calls[0].args[0]) != "entropy"
    ):
        _fail()
    return {
        "sealed_order_revalidation_input": "decoded order_entropy",
        "realized_order_comparison": True,
    }


def _validate_integration(tree: ast.Module) -> dict[str, Any]:
    functions = _function_map(tree)
    draw = functions.get("_draw_entropy32")
    if draw is None or _signature(draw):
        _fail()
    urandom_calls = [
        node
        for node in ast.walk(draw)
        if isinstance(node, ast.Call) and _dotted_name(node.func) == "os.urandom"
    ]
    if (
        len(urandom_calls) != 1
        or len(urandom_calls[0].args) != 1
        or _expression(urandom_calls[0].args[0])
        != "random_domains.ENTROPY_BYTES"
        or urandom_calls[0].keywords
    ):
        _fail()
    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    delivery = classes.get("ScorerDelivery")
    coordinator = classes.get("SyntheticLifecycleCoordinator")
    if delivery is None or coordinator is None:
        _fail()
    delivery_fields = [
        node.target.id
        for node in delivery.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]
    if delivery_fields != ["bundle_path", "bundle_bytes"]:
        _fail()
    decorators = [_dotted_name(node) for node in delivery.decorator_list]
    frozen = any(
        isinstance(node, ast.Call)
        and _dotted_name(node.func) == "dataclass"
        and any(
            keyword.arg == "frozen"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        for node in delivery.decorator_list
    )
    if not frozen:
        _fail()
    public_members = [
        node.name
        for node in coordinator.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    expected_members = [
        "start",
        "ledger_path",
        "admit_attempt",
        "expose_task",
        "record_admitted_not_exposed",
        "record_terminal",
        "record_harness_failure",
        "prepare_scoring",
        "acknowledge_score",
        "authenticate_synthetic_unblinding",
    ]
    if public_members != expected_members:
        _fail()
    return {
        "entropy_drawer_signature": [],
        "entropy_source": "os.urandom(random_domains.ENTROPY_BYTES)",
        "scorer_delivery_fields": delivery_fields,
        "scorer_delivery_frozen": True,
        "public_coordinator_members": public_members,
        "decorator_names": sorted(name for name in decorators if name),
    }


def _validate_pair_creation(tree: ast.Module) -> dict[str, Any]:
    functions = _function_map(tree)
    expected = _EXPECTED_SIGNATURES[
        "governance_tools/solo_r2_pair_creation.py"
    ]
    draw = functions.get("_draw_entropy32")
    order_state = functions.get("_order_state")
    if (
        draw is None
        or order_state is None
        or _signature(draw) != expected["_draw_entropy32"]
        or _signature(order_state) != expected["_order_state"]
    ):
        _fail()
    urandom_calls = [
        node
        for node in ast.walk(draw)
        if isinstance(node, ast.Call) and _dotted_name(node.func) == "os.urandom"
    ]
    if (
        len(urandom_calls) != 1
        or len(urandom_calls[0].args) != 1
        or _expression(urandom_calls[0].args[0])
        != "random_domains.ENTROPY_BYTES"
        or urandom_calls[0].keywords
    ):
        _fail()
    entropy_assignments = [
        node
        for node in ast.walk(order_state)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "order_entropy"
        and isinstance(node.value, ast.Call)
        and _dotted_name(node.value.func) == "_draw_entropy32"
        and not node.value.args
        and not node.value.keywords
    ]
    order_calls = [
        node
        for node in ast.walk(order_state)
        if isinstance(node, ast.Call)
        and _dotted_name(node.func) == "random_domains.arm_order_from_entropy"
    ]
    if (
        len(entropy_assignments) != 1
        or len(order_calls) != 1
        or len(order_calls[0].args) != 1
        or _expression(order_calls[0].args[0]) != "order_entropy"
        or order_calls[0].keywords
    ):
        _fail()
    return {
        "entropy_drawer_signature": [],
        "entropy_source": "os.urandom(random_domains.ENTROPY_BYTES)",
        "order_state_signature": ["evaluation_id", "pair_id"],
        "order_entropy_assignment": "order_entropy = _draw_entropy32()",
        "arm_order_input": "order_entropy",
    }


def _validate_evidence(value: object) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != _TOP_LEVEL_KEYS:
        _fail()
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["artifact_type"] != ARTIFACT_TYPE
        or value["machine_disposition"] != STRUCTURAL_CONFORMANCE_PASS
        or value["sampling_role"] != SAMPLING_ROLE
    ):
        _fail()
    namespace = value["production_namespace_scan"]
    if type(namespace) is not dict or frozenset(namespace) != {
        "patterns",
        "observed_modules",
        "runtime_participants",
        "excluded_validation_modules",
    }:
        _fail()
    exclusions = namespace["excluded_validation_modules"]
    if exclusions != [
        {"path": INSPECTOR_RELPATH, "reason": EXCLUSION_REASON}
    ]:
        _fail()
    metadata = value["metadata_reconciliation"]
    if type(metadata) is not dict or frozenset(metadata) != {
        "candidate_json_excludes",
        "external_provenance_layers",
        "superseded_preflight_requirement",
    }:
        _fail()
    if metadata["candidate_json_excludes"] != [
        "absolute_local_path",
        "human_review_disposition",
        "review_timestamp",
        "reviewer_identity",
    ]:
        _fail()
    return value


def _canonical_bytes(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        reparsed = json.loads(encoded.decode("utf-8"))
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        _fail()
    _validate_evidence(reparsed)
    if encoded.startswith(b"\xef\xbb\xbf") or b"\r" in encoded:
        _fail()
    return encoded + b"\n"


def build_evidence(project_root: Path | str) -> dict[str, Any]:
    """Build deterministic R1 evidence without writing to the repository."""

    root = _validate_project_root(project_root)
    authority_bindings: list[dict[str, Any]] = []
    for binding in _AUTHORITY_BINDINGS:
        data = _read_bound_bytes(root, binding)
        authority_bindings.append({**binding, "bytes": len(data)})

    source_bytes: dict[str, bytes] = {}
    source_bindings: list[dict[str, Any]] = []
    for binding in _SOURCE_BINDINGS:
        data = _read_bound_bytes(root, binding)
        source_bytes[binding["path"]] = data
        source_bindings.append({**binding, "bytes": len(data)})

    inspector_path = root / INSPECTOR_RELPATH
    try:
        resolved_inspector = inspector_path.resolve(strict=True)
        if not resolved_inspector.is_file() or not _is_within(
            resolved_inspector, root
        ):
            _fail()
        inspector_bytes = resolved_inspector.read_bytes()
    except R1ConformanceError:
        raise
    except OSError:
        _fail()

    observed_namespace = _scan_namespace(root)
    trees: dict[str, ast.Module] = {}
    for relpath in _RUNTIME_MODULES:
        try:
            data = (root / relpath).read_bytes()
        except OSError:
            _fail()
        trees[relpath] = _parse_python(data, relpath)

    random_surface = _validate_random_domains(
        trees["governance_tools/solo_r2_random_domains.py"]
    )
    bundle_surface = _validate_bundle(
        trees["governance_tools/solo_r2_blind_scoring_bundle.py"]
    )
    controller_surface = _validate_controller(
        trees["governance_tools/solo_r2_controller_state.py"]
    )
    integration_surface = _validate_integration(
        trees["governance_tools/solo_r2_lifecycle_integration.py"]
    )
    pair_creation_surface = _validate_pair_creation(
        trees["governance_tools/solo_r2_pair_creation.py"]
    )

    import_projection = _random_import_projection(trees)
    if import_projection != _EXPECTED_RANDOM_IMPORTS:
        _fail()
    calls = sorted(
        (
            call
            for relpath, tree in trees.items()
            for call in _collect_calls(relpath, tree)
        ),
        key=lambda item: (item["path"], item["line"], item["callee"]),
    )
    expected_calls = sorted(
        (dict(item) for item in _EXPECTED_RELEVANT_CALLS),
        key=lambda item: (item["path"], item["line"], item["callee"]),
    )
    if calls != expected_calls:
        _fail()

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "machine_disposition": STRUCTURAL_CONFORMANCE_PASS,
        "authority_bindings": authority_bindings,
        "source_snapshot": {
            "repository_tree_commit": SOURCE_SNAPSHOT_COMMIT,
            "source_bindings": source_bindings,
        },
        "inspector_binding": {
            "path": INSPECTOR_RELPATH,
            "bytes": len(inspector_bytes),
            "sha256": hashlib.sha256(inspector_bytes).hexdigest(),
            "git_blob": _git_blob_sha1(inspector_bytes),
            "runtime_participant": False,
        },
        "production_namespace_scan": {
            "patterns": [
                "governance_tools/solo_attempt_ledger_v2*.py",
                "governance_tools/solo_r2_*.py",
            ],
            "observed_modules": observed_namespace,
            "runtime_participants": list(_RUNTIME_MODULES),
            "excluded_validation_modules": [
                {"path": INSPECTOR_RELPATH, "reason": EXCLUSION_REASON}
            ],
        },
        "structural_checks": [
            {
                "check_id": "R1_OPAQUE_GENERATOR_INPUT_EXCLUSION",
                "status": "PASS",
            },
            {
                "check_id": "R1_ORDER_GENERATOR_INPUT_EXCLUSION",
                "status": "PASS",
            },
            {
                "check_id": "R1_PRODUCTION_CALL_SITE_CLOSURE",
                "status": "PASS",
            },
            {
                "check_id": "R1_PRESENTATION_ORDER_STRUCTURAL_SEPARATION",
                "status": "PASS",
            },
            {
                "check_id": "TRANCHE4_INTERFACE_RECONCILIATION",
                "status": "PASS",
            },
        ],
        "generator_surfaces": {
            "random_domains": random_surface,
            "blind_scoring_bundle": bundle_surface,
            "controller_state": controller_surface,
            "lifecycle_integration": integration_surface,
            "pair_creation": pair_creation_surface,
            "random_domain_import_projection": import_projection,
        },
        "production_call_sites": calls,
        "tranche4_interface_reconciliation": {
            "implementation_commit": TRANCHE4_IMPLEMENTATION_COMMIT,
            "scorer_delivery": {
                "fields": ["bundle_path", "bundle_bytes"],
                "frozen": True,
                "ledger_path_visible_to_scorer": False,
            },
            "mapping": [
                {
                    "definition": "start_shakedown()",
                    "implementation": "start()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": "record_pre_attempt_failure()",
                    "implementation": "internal start() failure path",
                    "disposition": "ACCEPTED_CAPABILITY_NARROWING",
                },
                {
                    "definition": "admit_attempt()",
                    "implementation": "admit_attempt()",
                    "disposition": "EXACT",
                },
                {
                    "definition": "record_task_exposed()",
                    "implementation": "expose_task()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": "mark_admitted_not_exposed()",
                    "implementation": "record_admitted_not_exposed()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": "record_execution_terminal()",
                    "implementation": "record_terminal()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": "prepare_scoring()",
                    "implementation": "prepare_scoring()",
                    "disposition": "EXACT",
                },
                {
                    "definition": "record_score_completion()",
                    "implementation": "acknowledge_score()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": "synthetic_unblind()",
                    "implementation": "authenticate_synthetic_unblinding()",
                    "disposition": "ACCEPTED_RENAME",
                },
                {
                    "definition": None,
                    "implementation": "ledger_path read-only property",
                    "disposition": "ACCEPTED_CONTROLLER_DIAGNOSTIC_SURFACE",
                },
            ],
        },
        "sampling_role": SAMPLING_ROLE,
        "metadata_reconciliation": {
            "candidate_json_excludes": [
                "absolute_local_path",
                "human_review_disposition",
                "review_timestamp",
                "reviewer_identity",
            ],
            "external_provenance_layers": {
                "human_review_disposition": "read_only_exact_identity_review",
                "review_actor": "review_record",
                "time_and_durability": "git_commit",
                "evidence_identity": "git_blob_and_sha256",
            },
            "superseded_preflight_requirement": (
                "reviewer_identity_timestamp_and_disposition_inside_candidate_json"
            ),
        },
        "invalidation_conditions": [
            "any_authority_binding_bytes_or_identity_change",
            "any_bound_runtime_source_bytes_or_git_blob_change",
            "inspector_bytes_or_git_blob_change",
            "generator_signature_or_admitted_input_surface_change",
            "random_domain_import_graph_change",
            "production_namespace_or_call_site_set_change",
            "presentation_order_call_argument_change",
            "tranche4_scorer_delivery_or_public_interface_change",
            "evidence_schema_or_canonical_encoding_change",
            "old_pass_must_not_be_reused_after_any_invalidation",
        ],
        "claim_ceiling": [
            "proves_current_exact_source_and_call_site_structure_only",
            "does_not_prove_os_csprng_quality",
            "does_not_prove_statistical_independence",
            "does_not_prove_arbitrary_covert_channel_absence",
            "does_not_prove_runtime_monkeypatch_or_instrumentation_safety",
            "does_not_establish_full_protocol_conformance",
            "does_not_authorize_v2_genesis_pair_attempt_scoring_or_unblinding",
        ],
    }
    return _validate_evidence(evidence)


def encode_evidence(value: object) -> bytes:
    """Return exact deterministic UTF-8/LF evidence bytes."""

    return _canonical_bytes(_validate_evidence(value))


def write_evidence(project_root: Path | str) -> tuple[Path, bytes]:
    """Create the fixed evidence path once after complete in-memory validation."""

    root = _validate_project_root(project_root)
    evidence_bytes = encode_evidence(build_evidence(root))
    target = root / EVIDENCE_RELPATH
    try:
        parent = target.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail(R1_EVIDENCE_WRITE_FAILURE)
    if not parent.is_dir() or not _is_within(parent, root) or target.exists():
        _fail(R1_EVIDENCE_WRITE_FAILURE)
    created = False
    try:
        with target.open("xb") as stream:
            created = True
            stream.write(evidence_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        if target.read_bytes() != evidence_bytes:
            raise OSError("read-back mismatch")
    except (OSError, RuntimeError):
        if created:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        _fail(R1_EVIDENCE_WRITE_FAILURE)
    return target, evidence_bytes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build deterministic Solo R2 R1 structural evidence."
    )
    parser.add_argument("--project-root", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.write:
            target, evidence_bytes = write_evidence(args.project_root)
            digest = hashlib.sha256(evidence_bytes).hexdigest()
            print(
                f"{STRUCTURAL_CONFORMANCE_PASS} "
                f"path={target.name} sha256={digest}"
            )
        else:
            evidence_bytes = encode_evidence(build_evidence(args.project_root))
            print(
                f"{STRUCTURAL_CONFORMANCE_PASS} "
                f"sha256={hashlib.sha256(evidence_bytes).hexdigest()}"
            )
    except R1ConformanceError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
