#!/usr/bin/env python3
"""Regression tests for the live multi-tool request observation."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from batch_request_check import inspect


def assistant(message_id: str, count: int) -> dict:
    return {
        "type": "assistant",
        "message": {
            "id": message_id,
            "content": [
                {"type": "tool_use", "id": f"tool-{message_id}-{i}", "name": "Bash"}
                for i in range(count)
            ],
        },
    }


class BatchObservation(unittest.TestCase):
    def _inspect(self, rows):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "session.jsonl")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")
            return inspect(path)

    def test_three_separate_messages_are_not_a_batch(self):
        result = self._inspect([
            assistant("one", 1),
            assistant("two", 1),
            assistant("three", 1),
        ])
        self.assertEqual(result["status"], "UNOBSERVED")
        self.assertFalse(result["multi_tool_message_observed"])
        self.assertEqual(result["max_tool_calls_in_one_message"], 1)
        self.assertIn("does not prove harness serialization", result["claim_boundary"])

    def test_one_message_with_three_tools_is_a_batch(self):
        result = self._inspect([assistant("batch", 3)])
        self.assertEqual(result["status"], "OBSERVED")
        self.assertTrue(result["multi_tool_message_observed"])
        self.assertEqual(result["max_tool_calls_in_one_message"], 3)

    def test_repeated_stream_rows_are_deduplicated_by_tool_id(self):
        row = assistant("batch", 2)
        result = self._inspect([row, row])
        self.assertEqual(result["max_tool_calls_in_one_message"], 2)

    def test_cli_unobserved_is_a_successful_measurement(self):
        with tempfile.TemporaryDirectory() as td:
            session = os.path.join(td, "session.jsonl")
            output = os.path.join(td, "batch.json")
            with open(session, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(assistant("one", 1)) + "\n")
            completed = subprocess.run(
                [
                    sys.executable,
                    os.path.join(os.path.dirname(__file__), "batch_request_check.py"),
                    "--session-log",
                    session,
                    "--out",
                    output,
                    "--wait-seconds",
                    "0",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with open(output, encoding="utf-8") as handle:
                result = json.load(handle)
            self.assertEqual(result["status"], "UNOBSERVED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
