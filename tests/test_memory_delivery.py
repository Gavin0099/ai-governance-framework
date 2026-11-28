"""Non-LLM T0 acceptance for the Owner's bounded Track C2 delivery contract.

Fixtures use real Git provenance and the existing canonical/R0/R1 producers.
R2 fixtures spell out its existing persisted identity contract; no live platform,
consumer wiring, wall-clock freshness, network or paid model is involved.
"""
from __future__ import annotations

import builtins
import hashlib
import io
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from governance_tools import memory_record
from memory_pipeline.active_task_round_trip import round_trip_active_task
from memory_pipeline.active_task_supersession import supersede_active_task
from runtime_hooks.core import memory_delivery as delivery
from runtime_hooks.core._canonical_closeout import (
    build_canonical_closeout,
    write_canonical_closeout,
    write_session_envelope,
)
from runtime_hooks.core.session_start import build_session_start_context

NOW = datetime(2026, 11, 28, 12, tzinfo=timezone.utc)
SID = "source-session"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=C2 fixture", "-c",
         "user.email=c2@example.invalid", "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=10,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = (tmp_path / "consumer").resolve()
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "T0 fixture")
    (root / "src").mkdir()
    (root / "src/state.py").write_text("state = 'ready'\n", encoding="utf-8")
    return root


def _stamp(path: Path, age_days: float = 0) -> None:
    timestamp = (NOW - timedelta(days=age_days)).timestamp()
    os.utime(path, (timestamp, timestamp))


def _json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    _stamp(path)
    return path


def _envelope(root: Path, sid: str = SID, provider: str = "codex") -> Path:
    result = write_session_envelope(
        sid, root, provider=provider, started_at=(NOW - timedelta(hours=1)).isoformat(),
        bound_consumer_root=root,
    )
    path = Path(result["artifact_path"])
    _stamp(path)
    return path


def _canonical(root: Path, sid: str = SID, summary: str = "State projection is ready.") -> Path:
    _envelope(root, sid)
    # Exercise the actual pure canonical producer rather than inventing valid=true.
    canonical = build_canonical_closeout(
        session_id=sid, closed_at=NOW.isoformat(),
        candidate_payload={"task_intent": "Implement state projection", "work_summary": summary,
                           "tools_used": [], "artifacts_referenced": ["src/state.py"], "open_risks": []},
        existing_artifacts=frozenset({"src/state.py"}), runtime_signals={},
    )
    assert canonical["closeout_status"] == "valid"
    path = write_canonical_closeout(canonical, root)
    _stamp(path)
    return path


def _replace(path: Path, **fields) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(fields)
    _json(path, data)
    return data


def _record(root: Path, version: str) -> dict[str, str]:
    return memory_record.build_session_derived_record(
        what_changed=f"State projection {version} recorded", commit=_git(root, "rev-parse", "HEAD"),
        session_id=f"session-{version}", memory_binding="bound", test_evidence=f"NOT RUN: {version} fixture setup",
        next_step="MUST: do not inject this instruction", plan_reconciliation="not_applicable",
    )


def _projection(record: dict, summary: str) -> bytes:
    return memory_record.render_active_task_projection(record, summary=summary).encode("utf-8")


def _base_input(root: Path, summary: str = "State projection is ready.") -> dict:
    (root / "memory").mkdir(exist_ok=True)
    record = _record(root, "v1")
    observation = {
        "resolution_state": "resolved", "query_class": "current_progress", "logical_name": "active_task",
        "requested_record_identity": record["record_identity"],
        "resolved_record_identity": record["record_identity"],
        "authorized_projection_sha256": hashlib.sha256(_projection(record, summary)).hexdigest(),
    }
    state, projection = round_trip_active_task(
        project_root=root, memory_root=root / "memory", logical_name="active_task", record=record,
        summary=summary, authority_observation=observation,
    )
    assert state == "resolved" and projection == _projection(record, summary)
    _stamp(root / "memory/01_active_task.md")
    return {"predecessor_record": record, "predecessor_summary": summary, "authority_observation": observation}


