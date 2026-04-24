from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from governance_tools.governance_version_check import (
    ALLOWED_VERDICTS,
    VersionCompatibilityResult,
    _parse_version,
    _satisfies,
    check_version_compatibility,
    format_summary,
    write_compatibility_artifact,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal valid YAML content
# ---------------------------------------------------------------------------

_REQUIRED_VERSIONS_MINIMAL = {
    "schema_version": "1.0",
    "framework_version": "0.4.0",
    "required": {
        "contract_schema_version": ">=1.2.0",
        "runtime_entrypoint_version": ">=1.1.0",
        "hook_wiring_version": ">=1.0.0",
        "artifact_layout_version": ">=1.0.0",
        "memory_layout_version": ">=1.0.0",
    },
    "features": {
        "pre_task_check": {
            "tier": "core",
            "requires": {
                "runtime_entrypoint_version": ">=1.0.0",
                "hook_wiring_version": ">=1.0.0",
            },
        },
        "post_task_check": {
            "tier": "core",
            "requires": {
                "runtime_entrypoint_version": ">=1.0.0",
                "hook_wiring_version": ">=1.0.0",
            },
        },
        "canonical_closeout": {
            "tier": "extended",
            "requires": {
                "artifact_layout_version": ">=1.0.0",
                "runtime_entrypoint_version": ">=1.0.0",
            },
        },
        "session_index": {
            "tier": "extended",
            "requires": {
                "memory_layout_version": ">=1.0.0",
            },
        },
        "agents_rule_candidates": {
            "tier": "extended",
            "requires": {
                "artifact_layout_version": ">=1.0.0",
            },
        },
        "decision_context_bridge": {
            "tier": "extended",
            "requires": {
                "runtime_entrypoint_version": ">=1.1.0",
                "contract_schema_version": ">=1.2.0",
            },
        },
    },
}

_VERSION_MANIFEST_FULL = {
    "schema_version": "1.0",
    "governance_version": "0.4.0",
    "contract_schema_version": "1.2.0",
    "runtime_entrypoint_version": "1.1.0",
    "hook_wiring_version": "1.0.0",
    "artifact_layout_version": "1.0.0",
    "memory_layout_version": "1.0.0",
}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _make_paths(tmp_path: Path, manifest_override: dict | None = None) -> tuple[Path, Path]:
    req_path = tmp_path / "required_versions.yaml"
    manifest_path = tmp_path / "version_manifest.yaml"
    _write_yaml(req_path, _REQUIRED_VERSIONS_MINIMAL)
    manifest = {**_VERSION_MANIFEST_FULL, **(manifest_override or {})}
    _write_yaml(manifest_path, manifest)
    return req_path, manifest_path


# ---------------------------------------------------------------------------
# Version comparison unit tests
# ---------------------------------------------------------------------------

def test_parse_version_basic() -> None:
    assert _parse_version("1.2.3") == (1, 2, 3)
    assert _parse_version("1.0") == (1, 0)
    assert _parse_version("2") == (2,)


def test_satisfies_gte_equal() -> None:
    assert _satisfies("1.2.0", ">=1.2.0") is True


def test_satisfies_gte_greater() -> None:
    assert _satisfies("1.3.0", ">=1.2.0") is True


def test_satisfies_gte_less() -> None:
    assert _satisfies("1.1.0", ">=1.2.0") is False


def test_satisfies_patch_greater() -> None:
    assert _satisfies("1.2.1", ">=1.2.0") is True


def test_satisfies_major_less() -> None:
    assert _satisfies("0.9.9", ">=1.0.0") is False


def test_satisfies_unsupported_operator_raises() -> None:
    with pytest.raises(ValueError, match="unsupported version operator"):
        _satisfies("1.0.0", "==1.0.0")


# ---------------------------------------------------------------------------
# Case 1: All versions satisfied → compatible
# ---------------------------------------------------------------------------

def test_full_manifest_returns_compatible(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "compatible"
    assert result.repo_manifest_found is True
    assert result.error is None
    assert result.disabled_runtime_features == []
    assert len(result.enabled_runtime_features) > 0
    assert result.missing_migrations == []


def test_all_checks_satisfied_when_compatible(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert all(c.satisfied for c in result.checks)


# ---------------------------------------------------------------------------
# Case 2: Old contract_schema_version → decision_context_bridge disabled
# ---------------------------------------------------------------------------

def test_old_contract_schema_disables_decision_context_bridge(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(
        tmp_path,
        manifest_override={"contract_schema_version": "1.1.0"},
    )
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    # contract_schema_version 1.1.0 < required 1.2.0 → check fails
    # decision_context_bridge requires contract_schema_version >= 1.2.0 → disabled
    # decision_context_bridge is extended tier → compatible_with_degradation
    assert result.verdict in ("migration_required", "compatible_with_degradation")
    assert "decision_context_bridge" in result.disabled_runtime_features


# ---------------------------------------------------------------------------
# Case 3: Old memory_layout, runtime ok → compatible_with_degradation
# ---------------------------------------------------------------------------

def test_old_memory_layout_gives_degraded_verdict(tmp_path: Path) -> None:
    # memory_layout_version 0.9.0 < required 1.0.0 → session_index disabled
    # session_index is extended → compatible_with_degradation
    req_path, manifest_path = _make_paths(
        tmp_path,
        manifest_override={"memory_layout_version": "0.9.0"},
    )
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "compatible_with_degradation"
    assert "session_index" in result.disabled_runtime_features
    # Core features must still be enabled
    assert "pre_task_check" in result.enabled_runtime_features
    assert "post_task_check" in result.enabled_runtime_features


# ---------------------------------------------------------------------------
# Case 4: Missing version_manifest → unsupported
# ---------------------------------------------------------------------------

def test_missing_version_manifest_returns_unsupported(tmp_path: Path) -> None:
    req_path = tmp_path / "required_versions.yaml"
    _write_yaml(req_path, _REQUIRED_VERSIONS_MINIMAL)
    missing_manifest = tmp_path / "nonexistent_manifest.yaml"

    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=missing_manifest,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "unsupported"
    assert result.repo_manifest_found is False
    assert result.error is not None
    assert "version_manifest_load_error" in result.error


# ---------------------------------------------------------------------------
# Case 5: Manifest format error → unsupported
# ---------------------------------------------------------------------------

def test_corrupt_manifest_returns_unsupported(tmp_path: Path) -> None:
    req_path = tmp_path / "required_versions.yaml"
    _write_yaml(req_path, _REQUIRED_VERSIONS_MINIMAL)
    bad_manifest = tmp_path / "version_manifest.yaml"
    bad_manifest.write_text(": : : invalid yaml {{{{", encoding="utf-8")

    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=bad_manifest,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "unsupported"
    assert result.repo_manifest_found is False


# ---------------------------------------------------------------------------
# Case 6: Old hook_wiring_version disables core feature → migration_required
# ---------------------------------------------------------------------------

def test_old_hook_wiring_gives_migration_required(tmp_path: Path) -> None:
    # hook_wiring_version 0.9.0 < required 1.0.0 → pre_task_check / post_task_check disabled
    # Both are core tier → migration_required
    req_path, manifest_path = _make_paths(
        tmp_path,
        manifest_override={"hook_wiring_version": "0.9.0"},
    )
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "migration_required"
    assert "pre_task_check" in result.disabled_runtime_features
    assert "post_task_check" in result.disabled_runtime_features


# ---------------------------------------------------------------------------
# Authority boundary: verdict values are always from ALLOWED_VERDICTS
# ---------------------------------------------------------------------------

def test_verdict_is_always_allowed(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict in ALLOWED_VERDICTS


# ---------------------------------------------------------------------------
# to_dict / artifact write
# ---------------------------------------------------------------------------

def test_result_to_dict_is_serializable(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    d = result.to_dict()
    # Must be JSON-serializable without error
    serialized = json.dumps(d)
    assert "compatible" in serialized


def test_write_compatibility_artifact(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    artifact_path = tmp_path / "out" / "version_compatibility.json"
    write_compatibility_artifact(result, artifact_path)
    assert artifact_path.is_file()
    loaded = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert loaded["verdict"] == "compatible"
    assert loaded["schema_version"] == "1.0"


# ---------------------------------------------------------------------------
# format_summary smoke
# ---------------------------------------------------------------------------

def test_format_summary_compatible(tmp_path: Path) -> None:
    req_path, manifest_path = _make_paths(tmp_path)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    summary = format_summary(result)
    assert "compatible" in summary
    assert "framework_version" in summary


def test_format_summary_unsupported(tmp_path: Path) -> None:
    req_path = tmp_path / "required_versions.yaml"
    _write_yaml(req_path, _REQUIRED_VERSIONS_MINIMAL)
    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=tmp_path / "nonexistent.yaml",
        checked_at="2026-04-24T00:00:00Z",
    )
    summary = format_summary(result)
    assert "UNSUPPORTED" in summary
    assert "error" in summary


# ---------------------------------------------------------------------------
# Real manifest paths: verify this repo passes its own check
# ---------------------------------------------------------------------------

def test_this_repo_passes_its_own_version_check() -> None:
    project_root = Path(__file__).resolve().parent.parent
    req_path = project_root / "governance" / "runtime" / "required_versions.yaml"
    manifest_path = project_root / ".governance" / "version_manifest.yaml"

    if not req_path.is_file() or not manifest_path.is_file():
        pytest.skip("required_versions.yaml or version_manifest.yaml not present")

    result = check_version_compatibility(
        required_versions_path=req_path,
        version_manifest_path=manifest_path,
        checked_at="2026-04-24T00:00:00Z",
    )
    assert result.verdict == "compatible", (
        f"This repo failed its own version check: {result.verdict}\n"
        f"Disabled: {result.disabled_runtime_features}\n"
        f"Missing migrations: {result.missing_migrations}"
    )
