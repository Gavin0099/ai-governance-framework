#!/usr/bin/env python3
"""Focused fail-closed tests for the experiment-local Gate 2 arm adapter."""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "producer-guard"))

import gate2_arm_adapter as arm  # noqa: E402
from gate2_policy import load_policy  # noqa: E402


POLICY = os.path.join(HERE, "policy_gate2_arm.json")
POLICY_D = os.path.join(HERE, "policy_gate2_arm_d.json")


class PolicyTests(unittest.TestCase):
    def test_policy_and_execution_tables_match(self) -> None:
        policy = load_policy(POLICY)
        expected = {
            name: entry[0] for name, entry in arm.base.EXEC.items()
        }
        actual = {
            name: len(spec) for name, spec in policy.verbs.items()
        }
        self.assertEqual(actual, expected)

    def test_write_scope_is_narrow(self) -> None:
        policy = load_policy(POLICY)
        valid = "QQ=="
        for path in (
            "scripts/hooks/pre-push",
            "governance_tools/version_bump_guard.py",
            "tests/test_version_bump_guard.py",
        ):
            self.assertTrue(policy.check("write", [path, valid])[0], path)
        for path in (
            "PLAN.md",
            "memory/2026-07-27.md",
            "scripts/run-runtime-governance.sh",
            "../outside.py",
            ".git/config",
        ):
            self.assertFalse(policy.check("write", [path, valid])[0], path)

    def test_fixed_mechanics_reject_arguments(self) -> None:
        policy = load_policy(POLICY)
        self.assertTrue(policy.check("reproduce", [])[0])
        self.assertTrue(policy.check("commit", [])[0])
        self.assertFalse(policy.check("reproduce", ["HEAD"])[0])
        self.assertFalse(policy.check("commit", ["--amend"])[0])

    def test_test_uses_only_the_fixed_offline_payload(self) -> None:
        with mock.patch.object(arm, "_run", return_value=(0, "4 passed")) as run:
            rc, rendered = arm.run_tests([])
        self.assertEqual((rc, rendered), (0, "4 passed"))
        self.assertEqual(
            run.call_args.args[0],
            [
                "env",
                "PYTHONDONTWRITEBYTECODE=1",
                f"PYTHONPATH={arm.PYTEST_PAYLOAD}:{arm.base.REPO}",
                "python",
                "-m",
                "pytest",
                "-q",
                "tests",
            ],
        )

    def test_arm_d_policy_adds_only_the_validator_treatment(self) -> None:
        common = load_policy(POLICY)
        arm_d = load_policy(POLICY_D)
        self.assertEqual(set(arm_d.verbs) - set(common.verbs), {"validate"})
        self.assertEqual(
            {name: spec for name, spec in arm_d.verbs.items() if name != "validate"},
            common.verbs,
        )

    def test_input_reads_are_routed_outside_the_repo(self) -> None:
        with mock.patch.object(arm, "_run", return_value=(0, "packet")) as run:
            self.assertEqual(arm.read_file(["input/TASK.md"]), (0, "packet"))
        self.assertEqual(run.call_args.args[0], ["cat", "/work/input/TASK.md"])

    def test_validator_feedback_preserves_each_exit(self) -> None:
        with mock.patch.object(
            arm,
            "_run",
            side_effect=[(1, "SC1090\n"), (1, "I001\nE501\n"), (0, "Success\n")],
        ):
            rc, rendered = arm.run_validators([])
        self.assertEqual(rc, 0)
        self.assertIn("[shellcheck exit=1]\nSC1090", rendered)
        self.assertIn("[ruff exit=1]\nI001\nE501", rendered)
        self.assertIn("[mypy exit=0]\nSuccess", rendered)


class ReproductionTests(unittest.TestCase):
    @staticmethod
    def sequence(final_output: str) -> list[tuple[int, str]]:
        return [
            (0, ""),
            (0, "a" * 40 + "\n"),
            (0, ""),
            (0, ""),
            (0, "b" * 40 + "\n"),
            (0, ""),
            (0, ""),
            (0, "c" * 40 + "\n"),
            (0, "d" * 40 + "\n"),
            (0, ""),
            (0, final_output),
        ]

    def test_reproduction_pass_requires_count_and_marker(self) -> None:
        output = (
            "[version_bump_guard]\nchanged_files=1\n[files]\n"
            + arm.MARKER_PATH
        )
        with mock.patch.object(arm, "_run", side_effect=self.sequence(output)):
            rc, rendered = arm.reproduce([])
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(rendered.split("[gate2_reproduction]\n", 1)[1])["verdict"],
            "PASS",
        )

    def test_reproduction_fails_on_historical_zero(self) -> None:
        output = "[version_bump_guard]\nchanged_files=0"
        with mock.patch.object(arm, "_run", side_effect=self.sequence(output)):
            rc, rendered = arm.reproduce([])
        self.assertEqual(rc, 1)
        self.assertEqual(
            json.loads(rendered.split("[gate2_reproduction]\n", 1)[1])["verdict"],
            "FAIL",
        )


class CommitTests(unittest.TestCase):
    def test_commit_receipt_is_create_once_and_bound(self) -> None:
        responses = [
            (1, ""),
            (0, ""),
            (1, ""),
            (0, "[main abc] Gate 2 producer output"),
            (0, "1" * 40 + "\n"),
            (0, "2" * 40 + "\n"),
            (0, "scripts/hooks/pre-push\ntests/test_version_bump_guard.py\n"),
            (0, ""),
            (0, ""),
        ]
        with mock.patch.object(arm, "_run", side_effect=responses) as run:
            rc, rendered = arm.commit_output([])
        self.assertEqual(rc, 0)
        receipt = json.loads(rendered)
        self.assertEqual(receipt["linked_commit"], "1" * 40)
        self.assertEqual(receipt["tree"], "2" * 40)
        self.assertTrue(receipt["status_clean"])
        written = run.call_args_list[-1]
        self.assertEqual(written.args[0], ["cp", "/dev/stdin", arm.COMMIT_RECEIPT])
        self.assertIn(b'"linked_commit": "1111', written.kwargs["stdin"])

    def test_second_commit_is_rejected(self) -> None:
        with mock.patch.object(arm, "_run", return_value=(0, "")):
            rc, rendered = arm.commit_output([])
        self.assertEqual(rc, 3)
        self.assertIn("already exists", rendered)

    def test_empty_commit_is_rejected(self) -> None:
        with mock.patch.object(
            arm, "_run", side_effect=[(1, ""), (0, ""), (0, "")]
        ):
            rc, rendered = arm.commit_output([])
        self.assertEqual(rc, 3)
        self.assertIn("no in-scope staged change", rendered)


if __name__ == "__main__":
    unittest.main()
