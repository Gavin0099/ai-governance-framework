import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.architecture_impact_estimator import estimate_architecture_impact, format_human_result


@pytest.fixture
def local_estimator_root():
    path = Path("tests") / "_tmp_architecture_impact"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_architecture_impact_estimator_escalates_refactor_with_api_changes(local_estimator_root):
    before_dir = local_estimator_root / "application"
    after_dir = local_estimator_root / "application"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)
    before_file = before_dir / "before.cs"
    after_file = after_dir / "after.cs"
    before_file.write_text("public class Service\n{\n    public int Run(int value) => value;\n}\n", encoding="utf-8")
    after_file.write_text(
        "public class Service\n{\n    public int Run(int value) => value;\n    public int Ping() => 0;\n}\n",
        encoding="utf-8",
    )

    result = estimate_architecture_impact(
        [before_file],
        [after_file],
        scope="refactor",
        active_rules=["common", "refactor"],
    )

    assert result["ok"] is True
    assert "public-api-expansion-risk" in result["concerns"]
    assert "public-api-review" in result["required_evidence"]
    assert result["recommended_oversight"] == "review-required"
    assert result["touched_layers"] == ["application"]
    assert "public_api_diff_checker" in result["expected_validators"]
    assert result["impact_report"]["public_api_diff_present"] is True


def test_architecture_impact_estimator_blocks_cross_project_dependency_risk(local_estimator_root):
    before_dir = local_estimator_root / "domain"
    after_dir = local_estimator_root / "infrastructure"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)
    before_file = before_dir / "before.cpp"
    after_file = after_dir / "after.cpp"
    before_file.write_text('#include "LocalHeader.h"\n', encoding="utf-8")
    after_file.write_text('#include "LocalHeader.h"\n#include "../peer/Global.h"\n', encoding="utf-8")

    result = estimate_architecture_impact(
        [before_file],
        [after_file],
        scope="feature",
        active_rules=["common", "cpp"],
    )

    assert result["ok"] is False
    assert "structural-drift-risk" in result["concerns"]
    assert "cross-layer-change-risk" in result["concerns"]
    assert result["recommended_risk"] == "high"
    assert result["recommended_oversight"] == "human-approval"
    assert result["impact_report"]["boundary_risk"] == "high"
    assert result["impact_report"]["touched_layers"] == ["domain", "infrastructure"]


def test_architecture_impact_estimator_marks_kernel_driver_as_high_risk(local_estimator_root):
    before_dir = local_estimator_root / "kernel" / "driver"
    after_dir = local_estimator_root / "kernel" / "driver"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)
    before_file = before_dir / "before.c"
    after_file = after_dir / "after.c"
    before_file.write_text("int driver_entry(void) { return 0; }\n", encoding="utf-8")
    after_file.write_text("int driver_entry(void) { return 1; }\n", encoding="utf-8")

    result = estimate_architecture_impact(
        [before_file],
        [after_file],
        scope="feature",
        active_rules=["common", "cpp", "kernel-driver"],
    )

    assert result["recommended_risk"] == "high"
    assert result["recommended_oversight"] == "human-approval"
    assert "driver-static-analysis" in result["required_evidence"]
    assert "driver_evidence_validator" in result["expected_validators"]
    assert result["impact_report"]["touched_layers"] == ["platform"]


def test_architecture_impact_estimator_human_output_is_readable(local_estimator_root):
    before_dir = local_estimator_root / "application"
    after_dir = local_estimator_root / "application"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)
    before_file = before_dir / "before.cs"
    after_file = after_dir / "after.cs"
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    result = estimate_architecture_impact(
        [before_file],
        [after_file],
        scope="refactor",
        active_rules=["common", "refactor"],
    )

    output = format_human_result(result)
    assert "recommended_risk=high" in output
    assert "recommended_oversight=human-approval" in output
    assert "touched_layers=application" in output
    assert "expected_validators=architecture_drift_checker,public_api_diff_checker,refactor_evidence_validator" in output
