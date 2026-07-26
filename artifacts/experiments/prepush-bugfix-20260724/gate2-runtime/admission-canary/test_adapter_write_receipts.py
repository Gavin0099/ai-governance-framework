#!/usr/bin/env python3
"""Regression tests for byte-attested writes and immutable reports."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest
from unittest import mock

import canary_adapter as adapter


class WriteReceipts(unittest.TestCase):
    def test_short_payloads_are_still_redacted_from_adapter_log_summaries(self):
        summary = adapter.summarise("write", ["src/x.py", "YQ=="])
        self.assertEqual(summary[0], "src/x.py")
        self.assertRegex(summary[1], r"^<b64 len=4 sha256=[0-9a-f]{16}>$")
        report_summary = adapter.summarise("report", ["e30="])
        self.assertRegex(report_summary[0], r"^<b64 len=4 sha256=[0-9a-f]{16}>$")

    def _docker_for(self, stored: bytes):
        digest = hashlib.sha256(stored).hexdigest()

        def fake(argv, stdin=None):
            if argv[:2] == ["cp", "/dev/stdin"]:
                return 0, ""
            if argv[0] == "sha256sum":
                return 0, f"{digest}  {argv[1]}\n"
            if argv[:2] == ["wc", "-c"]:
                return 0, f"{len(stored)} {argv[2]}\n"
            raise AssertionError(argv)

        return fake

    def test_write_receipt_attests_exact_submitted_bytes(self):
        content = b"alpha\nbeta\n"
        with mock.patch.object(adapter, "docker", self._docker_for(content)):
            rc, out = adapter.write_file(
                "/work/repo/src/x.py",
                base64.b64encode(content).decode(),
                receipt_target="repo:src/x.py",
            )
        receipt = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["bytes"], len(content))
        self.assertEqual(receipt["sha256"], hashlib.sha256(content).hexdigest())
        self.assertTrue(receipt["content_matches_request"])
        self.assertTrue(receipt["written"])

    def test_storage_mismatch_is_a_nonzero_exit(self):
        requested = b"alpha\nbeta\n"
        stored = b"alpha\nbet\n"
        with mock.patch.object(adapter, "docker", self._docker_for(stored)):
            rc, out = adapter.write_file(
                "/work/repo/src/x.py",
                base64.b64encode(requested).decode(),
                receipt_target="repo:src/x.py",
            )
        receipt = json.loads(out)
        self.assertEqual(rc, 3)
        self.assertFalse(receipt["content_matches_request"])

    def test_report_refuses_to_overwrite_an_existing_artifact(self):
        calls = []

        def fake(argv, stdin=None):
            calls.append((argv, stdin))
            if argv[:2] == ["test", "-e"]:
                return 0, ""
            raise AssertionError("report must stop before cp")

        with mock.patch.object(adapter, "docker", fake):
            rc, out = adapter.write_file(
                "/work/out/result.json",
                base64.b64encode(b'{"status":"pass"}').decode(),
                receipt_target="out:result.json",
                overwrite=False,
            )
        receipt = json.loads(out)
        self.assertEqual(rc, 3)
        self.assertFalse(receipt["written"])
        self.assertIn("immutable", receipt["error"])
        self.assertEqual(len(calls), 1)

    def test_first_report_is_attested(self):
        content = b'{"status":"pass"}'
        base_fake = self._docker_for(content)

        def fake(argv, stdin=None):
            if argv[:2] == ["test", "-e"]:
                return 1, ""
            return base_fake(argv, stdin)

        with mock.patch.object(adapter, "docker", fake):
            rc, out = adapter.write_file(
                "/work/out/result.json",
                base64.b64encode(content).decode(),
                receipt_target="out:result.json",
                overwrite=False,
            )
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(out)["content_matches_request"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
