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
HARNESS_CONTRACT = EXPERIMENT / "candidate/gate3-harness-contract-v1.json"
MODULE_PATH = HERE / "gate3_evidence_chain.py"
SPEC = importlib.util.spec_from_file_location("gate3_evidence_chain", MODULE_PATH)
assert SPEC and SPEC.loader
chain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chain)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    )


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout


class Gate3ChainFixture:
    """Shared chain fixture.

    Deliberately not a TestCase. When this was one, every class that
    needed the fixture inherited its tests too and the runner collected
    them again per subclass: 115 collections for 47 distinct tests, with
    no added coverage and nearly triple the runtime.
    """

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        self.chain_dir = self.evidence_root / "chain"
        self.harness_sha256 = digest(HARNESS_CONTRACT.read_bytes())
        self.common_input_artifacts = {
            "baseline_instruction_sha256": self.retain_input(
                "baseline-instruction.txt", b"baseline instructions\n"
            ),
            "task_packet_sha256": self.retain_input(
                "task-packet.txt", b"repair the arithmetic defect\n"
            ),
            "permissions_sha256": self.retain_input(
                "permissions.json", b'{"mode":"managed"}\n'
            ),
            "budget_sha256": self.retain_input(
                "budget.json", b'{"wall_clock_seconds":1800}\n'
            ),
            "harness_contract_sha256": self.retain_input(
                "gate3-harness-contract-v1.json",
                HARNESS_CONTRACT.read_bytes(),
            ),
            "scorer_rubric_sha256": self.retain_input(
                "scorer-rubric.txt", b"score only the blind packet\n"
            ),
        }
        self.mapping = {
            "OUT-111111111111": "A",
            "OUT-222222222222": "B",
        }
        self.nonce_hex = "ab" * 32
        # A skill_primary comparison varies the skill packet and nothing else.
        # These three inputs are deliberately shared: if they differed, B minus
        # A would be a mixture of skill, governance and validator effects and
        # could not be read as the skill effect at all.
        shared_governance = self.retain_input(
            "governance-shared.txt", b"governance shared\n"
        )
        shared_validator_bundle = self.retain_input(
            "validator-shared.py", b"print('validator shared')\n"
        )
        shared_validator_config = self.retain_input(
            "validator-shared.json", b'{"mode":"shared"}\n'
        )
        self.treatment_input_artifacts = {
            "A": {
                "treatment_packet_sha256": self.retain_input(
                    "treatment-a.txt", b"no skill packet\n"
                ),
                "governance_instruction_sha256": shared_governance,
                "validator_bundle_sha256": shared_validator_bundle,
                "validator_config_sha256": shared_validator_config,
            },
            "B": {
                "treatment_packet_sha256": self.retain_input(
                    "treatment-b.txt", b"skill packet\n"
                ),
                "governance_instruction_sha256": shared_governance,
                "validator_bundle_sha256": shared_validator_bundle,
                "validator_config_sha256": shared_validator_config,
            },
        }
        self.treatment_inputs = {
            treatment: {
                field: entry["sha256"]
                for field, entry in artifacts.items()
            }
            for treatment, artifacts in self.treatment_input_artifacts.items()
        }
        self.randomization_record = self.evidence_root / "randomization.json"
        write_json(
            self.randomization_record,
            {
                "anonymous_ids": sorted(self.mapping),
                "mapping_commitment_sha256": chain._mapping_commitment(
                    self.mapping, "skill_primary", self.nonce_hex
                ),
                "pair_id": "task-1-pair-1",
                "repeat_index": 1,
                "schema": "gate3-randomization-record.v1",
                "study_kind": "skill_primary",
                "task_id": "task-1",
                "treatment_inputs": self.treatment_inputs,
            },
        )
        self.randomization_sha256 = digest(
            self.randomization_record.read_bytes()
        )
        self.common_input_artifacts["randomization_record_sha256"] = {
            "path": self.evidence_relative(self.randomization_record),
            "sha256": self.randomization_sha256,
        }

        self.base_repo = self.root / "base-repo"
        self.base_repo.mkdir()
        run_git(self.base_repo, "init", "-q")
        run_git(self.base_repo, "config", "user.email", "test@example.com")
        run_git(self.base_repo, "config", "user.name", "Gate3 Test")
        (self.base_repo / "calc.py").write_text(
            "def add(a, b):\n    return a - b\n", encoding="utf-8"
        )
        run_git(self.base_repo, "add", "calc.py")
        run_git(self.base_repo, "commit", "-q", "-m", "baseline")
        self.baseline_commit = run_git(
            self.base_repo, "rev-parse", "HEAD"
        ).decode("ascii").strip()

        (
            self.repo_a,
            self.packet_a,
            self.metrics_a,
            self.admission_a,
        ) = self.make_outcome(
            "OUT-111111111111", "A", "a", completed=True
        )
        (
            self.repo_b,
            self.packet_b,
            self.metrics_b,
            self.admission_b,
        ) = self.make_outcome(
            "OUT-222222222222", "B", "b", completed=True
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def evidence_relative(self, path: Path) -> str:
        return path.relative_to(self.evidence_root).as_posix()

    def retain_input(self, filename: str, payload: bytes) -> dict[str, str]:
        path = self.evidence_root / "inputs" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {
            "path": self.evidence_relative(path),
            "sha256": digest(payload),
        }

    def make_outcome(
        self,
        anon_id: str,
        treatment: str,
        suffix: str,
        *,
        completed: bool,
        pair_id: str = "task-1-pair-1",
        repeat_index: int = 1,
    ) -> tuple[Path, Path, Path, Path]:
        repo = self.root / f"repo-{suffix}"
        run_git(self.root, "clone", "--quiet", str(self.base_repo), str(repo))
        run_git(repo, "config", "user.email", "test@example.com")
        run_git(repo, "config", "user.name", "Gate3 Test")
        (repo / "calc.py").write_text(
            f"def add(a, b):\n    return a + b  # {suffix}\n", encoding="utf-8"
        )
        run_git(repo, "add", "calc.py")
        run_git(repo, "commit", "-q", "-m", f"output {suffix}")
        output_commit = run_git(repo, "rev-parse", "HEAD").decode(
            "ascii"
        ).strip()

        bundle = self.evidence_root / f"repo-{suffix}.bundle"
        run_git(repo, "bundle", "create", str(bundle), "--all")
        final_diff = self.evidence_root / f"final-diff-{suffix}.patch"
        final_diff.write_bytes(
            run_git(
                repo,
                "diff",
                "--binary",
                "--full-index",
                self.baseline_commit,
                output_commit,
                "--",
            )
        )
        tracked = [
            item.decode("utf-8")
            for item in run_git(
                repo,
                "diff",
                "--name-only",
                "-z",
                self.baseline_commit,
                output_commit,
                "--",
            ).split(b"\0")
            if item
        ]
        event_log = self.evidence_root / f"event-log-{suffix}.jsonl"
        event_log.write_bytes(
            json.dumps({"event": "completed", "run": suffix}, sort_keys=True)
            .encode("utf-8")
            + b"\n"
        )
        test_output = self.evidence_root / f"test-output-{suffix}.txt"
        test_output.write_bytes(b"1 passed\n")
        receipt = self.evidence_root / f"receipt-{suffix}.json"
        write_json(
            receipt,
            {
                "command": "pytest -q",
                "exit_code": 0,
                "linked_commit": output_commit,
                "output_path": self.evidence_relative(test_output),
                "output_sha256": digest(test_output.read_bytes()),
                "schema": "gate3-test-evidence-receipt.v1",
            },
        )
        receipt_index = [
            {
                "path": self.evidence_relative(receipt),
                "sha256": digest(receipt.read_bytes()),
            }
        ]
        # A real retained receipt showing the regression failing at the
        # baseline. regression_baseline_fail is read from this, not from a
        # metrics flag asserting the observation happened.
        baseline_output = self.evidence_root / f"baseline-output-{suffix}.txt"
        baseline_output.write_bytes(b"1 failed\n")
        baseline_receipt = self.evidence_root / f"baseline-receipt-{suffix}.json"
        write_json(
            baseline_receipt,
            {
                "command": "pytest -q",
                "exit_code": 1,
                "expected_failure": True,
                "linked_commit": self.baseline_commit,
                "output_path": self.evidence_relative(baseline_output),
                "output_sha256": digest(baseline_output.read_bytes()),
                "schema": "gate3-synthetic-baseline-test-receipt.v1",
            },
        )
        self.baseline_receipt_sha256 = digest(baseline_receipt.read_bytes())
        self.baseline_receipt_ref = {
            "path": self.evidence_relative(baseline_receipt),
            "sha256": self.baseline_receipt_sha256,
        }
        receipt_set_sha = digest(chain._json_bytes(receipt_index))
        packet = self.evidence_root / f"packet-{suffix}.json"
        write_json(
            packet,
            {
                "anon_id": anon_id,
                "baseline_commit": self.baseline_commit,
                "final_diff_sha256": digest(final_diff.read_bytes()),
                "harness_contract_sha256": self.harness_sha256,
                "output_commit": output_commit,
                "receipt_set_sha256": receipt_set_sha,
                "schema": "gate3-outcome-packet.v1",
                "scorer_payload": {
                    "baseline_test_receipt_sha256": self.baseline_receipt_sha256,
                    "final_diff_utf8": final_diff.read_text(encoding="utf-8"),
                    "test_exit_code": 0,
                },
            },
        )
        input_artifacts = {
            **copy.deepcopy(self.common_input_artifacts),
            **copy.deepcopy(self.treatment_input_artifacts[treatment]),
        }
        input_digests = {
            field: entry["sha256"]
            for field, entry in input_artifacts.items()
        }
        admission = self.evidence_root / f"admission-{suffix}.json"
        write_json(
            admission,
            {
                "anon_id": anon_id,
                "baseline_commit": self.baseline_commit,
                "baseline_test_receipt": dict(self.baseline_receipt_ref),
                "event_log": {
                    "path": self.evidence_relative(event_log),
                    "sha256": digest(event_log.read_bytes()),
                },
                "final_diff": {
                    "path": self.evidence_relative(final_diff),
                    "sha256": digest(final_diff.read_bytes()),
                    "tracked_changed_files": tracked,
                },
                "git_bundle": {
                    "path": self.evidence_relative(bundle),
                    "sha256": digest(bundle.read_bytes()),
                },
                "input_artifacts": input_artifacts,
                "input_digests": input_digests,
                "model_build": "model-build-1",
                "output_commit": output_commit,
                "output_packet_sha256": digest(packet.read_bytes()),
                "receipt_set_sha256": receipt_set_sha,
                "receipts": receipt_index,
                "schema": "gate3-outcome-admission.v1",
                "treatment": treatment,
                "worktree_clean_at_capture": True,
            },
        )
        metrics = self.evidence_root / f"metrics-{suffix}.json"
        write_json(metrics, self.metrics(
            anon_id,
            packet,
            completed=completed,
            suffix=suffix,
            pair_id=pair_id,
            repeat_index=repeat_index,
        ))
        return repo, packet, metrics, admission

    def metrics(
        self,
        anon_id: str,
        packet: Path,
        *,
        completed: bool,
        suffix: str | None = None,
        pair_id: str = "task-1-pair-1",
        repeat_index: int = 1,
    ) -> dict[str, object]:
        observation = {"observed": False, "evidence_sha256": []}
        baseline_observation = {
            "observed": True,
            "evidence_sha256": [self.baseline_receipt_sha256],
        }
        if suffix is None:
            suffix = "a" if anon_id == "OUT-111111111111" else "b"
        event_log = self.evidence_root / f"event-log-{suffix}.jsonl"
        return {
            "anon_id": anon_id,
            "artifacts": {
                "event_log_sha256": digest(event_log.read_bytes()),
                "output_packet_sha256": digest(packet.read_bytes()),
            },
            "baseline_commit": self.baseline_commit,
            "budget_sha256": self.common_input_artifacts[
                "budget_sha256"
            ]["sha256"],
            "completed_under_cap": completed,
            "conditional_quality_eligible": completed,
            "costs": {
                "changed_files": 1,
                "core_available": True,
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
                "failing_regression_before_fix": copy.deepcopy(
                    baseline_observation
                ),
                "post_restore_retest_performed": copy.deepcopy(observation),
                "reproduction_before_first_edit": copy.deepcopy(observation),
                "root_cause_recorded_before_first_edit": copy.deepcopy(
                    observation
                ),
            },
            "harness_contract_sha256": self.harness_sha256,
            "model_build": "model-build-1",
            "pair_id": pair_id,
            "permissions_sha256": self.common_input_artifacts[
                "permissions_sha256"
            ]["sha256"],
            "randomization_record_sha256": self.randomization_sha256,
            "repeat_index": repeat_index,
            "run_id": f"run-{anon_id[-4:]}",
            "schema": "gate3-run-metrics.v1",
            "scorer_rubric_sha256": self.common_input_artifacts[
                "scorer_rubric_sha256"
            ]["sha256"],
            "status": "completed" if completed else "timed_out",
            "task_id": "task-1",
            "task_packet_sha256": self.common_input_artifacts[
                "task_packet_sha256"
            ]["sha256"],
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
            "blind_input_set_sha256": chain._blind_input_set_sha256(
                {
                    "OUT-111111111111": {
                        "packet_sha256": digest(self.packet_a.read_bytes())
                    },
                    "OUT-222222222222": {
                        "packet_sha256": digest(self.packet_b.read_bytes())
                    },
                }
            ),
            "independence_declaration": True,
            "model_build": "scorer-model-1",
            "outputs": [
                output("OUT-111111111111", True),
                output("OUT-222222222222", not timeout_b),
            ],
            "schema": "gate3-blind-score.v1",
            "scorer_context_id": f"context-{role}",
            "scorer_identity": f"scorer-{role}",
            "scorer_role": role,
            "scorer_rubric_sha256": self.common_input_artifacts[
                "scorer_rubric_sha256"
            ]["sha256"],
        }

    def seal_pair(self) -> None:
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        chain.seal_outcome(
            self.chain_dir,
            CONTRACT,
            self.packet_a,
            self.metrics_a,
            self.admission_a,
            self.repo_a,
        )
        chain.seal_outcome(
            self.chain_dir,
            CONTRACT,
            self.packet_b,
            self.metrics_b,
            self.admission_b,
            self.repo_b,
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
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
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


class Gate3EvidenceChainTests(Gate3ChainFixture, unittest.TestCase):
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

    def test_zero_core_cost_is_rejected(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        value = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        value["costs"]["tool_calls"] = 0  # type: ignore[index]
        with self.assertRaisesRegex(chain.EvidenceError, "greater than zero"):
            chain.validate_metrics(value, contract)

    def test_unavailable_core_costs_make_gate_insufficient(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        arm_a = self.metrics(
            "OUT-111111111111", self.packet_a, completed=True
        )
        arm_b = self.metrics(
            "OUT-222222222222", self.packet_b, completed=True
        )
        for value in (arm_a, arm_b):
            costs = value["costs"]  # type: ignore[index]
            costs["core_available"] = False
            costs["wall_clock_ms"] = None
            costs["tool_calls"] = None
            costs["core_unavailable_reason"] = "provider telemetry absent"
            chain.validate_metrics(value, contract)
        result = chain.evaluate_cost_gate([(arm_a, arm_b)], contract)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertEqual(result["valid_pairs"], 0)

    def test_even_sample_cost_median_is_arithmetic_middle_mean(self) -> None:
        contract, _ = chain.load_contract(CONTRACT)
        pairs = []
        for ratio in (1.0, 1.4):
            arm_a = self.metrics(
                "OUT-111111111111", self.packet_a, completed=True
            )
            arm_b = self.metrics(
                "OUT-222222222222", self.packet_b, completed=True
            )
            arm_a["costs"]["wall_clock_ms"] = 100  # type: ignore[index]
            arm_a["costs"]["tool_calls"] = 10  # type: ignore[index]
            arm_b["costs"]["wall_clock_ms"] = int(100 * ratio)  # type: ignore[index]
            arm_b["costs"]["tool_calls"] = int(10 * ratio)  # type: ignore[index]
            pairs.append((arm_a, arm_b))
        result = chain.evaluate_cost_gate(pairs, contract)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["median_paired_wall_clock_ratio"], 1.2)
        self.assertEqual(result["median_paired_tool_call_ratio"], 1.2)

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
                self.chain_dir,
                CONTRACT,
                self.packet_a,
                self.metrics_a,
                self.admission_a,
                self.repo_a,
            )

    def test_create_once_refuses_existing_event(self) -> None:
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        chain.seal_outcome(
            self.chain_dir,
            CONTRACT,
            self.packet_a,
            self.metrics_a,
            self.admission_a,
            self.repo_a,
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

    def test_role_only_copy_cannot_impersonate_second_scorer(self) -> None:
        self.seal_pair()
        primary = self.evidence_root / "primary.json"
        second = self.evidence_root / "second.json"
        primary_value = self.score("primary")
        second_value = copy.deepcopy(primary_value)
        second_value["scorer_role"] = "second"
        write_json(primary, primary_value)
        write_json(second, second_value)
        chain.submit_scorer(
            self.chain_dir, CONTRACT, "primary", primary
        )
        with self.assertRaisesRegex(chain.EvidenceError, "contexts"):
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
        alternate_task = self.retain_input(
            "task-packet-b.txt", b"different task packet\n"
        )
        value = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        value["task_packet_sha256"] = alternate_task["sha256"]
        write_json(self.metrics_b, value)
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["input_digests"]["task_packet_sha256"] = alternate_task[
            "sha256"
        ]
        admission["input_artifacts"]["task_packet_sha256"] = alternate_task
        write_json(self.admission_b, admission)
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        chain.seal_outcome(
            self.chain_dir,
            CONTRACT,
            self.packet_a,
            self.metrics_a,
            self.admission_a,
            self.repo_a,
        )
        chain.seal_outcome(
            self.chain_dir,
            CONTRACT,
            self.packet_b,
            self.metrics_b,
            self.admission_b,
            self.repo_b,
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
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )
        with self.assertRaisesRegex(chain.EvidenceError, "required chain state"):
            chain.release_mapping(self.chain_dir, CONTRACT, mapping)

    def test_mapping_swap_is_rejected_by_preregistered_commitment(self) -> None:
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
        swapped = self.evidence_root / "mapping-swapped.json"
        write_json(
            swapped,
            {
                "mapping": {
                    "OUT-111111111111": "B",
                    "OUT-222222222222": "A",
                },
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )
        with self.assertRaisesRegex(chain.EvidenceError, "commitment"):
            chain.release_mapping(self.chain_dir, CONTRACT, swapped)

    def test_two_arms_carrying_one_treatment_are_refused_at_blind_set(
        self,
    ) -> None:
        """Both arms on the same skill packet is not a comparison at all.

        This used to be spelled as a mapping-binding failure, and it reached
        that check because nothing earlier noticed that the two arms were now
        identical. The single-varying-factor rule refuses it first, which is
        the more direct statement of what is wrong.
        """
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["treatment"] = "A"
        admission["input_digests"].update(self.treatment_inputs["A"])
        admission["input_artifacts"].update(
            self.treatment_input_artifacts["A"]
        )
        write_json(self.admission_b, admission)
        with self.assertRaisesRegex(
            chain.EvidenceError, "do not differ in the studied factor"
        ):
            self.seal_pair()

    def test_admitted_treatment_must_match_released_mapping(self) -> None:
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["treatment"] = "A"
        write_json(self.admission_b, admission)
        self.seal_pair()
        primary = self.evidence_root / "primary.json"
        second = self.evidence_root / "second.json"
        mapping = self.evidence_root / "mapping.json"
        write_json(primary, self.score("primary"))
        write_json(second, self.score("second"))
        write_json(
            mapping,
            {
                "mapping": self.mapping,
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
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
        with self.assertRaisesRegex(chain.EvidenceError, "admitted treatment"):
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
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
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
        self.assertEqual(result["event_count"], 7)
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

    def test_receipt_linked_commit_mismatch_is_rejected(self) -> None:
        receipt_path = self.evidence_root / "receipt-a.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["linked_commit"] = "f" * 40
        write_json(receipt_path, receipt)
        admission = json.loads(self.admission_a.read_text(encoding="utf-8"))
        admission["receipts"][0]["sha256"] = digest(receipt_path.read_bytes())
        write_json(self.admission_a, admission)
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        with self.assertRaisesRegex(chain.EvidenceError, "bind the output commit"):
            chain.seal_outcome(
                self.chain_dir,
                CONTRACT,
                self.packet_a,
                self.metrics_a,
                self.admission_a,
                self.repo_a,
            )

    def test_digest_shaped_input_without_matching_source_is_rejected(self) -> None:
        admission = json.loads(self.admission_a.read_text(encoding="utf-8"))
        admission["input_digests"]["baseline_instruction_sha256"] = "f" * 64
        admission["input_artifacts"]["baseline_instruction_sha256"][
            "sha256"
        ] = "f" * 64
        write_json(self.admission_a, admission)
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        with self.assertRaisesRegex(
            chain.EvidenceError, "retained input artifact does not match"
        ):
            chain.seal_outcome(
                self.chain_dir,
                CONTRACT,
                self.packet_a,
                self.metrics_a,
                self.admission_a,
                self.repo_a,
            )

    def test_duplicate_receipt_path_is_rejected(self) -> None:
        admission = json.loads(self.admission_a.read_text(encoding="utf-8"))
        admission["receipts"].append(copy.deepcopy(admission["receipts"][0]))
        write_json(self.admission_a, admission)
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        with self.assertRaisesRegex(chain.EvidenceError, "sorted and unique"):
            chain.seal_outcome(
                self.chain_dir,
                CONTRACT,
                self.packet_a,
                self.metrics_a,
                self.admission_a,
                self.repo_a,
            )

    def test_dirty_live_capture_is_rejected(self) -> None:
        (self.repo_a / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        chain.commit_randomization(
            self.chain_dir, CONTRACT, self.randomization_record
        )
        with self.assertRaisesRegex(chain.EvidenceError, "not clean"):
            chain.seal_outcome(
                self.chain_dir,
                CONTRACT,
                self.packet_a,
                self.metrics_a,
                self.admission_a,
                self.repo_a,
            )

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
        try:
            with self.assertRaisesRegex(chain.EvidenceError, "evidence root"):
                chain._source_relative_to_evidence_root(
                    outside, self.chain_dir
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
                "nonce_hex": self.nonce_hex,
                "randomization_record_sha256": self.randomization_sha256,
                "schema": "gate3-mapping-release.v1",
                "study_kind": "skill_primary",
            },
        )

        commands = [
            [
                "commit-randomization",
                "--chain-dir",
                str(self.chain_dir),
                "--contract",
                str(CONTRACT),
                "--record",
                str(self.randomization_record),
            ],
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
                "--admission",
                str(self.admission_a),
                "--repo-root",
                str(self.repo_a),
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
                "--admission",
                str(self.admission_b),
                "--repo-root",
                str(self.repo_b),
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
        run_git(candidate_root, "init", "-q")
        run_git(candidate_root, "config", "user.email", "test@example.com")
        run_git(candidate_root, "config", "user.name", "Gate3 Test")
        run_git(candidate_root, "add", ".")
        run_git(candidate_root, "commit", "-q", "-m", "candidate base")
        source_base = run_git(candidate_root, "rev-parse", "HEAD").decode(
            "ascii"
        ).strip()
        with self.assertRaisesRegex(chain.EvidenceError, "git cat-file"):
            chain.build_candidate_manifest(
                candidate_root, manifest, "1" * 40
            )
        chain.build_candidate_manifest(
            candidate_root, manifest, source_base
        )
        result = chain.verify_candidate(candidate_root, manifest)
        self.assertEqual(result["status"], "PASS")
        contract = candidate_root.joinpath(*chain.CANDIDATE_FILES[3].split("/"))
        contract.write_bytes(contract.read_bytes() + b" ")
        with self.assertRaisesRegex(chain.EvidenceError, "candidate file mismatch"):
            chain.verify_candidate(candidate_root, manifest)


if __name__ == "__main__":
    unittest.main()


class Gate3SingleFactorTests(Gate3ChainFixture, unittest.TestCase):
    """Every non-studied input must be equal across the two arms.

    Checking each arm against its own preregistered digests is not the same
    check: it passes happily while the arms differ in three ways at once, which
    is how the original fixture shipped.
    """

    def _seal_with_b_field(self, field: str, digest: str) -> None:
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["input_digests"][field] = digest
        write_json(self.admission_b, admission)
        self.seal_pair()

    def test_each_non_studied_input_must_match_across_arms(self) -> None:
        for field in (
            "baseline_instruction_sha256",
            "governance_instruction_sha256",
            "validator_bundle_sha256",
            "validator_config_sha256",
            "task_packet_sha256",
            "permissions_sha256",
            "budget_sha256",
            "scorer_rubric_sha256",
        ):
            with self.subTest(field=field):
                self.setUp()
                with self.assertRaises(chain.EvidenceError):
                    self._seal_with_b_field(field, "c" * 64)

    def test_the_studied_factor_must_actually_differ(self) -> None:
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["input_digests"]["treatment_packet_sha256"] = (
            self.treatment_inputs["A"]["treatment_packet_sha256"]
        )
        admission["input_artifacts"]["treatment_packet_sha256"] = (
            self.treatment_input_artifacts["A"]["treatment_packet_sha256"]
        )
        write_json(self.admission_b, admission)
        with self.assertRaisesRegex(
            chain.EvidenceError, "do not differ in the studied factor"
        ):
            self.seal_pair()


class Gate3ScorerBlindnessTests(Gate3ChainFixture, unittest.TestCase):
    """The packet must not tell the scorer which arm it is looking at.

    Withholding the mapping is not blindness if the packet names the arm.
    """

    def _seal_with_packet(self, mutate) -> None:
        """Mutate the packet and re-bind every digest that covers it.

        Without the re-binding the run stops at a digest mismatch, which is a
        different check and would let a leak test pass for the wrong reason.
        """
        packet = json.loads(self.packet_b.read_text(encoding="utf-8"))
        mutate(packet)
        write_json(self.packet_b, packet)
        packet_sha = digest(self.packet_b.read_bytes())
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["output_packet_sha256"] = packet_sha
        write_json(self.admission_b, admission)
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["artifacts"]["output_packet_sha256"] = packet_sha
        write_json(self.metrics_b, metrics)
        self.seal_pair()

    def test_a_top_level_treatment_field_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "exact set"):
            self._seal_with_packet(
                lambda packet: packet.update({"treatment": "A"})
            )

    def test_a_nested_treatment_field_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "allowed field set"):
            self._seal_with_packet(
                lambda packet: packet["scorer_payload"].update(
                    {"treatment": "A"}
                )
            )

    def test_an_identity_naming_value_is_refused(self) -> None:
        with self.assertRaisesRegex(
            chain.EvidenceError, "reveals treatment identity"
        ):
            self._seal_with_packet(
                lambda packet: packet["scorer_payload"].update(
                    {"baseline_test_receipt_sha256": "inputs/treatment-b.txt"}
                )
            )

    def test_a_nested_payload_object_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "not scalar"):
            self._seal_with_packet(
                lambda packet: packet["scorer_payload"].update(
                    {"test_exit_code": {"arm": "B"}}
                )
            )

    def test_producer_diff_content_is_not_vocabulary_checked(self) -> None:
        """A fix may legitimately contain any word, including these.

        Asserted against the shape validator directly. Sealing would now fail
        for a different reason: the diff must equal the retained bytes, which
        is a separate guarantee added later.
        """
        packet = json.loads(self.packet_b.read_text(encoding="utf-8"))
        packet["scorer_payload"]["final_diff_utf8"] = (
            "def apply_treatment(skill, arm):" + chr(10) + "    return skill"
        )
        contract, _ = chain.load_contract(CONTRACT)
        chain._validate_scorer_packet_shape(
            packet, contract["_scorer_packet_policy"]
        )


class Gate3ScorerDisagreementTests(unittest.TestCase):
    """Conservative intersection, and what it deliberately refuses to do."""

    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.policy = self.contract["decision_rule"][
            "scorer_disagreement_policy"
        ]
        self.verifier = {
            field: True
            for field in self.policy["verifier_determined_fields"]
        }

    def _score(self, **overrides: bool) -> dict[str, object]:
        value = {
            field: True for field in self.policy["scorer_judged_fields"]
        }
        value.update(overrides)
        return value

    def test_both_scorers_passing_is_a_qualifying_success(self) -> None:
        result = chain.resolve_qualifying_success(
            self._score(), self._score(), self.verifier, self.contract
        )
        self.assertTrue(result["qualifying_success"])
        self.assertFalse(result["scorers_conflicted"])

    def test_disagreement_is_not_a_qualifying_success(self) -> None:
        for field in self.policy["scorer_judged_fields"]:
            with self.subTest(field=field):
                result = chain.resolve_qualifying_success(
                    self._score(),
                    self._score(**{field: False}),
                    self.verifier,
                    self.contract,
                )
                self.assertFalse(result["qualifying_success"])
                self.assertEqual(result["conflicting_fields"], [field])

    def test_disagreement_does_not_discard_the_run(self) -> None:
        """The conflicted run stays countable; only its verdict is negative.

        Dropping it instead would shrink the denominator, and the promotion
        threshold is written against a fixed sample size.
        """
        result = chain.resolve_qualifying_success(
            self._score(),
            self._score(oracle_acceptance=False),
            self.verifier,
            self.contract,
        )
        self.assertIn("qualifying_success", result)
        self.assertFalse(result["qualifying_success"])
        self.assertTrue(result["scorers_conflicted"])

    def test_agreement_cannot_override_the_verifier(self) -> None:
        """Objective fields are observed, not voted on."""
        for field in self.policy["verifier_determined_fields"]:
            with self.subTest(field=field):
                result = chain.resolve_qualifying_success(
                    self._score(),
                    self._score(),
                    {**self.verifier, field: False},
                    self.contract,
                )
                self.assertFalse(result["qualifying_success"])
                self.assertFalse(result["scorers_conflicted"])

    def test_the_policy_is_conservative_intersection(self) -> None:
        self.assertEqual(self.policy["policy"], "conservative_intersection")
        self.assertTrue(self.policy["sample_size_unchanged_by_conflict"])
        self.assertTrue(self.policy["retain_both_submissions_and_conflict_record"])
        self.assertEqual(self.policy["objective_fields_source"], "verifier")
        self.assertFalse(
            set(self.policy["scorer_judged_fields"])
            & set(self.policy["verifier_determined_fields"])
        )
        self.assertEqual(
            sorted(
                self.policy["scorer_judged_fields"]
                + self.policy["verifier_determined_fields"]
            ),
            sorted(self.contract["decision_rule"]["qualifying_success_requires"]),
        )


class Gate3SampleSizeTests(unittest.TestCase):
    def test_the_task_count_is_exactly_three(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        primary = contract["primary_study"]
        self.assertEqual(primary["natural_bug_tasks"], 3)
        self.assertNotIn("minimum_natural_bug_tasks", primary)
        self.assertIn("no_post_hoc_expansion", primary["natural_bug_tasks_policy"])
        # The promotion threshold is written against exactly this count.
        self.assertEqual(
            contract["decision_rule"]["promotion_requires"]["b_task_wins_min"], 2
        )


class Gate3DisagreementBoundaryTests(unittest.TestCase):
    """Disagreement must not become a side door to extra runs.

    The third pair is a frozen adaptive sample decided before signature, not
    an adjudication device. It still triggers on post-intersection counts, and
    nothing triggers a fourth.
    """

    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.policy = self.contract["decision_rule"][
            "scorer_disagreement_policy"
        ]

    def test_conflict_authorizes_no_replacement_or_adjudication_run(
        self,
    ) -> None:
        self.assertTrue(
            self.policy[
                "conflict_does_not_authorize_replacement_or_adjudication_run"
            ]
        )
        self.assertEqual(
            self.contract["scorer_submission"]["roles"], ["primary", "second"]
        )

    def test_the_frozen_third_pair_rule_still_applies(self) -> None:
        self.assertTrue(
            self.policy["frozen_third_pair_rule_applies_to_post_intersection_counts"]
        )
        self.assertIn(
            "tied_qualifying_success_count",
            self.contract["primary_study"]["third_pair_trigger"],
        )

    def test_no_fourth_pair_under_any_disagreement_or_tie(self) -> None:
        self.assertTrue(self.policy["no_fourth_pair_under_any_disagreement_or_tie"])
        self.assertEqual(
            self.policy["maximum_pairs_per_task"],
            self.contract["primary_study"]["maximum_pairs_per_task"],
        )
        self.assertEqual(self.policy["maximum_pairs_per_task"], 3)

    def test_a_conflicted_run_still_counts_toward_the_pair(self) -> None:
        """The conflicted run is non-qualifying, not absent.

        A tie can therefore arise from conflict, and the frozen third pair may
        follow. That is the adaptive sample doing what it was preregistered to
        do, not disagreement buying an extra run.
        """
        verifier = {
            field: True
            for field in self.policy["verifier_determined_fields"]
        }
        agreed = {
            field: True for field in self.policy["scorer_judged_fields"]
        }
        conflicted = dict(agreed, oracle_acceptance=False)
        result = chain.resolve_qualifying_success(
            agreed, conflicted, verifier, self.contract
        )
        self.assertFalse(result["qualifying_success"])
        self.assertTrue(result["scorers_conflicted"])
        self.assertEqual(result["conflicting_fields"], ["oracle_acceptance"])
        self.assertTrue(self.policy["sample_size_unchanged_by_conflict"])

    def test_scorer_independence_is_required(self) -> None:
        self.assertIn(
            "independently_satisfy_every_scorer_judged_qualifying_criterion",
            self.policy["rule"],
        )
        self.assertTrue(
            self.contract["scorer_submission"]["scorer_context_must_differ"]
        )


class Gate3TaskDecisionTests(unittest.TestCase):
    """The disagreement boundary, exercised through the deciding code path.

    Asserting the contract's flags proves only that the flags are set. These
    build an actual decision and check what it refuses.
    """

    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.policy = self.contract["decision_rule"][
            "scorer_disagreement_policy"
        ]

    def _run(self, *, qualifying: bool = True, completed: bool = True,
             conflict: bool = False) -> dict[str, object]:
        judged = {
            field: qualifying
            for field in self.policy["scorer_judged_fields"]
        }
        second = dict(judged)
        if conflict:
            second["oracle_acceptance"] = not judged["oracle_acceptance"]
        verifier = {
            field: True
            for field in self.policy["verifier_determined_fields"]
        }
        verifier["completed_under_cap"] = completed
        return {"primary": judged, "second": second, "verifier": verifier}

    def _pair(self, index: int, *, a: dict, b: dict, **extra) -> dict:
        return {
            "pair_id": f"task-1-pair-{index}",
            "repeat_index": index,
            "runs": {"A": a, "B": b},
            **extra,
        }

    def _decide(self, pairs: list[dict]) -> dict[str, object]:
        return chain.build_task_decision(
            "task-1", "skill_primary", pairs, self.contract
        )

    def test_two_clear_pairs_decide_the_task(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(qualifying=False), b=self._run()),
            self._pair(2, a=self._run(qualifying=False), b=self._run()),
        ])
        self.assertEqual(decision["status"], "decided")
        self.assertEqual(decision["winner"], "B")
        self.assertEqual(decision["qualifying_success_counts"], {"A": 0, "B": 2})

    def test_a_tie_after_two_pairs_requires_the_third(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(), b=self._run()),
            self._pair(2, a=self._run(), b=self._run()),
        ])
        self.assertEqual(decision["status"], "third_pair_required")
        self.assertIsNone(decision["winner"])

    def test_a_non_completed_run_requires_the_third_pair(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(completed=False), b=self._run()),
            self._pair(2, a=self._run(qualifying=False), b=self._run()),
        ])
        self.assertEqual(decision["status"], "third_pair_required")

    def test_conflict_does_not_authorize_a_replacement_pair(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "no replacement"):
            self._decide([
                self._pair(1, a=self._run(conflict=True), b=self._run()),
                self._pair(2, a=self._run(), b=self._run(),
                           replacement_for="task-1-pair-1"),
            ])

    def test_a_fourth_pair_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "frozen maximum"):
            self._decide([
                self._pair(index, a=self._run(), b=self._run())
                for index in (1, 2, 3, 4)
            ])

    def test_three_pairs_decide_even_when_still_tied(self) -> None:
        decision = self._decide([
            self._pair(index, a=self._run(), b=self._run())
            for index in (1, 2, 3)
        ])
        self.assertEqual(decision["status"], "decided")
        self.assertIsNone(decision["winner"])

    def test_an_adjudicating_third_scorer_is_refused(self) -> None:
        run = self._run()
        run["adjudicator"] = dict(run["primary"])
        with self.assertRaisesRegex(chain.EvidenceError, "exactly the two roles"):
            self._decide([
                self._pair(1, a=run, b=self._run()),
                self._pair(2, a=self._run(), b=self._run()),
            ])

    def test_a_repeated_pair_is_refused(self) -> None:
        pair = self._pair(1, a=self._run(), b=self._run())
        with self.assertRaisesRegex(chain.EvidenceError, "repeats a pair_id"):
            self._decide([pair, dict(pair, repeat_index=2)])

    def test_a_gap_in_the_pair_sequence_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "sequence has a gap"):
            self._decide([
                self._pair(1, a=self._run(), b=self._run()),
                self._pair(3, a=self._run(), b=self._run()),
            ])

    def test_one_pair_is_not_a_task(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "at least two pairs"):
            self._decide([self._pair(1, a=self._run(), b=self._run())])

    def test_the_conflict_record_is_retained(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(conflict=True), b=self._run()),
            self._pair(2, a=self._run(qualifying=False), b=self._run()),
        ])
        self.assertEqual(len(decision["conflict_record"]), 1)
        self.assertEqual(decision["conflict_record"][0]["arm"], "A")
        self.assertEqual(
            decision["conflict_record"][0]["fields"], ["oracle_acceptance"]
        )
        # The conflicted run stayed in its pair rather than being dropped.
        self.assertEqual(decision["pair_count"], 2)

    def test_an_unauthorized_third_pair_is_refused(self) -> None:
        """A decided task cannot be reopened by appending a pair.

        The first two pairs settle it 1:0; adding a third would move the count
        to 1:1. Accepting that is optional stopping with extra steps.
        """
        with self.assertRaisesRegex(chain.EvidenceError, "unauthorized"):
            self._decide([
                self._pair(1, a=self._run(), b=self._run(qualifying=False)),
                self._pair(2, a=self._run(qualifying=False),
                           b=self._run(qualifying=False)),
                self._pair(3, a=self._run(qualifying=False), b=self._run()),
            ])

    def test_a_third_pair_is_allowed_after_a_genuine_tie(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(), b=self._run()),
            self._pair(2, a=self._run(qualifying=False),
                       b=self._run(qualifying=False)),
            self._pair(3, a=self._run(qualifying=False), b=self._run()),
        ])
        self.assertEqual(decision["status"], "decided")
        self.assertEqual(decision["winner"], "B")

    def test_a_third_pair_is_allowed_after_a_non_completed_run(self) -> None:
        decision = self._decide([
            self._pair(1, a=self._run(completed=False), b=self._run()),
            self._pair(2, a=self._run(qualifying=False), b=self._run()),
            self._pair(3, a=self._run(qualifying=False), b=self._run()),
        ])
        self.assertEqual(decision["status"], "decided")

    def test_a_boolean_repeat_index_is_refused(self) -> None:
        """bool subclasses int, so True would pass as repeat_index 1."""
        pair = self._pair(1, a=self._run(), b=self._run())
        pair["repeat_index"] = True
        with self.assertRaisesRegex(chain.EvidenceError, "must be an integer"):
            self._decide([pair, self._pair(2, a=self._run(), b=self._run())])

    def test_an_empty_or_untrimmed_task_id_is_refused(self) -> None:
        pairs = [
            self._pair(1, a=self._run(), b=self._run()),
            self._pair(2, a=self._run(), b=self._run()),
        ]
        for task_id in ("", "   ", " task-1", "task-1 "):
            with self.subTest(task_id=repr(task_id)):
                with self.assertRaisesRegex(
                    chain.EvidenceError, "non-empty and trimmed"
                ):
                    chain.build_task_decision(
                        task_id, "skill_primary", pairs, self.contract
                    )

    def test_an_untrimmed_pair_id_is_refused(self) -> None:
        pair = self._pair(1, a=self._run(), b=self._run())
        pair["pair_id"] = " task-1-pair-1"
        with self.assertRaisesRegex(chain.EvidenceError, "pair_id must be non-empty"):
            self._decide([pair, self._pair(2, a=self._run(), b=self._run())])


