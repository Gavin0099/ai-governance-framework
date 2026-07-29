from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
MODULE_PATH = HERE / "gate3_common_harness.py"
SPEC = importlib.util.spec_from_file_location("gate3_common_harness", MODULE_PATH)
assert SPEC and SPEC.loader
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(harness._json_bytes(value))


class Gate3CommonHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.class_temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.class_temp.name)
        cls.canonical = cls.root / "canonical-rehearsal"
        cls.result = harness.build_rehearsal(
            ROOT,
            cls.canonical,
            nonce_hex="ab" * 32,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.class_temp.cleanup()

    def copy_case(self, name: str) -> Path:
        case = self.root / name
        shutil.copytree(self.canonical, case)
        return case

    def refresh_inventory(self, case: Path, relative: str) -> dict[str, object]:
        summary_path = case / "rehearsal-summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        path = case.joinpath(*relative.split("/"))
        entry = next(
            item
            for item in summary["artifact_inventory"]
            if item["path"] == relative
        )
        raw = path.read_bytes()
        entry["bytes"] = len(raw)
        entry["sha256"] = digest(raw)
        write_json(summary_path, summary)
        return summary

    def test_fresh_rehearsal_builds_two_outcomes_and_full_chain(self) -> None:
        self.assertEqual(self.result["status"], "PASS")
        self.assertEqual(self.result["outcome_count"], 2)
        self.assertEqual(self.result["event_count"], 7)
        self.assertEqual(
            self.result["candidate_manifest_sha256"],
            harness.EXPECTED_CANDIDATE_MANIFEST_SHA256,
        )
        verified = harness.verify_rehearsal(ROOT, self.canonical)
        self.assertEqual(verified["checks"]["chain"], "PASS")
        self.assertEqual(
            verified["checks"]["baseline_failure_receipt"], "PASS"
        )
        self.assertEqual(
            verified["checks"]["structured_write_receipts"], "PASS"
        )
        baseline = json.loads(
            (self.canonical / "baseline-test-receipt.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotEqual(baseline["exit_code"], 0)
        for treatment in ("a", "b"):
            final_receipt = json.loads(
                (
                    self.canonical
                    / f"outcomes/{treatment}/test-receipt.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(final_receipt["exit_code"], 0)

    @unittest.skipUnless(sys.platform == "win32", "Windows ACL regression")
    def test_published_directory_inherits_parent_acl_on_windows(self) -> None:
        env = dict(os.environ)
        env["GATE3_ACL_PATH"] = str(self.canonical)
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    "(Get-Acl -LiteralPath "
                    "$env:GATE3_ACL_PATH).AreAccessRulesProtected"
                ),
            ],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), "False")

    def test_structured_write_returns_exact_stored_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            evidence = root / "evidence"
            repo.mkdir()
            evidence.mkdir()
            receipt = evidence / "write-receipt.json"
            payload = b"byte-exact payload\n"
            result = harness.structured_write(
                repo, "nested/value.txt", payload, receipt, evidence
            )
            self.assertTrue(result["match"])
            self.assertEqual(result["stored_bytes"], len(payload))
            self.assertEqual(result["stored_sha256"], digest(payload))
            self.assertEqual(
                (repo / "nested/value.txt").read_bytes(), payload
            )

    def test_structured_write_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            evidence = root / "evidence"
            repo.mkdir()
            evidence.mkdir()
            with self.assertRaisesRegex(harness.HarnessError, "safe relative"):
                harness.structured_write(
                    repo,
                    "../escape.txt",
                    b"escape\n",
                    evidence / "receipt.json",
                    evidence,
                )

    def test_existing_output_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(harness.HarnessError, "already exists"):
            harness.build_rehearsal(
                ROOT,
                self.canonical,
                nonce_hex="ab" * 32,
            )

    def test_retained_input_mutation_is_rejected_even_if_inventory_updates(
        self,
    ) -> None:
        case = self.copy_case("mutated-input")
        relative = "inputs/task-packet.txt"
        path = case / relative
        path.write_bytes(path.read_bytes() + b"tampered\n")
        self.refresh_inventory(case, relative)
        with self.assertRaisesRegex(
            harness.chain.EvidenceError, "retained input artifact"
        ):
            harness.verify_rehearsal(ROOT, case)

    def test_mapping_mutation_is_rejected_even_if_inventory_updates(self) -> None:
        case = self.copy_case("mutated-mapping")
        relative = "mapping-reveal.json"
        path = case / relative
        mapping = json.loads(path.read_text(encoding="utf-8"))
        mapping["mapping"] = {
            "OUT-111111111111": "B",
            "OUT-222222222222": "A",
        }
        write_json(path, mapping)
        self.refresh_inventory(case, relative)
        with self.assertRaisesRegex(
            harness.chain.EvidenceError, "mapping digest mismatch"
        ):
            harness.verify_rehearsal(ROOT, case)

    def test_missing_receipt_is_rejected(self) -> None:
        case = self.copy_case("missing-receipt")
        (case / "outcomes/a/test-receipt.json").unlink()
        with self.assertRaisesRegex(harness.HarnessError, "inventory mismatch"):
            harness.verify_rehearsal(ROOT, case)

    def test_structured_write_receipt_cannot_relabel_bundled_bytes(self) -> None:
        case = self.copy_case("mutated-write-receipt")
        relative = "outcomes/a/structured-write-receipt.json"
        receipt_path = case / relative
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        false_payload = b"def add(a, b):\n    return 999\n"
        receipt["requested_bytes"] = len(false_payload)
        receipt["stored_bytes"] = len(false_payload)
        receipt["requested_sha256"] = digest(false_payload)
        receipt["stored_sha256"] = digest(false_payload)
        write_json(receipt_path, receipt)
        summary = self.refresh_inventory(case, relative)
        outcome = next(
            item
            for item in summary["outcomes"]
            if item["treatment"] == "A"
        )
        outcome["write_receipt_sha256"] = digest(receipt_path.read_bytes())
        write_json(case / "rehearsal-summary.json", summary)
        with self.assertRaisesRegex(
            harness.HarnessError, "does not match bundled output"
        ):
            harness.verify_rehearsal(ROOT, case)

    def test_capture_receipt_cannot_relabel_baseline_commit(self) -> None:
        case = self.copy_case("mutated-capture-receipt")
        relative = "outcomes/a/live-capture-receipt.json"
        receipt_path = case / relative
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["baseline_commit"] = "f" * 40
        write_json(receipt_path, receipt)
        summary = self.refresh_inventory(case, relative)
        outcome = next(
            item
            for item in summary["outcomes"]
            if item["treatment"] == "A"
        )
        outcome["capture_receipt"]["sha256"] = digest(
            receipt_path.read_bytes()
        )
        write_json(case / "rehearsal-summary.json", summary)
        with self.assertRaisesRegex(
            harness.HarnessError, "live capture receipt is invalid"
        ):
            harness.verify_rehearsal(ROOT, case)

    def test_baseline_failure_receipt_cannot_be_relabelled_as_pass(self) -> None:
        case = self.copy_case("mutated-baseline-receipt")
        relative = "baseline-test-receipt.json"
        receipt_path = case / relative
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["exit_code"] = 0
        write_json(receipt_path, receipt)
        summary = self.refresh_inventory(case, relative)
        summary["baseline_test_receipt"]["sha256"] = digest(
            receipt_path.read_bytes()
        )
        write_json(case / "rehearsal-summary.json", summary)
        with self.assertRaisesRegex(
            harness.HarnessError, "baseline test receipt is invalid"
        ):
            harness.verify_rehearsal(ROOT, case)

    def test_candidate_manifest_identity_is_unchanged(self) -> None:
        manifest = (
            ROOT
            / "artifacts/experiments/prepush-bugfix-20260724/candidate"
            / "gate3-preregistration-amendment-v1-candidate-manifest.json"
        )
        self.assertEqual(
            digest(manifest.read_bytes()),
            harness.EXPECTED_CANDIDATE_MANIFEST_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
