from governance_tools.version_bump_guard import evaluate_paths


def test_recommend_none_for_docs_only() -> None:
    result = evaluate_paths(
        [
            "docs/guide.md",
            "memory/2026-05-06.md",
        ]
    )
    assert result.recommended_bump == "none"
    assert result.manual_review_required is False


def test_recommend_patch_for_test_only_change() -> None:
    result = evaluate_paths(["tests/test_external_repo_smoke.py"])
    assert result.recommended_bump == "patch"


def test_recommend_minor_for_runtime_surface_change() -> None:
    result = evaluate_paths(["runtime_hooks/core/post_task_check.py"])
    assert result.recommended_bump == "minor"


def test_recommend_major_for_required_versions_change() -> None:
    result = evaluate_paths(["governance/runtime/required_versions.yaml"])
    assert result.recommended_bump == "major"
    assert result.manual_review_required is True

