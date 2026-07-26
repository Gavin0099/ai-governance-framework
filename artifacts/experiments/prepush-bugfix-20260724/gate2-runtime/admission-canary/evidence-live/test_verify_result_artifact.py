#!/usr/bin/env python3
"""Regression tests for joining report receipts to the final scorer artifact."""
from __future__ import annotations

import unittest

from verify_result_artifact import verify


def report(exit_code=0, digest="abc", size=12, written=True):
    return {
        "verb": "report",
        "decision": "executed",
        "exit": exit_code,
        "result_receipt": {
            "written": written,
            "content_matches_request": exit_code == 0,
            "sha256": digest,
            "bytes": size,
        },
    }


def snapshot(digest="abc", size=12, parsed=True):
    return {
        "work_out_artifacts": {
            "result.json": {
                "sha256": digest,
                "bytes": size,
                "parsed_json": {"status": "pass"} if parsed else None,
            },
        },
    }


class ResultReceiptVerification(unittest.TestCase):
    def test_one_matching_report_passes(self):
        result = verify([report()], snapshot())
        self.assertEqual(result["status"], "PASS")

    def test_final_artifact_digest_mismatch_fails(self):
        result = verify([report(digest="abc")], snapshot(digest="def"))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["receipt_digest_matches_final_artifact"])

    def test_two_successful_reports_fail_immutability(self):
        result = verify([report(), report()], snapshot())
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["exactly_one_successful_immutable_report"])

    def test_failed_overwrite_after_success_keeps_one_success(self):
        failed = report(exit_code=3, written=False)
        result = verify([report(), failed], snapshot())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["report_attempts"], 2)
        self.assertEqual(result["successful_reports"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