class Gate3TaskDecisionReceiptTests(Gate3ChainFixture, unittest.TestCase):
    """Everything must come from the chain, and each pair from a distinct one.

    A valid chain plus digest-valid arbitrary JSON proves only that some valid
    chain exists somewhere. The scores have to come from that chain.
    """

    def setUp(self) -> None:
        super().setUp()
        # load_contract, not a raw parse: the runtime stashes the harness
        # policies on the contract and the derivation needs them.
        self.contract, _ = chain.load_contract(CONTRACT)
        self.receipt = self.evidence_root / "task-decision.json"
        self.full_chain()

    def _dirs(self) -> list[str]:
        return [self.evidence_relative(self.chain_dir)]

    def test_scores_are_derived_from_the_chain(self) -> None:
        pairs, pinned = chain._pairs_from_chains(
            self._dirs(), self.evidence_root, CONTRACT, self.contract
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(set(pairs[0]["runs"]), {"A", "B"})
        policy = self.contract["decision_rule"]["scorer_disagreement_policy"]
        self.assertEqual(
            set(pairs[0]["runs"]["A"]["primary"]),
            set(policy["scorer_judged_fields"]),
        )
        self.assertEqual(
            set(pairs[0]["runs"]["A"]["verifier"]),
            set(policy["verifier_determined_fields"]),
        )
        self.assertEqual(pinned[0]["study_kind"], "skill_primary")

    def test_one_chain_cannot_serve_as_two_pairs(self) -> None:
        """The previous fixture did exactly this and passed."""
        with self.assertRaisesRegex(chain.EvidenceError, "reuses one chain"):
            chain._pairs_from_chains(
                self._dirs() * 2, self.evidence_root, CONTRACT, self.contract
            )

    def test_an_incomplete_chain_is_refused(self) -> None:
        other = self.evidence_root / "chain-2"
        chain.commit_randomization(other, CONTRACT, self.randomization_record)
        with self.assertRaises(chain.EvidenceError):
            chain._pairs_from_chains(
                [self.evidence_relative(other)],
                self.evidence_root, CONTRACT, self.contract,
            )

    def test_a_path_outside_the_evidence_root_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "escapes evidence root"):
            chain._pairs_from_chains(
                ["../outside"], self.evidence_root, CONTRACT, self.contract
            )

    def test_editing_a_submission_after_sealing_is_caught(self) -> None:
        primary = self.evidence_root / "primary.json"
        payload = self.score("primary")
        payload["outputs"][0]["oracle_acceptance"] = False
        write_json(primary, payload)
        with self.assertRaises(chain.EvidenceError):
            chain._pairs_from_chains(
                self._dirs(), self.evidence_root, CONTRACT, self.contract
            )

    def test_cli_publishes_and_verifies_end_to_end(self) -> None:
        sources = self.evidence_root / "sources.json"
        write_json(sources, {"chain_dirs": self._dirs() * 1})
        # One chain is one pair, and a task needs two; prove the CLI surfaces
        # that as a parseable failure rather than a traceback.
        report = self.evidence_root / "report.json"
        code = chain.main([
            "publish-task-decision",
            "--receipt", str(self.receipt),
            "--task-id", "task-1",
            "--study-kind", "skill_primary",
            "--sources", str(sources),
            "--evidence-root", str(self.evidence_root),
            "--contract", str(CONTRACT),
            "--json-out", str(report),
        ])
        self.assertEqual(code, 2)
        parsed = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(parsed["status"], "FAIL")
        self.assertIn("at least two pairs", parsed["error"])
        self.assertFalse(self.receipt.exists())

    def test_cli_verify_reports_a_parseable_failure(self) -> None:
        write_json(self.receipt, {"schema": "wrong"})
        report = self.evidence_root / "verify-report.json"
        code = chain.main([
            "verify-task-decision",
            "--receipt", str(self.receipt),
            "--evidence-root", str(self.evidence_root),
            "--contract", str(CONTRACT),
            "--json-out", str(report),
        ])
        self.assertEqual(code, 2)
        parsed = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(parsed["status"], "FAIL")
        self.assertIn("schema is invalid", parsed["error"])


