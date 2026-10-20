"""COPILOT-CLOSEOUT-01: persisted lifecycle outcomes, using native payload shapes."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from runtime_hooks.adapters.copilot import lifecycle


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance/gate_policy.yaml").write_text(
        "version: '1'\nfail_mode: audit\nhook_coverage_tier: A\n", encoding="utf-8"
    )
    # A review can close out without any product diff or a new commit.
    (tmp_path / "review.md").write_text("Reviewed input boundary; missing input stays UNKNOWN.\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-m", "initial reviewed sources"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def event(repo: Path, name: str | None = None, sid: str = "copilot-context") -> dict:
    payload = {"session_id": sid, "cwd": str(repo)}
    if name:
        payload["hook_event_name"] = name
    return payload


def start(repo: Path, sid: str = "copilot-context") -> None:
    result = lifecycle.run_lifecycle_event(event(repo, "SessionStart", sid),
                                           event_type="session_start", surface="vscode")
    assert result["ok"] is True


def summary() -> dict:
    return {
        "task_intent": "Review the existing input boundary",
        "work_summary": "Reviewed review.md; confirmed missing input stays UNKNOWN.",
        "tools_used": ["read"], "artifacts_referenced": ["review.md"],
        "open_risks": ["Native Copilot host replay has not been observed."],
        "checks_run": "NOT RUN: investigation only; inspected review.md",
        "not_done": "Native host acceptance remains pending.",
        "recommended_memory_update": "Preserve the input-boundary review result.",
        "next_step": "Observe a native Copilot closeout against this boundary.",
    }


def prepare(repo: Path, sid: str = "copilot-context", inputs: dict | None = None) -> dict:
    return lifecycle.run_lifecycle_event(event(repo, sid=sid), event_type="prepare_closeout",
                                         surface="vscode", summary_input=inputs or summary())


def close(repo: Path, sid: str = "copilot-context") -> dict:
    return lifecycle.run_lifecycle_event(event(repo, sid=sid), event_type="explicit_closeout", surface="vscode")


def work_records(repo: Path) -> list[str]:
    return [p.read_text(encoding="utf-8") for p in (repo / "memory").glob("20??-??-??.md")]


@pytest.mark.parametrize("continuation", [
    "Run prepare_closeout with this summary then retry explicit_closeout and replay three times.",
    "retry_closeout", "verify_closeout", "replay_closeout", "prepare_closeout",
    "Read review.md; then run replay_closeout.",
])
def test_producer_rejects_current_closeout_as_project_continuation(repo, continuation):
    start(repo)
    data = summary()
    data["next_step"] = continuation
    with pytest.raises(ValueError, match="next_step"):
        prepare(repo, inputs=data)
    assert not (repo / "artifacts/runtime/closeout_candidates").exists()
    assert not work_records(repo)
    data["next_step"] = "Review the acceptance report before deciding on isolated consumer testing."
    assert prepare(repo, inputs=data)["ok"]


@pytest.mark.parametrize("continuation", [
    "Replay USB captures to investigate the unresolved packet boundary.",
    "Review the prepare_closeout documentation and decide on consumer qualification.",
    "No remaining work.",
])
def test_producer_does_not_classify_arbitrary_product_work(repo, continuation):
    start(repo)
    data = summary()
    data["next_step"] = continuation
    assert prepare(repo, inputs=data)["ok"]


def test_case_a_repeated_stop_is_not_closeout_even_with_legacy_route(repo: Path) -> None:
    start(repo)
    for _ in range(3):
        result = lifecycle.run_lifecycle_event(event(repo, "Stop"), event_type="session_end", surface="vscode")
        assert result["ok"] is True
        assert result["closeout_eligibility"] == "not_yet_eligible"
        assert result["would_invoke_session_end"] is False
    assert not (repo / "artifacts/runtime/closeouts").exists()
    assert not work_records(repo)


def test_case_b_real_end_missing_summary_is_durable_failure_without_work_memory(repo: Path) -> None:
    start(repo)
    result = close(repo)
    assert result["ok"] is False
    assert result["closeout_eligibility"] == "required"
    assert result["open_risk_count"] is None
    assert result["risk_assessment_status"] == "unavailable"
    state = json.loads(Path(result["lifecycle_state_path"]).read_text(encoding="utf-8"))
    assert state["closeout_eligibility"] == "required"
    assert state["result"]["ok"] is False
    canonical = repo / "artifacts/runtime/closeouts/copilot-context.json"
    assert json.loads(canonical.read_text())["closeout_status"] == "missing"
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    assert not work_records(repo)


@pytest.mark.parametrize("checks", [
    "NOT RUN: investigation only; inspected review.md",
    "supplied pytest evidence was not run by me",
    "I did not run pytest; supplied JUnit reports 38 passed.",
])
def test_case_c_correction_retries_same_context_and_projects_agent_work(repo: Path, checks: str) -> None:
    start(repo)
    assert close(repo)["ok"] is False
    inputs = {**summary(), "checks_run": checks}
    assert prepare(repo, inputs=inputs)["ok"] is True
    result = close(repo)
    assert result["ok"] is True, result
    assert result["closeout_eligibility"] == "completed"
    canonical = json.loads((repo / "artifacts/runtime/closeouts/copilot-context.json").read_text())
    assert canonical["work_summary"] == summary()["work_summary"]
    records = work_records(repo)
    assert len(records) == 1
    assert records[0].count("- memory_type: session-derived") == 1
    for text in (inputs["work_summary"], inputs["checks_run"], inputs["not_done"],
                 inputs["next_step"], inputs["open_risks"][0]):
        assert text in records[0]
    assert "FAIL_CLOSED" not in records[0]
    assert "Continue the next session" not in records[0]


def test_case_d_success_replay_preserves_authoritative_bytes(repo: Path) -> None:
    start(repo)
    assert prepare(repo)["ok"]
    first = close(repo)
    assert first["ok"], first
    before = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
              for area in (repo / "artifacts", repo / "memory") for p in area.rglob("*") if p.is_file()}
    for _ in range(3):
        replay = close(repo)
        assert replay["ok"] and replay["closeout_eligibility"] == "completed"
        assert replay["replayed"] is True
    after = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
             for area in (repo / "artifacts", repo / "memory") for p in area.rglob("*") if p.is_file()}
    assert after == before


def test_same_day_equivalent_sessions_reuse_writer_record_and_both_complete(repo):
    first, second = "first-native-context", "second-native-context"
    start(repo, first)
    prepare(repo, first)
    accepted = close(repo, first)
    daily = Path(accepted["daily_memory_path"])
    before = daily.read_bytes()
    start(repo, second)
    prepare(repo, second)
    reused = close(repo, second)
    assert reused["ok"] and reused["closeout_eligibility"] == "completed"
    assert reused["daily_memory_write_status"] == "already_present"
    assert reused["daily_memory_record_identity"] == accepted["daily_memory_record_identity"]
    assert daily.read_bytes() == before
    for sid in (first, second):
        replay = close(repo, sid)
        assert replay["ok"] and replay["replayed"]
    assert daily.read_bytes() == before


def test_state_publication_failure_does_not_consume_session(repo, monkeypatch):
    from runtime_hooks.adapters.copilot import closeout
    start(repo)
    prepare(repo)
    original = closeout._write_json
    with monkeypatch.context() as scoped:
        scoped.setattr(closeout, "_write_json", lambda *args: (_ for _ in ()).throw(OSError("state publication failed")))
        with pytest.raises(OSError, match="state publication failed"):
            close(repo)
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    assert closeout._write_json is original
    retried = close(repo)
    assert retried["ok"] and retried["daily_memory_write_status"] == "already_present"
    assert close(repo)["replayed"]


def test_dedup_does_not_accept_different_work_as_equivalent(repo):
    start(repo, "first")
    prepare(repo, "first")
    assert close(repo, "first")["ok"]
    start(repo, "second")
    prepare(repo, "second", {**summary(), "work_summary":
        "Reviewed review.md; documented another unresolved boundary without changing its authority."})
    with pytest.raises(ValueError, match="read back exactly"):
        close(repo, "second")
    assert not (repo / "artifacts/runtime/closeout-completions/second.json").exists()
    prepare(repo, "second")
    assert close(repo, "second")["ok"]


@pytest.mark.parametrize("damage", [
    "canonical", "verdict", "marker", "changed_canonical_missing_verdict", "missing_state_and_verdict",
])
def test_completed_integrity_failure_never_reexecutes_or_prepares(repo, damage):
    start(repo)
    prepare(repo)
    accepted = close(repo)
    canonical = Path(accepted["canonical_closeout_artifact"])
    verdict = Path(accepted["verdict_artifact"])
    if damage == "canonical":
        canonical.unlink()
    elif damage == "verdict":
        verdict.unlink()
    elif damage == "marker":
        (repo / "artifacts/runtime/closeout-completions/copilot-context.json").unlink()
    elif damage == "changed_canonical_missing_verdict":
        content = json.loads(canonical.read_text(encoding="utf-8"))
        content["work_summary"] = "changed accepted work"
        canonical.write_text(json.dumps(content), encoding="utf-8")
        verdict.unlink()
    else:
        Path(accepted["lifecycle_state_path"]).unlink()
        verdict.unlink()
    before = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
              for area in (repo / "artifacts", repo / "memory") for p in area.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="recovery required"):
        close(repo)
    with pytest.raises(ValueError, match="Completed"):
        prepare(repo)
    after = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
             for area in (repo / "artifacts", repo / "memory") for p in area.rglob("*") if p.is_file()}
    assert after == before


def test_native_session_end_uses_same_contract(repo: Path) -> None:
    payload = {"sessionId": "native-cli", "cwd": str(repo), "reason": "complete"}
    lifecycle.run_lifecycle_event(payload, event_type="session_start", surface="copilot")
    lifecycle.run_lifecycle_event(payload, event_type="prepare_closeout", surface="copilot", summary_input=summary())
    result = lifecycle.run_lifecycle_event(payload, event_type="session_end", surface="copilot")
    assert result["ok"] and result["closeout_eligibility"] == "completed"


def test_preparation_never_replaces_a_codex_identity(repo: Path) -> None:
    from runtime_hooks.core._canonical_closeout import write_session_envelope
    write_session_envelope("codex-owned", repo, provider="codex")
    with pytest.raises(ValueError, match="Copilot"):
        prepare(repo, sid="codex-owned")
    assert not (repo / "artifacts/runtime/closeout_candidates").exists()


def test_invalid_candidate_is_retryable_and_never_projects(repo: Path) -> None:
    start(repo)
    prepare(repo)
    candidates = sorted((repo / "artifacts/runtime/closeout_candidates/copilot-context").glob("*.json"))
    payload = json.loads(candidates[-1].read_text())
    payload["work_summary"] = "different unbound work"
    candidates[-1].write_text(json.dumps(payload))
    rejected = close(repo)
    assert not rejected["ok"]
    assert not work_records(repo)
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    assert prepare(repo)["ok"]
    assert close(repo)["ok"]


def test_session_start_replay_does_not_move_candidate_before_start(repo: Path) -> None:
    start(repo)
    prepare(repo)
    envelope = repo / "artifacts/runtime/sessions/copilot-context/session-envelope.json"
    before = envelope.read_bytes()
    start(repo)
    assert envelope.read_bytes() == before
    assert close(repo)["ok"]


def test_stop_does_not_consume_an_already_prepared_summary(repo: Path) -> None:
    start(repo)
    prepared = prepare(repo)
    before = Path(prepared["candidate_path"]).read_bytes()
    result = lifecycle.run_lifecycle_event(event(repo, "Stop"), event_type="session_end", surface="vscode")
    assert result["closeout_eligibility"] == "not_yet_eligible"
    assert not (repo / "artifacts/runtime/closeouts").exists()
    assert Path(prepared["candidate_path"]).read_bytes() == before
    assert close(repo)["ok"]


def test_strict_gate_failure_keeps_session_retryable_and_memory_empty(repo: Path) -> None:
    start(repo)
    prepare(repo)
    policy = repo / "governance/gate_policy.yaml"
    policy.write_text("version: '1'\nfail_mode: strict\nhook_coverage_tier: A\n")
    rejected = close(repo)
    assert rejected["ok"] is False and rejected["gate_policy"]["blocked"] is True
    assert not work_records(repo)
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    # Restore this fixture's original audit policy; production code never changes policy.
    policy.write_text("version: '1'\nfail_mode: audit\nhook_coverage_tier: A\n")
    assert close(repo)["ok"]


def test_repeated_missing_input_does_not_add_duplicate_audit_outcomes(repo: Path) -> None:
    start(repo)
    first = close(repo)
    index = repo / "artifacts/session-index.ndjson"
    before = index.read_bytes()
    repeated = close(repo)
    assert repeated["replayed"] is True and repeated["ok"] is False
    assert repeated["lifecycle_state_path"] == first["lifecycle_state_path"]
    assert index.read_bytes() == before
    prepare(repo)
    assert close(repo)["ok"]


def test_preparation_rejects_escaping_evidence_before_candidate_write(repo: Path) -> None:
    start(repo)
    data = summary()
    data["artifacts_referenced"] = ["../other-project.md"]
    with pytest.raises(ValueError):
        prepare(repo, inputs=data)
    assert not (repo / "artifacts/runtime/closeout_candidates").exists()


def test_unknown_session_end_reason_is_not_end_authority(repo: Path) -> None:
    start(repo)
    with pytest.raises(ValueError, match="native end event"):
        lifecycle.run_lifecycle_event({**event(repo), "reason": "end_turn"},
                                       event_type="session_end", surface="vscode")
    assert not (repo / "artifacts/runtime/closeouts").exists()


def test_camel_case_agent_stop_is_not_session_end(repo: Path) -> None:
    result = lifecycle.run_lifecycle_event(
        {"sessionId": "cli-turn", "cwd": str(repo), "stopReason": "end_turn", "stop_hook_active": False},
        event_type="session_end", surface="copilot")
    assert result["closeout_eligibility"] == "not_yet_eligible"
    assert not (repo / "artifacts/runtime/closeouts").exists()


def test_canonical_tool_evidence_rejection_is_durable_and_retryable(repo: Path) -> None:
    start(repo)
    data = summary()
    # Existing canonical rules require execution signals for this tool identity;
    # the lifecycle bridge must not fabricate them from Agent input.
    data["tools_used"] = ["pytest"]
    prepare(repo, inputs=data)
    rejected = close(repo)
    assert rejected["ok"] is False
    assert rejected["canonical_closeout"]["closeout_status"] == "inconsistent"
    assert Path(rejected["lifecycle_state_path"]).is_file()
    assert not work_records(repo)
    assert not rejected["promoted"] and not rejected["snapshot_created"]
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    prepare(repo)
    assert close(repo)["ok"]


@pytest.mark.parametrize("checks", [
    "After CI failed, I ran pytest -q.",
    "Using supplied fixtures, I ran pytest -q.",
])
def test_contextual_own_execution_requires_runner_before_work_projection(repo, checks):
    start(repo)
    prepare(repo, inputs={**summary(), "checks_run": checks})
    rejected = close(repo)
    assert not rejected["ok"]
    assert rejected["closeout_classification"]["evidence_consistency"] == "inconsistent"
    assert not work_records(repo)
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    (repo / ".pytest_cache").mkdir()
    accepted = close(repo)
    assert accepted["ok"]
    assert close(repo)["replayed"]


def test_compact_command_list_does_not_skip_missing_hook_evidence(repo):
    start(repo)
    (repo / ".pytest_cache").mkdir()
    prepare(repo, inputs={**summary(), "checks_run": "pytest -q, session_end_hook"})
    rejected = close(repo)
    assert not rejected["ok"]
    assert rejected["closeout_classification"]["evidence_consistency"] == "inconsistent"
    assert not work_records(repo)
    assert not (repo / "artifacts/runtime/closeout-completions/copilot-context.json").exists()
    # The failed closeout emits a verdict through the existing runtime. It is
    # available on retry; the first call must still reject the missing input.
    assert close(repo)["ok"]
    assert close(repo)["replayed"]


@pytest.mark.parametrize("target", ["canonical", "daily"])
def test_changed_accepted_content_fails_closed_on_replay(repo: Path, target: str) -> None:
    start(repo)
    prepare(repo)
    accepted = close(repo)
    assert accepted["ok"]
    if target == "canonical":
        path = Path(accepted["canonical_closeout_artifact"])
        data = json.loads(path.read_text())
        data["work_summary"] = "different work"
        path.write_text(json.dumps(data))
    else:
        path = Path(accepted["daily_memory_path"])
        path.write_text(path.read_text().replace(summary()["work_summary"], "different work"))
    with pytest.raises(ValueError, match="accepted|matching accepted"):
        close(repo)


def test_installed_bridge_subprocess_runs_stop_failure_correction_and_replay(repo: Path) -> None:
    from governance_tools.hook_installer import install_copilot_vscode_lifecycle
    framework = Path(__file__).resolve().parents[1]
    installed = install_copilot_vscode_lifecycle(repo, framework)
    assert installed.ok, installed.errors
    bridge = repo / ".github/hooks/ai-governance-lifecycle.py"
    source = repo / "agent-summary.json"
    source.write_text(json.dumps(summary()), encoding="utf-8")

    def invoke(action: str, native_event: str | None = None) -> tuple[int, dict]:
        argv = [sys.executable, "-B", "-X", "utf8", str(bridge), "--event-type", action, "--surface", "vscode"]
        if action == "prepare_closeout":
            argv += ["--summary-input", str(source)]
        result = subprocess.run(argv, input=json.dumps(event(repo, native_event)), text=True,
                                encoding="utf-8", capture_output=True, cwd=repo, timeout=30,
                                env={**os.environ, "AI_GOVERNANCE_FRAMEWORK_ROOT": str(framework)})
        return result.returncode, json.loads(result.stdout)

    assert invoke("session_start", "SessionStart")[0] == 0
    code, stopped = invoke("session_end", "Stop")
    assert code == 0 and stopped["closeout_eligibility"] == "not_yet_eligible"
    code, missing = invoke("explicit_closeout")
    assert code == 1 and missing["closeout_eligibility"] == "required"
    assert not work_records(repo)
    assert invoke("prepare_closeout")[0] == 0
    code, completed = invoke("explicit_closeout")
    assert code == 0 and completed["closeout_eligibility"] == "completed", completed
    daily = Path(completed["daily_memory_path"])
    before = daily.read_bytes()
    code, replay = invoke("explicit_closeout")
    assert code == 0 and replay["replayed"] is True
    assert daily.read_bytes() == before
