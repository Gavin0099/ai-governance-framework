#!/usr/bin/env python3
"""
Tests for governance_tools/output_tier.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.output_tier import (
    TASK_LEVEL_TIER_MAP,
    OutputTier,
    TieredOutput,
    generate_trace_id,
    get_default_tier,
    load_tier3_artifact,
)


# ── get_default_tier ──────────────────────────────────────────────────────────

class TestGetDefaultTier:

    def test_l0_maps_to_tier1(self):
        assert get_default_tier("L0") == OutputTier.TIER1

    def test_l1_maps_to_tier2(self):
        assert get_default_tier("L1") == OutputTier.TIER2

    def test_l2_maps_to_tier3(self):
        assert get_default_tier("L2") == OutputTier.TIER3

    def test_case_insensitive_lower(self):
        assert get_default_tier("l0") == OutputTier.TIER1
        assert get_default_tier("l1") == OutputTier.TIER2
        assert get_default_tier("l2") == OutputTier.TIER3

    def test_unknown_level_defaults_to_tier2(self):
        assert get_default_tier("L9") == OutputTier.TIER2

    def test_empty_string_defaults_to_tier2(self):
        assert get_default_tier("") == OutputTier.TIER2

    def test_tier_int_values(self):
        assert OutputTier.TIER1 == 1
        assert OutputTier.TIER2 == 2
        assert OutputTier.TIER3 == 3

    def test_all_task_levels_covered(self):
        for level in ("L0", "L1", "L2"):
            tier = get_default_tier(level)
            assert isinstance(tier, OutputTier)


# ── helpers ───────────────────────────────────────────────────────────────────

def make_sample_output(**kwargs) -> TieredOutput:
    defaults = {
        "verdict": "pass",
        "violations": [],
        "evidence_ids": ["ev-001"],
        "trace_id": "abc123def456abcd",
        "task_level": "L1",
        "repo_type": "service",
    }
    defaults.update(kwargs)
    return TieredOutput(**defaults)


# ── TieredOutput.render — Tier 1 ─────────────────────────────────────────────

class TestTieredOutputRenderTier1:

    def test_tier1_contains_verdict(self):
        output = make_sample_output(verdict="fail")
        rendered = output.render(OutputTier.TIER1)
        assert rendered["verdict"] == "fail"

    def test_tier1_contains_violations(self):
        violations = [{"rule_id": "R001", "severity": "high"}]
        output = make_sample_output(violations=violations)
        rendered = output.render(OutputTier.TIER1)
        assert rendered["violations"] == violations

    def test_tier1_contains_evidence_ids(self):
        output = make_sample_output(evidence_ids=["ev-001", "ev-002"])
        rendered = output.render(OutputTier.TIER1)
        assert rendered["evidence_ids"] == ["ev-001", "ev-002"]

    def test_tier1_contains_trace_id(self):
        output = make_sample_output(trace_id="mytraceabc12345a")
        rendered = output.render(OutputTier.TIER1)
        assert rendered["trace_id"] == "mytraceabc12345a"

    def test_tier1_contains_task_level(self):
        output = make_sample_output(task_level="L0")
        rendered = output.render(OutputTier.TIER1)
        assert rendered["task_level"] == "L0"

    def test_tier1_contains_repo_type(self):
        output = make_sample_output(repo_type="firmware")
        rendered = output.render(OutputTier.TIER1)
        assert rendered["repo_type"] == "firmware"

    def test_tier1_output_tier_value_is_1(self):
        output = make_sample_output()
        rendered = output.render(OutputTier.TIER1)
        assert rendered["output_tier"] == 1

    def test_tier1_excludes_reasoning_fragments(self):
        output = make_sample_output(
            reasoning_fragments=[{"rule_id": "R001", "prose": "test"}]
        )
        rendered = output.render(OutputTier.TIER1)
        assert "reasoning_fragments" not in rendered

    def test_tier1_excludes_policy_refs(self):
        output = make_sample_output(policy_refs=["P-001"])
        rendered = output.render(OutputTier.TIER1)
        assert "policy_refs" not in rendered

    def test_tier1_excludes_decision_path(self):
        output = make_sample_output(decision_path=["step1", "step2"])
        rendered = output.render(OutputTier.TIER1)
        assert "decision_path" not in rendered

    def test_tier1_excludes_full_trace_ref(self):
        output = make_sample_output(full_trace={"key": "value"})
        rendered = output.render(OutputTier.TIER1)
        assert "full_trace_ref" not in rendered
        assert "full_trace" not in rendered


# ── TieredOutput.render — Tier 2 ─────────────────────────────────────────────

class TestTieredOutputRenderTier2:

    def test_tier2_output_tier_value_is_2(self):
        output = make_sample_output()
        rendered = output.render(OutputTier.TIER2)
        assert rendered["output_tier"] == 2

    def test_tier2_includes_all_tier1_fields(self):
        output = make_sample_output()
        rendered = output.render(OutputTier.TIER2)
        for field in ("verdict", "violations", "evidence_ids", "trace_id", "task_level", "repo_type"):
            assert field in rendered

    def test_tier2_includes_reasoning_fragments(self):
        fragments = [{"rule_id": "R001", "prose": "test reasoning"}]
        output = make_sample_output(reasoning_fragments=fragments)
        rendered = output.render(OutputTier.TIER2)
        assert "reasoning_fragments" in rendered
        assert rendered["reasoning_fragments"] == fragments

    def test_tier2_includes_policy_refs(self):
        output = make_sample_output(policy_refs=["P-001", "P-002"])
        rendered = output.render(OutputTier.TIER2)
        assert rendered["policy_refs"] == ["P-001", "P-002"]

    def test_tier2_includes_decision_path(self):
        output = make_sample_output(decision_path=["step1", "step2"])
        rendered = output.render(OutputTier.TIER2)
        assert rendered["decision_path"] == ["step1", "step2"]

    def test_tier2_excludes_full_trace_ref(self):
        output = make_sample_output(full_trace={"key": "value"})
        rendered = output.render(OutputTier.TIER2)
        assert "full_trace_ref" not in rendered
        assert "full_trace" not in rendered


# ── TieredOutput.render — Tier 3 ─────────────────────────────────────────────

class TestTieredOutputRenderTier3:

    def test_tier3_output_tier_value_is_3(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2")
            rendered = output.render(OutputTier.TIER3)
        assert rendered["output_tier"] == 3

    def test_tier3_excludes_full_trace_inline(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(
                task_level="L2",
                full_trace={"key": "very long value"},
                onboarding_narrative="This is a long narrative...",
            )
            rendered = output.render(OutputTier.TIER3)
        assert "full_trace" not in rendered
        assert "onboarding_narrative" not in rendered

    def test_tier3_has_full_trace_ref(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2")
            rendered = output.render(OutputTier.TIER3)
        assert "full_trace_ref" in rendered

    def test_tier3_artifact_file_created(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", full_trace={"k": "v"})
            rendered = output.render(OutputTier.TIER3)

        artifact_path = Path(rendered["full_trace_ref"])
        assert artifact_path.exists()

    def test_tier3_artifact_contains_trace_id(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", trace_id="abc123def456abcd")
            rendered = output.render(OutputTier.TIER3)

        artifact_path = Path(rendered["full_trace_ref"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["trace_id"] == "abc123def456abcd"

    def test_tier3_artifact_contains_verdict(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", verdict="fail")
            rendered = output.render(OutputTier.TIER3)

        artifact_path = Path(rendered["full_trace_ref"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["verdict"] == "fail"

    def test_tier3_artifact_contains_full_trace(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", full_trace={"important": "data"})
            rendered = output.render(OutputTier.TIER3)

        artifact_path = Path(rendered["full_trace_ref"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["full_trace"] == {"important": "data"}

    def test_tier3_artifact_contains_reasoning_fragments(self, tmp_path):
        frags = [{"rule_id": "R001", "severity": "high"}]
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", reasoning_fragments=frags)
            rendered = output.render(OutputTier.TIER3)

        artifact_path = Path(rendered["full_trace_ref"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["reasoning_fragments"] == frags

    def test_tier3_also_includes_tier2_fields(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(
                task_level="L2",
                reasoning_fragments=[{"rule_id": "R001"}],
                policy_refs=["P-001"],
            )
            rendered = output.render(OutputTier.TIER3)
        assert "reasoning_fragments" in rendered
        assert "policy_refs" in rendered


# ── render_for_task_level ─────────────────────────────────────────────────────

class TestRenderForTaskLevel:

    def test_l0_renders_tier1(self):
        output = make_sample_output(
            reasoning_fragments=[{"rule_id": "R001"}]
        )
        rendered = output.render_for_task_level("L0")
        assert rendered["output_tier"] == 1
        assert "reasoning_fragments" not in rendered

    def test_l1_renders_tier2(self):
        output = make_sample_output(
            reasoning_fragments=[{"rule_id": "R001"}]
        )
        rendered = output.render_for_task_level("L1")
        assert rendered["output_tier"] == 2
        assert "reasoning_fragments" in rendered

    def test_l2_renders_tier3(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2")
            rendered = output.render_for_task_level("L2")
        assert rendered["output_tier"] == 3
        assert "full_trace_ref" in rendered


# ── Token reduction property ──────────────────────────────────────────────────

class TestTier1TokenReduction:

    def test_tier1_smaller_than_tier2(self):
        """Tier 1 의 rendered 輸出應小於 Tier 2。"""
        output = make_sample_output(
            reasoning_fragments=[{"rule_id": f"R{i:03}", "prose": "x" * 200}
                                  for i in range(10)],
            policy_refs=["P-001", "P-002"],
            decision_path=["step1", "step2", "step3"],
        )
        tier1_json = json.dumps(output.render(OutputTier.TIER1))
        tier2_json = json.dumps(output.render(OutputTier.TIER2))
        assert len(tier1_json) < len(tier2_json)


# ── generate_trace_id ─────────────────────────────────────────────────────────

class TestGenerateTraceId:

    def test_returns_16_char_hex(self):
        trace_id = generate_trace_id("fix button", "L0")
        assert len(trace_id) == 16
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_different_inputs_different_ids(self):
        id1 = generate_trace_id("fix button", "L0")
        id2 = generate_trace_id("update schema", "L1")
        assert id1 != id2

    def test_empty_task_produces_valid_id(self):
        trace_id = generate_trace_id("", "L1")
        assert len(trace_id) == 16


# ── load_tier3_artifact ───────────────────────────────────────────────────────

class TestLoadTier3Artifact:

    def test_returns_none_when_not_found(self, tmp_path):
        result = load_tier3_artifact("nonexistent", audit_dir=tmp_path)
        assert result is None

    def test_returns_artifact_when_exists(self, tmp_path):
        artifact = {"trace_id": "abc123", "verdict": "pass"}
        (tmp_path / "abc123.json").write_text(
            json.dumps(artifact), encoding="utf-8"
        )
        result = load_tier3_artifact("abc123", audit_dir=tmp_path)
        assert result is not None
        assert result["verdict"] == "pass"

    def test_roundtrip_write_and_read(self, tmp_path):
        with patch("governance_tools.output_tier.GOVERNANCE_AUDIT_DIR", tmp_path):
            output = make_sample_output(task_level="L2", verdict="warn")
            rendered = output.render(OutputTier.TIER3)

        artifact = load_tier3_artifact(output.trace_id, audit_dir=tmp_path)
        assert artifact is not None
        assert artifact["verdict"] == "warn"
        assert artifact["trace_id"] == output.trace_id