class Gate3BaselineEvidenceTests(Gate3ChainFixture, unittest.TestCase):
    """regression_baseline_fail must rest on a receipt, not on a flag.

    A metrics observation with an evidence digest that names nothing is
    self-report however well-formed the digest looks.
    """

    def setUp(self) -> None:
        super().setUp()
        self.contract, _ = chain.load_contract(CONTRACT)

    def _seal_with_admission(self, mutate) -> None:
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        mutate(admission)
        write_json(self.admission_b, admission)
        self.seal_pair()

    def _seal_with_metrics(self, mutate) -> None:
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        mutate(metrics)
        write_json(self.metrics_b, metrics)
        self.seal_pair()

    def test_a_fabricated_evidence_digest_is_refused(self) -> None:
        """The exact PoC: a well-formed digest naming nothing."""
        with self.assertRaisesRegex(chain.EvidenceError, "does not name its receipt"):
            self._seal_with_metrics(
                lambda m: m["method_observations"][
                    "failing_regression_before_fix"
                ].update({"evidence_sha256": ["0" * 64]})
            )

    def test_an_absent_baseline_receipt_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "pins no baseline"):
            self._seal_with_admission(
                lambda a: a.pop("baseline_test_receipt")
            )

    def test_a_baseline_receipt_that_passed_is_refused(self) -> None:
        path = self.evidence_root / "baseline-receipt-b.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["exit_code"] = 0
        write_json(path, receipt)
        with self.assertRaises(chain.EvidenceError):
            self._seal_with_admission(
                lambda a: a["baseline_test_receipt"].update(
                    {"sha256": digest(path.read_bytes())}
                )
            )

    def test_a_baseline_receipt_for_another_commit_is_refused(self) -> None:
        path = self.evidence_root / "baseline-receipt-b.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["linked_commit"] = "f" * 40
        write_json(path, receipt)
        with self.assertRaises(chain.EvidenceError):
            self._seal_with_admission(
                lambda a: a["baseline_test_receipt"].update(
                    {"sha256": digest(path.read_bytes())}
                )
            )

    def test_a_tampered_baseline_output_is_refused(self) -> None:
        (self.evidence_root / "baseline-output-b.txt").write_bytes(b"0 failed\n")
        with self.assertRaisesRegex(chain.EvidenceError, "output digest mismatch"):
            self.seal_pair()


