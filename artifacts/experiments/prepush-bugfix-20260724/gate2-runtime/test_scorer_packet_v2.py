#!/usr/bin/env python3
"""Counter-example tests for commit-bound scorer-packet schema v2."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from unittest import mock

import scorer_packet_v2 as P


BASELINE = "a" * 40
OUTPUT = "b" * 40
CONTAINER_ID = "c" * 64
RUN_ID = "gate2-arm-A"
RECEIPT_PATH = P.DEFAULT_RECEIPT_CONTAINER_PATH
RESULT = b'{"status":"pass","summary":"fixed add"}\n'
DIFF = (
    b"diff --git a/src/calc.py b/src/calc.py\n"
    b"index 1111111..2222222 100644\n"
    b"--- a/src/calc.py\n"
    b"+++ b/src/calc.py\n"
    b"@@ -1 +1 @@\n"
    b"-return a-b\n"
    b"+return a+b\n"
)
PATHS = b"src/calc.py\n"


def receipt_bytes(linked_commit: str = OUTPUT) -> bytes:
    return (
        json.dumps(
            {
                "receipt_schema": "test_evidence_receipt.v0.1",
                "arm": "A",
                "linked_commit": linked_commit,
                "exit_code": 0,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def valid_state() -> dict:
    return {
        "container_name": "gate2-arm-A",
        "container_id": CONTAINER_ID,
        "baseline_commit": BASELINE,
        "output_commit": OUTPUT,
        "receipt_container_path": RECEIPT_PATH,
        "result_bytes": RESULT,
        "diff_bytes": DIFF,
        "status_bytes": b"",
        "tracked_paths_bytes": PATHS,
        "receipt_bytes": receipt_bytes(),
    }


def build_valid():
    return P.build_packet(
        run_id=RUN_ID,
        captured_at="2026-07-26T20:00:00Z",
        **valid_state(),
    )


class ScorerPacketV2Tests(unittest.TestCase):
    def publish_valid(self, directory: str):
        files, packet = build_valid()
        path = P.publish_packet(directory, files, packet)
        return path, packet

    def verify(self, packet_path: str, observed=None):
        return P.verify_packet(
            packet_path,
            expected_run_id=RUN_ID,
            expected_baseline_commit=BASELINE,
            expected_output_commit=OUTPUT,
            expected_container_id=CONTAINER_ID,
            observed_state=valid_state() if observed is None else observed,
        )

    def test_clean_commit_packet_and_live_binding_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, packet = self.publish_valid(directory)
            result = self.verify(packet_path)
            self.assertEqual("PASS", result["status"])
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(BASELINE, packet["baseline_commit"])
            self.assertEqual(OUTPUT, packet["output_commit"])

    def test_dirty_worktree_is_rejected_before_publish(self):
        state = valid_state()
        state["status_bytes"] = b" M src/calc.py\n"
        with self.assertRaisesRegex(ValueError, "dirty"):
            P.build_packet(
                run_id=RUN_ID,
                captured_at="2026-07-26T20:00:00Z",
                **state,
            )

    def test_receipt_linked_commit_mismatch_is_rejected(self):
        state = valid_state()
        state["receipt_bytes"] = receipt_bytes("d" * 40)
        with self.assertRaisesRegex(ValueError, "linked_commit"):
            P.build_packet(
                run_id=RUN_ID,
                captured_at="2026-07-26T20:00:00Z",
                **state,
            )

    def test_abbreviated_commit_or_noncanonical_receipt_path_is_rejected(self):
        mutations = (
            ("baseline_commit", BASELINE[:8]),
            ("output_commit", OUTPUT[:8]),
            ("container_id", CONTAINER_ID[:12]),
            ("receipt_container_path", "/tmp/receipt.json"),
        )
        for key, value in mutations:
            state = valid_state()
            state[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                P.build_packet(
                    run_id=RUN_ID,
                    captured_at="2026-07-26T20:00:00Z",
                    **state,
                )

    def test_empty_or_incomplete_diff_is_rejected(self):
        for diff in (b"", b"diff --git a/other.py b/other.py\n"):
            state = valid_state()
            state["diff_bytes"] = diff
            with self.subTest(diff=diff), self.assertRaises(ValueError):
                P.build_packet(
                    run_id=RUN_ID,
                    captured_at="2026-07-26T20:00:00Z",
                    **state,
                )

    def test_missing_or_tampered_artifact_fails(self):
        for key, filename in P.ARTIFACT_FILES.items():
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                packet_path, _ = self.publish_valid(directory)
                path = os.path.join(directory, filename)
                if key == "status":
                    os.unlink(path)
                else:
                    with open(path, "ab") as handle:
                        handle.write(b"tamper")
                result = self.verify(packet_path)
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    not result["checks"]["all_artifacts_exist"]
                    or not result["checks"]["artifact_digests_match"]
                )

    def test_manifest_identity_or_digest_tampering_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, _ = self.publish_valid(directory)
            with open(packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            packet["output_commit"] = "d" * 40
            packet["artifacts"]["diff"]["sha256"] = "0" * 64
            with open(packet_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(packet, handle)
            result = self.verify(packet_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["output_commit_matches"])
            self.assertFalse(result["checks"]["artifact_digests_match"])

    def test_wrong_expected_identity_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, _ = self.publish_valid(directory)
            result = P.verify_packet(
                packet_path,
                expected_run_id="wrong-run",
                expected_baseline_commit="d" * 40,
                expected_output_commit="e" * 40,
                expected_container_id="f" * 64,
                observed_state=valid_state(),
            )
            self.assertEqual("FAIL", result["status"])
            for check in (
                "run_id_matches",
                "baseline_commit_matches",
                "output_commit_matches",
                "container_id_matches",
            ):
                self.assertFalse(result["checks"][check])

    def test_live_container_byte_or_identity_mismatch_fails(self):
        mutations = (
            ("container_id", "d" * 64),
            ("output_commit", "e" * 40),
            ("diff_bytes", DIFF + b"tamper\n"),
            ("receipt_bytes", receipt_bytes("f" * 40)),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                packet_path, _ = self.publish_valid(directory)
                observed = copy.deepcopy(valid_state())
                observed[key] = value
                result = self.verify(packet_path, observed)
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    not result["checks"]["live_container_identity_matches"]
                    or not result["checks"]["live_commit_identity_matches"]
                    or not result["checks"]["live_artifact_bytes_match"]
                )

    def test_container_capture_uses_baseline_to_output_commit_diff(self):
        calls = []

        def fake_run(argv):
            if argv[:3] == ["docker", "inspect", "-f"]:
                return (
                    (CONTAINER_ID + "\n").encode("ascii")
                    if argv[3] == "{{.Id}}"
                    else b"running\n"
                )
            raise AssertionError(argv)

        def fake_exec(container, argv, *, workdir):
            calls.append((container, argv, workdir))
            if argv == ["git", "rev-parse", "HEAD"]:
                return (OUTPUT + "\n").encode("ascii")
            if argv[:2] == ["git", "cat-file"]:
                return b""
            if argv[:2] == ["git", "merge-base"]:
                return b""
            if argv == ["cat", "/work/out/result.json"]:
                return RESULT
            if argv[:2] == ["git", "diff"] and "--name-only" not in argv:
                self.assertIn(BASELINE, argv)
                self.assertIn(OUTPUT, argv)
                return DIFF
            if argv[:3] == ["git", "status", "--porcelain=v1"]:
                return b""
            if argv[:3] == ["git", "diff", "--name-only"]:
                self.assertIn(BASELINE, argv)
                self.assertIn(OUTPUT, argv)
                return PATHS
            if argv == ["cat", RECEIPT_PATH]:
                return receipt_bytes()
            raise AssertionError(argv)

        with mock.patch.object(P, "run_bytes", side_effect=fake_run), mock.patch.object(
            P, "docker_exec", side_effect=fake_exec
        ):
            state = P.capture_container_state(
                container=RUN_ID,
                baseline_commit=BASELINE,
                receipt_container_path=RECEIPT_PATH,
            )
        self.assertEqual(OUTPUT, state["output_commit"])
        self.assertEqual(DIFF, state["diff_bytes"])
        self.assertTrue(
            any(
                argv[:2] == ["git", "merge-base"]
                and argv[-2:] == [BASELINE, OUTPUT]
                for _, argv, _ in calls
            )
        )

    def test_container_capture_propagates_ancestry_failure(self):
        def fake_run(argv):
            return (
                (CONTAINER_ID + "\n").encode("ascii")
                if argv[3] == "{{.Id}}"
                else b"running\n"
            )

        def fake_exec(container, argv, *, workdir):
            if argv == ["git", "rev-parse", "HEAD"]:
                return (OUTPUT + "\n").encode("ascii")
            if argv[:2] == ["git", "cat-file"]:
                return b""
            if argv[:2] == ["git", "merge-base"]:
                raise RuntimeError("not an ancestor")
            raise AssertionError(argv)

        with mock.patch.object(P, "run_bytes", side_effect=fake_run), mock.patch.object(
            P, "docker_exec", side_effect=fake_exec
        ), self.assertRaisesRegex(RuntimeError, "ancestor"):
            P.capture_container_state(
                container=RUN_ID,
                baseline_commit=BASELINE,
                receipt_container_path=RECEIPT_PATH,
            )

    def test_verification_without_live_binding_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, _ = self.publish_valid(directory)
            result = P.verify_packet(
                packet_path,
                expected_run_id=RUN_ID,
                expected_baseline_commit=BASELINE,
                expected_output_commit=OUTPUT,
                expected_container_id=CONTAINER_ID,
                observed_state=None,
            )
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["live_container_binding_present"])

    def test_publish_failure_removes_every_partial_output(self):
        files, packet = build_valid()
        with tempfile.TemporaryDirectory() as directory:
            calls = 0

            def failing_writer(path: str, payload: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("simulated write failure")
                P.atomic_write_bytes(path, payload)

            with self.assertRaisesRegex(OSError, "simulated"):
                P.publish_packet(directory, files, packet, writer=failing_writer)
            self.assertEqual([], os.listdir(directory))

    def test_packet_is_create_once(self):
        with tempfile.TemporaryDirectory() as directory:
            self.publish_valid(directory)
            files, packet = build_valid()
            with self.assertRaises(FileExistsError):
                P.publish_packet(directory, files, packet)


if __name__ == "__main__":
    unittest.main()
