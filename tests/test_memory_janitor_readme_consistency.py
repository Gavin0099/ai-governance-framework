"""
Keeps the memory_janitor section of governance_tools/README.md in step with
the tool.  The section had drifted: line-only thresholds with wrong numbers, a
CRITICAL row recommending `--execute` (which always fails closed), and an
"archive behaviour" paragraph describing a copy+pointer archive that no longer
runs.
"""

from __future__ import annotations

import re
from pathlib import Path

from governance_tools.memory_janitor import MemoryJanitor as J

README = Path(__file__).resolve().parent.parent / "governance_tools" / "README.md"


def _section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## memory_janitor.py")
    return text[start:text.index("\n---", start)]


def _rows() -> dict[str, tuple[str, str, str]]:
    rows = {}
    for line in _section().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] in {"SAFE", "WARNING", "CRITICAL", "EMERGENCY"}:
            # (lines, chars, action); a table without a chars column yields ""
            rows[cells[0]] = (cells[1], cells[2] if len(cells) >= 4 else "", cells[-1])
    assert rows, "no threshold rows found in the memory_janitor section"
    return rows


def _number(cell: str) -> int:
    return int(re.sub(r"[^\d]", "", cell))


def test_threshold_table_matches_janitor_constants():
    rows = _rows()
    assert set(rows) == {"SAFE", "WARNING", "CRITICAL", "EMERGENCY"}
    expected = {
        "SAFE": (J.HOT_MEMORY_SOFT_LIMIT, J.HOT_MEMORY_SOFT_SIZE_LIMIT, "<"),
        "WARNING": (J.HOT_MEMORY_SOFT_LIMIT, J.HOT_MEMORY_SOFT_SIZE_LIMIT, "≥"),
        "CRITICAL": (J.HOT_MEMORY_HARD_LIMIT, J.HOT_MEMORY_HARD_SIZE_LIMIT, "≥"),
        "EMERGENCY": (J.HOT_MEMORY_CRITICAL, J.HOT_MEMORY_CRITICAL_SIZE_LIMIT, "≥"),
    }
    for status, (lines, chars, op) in expected.items():
        line_cell, char_cell, _ = rows[status]
        assert line_cell.startswith(op) and _number(line_cell) == lines, (status, line_cell)
        assert char_cell.startswith(op) and _number(char_cell) == chars, (status, char_cell)


def test_no_row_recommends_execute():
    for status, (_, _, action) in _rows().items():
        assert "--execute" not in action, f"{status} row recommends --execute: {action}"


def test_archive_behaviour_does_not_describe_a_working_execute_archive():
    section = _section()
    assert "copy+pointer" not in section
    assert "fail closed" in section
    assert "不會自動歸檔或修改" in section