class Gate3TaskIdentityTests(Gate3ChainFixture, unittest.TestCase):
    """Identity comes from the sealed chains, not from the caller."""

    def setUp(self) -> None:
        super().setUp()
        self.contract, _ = chain.load_contract(CONTRACT)
        self.full_chain()
        self.pinned = chain._pairs_from_chains(
            [self.evidence_relative(self.chain_dir)],
            self.evidence_root, CONTRACT, self.contract,
        )[1]

    def test_task_id_is_pinned_from_the_randomization_record(self) -> None:
        self.assertEqual(self.pinned[0]["task_id"], "task-1")
        self.assertEqual(self.pinned[0]["study_kind"], "skill_primary")

    def test_a_relabelled_task_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "task_id differs"):
            chain._assert_expected_identity(
                "some-other-task", "skill_primary", self.pinned
            )

    def test_a_relabelled_study_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "study_kind differs"):
            chain._assert_expected_identity(
                "task-1", "governance_diagnostic", self.pinned
            )

    def test_the_matching_identity_is_accepted(self) -> None:
        chain._assert_expected_identity("task-1", "skill_primary", self.pinned)


class Gate3TaskDecisionCliTests(Gate3ChainFixture, unittest.TestCase):
    """The success path, through the CLI, with two distinct chains.

    The previous CLI tests only exercised refusals, so a publish that works
    was never actually run.
    """

    def setUp(self) -> None:
        super().setUp()
        self.contract, _ = chain.load_contract(CONTRACT)
        self.receipt = self.evidence_root / "task-decision.json"
        self.full_chain()
        self.second_chain = self._second_chain()
        self.sources = self.evidence_root / "sources.json"
        write_json(self.sources, {"chain_dirs": [
            self.evidence_relative(self.chain_dir),
            self.evidence_relative(self.second_chain),
        ]})

    def _second_chain(self) -> Path:
        """A genuinely separate pair: new outcomes, new randomization."""
        chain_dir = self.evidence_root / "chain-2"
        mapping = {"OUT-333333333333": "A", "OUT-444444444444": "B"}
        record = self.evidence_root / "randomization-2.json"
        write_json(record, {
            "anonymous_ids": sorted(mapping),
            "mapping_commitment_sha256": chain._mapping_commitment(
                mapping, "skill_primary", self.nonce_hex
            ),
            "pair_id": "task-1-pair-2",
            "repeat_index": 2,
            "schema": "gate3-randomization-record.v1",
            "study_kind": "skill_primary",
            "task_id": "task-1",
            "treatment_inputs": self.treatment_inputs,
        })
        record_sha = digest(record.read_bytes())
        self.common_input_artifacts["randomization_record_sha256"] = {
            "path": self.evidence_relative(record),
            "sha256": record_sha,
        }
        # metrics() reads this directly; leaving it on the first record would
        # make the second pair's admission and metrics disagree.
        self.randomization_sha256 = record_sha
        outcomes = {
            anon: self.make_outcome(
                anon, treat, suffix, completed=True,
                pair_id="task-1-pair-2", repeat_index=2,
            )
            for anon, treat, suffix in (
                ("OUT-333333333333", "A", "c"),
                ("OUT-444444444444", "B", "d"),
            )
        }
        chain.commit_randomization(chain_dir, CONTRACT, record)
        for anon in sorted(outcomes):
            repo, packet, metrics, admission = outcomes[anon]
            chain.seal_outcome(
                chain_dir, CONTRACT, packet, metrics, admission, repo
            )
        chain.close_blind_set(chain_dir, CONTRACT, "skill_primary")
        for role in ("primary", "second"):
            path = self.evidence_root / f"{role}-2.json"
            write_json(path, self.score_for(role, mapping, outcomes))
            chain.submit_scorer(chain_dir, CONTRACT, role, path)
        reveal = self.evidence_root / "mapping-2.json"
        write_json(reveal, {
            "mapping": mapping,
            "nonce_hex": self.nonce_hex,
            "randomization_record_sha256": record_sha,
            "schema": "gate3-mapping-release.v1",
            "study_kind": "skill_primary",
        })
        chain.release_mapping(chain_dir, CONTRACT, reveal)
        return chain_dir

    def score_for(self, role: str, mapping: dict, outcomes: dict) -> dict:
        base = self.score(role)
        base["outputs"] = [
            dict(output, anon_id=anon)
            for output, anon in zip(base["outputs"], sorted(mapping))
        ]
        base["blind_input_set_sha256"] = chain._blind_input_set_sha256({
            anon: {"packet_sha256": digest(outcomes[anon][1].read_bytes())}
            for anon in mapping
        })
        base["scorer_context_id"] = f"{role}-context-2"
        return base

    def _publish(self, out: Path) -> int:
        return chain.main([
            "publish-task-decision",
            "--receipt", str(self.receipt),
            "--task-id", "task-1",
            "--study-kind", "skill_primary",
            "--sources", str(self.sources),
            "--evidence-root", str(self.evidence_root),
            "--contract", str(CONTRACT),
            "--json-out", str(out),
        ])

    def test_cli_publishes_then_verifies(self) -> None:
        report = self.evidence_root / "publish.json"
        self.assertEqual(self._publish(report), 0)
        self.assertEqual(
            json.loads(report.read_text(encoding="utf-8"))["status"], "PASS"
        )
        verify_report = self.evidence_root / "verify.json"
        self.assertEqual(chain.main([
            "verify-task-decision",
            "--receipt", str(self.receipt),
            "--evidence-root", str(self.evidence_root),
            "--contract", str(CONTRACT),
            "--json-out", str(verify_report),
        ]), 0)
        parsed = json.loads(verify_report.read_text(encoding="utf-8"))
        self.assertEqual(parsed["status"], "PASS")
        self.assertIn(parsed["task_status"], {"decided", "third_pair_required"})

    def test_cli_publication_is_create_once(self) -> None:
        self.assertEqual(self._publish(self.evidence_root / "p1.json"), 0)
        report = self.evidence_root / "p2.json"
        self.assertEqual(self._publish(report), 2)
        self.assertEqual(
            json.loads(report.read_text(encoding="utf-8"))["status"], "FAIL"
        )

    def test_cli_refuses_a_relabelled_task(self) -> None:
        report = self.evidence_root / "relabel.json"
        code = chain.main([
            "publish-task-decision",
            "--receipt", str(self.receipt),
            "--task-id", "task-9",
            "--study-kind", "skill_primary",
            "--sources", str(self.sources),
            "--evidence-root", str(self.evidence_root),
            "--contract", str(CONTRACT),
            "--json-out", str(report),
        ])
        self.assertEqual(code, 2)
        self.assertIn(
            "task_id differs",
            json.loads(report.read_text(encoding="utf-8"))["error"],
        )
        self.assertFalse(self.receipt.exists())


