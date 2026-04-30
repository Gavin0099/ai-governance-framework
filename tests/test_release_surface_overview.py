import json
import subprocess
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_snapshot import (
    build_release_package_snapshot,
    write_release_root_index,
    write_snapshot_bundle,
)
from governance_tools.release_surface_overview import (
    assess_release_surface,
    format_human_result,
    format_markdown_result,
)
from governance_tools.escalation_authority_writer import write_authority_artifact
from governance_tools.authority_rollout_policy import STRICT_POLICY_MODE


def _local_tmp(name: str) -> Path:
    path = Path("tests") / "_tmp_release_surface_overview" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_release_surface_overview_fails_closed_for_current_alpha_with_escalation_debt():
    """Real repo has active escalation log but no authority artifacts → fail-closed is correct."""
    result = assess_release_surface(Path(".").resolve(), version="v1.0.0-alpha")

    assert result["ok"] is False
    assert result["readiness"]["ok"] is True
    assert result["package"]["ok"] is True
    assert "escalation_authority" in result
    assert result["escalation_authority"]["source"] in {
        "no_escalation_expected",
        "escalation_expected_missing",
        "authority-writer-monopoly",
    }
    assert result["escalation_authority"]["release_blocked"] is True
    assert result["bundle_manifest"]["source"] in {"unavailable", "docs-release", "artifact-bundle"}
    assert result["publication_manifest"]["source"] in {"unavailable", "docs-release-root", "artifact-bundle"}
    assert any(item["name"] == "release_package_snapshot_docs" for item in result["commands"])


