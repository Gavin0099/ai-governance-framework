from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.doc_drift_checker import assess_doc_drift, format_human


FIXTURE_ROOT = Path("tests/_tmp_doc_drift_checker")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_doc_drift_checker_flags_readme_phase_lag_and_undocumented_surface() -> None:
    root = _reset_fixture("phase_lag")
    _write(root / "PLAN.md", "# Plan\n\n## Phase 7\n- goals\n- report\n")
    _write(root / "README.md", "# Readme\n\n## Phase 5\n")
    _write(root / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(root / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(root / "app" / "settings" / "page.tsx", "export default function Settings() {}\n")
    _write(root / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    result = assess_doc_drift(root)

    assert result["ok"] is False
    assert any("README phase 5 trails PLAN phase 7" in item for item in result["warnings"])
    assert any(item["route"] == "/settings" for item in result["undocumented_routes"])
    assert any(item["migration"] == "008_goal_tracking" for item in result["undocumented_migrations"])


def test_doc_drift_checker_passes_when_surface_is_covered() -> None:
    root = _reset_fixture("surface_covered")
    _write(root / "PLAN.md", "# Plan\n\n## Phase 2\n- goals\n- report\n- goal tracking\n")
    _write(root / "README.md", "# Readme\n\n## Phase 2\nSupports goals, report, and goal tracking.\n")
    _write(root / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(root / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(root / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    result = assess_doc_drift(root)

    assert result["ok"] is True
    assert result["warnings"] == []
    assert result["undocumented_routes"] == []
    assert result["undocumented_migrations"] == []


def test_format_human_surfaces_summary_and_findings() -> None:
    root = _reset_fixture("human_output")
    _write(root / "PLAN.md", "# Plan\n\n## Phase 3\n- goals\n")
    _write(root / "README.md", "# Readme\n\n## Phase 1\n")
    _write(root / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(root / "app" / "settings" / "page.tsx", "export default function Settings() {}\n")

    rendered = format_human(assess_doc_drift(root))

    assert "[doc_drift_checker]" in rendered
    assert "warning: phase-sync:README.md" in rendered
    assert "undocumented_route=/settings" in rendered
