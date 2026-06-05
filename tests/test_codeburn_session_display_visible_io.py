from __future__ import annotations

import json
from pathlib import Path

from codeburn.phase1.codeburn_session_display import _parse_codex_jsonl, display


def _write_codex_jsonl(path: Path, *, input_tokens, output_tokens) -> None:
    record = {
        "timestamp": "2026-06-05T00:00:00.000Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            },
        },
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_codex_session_display_hides_visible_io_sum_by_default(tmp_path, capsys, monkeypatch):
    transcript = tmp_path / "codex.jsonl"
    _write_codex_jsonl(transcript, input_tokens=120, output_tokens=30)
    monkeypatch.delenv("CODEBURN_SHOW_VISIBLE_IO_SUM", raising=False)

    summary = _parse_codex_jsonl(transcript)
    display("codex-session", summary, conn=None)

    captured = capsys.readouterr()
    assert summary["visible_io_token_sum"] == 150
    assert "visible_io_token_sum" not in captured.out


def test_codex_session_display_shows_visible_io_sum_when_env_enabled(
    tmp_path,
    capsys,
    monkeypatch,
):
    transcript = tmp_path / "codex.jsonl"
    _write_codex_jsonl(transcript, input_tokens=120, output_tokens=30)
    monkeypatch.setenv("CODEBURN_SHOW_VISIBLE_IO_SUM", "1")

    summary = _parse_codex_jsonl(transcript)
    display("codex-session", summary, conn=None)

    captured = capsys.readouterr()
    assert "visible_io_token_sum: 150 | Class C observation-only" in captured.out
    assert "not billing truth | not efficiency | not cross-provider comparable" in captured.out


def test_codex_session_display_visible_io_sum_keeps_missing_field_null(
    tmp_path,
    capsys,
    monkeypatch,
):
    transcript = tmp_path / "codex.jsonl"
    _write_codex_jsonl(transcript, input_tokens=120, output_tokens=None)
    monkeypatch.setenv("CODEBURN_SHOW_VISIBLE_IO_SUM", "1")

    summary = _parse_codex_jsonl(transcript)
    display("codex-session", summary, conn=None)

    captured = capsys.readouterr()
    assert summary["visible_io_token_sum"] is None
    assert summary["visible_io_missing_field_reason"] == "completion_tokens_missing"
    assert "visible_io_token_sum: NULL | Class C observation-only" in captured.out
    assert "missing_field_policy=null_not_zero reason=completion_tokens_missing" in captured.out
