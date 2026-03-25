from __future__ import annotations

from governance_tools.workflow_observation_policy import (
    consumer_defaults,
    diagnostic_field_policy,
    load_workflow_observation_policy,
    observation_metric_name,
    state_policy,
)


def test_policy_uses_observation_coverage_not_workflow_score() -> None:
    policy = load_workflow_observation_policy()
    assert observation_metric_name() == "observation_coverage"
    assert "workflow_score" in policy["metric"]["forbidden_aliases"]


def test_policy_forbids_direct_enforcement_from_observation_states() -> None:
    defaults = consumer_defaults()
    assert "block" in defaults["forbidden_direct_consequences"]
    assert "raise_minimum_task_level" in defaults["forbidden_direct_consequences"]
    assert "compliance_judgment" in defaults["forbidden_observation_only_conclusions"]
    assert "intent_inference" in defaults["forbidden_observation_only_conclusions"]
    assert "observation-only combination inference" in defaults["combination_rule"]

    missing = state_policy("missing")
    unverifiable = state_policy("unverifiable")
    stale = state_policy("stale")

    assert missing["failure_source_class"] == "no_artifact_present"
    assert "workflow was not done" in missing["forbidden_interpretations"]
    assert "intentional bypass occurred" in unverifiable["forbidden_interpretations"]
    assert "task is invalid" in stale["forbidden_interpretations"]


def test_failure_source_class_is_diagnostic_only() -> None:
    policy = diagnostic_field_policy("failure_source_class")
    assert policy["role"] == "diagnostic_aid"
    assert "consequence_key" in policy["not_a"]
    assert "policy_severity" in policy["not_a"]
    assert "compliance_proxy" in policy["not_a"]