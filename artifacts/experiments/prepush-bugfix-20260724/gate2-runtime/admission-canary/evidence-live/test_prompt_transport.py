#!/usr/bin/env python3
"""Regression tests for frozen-prompt transport and session identity."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from prompt_identity_check import _first_user_text, compare
from prompt_transport_preflight import inspect_prompt


class TransportPreflight(unittest.TestCase):
    def test_bom_free_unicode_prompt_is_go(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = os.path.join(td, "prompt.txt")
            raw = "adapter — byte exact\n".encode("utf-8")
            with open(prompt, "wb") as handle:
                handle.write(raw)
            result = inspect_prompt(prompt)
        self.assertEqual(result["status"], "GO")
        self.assertTrue(result["utf8_valid"])
        self.assertFalse(result["utf8_bom"])
        self.assertEqual(result["prompt_bytes"], len(raw))
        self.assertEqual(result["non_ascii_codepoints"], 1)

    def test_utf8_bom_is_no_go(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = os.path.join(td, "prompt.txt")
            with open(prompt, "wb") as handle:
                handle.write(b"\xef\xbb\xbftext\n")
            result = inspect_prompt(prompt)
        self.assertEqual(result["status"], "NO-GO")
        self.assertTrue(result["utf8_bom"])

    def test_invalid_utf8_is_no_go(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = os.path.join(td, "prompt.txt")
            with open(prompt, "wb") as handle:
                handle.write(b"text\xff\n")
            result = inspect_prompt(prompt)
        self.assertEqual(result["status"], "NO-GO")
        self.assertFalse(result["utf8_valid"])


class SessionIdentity(unittest.TestCase):
    def _write_session(self, path: str, text: str) -> None:
        rows = [
            {"type": "queue-operation", "operation": "enqueue", "content": text},
            {
                "type": "user",
                "message": {"role": "user", "content": text},
                "sessionId": "test-session",
            },
        ]
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_exact_session_message_is_go(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = os.path.join(td, "prompt.txt")
            session = os.path.join(td, "session.jsonl")
            text = "adapter — byte exact\n"
            with open(prompt, "wb") as handle:
                handle.write(text.encode("utf-8"))
            self._write_session(session, text)
            result = compare(prompt, session)
        self.assertEqual(result["status"], "GO")
        self.assertTrue(result["exact_prompt_match"])
        self.assertIsNone(result["first_difference"])

    def test_reencoded_session_message_is_no_go(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = os.path.join(td, "prompt.txt")
            session = os.path.join(td, "session.jsonl")
            with open(prompt, "wb") as handle:
                handle.write("adapter — byte exact\n".encode("utf-8"))
            self._write_session(session, "adapter ? byte exact\n\r\n")
            result = compare(prompt, session)
        self.assertEqual(result["status"], "NO-GO")
        self.assertFalse(result["exact_prompt_match"])
        self.assertEqual(
            result["first_difference"],
            {
                "index": 8,
                "expected_codepoint": "U+2014",
                "actual_codepoint": "U+003F",
            },
        )

    def test_partial_trailing_jsonl_line_is_not_treated_as_identity(self):
        with tempfile.TemporaryDirectory() as td:
            session = os.path.join(td, "session.jsonl")
            with open(session, "w", encoding="utf-8", newline="\n") as handle:
                handle.write('{"type":"queue-operation"}\n')
                handle.write('{"type":"user","message":')
            self.assertEqual(_first_user_text(session), (None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
