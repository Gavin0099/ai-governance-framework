#!/usr/bin/env python3
"""Regression tests for scorer-artifact detail in operator snapshots."""
from __future__ import annotations

import unittest
from unittest import mock

import workspace_snapshot as snapshot


class OutputArtifactSnapshot(unittest.TestCase):
    def test_result_records_digest_bytes_text_and_parsed_json(self):
        responses = {
            "sha256sum": (0, "abc123  /work/out/result.json"),
            "wc": (0, "18 /work/out/result.json"),
            "cat": (0, '{"status":"pass"}'),
        }

        def fake(argv, workdir="/work/repo"):
            return responses[argv[0]]

        with mock.patch.object(snapshot, "dexec", fake):
            result = snapshot.collect_out_artifacts(["result.json"])
        artifact = result["result.json"]
        self.assertEqual(artifact["sha256"], "abc123")
        self.assertEqual(artifact["bytes"], 18)
        self.assertEqual(artifact["parsed_json"], {"status": "pass"})
        self.assertEqual(artifact["utf8_text_trimmed"], '{"status":"pass"}')

    def test_non_json_output_is_recorded_without_false_parse_claim(self):
        def fake(argv, workdir="/work/repo"):
            return {
                "sha256sum": (0, "def456  /work/out/note.txt"),
                "wc": (0, "4 /work/out/note.txt"),
                "cat": (0, "note"),
            }[argv[0]]

        with mock.patch.object(snapshot, "dexec", fake):
            result = snapshot.collect_out_artifacts(["note.txt"])
        self.assertIsNone(result["note.txt"]["parsed_json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
