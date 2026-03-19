from __future__ import annotations

from pathlib import Path

from governance_tools.feature_surface_snapshot import build_feature_surface_snapshot, format_human


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_feature_surface_snapshot_collects_routes_and_migrations(tmp_path: Path) -> None:
    _write(tmp_path / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(tmp_path / "app" / "goal" / "[id]" / "progress" / "page.tsx", "export default function Progress() {}")
    _write(tmp_path / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(tmp_path / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    snapshot = build_feature_surface_snapshot(tmp_path)

    assert snapshot["app_route_count"] == 2
    assert "/goals" in snapshot["app_routes"]
    assert "/goal/[id]/progress" in snapshot["app_routes"]
    assert snapshot["api_routes"] == ["/report"]
    assert snapshot["migrations"] == ["008_goal_tracking"]


def test_format_human_lists_surface_entries(tmp_path: Path) -> None:
    _write(tmp_path / "app" / "report" / "page.tsx", "export default function Report() {}")

    rendered = format_human(build_feature_surface_snapshot(tmp_path))

    assert "[feature_surface_snapshot]" in rendered
    assert "app_route=/report" in rendered