class Gate3ScorerPayloadBindingTests(Gate3ChainFixture, unittest.TestCase):
    """What the scorer reads must be what was retained.

    Verbatim from the review that found all three accepted. The bundle, diff
    and receipts can all be correct while the scorer is shown something else.
    """

    def _seal_with_payload(self, field: str, value: object) -> None:
        packet = json.loads(self.packet_b.read_text(encoding="utf-8"))
        packet["scorer_payload"][field] = value
        write_json(self.packet_b, packet)
        packet_sha = digest(self.packet_b.read_bytes())
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["output_packet_sha256"] = packet_sha
        write_json(self.admission_b, admission)
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["artifacts"]["output_packet_sha256"] = packet_sha
        write_json(self.metrics_b, metrics)
        self.seal_pair()

    def test_a_substituted_diff_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "differs from the retained diff"):
            self._seal_with_payload(
                "final_diff_utf8", "THIS IS NOT THE RETAINED DIFF"
            )

    def test_a_fabricated_exit_code_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "differs from the retained receipts"):
            self._seal_with_payload("test_exit_code", 999)

    def test_a_boolean_exit_code_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "differs from the retained receipts"):
            self._seal_with_payload("test_exit_code", True)

    def test_a_fabricated_baseline_digest_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "differs from the admitted one"):
            self._seal_with_payload("baseline_test_receipt_sha256", "0" * 64)


