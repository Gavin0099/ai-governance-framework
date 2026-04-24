"""Tests for governance version compatibility integration in session_start.

These tests verify:
  - version_compatibility key is always present in session_start result
  - compatible/degraded/migration_required remain advisory_only=True
  - unsupported triggers controlled refusal and advisory_only=False
  - migration_required enters legacy_only instead of blocking
  - format_human_result always emits version_compat= line
  - compatible verdict produces no advisory warning lines
  - degraded/migration_required/unsupported produce appropriate output lines
  - session_start does not re-derive feature matrix logic
  - unsupported semantics remain unchanged while legacy_only skips new-runtime consumers
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


FIXTURE_ROOT = Path("tests/_tmp_session_start_version_compat")


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
def session_root(request):
    path = FIXTURE_ROOT / request.node.name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    _minimal_plan(path)
    (path / "tool.py").write_text("print('ok')", encoding="utf-8")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


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


def test_version_compatibility_key_always_present(session_root) -> None:
    result = _run(session_root)
    assert "version_compatibility" in result


def test_version_compatibility_advisory_only_true_for_supported_verdicts(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["advisory_only"] is True


def test_version_compatibility_unsupported_is_not_advisory_only(session_root) -> None:
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "unsupported"
    assert vc["advisory_only"] is False


def test_version_compatibility_has_verdict(session_root) -> None:
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] in ("compatible", "compatible_with_degradation", "migration_required", "unsupported")


def test_session_start_controlled_refusal_when_manifest_missing(session_root) -> None:
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "unsupported"
    assert result["status"] == "blocked"
    assert result["mode"] == "controlled_refusal"
    assert result["reason"] == "version_compatibility_unsupported"
    assert result["ok"] is False


def test_session_start_not_blocked_when_manifest_present_compatible(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "compatible"
    assert vc["advisory_only"] is True
    assert isinstance(result, dict)


def test_session_start_not_blocked_when_manifest_degraded(session_root) -> None:
    _write_version_manifest(session_root, memory_layout_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "compatible_with_degradation"
    assert vc["advisory_only"] is True
    assert isinstance(result, dict)


def test_session_start_not_blocked_when_migration_required(session_root) -> None:
    _write_version_manifest(session_root, hook_wiring_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert vc["verdict"] == "migration_required"
    assert vc["advisory_only"] is True
    assert result["status"] == "degraded"
    assert result["mode"] == "legacy_only"
    assert result["reason"] == "version_compatibility_migration_required"
    assert isinstance(result, dict)


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
    assert "manual action required" not in output


def test_format_human_result_migration_required_has_advisory(session_root) -> None:
    _write_version_manifest(session_root, hook_wiring_version="0.9.0")
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=migration_required" in output
    assert "status=degraded" in output
    assert "mode=legacy_only" in output
    assert "version_compat_advisory=manual action required" in output
    assert "legacy_only_boundary=feature_gated_runtime_extensions_not_loaded" in output
    assert "legacy_allowed_features=core_pre_task_check,core_post_task_check,basic_version_compatibility_artifact_write" in output
    assert "legacy_disabled_features=post_task_check,pre_task_check" in output
    assert "legacy_no_reinference_rule=" in output


def test_format_human_result_unsupported_has_controlled_refusal_lines(session_root) -> None:
    result = _run(session_root)
    output = format_human_result(result)
    assert "version_compat=unsupported" in output
    assert "version_compat_advisory=manual action required" in output
    assert "status=blocked" in output
    assert "mode=controlled_refusal" in output
    assert "controlled_refusal_boundary=downstream_governance_features_not_loaded" in output


def test_disabled_features_come_from_check_output_not_session_logic(session_root) -> None:
    _write_version_manifest(session_root, memory_layout_version="0.9.0")
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert "session_index" in vc["disabled_runtime_features"]
    assert "pre_task_check" in vc["enabled_runtime_features"]


def test_enabled_features_come_from_check_output(session_root) -> None:
    _write_version_manifest(session_root)
    result = _run(session_root)
    vc = result["version_compatibility"]
    assert len(vc["enabled_runtime_features"]) == 6
    assert vc["disabled_runtime_features"] == []


def test_migration_required_short_circuits_new_runtime_consumers(session_root, monkeypatch) -> None:
    _write_version_manifest(session_root, hook_wiring_version="0.9.0")
    calls: list[str] = []

    def _record_if_called(name: str):
        def _inner(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"{name} should not be called in legacy_only mode")
        return _inner

    monkeypatch.setattr("runtime_hooks.core.session_start.generate_state", _record_if_called("generate_state"))
    monkeypatch.setattr("runtime_hooks.core.session_start.build_change_proposal", _record_if_called("build_change_proposal"))
    monkeypatch.setattr("runtime_hooks.core.session_start.load_closeout_context", _record_if_called("load_closeout_context"))

    result = _run(session_root)

    assert result["mode"] == "legacy_only"
    assert result["closeout_context"] is None
    assert result["legacy_capability_policy"]["mode"] == "legacy_only"
    assert result["legacy_capability_policy"]["disabled_features"] == ["post_task_check", "pre_task_check"]
    assert result["legacy_capability_policy"]["artifact_write_policy"]["allowed"] == [
        "artifacts/governance/version_compatibility.json"
    ]
    assert calls == []


def test_unsupported_short_circuits_downstream_consumption(session_root, monkeypatch) -> None:
    calls: list[str] = []

    def _fail_if_called(name: str):
        def _inner(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"{name} should not be called under controlled refusal")
        return _inner

    monkeypatch.setattr("runtime_hooks.core.session_start.generate_state", _fail_if_called("generate_state"))
    monkeypatch.setattr("runtime_hooks.core.session_start.run_pre_task_check", _fail_if_called("run_pre_task_check"))
    monkeypatch.setattr("runtime_hooks.core.session_start.load_closeout_context", _fail_if_called("load_closeout_context"))

    result = _run(session_root)

    assert result["mode"] == "controlled_refusal"
    assert calls == []
