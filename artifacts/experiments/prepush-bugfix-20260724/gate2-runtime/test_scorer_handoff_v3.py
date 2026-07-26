#!/usr/bin/env python3
"""Fail-closed tests for the scorer-handoff v3 candidate."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_ROOT = os.path.dirname(HERE)
if EXPERIMENT_ROOT not in sys.path:
    sys.path.insert(0, EXPERIMENT_ROOT)

import redaction_runner as R
import scorer_handoff_v3 as H
import scorer_packet_v2 as P
from test_scorer_packet_v2 import (
    BASELINE,
    CONTAINER_ID,
    OUTPUT,
    RUN_ID,
    build_valid,
    valid_state,
)


CONTRACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "candidate",
    "scorer-handoff-contract-v3.json",
)
CANDIDATE_MANIFEST = os.path.join(
    os.path.dirname(CONTRACT),
    "scorer-handoff-v3-candidate-manifest.json",
)


class ScorerHandoffV3Tests(unittest.TestCase):
    def prepare_sources(self, directory: str):
        packet_dir = os.path.join(directory, "source-packet")
        files, packet = build_valid()
        packet_path = P.publish_packet(packet_dir, files, packet)
        test_log = os.path.join(directory, "test.log")
        validator = os.path.join(directory, "validator.log")
        with open(test_log, "wb") as handle:
            handle.write(b"3 passed\n")
        with open(validator, "wb") as handle:
            handle.write(b"shellcheck=1 ruff=1 mypy=0\n")
        return packet_path, test_log, validator

    def build(self, directory: str):
        packet_path, test_log, validator = self.prepare_sources(directory)
        outputs, manifest = H.build_handoff(
            contract_path=CONTRACT,
            scorer_packet_path=packet_path,
            expected_run_id=RUN_ID,
            expected_baseline_commit=BASELINE,
            expected_output_commit=OUTPUT,
            expected_container_id=CONTAINER_ID,
            observed_state=valid_state(),
            test_log_path=test_log,
            validator_output_path=validator,
        )
        out_dir = os.path.join(directory, "handoff")
        manifest_path = H.publish_handoff(out_dir, outputs, manifest)
        return packet_path, manifest_path, outputs, manifest

    def verify(self, packet_path: str, manifest_path: str, **overrides):
        with open(packet_path, "rb") as handle:
            packet_sha = P.sha256(handle.read())
        values = {
            "contract_path": CONTRACT,
            "expected_run_id": RUN_ID,
            "expected_baseline_commit": BASELINE,
            "expected_output_commit": OUTPUT,
            "expected_container_id": CONTAINER_ID,
            "expected_scorer_packet_sha256": packet_sha,
        }
        values.update(overrides)
        return H.verify_handoff(manifest_path, **values)

    def test_live_verified_packet_builds_complete_four_section_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, outputs, manifest = self.build(directory)
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("PASS", result["status"])
            self.assertTrue(all(result["checks"].values()))

            packet = json.loads(outputs["redacted-packet.json"])
            sections = R.parse_canonical(
                packet["redacted_output"].encode("utf-8")
            )
            self.assertIn("return a+b", sections["FIX_DIFF"])
            self.assertIn("3 passed", sections["TEST_LOG"])
            self.assertIn("shellcheck=1", sections["VALIDATOR_OUTPUT"])
            self.assertIn('"summary":"fixed add"', sections["COMPLETION_CLAIM"])
            self.assertEqual(H.SECTION_SOURCES, manifest["section_mapping"])

    def test_receipt_is_anonymized_and_bound_to_output_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, outputs, _ = self.build(directory)
            receipt = json.loads(outputs["redacted-receipt.json"])
            self.assertNotIn("arm", receipt)
            self.assertEqual(OUTPUT, receipt["source_output_commit"])
            self.assertRegex(receipt["anon_id"], r"^OUT-[0-9a-f]{12}$")

    def test_missing_or_empty_attachment_is_rejected_without_outputs(self):
        for case in ("missing_test", "empty_validator"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                packet_path, test_log, validator = self.prepare_sources(directory)
                if case == "missing_test":
                    os.unlink(test_log)
                else:
                    open(validator, "wb").close()
                with self.assertRaises(H.HandoffError):
                    H.build_handoff(
                        contract_path=CONTRACT,
                        scorer_packet_path=packet_path,
                        expected_run_id=RUN_ID,
                        expected_baseline_commit=BASELINE,
                        expected_output_commit=OUTPUT,
                        expected_container_id=CONTAINER_ID,
                        observed_state=valid_state(),
                        test_log_path=test_log,
                        validator_output_path=validator,
                    )
                self.assertFalse(os.path.exists(os.path.join(directory, "handoff")))

    def test_reserved_marker_or_cr_in_attachment_is_rejected(self):
        bad_payloads = (
            b"ok\r\n",
            b"before\n=== VALIDATOR_OUTPUT ===\nafter\n",
        )
        for payload in bad_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                packet_path, test_log, validator = self.prepare_sources(directory)
                with open(test_log, "wb") as handle:
                    handle.write(payload)
                with self.assertRaises(H.HandoffError):
                    H.build_handoff(
                        contract_path=CONTRACT,
                        scorer_packet_path=packet_path,
                        expected_run_id=RUN_ID,
                        expected_baseline_commit=BASELINE,
                        expected_output_commit=OUTPUT,
                        expected_container_id=CONTAINER_ID,
                        observed_state=valid_state(),
                        test_log_path=test_log,
                        validator_output_path=validator,
                    )

    def test_tampered_source_packet_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, test_log, validator = self.prepare_sources(directory)
            source_diff = os.path.join(os.path.dirname(packet_path), "final-diff.patch")
            with open(source_diff, "ab") as handle:
                handle.write(b"tamper\n")
            with self.assertRaisesRegex(H.HandoffError, "failed live verification"):
                H.build_handoff(
                    contract_path=CONTRACT,
                    scorer_packet_path=packet_path,
                    expected_run_id=RUN_ID,
                    expected_baseline_commit=BASELINE,
                    expected_output_commit=OUTPUT,
                    expected_container_id=CONTAINER_ID,
                    observed_state=valid_state(),
                    test_log_path=test_log,
                    validator_output_path=validator,
                )

    def test_wrong_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, test_log, validator = self.prepare_sources(directory)
            with self.assertRaisesRegex(H.HandoffError, "failed live verification"):
                H.build_handoff(
                    contract_path=CONTRACT,
                    scorer_packet_path=packet_path,
                    expected_run_id="wrong",
                    expected_baseline_commit=BASELINE,
                    expected_output_commit=OUTPUT,
                    expected_container_id=CONTAINER_ID,
                    observed_state=valid_state(),
                    test_log_path=test_log,
                    validator_output_path=validator,
                )

    def test_candidate_contract_cannot_masquerade_as_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(CONTRACT, encoding="utf-8") as handle:
                contract = json.load(handle)
            contract["frozen"] = True
            path = os.path.join(directory, "bad-contract.json")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(contract, handle)
            packet_path, test_log, validator = self.prepare_sources(directory)
            with self.assertRaisesRegex(H.HandoffError, "frozen=false"):
                H.build_handoff(
                    contract_path=path,
                    scorer_packet_path=packet_path,
                    expected_run_id=RUN_ID,
                    expected_baseline_commit=BASELINE,
                    expected_output_commit=OUTPUT,
                    expected_container_id=CONTAINER_ID,
                    observed_state=valid_state(),
                    test_log_path=test_log,
                    validator_output_path=validator,
                )

    def test_missing_or_tampered_published_output_fails_verification(self):
        for key, filename in H.OUTPUT_FILES.items():
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                packet_path, manifest_path, _, _ = self.build(directory)
                path = os.path.join(os.path.dirname(manifest_path), filename)
                if key == "packet":
                    with open(path, "ab") as handle:
                        handle.write(b"tamper")
                else:
                    os.unlink(path)
                result = self.verify(packet_path, manifest_path)
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    not result["checks"]["all_outputs_exist"]
                    or not result["checks"]["output_digests_match"]
                )

    def test_manifest_source_identity_or_packet_digest_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            manifest["source_identity"]["output_commit"] = "d" * 40
            manifest["source_artifacts"]["scorer_packet"]["sha256"] = "0" * 64
            with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest, handle)
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["source_identity_matches"])
            self.assertFalse(result["checks"]["source_packet_digest_matches"])

    def test_coherent_output_rewrite_still_fails_contract_and_commit_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            base = os.path.dirname(manifest_path)
            redacted_packet_path = os.path.join(base, "redacted-packet.json")
            receipt_path = os.path.join(base, "redacted-receipt.json")
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            with open(redacted_packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            with open(receipt_path, encoding="utf-8") as handle:
                receipt = json.load(handle)
            packet["contract_sha256"] = "0" * 64
            receipt["source_output_commit"] = "d" * 40
            packet_bytes = P._json_bytes(packet)
            receipt_bytes = P._json_bytes(receipt)
            with open(redacted_packet_path, "wb") as handle:
                handle.write(packet_bytes)
            with open(receipt_path, "wb") as handle:
                handle.write(receipt_bytes)
            manifest["packet_sha256"] = P.sha256(packet_bytes)
            manifest["receipt_sha256"] = P.sha256(receipt_bytes)
            with open(manifest_path, "wb") as handle:
                handle.write(P._json_bytes(manifest))
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["packet_contract_digest_matches"])
            self.assertFalse(result["checks"]["receipt_output_commit_matches"])

    def test_coherent_source_artifact_omission_fails_exact_set_check(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            base = os.path.dirname(manifest_path)
            redacted_packet_path = os.path.join(base, "redacted-packet.json")
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            with open(redacted_packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            del manifest["source_artifacts"]["validator_output"]
            del packet["source_attestation"]["artifacts"]["validator_output"]
            packet_bytes = P._json_bytes(packet)
            with open(redacted_packet_path, "wb") as handle:
                handle.write(packet_bytes)
            manifest["packet_sha256"] = P.sha256(packet_bytes)
            with open(manifest_path, "wb") as handle:
                handle.write(P._json_bytes(manifest))
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["source_artifact_set_is_exact"])

    def test_publish_failure_removes_every_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, test_log, validator = self.prepare_sources(directory)
            outputs, manifest = H.build_handoff(
                contract_path=CONTRACT,
                scorer_packet_path=packet_path,
                expected_run_id=RUN_ID,
                expected_baseline_commit=BASELINE,
                expected_output_commit=OUTPUT,
                expected_container_id=CONTAINER_ID,
                observed_state=valid_state(),
                test_log_path=test_log,
                validator_output_path=validator,
            )
            out_dir = os.path.join(directory, "handoff")
            calls = 0

            def failing_writer(path: str, payload: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated publish failure")
                P.atomic_write_bytes(path, payload)

            with self.assertRaisesRegex(OSError, "simulated"):
                H.publish_handoff(out_dir, outputs, manifest, writer=failing_writer)
            self.assertEqual([], os.listdir(out_dir))

    def test_handoff_is_create_once(self):
        with tempfile.TemporaryDirectory() as directory:
            _, manifest_path, outputs, manifest = self.build(directory)
            with self.assertRaises(FileExistsError):
                H.publish_handoff(
                    os.path.dirname(manifest_path), outputs, manifest
                )

    def test_exact_candidate_manifest_passes_and_tamper_or_omission_fails(self):
        result = H.verify_candidate_manifest(
            CANDIDATE_MANIFEST,
            repo_root=os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))
                        )
                    )
                )
            ),
        )
        self.assertEqual("PASS", result["status"])

        with open(CANDIDATE_MANIFEST, encoding="utf-8") as handle:
            manifest = json.load(handle)
        source_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )
        )
        for mode in ("tamper", "missing"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                for item in manifest["files"]:
                    source = os.path.join(source_root, *item["path"].split("/"))
                    destination = os.path.join(root, *item["path"].split("/"))
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    shutil.copyfile(source, destination)
                manifest_path = os.path.join(root, "candidate-manifest.json")
                with open(manifest_path, "wb") as handle:
                    handle.write(P._json_bytes(manifest))
                target = os.path.join(
                    root, *manifest["files"][1]["path"].split("/")
                )
                if mode == "tamper":
                    with open(target, "ab") as handle:
                        handle.write(b"tamper")
                else:
                    os.unlink(target)
                result = H.verify_candidate_manifest(
                    manifest_path, repo_root=root
                )
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    not result["checks"]["candidate_paths_are_confined_regular_files"]
                    or not result["checks"]["candidate_byte_counts_match"]
                    or not result["checks"]["candidate_digests_match"]
                )


if __name__ == "__main__":
    unittest.main()
