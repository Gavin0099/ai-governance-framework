from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENT = HERE.parent
CONTRACT = EXPERIMENT / "candidate/gate3-protocol-contract-v1.json"
MODULE_PATH = HERE / "gate3_evidence_chain.py"
SPEC = importlib.util.spec_from_file_location("gate3_evidence_chain", MODULE_PATH)
assert SPEC and SPEC.loader
chain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chain)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class Gate3EvidenceChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        self.chain_dir = self.evidence_root / "chain"
        self.packet_a = self.evidence_root / "packet-a.json"
        self.packet_b = self.evidence_root / "packet-b.json"
        self.packet_a.write_bytes(b'{"packet":"a"}\n')
        self.packet_b.write_bytes(b'{"packet":"b"}\n')
        self.metrics_a = self.evidence_root / "metrics-a.json"
        self.metrics_b = self.evidence_root / "metrics-b.json"
        write_json(
            self.metrics_a,
            self.metrics("OUT-111111111111", self.packet_a, completed=True),
        )
        write_json(
            self.metrics_b,
            self.metrics("OUT-222222222222", self.packet_b, completed=True),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def metrics(
        self, anon_id: str, packet: Path, *, completed: bool
    ) -> dict[str, object]:
        observation = {"observed": False, "evidence_sha256": []}
        return {
            "anon_id": anon_id,
            "artifacts": {
                "event_log_sha256": "a" * 64,
                "output_packet_sha256": digest(packet.read_bytes()),
            },
            "baseline_commit": "b" * 40,
            "budget_sha256": "1" * 64,
            "completed_under_cap": completed,
            "conditional_quality_eligible": completed,
            "costs": {
                "changed_files": 1,
                "diff_bytes": 42,
                "owner_interventions": 0,
                "retries": 0,
                "rework_count": 0,
                "tokens": {
                    "available": False,
                    "reason": "provider did not expose usage",
                },
                "tool_calls": 4,
                "wall_clock_ms": 1000,
            },
            "method_observations": {
                "claim_bounded_to_evidence": copy.deepcopy(observation),
                "defect_reintroduction_performed": copy.deepcopy(observation),
                "failing_regression_before_fix": copy.deepcopy(observation),
                "post_restore_retest_performed": copy.deepcopy(observation),
                "reproduction_before_first_edit": copy.deepcopy(observation),
                "root_cause_recorded_before_first_edit": copy.deepcopy(
                    observation
                ),
            },
            "harness_contract_sha256": "2" * 64,
            "model_build": "model-build-1",
            "pair_id": "task-1-pair-1",
            "permissions_sha256": "3" * 64,
            "randomization_record_sha256": "4" * 64,
            "repeat_index": 1,
            "run_id": f"run-{anon_id[-4:]}",
            "schema": "gate3-run-metrics.v1",
            "scorer_rubric_sha256": "5" * 64,
            "status": "completed" if completed else "timed_out",
            "task_id": "task-1",
            "task_packet_sha256": "6" * 64,
            "timestamps": {
                "finished_at": "2026-07-29T02:01:00+00:00",
                "first_edit_at": (
                    "2026-07-29T02:00:30+00:00" if completed else None
                ),
                "started_at": "2026-07-29T02:00:00+00:00",
            },
        }

    def score(
        self, role: str, *, timeout_b: bool = False
    ) -> dict[str, object]:
        def output(anon_id: str, completed: bool) -> dict[str, object]:
            base: dict[str, object] = {
                "anon_id": anon_id,
                "completed_under_cap": completed,
            }
            conditional = {
                "claim_mismatch_count": 0,
                "critical_residuals": 0,
                "major_residuals": 0,
                "no_new_scoped_regression": True,
                "oracle_acceptance": True,
                "original_defect_caught": True,
                "regression_baseline_fail": True,
                "regression_passes_after_fix": True,
                "scope_hygiene": "clean",
                "sensitivity_score": {"caught": 1, "total": 1},
            }
            base.update(
                conditional
                if completed
                else {key: None for key in conditional}
            )
            return base

        return {
            "outputs": [
                output("OUT-111111111111", True),
                output("OUT-222222222222", not timeout_b),
            ],
            "schema": "gate3-blind-score.v1",
            "scorer_role": role,
        }

    def seal_pair(self) -> None:
        chain.seal_outcome(
            self.chain_dir, CONTRACT, self.packet_a, self.metrics_a
        )
        chain.seal_outcome(
            self.chain_dir, CONTRACT, self.packet_b, self.metrics_b
        )
        chain.close_blind_set(
            self.chain_dir, CONTRACT, "skill_primary"
        )

    def full_chain(self) -> tuple[Path, Path, Path]:
        self.seal_pair()
        primary = self.evidence_root / "primary.json"
        second = self.evidence_root / "second.json"
        mapping = self.evidence_root / "mapping.json"
        write_json(primary, self.score("primary"))
        write_json(second, self.score("second"))
        write_json(
            mapping,
            {
                "mapping": {
                    "OUT-111111111111": "A",
                    "OUT-222222222222": "B",
                },
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )
        chain.submit_scorer(
            self.chain_dir, CONTRACT, "primary", primary
        )
        chain.submit_scorer(
            self.chain_dir, CONTRACT, "second", second
        )
        chain.release_mapping(self.chain_dir, CONTRACT, mapping)
        return primary, second, mapping

    def test_completed_and_timeout_metrics_validate(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        chain.validate_metrics(
            json.loads(self.metrics_a.read_text(encoding="utf-8")),
            contract,
            packet_sha256=digest(self.packet_a.read_bytes()),
        )
        timeout = self.metrics(
            "OUT-222222222222", self.packet_b, completed=False
        )
        chain.validate_metrics(
            timeout,
            contract,
            packet_sha256=digest(self.packet_b.read_bytes()),
        )

    def test_metrics_completion_state_disagreement_fails(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        value = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        value["status"] = "timed_out"
        with self.assertRaisesRegex(chain.EvidenceError, "disagree"):
            chain.validate_metrics(value, contract)

    def test_unavailable_tokens_require_reason(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        value = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        del value["costs"]["tokens"]["reason"]  # type: ignore[index]
        with self.assertRaisesRegex(chain.EvidenceError, "require a reason"):
            chain.validate_metrics(value, contract)

    def test_invalid_timestamp_order_fails(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        value = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        value["timestamps"]["finished_at"] = (  # type: ignore[index]
            "2026-07-29T01:59:00+00:00"
        )
        with self.assertRaisesRegex(chain.EvidenceError, "precedes"):
            chain.validate_metrics(value, contract)

    def test_observed_method_requires_digest_evidence(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        value = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        value["method_observations"][  # type: ignore[index]
            "reproduction_before_first_edit"
        ]["observed"] = True
        with self.assertRaisesRegex(chain.EvidenceError, "lacks digest"):
            chain.validate_metrics(value, contract)

    def test_packet_metrics_digest_disagreement_fails(self) -> None:
        value = json.loads(self.metrics_a.read_text(encoding="utf-8"))
        value["artifacts"]["output_packet_sha256"] = "b" * 64
        write_json(self.metrics_a, value)
        with self.assertRaisesRegex(chain.EvidenceError, "does not match"):
            chain.seal_outcome(
                self.chain_dir, CONTRACT, self.packet_a, self.metrics_a
            )

    def test_create_once_refuses_existing_event(self) -> None:
        chain.seal_outcome(
            self.chain_dir, CONTRACT, self.packet_a, self.metrics_a
        )
        first = next(self.chain_dir.iterdir())
        with self.assertRaisesRegex(chain.EvidenceError, "already exists"):
            chain._publish_create_once(first, first.read_bytes())

    def test_second_scorer_before_primary_fails(self) -> None:
        self.seal_pair()
        second = self.evidence_root / "second.json"
        write_json(second, self.score("second"))
        with self.assertRaisesRegex(chain.EvidenceError, "not allowed"):
            chain.submit_scorer(
                self.chain_dir, CONTRACT, "second", second
            )

    def test_scorer_population_mismatch_fails(self) -> None:
        self.seal_pair()
        primary = self.score("primary")
        primary["outputs"] = primary["outputs"][:1]
        path = self.evidence_root / "primary.json"
        write_json(path, primary)
        with self.assertRaisesRegex(chain.EvidenceError, "incomplete"):
            chain.submit_scorer(
                self.chain_dir, CONTRACT, "primary", path
            )

    def test_blind_set_rejects_pair_control_mismatch(self) -> None:
        value = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        value["harness_contract_sha256"] = "9" * 64
        write_json(self.metrics_b, value)
        chain.seal_outcome(
            self.chain_dir, CONTRACT, self.packet_a, self.metrics_a
        )
        chain.seal_outcome(
            self.chain_dir, CONTRACT, self.packet_b, self.metrics_b
        )
        with self.assertRaisesRegex(chain.EvidenceError, "pair controls"):
            chain.close_blind_set(
                self.chain_dir, CONTRACT, "skill_primary"
            )

    def test_timeout_quality_coercion_fails(self) -> None:
        timeout_metrics = self.metrics(
            "OUT-222222222222", self.packet_b, completed=False
        )
        write_json(self.metrics_b, timeout_metrics)
        self.seal_pair()
        submission = self.score("primary", timeout_b=True)
        submission["outputs"][1]["oracle_acceptance"] = False
        path = self.evidence_root / "primary.json"
        write_json(path, submission)
        with self.assertRaisesRegex(chain.EvidenceError, "scored quality"):
            chain.submit_scorer(
                self.chain_dir, CONTRACT, "primary", path
            )

    def test_mapping_release_before_two_scorers_fails(self) -> None:
        self.seal_pair()
        mapping = self.evidence_root / "mapping.json"
        write_json(
            mapping,
            {
                "mapping": {
                    "OUT-111111111111": "A",
                    "OUT-222222222222": "B",
                },
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )
        with self.assertRaisesRegex(chain.EvidenceError, "required chain state"):
            chain.release_mapping(self.chain_dir, CONTRACT, mapping)

    def test_wrong_mapping_treatment_set_fails(self) -> None:
        self.seal_pair()
        primary = self.evidence_root / "primary.json"
        second = self.evidence_root / "second.json"
        write_json(primary, self.score("primary"))
        write_json(second, self.score("second"))
        chain.submit_scorer(
            self.chain_dir, CONTRACT, "primary", primary
        )
        chain.submit_scorer(
            self.chain_dir, CONTRACT, "second", second
        )
        mapping = self.evidence_root / "mapping.json"
        write_json(
            mapping,
            {
                "mapping": {
                    "OUT-111111111111": "A",
                    "OUT-222222222222": "D",
                },
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )
        with self.assertRaisesRegex(chain.EvidenceError, "treatment set"):
            chain.release_mapping(self.chain_dir, CONTRACT, mapping)

    def test_full_chain_verifies_and_binds_scorer_events(self) -> None:
        self.full_chain()
        result = chain.verify_chain(
            self.chain_dir, CONTRACT, require_state="mapping_released"
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["event_count"], 6)
        final = json.loads(
            sorted(self.chain_dir.iterdir())[-1].read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(final["scorer_event_sha256"]), {"primary", "second"}
        )

    def test_mapping_scorer_event_digest_tamper_fails(self) -> None:
        self.full_chain()
        final_path = sorted(self.chain_dir.iterdir())[-1]
        final = json.loads(final_path.read_text(encoding="utf-8"))
        final["scorer_event_sha256"]["primary"] = "0" * 64
        final_path.write_bytes(chain._json_bytes(final))
        with self.assertRaisesRegex(chain.EvidenceError, "scorer-event"):
            chain.verify_chain(self.chain_dir, CONTRACT)

    def test_retained_packet_tamper_fails(self) -> None:
        self.full_chain()
        self.packet_a.write_bytes(b'{"packet":"tampered"}\n')
        with self.assertRaisesRegex(chain.EvidenceError, "packet digest"):
            chain.verify_chain(self.chain_dir, CONTRACT)

    def test_missing_event_fails(self) -> None:
        self.full_chain()
        sorted(self.chain_dir.iterdir())[2].unlink()
        with self.assertRaisesRegex(chain.EvidenceError, "filename mismatch"):
            chain.verify_chain(self.chain_dir, CONTRACT)

    def test_previous_digest_tamper_fails(self) -> None:
        self.full_chain()
        fourth = sorted(self.chain_dir.iterdir())[3]
        value = json.loads(fourth.read_text(encoding="utf-8"))
        value["previous_event_sha256"] = "0" * 64
        fourth.write_bytes(chain._json_bytes(value))
        with self.assertRaisesRegex(chain.EvidenceError, "previous event digest"):
            chain.verify_chain(self.chain_dir, CONTRACT)

    def test_partial_publish_never_creates_final(self) -> None:
        target = self.root / "create-once.json"
        with mock.patch.object(chain.os, "link", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                chain._publish_create_once(target, b"complete")
        self.assertFalse(target.exists())

    def test_source_outside_evidence_root_fails(self) -> None:
        outside = self.root / "outside-packet.json"
        outside.write_bytes(b"outside\n")
        metrics = self.metrics(
            "OUT-111111111111", outside, completed=True
        )
        write_json(self.metrics_a, metrics)
        try:
            with self.assertRaisesRegex(chain.EvidenceError, "evidence root"):
                chain.seal_outcome(
                    self.chain_dir, CONTRACT, outside, self.metrics_a
                )
        finally:
            outside.unlink(missing_ok=True)

    def test_cli_failure_writes_parseable_json(self) -> None:
        invalid = json.loads(self.metrics_a.read_text(encoding="utf-8"))
        invalid["status"] = "timed_out"
        write_json(self.metrics_a, invalid)
        report = self.root / "report.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "validate-metrics",
                "--contract",
                str(CONTRACT),
                "--metrics",
                str(self.metrics_a),
                "--json-out",
                str(report),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(
            json.loads(report.read_text(encoding="utf-8"))["status"], "FAIL"
        )

    def test_cli_end_to_end_chain(self) -> None:
        primary = self.evidence_root / "primary.json"
        second = self.evidence_root / "second.json"
        mapping = self.evidence_root / "mapping.json"
        report = self.root / "chain-report.json"
        write_json(primary, self.score("primary"))
        write_json(second, self.score("second"))
        write_json(
            mapping,
            {
                "mapping": {
                    "OUT-111111111111": "A",
                    "OUT-222222222222": "B",
                },
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )

        commands = [
            [
                "seal-outcome",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--packet",
                str(self.packet_a),
                "--metrics",
                str(self.metrics_a),
            ],
            [
                "seal-outcome",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--packet",
                str(self.packet_b),
                "--metrics",
                str(self.metrics_b),
            ],
            [
                "close-blind-set",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--study-kind",
                "skill_primary",
            ],
            [
                "submit-scorer",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--role",
                "primary",
                "--submission",
                str(primary),
            ],
            [
                "submit-scorer",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--role",
                "second",
                "--submission",
                str(second),
            ],
            [
                "release-mapping",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--mapping",
                str(mapping),
            ],
            [
                "verify",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--require-state",
                "mapping_released",
                "--json-out",
                str(report),
            ],
        ]
        for args in commands:
            completed = subprocess.run(
                [sys.executable, str(MODULE_PATH), *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )
        self.assertEqual(
            json.loads(report.read_text(encoding="utf-8"))["status"], "PASS"
        )

    def test_candidate_manifest_build_verify_and_tamper_rejection(self) -> None:
        candidate_root = self.root / "candidate-repo"
        for relative in chain.CANDIDATE_FILES:
            source = ROOT.joinpath(*relative.split("/"))
            target = candidate_root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        manifest = candidate_root.joinpath(
            *chain.CANDIDATE_MANIFEST.split("/")
        )
        chain.build_candidate_manifest(
            candidate_root, manifest, "1" * 40
        )
        result = chain.verify_candidate(candidate_root, manifest)
        self.assertEqual(result["status"], "PASS")
        contract = candidate_root.joinpath(*chain.CANDIDATE_FILES[2].split("/"))
        contract.write_bytes(contract.read_bytes() + b" ")
        with self.assertRaisesRegex(chain.EvidenceError, "candidate file mismatch"):
            chain.verify_candidate(candidate_root, manifest)


if __name__ == "__main__":
    unittest.main()
