import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.architecture_impact_estimator import estimate_architecture_impact


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
    before_file = local_estimator_root / "before.cs"
    after_file = local_estimator_root / "after.cs"
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


def test_architecture_impact_estimator_blocks_cross_project_dependency_risk(local_estimator_root):
    before_file = local_estimator_root / "before.cpp"
    after_file = local_estimator_root / "after.cpp"
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
    assert result["recommended_risk"] == "high"
    assert result["recommended_oversight"] == "human-approval"


def test_architecture_impact_estimator_marks_kernel_driver_as_high_risk(local_estimator_root):
    before_file = local_estimator_root / "before.c"
    after_file = local_estimator_root / "after.c"
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
