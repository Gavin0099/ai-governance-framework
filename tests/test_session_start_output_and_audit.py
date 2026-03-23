from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from runtime_hooks.core.payload_audit_logger import log_session_payload, resolve_session_type
from runtime_hooks.core.session_start import _emit_rendered_output


FIXTURE_ROOT = Path("tests/_tmp_session_start_output_and_audit")


def _reset_fixture_dir(name: str) -> Path:
    root = FIXTURE_ROOT / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_resolve_session_type_keeps_onboarding_lane_for_l1() -> None:
    assert resolve_session_type(
        task_level="L1",
        task_type="onboarding",
        risk="medium",
        rules="common",
        task_text="Adopt governance baseline for external repo",
    ) == "onboarding"


def test_log_session_payload_writes_onboarding_jsonl_for_onboarding_task() -> None:
    repo_root = _reset_fixture_dir("onboarding_lane")
    result = {
        "ok": True,
        "task_level": "L1",
        "runtime_contract": {"rules": ["common"]},
        "pre_task_check": {"warnings": [], "errors": []},
        "suggested_rules_preview": [],
        "suggested_agent": None,
    }
    log_file = log_session_payload(
        result,
        project_root=repo_root,
        task_type="onboarding",
        risk="medium",
        rules="common",
        task_text="Adopt governance baseline for external repo",
        format_mode="json",
        rendered_output='{"ok": true}',
    )
    assert log_file.name.startswith("onboarding-")
    payload = json.loads(log_file.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["session_type"] == "onboarding"
    assert payload["task_level"] == "L1"
    assert payload["task_type"] == "onboarding"


def test_emit_rendered_output_falls_back_on_unicode_encode_error() -> None:
    class FailingStdout:
        encoding = "cp950"

        def __init__(self) -> None:
            self.buffer = io.BytesIO()

        def write(self, _text: str) -> int:
            raise UnicodeEncodeError("cp950", "??", 0, 1, "illegal multibyte sequence")

        def flush(self) -> None:
            return

    fake_stdout = FailingStdout()
    with patch("runtime_hooks.core.session_start.sys.stdout", fake_stdout):
        _emit_rendered_output('{"label": "??"}')
    written = fake_stdout.buffer.getvalue().decode("cp950", errors="replace")
    assert '"label": "?' in written or '"label": "?' in written
