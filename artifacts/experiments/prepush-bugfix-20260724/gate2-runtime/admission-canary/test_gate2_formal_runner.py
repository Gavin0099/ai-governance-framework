#!/usr/bin/env python3
"""Focused tests for frozen Gate 2 operator-runner invariants."""
from __future__ import annotations

import copy
import os
import sys
import unittest
from unittest import mock


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
    def test_recoverable_instrument_failure_is_narrow(self) -> None:
        failed_name = (
            "shared observable (normalised stdout digest) agrees on both sides "
            "(order-independent)"
        )
        admitted = {
            "verdict": "FAIL",
            "adapter_rejected": 0,
            "checks": [
                {"name": "other", "pass": True},
                {"name": failed_name, "pass": False},
            ],
        }
        self.assertTrue(runner._recoverable_instrument_failure(admitted))
        rejected = copy.deepcopy(admitted)
        rejected["adapter_rejected"] = 1
        self.assertFalse(runner._recoverable_instrument_failure(rejected))
        rejected = copy.deepcopy(admitted)
        rejected["checks"].append({"name": "another", "pass": False})
        self.assertFalse(runner._recoverable_instrument_failure(rejected))

    def test_external_rate_limit_requires_all_terminal_markers(self) -> None:
        stream = "".join(
            (
                '"status":"rejected"',
                '"rateLimitType":"five_hour"',
                '"error":"rate_limit"',
                '"api_error_status":429',
            )
        )
        self.assertTrue(runner._verified_external_rate_limit(stream))
        self.assertFalse(
            runner._verified_external_rate_limit(
                stream.replace('"api_error_status":429', "")
            )
        )

    def test_prestart_audit_refuses_after_arm_start_before_write(self) -> None:
        state = {
            "arms": {
                arm: {
                    "status": (
                        "complete" if arm == "D" else "admitted_not_run"
                    )
                }
                for arm in runner.ORDER
            }
        }
        with (
            mock.patch.object(
                runner,
                "load_state",
                return_value=(
                    runner.Path("master"),
                    runner.Path("state.json"),
                    state,
                ),
            ),
            mock.patch.object(runner, "write_json") as write_json,
            mock.patch.object(runner, "docker") as docker,
        ):
            with self.assertRaises(SystemExit):
                runner.audit_resources("master")
        write_json.assert_not_called()
        docker.assert_not_called()

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

    def test_producer_and_scorer_models_are_separated(self) -> None:
        self.assertEqual(runner.PRODUCER_MODEL, "sonnet")
        self.assertEqual(runner.SCORER_MODEL, "haiku")
        self.assertNotEqual(runner.PRODUCER_MODEL, runner.SCORER_MODEL)

    def test_normal_and_terminal_timeout_are_scorable_outcomes(self) -> None:
        self.assertTrue(runner._arm_has_scorable_outcome({"status": "complete"}))
        self.assertTrue(
            runner._arm_has_scorable_outcome(
                {"status": "terminal_timeout_complete"}
            )
        )
        self.assertFalse(
            runner._arm_has_scorable_outcome({"status": "failed_timeout"})
        )

    def test_recovery_order_skips_terminal_timeout_outcome(self) -> None:
        state = {
            "arms": {
                "D": {"status": "terminal_timeout_complete"},
                "C": {"status": "failed_exit_1"},
                "A": {"status": "admitted_not_run"},
                "B": {"status": "admitted_not_run"},
            }
        }
        self.assertEqual(runner._next_arm_requiring_outcome(state), "C")

    def test_timeout_amendment_manifest_verifies_exact_files(self) -> None:
        digest = runner.verify_timeout_amendment()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_windows_timeout_kills_tree_before_pipe_collection(self) -> None:
        events: list[str] = []

        class FakeProcess:
            pid = 4242
            returncode = None
            calls = 0

            def communicate(self, **kwargs: object) -> tuple[bytes, bytes]:
                self.calls += 1
                if self.calls == 1:
                    events.append("timeout")
                    raise runner.subprocess.TimeoutExpired("claude", 1800)
                events.append("collect")
                self.returncode = 1
                return b"stdout", b"stderr"

            def poll(self) -> int | None:
                return self.returncode

            def kill(self) -> None:
                events.append("fallback-kill")
                self.returncode = 1

        def taskkill(*args: object, **kwargs: object) -> object:
            events.append("taskkill-tree")
            return runner.subprocess.CompletedProcess(
                ["taskkill"], 0, b"", b""
            )

        with (
            mock.patch.object(runner.os, "name", "nt"),
            mock.patch.object(runner.subprocess, "Popen", return_value=FakeProcess()),
            mock.patch.object(runner.subprocess, "run", side_effect=taskkill),
        ):
            completed, stdout, stderr, receipt = runner._run_formal_model(
                ["claude.cmd"], prompt=b"prompt", project=runner.Path(".")
            )
        self.assertIsNone(completed)
        self.assertEqual(stdout, b"stdout")
        self.assertEqual(stderr, b"stderr")
        self.assertEqual(events, ["timeout", "taskkill-tree", "collect"])
        self.assertEqual(receipt["termination_method"], "windows_taskkill_tree")
        self.assertTrue(receipt["process_tree_terminated"])
        self.assertTrue(receipt["stdout_pipe_closed"])


if __name__ == "__main__":
    unittest.main()
