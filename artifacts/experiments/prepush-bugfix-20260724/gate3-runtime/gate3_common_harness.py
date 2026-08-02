from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import gate3_evidence_chain as chain


HERE = Path(__file__).resolve().parent
EXPERIMENT_ROOT = HERE.parent
DEFAULT_CONTRACT = (
    EXPERIMENT_ROOT / "candidate/gate3-protocol-contract-v1.json"
)
DEFAULT_HARNESS_CONTRACT = (
    EXPERIMENT_ROOT / "candidate/gate3-harness-contract-v1.json"
)
DEFAULT_CANDIDATE_MANIFEST = (
    EXPERIMENT_ROOT
    / "candidate/gate3-preregistration-amendment-v1-candidate-manifest.json"
)

REHEARSAL_SCHEMA = "gate3-common-harness-rehearsal.v1"
WRITE_RECEIPT_SCHEMA = "gate3-structured-write-receipt.v1"
CAPTURE_RECEIPT_SCHEMA = "gate3-live-capture-receipt.v1"
BASELINE_RECEIPT_SCHEMA = "gate3-synthetic-baseline-test-receipt.v1"
AUTHORIZATION = "non_counted_synthetic_rehearsal_only"
EXPECTED_CANDIDATE_MANIFEST_SHA256 = (
    "d64817c2ceb190f43764b0d08c098deb821ca4755e273e045dec34812cc97d00"
)
ANON_MAPPING = {
    "OUT-111111111111": "A",
    "OUT-222222222222": "B",
}
COMMIT_ENV = {
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
}
REGRESSION_SNIPPET = (
    "from calc import add; "
    "raise SystemExit(0 if add(2, 3) == 5 else 1)"
)


class HarnessError(ValueError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: object) -> bytes:
    return chain._json_bytes(value)


def _load_json(path: Path) -> dict[str, Any]:
    return chain._load_json(path)


def _write_json(path: Path, value: object) -> None:
    chain._atomic_write(path, _json_bytes(value))


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=process_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise HarnessError(
            f"command failed ({completed.returncode}): "
            f"{' '.join(command)}: {detail}"
        )
    return completed


