#!/usr/bin/env python3
"""Focused tests for the Gate 2 terminal-timeout packet."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import gate2_terminal_outcome as terminal


class TerminalOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.transcript = self.root / "transcript.jsonl"
        self.adapter = self.root / "adapter-log.jsonl"
        self.stream = self.root / "claude-stream.jsonl"
        self.transcript.write_bytes(b'{"event":"tool"}\n')
        self.adapter.write_bytes(b'{"sequence":1}\n')
        self.stream.write_bytes(b'{"type":"assistant"}\n')
        self.cleanup = {
            "timeout_seconds": 1800,
            "process_pid": 4242,
            "termination_method": "windows_taskkill_tree",
            "termination_returncode": 0,
            "process_tree_terminated": True,
            "stdout_pipe_closed": True,
            "completed_at_epoch": 1785200000.0,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _build(self, *, producer_result: bytes | None = None) -> Path:
        return terminal.build_packet(
            out_dir=self.root / "packet",
            run_id="gate2-formal-opaque-OUTRUN-0123456789abcdef",
            container_id="a" * 64,
            baseline_commit="b" * 40,
            current_head="c" * 40,
            current_tree="d" * 40,
            final_diff=b"diff --git a/x b/x\n",
            final_status=b" M x\n",
            producer_result=producer_result,
            cleanup_receipt=self.cleanup,
            transcript_path=self.transcript,
            adapter_log_path=self.adapter,
            stream_path=self.stream,
        )

    def _verify(self, packet: Path) -> dict[str, object]:
        return terminal.verify_packet(
            packet_path=packet,
            expected_run_id="gate2-formal-opaque-OUTRUN-0123456789abcdef",
            expected_container_id="a" * 64,
            expected_baseline_commit="b" * 40,
            transcript_path=self.transcript,
            adapter_log_path=self.adapter,
            stream_path=self.stream,
        )

    def test_absent_producer_claim_builds_and_verifies(self) -> None:
        packet = self._build()
        result = self._verify(packet)
        self.assertEqual(result["status"], "PASS")
        value = json.loads(packet.read_text(encoding="utf-8"))
        self.assertEqual(
            value["terminal_outcome"]["producer_completion_claim"], "absent"
        )
        self.assertFalse((packet.parent / "result.json").exists())

    def test_present_producer_claim_is_preserved_and_verified(self) -> None:
        raw = b'{"summary":"partial completion claim"}\n'
        packet = self._build(producer_result=raw)
        result = self._verify(packet)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual((packet.parent / "result.json").read_bytes(), raw)

    def test_tampered_diff_fails_verification(self) -> None:
        packet = self._build()
        (packet.parent / "final-diff.patch").write_bytes(b"tampered")
        result = self._verify(packet)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["artifact_hashes"])

    def test_arm_identity_in_opaque_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            terminal.build_packet(
                out_dir=self.root / "packet",
                run_id="gate2-arm-B",
                container_id="a" * 64,
                baseline_commit="b" * 40,
                current_head="c" * 40,
                current_tree="d" * 40,
                final_diff=b"",
                final_status=b"",
                producer_result=None,
                cleanup_receipt=self.cleanup,
                transcript_path=self.transcript,
                adapter_log_path=self.adapter,
                stream_path=self.stream,
            )

    def test_missing_transcript_is_explicit_and_verifiable(self) -> None:
        self.transcript.unlink()
        packet = self._build()
        result = self._verify(packet)
        self.assertEqual(result["status"], "PASS")
        value = json.loads(packet.read_text(encoding="utf-8"))
        transcript = value["external_evidence"][0]
        self.assertEqual(
            transcript,
            {
                "name": "transcript.jsonl",
                "present": False,
                "bytes": 0,
                "sha256": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
