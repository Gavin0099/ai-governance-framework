from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime_hooks.adapters.copilot import lifecycle


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_vscode_stop_normalizes_snake_case_payload(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")

    result = lifecycle.normalize_lifecycle_payload(
        {
            "hook_event_name": "Stop",
            "session_id": "vscode-session-1",
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
            "stop_hook_active": False,
        },
        event_type="session_end",
        surface="vscode",
    )

    assert result["session_id"] == "vscode-session-1"
    assert result["project_root"] == tmp_path.resolve()
    assert result["transcript_path"] == transcript.resolve()
    assert result["provider"] == "github-copilot-vscode"


def test_copilot_session_end_normalizes_camel_case_payload(tmp_path: Path) -> None:
    result = lifecycle.normalize_lifecycle_payload(
        {
            "sessionId": "copilot-session-1",
            "cwd": str(tmp_path),
            "reason": "complete",
        },
        event_type="session_end",
        surface="copilot",
    )

    assert result["session_id"] == "copilot-session-1"
    assert result["project_root"] == tmp_path.resolve()
    assert result["reason"] == "complete"
    assert result["provider"] == "github-copilot"


@pytest.mark.parametrize(
    "session_id",
    [
        ".",
        "..",
        "../outside",
        r"..\outside",
        "/absolute",
        r"C:\absolute",
        "contains/slash",
        "contains\\backslash",
        "control\ncharacter",
        "x" * 129,
    ],
)
def test_unsafe_session_id_is_rejected_before_any_write(
    tmp_path: Path,
    session_id: str,
) -> None:
    with pytest.raises(ValueError, match="safe path segment"):
        lifecycle.normalize_lifecycle_payload(
            {"sessionId": session_id, "cwd": str(tmp_path)},
            event_type="session_start",
            surface="auto",
        )


def test_auto_surface_uses_payload_field_convention(tmp_path: Path) -> None:
    vscode = lifecycle.normalize_lifecycle_payload(
        {"session_id": "vscode-auto-1", "cwd": str(tmp_path)},
        event_type="session_start",
        surface="auto",
    )
    copilot = lifecycle.normalize_lifecycle_payload(
        {"sessionId": "copilot-auto-1", "cwd": str(tmp_path)},
        event_type="session_start",
        surface="auto",
    )

    assert vscode["surface"] == "vscode"
    assert vscode["provider"] == "github-copilot-vscode"
    assert copilot["surface"] == "copilot"
    assert copilot["provider"] == "github-copilot"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"cwd": "."}, "session_id/sessionId"),
        ({"session_id": "session-1"}, "missing cwd"),
    ],
)
def test_lifecycle_payload_missing_identity_or_cwd_fails_closed(
    payload: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        lifecycle.normalize_lifecycle_payload(
            payload,
            event_type="session_end",
            surface="vscode",
        )


def test_session_start_writes_envelope_with_native_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    monkeypatch.setattr(lifecycle, "resolve_framework_root", lambda _root: REPO_ROOT)

    def _capture(session_id: str, project_root: Path, *, provider: str) -> dict[str, str]:
        observed.update(
            session_id=session_id,
            project_root=project_root,
            provider=provider,
        )
        return {
            "artifact_path": "artifacts/runtime/sessions/vscode-session-2/session-envelope.json"
        }

    monkeypatch.setattr(lifecycle, "_write_session_envelope", _capture)

    result = lifecycle.run_lifecycle_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "vscode-session-2",
            "cwd": str(tmp_path),
        },
        event_type="session_start",
        surface="vscode",
    )

    assert result["ok"] is True
    assert result["status"] == "session_envelope_written"
    assert (
        result["session_envelope_path"]
        == "artifacts/runtime/sessions/vscode-session-2/session-envelope.json"
    )
    assert observed == {
        "session_id": "vscode-session-2",
        "project_root": tmp_path.resolve(),
        "provider": "github-copilot-vscode",
    }


