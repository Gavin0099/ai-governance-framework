from __future__ import annotations

import json
from pathlib import Path

from governance_tools.external_repo_onboarding_index import (
    build_external_repo_onboarding_index,
    format_human,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_external_repo_onboarding_index_orders_failures_first(tmp_path: Path) -> None:
    ok_repo = tmp_path / "ok-repo"
    bad_repo = tmp_path / "bad-repo"

    _write_json(
        ok_repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": True,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "ok-contract.yaml",
            "readiness": {"ready": True, "errors": []},
            "smoke": {"ok": True, "rules": ["common", "firmware"], "errors": []},
        },
    )
    _write_json(
        bad_repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": False,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "bad-contract.yaml",
            "readiness": {"ready": False, "errors": ["missing hooks"]},
            "smoke": {"ok": False, "rules": ["common"], "errors": ["bad contract"]},
        },
    )

    result = build_external_repo_onboarding_index([ok_repo, bad_repo])

    assert result["ok"] is False
    assert result["indexed_count"] == 2
    assert result["entries"][0]["repo_root"].endswith("bad-repo")
    assert result["entries"][1]["repo_root"].endswith("ok-repo")


def test_build_external_repo_onboarding_index_tracks_missing_reports(tmp_path: Path) -> None:
    repo = tmp_path / "missing-repo"
    result = build_external_repo_onboarding_index([repo])

    assert result["ok"] is False
    assert result["indexed_count"] == 0
    assert result["missing_reports"] == [str(repo.resolve())]


def test_format_human_lists_repos_and_missing_reports(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_json(
        repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": True,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "contract.yaml",
            "readiness": {"ready": True, "errors": []},
            "smoke": {"ok": True, "rules": ["common", "kernel-driver"], "errors": []},
        },
    )

    result = build_external_repo_onboarding_index([repo, tmp_path / "missing"])
    rendered = format_human(result)

    assert "[external_repo_onboarding_index]" in rendered
    assert "[missing_reports]" in rendered
    assert "[repos]" in rendered
    assert "kernel-driver" in rendered