class Gate3ObservationEvidenceTests(Gate3ChainFixture, unittest.TestCase):
    """An observation whose evidence resolves to nothing is an assertion."""

    def _seal_with_observation(self, name: str, value: dict) -> None:
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["method_observations"][name] = value
        write_json(self.metrics_b, metrics)
        self.seal_pair()

    def test_a_fabricated_observation_digest_is_refused(self) -> None:
        """The review's proof-of-concept, verbatim."""
        with self.assertRaisesRegex(
            chain.EvidenceError, "resolves to no retained artifact"
        ):
            self._seal_with_observation(
                "claim_bounded_to_evidence",
                {"observed": True, "evidence_sha256": ["0" * 64]},
            )

    def test_an_observed_claim_without_evidence_is_refused(self) -> None:
        # validate_metrics already refuses this, with its own wording.
        with self.assertRaisesRegex(chain.EvidenceError, "lacks digest evidence"):
            self._seal_with_observation(
                "claim_bounded_to_evidence",
                {"observed": True, "evidence_sha256": []},
            )

    def test_an_observation_naming_a_retained_artifact_is_accepted(self) -> None:
        self._seal_with_observation(
            "claim_bounded_to_evidence",
            {"observed": True, "evidence_sha256": [self.baseline_receipt_sha256]},
        )

    def test_an_unobserved_claim_needs_no_evidence(self) -> None:
        self._seal_with_observation(
            "claim_bounded_to_evidence",
            {"observed": False, "evidence_sha256": []},
        )


