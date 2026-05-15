import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.session_end_hook import run_session_end_hook


_FIXTURE_ROOT = Path(__file__).parent / "_tmp_session_end_hook_closeout_bridge"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_session_end_hook_writes_non_missing_canonical_closeout_when_closeout_present() -> None:
    repo = _reset_fixture("bridge_valid_closeout")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    touched = repo / "src" / "main.cpp"
    touched.parent.mkdir(parents=True, exist_ok=True)
    touched.write_text("int main(){return 0;}\n", encoding="utf-8")

    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: canonical closeout bridge validation",
                "WORK_COMPLETED: updated src/main.cpp and validated closeout bridge",
                "FILES_TOUCHED: src/main.cpp",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: one week observation window",
                "RECOMMENDED_MEMORY_UPDATE: keep closeout generation enabled",
                "TASK_ID: bridge-test",
                "RUN_ID: run-001",
                "COMMIT_HASH: abc1234",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(repo)
    assert result["closeout_status"] == "valid"

    canonical_path = repo / "artifacts" / "runtime" / "closeouts" / f"{result['session_id']}.json"
    assert canonical_path.exists()
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    assert canonical["closeout_status"] == "valid"
    assert canonical["task_intent"] == "canonical closeout bridge validation"


def test_session_end_hook_accepts_closeout_metadata_lines_when_closeout_present() -> None:
    repo = _reset_fixture("bridge_metadata_lines")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    touched = repo / "src" / "main.cpp"
    touched.parent.mkdir(parents=True, exist_ok=True)
    touched.write_text("int main(){return 0;}\n", encoding="utf-8")

    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: metadata bridge validation",
                "WORK_COMPLETED: validated extra run metadata lines in src/main.cpp",
                "FILES_TOUCHED: src/main.cpp",
                "CHECKS_RUN: session_end_hook; npm",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: NO_UPDATE",
                "TASK_ID: metadata-test",
                "RUN_ID: run-002",
                "COMMIT_HASH: def5678",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(repo)
    assert result["closeout_status"] == "valid"
    assert result["per_layer_results"]["missing_fields"] == []
