from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.governance_auditor import audit_governance, format_human_result


FIXTURE_ROOT = Path("tests/_tmp_governance_auditor")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_minimal_project(root: Path) -> None:
    _write(root / "README.md", "scripts/run-runtime-governance.sh\n")
    _write(root / ".github/workflows/governance.yml", "runtime-enforcement\nscripts/run-runtime-governance.sh --mode ci\n")
    _write(root / "runtime_hooks/README.md", "scripts/run-runtime-governance.sh\n")
    _write(root / "runtime_hooks/core/pre_task_check.py", "# ok\n")
    _write(root / "runtime_hooks/core/post_task_check.py", "# ok\n")
    _write(root / "runtime_hooks/core/session_end.py", "# ok\n")
    _write(root / "runtime_hooks/dispatcher.py", "# ok\n")
    _write(root / "scripts/run-runtime-governance.sh", "#!/usr/bin/env bash\n")
    _write(root / "governance/HUMAN-OVERSIGHT.md", "ok\n")
    _write(root / "governance/AGENT.md", "ok\n")
    _write(root / "governance/TESTING.md", "ok\n")
    _write(root / "governance/SYSTEM_PROMPT.md", "cross-project private include\n")
    _write(root / "governance/ARCHITECTURE.md", "AdditionalIncludeDirectories\n")
    _write(root / "governance/REVIEW_CRITERIA.md", "C9 Project Include Boundary\n")
    _write(root / "governance/rules/common/core.md", "ok\n")
    _write(root / "governance/rules/python/coding.md", "ok\n")
    _write(root / "governance/rules/cpp/build_boundary.md", "AdditionalIncludeDirectories\n")
    _write(root / "governance/rules/refactor/behavior_lock.md", "ok\n")
    _write(root / "governance/rules/refactor/boundary_safety.md", "ok\n")


def test_governance_auditor_passes_on_repo_root():
    result = audit_governance(Path(".").resolve())
    assert result["ok"] is True
    assert result["errors"] == []
    assert "doc_drift" in result


def test_governance_auditor_can_include_release_readiness():
    result = audit_governance(Path(".").resolve(), release_version="v1.0.0-alpha")

    assert result["ok"] is True
    assert result["release_readiness"]["ok"] is True
    assert any(check["name"] == "release:readiness" and check["ok"] for check in result["checks"])


def test_governance_auditor_human_output_is_summary_first():
    result = audit_governance(Path(".").resolve(), release_version="v1.0.0-alpha")
    output = format_human_result(result)

    assert "[governance_auditor]" in output
    assert "summary=ok=True | checks=" in output
    assert "doc_drift_routes=" in output
    assert "release=v1.0.0-alpha/ready" in output


def test_governance_auditor_detects_missing_runtime_enforcement():
    root = _reset_fixture("missing_runtime")
    _seed_minimal_project(root)
    (root / "scripts/run-runtime-governance.sh").unlink()

    result = audit_governance(root)

    assert result["ok"] is False
    assert any("runtime:scripts/run-runtime-governance.sh" in error for error in result["errors"])


def test_governance_auditor_detects_build_boundary_alignment_drift():
    root = _reset_fixture("boundary_drift")
    _seed_minimal_project(root)
    _write(root / "governance/rules/cpp/build_boundary.md", "missing expected marker\n")

    result = audit_governance(root)

    assert result["ok"] is False
    assert any("alignment:build-boundary" in error for error in result["errors"])


def test_governance_auditor_can_include_external_onboarding_index():
    root = _reset_fixture("with_external_repos")
    _seed_minimal_project(root)
    ok_repo = root / "external-ok"
    bad_repo = root / "external-bad"

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

    result = audit_governance(root, external_repos=[ok_repo, bad_repo])

    assert result["ok"] is False
    assert result["external_onboarding"]["indexed_count"] == 2
    assert result["external_onboarding"]["top_issues"][0]["repo_root"].endswith("external-bad")
    assert any("external:onboarding-index" in error for error in result["errors"])


def test_governance_auditor_surfaces_doc_drift_as_warning():
    root = _reset_fixture("doc_drift")
    _seed_minimal_project(root)
    _write(root / "PLAN.md", "# Plan\n\n## Phase 7\n- goals\n")
    _write(root / "app/goals/page.tsx", "export default function Goals() {}\n")
    _write(root / "app/api/report/route.ts", "export async function GET() {}\n")

    result = audit_governance(root)

    assert result["ok"] is True
    assert result["doc_drift"]["ok"] is False
    assert any("doc-drift:" in warning for warning in result["warnings"])
