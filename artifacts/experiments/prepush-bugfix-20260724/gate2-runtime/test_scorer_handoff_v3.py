#!/usr/bin/env python3
"""Fail-closed tests for the scorer-handoff v3 candidate."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
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

    def build(
        self,
        directory: str,
        *,
        blinding_compromised_reason: str | None = None,
    ):
        packet_path, test_log, validator = self.prepare_sources(directory)
        blinding_args = {}
        if blinding_compromised_reason is not None:
            blinding_args["blinding_compromised_reason"] = (
                blinding_compromised_reason
            )
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
            **blinding_args,
        )
        out_dir = os.path.join(directory, "handoff")
        manifest_path = H.publish_handoff(out_dir, outputs, manifest)
        return packet_path, manifest_path, outputs, manifest

    def verify(self, packet_path: str, manifest_path: str, **overrides):
        with open(packet_path, "rb") as handle:
            packet_sha = P.sha256(handle.read())
        source_root = os.path.dirname(os.path.dirname(manifest_path))
        values = {
            "contract_path": CONTRACT,
            "scorer_packet_path": packet_path,
            "test_log_path": os.path.join(source_root, "test.log"),
            "validator_output_path": os.path.join(
                source_root, "validator.log"
            ),
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

    def test_coherent_fix_diff_rewrite_is_rejected_by_source_reproduction(self):
        """A self-consistent published set must still bind to the pinned source."""
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

            packet["redacted_output"] = packet["redacted_output"].replace(
                "return a+b", "return forged"
            )
            packet["redacted_output_sha256"] = P.sha256(
                packet["redacted_output"].encode("utf-8")
            )
            packet["raw_output_sha256"] = "f" * 64
            forged_anon = "OUT-" + ("f" * 12)
            packet["anon_id"] = forged_anon
            receipt["anon_id"] = forged_anon
            manifest["anon_id"] = forged_anon

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
            self.assertFalse(
                result["checks"]["published_packet_matches_source_rebuild"]
            )

    def test_source_attachment_tamper_after_publish_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            with open(os.path.join(directory, "test.log"), "ab") as handle:
                handle.write(b"forged later line\n")
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(
                result["checks"]["published_packet_matches_source_rebuild"]
            )
            self.assertFalse(
                result["checks"]["source_artifacts_match_rebuild"]
            )

    def test_offline_rebuild_rejects_semantically_contradictory_source_packet(self):
        """Digest-consistent source bytes must still satisfy packet semantics."""
        with tempfile.TemporaryDirectory() as directory:
            packet_path, test_log, validator = self.prepare_sources(directory)
            packet_dir = os.path.dirname(packet_path)
            tracked_payload = b"never_touched.py\n"
            tracked_path = os.path.join(
                packet_dir, P.ARTIFACT_FILES["tracked_paths"]
            )
            with open(tracked_path, "wb") as handle:
                handle.write(tracked_payload)
            with open(packet_path, encoding="utf-8") as handle:
                packet = json.load(handle)
            packet["artifacts"]["tracked_paths"]["bytes"] = len(tracked_payload)
            packet["artifacts"]["tracked_paths"]["sha256"] = P.sha256(
                tracked_payload
            )
            packet["workspace"]["tracked_changed_files"] = [
                "completely_different.py"
            ]
            packet["scorer_input_core"] = ["diff"]
            with open(packet_path, "wb") as handle:
                handle.write(P._json_bytes(packet))

            with open(packet_path, "rb") as handle:
                packet_bytes = handle.read()
            payloads, artifact_checks, artifact_errors = P._read_packet_artifacts(
                packet_path, packet
            )
            self.assertTrue(all(artifact_checks.values()), artifact_errors)
            with open(CONTRACT, "rb") as handle:
                contract_bytes = handle.read()
            contract = json.loads(contract_bytes)
            with open(test_log, "rb") as handle:
                test_log_bytes = handle.read()
            with open(validator, "rb") as handle:
                validator_output_bytes = handle.read()
            outputs, manifest = H._assemble_handoff(
                contract_bytes=contract_bytes,
                contract=contract,
                packet_manifest_bytes=packet_bytes,
                packet_payloads=payloads,
                test_log_bytes=test_log_bytes,
                validator_output_bytes=validator_output_bytes,
                source_identity={
                    "run_id": RUN_ID,
                    "baseline_commit": BASELINE,
                    "output_commit": OUTPUT,
                    "container_id": CONTAINER_ID,
                },
            )
            manifest_path = H.publish_handoff(
                os.path.join(directory, "handoff"), outputs, manifest
            )

            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["source_rebuild_inputs_are_valid"])
            errors = " ".join(result["errors"])
            for name in (
                "tracked_inventory_matches_diff",
                "manifest_inventory_matches_captured_files",
                "core_scorer_inputs_are_exact",
            ):
                self.assertIn(name, errors)

    def test_flagged_blinding_reason_rebuilds_and_mismatch_fails(self):
        reason = (
            "arm C treatment assignment leaked via "
            "governance-packet.md path in claim"
        )
        redacted_reason = (
            "[ARM] [ASSIGNMENT] leaked via [PACKET] path in claim"
        )
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, outputs, _ = self.build(
                directory, blinding_compromised_reason=reason
            )
            packet = json.loads(outputs["redacted-packet.json"])
            self.assertIs(packet["blinding_compromised"], True)
            self.assertEqual(
                redacted_reason, packet["blinding_compromised_reason"]
            )
            self.assertNotIn(reason, outputs["redacted-packet.json"].decode("utf-8"))
            self.assertEqual(
                3, packet["total_blinding_reason_redactions"]
            )
            self.assertEqual(
                3,
                sum(
                    packet[
                        "blinding_compromised_reason_per_rule_match_count"
                    ].values()
                ),
            )

            matching = self.verify(
                packet_path,
                manifest_path,
                blinding_compromised_reason=reason,
            )
            self.assertEqual("PASS", matching["status"])
            self.assertTrue(all(matching["checks"].values()))

            missing = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", missing["status"])
            self.assertFalse(
                missing["checks"]["published_packet_matches_source_rebuild"]
            )

            mismatched = self.verify(
                packet_path,
                manifest_path,
                blinding_compromised_reason="different reason",
            )
            self.assertEqual("FAIL", mismatched["status"])
            self.assertFalse(
                mismatched["checks"]["blinding_and_channel_fields_match_contract"]
            )

            with open(packet_path, "rb") as handle:
                packet_sha = P.sha256(handle.read())
            json_out = os.path.join(directory, "flagged-verification.json")
            completed = subprocess.run(
                [
                    sys.executable,
                    H.__file__,
                    "verify",
                    "--manifest",
                    manifest_path,
                    "--contract",
                    CONTRACT,
                    "--scorer-packet",
                    packet_path,
                    "--test-log",
                    os.path.join(directory, "test.log"),
                    "--validator-output",
                    os.path.join(directory, "validator.log"),
                    "--expected-run-id",
                    RUN_ID,
                    "--expected-baseline-commit",
                    BASELINE,
                    "--expected-output-commit",
                    OUTPUT,
                    "--expected-container-id",
                    CONTAINER_ID,
                    "--expected-scorer-packet-sha256",
                    packet_sha,
                    "--blinding-compromised-reason",
                    reason,
                    "--json-out",
                    json_out,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            with open(json_out, encoding="utf-8") as handle:
                cli_result = json.load(handle)
            self.assertEqual("PASS", cli_result["status"])

            with self.assertRaisesRegex(H.HandoffError, "non-blank"):
                self.build(
                    os.path.join(directory, "blank"),
                    blinding_compromised_reason="  ",
                )

    def test_candidate_rejects_shipped_smoke_contract_digest_mismatch(self):
        source_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )
        )
        with open(CANDIDATE_MANIFEST, encoding="utf-8") as handle:
            manifest = json.load(handle)
        for item in manifest["files"]:
            path = os.path.join(source_root, *item["path"].split("/"))
            with open(path, "rb") as handle:
                payload = handle.read()
            item["bytes"] = len(payload)
            item["sha256"] = P.sha256(payload)
        manifest["shipped_smoke"] = {
            "scope": "fresh synthetic Docker integration; not a Gate 2 arm",
            "contract_sha256": "0" * 64,
            "handoff_manifest_path": (
                "artifacts/evidence/test-results/"
                "gate2-scorer-handoff-v3-rebuild-smoke-20260726/"
                "scorer-handoff-v3/scorer-handoff-v3.json"
            ),
            "verification_path": (
                "artifacts/evidence/test-results/"
                "gate2-scorer-handoff-v3-rebuild-smoke-20260726/"
                "scorer-handoff-verification.json"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = os.path.join(directory, "candidate-manifest.json")
            with open(manifest_path, "wb") as handle:
                handle.write(P._json_bytes(manifest))
            result = H.verify_candidate_manifest(
                manifest_path, repo_root=source_root
            )
        self.assertEqual("FAIL", result["status"])
        self.assertFalse(
            result["checks"][
                "shipped_smoke_contract_digest_matches_candidate"
            ]
        )

    def test_cli_verify_rebuilds_from_explicit_source_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            with open(packet_path, "rb") as handle:
                packet_sha = P.sha256(handle.read())
            json_out = os.path.join(directory, "verification.json")
            command = [
                sys.executable,
                H.__file__,
                "verify",
                "--manifest",
                manifest_path,
                "--contract",
                CONTRACT,
                "--scorer-packet",
                packet_path,
                "--test-log",
                os.path.join(directory, "test.log"),
                "--validator-output",
                os.path.join(directory, "validator.log"),
                "--expected-run-id",
                RUN_ID,
                "--expected-baseline-commit",
                BASELINE,
                "--expected-output-commit",
                OUTPUT,
                "--expected-container-id",
                CONTAINER_ID,
                "--expected-scorer-packet-sha256",
                packet_sha,
                "--json-out",
                json_out,
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            with open(json_out, encoding="utf-8") as handle:
                result = json.load(handle)
            self.assertEqual("PASS", result["status"])
            self.assertTrue(
                result["checks"]["published_packet_matches_source_rebuild"]
            )
            self.assertTrue(
                result["checks"]["published_receipt_matches_source_rebuild"]
            )

    def test_coherent_completion_claim_rewrite_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            packet_path, manifest_path, _, _ = self.build(directory)
            base = os.path.dirname(manifest_path)
            packet_path_out = os.path.join(base, "redacted-packet.json")
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            with open(packet_path_out, encoding="utf-8") as handle:
                packet = json.load(handle)
            packet["redacted_output"] = packet["redacted_output"].replace(
                '"summary":"fixed add"', '"summary":"forged claim"'
            )
            packet["redacted_output_sha256"] = P.sha256(
                packet["redacted_output"].encode("utf-8")
            )
            packet_bytes = P._json_bytes(packet)
            with open(packet_path_out, "wb") as handle:
                handle.write(packet_bytes)
            manifest["packet_sha256"] = P.sha256(packet_bytes)
            with open(manifest_path, "wb") as handle:
                handle.write(P._json_bytes(manifest))
            result = self.verify(packet_path, manifest_path)
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(
                result["checks"]["published_packet_matches_source_rebuild"]
            )

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
        with open(CANDIDATE_MANIFEST, encoding="utf-8") as handle:
            declared = json.load(handle)
        declared_paths = {item["path"] for item in declared["files"]}
        self.assertIn(
            "artifacts/experiments/prepush-bugfix-20260724/redaction_runner.py",
            declared_paths,
        )

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
        self.assertTrue(result["checks"]["canonical_file_set_is_exact"])
        self.assertTrue(result["checks"]["canonical_digests_match"])
        self.assertTrue(result["checks"]["byte_preservation_attributes_are_complete"])

        manifest = declared
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
                for item in (
                    manifest["files"]
                    + manifest["shipped_smoke"]["files"]
                ):
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

        with tempfile.TemporaryDirectory() as root:
            for item in (
                manifest["files"]
                + manifest["shipped_smoke"]["files"]
            ):
                source = os.path.join(source_root, *item["path"].split("/"))
                destination = os.path.join(root, *item["path"].split("/"))
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copyfile(source, destination)
            for relative in H.CANONICAL_FILES:
                source = os.path.join(source_root, *relative.split("/"))
                destination = os.path.join(root, *relative.split("/"))
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copyfile(source, destination)
            manifest_path = os.path.join(root, "candidate-manifest.json")
            with open(manifest_path, "wb") as handle:
                handle.write(P._json_bytes(manifest))
            canonical_target = os.path.join(
                root, *next(iter(H.CANONICAL_FILES)).split("/")
            )
            with open(canonical_target, "ab") as handle:
                handle.write(b"tamper")
            result = H.verify_candidate_manifest(
                manifest_path, repo_root=root
            )
            self.assertEqual("FAIL", result["status"])
            self.assertFalse(result["checks"]["canonical_digests_match"])


if __name__ == "__main__":
    unittest.main()
