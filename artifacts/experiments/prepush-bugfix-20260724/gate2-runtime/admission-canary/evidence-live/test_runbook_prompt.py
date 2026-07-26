#!/usr/bin/env python3
"""Regression tests for the producer-facing prompt in the live runbook."""
from __future__ import annotations

import os
import re
import unittest


RUNBOOK = os.path.join(os.path.dirname(__file__), "RUNBOOK.md")


def producer_prompt() -> str:
    with open(RUNBOOK, encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r"(?ms)^> You are working.*?^> describes\.\s*$", text)
    if not match:
        raise AssertionError("Step 2 producer prompt not found")
    lines = []
    for line in match.group(0).splitlines():
        if line == ">":
            lines.append("")
        elif line.startswith("> "):
            lines.append(line[2:])
        else:
            raise AssertionError(f"unexpected prompt line: {line!r}")
    return "\n".join(lines) + "\n"


class OutcomeLevelPrompt(unittest.TestCase):
    def test_prompt_requests_outcomes_without_prescribing_tool_call_shape(self):
        prompt = producer_prompt()
        self.assertIn("understand the task and current behaviour", prompt)
        self.assertIn("examined all three inputs", prompt)
        self.assertNotIn("first assistant response", prompt)
        self.assertNotIn("exactly three", prompt)
        self.assertNotIn("tool-use blocks", prompt)
        self.assertNotIn("Do not emit text between them", prompt)

    def test_runbook_records_batch_without_making_absence_a_no_go(self):
        with open(RUNBOOK, encoding="utf-8") as handle:
            text = handle.read()
        normalized = " ".join(text.split())
        self.assertIn("`UNOBSERVED` is also a valid measurement", normalized)
        self.assertIn("must not abort or alter the producer task", normalized)
        self.assertNotIn(
            "three nominally grouped reads were actually three separate",
            normalized,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
