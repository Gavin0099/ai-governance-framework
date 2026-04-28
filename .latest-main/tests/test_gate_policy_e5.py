"""
E5 tests — repo-local gate policy discovery and provenance.

Covers:
  - Policy discovery precedence: repo_local > framework_default > builtin_default
  - provenance fields: policy_source, policy_path, fallback_used, repo_policy_present
  - repo_local_policy_missing warning in session_end_hook
  - session_end_hook gate_policy field exposes full provenance
  - human output displays policy_source + fallback_used + repo_policy_present
  - Repo-local policy can override framework default settings
  - to_provenance_dict() is serialisable
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.gate_policy import (
    GatePolicy,
    load_policy,
    POLICY_SOURCE_REPO_LOCAL,
    POLICY_SOURCE_FRAMEWORK_DEFAULT,
    POLICY_SOURCE_BUILTIN_DEFAULT,
    FAIL_MODE_PERMISSIVE,
    FAIL_MODE_AUDIT,
    FAIL_MODE_STRICT,
    _FRAMEWORK_POLICY_PATH,
)
from governance_tools.session_end_hook import run_session_end_hook, format_human_result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_repo_policy(project_root: Path, content: str) -> Path:
    pol_dir = project_root / "governance"
    pol_dir.mkdir(parents=True, exist_ok=True)
    p = pol_dir / "gate_policy.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _minimal_hr_result(**overrides) -> dict:
    base = {
        "ok": True,
        "session_id": "s-test",
        "closeout_status": "valid",
        "memory_tier": "no_update",
        "repo_readiness_level": 0,
        "repo_readiness_limiting_factor": None,
        "repo_closeout_activation_state": "unknown",
        "repo_activation_recency": None,
        "repo_activation_gap": None,
        "closeout_classification": None,
        "per_layer_results": {},
        "failure_signals": [],
        "failure_disposition": None,
        "gate_policy": {
            "fail_mode": "strict",
            "artifact_state": "absent",
            "blocked": True,
            "policy_source": POLICY_SOURCE_FRAMEWORK_DEFAULT,
            "policy_path": str(_FRAMEWORK_POLICY_PATH),
            "fallback_used": True,
            "repo_policy_present": False,
        },
        "closeout_file": "artifacts/session-closeout.txt",
        "decision": "DO_NOT_PROMOTE",
        "snapshot_created": False,
        "promoted": False,
        "memory_closeout": None,
        "warnings": [],
        "errors": [],
    }
    base.update(overrides)
    return base


@pytest.fixture
def tmp_project_root(tmp_path):
    (tmp_path / "artifacts" / "runtime").mkdir(parents=True)
    return tmp_path


# ── Discovery precedence ──────────────────────────────────────────────────────

def test_discovery_uses_framework_default_when_no_project_root():
    """load_policy() with no args uses framework default."""
    p = load_policy()
    assert p.policy_source == POLICY_SOURCE_FRAMEWORK_DEFAULT
    assert p.fallback_used is False        # no discovery was attempted
    assert p.repo_policy_present is False  # no project_root given
    assert "gate_policy.yaml" in p.policy_path


def test_discovery_uses_framework_default_when_project_root_has_no_policy(tmp_path):
    """project_root exists but has no governance/gate_policy.yaml → framework_default."""
    p = load_policy(project_root=tmp_path)
    assert p.policy_source == POLICY_SOURCE_FRAMEWORK_DEFAULT
    assert p.fallback_used is True
    assert p.repo_policy_present is False


def test_discovery_uses_repo_local_when_present(tmp_path):
    """project_root/governance/gate_policy.yaml → repo_local."""
    _write_repo_policy(tmp_path, "version: '1'\nfail_mode: permissive\n")
    p = load_policy(project_root=tmp_path)
    assert p.policy_source == POLICY_SOURCE_REPO_LOCAL
    assert p.fallback_used is False
    assert p.repo_policy_present is True
    assert p.fail_mode == FAIL_MODE_PERMISSIVE


def test_discovery_repo_local_overrides_framework_settings(tmp_path):
    """Repo-local policy completely replaces framework defaults."""
    _write_repo_policy(tmp_path, (
        "version: '1'\n"
        "fail_mode: audit\n"
        "blocking_actions: []\n"
        "artifact_stale_seconds: 7200\n"
    ))
    p = load_policy(project_root=tmp_path)
    assert p.fail_mode == FAIL_MODE_AUDIT
    assert p.blocking_actions == []
    assert p.artifact_stale_seconds == 7200


def test_discovery_explicit_path_kwarg_bypasses_discovery(tmp_path):
    """path= keyword bypasses project_root discovery entirely."""
    pol_file = tmp_path / "custom.yaml"
    pol_file.write_text("version: '1'\nfail_mode: audit\n", encoding="utf-8")
    p = load_policy(path=pol_file)
    assert p.fail_mode == FAIL_MODE_AUDIT
    assert p.policy_source == POLICY_SOURCE_REPO_LOCAL   # as if it's a local override


def test_discovery_builtin_default_when_framework_policy_absent(tmp_path, monkeypatch):
    """When neither repo-local nor framework file exists, builtin defaults are used."""
    import governance_tools.gate_policy as gp_mod
    original = gp_mod._FRAMEWORK_POLICY_PATH
    try:
        gp_mod._FRAMEWORK_POLICY_PATH = tmp_path / "nonexistent.yaml"
        p = load_policy(project_root=tmp_path)
        assert p.policy_source == POLICY_SOURCE_BUILTIN_DEFAULT
        assert p.fallback_used is True
        assert p.fail_mode == FAIL_MODE_STRICT   # builtin default
    finally:
        gp_mod._FRAMEWORK_POLICY_PATH = original


# ── Provenance fields ─────────────────────────────────────────────────────────

def test_provenance_dict_is_serialisable(tmp_path):
    _write_repo_policy(tmp_path, "version: '1'\nfail_mode: strict\n")
    p = load_policy(project_root=tmp_path)
    d = p.to_provenance_dict()
    assert json.dumps(d)   # must not raise
    assert d["policy_source"] == POLICY_SOURCE_REPO_LOCAL
    assert d["repo_policy_present"] is True
    assert d["fallback_used"] is False
    assert d["policy_path"]


def test_provenance_fallback_used_set_correctly(tmp_path):
    p = load_policy(project_root=tmp_path)        # no repo-local policy
    assert p.fallback_used is True
    assert p.repo_policy_present is False


def test_provenance_repo_policy_present_true_when_exists(tmp_path):
    _write_repo_policy(tmp_path, "version: '1'\n")
    p = load_policy(project_root=tmp_path)
    assert p.repo_policy_present is True


def test_policy_path_points_to_actual_file(tmp_path):
    pol = _write_repo_policy(tmp_path, "version: '1'\n")
    p = load_policy(project_root=tmp_path)
    assert p.policy_path == str(pol)


# ── repo_local_policy_missing warning ────────────────────────────────────────

def test_session_end_hook_emits_repo_local_policy_missing_warning(tmp_project_root):
    """tmp_project_root has no governance/gate_policy.yaml → warning emitted."""
    result = run_session_end_hook(project_root=tmp_project_root)
    assert any("repo_local_policy_missing" in w for w in result["warnings"])


def test_session_end_hook_no_missing_warning_when_repo_local_present(tmp_project_root):
    """When repo-local policy exists, no missing warning."""
    _write_repo_policy(tmp_project_root, "version: '1'\nfail_mode: permissive\n")
    result = run_session_end_hook(project_root=tmp_project_root)
    assert not any("repo_local_policy_missing" in w for w in result["warnings"])


def test_session_end_hook_missing_warning_names_fallback_source(tmp_project_root):
    """The warning message names which policy source is being used."""
    result = run_session_end_hook(project_root=tmp_project_root)
    missing_warnings = [w for w in result["warnings"] if "repo_local_policy_missing" in w]
    assert len(missing_warnings) == 1
    assert "framework_default" in missing_warnings[0] or "builtin" in missing_warnings[0]


# ── gate_policy field in session_end_hook result ─────────────────────────────

def test_session_end_hook_gate_policy_has_full_provenance(tmp_project_root):
    result = run_session_end_hook(project_root=tmp_project_root)
    gp = result["gate_policy"]
    assert "policy_source" in gp
    assert "policy_path" in gp
    assert "fallback_used" in gp
    assert "repo_policy_present" in gp
    assert gp["repo_policy_present"] is False
    assert gp["fallback_used"] is True


def test_session_end_hook_gate_policy_shows_repo_local_when_present(tmp_project_root):
    _write_repo_policy(tmp_project_root, "version: '1'\nfail_mode: permissive\n")
    result = run_session_end_hook(project_root=tmp_project_root)
    gp = result["gate_policy"]
    assert gp["policy_source"] == POLICY_SOURCE_REPO_LOCAL
    assert gp["fallback_used"] is False
    assert gp["repo_policy_present"] is True


def test_session_end_hook_repo_local_permissive_skips_strict_gate(tmp_project_root):
    """Repo says permissive → absent artifact does NOT block."""
    _write_repo_policy(tmp_project_root, "version: '1'\nfail_mode: permissive\n")
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["gate_policy"]["blocked"] is False
    assert not any("[gate_policy:strict]" in e for e in result["errors"])


def test_session_end_hook_repo_local_audit_never_blocks(tmp_project_root):
    """Repo says audit → gate never blocks regardless of disposition."""
    _write_repo_policy(tmp_project_root, "version: '1'\nfail_mode: audit\n")
    artifact_dir = tmp_project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "latest.json").write_text(json.dumps({
        "source": "pytest-text",
        "failure_disposition": {
            "verdict_blocked": True,
            "total": 3,
            "unknown_count": 0,
            "taxonomy_expansion_signal": False,
            "by_action": {"production_fix_required": 3},
        },
    }), encoding="utf-8")
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["gate_policy"]["blocked"] is False


# ── human output ──────────────────────────────────────────────────────────────

def test_format_human_result_shows_policy_source_and_provenance():
    result = _minimal_hr_result()
    output = format_human_result(result)
    assert "gate_policy:" in output
    assert "policy_source=" in output
    assert "fallback_used=" in output
    assert "repo_policy_present=" in output


def test_format_human_result_shows_policy_path():
    result = _minimal_hr_result()
    result["gate_policy"]["policy_path"] = "/some/path/gate_policy.yaml"
    output = format_human_result(result)
    assert "policy_path=/some/path/gate_policy.yaml" in output


def test_format_human_result_no_policy_path_line_when_empty():
    result = _minimal_hr_result()
    result["gate_policy"]["policy_path"] = ""
    output = format_human_result(result)
    assert "policy_path=" not in output
