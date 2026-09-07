"""Owner-defined gate input contract, exercised through the real closeout hook."""

import json
import os
from pathlib import Path

import pytest

from governance_tools.gate_policy import classify_artifact, evaluate_gate, load_policy
from governance_tools.session_end_hook import run_session_end_hook
from runtime_hooks.core._canonical_closeout import write_candidate, write_session_envelope


def _ready_closeout(root: Path, mode: object) -> None:
    """Real session envelope, bound candidate, and matching valid closeout."""
    write_session_envelope("gate-input-replay", root, provider="test")
    evidence = root / "evidence.txt"
    evidence.write_text("isolated gate input replay\n", encoding="utf-8")
    intent = "validate gate input handling"
    summary = "prepared evidence.txt for isolated closeout replay"
    write_candidate("gate-input-replay", root, {
        "task_intent": intent,
        "work_summary": summary,
        "tools_used": ["inspect"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
    })
    (root / "artifacts" / "session-closeout.txt").write_text(
        f"TASK_INTENT: {intent}\nWORK_COMPLETED: {summary}\n"
        "FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n"
        "NOT_DONE: consumer replay\nRECOMMENDED_MEMORY_UPDATE: NONE\n",
        encoding="utf-8",
    )
    (root / "governance").mkdir()
    # JSON scalar values are also YAML, retaining null/bool/number types.
    (root / "governance" / "gate_policy.yaml").write_text(
        f"fail_mode: {json.dumps(mode)}\nartifact_stale_seconds: 86400\n",
        encoding="utf-8",
    )


def _artifact(root: Path, value: object, *, stale: bool = False) -> Path:
    path = root / "artifacts" / "runtime" / "test-results" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"failure_disposition": value}), encoding="utf-8")
    if stale:
        os.utime(path, (1, 1))
    return path


def _close(root: Path) -> dict:
    return run_session_end_hook(
        root, hook_session_id="gate-input-replay", ledger_write_allowed=False,
    )


def test_session_end_hook_typo_mode_missing_artifact_fails_closed(tmp_path):
    _ready_closeout(tmp_path, "strcit")
    with pytest.raises(ValueError, match="invalid fail_mode"):
        _close(tmp_path)


@pytest.mark.parametrize("stale", [False, True])
def test_session_end_hook_strict_empty_list_cannot_complete(tmp_path, stale):
    _ready_closeout(tmp_path, "strict")
    _artifact(tmp_path, [], stale=stale)
    result = _close(tmp_path)
    assert result["closeout_status"] == "valid", result
    assert result["gate_policy"]["artifact_state"] == "malformed", result
    assert result["gate_policy"]["blocked"] is True
    assert result["ok"] is False


@pytest.mark.parametrize("value", [None, {}, {"by_action": {}, "unknown_count": 0}])
def test_session_end_hook_strict_legal_no_failure_completes(tmp_path, value):
    _ready_closeout(tmp_path, "strict")
    _artifact(tmp_path, value)
    result = _close(tmp_path)
    assert result["closeout_status"] == "valid", result
    assert result["gate_policy"]["artifact_state"] == "ok"
    assert result["gate_policy"]["blocked"] is False
    assert result["ok"] is True, result


def test_session_end_hook_strict_production_failure_still_blocks(tmp_path):
    _ready_closeout(tmp_path, "strict")
    _artifact(tmp_path, {"by_action": {"production_fix_required": 1}})
    result = _close(tmp_path)
    assert result["closeout_status"] == "valid", result
    assert result["gate_policy"]["blocked"] is True
    assert result["ok"] is False


def test_session_end_hook_strict_missing_artifact_still_blocks(tmp_path):
    _ready_closeout(tmp_path, "strict")
    result = _close(tmp_path)
    assert result["closeout_status"] == "valid", result
    assert result["gate_policy"]["blocked"] is True
    assert result["ok"] is False


@pytest.mark.parametrize("mode", ["strcit", "", "STRICT", " strict ", None, 0, False, [], {}])
def test_invalid_policy_mode_raises_without_fallback(tmp_path, mode):
    _ready_closeout(tmp_path, mode)
    with pytest.raises(ValueError, match="invalid fail_mode"):
        load_policy(project_root=tmp_path)


@pytest.mark.parametrize("mode", ["strict", "permissive", "audit"])
def test_legal_policy_modes_preserved(tmp_path, mode):
    _ready_closeout(tmp_path, mode)
    policy = load_policy(project_root=tmp_path)
    assert policy.fail_mode == mode
    assert policy.fallback_used is False


@pytest.mark.parametrize("value", [[], [1], "", "bad", 0, 1, 0.5, False, True])
@pytest.mark.parametrize("stale", [False, True])
@pytest.mark.parametrize("mode", ["strict", "permissive", "audit"])
def test_wrong_disposition_types_classified_before_staleness(tmp_path, value, stale, mode):
    _ready_closeout(tmp_path, mode)
    policy = load_policy(project_root=tmp_path)
    result = classify_artifact(_artifact(tmp_path, value, stale=stale), policy)
    assert result.state == "malformed"
    assert "failure_disposition" in result.load_error
    assert result.failure_disposition is None
    assert result.failure_disposition_key_present is True
    gate = evaluate_gate(result, policy)
    assert gate.blocked is (mode == "strict")
    if mode == "audit":
        assert any("malformed" in warning for warning in gate.warnings)


@pytest.mark.parametrize("mode", ["permissive", "audit"])
def test_session_end_hook_non_strict_malformed_preserves_mode(tmp_path, mode):
    _ready_closeout(tmp_path, mode)
    _artifact(tmp_path, [])
    result = _close(tmp_path)
    assert result["gate_policy"]["artifact_state"] == "malformed"
    assert result["gate_policy"]["blocked"] is False
    assert result["ok"] is True, result
