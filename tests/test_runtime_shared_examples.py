import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.adapters.claude_code.normalize_event import normalize_event as normalize_claude
from runtime_hooks.adapters.codex.normalize_event import normalize_event as normalize_codex


def test_claude_pre_native_normalizes_to_shared_example():
    native = json.loads(
        Path("runtime_hooks/examples/claude_code/pre_task.native.json").read_text(encoding="utf-8")
    )
    shared = json.loads(
        Path("runtime_hooks/examples/shared/pre_task.shared.json").read_text(encoding="utf-8")
    )
    assert normalize_claude(native, "pre_task") == shared


def test_claude_session_start_native_normalizes_to_shared_example():
    native = json.loads(
        Path("runtime_hooks/examples/claude_code/session_start.native.json").read_text(encoding="utf-8")
    )
    shared = json.loads(
        Path("runtime_hooks/examples/shared/session_start.shared.json").read_text(encoding="utf-8")
    )
    assert normalize_claude(native, "session_start") == shared


def test_codex_post_native_normalizes_to_shared_example():
    native = json.loads(
        Path("runtime_hooks/examples/codex/post_task.native.json").read_text(encoding="utf-8")
    )
    shared = json.loads(
        Path("runtime_hooks/examples/shared/post_task.shared.json").read_text(encoding="utf-8")
    )
    assert normalize_codex(native, "post_task") == shared
