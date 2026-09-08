"""Focused in-process evidence for the M3-b-2A launch producer seam."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import gate3_historical_bootstrap as bootstrap
import gate3_historical_child as child
import gate3_historical_materialize as materialize
import gate3_native_boundary as boundary
import gate3_historical_process as process


COMMIT = "4" * 40
PAYLOADS = {
    "pkg/a.py": b"# process fixture a\n",
    "pkg/b.py": b"# process fixture b\n",
}
INVENTORY = {
    path: hashlib.sha256(payload).hexdigest() for path, payload in PAYLOADS.items()
}


def candidate_bytes() -> bytes:
    files = [
        {
            "bytes": len(PAYLOADS[path]),
            "path": path,
            "sha256": digest,
        }
        for path, digest in sorted(INVENTORY.items())
    ]
    return json.dumps(
        {
            "files": files,
            "schema": bootstrap.CANDIDATE_SET_SCHEMA,
            "source_base_commit": COMMIT,
        },
        sort_keys=True,
    ).encode("ascii")


def build_tree(base: Path) -> materialize.MaterializedTree:
    def read_blob(commit: str, path: str) -> bytes:
        assert commit == COMMIT
        return PAYLOADS[path]

    return materialize._materialize_bound(
        commit=COMMIT,
        inventory=INVENTORY,
        read_blob=read_blob,
        base=base,
    )


def test_the_launch_producer_is_inert_and_has_no_process_surface() -> None:
    assert process.ACTIVE is False
    source = Path(process.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not names.intersection({"Popen", "run", "CreateProcessW"})
    assert not attributes.intersection({"Popen", "run", "CreateProcessW"})
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported.intersection({"subprocess", "ctypes", "multiprocessing"})
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and "__main__" in ast.unparse(node.test)
        for node in ast.walk(tree)
    )


def test_the_public_entrypoint_accepts_a_tree_and_no_root_parameter() -> None:
    parameters = inspect.signature(process.build_launch_stream).parameters
    assert tuple(parameters) == (
        "tree",
        "candidate_set_bytes",
        "bindings",
    )
    assert "root" not in parameters
    assert "payloads" not in parameters


def test_only_the_parent_adapter_calls_the_launch_encoder() -> None:
    directory = Path(process.__file__).parent
    callers = []
    for path in directory.glob("gate3_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "encode_launch_stream"
            for node in ast.walk(tree)
        ):
            callers.append(path.name)
    assert callers == ["gate3_historical_process.py"]


def test_a_non_tree_is_refused_before_inner_encoding(monkeypatch) -> None:
    called = False

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("inner encoder reached")

    monkeypatch.setattr(child, "encode_stream", forbidden)
    with pytest.raises(
        child.TransportError, match="^MATERIALIZED_ROOT_RECORD_INVALID$"
    ):
        process.build_launch_stream("C:\\not-authority", b"candidate")
    assert called is False


def test_a_materializer_refusal_is_closed_and_carries_no_root(monkeypatch) -> None:
    def refusing(*_args, **_kwargs):
        raise materialize.MaterializationError("RECORD_INVALID")

    monkeypatch.setattr(materialize, "transport_bundle", refusing)
    with pytest.raises(child.TransportError) as caught:
        process.build_launch_stream(object(), b"candidate")
    assert caught.value.code == "MATERIALIZED_ROOT_RECORD_INVALID"
    assert caught.value.args == ("MATERIALIZED_ROOT_RECORD_INVALID",)


def test_a_non_record_materializer_failure_is_not_flattened(monkeypatch) -> None:
    def refusing(*_args, **_kwargs):
        raise materialize.MaterializationError("MATERIALIZED_BYTES_CHANGED")

    monkeypatch.setattr(materialize, "transport_bundle", refusing)
    with pytest.raises(
        materialize.MaterializationError, match="^MATERIALIZED_BYTES_CHANGED$"
    ):
        process.build_launch_stream(object(), b"candidate")


def test_a_live_tree_produces_its_exact_root_and_unchanged_inner_frame(
    tmp_path: Path, monkeypatch
) -> None:
    base = tmp_path / "borrowed-base"
    base.mkdir()
    tree = build_tree(base)
    candidate = candidate_bytes()
    monkeypatch.setattr(child, "RUNTIME_MODULE_ALLOWLIST", tuple(PAYLOADS))
    monkeypatch.setattr(
        child, "CANDIDATE_SET_SHA256", hashlib.sha256(candidate).hexdigest()
    )
    monkeypatch.setattr(bootstrap, "RUNTIME_MODULE_ALLOWLIST", tuple(PAYLOADS))
    monkeypatch.setattr(
        bootstrap, "CANDIDATE_SET_SHA256", hashlib.sha256(candidate).hexdigest()
    )
    monkeypatch.setattr(bootstrap, "SOURCE_COMMIT", COMMIT)
    try:
        stream = process.build_launch_stream(tree, candidate)
        inner, raw_root = (
            stream[18 : 18 + int.from_bytes(stream[10:14], "little")],
            stream[18 + int.from_bytes(stream[10:14], "little") :],
        )
        assert inner == child.encode_stream(candidate, PAYLOADS)
        assert raw_root.decode("utf-8") == str(tree.root)
        assert child.decode_launch_stream(stream) == (PAYLOADS, str(tree.root))
    finally:
        materialize._cleanup_bound(tree)


def test_candidate_and_tree_authorities_must_describe_the_same_inventory(
    tmp_path: Path, monkeypatch
) -> None:
    base = tmp_path / "borrowed-base"
    base.mkdir()
    tree = build_tree(base)
    changed = dict(PAYLOADS)
    changed["pkg/a.py"] = b"# different authority\n"
    candidate = candidate_bytes()
    value = json.loads(candidate)
    value["files"][0]["bytes"] = len(changed["pkg/a.py"])
    value["files"][0]["sha256"] = hashlib.sha256(changed["pkg/a.py"]).hexdigest()
    candidate = json.dumps(value, sort_keys=True).encode("ascii")
    monkeypatch.setattr(bootstrap, "RUNTIME_MODULE_ALLOWLIST", tuple(PAYLOADS))
    monkeypatch.setattr(
        bootstrap, "CANDIDATE_SET_SHA256", hashlib.sha256(candidate).hexdigest()
    )
    monkeypatch.setattr(bootstrap, "SOURCE_COMMIT", COMMIT)
    reads = []
    real_read = boundary.read_all

    def watching(bindings, leaf):
        reads.append(leaf)
        return real_read(bindings, leaf)

    monkeypatch.setattr(boundary, "read_all", watching)
    try:
        with pytest.raises(
            child.TransportError, match="^MATERIALIZED_ROOT_RECORD_INVALID$"
        ):
            process.build_launch_stream(tree, candidate)
        assert {id(leaf) for leaf in reads} == {
            id(leaf) for _label, leaf in tree.leaves
        }
    finally:
        monkeypatch.setattr(boundary, "read_all", real_read)
        materialize._cleanup_bound(tree)
