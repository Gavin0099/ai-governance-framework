"""Regression tests for the explicit canonical-root binding contract.

Owner-ratified 2026-06-23 (`docs/governance/artifact-write-boundary-2026-06-23.md`):

    Canonical artifact root is an explicit contract, not an ambient
    cwd-derived property.

These tests pin that contract at the surface that actually misrouted evidence on
2026-08-30: `session_closeout_entry`. They assert both halves of the ratified
decision -- that a supplied root is canonicalized and validated, and that a
missing or unusable root fails closed with zero writes rather than falling back
to the current working directory.

Root discovery is deliberately not tested, because it is deliberately not
implemented: deriving a root from Git, markers or parent traversal is the
branch the owner did not ratify.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from governance_tools.session_closeout_entry import (  # noqa: E402
    RootBindingError,
    _validate_explicit_project_root,
    main,
)

ENTRYPOINT = "governance_tools.session_closeout_entry"


def _make_valid_root(base: Path) -> Path:
    """Build a directory that satisfies the root-marker contract."""
    root = base / "repo"
    (root / "governance").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# markers\n", encoding="utf-8")
    return root


def _run_entrypoint(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", ENTRYPOINT, *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _tree(path: Path) -> set[Path]:
    return {p.relative_to(path) for p in path.rglob("*")}


# --- 1 & 2: the resolved root is the supplied root, whatever the cwd ---------


def test_supplied_root_resolves_identically_from_any_cwd(tmp_path, monkeypatch):
    """Cases 1 and 2: cwd must not influence the canonical root."""
    root = _make_valid_root(tmp_path)
    nested = root / "nested" / "deeper"
    nested.mkdir(parents=True)

    monkeypatch.chdir(root)
    from_root = _validate_explicit_project_root(str(root))

    monkeypatch.chdir(nested)
    from_nested = _validate_explicit_project_root(str(root))

    assert from_root == from_nested == root.resolve()
    assert from_nested != nested.resolve()


def test_main_writes_to_explicit_root_when_invoked_from_nested_cwd(
    tmp_path, monkeypatch
):
    """The real outer entrypoint must not write canonical evidence under cwd."""
    root = _make_valid_root(tmp_path)
    nested = root / ".qualification_tmp" / "solo-20260830"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_closeout_entry.py",
            "--project-root",
            str(root),
            "--format",
            "json",
            "--agent-id",
            "root-binding-regression",
            "--trigger-mode",
            "synthetic_smoke",
        ],
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    hook_result = {
        "canonical_closeout_artifact": None,
        "memory_closeout": {"decision": "pass", "candidate_signals": []},
        "promoted": True,
        "gate_verdict": "PASS",
        "session_id": "session-root-binding-regression",
        "daily_memory_write_status": "skipped",
        "memory_authority": {},
        "memory_workflow": {},
    }

    with patch("governance_tools.session_closeout_entry.run", return_value=hook_result):
        assert main() == 0

    assert (root / "artifacts" / "runtime" / "closeout-trigger-evidence.ndjson").is_file()
    assert len(list((root / "artifacts" / "runtime" / "closeout-receipts").glob("*.json"))) == 1
    assert not (nested / "artifacts").exists()
    assert not (nested / "memory").exists()


def test_relative_supplied_root_is_canonicalized(tmp_path, monkeypatch):
    """A supplied root is normalized to an absolute path, not left relative."""
    root = _make_valid_root(tmp_path)
    monkeypatch.chdir(root.parent)

    resolved = _validate_explicit_project_root(root.name)

    assert resolved.is_absolute()
    assert resolved == root.resolve()


# --- 3: a missing root fails closed -----------------------------------------


def test_missing_project_root_fails_closed_with_no_writes(tmp_path):
    """Case 3: omitting --project-root must refuse, not default to cwd."""
    workdir = tmp_path / "somewhere"
    workdir.mkdir()

    before = _tree(workdir)
    result = _run_entrypoint(workdir)
    after = _tree(workdir)

    assert result.returncode != 0
    assert "--project-root" in (result.stderr + result.stdout)
    assert after == before


# --- 4 & 5: an unusable root fails closed ------------------------------------


def test_root_without_governance_markers_is_rejected(tmp_path):
    """Case 4: a directory that is not a governance root is refused."""
    bare = tmp_path / "bare"
    bare.mkdir()

    with pytest.raises(RootBindingError) as excinfo:
        _validate_explicit_project_root(str(bare))

    assert "missing governance markers" in str(excinfo.value)


def test_partial_markers_are_rejected(tmp_path):
    """Every required marker must be present; one is not enough."""
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "AGENTS.md").write_text("# only one marker\n", encoding="utf-8")

    with pytest.raises(RootBindingError):
        _validate_explicit_project_root(str(partial))


def test_wrong_marker_types_are_rejected(tmp_path):
    """Marker names alone are insufficient; their filesystem types are fixed."""
    wrong_types = tmp_path / "wrong-types"
    wrong_types.mkdir()
    (wrong_types / "AGENTS.md").mkdir()
    (wrong_types / "governance").write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(RootBindingError):
        _validate_explicit_project_root(str(wrong_types))


def test_nonexistent_root_is_rejected(tmp_path):
    """Case 5: a root that does not exist cannot be resolved."""
    with pytest.raises(RootBindingError) as excinfo:
        _validate_explicit_project_root(str(tmp_path / "absent"))

    assert "cannot be resolved" in str(excinfo.value)


def test_file_as_root_is_rejected(tmp_path):
    """Case 5: a path that exists but is not a directory is refused."""
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("x\n", encoding="utf-8")

    with pytest.raises(RootBindingError) as excinfo:
        _validate_explicit_project_root(str(not_a_dir))

    assert "not a directory" in str(excinfo.value)


def test_unwritable_root_is_rejected(tmp_path, monkeypatch):
    """Case 5: writability must be established before any writer runs."""
    root = _make_valid_root(tmp_path)
    monkeypatch.setattr(
        "governance_tools.session_closeout_entry.os.access",
        lambda path, mode: False,
    )

    with pytest.raises(RootBindingError) as excinfo:
        _validate_explicit_project_root(str(root))

    assert "not writable" in str(excinfo.value)


# --- 6: failures leave nothing behind ----------------------------------------


def test_failed_binding_writes_nothing_to_cwd_or_supplied_path(tmp_path):
    """Case 6: no partial `artifacts/` or `memory/` output on any failure path."""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    bare = tmp_path / "bare-root"
    bare.mkdir()

    before_cwd, before_root = _tree(workdir), _tree(bare)
    result = _run_entrypoint(workdir, "--project-root", str(bare))

    assert result.returncode != 0
    assert "ROOT_BINDING_FAILURE" in result.stderr
    assert _tree(workdir) == before_cwd
    assert _tree(bare) == before_root
    for produced in (workdir, bare):
        assert not (produced / "artifacts").exists()
        assert not (produced / "memory").exists()


# --- the un-ratified branch stays un-implemented -----------------------------


def test_no_root_discovery_from_a_valid_root_cwd(tmp_path, monkeypatch):
    """Standing inside a valid root does not supply the root implicitly."""
    root = _make_valid_root(tmp_path)
    monkeypatch.chdir(root)

    result = _run_entrypoint(root)

    assert result.returncode != 0
    assert "--project-root" in (result.stderr + result.stdout)