def _git(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> bytes:
    return _run(["git", *args], cwd=repo, env=env).stdout


def _relative(path: Path, evidence_root: Path) -> str:
    try:
        return path.resolve().relative_to(evidence_root.resolve()).as_posix()
    except ValueError as exc:
        raise HarnessError(
            f"artifact escapes rehearsal evidence root: {path}"
        ) from exc


def _artifact_entry(path: Path, evidence_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "path": _relative(path, evidence_root),
        "sha256": _sha256_bytes(raw),
    }


def _retain(
    evidence_root: Path,
    relative: str,
    payload: bytes,
) -> dict[str, str]:
    path = evidence_root.joinpath(*relative.split("/"))
    chain._atomic_write(path, payload)
    return {
        "path": _relative(path, evidence_root),
        "sha256": _sha256_bytes(payload),
    }


def structured_write(
    repo_root: Path,
    relative_path: str,
    payload: bytes,
    receipt_path: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise HarnessError("structured write payload must be bytes")
    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise HarnessError("structured write target must be a safe relative path")
    target = repo_root.joinpath(*relative.parts)
    try:
        target.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise HarnessError("structured write target escapes repository") from exc
    chain._atomic_write(target, payload)
    stored = target.read_bytes()
    requested_sha = _sha256_bytes(payload)
    stored_sha = _sha256_bytes(stored)
    receipt = {
        "authorization": AUTHORIZATION,
        "match": stored == payload,
        "requested_bytes": len(payload),
        "requested_sha256": requested_sha,
        "schema": WRITE_RECEIPT_SCHEMA,
        "stored_bytes": len(stored),
        "stored_sha256": stored_sha,
        "target_path": relative.as_posix(),
    }
    if receipt["match"] is not True:
        raise HarnessError("structured write stored bytes differ from request")
    _write_json(receipt_path, receipt)
    return {
        **receipt,
        "receipt_path": _relative(receipt_path, evidence_root),
        "receipt_sha256": _sha256_file(receipt_path),
    }


def _init_base_repo(work_root: Path) -> tuple[Path, str]:
    repo = work_root / "base"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "gate3-rehearsal@example.invalid")
    _git(repo, "config", "user.name", "Gate3 Rehearsal")
    (repo / "calc.py").write_bytes(
        b"def add(a, b):\n    return a - b\n"
    )
    (repo / "test_calc.py").write_bytes(
        b"import unittest\n"
        b"from calc import add\n\n"
        b"class CalcTests(unittest.TestCase):\n"
        b"    def test_add(self):\n"
        b"        self.assertEqual(add(2, 3), 5)\n\n"
        b"if __name__ == '__main__':\n"
        b"    unittest.main()\n"
    )
    _git(repo, "add", "calc.py", "test_calc.py")
    _git(repo, "commit", "-q", "-m", "synthetic baseline", env=COMMIT_ENV)
    commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return repo, commit


def _common_inputs(
    evidence_root: Path,
    harness_contract_path: Path,
) -> dict[str, dict[str, str]]:
    return {
        "baseline_instruction_sha256": _retain(
            evidence_root,
            "inputs/baseline-instruction.txt",
            b"Start from the planted subtraction defect.\n",
        ),
        "task_packet_sha256": _retain(
            evidence_root,
            "inputs/task-packet.txt",
            b"Repair add() and preserve the regression test.\n",
        ),
        "permissions_sha256": _retain(
            evidence_root,
            "inputs/permissions.json",
            b'{"mode":"synthetic_rehearsal","network":false}\n',
        ),
        "budget_sha256": _retain(
            evidence_root,
            "inputs/budget.json",
            b'{"tool_calls":8,"wall_clock_seconds":120}\n',
        ),
        "harness_contract_sha256": _retain(
            evidence_root,
            "inputs/gate3-harness-contract-v1.json",
            harness_contract_path.read_bytes(),
        ),
        "scorer_rubric_sha256": _retain(
            evidence_root,
            "inputs/scorer-rubric.txt",
            b"Synthetic scorer: verify completion fields only; do not rank arms.\n",
        ),
    }


def _treatment_inputs(
    evidence_root: Path,
) -> dict[str, dict[str, dict[str, str]]]:
    values: dict[str, dict[str, dict[str, str]]] = {}
    for treatment in ("A", "B"):
        lower = treatment.lower()
        values[treatment] = {
            "treatment_packet_sha256": _retain(
                evidence_root,
                f"inputs/treatment-{lower}.txt",
                f"synthetic treatment {treatment}\n".encode("utf-8"),
            ),
            # Shared content across arms on purpose. A skill_primary
            # comparison varies the treatment packet and nothing else; these
            # previously differed per arm, which made the rehearsal model a
            # comparison that could not be interpreted.
            "governance_instruction_sha256": _retain(
                evidence_root,
                f"inputs/governance-{lower}.txt",
                b"governance instructions\n",
            ),
            "validator_bundle_sha256": _retain(
                evidence_root,
                f"inputs/validator-{lower}.py",
                b"def validate():\n    return True\n",
            ),
            "validator_config_sha256": _retain(
                evidence_root,
                f"inputs/validator-{lower}.json",
                (
                    json.dumps({"mode": "shared"}, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            ),
        }
    return values


def _capture_receipt(
    repo: Path,
    evidence_root: Path,
    outcome_dir: Path,
    baseline_commit: str,
    output_commit: str,
) -> dict[str, Any]:
    head_raw = _git(repo, "rev-parse", "HEAD")
    status_raw = _git(
        repo, "status", "--porcelain=v1", "--untracked-files=all"
    )
    head_path = outcome_dir / "live-head.txt"
    status_path = outcome_dir / "live-status.txt"
    chain._atomic_write(head_path, head_raw)
    chain._atomic_write(status_path, status_raw)
    receipt_path = outcome_dir / "live-capture-receipt.json"
    value = {
        "authorization": AUTHORIZATION,
        "baseline_commit": baseline_commit,
        "clean": status_raw == b"",
        "head_path": _relative(head_path, evidence_root),
        "head_sha256": _sha256_bytes(head_raw),
        "output_commit": output_commit,
        "schema": CAPTURE_RECEIPT_SCHEMA,
        "status_path": _relative(status_path, evidence_root),
        "status_sha256": _sha256_bytes(status_raw),
    }
    if value["clean"] is not True or head_raw != (
        output_commit + "\n"
    ).encode("ascii"):
        raise HarnessError("live capture is not clean at output commit")
    _write_json(receipt_path, value)
    return {
        "path": _relative(receipt_path, evidence_root),
        "sha256": _sha256_file(receipt_path),
    }


def _regression_command_label() -> str:
    return (
        f'{Path(sys.executable).name} -B -c "{REGRESSION_SNIPPET}"'
    )


def _run_tests(repo: Path) -> tuple[int, bytes]:
    completed = subprocess.run(
        [sys.executable, "-B", "-c", REGRESSION_SNIPPET],
        cwd=repo,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def _record_baseline_failure(
    base_repo: Path,
    baseline_commit: str,
    evidence_root: Path,
) -> dict[str, Any]:
    exit_code, output = _run_tests(base_repo)
    if exit_code == 0:
        raise HarnessError("synthetic baseline unexpectedly passed")
    output_path = evidence_root / "baseline-test-output.txt"
    receipt_path = evidence_root / "baseline-test-receipt.json"
    chain._atomic_write(output_path, output)
    receipt = {
        "authorization": AUTHORIZATION,
        "command": _regression_command_label(),
        "exit_code": exit_code,
        "expected_failure": True,
        "linked_commit": baseline_commit,
        "output_path": _relative(output_path, evidence_root),
        "output_sha256": _sha256_file(output_path),
        "schema": BASELINE_RECEIPT_SCHEMA,
    }
    _write_json(receipt_path, receipt)
    return {
        "path": _relative(receipt_path, evidence_root),
        "sha256": _sha256_file(receipt_path),
    }


def _method_observations(
    baseline_receipt_sha256: str | None = None,
) -> dict[str, dict[str, Any]]:
    names = (
        "reproduction_before_first_edit",
        "root_cause_recorded_before_first_edit",
        "failing_regression_before_fix",
        "defect_reintroduction_performed",
        "post_restore_retest_performed",
        "claim_bounded_to_evidence",
    )
    values = {
        name: {"evidence_sha256": [], "observed": False}
        for name in names
    }
    if baseline_receipt_sha256 is not None:
        # The observation has to name the retained receipt; an empty evidence
        # list would make regression_baseline_fail self-reported.
        values["failing_regression_before_fix"] = {
            "evidence_sha256": [baseline_receipt_sha256],
            "observed": True,
        }
    return values


def _build_outcome(
    *,
    anon_id: str,
    treatment: str,
    suffix: str,
    base_repo: Path,
    baseline_commit: str,
    work_root: Path,
    evidence_root: Path,
    chain_dir: Path,
    contract_path: Path,
    common_inputs: dict[str, dict[str, str]],
    treatment_inputs: dict[str, dict[str, dict[str, str]]],
    randomization_sha256: str,
    baseline_test_receipt: dict[str, str],
) -> dict[str, Any]:
    baseline_test_receipt_sha256 = baseline_test_receipt["sha256"]
    repo = work_root / f"repo-{suffix}"
    _git(work_root, "clone", "--quiet", str(base_repo), str(repo))
    _git(repo, "config", "user.email", "gate3-rehearsal@example.invalid")
    _git(repo, "config", "user.name", "Gate3 Rehearsal")
    outcome_dir = evidence_root / "outcomes" / suffix
    outcome_dir.mkdir(parents=True)

    payload = b"def add(a, b):\n    return a + b\n"
    write_receipt_path = outcome_dir / "structured-write-receipt.json"
    write_receipt = structured_write(
        repo,
        "calc.py",
        payload,
        write_receipt_path,
        evidence_root,
    )
    _git(repo, "add", "calc.py")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        f"synthetic output {treatment}",
        env=COMMIT_ENV,
    )
    output_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    test_exit, test_output = _run_tests(repo)
    test_output_path = outcome_dir / "test-output.txt"
    chain._atomic_write(test_output_path, test_output)
    if test_exit != 0:
        raise HarnessError(
            f"synthetic outcome {treatment} tests failed: "
            f"{test_output.decode('utf-8', errors='replace')}"
        )
    test_receipt_path = outcome_dir / "test-receipt.json"
    _write_json(
        test_receipt_path,
        {
            "command": _regression_command_label(),
            "exit_code": test_exit,
            "linked_commit": output_commit,
            "output_path": _relative(test_output_path, evidence_root),
            "output_sha256": _sha256_file(test_output_path),
            "schema": chain.RECEIPT_SCHEMA,
        },
    )
    receipt_index = [
        {
            "path": _relative(test_receipt_path, evidence_root),
            "sha256": _sha256_file(test_receipt_path),
        }
    ]
    receipt_set_sha = _sha256_bytes(_json_bytes(receipt_index))

    final_diff = outcome_dir / "final-diff.patch"
    chain._atomic_write(
        final_diff,
        _git(
            repo,
            "diff",
            "--binary",
            "--full-index",
            baseline_commit,
            output_commit,
            "--",
        ),
    )
    tracked = [
        item.decode("utf-8")
        for item in _git(
            repo,
            "diff",
            "--name-only",
            "-z",
            baseline_commit,
            output_commit,
            "--",
        ).split(b"\0")
        if item
    ]
    bundle = outcome_dir / "repo.bundle"
    _git(repo, "bundle", "create", str(bundle), "--all")

    capture_receipt = _capture_receipt(
        repo,
        evidence_root,
        outcome_dir,
        baseline_commit,
        output_commit,
    )
    event_log = outcome_dir / "event-log.jsonl"
    event_lines = [
        {
            "event": "structured_write",
            "receipt_sha256": write_receipt["receipt_sha256"],
        },
        {
            "event": "tests_passed",
            "receipt_sha256": _sha256_file(test_receipt_path),
        },
        {
            "event": "clean_capture",
            "receipt_sha256": capture_receipt["sha256"],
        },
    ]
    chain._atomic_write(
        event_log,
        b"".join(
            json.dumps(item, sort_keys=True).encode("utf-8") + b"\n"
            for item in event_lines
        ),
    )

    harness_sha = common_inputs["harness_contract_sha256"]["sha256"]
    packet_path = outcome_dir / "scorer-packet.json"
    _write_json(
        packet_path,
        {
            "anon_id": anon_id,
            "baseline_commit": baseline_commit,
            "final_diff_sha256": _sha256_file(final_diff),
            "harness_contract_sha256": harness_sha,
            "output_commit": output_commit,
            "receipt_set_sha256": receipt_set_sha,
            "schema": chain.OUTCOME_PACKET_SCHEMA,
            "scorer_payload": {
                "baseline_test_receipt_sha256": (
                    baseline_test_receipt_sha256
                ),
                "final_diff_utf8": final_diff.read_text(encoding="utf-8"),
                "test_exit_code": test_exit,
            },
        },
    )
    input_artifacts = {
        **copy.deepcopy(common_inputs),
        **copy.deepcopy(treatment_inputs[treatment]),
    }
    input_digests = {
        field: entry["sha256"]
        for field, entry in input_artifacts.items()
    }
    admission_path = outcome_dir / "admission.json"
    _write_json(
        admission_path,
        {
            "anon_id": anon_id,
            "baseline_commit": baseline_commit,
            "baseline_test_receipt": dict(baseline_test_receipt),
            "event_log": {
                "path": _relative(event_log, evidence_root),
                "sha256": _sha256_file(event_log),
            },
            "final_diff": {
                "path": _relative(final_diff, evidence_root),
                "sha256": _sha256_file(final_diff),
                "tracked_changed_files": tracked,
            },
            "git_bundle": {
                "path": _relative(bundle, evidence_root),
                "sha256": _sha256_file(bundle),
            },
            "input_artifacts": input_artifacts,
            "input_digests": input_digests,
            "model_build": "synthetic-model-build-v1",
            "output_commit": output_commit,
            "output_packet_sha256": _sha256_file(packet_path),
            "receipt_set_sha256": receipt_set_sha,
            "receipts": receipt_index,
            "schema": chain.ADMISSION_SCHEMA,
            "treatment": treatment,
            "worktree_clean_at_capture": True,
        },
    )
    metrics_path = outcome_dir / "metrics.json"
    _write_json(
        metrics_path,
        {
            "anon_id": anon_id,
            "artifacts": {
                "event_log_sha256": _sha256_file(event_log),
                "output_packet_sha256": _sha256_file(packet_path),
            },
            "baseline_commit": baseline_commit,
            "budget_sha256": common_inputs["budget_sha256"]["sha256"],
            "completed_under_cap": True,
            "conditional_quality_eligible": True,
            "costs": {
                "changed_files": len(tracked),
                "core_available": True,
                "diff_bytes": len(final_diff.read_bytes()),
                "owner_interventions": 0,
                "retries": 0,
                "rework_count": 0,
                "tokens": {
                    "available": False,
                    "reason": "synthetic harness exposes no token telemetry",
                },
                "tool_calls": 4,
                "wall_clock_ms": 1000 if treatment == "A" else 1100,
            },
            "harness_contract_sha256": harness_sha,
            "method_observations": _method_observations(
                baseline_test_receipt_sha256
            ),
            "model_build": "synthetic-model-build-v1",
            "pair_id": "synthetic-pair-1",
            "permissions_sha256": common_inputs[
                "permissions_sha256"
            ]["sha256"],
            "randomization_record_sha256": randomization_sha256,
            "repeat_index": 1,
            "run_id": f"synthetic-run-{treatment.lower()}",
            "schema": chain.METRICS_SCHEMA,
            "scorer_rubric_sha256": common_inputs[
                "scorer_rubric_sha256"
            ]["sha256"],
            "status": "completed",
            "task_id": "synthetic-task-1",
            "task_packet_sha256": common_inputs[
                "task_packet_sha256"
            ]["sha256"],
            "timestamps": {
                "finished_at": "2026-07-29T06:01:00+00:00",
                "first_edit_at": "2026-07-29T06:00:30+00:00",
                "started_at": "2026-07-29T06:00:00+00:00",
            },
        },
    )
    chain.seal_outcome(
        chain_dir,
        contract_path,
        packet_path,
        metrics_path,
        admission_path,
        repo,
    )
    return {
        "admission_path": _relative(admission_path, evidence_root),
        "anon_id": anon_id,
        "capture_receipt": capture_receipt,
        "metrics_path": _relative(metrics_path, evidence_root),
        "output_commit": output_commit,
        "packet_path": _relative(packet_path, evidence_root),
        "treatment": treatment,
        "write_receipt_path": write_receipt["receipt_path"],
        "write_receipt_sha256": write_receipt["receipt_sha256"],
    }


def _score(
    role: str,
    outcome_entries: list[dict[str, Any]],
    scorer_rubric_sha256: str,
    blind_input_set_sha256: str,
) -> dict[str, Any]:
    outputs = []
    for outcome in sorted(outcome_entries, key=lambda item: item["anon_id"]):
        outputs.append(
            {
                "anon_id": outcome["anon_id"],
                "claim_mismatch_count": 0,
                "completed_under_cap": True,
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
        )
    return {
        "blind_input_set_sha256": blind_input_set_sha256,
        "independence_declaration": True,
        "model_build": "synthetic-scorer-build-v1",
        "outputs": outputs,
        "schema": chain.SCORE_SCHEMA,
        "scorer_context_id": f"synthetic-{role}-context",
        "scorer_identity": f"synthetic-{role}-scorer",
        "scorer_role": role,
        "scorer_rubric_sha256": scorer_rubric_sha256,
    }


def _inventory(evidence_root: Path) -> list[dict[str, Any]]:
    summary_path = evidence_root / "rehearsal-summary.json"
    paths = [
        path
        for path in sorted(evidence_root.rglob("*"))
        if path.is_file() and path != summary_path
    ]
    symlinks = [path for path in paths if path.is_symlink()]
    if symlinks:
        raise HarnessError(
            "rehearsal artifact inventory may not contain symlinks"
        )
    return [_artifact_entry(path, evidence_root) for path in paths]


def _build_into(
    repo_root: Path,
    evidence_root: Path,
    nonce_hex: str,
) -> dict[str, Any]:
    contract_path = repo_root / DEFAULT_CONTRACT.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    harness_contract_path = repo_root / DEFAULT_HARNESS_CONTRACT.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    manifest_path = repo_root / DEFAULT_CANDIDATE_MANIFEST.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    if _sha256_file(manifest_path) != EXPECTED_CANDIDATE_MANIFEST_SHA256:
        raise HarnessError("candidate manifest is not the merged reviewed identity")
    candidate_result = chain.verify_candidate(repo_root, manifest_path)
    if candidate_result["status"] != "PASS":
        raise HarnessError("candidate verification did not pass")
    if len(nonce_hex) != 64 or any(
        character not in "0123456789abcdef" for character in nonce_hex
    ):
        raise HarnessError("rehearsal nonce must be 64 lowercase hex characters")

    evidence_root.mkdir(parents=True, exist_ok=True)
    chain_dir = evidence_root / "chain"
    common_inputs = _common_inputs(evidence_root, harness_contract_path)
    treatment_artifacts = _treatment_inputs(evidence_root)
    treatment_digests = {
        treatment: {
            field: entry["sha256"]
            for field, entry in artifacts.items()
        }
        for treatment, artifacts in treatment_artifacts.items()
    }
    randomization_path = evidence_root / "randomization-record.json"
    _write_json(
        randomization_path,
        {
            "anonymous_ids": sorted(ANON_MAPPING),
            "mapping_commitment_sha256": chain._mapping_commitment(
                ANON_MAPPING, "skill_primary", nonce_hex
            ),
            "pair_id": "synthetic-pair-1",
            "repeat_index": 1,
            "schema": chain.RANDOMIZATION_SCHEMA,
            "study_kind": "skill_primary",
            "task_id": "synthetic-task-1",
            "treatment_inputs": treatment_digests,
        },
    )
    randomization_sha = _sha256_file(randomization_path)
    common_inputs["randomization_record_sha256"] = {
        "path": _relative(randomization_path, evidence_root),
        "sha256": randomization_sha,
    }
    chain.commit_randomization(chain_dir, contract_path, randomization_path)

    with tempfile.TemporaryDirectory(prefix="gate3-common-harness-work-") as temp:
        work_root = Path(temp)
        base_repo, baseline_commit = _init_base_repo(work_root)
        baseline_test_receipt = _record_baseline_failure(
            base_repo,
            baseline_commit,
            evidence_root,
        )
        outcomes = []
        for anon_id, treatment in sorted(ANON_MAPPING.items()):
            outcomes.append(
                _build_outcome(
                    anon_id=anon_id,
                    treatment=treatment,
                    suffix=treatment.lower(),
                    base_repo=base_repo,
                    baseline_commit=baseline_commit,
                    work_root=work_root,
                    evidence_root=evidence_root,
                    chain_dir=chain_dir,
                    contract_path=contract_path,
                    common_inputs=common_inputs,
                    treatment_inputs=treatment_artifacts,
                    randomization_sha256=randomization_sha,
                    baseline_test_receipt=baseline_test_receipt,
                )
            )

    chain.close_blind_set(chain_dir, contract_path, "skill_primary")
    close_event = _load_json(chain._event_files(chain_dir)[3])
    for role in ("primary", "second"):
        score_path = evidence_root / f"synthetic-{role}-score.json"
        _write_json(
            score_path,
            _score(
                role,
                outcomes,
                common_inputs["scorer_rubric_sha256"]["sha256"],
                close_event["blind_input_set_sha256"],
            ),
        )
        chain.submit_scorer(chain_dir, contract_path, role, score_path)
    mapping_path = evidence_root / "mapping-reveal.json"
    _write_json(
        mapping_path,
        {
            "mapping": ANON_MAPPING,
            "nonce_hex": nonce_hex,
            "randomization_record_sha256": randomization_sha,
            "schema": chain.MAPPING_SCHEMA,
            "study_kind": "skill_primary",
        },
    )
    chain.release_mapping(chain_dir, contract_path, mapping_path)
    chain_result = chain.verify_chain(
        chain_dir, contract_path, require_state="mapping_released"
    )
    summary = {
        "artifact_inventory": _inventory(evidence_root),
        "authorization": AUTHORIZATION,
        "baseline_test_receipt": baseline_test_receipt,
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
        "candidate_verification_checks": len(candidate_result["checks"]),
        "chain": {
            "event_count": chain_result["event_count"],
            "head_sha256": chain_result["head_sha256"],
            "state": chain_result["state"],
        },
        "harness_implementation_sha256": _sha256_file(Path(__file__)),
        "not_claimed": [
            "independent approval",
            "owner signature",
            "canonical promotion",
            "natural bug admission",
            "counted Gate 3 run",
            "Gate 3 start",
            "Skill effectiveness",
            "cryptographic writer authentication",
        ],
        "outcomes": sorted(outcomes, key=lambda item: item["anon_id"]),
        "rehearsal_kind": "fresh_synthetic_non_counted",
        "schema": REHEARSAL_SCHEMA,
    }
    _write_json(evidence_root / "rehearsal-summary.json", summary)
    return summary


def build_rehearsal(
    repo_root: Path,
    output_root: Path,
    *,
    nonce_hex: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise HarnessError(f"rehearsal output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    # tempfile.mkdtemp() installs a private, protected ACL on Windows. Renaming
    # that directory into the evidence tree preserves the ACL and can make the
    # published packet unreadable to a later operator or Git process. A normal
    # sibling mkdir inherits the repository ACL while retaining create-once,
    # unpredictable publication semantics.
    temporary = output_root.parent / (
        f".{output_root.name}.{secrets.token_hex(16)}"
    )
    temporary.mkdir()
    published = False
    try:
        _build_into(repo_root, temporary, nonce_hex or secrets.token_hex(32))
        verify_rehearsal(repo_root, temporary)
        os.rename(temporary, output_root)
        published = True
        return verify_rehearsal(repo_root, output_root)
    except BaseException:
        cleanup = output_root if published else temporary
        shutil.rmtree(cleanup, ignore_errors=True)
        raise


def _verify_inventory(
    evidence_root: Path,
    expected: object,
) -> None:
    if not isinstance(expected, list):
        raise HarnessError("rehearsal artifact inventory is absent")
    actual = _inventory(evidence_root)
    if expected != actual:
        raise HarnessError("rehearsal artifact inventory mismatch")


def _verify_baseline_receipt(
    evidence_root: Path,
    entry: object,
) -> tuple[str, str]:
    if not isinstance(entry, dict):
        raise HarnessError("baseline test receipt entry is absent")
    path = chain._source_from_event(
        entry.get("path"), evidence_root / "chain"
    )
    if entry.get("sha256") != _sha256_file(path):
        raise HarnessError("baseline test receipt digest mismatch")
    receipt = _load_json(path)
    output_path = chain._source_from_event(
        receipt.get("output_path"), evidence_root / "chain"
    )
    if (
        receipt.get("schema") != BASELINE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("expected_failure") is not True
        or not isinstance(receipt.get("exit_code"), int)
        or isinstance(receipt.get("exit_code"), bool)
        or receipt["exit_code"] == 0
        or not chain.HEX40.fullmatch(str(receipt.get("linked_commit", "")))
        or not output_path.is_file()
        or receipt.get("output_sha256") != _sha256_file(output_path)
    ):
        raise HarnessError("baseline test receipt is invalid")
    return receipt["linked_commit"], entry["sha256"]


def _verify_write_receipt(
    evidence_root: Path,
    outcome: dict[str, Any],
    admission: dict[str, Any],
) -> None:
    receipt_path = chain._source_from_event(
        outcome.get("write_receipt_path"), evidence_root / "chain"
    )
    receipt = _load_json(receipt_path)
    if (
        receipt.get("schema") != WRITE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("match") is not True
        or receipt.get("requested_bytes") != receipt.get("stored_bytes")
        or receipt.get("requested_sha256") != receipt.get("stored_sha256")
        or receipt.get("target_path") != "calc.py"
        or outcome.get("write_receipt_sha256") != _sha256_file(receipt_path)
    ):
        raise HarnessError("structured write receipt is invalid")
    bundle_path = chain._source_from_event(
        admission["git_bundle"]["path"], evidence_root / "chain"
    )
    with tempfile.TemporaryDirectory(prefix="gate3-write-verify-") as temp:
        clone = Path(temp) / "repo"
        _run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                str(bundle_path),
                str(clone),
            ],
            cwd=Path(temp),
        )
        stored = _git(
            clone,
            "show",
            f"{admission['output_commit']}:{receipt['target_path']}",
        )
    if (
        len(stored) != receipt["stored_bytes"]
        or _sha256_bytes(stored) != receipt["stored_sha256"]
    ):
        raise HarnessError("structured write receipt does not match bundled output")


def _verify_capture_receipt(
    evidence_root: Path,
    outcome: dict[str, Any],
    admission: dict[str, Any],
) -> None:
    entry = outcome.get("capture_receipt")
    if not isinstance(entry, dict):
        raise HarnessError("live capture receipt entry is absent")
    path = chain._source_from_event(entry.get("path"), evidence_root / "chain")
    if entry.get("sha256") != _sha256_file(path):
        raise HarnessError("live capture receipt digest mismatch")
    receipt = _load_json(path)
    head_path = chain._source_from_event(
        receipt.get("head_path"), evidence_root / "chain"
    )
    status_path = chain._source_from_event(
        receipt.get("status_path"), evidence_root / "chain"
    )
    if (
        receipt.get("schema") != CAPTURE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("clean") is not True
        or receipt.get("baseline_commit") != admission["baseline_commit"]
        or receipt.get("output_commit") != outcome.get("output_commit")
        or receipt.get("output_commit") != admission["output_commit"]
        or receipt.get("head_sha256") != _sha256_file(head_path)
        or receipt.get("status_sha256") != _sha256_file(status_path)
        or status_path.read_bytes() != b""
        or head_path.read_bytes()
        != (str(outcome["output_commit"]) + "\n").encode("ascii")
    ):
        raise HarnessError("live capture receipt is invalid")


def verify_rehearsal(
    repo_root: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    evidence_root = evidence_root.resolve()
    summary_path = evidence_root / "rehearsal-summary.json"
    summary_raw = summary_path.read_bytes()
    summary = _load_json(summary_path)
    if summary_raw != _json_bytes(summary):
        raise HarnessError("rehearsal summary is not canonical JSON")
    if (
        summary.get("schema") != REHEARSAL_SCHEMA
        or summary.get("authorization") != AUTHORIZATION
        or summary.get("rehearsal_kind") != "fresh_synthetic_non_counted"
        or summary.get("candidate_manifest_sha256")
        != EXPECTED_CANDIDATE_MANIFEST_SHA256
        or summary.get("harness_implementation_sha256")
        != _sha256_file(Path(__file__))
    ):
        raise HarnessError("rehearsal summary identity is invalid")
    manifest_path = repo_root / DEFAULT_CANDIDATE_MANIFEST.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    if _sha256_file(manifest_path) != EXPECTED_CANDIDATE_MANIFEST_SHA256:
        raise HarnessError("candidate manifest changed after rehearsal")
    candidate_result = chain.verify_candidate(repo_root, manifest_path)
    if summary.get("candidate_verification_checks") != len(
        candidate_result["checks"]
    ):
        raise HarnessError("candidate verification check count mismatch")
    _verify_inventory(evidence_root, summary.get("artifact_inventory"))
    baseline_commit, baseline_receipt_sha = _verify_baseline_receipt(
        evidence_root, summary.get("baseline_test_receipt")
    )

    contract_path = repo_root / DEFAULT_CONTRACT.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    contract, _ = chain.load_contract(contract_path)
    chain_result = chain.verify_chain(
        evidence_root / "chain",
        contract_path,
        require_state="mapping_released",
    )
    if summary.get("chain") != {
        "event_count": chain_result["event_count"],
        "head_sha256": chain_result["head_sha256"],
        "state": chain_result["state"],
    }:
        raise HarnessError("rehearsal chain summary mismatch")
    outcomes = summary.get("outcomes")
    if (
        not isinstance(outcomes, list)
        or len(outcomes) != 2
        or {item.get("anon_id") for item in outcomes} != set(ANON_MAPPING)
    ):
        raise HarnessError("rehearsal outcome population is invalid")
    for outcome in outcomes:
        packet_path = chain._source_from_event(
            outcome.get("packet_path"), evidence_root / "chain"
        )
        metrics_path = chain._source_from_event(
            outcome.get("metrics_path"), evidence_root / "chain"
        )
        admission_path = chain._source_from_event(
            outcome.get("admission_path"), evidence_root / "chain"
        )
        metrics = chain.validate_metrics(
            _load_json(metrics_path),
            contract,
            packet_sha256=_sha256_file(packet_path),
        )
        admission = chain.validate_admission(
            admission_path,
            packet_path,
            metrics,
            contract,
            evidence_root / "chain",
        )
        packet = _load_json(packet_path)
        if (
            admission["anon_id"] != outcome["anon_id"]
            or admission["treatment"] != outcome["treatment"]
            or admission["output_commit"] != outcome["output_commit"]
            or admission["baseline_commit"] != baseline_commit
            or packet["scorer_payload"].get(
                "baseline_test_receipt_sha256"
            )
            != baseline_receipt_sha
        ):
            raise HarnessError("rehearsal outcome summary mismatch")
        _verify_write_receipt(evidence_root, outcome, admission)
        _verify_capture_receipt(evidence_root, outcome, admission)
    return {
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
        "checks": {
            "artifact_inventory": "PASS",
            "baseline_failure_receipt": "PASS",
            "candidate_exact_bytes": "PASS",
            "chain": "PASS",
            "live_capture_receipts": "PASS",
            "outcomes": "PASS",
            "structured_write_receipts": "PASS",
        },
        "event_count": chain_result["event_count"],
        "head_sha256": chain_result["head_sha256"],
        "outcome_count": len(outcomes),
        "status": "PASS",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--repo-root", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--nonce-hex")
    verify = sub.add_parser("verify")
    verify.add_argument("--repo-root", required=True)
    verify.add_argument("--rehearsal-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build_rehearsal(
                Path(args.repo_root),
                Path(args.out),
                nonce_hex=args.nonce_hex,
            )
        else:
            result = verify_rehearsal(
                Path(args.repo_root),
                Path(args.rehearsal_root),
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HarnessError, chain.EvidenceError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
