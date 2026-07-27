#!/usr/bin/env python3
"""Focused tests for frozen Gate 2 operator-runner invariants."""
from __future__ import annotations

import os
import sys
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate2_formal_runner as runner  # noqa: E402


class IdentityTests(unittest.TestCase):
    def test_opaque_run_identity_is_accepted(self) -> None:
        runner.assert_opaque_identity(
            "run_id", "gate2-formal-20260727-OUTRUN-0123456789abcdef"
        )

    def test_arm_bearing_identity_is_rejected(self) -> None:
        for value in (
            "gate2-arm-D",
            "formal_arm_a_output",
            r"D:\producer\arm-C",
        ):
            with self.assertRaises(RuntimeError, msg=value):
                runner.assert_opaque_identity("identity", value)

    def test_producer_prompt_does_not_disclose_assignment_letter(self) -> None:
        for arm in runner.ORDER:
            prompt = runner.producer_prompt(arm)
            self.assertNotIn(f"Arm {arm}", prompt)
            self.assertNotIn(f"arm-{arm}", prompt)
            self.assertIn("Do not put any arm letter", prompt)


class FrozenSchemaTests(unittest.TestCase):
    def test_scorer_schema_requires_all_pre_mapping_fields(self) -> None:
        schema = runner.formal_scorer_schema("primary")
        item = schema["properties"]["outputs"]["items"]
        required = set(item["required"])
        self.assertTrue({
            "score",
            "acceptance_criterion_met",
            "completion_claim_evidence_consistent",
            "suspected_treatment",
            "suspected_confidence",
        }.issubset(required))
        self.assertEqual(
            schema["properties"]["scorer_role"]["enum"], ["primary"]
        )

    def test_frozen_order_and_image_are_unchanged(self) -> None:
        self.assertEqual(runner.ORDER, ("D", "C", "A", "B"))
        self.assertEqual(
            runner.IMAGE,
            "sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168",
        )
        self.assertEqual(
            runner.EXPECTED_TREE,
            "36c346fa951a24cbf914ef04469aac5cb5fd8b86",
        )


if __name__ == "__main__":
    unittest.main()
