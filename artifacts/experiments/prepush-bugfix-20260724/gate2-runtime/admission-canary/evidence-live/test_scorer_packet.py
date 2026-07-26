#!/usr/bin/env python3
"""Counter-examples for operator-owned blind-scorer packets."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from capture_scorer_packet import build_packet, write_packet
from evidence_io import atomic_write_bytes
from verify_scorer_packet import verify


RUN_ID = "live-canary-test"
HEAD = "a" * 40
CONTAINER_ID = "container-id"
RESULT = b'{"change":"fixed add","tests":"3 passed"}\n'
DIFF = (
    b"diff --git a/src/calc.py b/src/calc.py\n"
    b"index c299416..af626eb 100644\n"
    b"--- a/src/calc.py\n"
    b"+++ b/src/calc.py\n"
    b"@@ -1,6 +1,3 @@\n"
    b'-\"\"\"Tiny arithmetic helpers.\"\"\"\n'
    b"-def add(a, b): return -1\n"
    b"+def add(a, b): return a + b\n"
)
STATUS = b" M src/calc.py\n?? src/__pycache__/calc.pyc\n"
TRACKED = b"src/calc.py\n"


def fixture(**overrides):
    values = {
        "run_id": RUN_ID,
        "container_name": RUN_ID,
        "container_id": CONTAINER_ID,
        "baseline_head": HEAD,
        "result_bytes": RESULT,
        "diff_bytes": DIFF,
        "status_bytes": STATUS,
        "tracked_paths_bytes": TRACKED,
        "captured_at": "2026-07-26T12:00:00Z",
    }
    values.update(overrides)
    return build_packet(**values)


def write_fixture(directory: str, **overrides) -> str:
    files, packet = fixture(**overrides)
    return write_packet(directory, files, packet)


class ScorerPacketHappyPath(unittest.TestCase):
    def test_packet_preserves_collateral_change_omitted_by_result(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(td)
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "PASS")
            self.assertNotIn(b"docstring", RESULT)
            self.assertIn(b'Tiny arithmetic helpers', DIFF)

    def test_binary_diff_path_is_preserved_and_verified(self):
        binary_diff = (
            b"diff --git a/assets/blob.bin b/assets/blob.bin\n"
            b"index 1111111..2222222 100644\n"
            b"Binary files a/assets/blob.bin and b/assets/blob.bin differ\n"
        )
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(
                td,
                diff_bytes=binary_diff,
                status_bytes=b" M assets/blob.bin\n",
                tracked_paths_bytes=b"assets/blob.bin\n",
            )
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "PASS")


class ScorerPacketFailsClosed(unittest.TestCase):
    def test_each_artifact_tamper_breaks_digest_verification(self):
        artifact_names = [
            "result.json",
            "final-diff.patch",
            "final-status.txt",
            "final-tracked-paths.txt",
        ]
        for name in artifact_names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                packet_path = write_fixture(td)
                with open(os.path.join(td, name), "ab") as handle:
                    handle.write(b"tamper")
                outcome = verify(
                    packet_path,
                    expected_run_id=RUN_ID,
                    expected_head=HEAD,
                    expected_container_id=CONTAINER_ID,
                )
                self.assertEqual(outcome["status"], "FAIL")
                self.assertFalse(outcome["checks"]["artifact_digests_match"])

    def test_missing_artifact_fails(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(td)
            os.remove(os.path.join(td, "final-diff.patch"))
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "FAIL")
            self.assertFalse(outcome["checks"]["all_artifacts_exist"])

    def test_manifest_artifact_omission_fails(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(td)
            with open(packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            del packet["artifacts"]["diff"]
            atomic_write_bytes(
                packet_path,
                (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode(),
            )
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "FAIL")
            self.assertFalse(
                outcome["checks"]["required_artifact_set_is_exact"]
            )

    def test_manifest_digest_tamper_fails(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(td)
            with open(packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            packet["artifacts"]["diff"]["sha256"] = "0" * 64
            atomic_write_bytes(
                packet_path,
                (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode(),
            )
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "FAIL")
            self.assertFalse(outcome["checks"]["artifact_digests_match"])

    def test_wrong_run_or_head_fails(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = write_fixture(td)
            outcome = verify(
                packet_path,
                expected_run_id="other",
                expected_head="b" * 40,
                expected_container_id="other-container",
            )
            self.assertEqual(outcome["status"], "FAIL")
            self.assertFalse(outcome["checks"]["run_id_matches"])
            self.assertFalse(outcome["checks"]["baseline_head_matches"])
            self.assertFalse(outcome["checks"]["container_id_matches"])

    def test_partial_manifest_is_not_a_valid_packet(self):
        with tempfile.TemporaryDirectory() as td:
            packet_path = os.path.join(td, "scorer-packet.json")
            atomic_write_bytes(packet_path, b'{"schema_version":')
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "FAIL")
            self.assertFalse(outcome["checks"]["packet_is_valid_json_object"])

    def test_manifest_is_written_last_and_failure_leaves_no_packet(self):
        with tempfile.TemporaryDirectory() as td:
            files, packet = fixture()

            def fail_on_manifest(path: str, payload: bytes) -> None:
                if os.path.basename(path) == "scorer-packet.json":
                    raise OSError("simulated manifest write failure")
                atomic_write_bytes(path, payload)

            with self.assertRaisesRegex(OSError, "simulated"):
                write_packet(td, files, packet, writer=fail_on_manifest)
            packet_path = os.path.join(td, "scorer-packet.json")
            self.assertFalse(os.path.exists(packet_path))
            outcome = verify(
                packet_path,
                expected_run_id=RUN_ID,
                expected_head=HEAD,
                expected_container_id=CONTAINER_ID,
            )
            self.assertEqual(outcome["status"], "FAIL")

    def test_capture_is_create_once(self):
        with tempfile.TemporaryDirectory() as td:
            write_fixture(td)
            with self.assertRaises(FileExistsError):
                write_fixture(td)

    def test_empty_or_omitted_tracked_diff_is_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, "final diff is empty"):
            fixture(diff_bytes=b"")
        with self.assertRaisesRegex(ValueError, "omits tracked changed file"):
            fixture(diff_bytes=b"diff --git a/other b/other\n")
        with self.assertRaisesRegex(ValueError, "no tracked changed file"):
            fixture(status_bytes=b"", tracked_paths_bytes=b"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
