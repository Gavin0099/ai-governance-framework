import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_snapshot import (
    build_release_package_snapshot,
    write_release_root_index,
    write_snapshot_bundle,
)
from governance_tools.reviewer_handoff_summary import (
    assess_reviewer_handoff,
    format_human_result,
    format_markdown_result,
)


def test_reviewer_handoff_summary_passes_for_current_alpha():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = assess_reviewer_handoff(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["trust_signal"]["ok"] is True
    assert result["release_surface"]["ok"] is True
    assert any(item["name"] == "release_surface_overview" for item in result["commands"])


def test_reviewer_handoff_summary_can_read_release_bundle_and_publication(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_release_package_snapshot(project_root=project_root, version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package" / "v1.0.0-alpha")
    root_paths = write_release_root_index(
        tmp_path / "docs" / "releases" / "generated",
        version="v1.0.0-alpha",
        bundle_paths=bundle,
    )

    result = assess_reviewer_handoff(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        release_bundle_manifest=Path(bundle["manifest_json"]),
        release_publication_manifest=Path(root_paths["generated_root_publication_manifest_json"]),
    )

    assert result["ok"] is True
    assert result["release_surface"]["bundle_manifest"]["available"] is True
    assert result["release_surface"]["bundle_manifest"]["source"] == "explicit"
    assert result["release_surface"]["publication_manifest"]["available"] is True
    assert result["release_surface"]["publication_manifest"]["source"] == "explicit"


def test_reviewer_handoff_summary_human_and_markdown_outputs_are_summary_first():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    result = assess_reviewer_handoff(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    rendered_human = format_human_result(result)
    rendered_markdown = format_markdown_result(result)

    assert rendered_human.startswith("summary=ok=True | upstream_ok=True | trust=True | release=True | lint=clean | release_version=v1.0.0-alpha")
    assert "[reviewer_handoff_summary]" in rendered_human
    assert "[trust_signal]" in rendered_human
    assert "[release_surface]" in rendered_human
    assert rendered_markdown.startswith("# Reviewer Handoff Summary")
    assert "## Handoff Status" in rendered_markdown
    assert "## Suggested Commands" in rendered_markdown


def test_reviewer_handoff_summary_surfaces_external_fact_states():
    rendered_human = format_human_result(
        {
            "ok": True,
            "project_root": ".",
            "plan_path": "PLAN.md",
            "release_version": "v1.0.0-alpha",
            "contract_path": "example/contract.yaml",
            "strict_runtime": False,
            "external_contract_repos": ["/tmp/kernel-driver-contract"],
            "trust_signal": {
                "ok": True,
                "quickstart": {"ok": True},
                "examples": {"ok": True},
                "release": {"ok": True},
                "auditor": {
                    "ok": True,
                    "external_onboarding": {
                        "top_issues": [
                            {
                                "repo_root": "/tmp/kernel-driver-contract",
                                "project_facts_summary": "status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md",
                            }
                        ]
                    },
                },
            },
            "release_surface": {
                "ok": True,
                "readiness": {"ok": True},
                "package": {"ok": True},
                "bundle_manifest": {"available": True, "source": "explicit"},
                "publication_manifest": {"available": True, "source": "explicit"},
            },
            "commands": [],
        }
    )
    rendered_markdown = format_markdown_result(
        {
            "ok": True,
            "project_root": ".",
            "plan_path": "PLAN.md",
            "release_version": "v1.0.0-alpha",
            "contract_path": "example/contract.yaml",
            "strict_runtime": False,
            "external_contract_repos": ["/tmp/kernel-driver-contract"],
            "trust_signal": {
                "ok": True,
                "quickstart": {"ok": True},
                "examples": {"ok": True},
                "release": {"ok": True},
                "auditor": {
                    "ok": True,
                    "external_onboarding": {
                        "top_issues": [
                            {
                                "repo_root": "/tmp/kernel-driver-contract",
                                "project_facts_summary": "status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md",
                            }
                        ]
                    },
                },
            },
            "release_surface": {
                "ok": True,
                "readiness": {"ok": True},
                "package": {"ok": True},
                "bundle_manifest": {"available": True, "ok": True, "source": "explicit"},
                "publication_manifest": {"available": True, "ok": True, "source": "explicit"},
            },
            "commands": [],
        }
    )

    assert "[external_project_facts]" in rendered_human
    assert "/tmp/kernel-driver-contract: status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md" in rendered_human
    assert "## External Fact States" in rendered_markdown
    assert "/tmp/kernel-driver-contract: status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md" in rendered_markdown


def test_reviewer_handoff_summary_cli_supports_direct_script_invocation(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_release_package_snapshot(project_root=project_root, version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package" / "v1.0.0-alpha")
    root_paths = write_release_root_index(
        tmp_path / "docs" / "releases" / "generated",
        version="v1.0.0-alpha",
        bundle_paths=bundle,
    )

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_handoff_summary.py",
            "--project-root",
            str(project_root),
            "--plan",
            str(project_root / "PLAN.md"),
            "--release-version",
            "v1.0.0-alpha",
            "--contract",
            str(contract_file),
            "--release-bundle-manifest",
            bundle["manifest_json"],
            "--release-publication-manifest",
            root_paths["generated_root_publication_manifest_json"],
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=True | upstream_ok=True | trust=True | release=True | lint=clean | release_version=v1.0.0-alpha" in result.stdout
    assert "[reviewer_handoff_summary]" in result.stdout


def test_reviewer_handoff_non_clean_cannot_appear_clean():
    rendered_human = format_human_result(
        {
            "ok": False,
            "upstream_ok": True,
            "project_root": ".",
            "plan_path": "PLAN.md",
            "release_version": "v1.0.0-alpha",
            "contract_path": "example/contract.yaml",
            "strict_runtime": False,
            "external_contract_repos": [],
            "trust_signal": {
                "ok": True,
                "quickstart": {"ok": True},
                "examples": {"ok": True},
                "release": {"ok": True},
                "auditor": {"ok": True, "external_onboarding": {"top_issues": []}},
            },
            "release_surface": {
                "ok": True,
                "readiness": {"ok": True},
                "package": {"ok": True},
                "bundle_manifest": {"available": True, "source": "explicit"},
                "publication_manifest": {"available": True, "source": "explicit"},
            },
            "reviewer_lint": {
                "status": "non-clean",
                "violation_count": 1,
                "highest_severity": "high",
                "violations": [
                    {
                        "severity": "high",
                        "claim_type": "promotion_claim",
                        "excerpt": "Recommendation: can proceed to promote discussion",
                    }
                ],
            },
            "commands": [],
        }
    )
    assert "summary=ok=False" in rendered_human
    assert "lint=non-clean" in rendered_human
    assert "violation=high|promotion_claim|Recommendation: can proceed to promote discussion" in rendered_human


def test_reviewer_handoff_lints_heading_and_next_step_fields(monkeypatch):
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary.assess_trust_signal_overview",
        lambda **_: {
            "ok": True,
            "quickstart": {"ok": True},
            "examples": {"ok": True},
            "release": {"ok": True},
            "auditor": {"ok": True, "external_onboarding": {"top_issues": []}},
        },
    )
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary.assess_release_surface",
        lambda *_args, **_kwargs: {
            "ok": True,
            "readiness": {"ok": True},
            "package": {"ok": True},
            "bundle_manifest": {"available": True, "source": "explicit", "ok": True},
            "publication_manifest": {"available": True, "source": "explicit", "ok": True},
        },
    )
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary._commands",
        lambda *_args, **_kwargs: [
            {"name": "Status: stable enough for next phase, ready for promote", "command": "echo noop"},
            {"name": "Next: can proceed to promote discussion", "command": "echo ready"},
        ],
    )

    from governance_tools.reviewer_handoff_summary import assess_reviewer_handoff

    result = assess_reviewer_handoff(
        project_root=Path(".").resolve(),
        plan_path=Path("PLAN.md"),
        release_version="v1.0.0-alpha",
    )
    assert result["upstream_ok"] is True
    assert result["ok"] is False
    assert result["reviewer_lint"]["status"] == "non-clean"
    assert result["reviewer_lint"]["violation_count"] >= 1


def test_allow_non_clean_flow_does_not_whiten_identity(monkeypatch):
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary.assess_trust_signal_overview",
        lambda **_: {
            "ok": True,
            "quickstart": {"ok": True},
            "examples": {"ok": True},
            "release": {"ok": True},
            "auditor": {"ok": True, "external_onboarding": {"top_issues": []}},
        },
    )
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary.assess_release_surface",
        lambda *_args, **_kwargs: {
            "ok": True,
            "readiness": {"ok": True},
            "package": {"ok": True},
            "bundle_manifest": {"available": True, "source": "explicit", "ok": True},
            "publication_manifest": {"available": True, "source": "explicit", "ok": True},
        },
    )
    monkeypatch.setattr(
        "governance_tools.reviewer_handoff_summary._commands",
        lambda *_args, **_kwargs: [
            {"name": "Recommendation: can proceed to promote discussion", "command": "echo promote"}
        ],
    )

    from governance_tools.reviewer_handoff_summary import assess_reviewer_handoff

    result = assess_reviewer_handoff(
        project_root=Path(".").resolve(),
        plan_path=Path("PLAN.md"),
        release_version="v1.0.0-alpha",
        fail_on_non_clean=True,
        allow_non_clean=True,
        lint_override_source="test_override",
    )
    assert result["upstream_ok"] is True
    assert result["reviewer_lint"]["status"] == "non-clean"
    assert result["ok"] is True
    assert result["handoff_clean_identity"] is False
    assert result["reviewer_lint_policy"]["override_active"] is True
    assert result["reviewer_lint_policy"]["override_source"] == "test_override"
