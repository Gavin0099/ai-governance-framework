#!/usr/bin/env python3
"""Regression tests for the live multi-tool request observation."""
from __future__ import annotations

import json
import os
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
        self.assertEqual(result["status"], "NO-GO")
        self.assertFalse(result["multi_tool_message_observed"])
        self.assertEqual(result["max_tool_calls_in_one_message"], 1)

    def test_one_message_with_three_tools_is_a_batch(self):
        result = self._inspect([assistant("batch", 3)])
        self.assertEqual(result["status"], "GO")
        self.assertTrue(result["multi_tool_message_observed"])
        self.assertEqual(result["max_tool_calls_in_one_message"], 3)

    def test_repeated_stream_rows_are_deduplicated_by_tool_id(self):
        row = assistant("batch", 2)
        result = self._inspect([row, row])
        self.assertEqual(result["max_tool_calls_in_one_message"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
