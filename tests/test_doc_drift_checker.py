from __future__ import annotations

from pathlib import Path

from governance_tools.doc_drift_checker import assess_doc_drift, format_human


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_doc_drift_checker_flags_readme_phase_lag_and_undocumented_surface(tmp_path: Path) -> None:
    _write(tmp_path / "PLAN.md", "# Plan\n\n## Phase 7\n- goals\n- report\n")
    _write(tmp_path / "README.md", "# Readme\n\n## Phase 5\n")
    _write(tmp_path / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(tmp_path / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(tmp_path / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    result = assess_doc_drift(tmp_path)

    assert result["ok"] is False
    assert any("README phase 5 trails PLAN phase 7" in item for item in result["warnings"])
    assert any(item["route"] == "/report" for item in result["undocumented_routes"])
    assert any(item["migration"] == "008_goal_tracking" for item in result["undocumented_migrations"])


def test_doc_drift_checker_passes_when_surface_is_covered(tmp_path: Path) -> None:
    _write(tmp_path / "PLAN.md", "# Plan\n\n## Phase 2\n- goals\n- report\n- goal tracking\n")
    _write(tmp_path / "README.md", "# Readme\n\n## Phase 2\nSupports goals, report, and goal tracking.\n")
    _write(tmp_path / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(tmp_path / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(tmp_path / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    result = assess_doc_drift(tmp_path)

    assert result["ok"] is True
    assert result["warnings"] == []
    assert result["undocumented_routes"] == []
    assert result["undocumented_migrations"] == []


def test_format_human_surfaces_summary_and_findings(tmp_path: Path) -> None:
    _write(tmp_path / "PLAN.md", "# Plan\n\n## Phase 3\n- goals\n")
    _write(tmp_path / "README.md", "# Readme\n\n## Phase 1\n")
    _write(tmp_path / "app" / "goals" / "page.tsx", "export default function Goals() {}")

    rendered = format_human(assess_doc_drift(tmp_path))

    assert "[doc_drift_checker]" in rendered
    assert "warning: phase-sync:README.md" in rendered
    assert "undocumented_route=/goals" in rendered
