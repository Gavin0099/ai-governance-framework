from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from governance_tools.fleet_matrix_snapshot_validator import (
    REQUIRED_TOP_LEVEL_KEYS,
    validate_snapshot_metadata,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_snapshot() -> dict:
    return {
        "matrix_version": "v1",
        "generated_at": "2026-06-12T17:33:13",
        "matrix_generated_at": "2026-06-12T09:33:13.0000000Z",
        "generation_tool": "scripts/governance_repo_matrix.ps1",
        "generation_tool_commit": "1082569",
        "source_repo_set": {
            "definition": "hardcoded-in-tool",
            "company_repos": ["repo-a"],
            "private_repos": ["repo-b"],
            "scope_file_used_for_classification": "governance/fleet/governance_scope.yaml",
        },
        "evidence_window_days": 7,
        "framework_repo": "framework",
        "repo_inventory": [],
    }


def test_valid_snapshot_passes() -> None:
    result = validate_snapshot_metadata(_valid_snapshot())
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["problems"] == []


def test_missing_reproducibility_metadata_fails() -> None:
    snapshot = _valid_snapshot()
    del snapshot["generation_tool_commit"]
    del snapshot["source_repo_set"]
    result = validate_snapshot_metadata(snapshot)
    assert result["ok"] is False
    assert "generation_tool_commit" in result["missing"]
    assert "source_repo_set" in result["missing"]


def test_pre_p1g_snapshot_shape_fails() -> None:
    # The 2026-05/06 artifact shape: generated_at without tool attribution.
    legacy = {
        "matrix_version": "v1",
        "generated_at": "2026-06-12T17:33:13",
        "evidence_window_days": 7,
        "framework_repo": "framework",
        "repo_inventory": [],
    }
    result = validate_snapshot_metadata(legacy)
    assert result["ok"] is False
    assert "matrix_generated_at" in result["missing"]
    assert "generation_tool" in result["missing"]


def test_source_repo_set_shape_and_window_checks() -> None:
    snapshot = _valid_snapshot()
    snapshot["source_repo_set"] = {"definition": "hardcoded-in-tool"}
    snapshot["evidence_window_days"] = 0
    result = validate_snapshot_metadata(snapshot)
    assert result["ok"] is False
    assert any("company_repos" in p for p in result["problems"])
    assert any("evidence_window_days" in p for p in result["problems"])


def test_cli_validates_file_with_bom(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snap.json"
    snapshot_path.write_text(
        json.dumps(_valid_snapshot()), encoding="utf-8-sig"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.fleet_matrix_snapshot_validator",
            "--snapshot",
            str(snapshot_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


def test_registered_generator_script_carries_metadata_keys() -> None:
    script = REPO_ROOT / "scripts" / "governance_repo_matrix.ps1"
    assert script.is_file(), "registered generator must exist at scripts/"
    text = script.read_text(encoding="utf-8")
    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in text, f"generator must emit {key}"
    assert "hardcoded-in-tool" in text
    # The registered tool must not hardcode the framework root.
    assert "$framework = if ($env:AI_GOVERNANCE_FRAMEWORK_ROOT)" in text
