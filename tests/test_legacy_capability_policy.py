from governance_tools.legacy_capability_policy import (
    LEGACY_CAPABILITY_POLICY_VERSION,
    build_legacy_capability_policy,
)


def test_build_legacy_capability_policy_has_expected_contract() -> None:
    policy = build_legacy_capability_policy(
        disabled_runtime_features=["pre_task_check", "canonical_closeout"],
    ).to_dict()

    assert policy["policy_version"] == LEGACY_CAPABILITY_POLICY_VERSION
    assert policy["mode"] == "legacy_only"
    assert policy["allowed_features"] == [
        "core_pre_task_check",
        "core_post_task_check",
        "basic_version_compatibility_artifact_write",
    ]
    assert policy["disabled_features"] == ["canonical_closeout", "pre_task_check"]
    assert policy["artifact_write_policy"]["allowed"] == [
        "artifacts/governance/version_compatibility.json"
    ]
    assert "session_index_artifacts" in policy["artifact_write_policy"]["disallowed"]
    assert "legacy_only_boundary=feature_gated_runtime_extensions_not_loaded" in policy["human_surface_requirements"]
    assert "must not re-infer capabilities" in policy["no_reinference_rule"]
