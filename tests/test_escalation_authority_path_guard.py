from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.escalation_authority_path_guard import find_direct_write_violations, run_guard


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_escalation_authority_path_guard" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_guard_current_repo_has_no_direct_write_violations():
    result = run_guard(Path(".").resolve())
    assert result["ok"] is True
    assert result["violation_count"] == 0


def test_guard_detects_direct_write_outside_authority_writer():
    root = _tmp_dir("detect")
    (root / "governance_tools").mkdir(parents=True, exist_ok=True)
    (root / "runtime_hooks").mkdir(parents=True, exist_ok=True)
    (root / "governance_tools" / "escalation_authority_writer.py").write_text(
        "# allowed writer placeholder\n",
        encoding="utf-8",
    )
    bad_file = root / "governance_tools" / "bad_writer.py"
    bad_file.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "p = Path('artifacts/runtime/e1b-phase-b-escalation/authority/esc-1.json')",
                "p.write_text('{}', encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        violations = find_direct_write_violations(root)
        assert len(violations) >= 1
        assert any(item["file"] == "governance_tools/bad_writer.py" for item in violations)
    finally:
        shutil.rmtree(root, ignore_errors=True)
