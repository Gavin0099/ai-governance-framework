from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.feature_surface_snapshot import build_feature_surface_snapshot, format_human


FIXTURE_ROOT = Path("tests/_tmp_feature_surface_snapshot")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_build_feature_surface_snapshot_collects_routes_and_migrations() -> None:
    root = _reset_fixture("collects_surface")
    _write(root / "app" / "goals" / "page.tsx", "export default function Goals() {}")
    _write(root / "app" / "goal" / "[id]" / "progress" / "page.tsx", "export default function Progress() {}")
    _write(root / "app" / "api" / "report" / "route.ts", "export async function GET() {}")
    _write(root / "supabase" / "migrations" / "008_goal_tracking.sql", "-- migration")

    snapshot = build_feature_surface_snapshot(root)

    assert snapshot["app_route_count"] == 2
    assert "/goals" in snapshot["app_routes"]
    assert "/goal/[id]/progress" in snapshot["app_routes"]
    assert snapshot["api_routes"] == ["/report"]
    assert snapshot["migrations"] == ["008_goal_tracking"]


def test_detects_routes_under_src_app_root() -> None:
    root = _reset_fixture("src_app_layout")
    _write(root / "src" / "app" / "dashboard" / "page.tsx", "export default function Dashboard() {}")
    _write(root / "src" / "app" / "api" / "user" / "route.ts", "export async function GET() {}")

    snapshot = build_feature_surface_snapshot(root)

    assert snapshot["app_routes"] == ["/dashboard"]
    assert snapshot["api_routes"] == ["/user"]


def test_warns_when_both_app_roots_exist(capsys) -> None:
    root = _reset_fixture("both_roots")
    _write(root / "app" / "legacy" / "page.tsx", "...")
    _write(root / "src" / "app" / "modern" / "page.tsx", "...")

    build_feature_surface_snapshot(root)
    captured = capsys.readouterr()

    assert "warning: multiple app route roots detected" in captured.err


def test_deduplicates_same_route_across_app_roots() -> None:
    root = _reset_fixture("deduplicate_roots")
    _write(root / "app" / "admin" / "page.tsx", "old admin")
    _write(root / "src" / "app" / "admin" / "page.tsx", "new admin")

    snapshot = build_feature_surface_snapshot(root)

    # Normalized route is /admin for both
    assert snapshot["app_routes"] == ["/admin"]
    assert snapshot["app_route_count"] == 1


def test_format_human_lists_surface_entries() -> None:
    root = _reset_fixture("human_output")
    _write(root / "app" / "report" / "page.tsx", "export default function Report() {}")

    rendered = format_human(build_feature_surface_snapshot(root))

    assert "[feature_surface_snapshot]" in rendered
    assert "app_route=/report" in rendered
