"""
Tests for gate_policy.py

Covers:
  - policy loading (from file, defaults on missing/corrupt)
  - artifact state classification (absent, malformed, stale, ok)
  - gate evaluation for each fail_mode × artifact state combination
  - blocking_actions enforcement
  - unknown_treatment modes
  - session_end_hook integration with gate_policy (fail_mode changes visible in result)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.gate_policy import (
    GatePolicy,
    load_policy,
    classify_artifact,
    evaluate_gate,
    ArtifactResult,
    ARTIFACT_STATE_ABSENT,
    ARTIFACT_STATE_MALFORMED,
    ARTIFACT_STATE_STALE,
    ARTIFACT_STATE_OK,
    FAIL_MODE_STRICT,
    FAIL_MODE_PERMISSIVE,
    FAIL_MODE_AUDIT,
    POLICY_SOURCE_BUILTIN_DEFAULT,
    POLICY_SOURCE_FRAMEWORK_DEFAULT,
)
from governance_tools.session_end_hook import run_session_end_hook


# ── Helpers ───────────────────────────────────────────────────────────────────

def _policy(**overrides) -> GatePolicy:
    base = GatePolicy(
        fail_mode=FAIL_MODE_STRICT,
        blocking_actions=["production_fix_required"],
        unknown_treatment_mode="block_if_count_exceeds",
        unknown_treatment_threshold=3,
        artifact_stale_seconds=86400,
        source="test",
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _write_artifact(tmp_path: Path, disposition: dict | None, *, stale: bool = False) -> Path:
    artifact_dir = tmp_path / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "latest.json"
    payload = {"source": "pytest-text", "failure_disposition": disposition}
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    if stale:
        # back-date mtime by 2 days
        old = time.time() - 172800
        import os
        os.utime(artifact, (old, old))
    return artifact


def _clean_disposition(verdict_blocked=False, pfr=0, unknown=0, taxonomy_signal=False) -> dict:
    return {
        "verdict_blocked": verdict_blocked,
        "total": pfr + unknown,
        "unknown_count": unknown,
        "taxonomy_expansion_signal": taxonomy_signal,
        "by_action": {
            "production_fix_required": pfr,
            "test_fix_only": 0,
            "quarantine": 0,
            "escalate": unknown,
            "ignore_for_verdict": 0,
        },
    }


# ── load_policy ───────────────────────────────────────────────────────────────

def test_load_policy_reads_governance_yaml():
    policy = load_policy()
    assert policy.fail_mode == FAIL_MODE_STRICT
    assert "production_fix_required" in policy.blocking_actions
    assert policy.artifact_stale_seconds > 0
    assert "gate_policy.yaml" in policy.source


def test_load_policy_falls_back_to_defaults_when_file_missing(tmp_path):
    policy = load_policy(path=tmp_path / "nonexistent.yaml")
    assert policy.fail_mode == FAIL_MODE_STRICT          # default
    assert policy.policy_source == POLICY_SOURCE_BUILTIN_DEFAULT


def test_load_policy_falls_back_to_defaults_on_bad_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(": : : invalid yaml :::", encoding="utf-8")
    # PyYAML may or may not raise on this — what matters is we get a policy back
    policy = load_policy(path=bad)
    assert isinstance(policy, GatePolicy)


def test_load_policy_honours_custom_fail_mode(tmp_path):
    cfg = tmp_path / "policy.yaml"
    cfg.write_text("version: '1'\nfail_mode: permissive\n", encoding="utf-8")
    policy = load_policy(path=cfg)
    assert policy.fail_mode == FAIL_MODE_PERMISSIVE


# ── classify_artifact ─────────────────────────────────────────────────────────

def test_classify_artifact_absent(tmp_path):
    result = classify_artifact(tmp_path / "nonexistent.json", _policy())
    assert result.state == ARTIFACT_STATE_ABSENT
    assert result.failure_disposition is None


def test_classify_artifact_malformed_bad_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{ not json }", encoding="utf-8")
    result = classify_artifact(f, _policy())
    assert result.state == ARTIFACT_STATE_MALFORMED
    assert result.load_error is not None


def test_classify_artifact_malformed_non_object(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    result = classify_artifact(f, _policy())
    assert result.state == ARTIFACT_STATE_MALFORMED


def test_classify_artifact_stale(tmp_path):
    artifact = _write_artifact(tmp_path, _clean_disposition(), stale=True)
    policy = _policy(artifact_stale_seconds=3600)   # 1 h threshold
    result = classify_artifact(artifact, policy)
    assert result.state == ARTIFACT_STATE_STALE
    assert result.stale_seconds > 3600


def test_classify_artifact_ok(tmp_path):
    artifact = _write_artifact(tmp_path, _clean_disposition())
    result = classify_artifact(artifact, _policy())
    assert result.state == ARTIFACT_STATE_OK
    assert result.failure_disposition is not None


def test_classify_artifact_stale_disabled(tmp_path):
    artifact = _write_artifact(tmp_path, _clean_disposition(), stale=True)
    policy = _policy(artifact_stale_seconds=0)
    result = classify_artifact(artifact, policy)
    assert result.state == ARTIFACT_STATE_OK   # stale detection disabled


def test_classify_artifact_ok_disposition_none_field(tmp_path):
    artifact = _write_artifact(tmp_path, None)
    result = classify_artifact(artifact, _policy())
    assert result.state == ARTIFACT_STATE_OK
    assert result.failure_disposition is None


# ── evaluate_gate — strict fail_mode ─────────────────────────────────────────

def test_strict_absent_blocks_with_error():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    ar = ArtifactResult(state=ARTIFACT_STATE_ABSENT)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True
    assert any("absent" in e for e in dec.errors)


def test_strict_malformed_blocks_with_error():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    ar = ArtifactResult(state=ARTIFACT_STATE_MALFORMED, load_error="invalid json")
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True
    assert any("malformed" in e for e in dec.errors)


def test_strict_stale_warns_and_still_evaluates_disposition():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    disp = _clean_disposition(verdict_blocked=True, pfr=1)
    ar = ArtifactResult(state=ARTIFACT_STATE_STALE, failure_disposition=disp, stale_seconds=90000)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True
    assert any("stale" in w for w in dec.warnings)
    assert any("production_fix_required" in e for e in dec.errors)


def test_strict_stale_warns_but_does_not_block_if_no_blocking_failures():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    disp = _clean_disposition(verdict_blocked=False, pfr=0)
    ar = ArtifactResult(state=ARTIFACT_STATE_STALE, failure_disposition=disp, stale_seconds=90000)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False
    assert any("stale" in w for w in dec.warnings)


def test_strict_ok_no_failures_passes():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    disp = _clean_disposition()
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False
    assert dec.errors == []


def test_strict_ok_production_fix_required_blocks():
    policy = _policy(fail_mode=FAIL_MODE_STRICT)
    disp = _clean_disposition(verdict_blocked=True, pfr=2)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True
    assert any("production_fix_required" in e for e in dec.errors)
    assert "2" in " ".join(dec.errors)


# ── evaluate_gate — permissive fail_mode ─────────────────────────────────────

def test_permissive_absent_does_not_block():
    policy = _policy(fail_mode=FAIL_MODE_PERMISSIVE)
    ar = ArtifactResult(state=ARTIFACT_STATE_ABSENT)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False
    assert dec.errors == []


def test_permissive_malformed_does_not_block():
    policy = _policy(fail_mode=FAIL_MODE_PERMISSIVE)
    ar = ArtifactResult(state=ARTIFACT_STATE_MALFORMED, load_error="bad")
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False


def test_permissive_stale_does_not_block():
    policy = _policy(fail_mode=FAIL_MODE_PERMISSIVE)
    disp = _clean_disposition(verdict_blocked=True, pfr=1)
    ar = ArtifactResult(state=ARTIFACT_STATE_STALE, failure_disposition=disp, stale_seconds=90000)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False


def test_permissive_ok_production_fix_required_blocks():
    policy = _policy(fail_mode=FAIL_MODE_PERMISSIVE)
    disp = _clean_disposition(verdict_blocked=True, pfr=1)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True


# ── evaluate_gate — audit fail_mode ──────────────────────────────────────────

def test_audit_absent_never_blocks():
    policy = _policy(fail_mode=FAIL_MODE_AUDIT)
    ar = ArtifactResult(state=ARTIFACT_STATE_ABSENT)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False
    assert any("audit" in w for w in dec.warnings)


def test_audit_ok_production_fix_required_still_does_not_block():
    policy = _policy(fail_mode=FAIL_MODE_AUDIT)
    disp = _clean_disposition(verdict_blocked=True, pfr=3)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False


# ── unknown_treatment ─────────────────────────────────────────────────────────

def test_unknown_treatment_always_block():
    policy = _policy(unknown_treatment_mode="always_block", unknown_treatment_threshold=0)
    disp = _clean_disposition(unknown=1)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is True
    assert any("unknown" in e for e in dec.errors)


def test_unknown_treatment_block_if_count_exceeds_threshold():
    policy = _policy(unknown_treatment_mode="block_if_count_exceeds", unknown_treatment_threshold=3)
    disp_below = _clean_disposition(unknown=3)
    disp_above = _clean_disposition(unknown=4)
    assert evaluate_gate(ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp_below), policy).blocked is False
    assert evaluate_gate(ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp_above), policy).blocked is True


def test_unknown_treatment_never_block_adds_warning_not_error():
    policy = _policy(unknown_treatment_mode="never_block")
    disp = _clean_disposition(unknown=10)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert dec.blocked is False
    assert any("unclassified" in w for w in dec.warnings)


# ── taxonomy_expansion_signal advisory ───────────────────────────────────────

def test_taxonomy_expansion_signal_surfaces_as_warning():
    policy = _policy()
    disp = _clean_disposition(taxonomy_signal=True, unknown=2)
    ar = ArtifactResult(state=ARTIFACT_STATE_OK, failure_disposition=disp)
    dec = evaluate_gate(ar, policy)
    assert any("taxonomy_expansion_signal" in w for w in dec.warnings)


# ── session_end_hook integration ──────────────────────────────────────────────

@pytest.fixture
def tmp_project_root(tmp_path):
    (tmp_path / "artifacts" / "runtime").mkdir(parents=True)
    return tmp_path


def test_session_end_hook_result_has_gate_policy_field(tmp_project_root):
    result = run_session_end_hook(project_root=tmp_project_root)
    assert "gate_policy" in result
    gp = result["gate_policy"]
    assert "fail_mode" in gp
    assert "artifact_state" in gp
    assert "blocked" in gp


def test_session_end_hook_strict_absent_sets_ok_false(tmp_project_root):
    """Default policy is strict → absent artifact → blocked → ok=False."""
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["gate_policy"]["artifact_state"] == ARTIFACT_STATE_ABSENT
    assert result["gate_policy"]["blocked"] is True
    assert result["ok"] is False
    assert any("[gate_policy:strict]" in e for e in result["errors"])


def test_session_end_hook_permissive_absent_does_not_block(tmp_project_root):
    """Repo-local policy set to permissive → absent artifact is ignored."""
    # Place the policy in the proper repo-local location
    pol_dir = tmp_project_root / "governance"
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nfail_mode: permissive\n", encoding="utf-8"
    )
    result = run_session_end_hook(project_root=tmp_project_root)

    assert result["gate_policy"]["artifact_state"] == ARTIFACT_STATE_ABSENT
    assert result["gate_policy"]["blocked"] is False
    assert not any("[gate_policy:strict]" in e for e in result["errors"])


def test_session_end_hook_ok_artifact_no_failures_passes_gate(tmp_project_root):
    artifact_dir = tmp_project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "latest.json").write_text(
        json.dumps({"source": "pytest-text", "failure_disposition": None}),
        encoding="utf-8",
    )
    # Place repo-local permissive policy
    pol_dir = tmp_project_root / "governance"
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nfail_mode: permissive\n", encoding="utf-8"
    )
    result = run_session_end_hook(project_root=tmp_project_root)

    assert result["gate_policy"]["blocked"] is False
    assert not any("[GATE:" in e for e in result["errors"])


def test_session_end_hook_format_includes_gate_policy_line(tmp_project_root):
    from governance_tools.session_end_hook import format_human_result
    fake = {
        "ok": False,
        "session_id": "s-test",
        "closeout_status": "closeout_missing",
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
            "policy_source": "framework_default",
            "policy_path": "governance/gate_policy.yaml",
            "fallback_used": True,
            "repo_policy_present": False,
        },
        "closeout_file": "artifacts/session-closeout.txt",
        "decision": "DO_NOT_PROMOTE",
        "snapshot_created": False,
        "promoted": False,
        "memory_closeout": None,
        "warnings": [],
        "errors": ["[gate_policy:strict] test-result artifact absent"],
    }
    output = format_human_result(fake)
    assert "gate_policy:" in output
    assert "fail_mode=strict" in output
    assert "artifact_state=absent" in output


# ── skip_type field ───────────────────────────────────────────────────────────

def test_load_policy_parses_skip_type_structural(tmp_path):
    pol_dir = tmp_path / "governance"
    pol_dir.mkdir(parents=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nskip_test_result_check: true\nskip_type: structural\n",
        encoding="utf-8",
    )
    policy = load_policy(path=pol_dir / "gate_policy.yaml")
    assert policy.skip_test_result_check is True
    assert policy.skip_type == "structural"
    assert policy.to_provenance_dict()["skip_type"] == "structural"


def test_load_policy_parses_skip_type_temporary(tmp_path):
    pol_dir = tmp_path / "governance"
    pol_dir.mkdir(parents=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nskip_test_result_check: true\nskip_type: temporary\n",
        encoding="utf-8",
    )
    policy = load_policy(path=pol_dir / "gate_policy.yaml")
    assert policy.skip_type == "temporary"


def test_load_policy_rejects_invalid_skip_type(tmp_path):
    pol_dir = tmp_path / "governance"
    pol_dir.mkdir(parents=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nskip_test_result_check: true\nskip_type: unknown_value\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="skip_type"):
        load_policy(path=pol_dir / "gate_policy.yaml")


def test_load_policy_skip_type_defaults_to_none(tmp_path):
    pol_dir = tmp_path / "governance"
    pol_dir.mkdir(parents=True)
    (pol_dir / "gate_policy.yaml").write_text(
        "version: '1'\nfail_mode: permissive\n",
        encoding="utf-8",
    )
    policy = load_policy(path=pol_dir / "gate_policy.yaml")
    assert policy.skip_type is None
    assert policy.to_provenance_dict()["skip_type"] is None
