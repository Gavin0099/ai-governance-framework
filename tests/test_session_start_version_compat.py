"""Tests for P5a: governance version compatibility advisory integration in session_start.

These tests verify:
  - version_compatibility key is always present in session_start result
  - advisory_only is always True (dry-run — no blocking in P5a)
  - format_human_result always emits version_compat= line
  - compatible verdict produces no advisory warning lines
  - degraded/migration_required/unsupported produce appropriate advisory lines
  - session_start never blocks regardless of verdict
  - session_start does not re-derive feature matrix logic

Note: tests use temp project roots that do not have version_manifest.yaml,
so the verdict will be unsupported — which is the correct advisory-only response.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from runtime_hooks.core.session_start import (
    build_session_start_context,
    format_human_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_plan(root: Path) -> Path:
    plan = root / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    return plan


def _write_version_manifest(root: Path, **overrides) -> None:
    defaults = {
        "schema_version": "1.0",
        "governance_version": "0.4.0",
        "contract_schema_version": "1.2.0",
        "runtime_entrypoint_version": "1.1.0",
        "hook_wiring_version": "1.0.0",
        "artifact_layout_version": "1.0.0",
        "memory_layout_version": "1.0.0",
    }
    manifest = {**defaults, **overrides}
    manifest_path = root / ".governance" / "version_manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.dump(manifest), encoding="utf-8")


@pytest.fixture()
def session_root(tmp_path):
    plan = _minimal_plan(tmp_path)
    (tmp_path / "tool.py").write_text("print('ok')", encoding="utf-8")
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def _run(root: Path, plan: Path | None = None) -> dict:
    if plan is None:
        plan = root / "PLAN.md"
    return build_session_start_context(
        project_root=root,
        plan_path=plan,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Test version compat advisory",
    )


# ---------------------------------------------------------------------------
# version_compatibility key is always present
# ---------------------------------------------------------------------------

def test_version_compatibility_key_always_present(session_root) -> None:
    result = _run(session_root)
    assert "version_compatibility" in result


def test_version_compatibility_advisory_only_always_true(session_root) -> None:
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["advisory_only"] is True


def test_version_compatibility_has_verdict(session_root) -> None:
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] in ("compatible", "compatible_with_degradation", "migration_required", "unsupported")


# ---------------------------------------------------------------------------
# Session start never blocks regardless of verdict
# ---------------------------------------------------------------------------

def test_session_start_not_blocked_when_manifest_missing(session_root) -> None:
    # No version_manifest.yaml — advisory verdict = unsupported
    # Session must still produce a result (ok may be False for other reasons, but never None)
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "unsupported"
    # Session start completed — result is a dict (not an exception)
    assert isinstance(result, dict)


def test_session_start_not_blocked_when_manifest_present_compatible(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "compatible"
    assert isinstance(result, dict)


def test_session_start_not_blocked_when_manifest_degraded(session_root) -> None:
    _write_version_manifest(session_root, memory_layout_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "compatible_with_degradation"
    assert isinstance(result, dict)


def test_session_start_not_blocked_when_migration_required(session_root) -> None:
    _write_version_manifest(session_root, hook_wiring_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "migration_required"
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# format_human_result always emits version_compat= line
# ---------------------------------------------------------------------------

def test_format_human_result_always_has_version_compat_line(session_root) -> None:
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=" in output


def test_format_human_result_compatible_no_advisory_warning(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=compatible" in output
    assert "version_compat_advisory" not in output
    assert "version_compat_disabled" not in output


def test_format_human_result_degraded_has_disabled_line(session_root) -> None:
    _write_version_manifest(session_root, memory_layout_version="0.9.0")
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=compatible_with_degradation" in output
    assert "version_compat_disabled=" in output
    assert "session_index" in output
    # advisory warning NOT required for degraded (session still runs)
    assert "manual action required" not in output


def test_format_human_result_migration_required_has_advisory(session_root) -> None:
    _write_version_manifest(session_root, hook_wiring_version="0.9.0")
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=migration_required" in output
    assert "version_compat_advisory=manual action required" in output


def test_format_human_result_unsupported_has_advisory(session_root) -> None:
    # No manifest → unsupported
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=unsupported" in output
    assert "version_compat_advisory=manual action required" in output


# ---------------------------------------------------------------------------
# Feature matrix is not re-derived in session_start
# ---------------------------------------------------------------------------

def test_disabled_features_come_from_check_output_not_session_logic(session_root) -> None:
    # Degrade memory_layout_version → session_index should be disabled
    _write_version_manifest(session_root, memory_layout_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    # session_start must not re-derive this — it comes from check output
    assert "session_index" in vc["disabled_runtime_features"]
    assert "pre_task_check" in vc["enabled_runtime_features"]


def test_enabled_features_come_from_check_output(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    vc = result["version_compatibility"]
    # All 6 features should be enabled when manifest is fully satisfied
    assert len(vc["enabled_runtime_features"]) == 6
    assert vc["disabled_runtime_features"] == []