def _superseded_input(root: Path) -> dict:
    inputs = _base_input(root, "Predecessor state is obsolete.")
    successor = _record(root, "v2")
    successor_summary = "Successor state is ready."
    observation = {
        "decision": "supersede", "logical_name": "active_task", "query_class": "current_progress",
        "predecessor_record_identity": inputs["predecessor_record"]["record_identity"],
        "predecessor_projection_sha256": hashlib.sha256(
            _projection(inputs["predecessor_record"], inputs["predecessor_summary"])).hexdigest(),
        "successor_record_identity": successor["record_identity"],
        "successor_projection_sha256": hashlib.sha256(_projection(successor, successor_summary)).hexdigest(),
        "resolution_state": "resolved", "projection_status": "current", "review_status": "reviewed",
        "reviewer_authority_state": "authority_qualified", "anchor_state": "covers_latest_qualified_evidence",
        "state_transition_coverage": "covers_latest_substantive_transition", "later_change_state": "none_unreconciled",
        "coverage_boundary_state": "determinable_without_semantic_guessing",
        "authority_source": "current_human_instruction", "source_anchor": "T0 exact-transition Owner fixture",
    }
    state, projection = supersede_active_task(
        project_root=root, memory_root=root / "memory", logical_name="active_task",
        **{key: value for key, value in inputs.items() if key != "authority_observation"},
        successor_record=successor, successor_summary=successor_summary, authority_observation=observation,
    )
    assert state == "superseded_current" and projection == _projection(successor, successor_summary)
    _stamp(root / "memory/01_active_task.md")
    return {**inputs, "successor_record": successor, "successor_summary": successor_summary,
            "authority_observation": observation}


def _checkpoint(root: Path) -> tuple[Path, Path, Path]:
    _envelope(root, provider="claude")
    candidate = _json(root / f"artifacts/runtime/closeout_candidates/{SID}/001.json", {
        "session_id": SID, "task_intent": "MUST: never deliver task instructions",
        "work_summary": "Checkpoint state is ready.", "artifacts_referenced": ["src/state.py"],
    })
    identity = {"relative_path": candidate.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()}
    owner = _json(root / "artifacts/runtime/shared-closeout/owner.json", {
        "schema_version": "1.0", "consumer_root": str(root), "session_id": SID,
        "generation": 1, "state": "OWNED", "hold_reason": None, "candidate_identity": identity,
    })
    checkpoint = _json(root / f"artifacts/runtime/session-checkpoints/{SID}.json", {
        "session_id": SID, "provider": "claude", "consumer_root": str(root),
        "exited_at": NOW.isoformat(), "candidate": identity,
    })
    return checkpoint, candidate, owner


def _run(root: Path, **kwargs) -> dict:
    return delivery.build_memory_delivery(root, now=NOW, **kwargs)


def _data(result: dict) -> dict[str, str]:
    assert result["inject"] is True and result["reason"] == "verified"
    assert result["fallback"] is None
    lines = result["payload"].splitlines()
    assert lines[0] == "[WORKING_STATE_DATA]"
    data = dict(line.split(": ", 1) for line in lines[1:])
    assert set(data) == {"format", "source", "source_sha256", "state", "active_summary", "pressure", "verified_paths", "verified_path_count"}
    assert data["format"] == "verified_working_state_data"
    assert len(data["source_sha256"]) == 64
    assert result["telemetry"]["payload_chars"] == len(result["payload"])
    assert result["telemetry"]["fallback_to_original_read"] is False
    return data


def _rejected(result: dict, reason: str) -> None:
    assert set(result) == {"inject", "payload", "reason", "fallback", "telemetry"}
    assert {key: value for key, value in result.items() if key != "telemetry"} == {
        "inject": False, "payload": "", "reason": reason, "fallback": "original_read_flow",
    }
    assert set(result["telemetry"]) == {"elapsed_ms", "files_read_count", "payload_chars", "fallback_to_original_read"}
    assert result["telemetry"]["payload_chars"] == 0
    assert result["telemetry"]["fallback_to_original_read"] is True
    assert result["telemetry"]["elapsed_ms"] >= 0


