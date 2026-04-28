from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.external_repo_onboarding_index import (
    build_external_repo_onboarding_index,
    format_human,
)


FIXTURE_ROOT = Path("tests/_tmp_external_repo_onboarding_index")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_external_repo_onboarding_index_orders_failures_first() -> None:
    root = _reset_fixture("orders_failures_first")
    ok_repo = root / "ok-repo"
    bad_repo = root / "bad-repo"

    _write_json(
        ok_repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": True,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "ok-contract.yaml",
            "readiness": {"ready": True, "errors": [], "project_facts": {"status": "available", "artifact_exists": False, "artifact_drift": False, "source_filename": "02_project_facts.md"}},
            "smoke": {"ok": True, "rules": ["common", "firmware"], "errors": []},
        },
    )
    _write_json(
        bad_repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": False,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "bad-contract.yaml",
            "readiness": {"ready": False, "errors": ["missing hooks"], "project_facts": {"status": "missing", "artifact_exists": False, "artifact_drift": False, "source_filename": None}},
            "smoke": {"ok": False, "rules": ["common"], "errors": ["bad contract"]},
        },
    )

    result = build_external_repo_onboarding_index([ok_repo, bad_repo])

    assert result["ok"] is False
    assert result["indexed_count"] == 2
    assert result["entries"][0]["repo_root"].endswith("bad-repo")
    assert result["entries"][0]["project_facts_status"] == "missing"
    assert result["entries"][1]["repo_root"].endswith("ok-repo")
    assert result["top_issues"][0]["repo_root"].endswith("bad-repo")
    assert "readiness" in result["top_issues"][0]["reasons"]
    assert "smoke" in result["top_issues"][0]["reasons"]
    assert "external_repo_onboarding_report.py" in result["top_issues"][0]["suggested_command"]


def test_build_external_repo_onboarding_index_tracks_missing_reports() -> None:
    root = _reset_fixture("tracks_missing_reports")
    repo = root / "missing-repo"
    result = build_external_repo_onboarding_index([repo])

    assert result["ok"] is False
    assert result["indexed_count"] == 0
    assert result["missing_reports"] == [str(repo.resolve())]


def test_format_human_lists_repos_and_missing_reports() -> None:
    root = _reset_fixture("format_human")
    repo = root / "repo"
    _write_json(
        repo / "memory" / "governance_onboarding" / "latest.json",
        {
            "ok": False,
            "generated_at": "2026-03-15T00:00:00+00:00",
            "contract_path": "contract.yaml",
            "readiness": {"ready": False, "errors": ["missing hooks"], "project_facts": {"status": "drifted", "artifact_exists": True, "artifact_drift": True, "source_filename": "02_project_facts.md"}},
            "smoke": {"ok": True, "rules": ["common", "kernel-driver"], "errors": []},
        },
    )

    result = build_external_repo_onboarding_index([repo, root / "missing"])
    rendered = format_human(result)

    assert "[external_repo_onboarding_index]" in rendered
    assert "summary=ok=False | repos=2 | indexed=1 | missing=1 | top_issues=1" in rendered
    assert "[missing_reports]" in rendered
    assert "[repos]" in rendered
    assert "[top_issues]" in rendered
    assert "kernel-driver" in rendered
    assert "project_facts=status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md" in rendered
    assert "external_repo_readiness.py" in rendered