def test_session_end_invokes_canonical_hook_with_same_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(lifecycle, "resolve_framework_root", lambda _root: REPO_ROOT)

    def _capture(
        project_root: Path,
        *,
        session_id: str,
        transcript_path: Path | None,
    ) -> dict[str, object]:
        observed.update(
            project_root=project_root,
            session_id=session_id,
            transcript_path=transcript_path,
        )
        return {
            "ok": True,
            "closeout_status": "valid",
            "decision": "DO_NOT_PROMOTE",
            "session_binding": {"status": "valid"},
        }

    monkeypatch.setattr(lifecycle, "_run_session_end", _capture)

    result = lifecycle.run_lifecycle_event(
        {
            "hook_event_name": "Stop",
            "session_id": "vscode-session-3",
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        },
        event_type="session_end",
        surface="vscode",
    )

    assert result["ok"] is True
    assert result["status"] == "session_end_invoked"
    assert result["session_binding_status"] == "valid"
    assert observed == {
        "project_root": tmp_path.resolve(),
        "session_id": "vscode-session-3",
        "transcript_path": transcript.resolve(),
    }


def test_dry_run_resolves_hub_topology_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle, "resolve_framework_root", lambda _root: REPO_ROOT)
    monkeypatch.setattr(
        lifecycle,
        "_write_session_envelope",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not write an envelope"),
    )
    monkeypatch.setattr(
        lifecycle,
        "_run_session_end",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not invoke session_end"),
    )

    result = lifecycle.run_lifecycle_event(
        {
            "sessionId": "hub-consumer-smoke",
            "cwd": str(tmp_path),
            "reason": "complete",
        },
        event_type="session_end",
        surface="copilot",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["would_invoke_session_end"] is True
    assert result["would_write_session_envelope"] is False


def test_hook_templates_use_independent_surface_event_names() -> None:
    vscode = json.loads(
        (REPO_ROOT / "governance" / "copilot-hooks-vscode-template.json").read_text(
            encoding="utf-8"
        )
    )
    copilot = json.loads(
        (
            REPO_ROOT / "governance" / "copilot-hooks-session-end-template.json"
        ).read_text(encoding="utf-8")
    )

    # VS Code loads both files and normalizes the Copilot config's lowerCamelCase
    # names, so `sessionStart` is already VS Code's only start handler. The VS
    # Code config must therefore declare `Stop` alone — adding `SessionStart`
    # would register a second handler for the same boundary.
    assert set(vscode["hooks"]) == {"Stop"}
    assert set(copilot["hooks"]) == {"sessionStart", "sessionEnd"}
    normalized_copilot = {name[0].upper() + name[1:] for name in copilot["hooks"]}
    assert not set(vscode["hooks"]) & normalized_copilot
    for payload in (vscode, copilot):
        for entries in payload["hooks"].values():
            assert "ai-governance-lifecycle.py" in entries[0]["command"]


def test_cross_loader_event_normalization_executes_each_boundary_once() -> None:
    vscode = json.loads(
        (REPO_ROOT / "governance" / "copilot-hooks-vscode-template.json").read_text(
            encoding="utf-8"
        )
    )
    copilot = json.loads(
        (
            REPO_ROOT / "governance" / "copilot-hooks-session-end-template.json"
        ).read_text(encoding="utf-8")
    )
    combined = {**vscode["hooks"], **copilot["hooks"]}

    vscode_normalized = {
        ("SessionStart" if name == "sessionStart" else "SessionEnd" if name == "sessionEnd" else name):
        entries
        for name, entries in combined.items()
    }
    assert len(vscode_normalized["SessionStart"]) == 1
    assert len(vscode_normalized["Stop"]) == 1
    assert "session_start" in vscode_normalized["SessionStart"][0]["command"]
    assert "session_end" in vscode_normalized["Stop"][0]["command"]

    assert len(combined["sessionStart"]) == 1
    assert len(combined["sessionEnd"]) == 1