def test_canonical_producer_to_delivery_is_deterministic_and_read_only(repo: Path) -> None:
    source = _canonical(repo)
    before = {path: path.read_bytes() for path in repo.rglob("*") if path.is_file()}
    first, second = _run(repo), _run(repo)
    assert first["payload"] == second["payload"]
    data = _data(first)
    assert data["source"] == "canonical_closeout" and data["state"] == "valid"
    assert data["pressure"] == "NOT_ASSESSED"  # Active memory was not read.
    assert data["source_sha256"] == hashlib.sha256(before[source]).hexdigest()
    assert json.loads(data["active_summary"]) == f"Session closed at {NOW.isoformat()}."
    assert json.loads(data["verified_paths"]) == []
    assert int(data["verified_path_count"]) == 2
    assert {path: path.read_bytes() for path in repo.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("superseded", [False, True])
def test_real_r0_r1_projection_is_verified_without_writing(repo: Path, superseded: bool) -> None:
    inputs = _superseded_input(repo) if superseded else _base_input(repo)
    path = repo / "memory/01_active_task.md"
    before = path.read_bytes()
    result = _run(repo, active_task=inputs)
    data = _data(result)
    current = "successor" if superseded else "predecessor"
    assert data["source"] == "r0_r1_active_task"
    assert data["state"] == ("superseded_current" if superseded else "base_current")
    assert data["source_sha256"] == hashlib.sha256(
        _projection(inputs[current + "_record"], inputs[current + "_summary"])).hexdigest()
    assert json.loads(data["active_summary"]) == f"Active record bound to commit {_git(repo, 'rev-parse', 'HEAD')}."
    assert "MUST" not in result["payload"] and "obsolete" not in result["payload"]
    assert json.loads(data["verified_paths"]) == ["memory/01_active_task.md"]
    assert path.read_bytes() == before


def test_r2_verified_checkpoint_delivers_bound_candidate_bytes(repo: Path) -> None:
    _checkpoint(repo)
    data = _data(_run(repo))
    assert data["source"] == "r2_checkpoint" and data["state"] == "checkpointed"
    assert json.loads(data["active_summary"]) == f"Checkpoint recorded at {NOW.isoformat()}."


def test_checkpoint_release_generation_is_reused(repo: Path) -> None:
    _, _, owner = _checkpoint(repo)
    record = json.loads(owner.read_text(encoding="utf-8"))
    record["state"] = "RELEASED"
    _json(repo / "artifacts/runtime/shared-closeout/releases/1.json", record)
    owner.unlink()
    assert _data(_run(repo))["source"] == "r2_checkpoint"


def test_source_precedence_is_checkpoint_then_canonical_then_active(repo: Path) -> None:
    inputs = _base_input(repo)
    _canonical(repo, sid="canonical-session")
    assert _data(_run(repo, active_task=inputs))["source"] == "canonical_closeout"
    _checkpoint(repo)
    assert _data(_run(repo, active_task=inputs))["source"] == "r2_checkpoint"


@pytest.mark.parametrize("platform,expected", [
    ("claude_code", {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "payload"}}),
    ("codex", {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "payload"}}),
    ("copilot", {"continue": True, "additionalContext": "payload"}),
    ("vscode_copilot", {"continue": True, "additionalContext": "payload"}),
    ("copilot_cli", {"continue": True, "additionalContext": "payload"}),
    ("antigravity", {"injectSteps": [{"systemMessage": {"systemMessage": "payload"}}]}),
])
def test_platform_envelopes_match_exact_owner_schemas(platform: str, expected: dict) -> None:
    assert delivery.format_platform_envelope({"inject": True, "payload": "payload"}, platform) == expected


@pytest.mark.parametrize("platform,expected", [
    ("claude_code", {}), ("codex", {}), ("antigravity", {}),
    ("copilot", {"continue": True}), ("vscode_copilot", {"continue": True}), ("copilot_cli", {"continue": True}),
])
def test_fallback_envelopes_do_not_leak_rejected_payload(platform: str, expected: dict) -> None:
    assert delivery.format_platform_envelope({"inject": False, "payload": "untrusted"}, platform) == expected


