#!/usr/bin/env python3
"""Regression checks for the live-run preflight's shared-observable gate."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "preflight_check.py")
POLICY = {"policy_id": "admission-canary-1", "policy_sha256": "p" * 64}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


class SharedObservablePreflight(unittest.TestCase):
    def _run(self, terminal_stdout: str, adapter_stdout: str, verb: str = "read"):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = os.path.join(tmp, "transcript.jsonl")
            adapter_log = os.path.join(tmp, "adapter-log.jsonl")
            deny_evidence = os.path.join(tmp, "deny.jsonl")
            args = ["TASK.md"] if verb == "read" else ["src/calc.py", "YQ=="]
            args_digest = sha("\x00".join(args))
            pre = {
                "event": "pre_tool_use", "tool_use_id": "toolu_live",
                "decision": "allow", "verb": verb, "args_sha256": args_digest,
                **POLICY,
            }
            term = {
                "event": "post_tool_use", "tool_use_id": "toolu_live",
                "stdout_sha256": sha(terminal_stdout),
            }
            adapter = {
                "seq": 1, "decision": "executed", "verb": verb,
                "args_sha256": args_digest, "exit": 0,
                "stdout_sha256": sha(adapter_stdout), **POLICY,
            }
            denied = {
                "event": "pre_tool_use", "tool_use_id": "toolu_denied",
                "decision": "deny", "reason": "outside adapter channel",
            }
            write_jsonl(transcript, [pre, term])
            write_jsonl(adapter_log, [adapter])
            write_jsonl(deny_evidence, [denied])
            return subprocess.run(
                [
                    sys.executable, SCRIPT,
                    "--transcript", transcript,
                    "--adapter-log", adapter_log,
                    "--deny-evidence", deny_evidence,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

    def test_multiline_digest_mismatch_is_no_go(self):
        cp = self._run("first\r\nsecond", "first\nsecond")
        self.assertEqual(cp.returncode, 1, cp.stdout)
        self.assertIn(
            "[FAIL] a natural output-bearing call has the same shared observable on both sides",
            cp.stdout,
        )
        self.assertIn("NO-GO", cp.stdout)

    def test_byte_exact_multiline_digest_is_go(self):
        cp = self._run("first\nsecond", "first\nsecond")
        self.assertEqual(cp.returncode, 0, cp.stdout)
        self.assertIn(
            "[PASS] a natural output-bearing call has the same shared observable on both sides",
            cp.stdout,
        )
        self.assertIn("GO -- all 14 checks passed", cp.stdout)

    def test_single_line_write_cannot_make_observable_gate_vacuously_pass(self):
        cp = self._run("ok", "ok", verb="write")
        self.assertEqual(cp.returncode, 1, cp.stdout)
        self.assertIn("no completed read/ls/test/diff/status call", cp.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