def test_release_surface_overview_can_read_explicit_bundle_and_publication():
    tmp_path = _local_tmp("explicit")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package" / "v1.0.0-alpha")
        root_paths = write_release_root_index(tmp_path / "docs" / "releases" / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

        result = assess_release_surface(
            Path(".").resolve(),
            version="v1.0.0-alpha",
            bundle_manifest=Path(bundle["manifest_json"]),
            publication_manifest=Path(root_paths["generated_root_publication_manifest_json"]),
        )

        # overall ok is governed by escalation authority (real repo fails closed); not what this test validates
        assert result["bundle_manifest"]["available"] is True
        assert result["bundle_manifest"]["source"] == "explicit"
        assert result["bundle_manifest"]["version"] == "v1.0.0-alpha"
        assert result["publication_manifest"]["available"] is True
        assert result["publication_manifest"]["source"] == "explicit"
        assert result["publication_manifest"]["publication_scope"] == "docs-release-root"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_human_and_markdown_outputs_are_summary_first():
    tmp_path = _local_tmp("rendering")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")
        result = assess_release_surface(
            Path(".").resolve(),
            version="v1.0.0-alpha",
            bundle_manifest=Path(bundle["manifest_json"]),
        )

        rendered_human = format_human_result(result)
        rendered_markdown = format_markdown_result(result)

        # Real repo fails closed due to escalation authority debt; rendering test checks format, not ok value.
        assert rendered_human.startswith("summary=ok=False | version=v1.0.0-alpha")
        assert "[release_surface_overview]" in rendered_human
        assert "[bundle_manifest]" in rendered_human
        assert "[publication_manifest]" in rendered_human
        assert "[escalation_authority]" in rendered_human
        assert rendered_markdown.startswith("# Release Surface Overview")
        assert "- Summary: `summary=ok=False | version=v1.0.0-alpha" in rendered_markdown
        assert "## Surface Status" in rendered_markdown
        assert "## Suggested Commands" in rendered_markdown
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_cli_supports_direct_script_invocation():
    tmp_path = _local_tmp("cli")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")
        root_paths = write_release_root_index(tmp_path / "docs" / "releases" / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

        result = subprocess.run(
            [
                sys.executable,
                "governance_tools/release_surface_overview.py",
                "--version",
                "v1.0.0-alpha",
                "--bundle-manifest",
                bundle["manifest_json"],
                "--publication-manifest",
                root_paths["generated_root_publication_manifest_json"],
                "--format",
                "human",
            ],
            check=False,
            capture_output=True, stdin=subprocess.DEVNULL,
            text=True,
        )

        # CLI exits 1 (ok=False) because real repo has escalation debt with no authority artifacts.
        assert "summary=ok=False | version=v1.0.0-alpha" in result.stdout
        assert "[release_surface_overview]" in result.stdout
        assert "[escalation_authority]" in result.stdout
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_fails_closed_on_untrusted_escalation_authority():
    tmp_path = _local_tmp("untrusted_authority")
    try:
        authority_dir = tmp_path / "artifacts" / "runtime" / "e1b-phase-b-escalation" / "authority"
        authority_dir.mkdir(parents=True, exist_ok=True)
        bad_artifact = {
            "artifact_type": "e1b_phase_b_escalation_authority",
            "artifact_schema": "e1b.phase_b.escalation_authority.v1",
            "authority_provenance": {
                "writer_id": "fake.writer",
                "writer_version": "1.0",
                "authority_valid": True,
                "payload_fingerprint": "bad",
            },
            "payload": {
                "escalation_id": "esc-20260417-001",
                "mitigation_validation_state": "author_provisional",
                "governance_track_state": "pending_independent_validation",
                "forced_owner": "framework_maintainer",
                "forced_escalation_target": "tier1_reviewer_pool",
                "forced_route_due_date": "2026-05-05",
                "forced_route_status": "assigned",
                "protected_claim_used": False,
                "coverage_era": "CURRENT",
                "coverage_caveat": None,
                "contamination_status": "resolved",
                "release_claims_resolved": False,
                "release_blocked": False,
                "release_block_reasons": [],
                "escalation_closed": False,
            },
        }
        (authority_dir / "esc-20260417-001.json").write_text(
            json.dumps(bad_artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = assess_release_surface(tmp_path, version="v1.0.0-alpha")

        assert result["ok"] is False
        assert result["escalation_authority"]["available"] is True
        assert result["escalation_authority"]["ok"] is False
        assert result["escalation_authority"]["release_blocked"] is True
        assert "untrusted_escalation_provenance" in result["escalation_authority"]["release_block_reasons"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_exposes_precedence_details_for_reviewer_surface():
    tmp_path = _local_tmp("precedence_reviewer_visible")
    try:
        resolved_payload = {
            "escalation_id": "esc-resolved",
            "mitigation_validation_state": "validated",
            "governance_track_state": "closure_eligible",
            "forced_owner": "framework_maintainer",
            "forced_escalation_target": "tier1_reviewer_pool",
            "forced_route_due_date": "2026-05-05",
            "forced_route_status": "completed",
            "protected_claim_used": False,
            "coverage_era": "CURRENT",
            "coverage_caveat": None,
            "contamination_status": "resolved",
            "release_claims_resolved": True,
            "escalation_closed": False,
            "authority_lifecycle_state": "resolved_confirmed",
            "lifecycle_transition": {
                "from_state": "resolved_provisional",
                "actor": "reviewer_confirmed",
                "auto": False,
                "reviewer_confirmation": {
                    "reviewer_id": "reviewer-001",
                    "confirmed_at": "2026-04-27T09:00:00+00:00",
                },
            },
        }
        active_payload = {
            "escalation_id": "esc-active",
            "mitigation_validation_state": "validated",
            "governance_track_state": "closure_eligible",
            "forced_owner": "framework_maintainer",
            "forced_escalation_target": "tier1_reviewer_pool",
            "forced_route_due_date": "2026-05-05",
            "forced_route_status": "in_progress",
            "protected_claim_used": False,
            "coverage_era": "CURRENT",
            "coverage_caveat": None,
            "contamination_status": "resolved",
            "release_claims_resolved": False,
            "escalation_closed": False,
            "authority_lifecycle_state": "active",
        }
        assert write_authority_artifact(tmp_path, resolved_payload)["ok"] is True
        assert write_authority_artifact(tmp_path, active_payload)["ok"] is True

        result = assess_release_surface(tmp_path, version="v1.0.0-alpha")
        rendered_human = format_human_result(result)

        assert result["ok"] is False
        assert result["escalation_authority"]["ok"] is False
        assert result["escalation_authority"]["precedence_applied"] is True
        assert (
            "authority_precedence_active_blocks_release"
            in result["escalation_authority"]["release_block_reasons"]
        )
        assert result["escalation_authority"]["lifecycle_effective_by_escalation"] == {
            "esc-active": "active",
            "esc-resolved": "resolved_confirmed",
        }
        assert "precedence_applied=True" in rendered_human
        assert (
            'lifecycle_effective_by_escalation={"esc-active": "active", "esc-resolved": "resolved_confirmed"}'
            in rendered_human
        )
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_strict_register_mode_off_vs_on():
    tmp_path = _local_tmp("strict_register_mode_off_vs_on")
    try:
        payload = {
            "escalation_id": "esc-strict-001",
            "mitigation_validation_state": "validated",
            "governance_track_state": "closure_eligible",
            "forced_owner": "framework_maintainer",
            "forced_escalation_target": "tier1_reviewer_pool",
            "forced_route_due_date": "2026-05-05",
            "forced_route_status": "completed",
            "protected_claim_used": False,
            "coverage_era": "CURRENT",
            "coverage_caveat": None,
            "contamination_status": "resolved",
            "release_claims_resolved": True,
            "escalation_closed": False,
            "authority_lifecycle_state": "resolved_confirmed",
            "lifecycle_transition": {
                "from_state": "resolved_provisional",
                "actor": "reviewer_confirmed",
                "auto": False,
                "reviewer_confirmation": {
                    "reviewer_id": "reviewer-001",
                    "confirmed_at": "2026-04-27T09:00:00+00:00",
                },
            },
        }
        assert write_authority_artifact(tmp_path, payload)["ok"] is True

        # Strict OFF: should not fail only because register is absent.
        result_off = assess_release_surface(
            tmp_path,
            version="v1.0.0-alpha",
            authority_require_register=False,
        )
        assert result_off["escalation_authority"]["register_required_mode"] is False
        assert result_off["escalation_authority"]["register_present"] is False
        assert result_off["escalation_authority"]["ok"] is True

        # Strict ON: same artifact should fail-closed on missing register.
        result_on = assess_release_surface(
            tmp_path,
            version="v1.0.0-alpha",
            authority_require_register=True,
        )
        rendered_on = format_human_result(result_on)
        assert result_on["escalation_authority"]["ok"] is False
        assert result_on["escalation_authority"]["decision_source"] == "strict_register_enforcement"
        assert "mandatory_register_missing" in result_on["escalation_authority"]["release_block_reasons"]
        assert "decision_source=strict_register_enforcement" in rendered_on
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_explicit_override_beats_policy_file():
    tmp_path = _local_tmp("strict_policy_file_override")
    try:
        payload = {
            "escalation_id": "esc-policy-override-001",
            "mitigation_validation_state": "validated",
            "governance_track_state": "closure_eligible",
            "forced_owner": "framework_maintainer",
            "forced_escalation_target": "tier1_reviewer_pool",
            "forced_route_due_date": "2026-05-05",
            "forced_route_status": "completed",
            "protected_claim_used": False,
            "coverage_era": "CURRENT",
            "coverage_caveat": None,
            "contamination_status": "resolved",
            "release_claims_resolved": True,
            "escalation_closed": False,
            "authority_lifecycle_state": "resolved_confirmed",
            "lifecycle_transition": {
                "from_state": "resolved_provisional",
                "actor": "reviewer_confirmed",
                "auto": False,
                "reviewer_confirmation": {
                    "reviewer_id": "reviewer-001",
                    "confirmed_at": "2026-04-27T09:00:00+00:00",
                },
            },
        }
        assert write_authority_artifact(tmp_path, payload)["ok"] is True
        policy_file = tmp_path / "artifacts" / "governance" / "authority-rollout-policy.json"
        policy_file.parent.mkdir(parents=True, exist_ok=True)
        policy_file.write_text(
            json.dumps({"policy_mode": STRICT_POLICY_MODE}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result_default = assess_release_surface(
            tmp_path,
            version="v1.0.0-alpha",
            authority_policy_file=policy_file,
        )
        assert result_default["escalation_authority"]["ok"] is False
        assert "mandatory_register_missing" in result_default["escalation_authority"]["release_block_reasons"]
        assert result_default["authority_rollout_policy"]["policy_source"] == "policy_file"

        result_explicit_override = assess_release_surface(
            tmp_path,
            version="v1.0.0-alpha",
            authority_policy_file=policy_file,
            authority_require_register=False,
        )
        assert result_explicit_override["escalation_authority"]["ok"] is True
        assert result_explicit_override["authority_rollout_policy"]["policy_source"] == "explicit_override"
        assert result_explicit_override["authority_rollout_policy"]["explicit_override"] is True
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_surface_overview_includes_structural_promotion_gate(monkeypatch):
    monkeypatch.setattr(
        "governance_tools.release_surface_overview.assess_release_readiness",
        lambda *_args, **_kwargs: {"ok": True, "checks": [], "warnings": [], "errors": []},
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview.assess_release_package",
        lambda *_args, **_kwargs: {
            "ok": True,
            "existing_release_docs": 1,
            "release_doc_count": 1,
            "existing_status_docs": 1,
            "status_doc_count": 1,
        },
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview._assess_bundle_manifest",
        lambda **_kwargs: {
            "ok": True,
            "available": True,
            "source": "explicit",
            "manifest_file": "x",
        },
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview._assess_publication_manifest",
        lambda **_kwargs: {
            "ok": True,
            "available": True,
            "source": "explicit",
            "manifest_file": "y",
        },
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview.resolve_authority_rollout_policy",
        lambda **_kwargs: type(
            "Policy",
            (),
            {
                "require_register": False,
                "policy_source": "explicit_override",
                "policy_mode": "non_strict",
                "explicit_override": True,
            },
        )(),
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview.assess_authority_directory",
        lambda *_args, **_kwargs: {
            "ok": True,
            "available": True,
            "source": "authority-writer-monopoly",
            "lifecycle_effective_by_escalation": {},
            "release_blocked": False,
            "artifacts_read": 0,
        },
    )
    monkeypatch.setattr(
        "governance_tools.release_surface_overview.evaluate_structural_promotion_gate",
        lambda *_args, **_kwargs: {
            "ok": False,
            "promotion_allowed": False,
            "failure_class": "runtime_unverifiable",
            "blocked_reasons": ["claim_boundary_not_runtime_verified"],
            "claim_boundary": "implementation_landed_not_runtime_verified",
            "test_execution_degraded_reason": "pytest_basetemp_permission_error",
        },
    )

    result = assess_release_surface(Path(".").resolve(), version="v1.0.0-alpha")
    assert result["ok"] is False
    assert result["structural_promotion"]["promotion_allowed"] is False
    assert "claim_boundary_not_runtime_verified" in result["structural_promotion"]["blocked_reasons"]