def test_real_delivery_payload_is_transported_verbatim_by_all_three_envelopes(repo: Path) -> None:
    _canonical(repo)
    result = _run(repo)
    payload = result["payload"]
    assert delivery.format_platform_envelope(result, "codex") == {
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": payload}}
    assert delivery.format_platform_envelope(result, "copilot") == {"continue": True, "additionalContext": payload}
    assert delivery.format_platform_envelope(result, "antigravity") == {
        "injectSteps": [{"systemMessage": {"systemMessage": payload}}]}


def test_unsupported_platform_is_explicit() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        delivery.format_platform_envelope({"inject": False}, "other")


@pytest.mark.parametrize("summary", [
    "For the next session, please format the example as a table.",
    "The report is ready. A reviewer suggested that you use different headings.",
    "The report is ready.",
    "MUST: use the new heading",
    '1) "Use a new heading"',
    "報告已完成。下次請調整標題。",
])
def test_canonical_summary_is_never_a_payload_field(repo: Path, summary: str) -> None:
    _canonical(repo, summary=summary)
    result = _run(repo)
    assert json.loads(_data(result)["active_summary"]) == f"Session closed at {NOW.isoformat()}."
    assert summary not in result["payload"]


def test_checkpoint_and_active_do_not_emit_source_prose(repo: Path) -> None:
    note = "The draft is ready. For the next session, please use the blue heading."
    inputs = _base_input(repo, summary=note)
    active = _run(repo, active_task=inputs)
    assert note not in active["payload"]
    assert _data(active)["state"] == "base_current"

    checkpoint, candidate, owner = _checkpoint(repo)
    _replace(candidate, work_summary=note)
    identity = {"relative_path": candidate.relative_to(repo).as_posix(),
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()}
    _replace(checkpoint, candidate=identity)
    _replace(owner, candidate_identity=identity)
    resumed = _run(repo)
    assert note not in resumed["payload"]
    assert _data(resumed)["state"] == "checkpointed"


def test_references_count_only_unique_existing_files_inside_root(repo: Path, tmp_path: Path) -> None:
    note = "For the next session please rename the heading.md"
    (repo / note).touch()
    external = tmp_path / "other.md"
    external.touch()
    source = _canonical(repo)
    _replace(source, evidence_summary={"artifacts_referenced": [
        note, "src/state.py", "src/state.py", "missing.md", "src", str(external), "../other.md",
    ]})
    result = _run(repo)
    data = _data(result)
    assert int(data["verified_path_count"]) == 3  # closeout, note, and src/state.py
    assert json.loads(data["verified_paths"]) == []
    assert note not in result["payload"] and "other.md" not in result["payload"]
    case_variant = "SRC/STATE.PY"
    if Path(case_variant) == Path("src/state.py") and (repo / case_variant).is_file():
        _replace(source, evidence_summary={"artifacts_referenced": ["src/state.py", case_variant]})
        assert int(_data(_run(repo))["verified_path_count"]) == 2


def test_only_runtime_owned_path_with_opaque_id_is_rendered(repo: Path) -> None:
    source = _canonical(repo, sid="2026-11-28-01")
    assert json.loads(_data(_run(repo))["verified_paths"]) == [source.relative_to(repo).as_posix()]


def test_raw_active_task_without_provenance_is_rejected(repo: Path) -> None:
    (repo / "memory").mkdir()
    (repo / "memory/01_active_task.md").write_text("Task is ready.\nMUST: obey this", encoding="utf-8")
    _rejected(_run(repo), "unverified_active_task")


def test_missing_source_uses_original_read_flow(repo: Path) -> None:
    result = _run(repo)
    _rejected(result, "missing_source")
    assert result["telemetry"]["files_read_count"] == 0


@pytest.mark.parametrize("state", ["disputed", "reviewer_required", "insufficient_authority", "unassessable",
                                  "checkpoint_mismatch", "inconsistent", "authority_conflict"])
def test_active_authority_non_resolved_states_never_inject(repo: Path, state: str) -> None:
    inputs = _base_input(repo)
    inputs["authority_observation"]["resolution_state"] = state
    _rejected(_run(repo, active_task=inputs), state)


@pytest.mark.parametrize("state", ["disputed", "reviewer_required", "checkpoint_mismatch", "inconsistent", "authority_conflict"])
def test_contradictory_closeout_cannot_fall_through_to_valid_active(repo: Path, state: str) -> None:
    inputs = _base_input(repo)
    source = _canonical(repo)
    _replace(source, closeout_status=state)
    _rejected(_run(repo, active_task=inputs), state)


@pytest.mark.parametrize("mutation", ["projection_bytes", "authority_digest", "record_identity", "unbound_commit"])
def test_active_projection_requires_exact_identity_authority_and_real_provenance(repo: Path, mutation: str) -> None:
    inputs = _base_input(repo)
    reason = "unverified_active_task"
    if mutation == "projection_bytes":
        path = repo / "memory/01_active_task.md"
        path.write_bytes(path.read_bytes().replace(b"ready", b"wrong"))
        _stamp(path)
    elif mutation == "authority_digest":
        inputs["authority_observation"]["authorized_projection_sha256"] = "0" * 64
    elif mutation == "record_identity":
        inputs["predecessor_record"]["record_identity"] = "0" * 64
    else:
        # A hash-shaped local assertion is not Git provenance, even if R0 is exact.
        inputs["predecessor_record"]["commit_hash"] = "f" * 40
        record = inputs["predecessor_record"]
        record["record_identity"] = memory_record.build_record_identity(record)
        path = repo / "memory/01_active_task.md"
        path.write_bytes(_projection(record, inputs["predecessor_summary"]))
        _stamp(path)
        inputs["authority_observation"].update({
            "requested_record_identity": record["record_identity"],
            "resolved_record_identity": record["record_identity"],
            "authorized_projection_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        reason = "unverified_provenance"
    _rejected(_run(repo, active_task=inputs), reason)


def test_incomplete_supersession_is_not_a_current_state(repo: Path) -> None:
    inputs = _superseded_input(repo)
    path = repo / "memory/01_active_task.md"
    raw = path.read_bytes()
    path.write_bytes(b"\n".join(line for line in raw.split(b"\n") if not line.startswith(b"<!-- memory_runtime")))
    _stamp(path)
    _rejected(_run(repo, active_task=inputs), "unverified_active_task")


@pytest.mark.parametrize("kind", ["canonical", "active", "checkpoint"])
def test_stale_source_file_is_rejected_even_with_valid_provenance(repo: Path, kind: str) -> None:
    kwargs = {}
    if kind == "canonical":
        path = _canonical(repo)
    elif kind == "checkpoint":
        path, _, _ = _checkpoint(repo)
    else:
        kwargs["active_task"] = _base_input(repo)
        path = repo / "memory/01_active_task.md"
    _stamp(path, 31)
    _rejected(_run(repo, **kwargs), "stale_source")


def test_old_closeout_timestamp_is_not_laundered_by_fresh_mtime(repo: Path) -> None:
    source = _canonical(repo)
    _replace(source, closed_at=(NOW - timedelta(days=31)).isoformat())
    _rejected(_run(repo), "stale_source")


def test_freshness_boundary_and_override_are_exact(repo: Path) -> None:
    source = _canonical(repo)
    _stamp(source, 30)
    assert _run(repo)["inject"] is True
    _stamp(source, 30 + 1 / 86400)
    _rejected(_run(repo), "stale_source")
    assert _run(repo, max_age_days=31)["inject"] is True


def test_future_mtime_is_rejected(repo: Path) -> None:
    _stamp(_canonical(repo), -1)
    _rejected(_run(repo), "future_timestamp")


@pytest.mark.parametrize("padding,expected", [("x\n" * 180, "WARNING"), ("x\n" * 200, "CRITICAL"),
                                             ("x" * 12000 + "\n", "EMERGENCY")],
                         ids=["warning", "critical", "emergency"])
def test_existing_janitor_pressure_is_respected(repo: Path, padding: str, expected: str) -> None:
    inputs = _base_input(repo)
    path = repo / "memory/01_active_task.md"
    path.write_bytes(path.read_bytes() + padding.encode())
    _stamp(path)
    result = _run(repo, active_task=inputs)
    if expected == "WARNING":
        assert _data(result)["pressure"] == expected
    else:
        _rejected(result, "memory_pressure_" + expected.lower())


@pytest.mark.parametrize("kind", ["canonical", "checkpoint", "envelope"])
def test_malformed_json_is_rejected(repo: Path, kind: str) -> None:
    if kind == "checkpoint":
        path, _, _ = _checkpoint(repo)
    else:
        source = _canonical(repo)
        path = source if kind == "canonical" else repo / f"artifacts/runtime/sessions/{SID}/session-envelope.json"
    path.write_text("{broken json", encoding="utf-8")
    _stamp(path)
    _rejected(_run(repo), "unverified_session_binding" if kind == "envelope" else "malformed_json")


@pytest.mark.parametrize("field,value,reason", [
    ("closed_at", "invalid", "invalid_timestamp"), ("closed_at", None, "invalid_timestamp"),
    ("session_id", "wrong-session", "session_mismatch"), ("work_summary", [], "unverified_closeout"),
    ("closeout_status", "content_insufficient", "unverified_closeout"),
    ("evidence_summary", [], "invalid_source"),
])
def test_invalid_canonical_fields_fail_closed(repo: Path, field: str, value, reason: str) -> None:
    _replace(_canonical(repo), **{field: value})
    _rejected(_run(repo), reason)


@pytest.mark.parametrize("timestamp", [
    "0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00",
])
@pytest.mark.parametrize("kind", ["canonical", "checkpoint", "envelope"])
def test_timestamp_timezone_overflow_returns_explicit_fallback(repo: Path, timestamp: str, kind: str) -> None:
    if kind == "checkpoint":
        path, _, _ = _checkpoint(repo)
        _replace(path, exited_at=timestamp)
    else:
        source = _canonical(repo)
        if kind == "canonical":
            _replace(source, closed_at=timestamp)
        else:
            _replace(repo / f"artifacts/runtime/sessions/{SID}/session-envelope.json", started_at=timestamp)
    _rejected(_run(repo), "verification_failed")


@pytest.mark.parametrize("now", [0, False, "2026-11-28T12:00:00+00:00"])
def test_invalid_now_type_returns_malformed_input(repo: Path, now: object) -> None:
    _canonical(repo)
    result = delivery.build_memory_delivery(repo, now=now)
    _rejected(result, "malformed_input")
    assert result["telemetry"]["files_read_count"] == 0


def test_source_session_mismatch_is_rejected(repo: Path) -> None:
    _canonical(repo)
    _rejected(_run(repo, session_id="foreign-session"), "session_mismatch")


def test_explicit_source_session_is_enforced_for_active_projection(repo: Path) -> None:
    inputs = _base_input(repo)
    _rejected(_run(repo, active_task=inputs, session_id="foreign-session"), "session_mismatch")
    assert _run(repo, active_task=inputs, session_id="session-v1")["inject"] is True


def test_wrong_root_envelope_is_rejected(repo: Path, tmp_path: Path) -> None:
    _canonical(repo)
    path = repo / f"artifacts/runtime/sessions/{SID}/session-envelope.json"
    _replace(path, repo_binding={"source": "codex_session_start", "consumer_root": str(tmp_path)})
    _rejected(_run(repo), "unverified_session_binding")


def test_legacy_unbound_envelope_is_not_verified(repo: Path) -> None:
    _canonical(repo)
    path = repo / f"artifacts/runtime/sessions/{SID}/session-envelope.json"
    _replace(path, schema_version="1.0")
    _rejected(_run(repo), "unverified_session_binding")


def test_workspace_and_actual_git_root_must_match(repo: Path, tmp_path: Path) -> None:
    _canonical(repo)
    _rejected(_run(repo, workspace_root=tmp_path.resolve()), "workspace_mismatch")
    _rejected(_run(repo / "src"), "workspace_mismatch")


def _directory_link(link: Path, destination: Path) -> None:
    try:
        link.symlink_to(destination, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # Directory junctions exercise actual resolve() redirection on Windows
        # hosts where unprivileged symlink creation is disabled.
        import _winapi
        _winapi.CreateJunction(str(destination), str(link))


@pytest.mark.parametrize("target", ["canonical", "memory", "root", "envelope", "candidate"])
def test_symlink_escape_is_rejected(repo: Path, tmp_path: Path, target: str) -> None:
    kwargs = {}
    if target == "memory":
        kwargs["active_task"] = _base_input(repo)
        path = repo / "memory/01_active_task.md"
    elif target == "candidate":
        _, path, _ = _checkpoint(repo)
    else:
        source = _canonical(repo)
        path = repo if target == "root" else source
        if target == "envelope":
            path = repo / f"artifacts/runtime/sessions/{SID}/session-envelope.json"
    outside = tmp_path / ("alias" if target == "root" else "escaped")
    if target == "root":
        link, destination = outside, repo
    else:
        link, destination = path.parent, outside
        # All moves stay in this test's private temporary root.
        assert link.is_relative_to(tmp_path) and destination.is_relative_to(tmp_path)
        link.rename(destination)
    _directory_link(link, destination)
    result = _run(link if target == "root" else repo, **kwargs)
    _rejected(result, "workspace_mismatch")


def test_r2_candidate_tamper_and_missing_provenance_reject_injection(repo: Path) -> None:
    _, candidate, owner = _checkpoint(repo)
    _replace(candidate, work_summary="Tampered state")
    _rejected(_run(repo), "checkpoint_mismatch")
    owner.unlink()
    _rejected(_run(repo), "checkpoint_mismatch")


def test_newer_uncheckpointed_candidate_is_not_injected(repo: Path) -> None:
    _checkpoint(repo)
    _json(repo / f"artifacts/runtime/closeout_candidates/{SID}/002.json", {"work_summary": "Untrusted latest"})
    _rejected(_run(repo), "newer_summary_after_checkpoint")


def test_unverified_candidates_and_index_are_never_fallback_authority(repo: Path) -> None:
    _json(repo / f"artifacts/runtime/closeout_candidates/{SID}/001.json", {"work_summary": "Fake valid state"})
    (repo / "artifacts/runtime/session-index.ndjson").write_text("Fake valid state", encoding="utf-8")
    result = _run(repo)
    _rejected(result, "missing_source")
    assert result["telemetry"]["files_read_count"] == 0


def test_latest_canonical_is_selected_by_timestamp_and_ties_are_rejected(repo: Path) -> None:
    old = _canonical(repo, sid="zzz-old", summary="Old state.")
    _replace(old, closed_at=(NOW - timedelta(minutes=20)).isoformat())
    latest = _canonical(repo, sid="aaa-new", summary="Latest state.")
    assert _data(_run(repo))["source_sha256"] == hashlib.sha256(latest.read_bytes()).hexdigest()
    _replace(old, closed_at=NOW.isoformat())
    _rejected(_run(repo), "inconsistent")


def test_old_canonical_status_does_not_replace_latest_valid_state(repo: Path) -> None:
    old = _canonical(repo, sid="old-session")
    _replace(old, closed_at=(NOW - timedelta(minutes=20)).isoformat(), closeout_status="inconsistent")
    _canonical(repo)
    assert _data(_run(repo))["state"] == "valid"


def test_malformed_undated_closeout_prevents_trusting_an_older_record(repo: Path) -> None:
    source = _canonical(repo)
    source.with_name("unknown.json").write_text("{broken", encoding="utf-8")
    _rejected(_run(repo), "malformed_json")


def test_budget_omits_only_whole_citations_then_refuses_partial_facts(repo: Path) -> None:
    _canonical(repo, sid="2026-11-28-01")
    full = _run(repo)
    assert len(full["payload"]) <= 600
    assert _run(repo, max_chars=len(full["payload"]))["payload"] == full["payload"]
    smaller = _run(repo, max_chars=len(full["payload"]) - 1)
    fields = _data(smaller)
    assert json.loads(fields["verified_paths"]) == []
    assert fields["active_summary"] == _data(full)["active_summary"]
    assert _run(repo, max_chars=len(smaller["payload"]))["payload"] == smaller["payload"]
    _rejected(_run(repo, max_chars=len(smaller["payload"]) - 1), "payload_budget_exceeded")


@pytest.mark.parametrize("kwargs", [{"max_chars": 0}, {"max_chars": True}, {"max_chars": "600"},
                                   {"max_age_days": -1}, {"max_age_days": True}])
def test_invalid_configuration_returns_explicit_fallback(repo: Path, kwargs: dict) -> None:
    _rejected(_run(repo, **kwargs), "invalid_configuration")


def test_metadata_candidate_count_is_bounded_without_sampling_old_state(repo: Path) -> None:
    source = _canonical(repo)
    for number in range(delivery.MAX_SOURCE_FILES):
        _json(source.with_name(f"extra-{number}.json"), {})
    result = _run(repo)
    _rejected(result, "source_budget_exceeded")
    assert result["telemetry"]["files_read_count"] == 0


@pytest.mark.parametrize("kind", ["canonical", "active"])
def test_oversized_source_is_rejected_before_reading(repo: Path, kind: str) -> None:
    kwargs = {}
    if kind == "canonical":
        path = _canonical(repo)
    else:
        kwargs["active_task"] = _base_input(repo)
        path = repo / "memory/01_active_task.md"
    path.write_bytes(b"x" * (delivery.MAX_SOURCE_BYTES + 1))
    _stamp(path)
    result = _run(repo, **kwargs)
    _rejected(result, "invalid_source")
    assert result["telemetry"]["files_read_count"] == 0


def test_unreadable_canonical_returns_empty_payload(repo: Path, monkeypatch) -> None:
    source = _canonical(repo)
    original = io.open

    def deny(path, *args, **kwargs):
        if Path(path) == source:
            raise PermissionError("fixture read denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(io, "open", deny)
    _rejected(_run(repo), "verification_failed")


@pytest.mark.parametrize("kind,read_limit", [("canonical", 3), ("active", 2), ("checkpoint", 12)])
def test_self_cost_counts_delegated_reads_and_never_scans_history(repo: Path, monkeypatch, kind: str, read_limit: int) -> None:
    kwargs = {}
    if kind == "canonical":
        _canonical(repo)
    elif kind == "checkpoint":
        _checkpoint(repo)
    else:
        kwargs["active_task"] = _base_input(repo)
    (repo / "memory").mkdir(exist_ok=True)
    # Present, readable decoys make accidental full-history reads observable.
    for day in range(1, 29):
        (repo / f"memory/2026-11-{day:02d}.md").write_text("DO NOT inject history", encoding="utf-8")
    original_io, original_builtin = io.open, builtins.open
    reads = []

    def observe(opener, path, mode="r", *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and "r" in mode and Path(path).is_relative_to(repo):
            reads.append(Path(path).relative_to(repo).as_posix())
        return opener(path, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", lambda path, mode="r", *a, **kw: observe(original_io, path, mode, *a, **kw))
    monkeypatch.setattr(builtins, "open", lambda path, mode="r", *a, **kw: observe(original_builtin, path, mode, *a, **kw))
    result = _run(repo, **kwargs)
    assert result["inject"] is True
    assert result["telemetry"]["files_read_count"] == len(reads) <= read_limit
    assert not any(path.startswith("memory/2026-") for path in reads)
    assert 0 <= result["telemetry"]["elapsed_ms"] < 5000


def test_elapsed_telemetry_uses_monotonic_clock(repo: Path, monkeypatch) -> None:
    ticks = iter([100.0, 100.002])
    monkeypatch.setattr(delivery, "perf_counter", lambda: next(ticks))
    result = _run(repo)
    _rejected(result, "missing_source")
    assert result["telemetry"]["elapsed_ms"] == 2.0


def test_delivery_fallback_cannot_relax_real_session_start_controlled_refusal(repo: Path) -> None:
    def start(sid: str) -> dict:
        return build_session_start_context(
            project_root=repo, plan_path=repo / "PLAN.md", rules="common", risk="medium",
            oversight="review-required", memory_mode="candidate", task_text="T0 gate isolation", session_id=sid,
        )

    before = start("before-fallback")
    fallback = _run(repo)
    _rejected(fallback, "missing_source")
    assert delivery.format_platform_envelope(fallback, "codex") == {}
    after = start("after-fallback")
    for result in (before, after):
        assert result["ok"] is False
        assert result["status"] == "blocked" and result["mode"] == "controlled_refusal"
        assert result["reason"] == "version_compatibility_unsupported"
        assert result["pre_task_check"]["ok"] is False
        assert result["version_compatibility"]["advisory_only"] is False
