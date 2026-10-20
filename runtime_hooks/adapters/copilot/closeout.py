"""Copilot v1.0 preparation and serialized closeout; never infer agent work.

Private session text avoids borrowing the Codex shared-text ownership contract.
The existing exclusion lock and canonical validator remain the execution boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_tools.prepare_closeout_candidate import render_inputs, _single_line
from governance_tools.shared_closeout_ownership import execution_exclusion, _path
from runtime_hooks.core._canonical_closeout import (
    assess_session_closeout_binding, build_candidate_artifact, read_session_envelope,
)


def validate_session(root: Path, sid: str, provider: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,127}", sid):
        raise ValueError("Copilot session must be a safe native identity")
    envelope = read_session_envelope(sid, root)
    if (provider not in {"github-copilot", "github-copilot-vscode"}
            or envelope is None or envelope.get("schema_version") != "1.0"
            or envelope.get("provider") != provider):
        raise ValueError("Copilot preparation requires its existing native v1.0 session identity")
    return envelope


def _session_path(root: Path, sid: str, name: str) -> Path:
    path = root / "artifacts/runtime/sessions" / sid / name
    if not path.resolve().is_relative_to(root / "artifacts/runtime/sessions" / sid):
        raise ValueError("Copilot session path escapes its native session")
    return path


def _write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_next_step(next_step: str) -> None:
    # This producer closes the current context. Its own preparation/retry/replay
    # plumbing cannot be the project continuation emitted after that closeout.
    # Match explicit action clauses, not mentions in documentation or arbitrary
    # product verbs (for example replaying a USB capture).
    if re.search(
        r"(?:^|[;,]|\b(?:then|and)\s+)\s*"
        r"(?:(?:run|invoke|execute|call|repeat)\s+)?"
        r"(?:prepare_closeout|retry_closeout|verify_closeout|replay_closeout|explicit_closeout)\b",
        next_step, re.IGNORECASE,
    ):
        raise ValueError(
            "next_step must name remaining work after this closeout, not its own "
            "prepare/retry/verify/replay operations; the Agent must correct the continuation"
        )


def prepare(root: Path, sid: str, provider: str, inputs: dict[str, Any]) -> dict[str, Any]:
    fields = {"task_intent", "work_summary", "tools_used", "artifacts_referenced", "open_risks",
              "checks_run", "not_done", "recommended_memory_update", "next_step"}
    if not isinstance(inputs, dict) or set(inputs) != fields:
        raise ValueError("Copilot summary requires agent work, checks, unfinished work, risks and next_step")
    next_step = _single_line(inputs["next_step"], "next_step")
    _validate_next_step(next_step)
    candidate, text = render_inputs({k: v for k, v in inputs.items() if k != "next_step"})
    for relative in candidate["artifacts_referenced"]:
        _path(root, relative)
    candidate.update({k: inputs[k] for k in ("checks_run", "not_done", "next_step")})
    text += ("NEXT_STEP: " + next_step + "\n").encode("utf-8")
    with execution_exclusion(root):
        validate_session(root, sid, provider)
        binding = assess_session_closeout_binding(sid, root, None)
        if binding["status"] == "already_consumed":
            raise ValueError("Completed Copilot session cannot prepare another closeout")
        now = datetime.now(timezone.utc)
        relative, payload, encoded = build_candidate_artifact(
            sid, candidate, timestamp=now.strftime("%Y%m%dT%H%M%S%fZ"), generated_at=now.isoformat())
        if assess_session_closeout_binding(sid, root, payload)["status"] != "valid":
            raise ValueError("Copilot candidate does not bind to its existing native session")
        candidate_path = root / relative
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        with candidate_path.open("xb") as stream:
            stream.write(encoded)
        text_path = _session_path(root, sid, "session-closeout.txt")
        temporary = text_path.with_suffix(".pending")
        temporary.write_bytes(text)
        temporary.replace(text_path)
        return {"ok": True, "status": "summary_prepared", "session_id": sid,
                "closeout_eligibility": "required", "candidate_path": str(candidate_path),
                "closeout_text_path": str(text_path)}


def run(root: Path, sid: str, provider: str, transcript_path: Path | None) -> dict[str, Any]:
    from governance_tools.session_end_hook import run_session_end_hook
    from governance_tools.memory_record import daily_memory_contains_record_identity, render_session_derived_entry

    with execution_exclusion(root):
        validate_session(root, sid, provider)
        state_path = _session_path(root, sid, "copilot-closeout-state.json")
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        candidates = sorted((root / "artifacts/runtime/closeout_candidates" / sid).glob("*.json"))
        transport = _session_path(root, sid, "session-closeout.txt")
        input_identity = hashlib.sha256(
            (candidates[-1].read_bytes() if candidates else b"NO_CANDIDATE") + b"\0"
            + (transport.read_bytes() if transport.exists() else b"NO_TEXT")
        ).hexdigest()
        binding = assess_session_closeout_binding(sid, root, None)
        if binding["status"] == "already_consumed":
            canonical_path = root / "artifacts/runtime/closeouts" / f"{sid}.json"
            if (state.get("closeout_eligibility") != "completed"
                    or not state.get("result", {}).get("ok")
                    or hashlib.sha256(canonical_path.read_bytes()).hexdigest() != state.get("canonical_sha256")):
                raise ValueError("Copilot completion has no matching accepted lifecycle result; recovery required")
            previous = state["result"]
            daily_path = Path(previous["daily_memory_path"])
            if not daily_path.resolve().is_relative_to(root / "memory"):
                raise ValueError("Copilot completed work memory is outside this repository")
            if not daily_memory_contains_record_identity(
                    daily_path=daily_path,
                    record_identity=previous["daily_memory_record_identity"]):
                raise ValueError("Copilot completed work memory is no longer verifiable")
            if (not state.get("daily_memory_entry")
                    or state["daily_memory_entry"] not in daily_path.read_text(encoding="utf-8")):
                raise ValueError("Copilot accepted work memory content has changed")
            return {**previous, "replayed": True}
        if (state.get("input_identity") == input_identity
                and state.get("result", {}).get("closeout_status") == "closeout_missing"):
            return {**state["result"], "replayed": True}
        result = run_session_end_hook(root, hook_session_id=sid, transcript_path=transcript_path,
                                      copilot_closeout=True)
        # Tier B/C advisory policies cannot turn a missing required summary into success.
        success = bool(result.get("ok") and result.get("closeout_status") == "valid"
                       and result.get("canonical_closeout", {}).get("closeout_status") == "valid")
        risk_available = (result.get("closeout_status") == "valid"
                          and result.get("canonical_closeout", {}).get("closeout_status") == "valid")
        result.update(ok=success, closeout_eligibility="completed" if success else "required",
                      replayed=False, lifecycle_state_path=str(state_path),
                      open_risk_count=(len(result["canonical_closeout"]["open_risks"]) if risk_available else None),
                      risk_assessment_status="agent_declared" if risk_available else "unavailable")
        state = {"session_id": sid, "input_identity": input_identity,
                 "closeout_eligibility": result["closeout_eligibility"], "result": result}
        if success:
            canonical_path = Path(result["canonical_closeout_artifact"])
            state["canonical_sha256"] = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
            runtime_summary = json.loads((root / "artifacts/runtime/summaries" / f"{sid}.json").read_text(encoding="utf-8"))
            entry = render_session_derived_entry(runtime_summary["daily_memory_record"])
            if entry not in Path(result["daily_memory_path"]).read_text(encoding="utf-8"):
                raise ValueError("Copilot work memory could not be read back exactly")
            state["daily_memory_entry"] = entry
        _write_json(state_path, state)
        return result
