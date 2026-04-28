import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.execution_surface_coverage import (
    build_execution_surface_coverage,
    coverage_has_signal,
    render_markdown,
)


def test_execution_surface_coverage_is_clean_for_current_repo():
    payload = build_execution_surface_coverage(Path(".").resolve())
    coverage = payload["coverage"]

    assert coverage["missing_hard_required"] == []
    assert coverage["missing_soft_required"] == []
    assert coverage["dead_surfaces"]["never_observed"] == []
    assert coverage["dead_surfaces"]["never_required"] == []
    assert payload["consumer"] == "reviewer"


def test_execution_surface_coverage_markdown_renders_signal_summary():
    payload = build_execution_surface_coverage(Path(".").resolve())

    markdown = render_markdown(payload)
    assert "# Execution Surface Coverage" in markdown
    assert "## Decision Status" in markdown
    assert "- missing_hard_required: `0`" in markdown
    assert "- dead_never_required: `0`" in markdown


def test_execution_surface_coverage_is_json_serializable():
    payload = build_execution_surface_coverage(Path(".").resolve())
    encoded = json.dumps(payload, ensure_ascii=False)
    assert '"decision_definitions"' in encoded
    assert '"surface_classifications"' in encoded


def test_execution_surface_coverage_signal_detection_catches_missing_hard(monkeypatch):
    import governance_tools.execution_surface_coverage as coverage_module

    monkeypatch.setattr(
        coverage_module,
        "DECISION_DEFINITIONS",
        coverage_module.DECISION_DEFINITIONS + [{
            "decision": "fake_decision",
            "required_surfaces": ["nonexistent_surface"],
            "evidence_surfaces": [],
            "authority_surfaces": [],
            "requirement_level": {"nonexistent_surface": "hard"},
        }],
    )

    payload = coverage_module.build_execution_surface_coverage(Path(".").resolve())
    assert coverage_has_signal(payload) is True
    assert any(item["decision"] == "fake_decision" for item in payload["coverage"]["missing_hard_required"])


def test_execution_surface_coverage_signal_detection_catches_dead_never_required(monkeypatch):
    import governance_tools.execution_surface_coverage as coverage_module

    monkeypatch.setattr(
        coverage_module,
        "SURFACE_CLASSIFICATIONS",
        coverage_module.SURFACE_CLASSIFICATIONS + [{
            "surface_name": "runtime_verdict_artifact_shadow",
            "surface_type": "evidence_surface",
            "coverage_role": "evidence",
            "requirement_level": "optional",
            "used_by": [],
            "failure_modes_if_missing": [],
        }],
    )
    original_build = coverage_module.build_runtime_surface_manifest

    def _build_manifest_with_shadow(repo_root):
        payload = original_build(repo_root)
        payload["evidence_surfaces"] = payload["evidence_surfaces"] + [{
            "surface_name": "runtime_verdict_artifact_shadow",
            "path_pattern": "stdout:shadow",
            "producer": "quickstart_smoke",
            "artifact_type": "shadow",
            "machine_readable": False,
            "human_auditable": True,
            "used_by": [],
        }]
        return payload

    monkeypatch.setattr(coverage_module, "build_runtime_surface_manifest", _build_manifest_with_shadow)

    payload = coverage_module.build_execution_surface_coverage(Path(".").resolve())
    assert coverage_has_signal(payload) is True
    assert any(item["surface_name"] == "runtime_verdict_artifact_shadow" for item in payload["coverage"]["dead_surfaces"]["never_required"])