class Gate3BaselineTypeTests(Gate3ChainFixture, unittest.TestCase):
    """bool is an int, and an unobserved flag is not an observation."""

    def _reseal(self, mutate) -> None:
        path = self.evidence_root / "baseline-receipt-b.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        mutate(receipt)
        write_json(path, receipt)
        new_sha = digest(path.read_bytes())
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["baseline_test_receipt"]["sha256"] = new_sha
        write_json(self.admission_b, admission)
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["method_observations"]["failing_regression_before_fix"][
            "evidence_sha256"
        ] = [new_sha]
        write_json(self.metrics_b, metrics)
        packet = json.loads(self.packet_b.read_text(encoding="utf-8"))
        packet["scorer_payload"]["baseline_test_receipt_sha256"] = new_sha
        write_json(self.packet_b, packet)
        packet_sha = digest(self.packet_b.read_bytes())
        admission = json.loads(self.admission_b.read_text(encoding="utf-8"))
        admission["output_packet_sha256"] = packet_sha
        write_json(self.admission_b, admission)
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["artifacts"]["output_packet_sha256"] = packet_sha
        write_json(self.metrics_b, metrics)
        self.seal_pair()

    def test_a_boolean_exit_code_cannot_impersonate_a_failure(self) -> None:
        """The review's proof-of-concept, verbatim: exit_code true."""
        with self.assertRaisesRegex(chain.EvidenceError, "did not fail"):
            self._reseal(lambda r: r.update({"exit_code": True}))

    def test_a_commandless_baseline_receipt_is_refused(self) -> None:
        with self.assertRaisesRegex(chain.EvidenceError, "names no command"):
            self._reseal(lambda r: r.update({"command": "   "}))

    def test_an_unobserved_baseline_flag_is_refused(self) -> None:
        metrics = json.loads(self.metrics_b.read_text(encoding="utf-8"))
        metrics["method_observations"]["failing_regression_before_fix"][
            "observed"
        ] = False
        write_json(self.metrics_b, metrics)
        with self.assertRaisesRegex(
            chain.EvidenceError, "does not name its receipt"
        ):
            self.seal_pair()
