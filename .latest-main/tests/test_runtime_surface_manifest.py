import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.runtime_surface_manifest import (
    build_runtime_surface_manifest,
    manifest_has_consistency_signal,
    render_markdown,
)


def test_runtime_surface_manifest_has_expected_first_slice_entries():
    manifest = build_runtime_surface_manifest(Path(".").resolve())

    assert {entry["adapter_family"] for entry in manifest["adapters"]} == {
        "claude_code",
        "codex",
        "gemini",
    }
    assert {entry["entrypoint_name"] for entry in manifest["runtime_entrypoints"]} >= {
        "session_start",
        "pre_task_check",
        "post_task_check",
        "session_end",
    }
    assert {entry["tool_name"] for entry in manifest["tool_entries"]} >= {
        "adopt_governance",
        "governance_drift_checker",
        "quickstart_smoke",
    }


def test_runtime_surface_manifest_consistency_is_clean_for_current_repo():
    manifest = build_runtime_surface_manifest(Path(".").resolve())
    consistency = manifest["consistency"]

    assert consistency["unknown_surfaces"] == []
    assert consistency["orphan_surfaces"] == []
    assert consistency["evidence_surface_mismatch"] == []
    assert consistency["signal_posture"] == "soft-enforcement"


def test_runtime_surface_manifest_markdown_renders_consistency_summary():
    manifest = build_runtime_surface_manifest(Path(".").resolve())

    markdown = render_markdown(manifest)
    assert "# Runtime Surface Manifest" in markdown
    assert "## Consistency Signals" in markdown
    assert "- unknown_surfaces: `0`" in markdown
    assert "- orphan_surfaces: `0`" in markdown
    assert "- evidence_surface_mismatch: `0`" in markdown


def test_runtime_surface_manifest_is_json_serializable():
    manifest = build_runtime_surface_manifest(Path(".").resolve())
    payload = json.dumps(manifest, ensure_ascii=False)
    assert '"adapters"' in payload
    assert '"consistency"' in payload


def test_runtime_surface_manifest_signal_detection_catches_unknown_adapter(monkeypatch):
    import governance_tools.runtime_surface_manifest as manifest_module

    monkeypatch.setattr(
        manifest_module,
        "KNOWN_ADAPTERS",
        {
            "claude_code": manifest_module.KNOWN_ADAPTERS["claude_code"],
            "codex": manifest_module.KNOWN_ADAPTERS["codex"],
        },
    )

    manifest = manifest_module.build_runtime_surface_manifest(Path(".").resolve())
    assert manifest_has_consistency_signal(manifest) is True
    assert any(
        item["type"] == "adapter_family" and item["name"] == "gemini"
        for item in manifest["consistency"]["unknown_surfaces"]
    )


def test_runtime_surface_manifest_signal_detection_catches_evidence_mismatch(monkeypatch):
    import governance_tools.runtime_surface_manifest as manifest_module

    monkeypatch.setattr(
        manifest_module,
        "KNOWN_EVIDENCE_SURFACES",
        manifest_module.KNOWN_EVIDENCE_SURFACES + [{
            "surface_name": "fake_evidence_surface",
            "path_pattern": "stdout:fake",
            "producer": "not_a_real_producer",
            "artifact_type": "fake-output",
            "machine_readable": False,
            "human_auditable": True,
            "used_by": ["test"],
        }],
    )

    manifest = manifest_module.build_runtime_surface_manifest(Path(".").resolve())
    assert manifest_has_consistency_signal(manifest) is True
    assert any(
        item["name"] == "fake_evidence_surface"
        for item in manifest["consistency"]["evidence_surface_mismatch"]
    )
