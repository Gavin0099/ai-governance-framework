"""Regression coverage for the summary's ordered pending-work view."""
from pathlib import Path

from scripts.plan_summary import build_plan_summary


def _summary(tmp_path: Path, text: str) -> dict:
    plan = tmp_path / "PLAN.md"
    plan.write_text(text, encoding="utf-8")
    return build_plan_summary(plan, tmp_path)


def test_pending_work_counts_open_items_by_explicit_priority(tmp_path: Path) -> None:
    summary = _summary(tmp_path, """# PLAN
## Pending Work - Ordered
P0 - completed repair:
- [x] Closed.
P1-B - pending maintenance:
- [ ] First action.
  More context mentioning P2 without changing the priority.
  - [ ] Second action.
P2 - evidence disposition:
- [ ] Retain an unresolved item.
P3 - separate program:
- [ ] Outside the reported priority groups.
## Historical Milestone Index
- [ ] Outside the backlog section.
""")
    assert summary["backlog_open"] == {"P0": 0, "P1": 2, "P2": 1}


def test_pending_work_requires_a_priority_label(tmp_path: Path) -> None:
    summary = _summary(tmp_path, """## Pending Work - Ordered
- [ ] Unclassified item.
This prose mentions P1.
- [ ] Still unclassified.
P2-E - release surface:
- [x] Closed.
""")
    assert summary["backlog_open"] == {"P0": 0, "P1": 0, "P2": 0}


def test_legacy_backlog_remains_the_preferred_source(tmp_path: Path) -> None:
    summary = _summary(tmp_path, """## Backlog
No open items.
## Pending Work - Ordered
P1 - alternate view:
- [ ] Do not add both views together.
""")
    assert summary["backlog_open"] == {"P0": 0, "P1": 0, "P2": 0}


def test_missing_backlog_preserves_existing_empty_counts(tmp_path: Path) -> None:
    summary = _summary(tmp_path, "## Current Sprint\n- [ ] Sprint action.\n")
    assert summary["backlog_open"] == {"P0": 0, "P1": 0, "P2": 0}
