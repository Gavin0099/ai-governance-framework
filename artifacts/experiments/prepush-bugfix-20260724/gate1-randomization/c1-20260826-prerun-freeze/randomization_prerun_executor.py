"""Frozen C1 create-once randomization executor.

The module performs no work on import. Its CLI requires explicit owner authority
bound to the executing Git commit. It never launches a producer, scorer, arm,
hosted-model request, mapping release, or Rekor POST.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


MANIFEST_SCHEMA = "c1-gate1-randomization-prerun-freeze.v4"
BATCH_SCHEMA = "c1-gate1-batch-admission.v1"
TERMINAL_SCHEMA = "c1-gate1-randomization-terminal.v4"
SOURCE_MAIN_COMMIT = "6f6e6ba2adb8a3ab58e5b69d466bf2b2e1570bcf"
D5_ADMISSION_COMMIT = "1ced27d08e0330ca5ebe21ed241f0074ec500958"
SUPERSEDED_FREEZE_COMMIT = "50ed5709e32bedb3c6b3ebe63a82f5e121296cd9"
PAIR_ID = "C1-skill-primary-pair-02"
FREEZE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = FREEZE_DIR / "randomization-prerun-manifest.json"
TREATMENT_PATH = FREEZE_DIR / "treatment-input-bindings.json"

STATUS_AUTHORITY = "RANDOMIZATION_AUTHORITY_MISMATCH"
STATUS_BINDING = "RANDOMIZATION_BINDING_MISMATCH"
STATUS_INFRASTRUCTURE = "RANDOMIZATION_INFRASTRUCTURE_PRECONDITION_FAILED"
STATUS_IDENTITY = "RANDOMIZATION_CLIENT_IDENTITY_MISMATCH"
STATUS_WINDOW = "RANDOMIZATION_WINDOW_PRECONDITION_FAILED"
STATUS_TREATMENT = "RANDOMIZATION_TREATMENT_BINDING_INCOMPLETE"
STATUS_OUTPUT_ROOT = "RANDOMIZATION_OUTPUT_ROOT_MISMATCH"
STATUS_PRIOR_PAIR = "RANDOMIZATION_PRIOR_PAIR_EXISTS"
STATUS_EXISTS = "RANDOMIZATION_OUTPUT_ALREADY_EXISTS"
STATUS_AMBIGUOUS = "RANDOMIZATION_COMMIT_STATE_AMBIGUOUS"
STATUS_COMMITTED = "RANDOMIZATION_COMMITTED"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_RETAINED_KEYS = {
    "mapping",
    "nonce",
    "nonce_hex",
    "rng_bytes",
    "private_path",
    "raw_environment_output",
    "provider_response_model",
    "server_model_id",
}
SENSITIVE_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"/(?:home|Users)/", re.IGNORECASE),
    re.compile("App" + "Data", re.IGNORECASE),
)


class RandomizationError(RuntimeError):
    """A precondition or create-once publication rule was violated."""


class AuthorityError(RandomizationError):
    pass


class BindingError(RandomizationError):
    pass


class InfrastructureError(RandomizationError):
    pass


class IdentityError(RandomizationError):
    pass


class WindowError(RandomizationError):
    pass


class TreatmentError(RandomizationError):
    pass


class OutputRootError(RandomizationError):
    pass


class PriorPairError(RandomizationError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utc_text(value: datetime) -> str:
    if value.tzinfo != timezone.utc:
        raise WindowError("timestamp is not UTC")
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BindingError(f"JSON is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise BindingError(f"JSON root is not an object: {path.name}")
    return value


def _module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BindingError(f"cannot load frozen module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _git(repo_root: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise BindingError(f"Git command failed: {' '.join(args[:2])}")
    if binary:
        return result.stdout
    try:
        return result.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise BindingError("Git output is not UTF-8") from exc


def _git_blob(repo_root: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo_root, "rev-parse", f"{commit}:{path}"))
    raw = _git(repo_root, "cat-file", "blob", oid, binary=True)
    assert isinstance(raw, bytes)
    return oid, raw


def _bounded_diagnostic(exc: BaseException) -> str:
    value = f"{type(exc).__name__}: {exc}"
    return value[:240]


def _walk_forbidden(node: object) -> None:
    if isinstance(node, Mapping):
        overlap = FORBIDDEN_RETAINED_KEYS.intersection(str(key) for key in node)
        if overlap:
            raise BindingError(
                "retained public JSON contains forbidden keys: "
                + ",".join(sorted(overlap))
            )
        for value in node.values():
            _walk_forbidden(value)
    elif isinstance(node, list):
        for value in node:
            _walk_forbidden(value)


def _validate_public_json(raw: bytes, *, guard: Any, repo_root: Path) -> None:
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BindingError("retained public JSON is invalid") from exc
    _walk_forbidden(value)
    if any(pattern.search(text) is not None for pattern in SENSITIVE_PATTERNS):
        raise BindingError("retained public JSON contains a leakage marker")
    result = guard.assess_bytes(
        raw, expected_repository_identities=(str(repo_root.resolve()),)
    )
    if result.status != guard.STATUS_PASS:
        raise BindingError(f"inventory guard returned {result.status}")


def _write_create_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise BindingError(f"create-once target exists: {path.name}") from exc


def _validate_frozen_files(manifest: Mapping[str, Any]) -> None:
    frozen = manifest.get("frozen_files")
    if not isinstance(frozen, list) or not frozen:
        raise BindingError("frozen file manifest is empty")
    seen: set[str] = set()
    for entry in frozen:
        if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256"}:
            raise BindingError("frozen file entry shape is invalid")
        relative = entry["path"]
        if not isinstance(relative, str) or relative in seen or "/" in relative:
            raise BindingError("frozen file path is invalid")
        seen.add(relative)
        path = FREEZE_DIR / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry["bytes"]
            or sha256_file(path) != entry["sha256"]
        ):
            raise BindingError(f"frozen file differs: {relative}")
    if "randomization_prerun_executor.py" not in seen:
        raise BindingError("executor is not frozen")
    expected = {
        path.name
        for path in FREEZE_DIR.iterdir()
        if path.is_file() and path.name != MANIFEST_PATH.name
    }
    if seen != expected:
        raise BindingError("frozen file set does not cover the directory")


def _validate_source_bindings(repo_root: Path, manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise BindingError("manifest schema mismatch")
    framework = manifest.get("framework_base")
    if not isinstance(framework, dict) or framework != {
        "d5_admission_commit": D5_ADMISSION_COMMIT,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "superseded_freeze_commit": SUPERSEDED_FREEZE_COMMIT,
    }:
        raise BindingError("framework commit bindings differ")
    if str(_git(repo_root, "rev-parse", f"{D5_ADMISSION_COMMIT}^")) == "":
        raise BindingError("D5 commit is not readable")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", D5_ADMISSION_COMMIT, SOURCE_MAIN_COMMIT],
        cwd=repo_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ancestor.returncode != 0:
        raise BindingError("D5 commit is not an ancestor of source main")
    if manifest.get("consumed_pair") != {
        "event_count": 0,
        "pair_id": "C1-skill-primary-pair-01",
        "randomization_created": False,
        "terminal_bytes": 416,
        "terminal_sha256": (
            "bb2d2b87e2d77732811b7aa5af89a18e8451aaf96510d0ac17c0b9a1b3f646aa"
        ),
        "terminal_status": "RANDOMIZATION_BINDING_MISMATCH",
        "treatment": "CONSUMED_INFRASTRUCTURE_INVALID_NO_RETRY",
    }:
        raise BindingError("consumed pair disposition differs")
    bindings = manifest.get("source_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise BindingError("source bindings are absent")
    for binding in bindings:
        if not isinstance(binding, dict):
            raise BindingError("source binding is invalid")
        path = binding.get("path")
        if not isinstance(path, str):
            raise BindingError("source binding path is invalid")
        oid, raw = _git_blob(repo_root, SOURCE_MAIN_COMMIT, path)
        if (
            oid != binding.get("git_blob_oid")
            or len(raw) != binding.get("bytes")
            or sha256_bytes(raw) != binding.get("sha256")
        ):
            raise BindingError(f"source binding differs: {path}")


def validate_authority(
    repo_root: Path, manifest: Mapping[str, Any], owner_authorized_commit: str
) -> str:
    head = str(_git(repo_root, "rev-parse", "HEAD"))
    if owner_authorized_commit != head:
        raise AuthorityError("owner authority does not match executing HEAD")
    if manifest.get("execution_authority") != {
        "authorized": False,
        "required": "explicit_owner_authorization_bound_to_reviewed_freeze_commit",
    }:
        raise AuthorityError("committed execution authority must remain closed")
    parent = str(_git(repo_root, "rev-parse", "HEAD^"))
    if parent != SUPERSEDED_FREEZE_COMMIT:
        raise BindingError("correction freeze parent is not the superseded freeze")
    ancestor = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            SOURCE_MAIN_COMMIT,
            head,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ancestor.returncode != 0:
        raise BindingError("reviewed source main is not an ancestor of the correction freeze")
    return head


def _frozen_publication_roots(
    repo_root: Path, manifest: Mapping[str, Any]
) -> tuple[Path, Path]:
    publication = manifest.get("publication")
    required = {
        "atomic_directory_rename",
        "create_once",
        "evidence_root_repo_relative",
        "final_attempt_root_repo_relative",
        "human_readability",
        "infrastructure_failure_consumes_pair",
        "private_mapping_reveal_path",
        "public_event_path",
        "public_randomization_record_path",
        "terminal_path",
    }
    if not isinstance(publication, dict) or set(publication) != required:
        raise OutputRootError("frozen publication contract is invalid")
    if (
        publication.get("human_readability") != "parent_acl_inheritance_required"
        or publication.get("infrastructure_failure_consumes_pair") is not True
    ):
        raise OutputRootError("frozen publication safety contract differs")
    evidence_text = publication.get("evidence_root_repo_relative")
    final_text = publication.get("final_attempt_root_repo_relative")
    if not isinstance(evidence_text, str) or not isinstance(final_text, str):
        raise OutputRootError("frozen publication roots are invalid")
    if "\\" in evidence_text or "\\" in final_text:
        raise OutputRootError("frozen publication roots must use repository separators")
    evidence_relative = Path(evidence_text)
    final_relative = Path(final_text)
    if (
        evidence_relative.is_absolute()
        or final_relative.is_absolute()
        or ".." in evidence_relative.parts
        or ".." in final_relative.parts
    ):
        raise OutputRootError("frozen publication roots must be repository relative")
    evidence_root = (repo_root / evidence_relative).resolve()
    final_root = (repo_root / final_relative).resolve()
    if final_root.parent != evidence_root:
        raise OutputRootError("final attempt root is not directly under the evidence root")
    return evidence_root, final_root


def _validate_no_prior_pair_state(evidence_root: Path) -> None:
    if not evidence_root.exists():
        return
    if not evidence_root.is_dir():
        raise PriorPairError("frozen evidence root exists but is not a directory")
    blocking_names = {
        "0001-randomization-committed.json",
        "randomization-record.json",
        "terminal.json",
    }
    if any(
        path.is_file() and path.name in blocking_names
        for path in evidence_root.rglob("*")
    ):
        raise PriorPairError(f"frozen evidence root already contains {PAIR_ID} state")


def validate_treatment_bindings(repo_root: Path) -> dict[str, dict[str, str]]:
    document = load_json(TREATMENT_PATH)
    if document.get("schema") != "c1-gate1-randomization-treatment-input-bindings.v1":
        raise TreatmentError("treatment binding schema mismatch")
    expected_comparison = {
        "pair_id": PAIR_ID,
        "repeat_index": 1,
        "study_kind": "skill_primary",
        "task_id": "C1",
    }
    if document.get("comparison") != expected_comparison:
        raise TreatmentError("comparison identity differs")
    sources = document.get("source_artifacts")
    if not isinstance(sources, dict):
        raise TreatmentError("treatment source artifacts are absent")
    for name, entry in sources.items():
        if not isinstance(entry, dict):
            raise TreatmentError(f"treatment source is invalid: {name}")
        path = entry.get("path")
        if not isinstance(path, str):
            raise TreatmentError(f"treatment path is invalid: {name}")
        if "git_blob_oid" in entry:
            oid, raw = _git_blob(repo_root, SOURCE_MAIN_COMMIT, path)
            if oid != entry["git_blob_oid"]:
                raise TreatmentError(f"treatment Git blob differs: {name}")
        else:
            local = FREEZE_DIR / path
            if not local.is_file():
                raise TreatmentError(f"treatment local artifact is absent: {name}")
            raw = local.read_bytes()
        if len(raw) != entry.get("bytes") or sha256_bytes(raw) != entry.get("sha256"):
            raise TreatmentError(f"treatment artifact differs: {name}")
    inputs = document.get("treatment_inputs")
    fields = {
        "treatment_packet_sha256",
        "governance_instruction_sha256",
        "validator_bundle_sha256",
        "validator_config_sha256",
    }
    if not isinstance(inputs, dict) or set(inputs) != {"A", "B"}:
        raise TreatmentError("A/B treatment population is invalid")
    for arm, value in inputs.items():
        if not isinstance(value, dict) or set(value) != fields:
            raise TreatmentError(f"{arm} treatment fields are invalid")
        if any(not isinstance(item, str) or HEX64.fullmatch(item) is None for item in value.values()):
            raise TreatmentError(f"{arm} treatment digest is not SHA-256")
    if inputs["A"]["governance_instruction_sha256"] != inputs["B"]["governance_instruction_sha256"]:
        raise TreatmentError("A/B governance bindings differ")
    if inputs["A"]["validator_bundle_sha256"] != inputs["B"]["validator_bundle_sha256"]:
        raise TreatmentError("A/B validator bundles differ")
    if inputs["A"]["validator_config_sha256"] != inputs["B"]["validator_config_sha256"]:
        raise TreatmentError("A/B validator configs differ")
    return {arm: dict(value) for arm, value in inputs.items()}


def validate_executable_launch(
    repo_root: Path, staged_executable: Path
) -> dict[str, object]:
    distribution = _module(FREEZE_DIR / "codex_distribution.py", "c1_codex_distribution")
    try:
        return distribution.validate_staged_executable(
            staged_executable, cwd=repo_root
        )
    except Exception as exc:
        raise InfrastructureError("exact staged Codex executable is unavailable") from exc


def measure_client_identity(
    repo_root: Path, launch: Mapping[str, object] | None = None
) -> dict[str, object]:
    identity_path = repo_root / (
        "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
        "c1-client-identity-amendment-20260826/client_identity_receipt.py"
    )
    adapter_path = repo_root / (
        "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
        "c1-client-identity-amendment-20260826/external_preflight_adapter.py"
    )
    identity = _module(identity_path, "c1_client_identity_runtime")
    adapter = _module(adapter_path, "c1_amendment_preflight_runtime")
    if launch is None:
        raise InfrastructureError("staged Codex launch observation is absent")
    executable = launch.get("executable")
    version_stdout = launch.get("version_stdout")
    if not isinstance(executable, Path) or not isinstance(version_stdout, bytes):
        raise InfrastructureError("Codex launch observation shape is invalid")
    scratch_root = Path(tempfile.gettempdir()) / "c1-pair02-f29-preflight"
    if scratch_root.exists():
        raise InfrastructureError("preflight scratch already exists")
    try:
        preflight, snapshot = adapter.measure_amended_preflight(
            run_id="c1-pair02-f29-preflight",
            executable=executable,
            preflight_root=scratch_root,
        )
        runner_identity = adapter.prove_runner_accepts_preflight(
            measured_preflight=preflight,
            executable_snapshot=snapshot,
            private_root=scratch_root / "runner-private",
        )
        projection = adapter.command_contract_projection()
        fields: dict[str, object] = {
            "schema": "c1-client-side-runtime-facts.v1",
            "model_requested_id": identity.EXPECTED_MODEL,
            "model_request_source": identity.EXPECTED_MODEL_SOURCE,
            "model_request_argument_sha256": identity.model_request_argument_sha256(),
            "identity_evidence_level": identity.EVIDENCE_LEVEL,
            "server_executed_model_observed": False,
            "provider_attestation_available": False,
            "cli_version": version_stdout.decode("utf-8", errors="strict").strip(),
            "cli_version_stdout_bytes": len(version_stdout),
            "cli_version_stdout_sha256": sha256_bytes(version_stdout),
            "cli_executable_bytes": executable.stat().st_size,
            "cli_executable_sha256": sha256_file(executable),
            "runner_git_blob_oid": identity.EXPECTED_RUNNER_OID,
            "runner_bytes": identity.EXPECTED_RUNNER_BYTES,
            "runner_sha256": identity.EXPECTED_RUNNER_SHA256,
            "preflight_adapter_sha256": sha256_file(adapter_path),
            "python_executable_sha256": sha256_file(Path(sys.executable).resolve()),
            "command_contract_sha256": projection["command_contract_sha256"],
        }
        invariant = identity.invariant_projection(fields)
        if runner_identity != {
            "cli_version": fields["cli_version"],
            "command_contract_sha256": fields["command_contract_sha256"],
            "executable_sha256": fields["cli_executable_sha256"],
            "kind": "codex_exec",
            "runner_sha256": fields["runner_sha256"],
        }:
            raise IdentityError("frozen runner rejected the exact preflight")
        digest = identity.client_runtime_projection_sha256(fields)
        manifest = load_json(MANIFEST_PATH)
        if manifest.get("client_runtime_projection_sha256") != digest:
            raise IdentityError("client runtime projection digest differs")
        return {
            **fields,
            "client_runtime_projection_sha256": digest,
            "invariant_projection": invariant,
            "preflight_bytes": len(preflight),
            "preflight_sha256": sha256_bytes(preflight),
        }
    finally:
        if scratch_root.exists():
            shutil.rmtree(scratch_root)


def validate_full_admission(
    repo_root: Path, runtime: Mapping[str, object], randomization_path: Path
) -> dict[str, object]:
    admission_dir = repo_root / (
        "artifacts/experiments/prepush-bugfix-20260724/"
        "gate1-arm-execution-admission/c1-20260825"
    )
    module = _module(
        admission_dir / "arm_execution_admission.py",
        "c1_arm_execution_admission_runtime",
    )
    manifest = load_json(admission_dir / "arm-execution-admission-manifest.json")
    result = module.evaluate_admission(
        repo_root=repo_root,
        manifest=manifest,
        runtime_facts={
            key: value
            for key, value in runtime.items()
            if key not in {
                "client_runtime_projection_sha256",
                "invariant_projection",
                "preflight_bytes",
                "preflight_sha256",
            }
        },
        randomization_path=randomization_path,
    )
    if (
        result.get("status") != module.PASSED
        or result.get("reasons") != []
        or result.get("randomization_created") is not False
    ):
        raise IdentityError("full arm execution admission did not pass")
    return result


def build_batch_admission(
    *, runtime: Mapping[str, object], freeze_commit: str, now: datetime
) -> dict[str, object]:
    if now.tzinfo != timezone.utc:
        raise WindowError("batch admission timestamp is not UTC")
    expiry = now + timedelta(hours=12)
    if expiry <= now:
        raise WindowError("batch admission window is invalid")
    return {
        "admission_at_utc": utc_text(now),
        "client_runtime_projection_sha256": runtime[
            "client_runtime_projection_sha256"
        ],
        "d5_admission_commit": D5_ADMISSION_COMMIT,
        "d5_terminal_sha256": (
            "511f13706053c1fdea4032ef23d2ae1be929556b88ea0d12e2ac90707dd3f7f6"
        ),
        "freeze_commit": freeze_commit,
        "historical_admission_terminal_sha256": (
            "692aadbdf5e1daf1dc9c7a7e3ef7339c6339ad0d307b2be0dcaadd4960140ed1"
        ),
        "identity_evidence_level": "CLIENT_SIDE_INVOCATION_ONLY",
        "model_requested_id": "gpt-5.6-sol",
        "provider_attestation_available": False,
        "schema": BATCH_SCHEMA,
        "server_executed_model_observed": False,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "window_expires_at_utc": utc_text(expiry),
    }


def build_randomization_documents(
    *,
    chain: Any,
    treatment_inputs: Mapping[str, Mapping[str, str]],
    rng: Callable[[int], bytes],
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = rng(6)
    second = rng(6)
    nonce = rng(32)
    selector = rng(1)
    if (
        len(first) != 6
        or len(second) != 6
        or len(nonce) != 32
        or len(selector) != 1
    ):
        raise BindingError("OS RNG returned an unexpected byte count")
    anonymous_ids = sorted((f"OUT-{first.hex()}", f"OUT-{second.hex()}"))
    if len(set(anonymous_ids)) != 2:
        raise BindingError("OS RNG produced duplicate anonymous IDs")
    treatments = ("A", "B") if selector[0] & 1 == 0 else ("B", "A")
    mapping = dict(zip(anonymous_ids, treatments, strict=True))
    nonce_hex = nonce.hex()
    commitment = chain._mapping_commitment(mapping, "skill_primary", nonce_hex)
    record = {
        "anonymous_ids": anonymous_ids,
        "mapping_commitment_sha256": commitment,
        "pair_id": PAIR_ID,
        "repeat_index": 1,
        "schema": chain.RANDOMIZATION_SCHEMA,
        "study_kind": "skill_primary",
        "task_id": "C1",
        "treatment_inputs": {
            arm: dict(value) for arm, value in treatment_inputs.items()
        },
    }
    chain.validate_randomization_record(record, chain.load_contract(
        _contract_path(chain.FRAMEWORK_ROOT)
    )[0])
    record_sha = sha256_bytes(chain._json_bytes(record))
    reveal = {
        "mapping": mapping,
        "nonce_hex": nonce_hex,
        "randomization_record_sha256": record_sha,
        "schema": chain.MAPPING_SCHEMA,
        "study_kind": "skill_primary",
    }
    chain.validate_mapping_reveal(
        reveal,
        chain.load_contract(_contract_path(chain.FRAMEWORK_ROOT))[0],
        record,
        record_sha,
    )
    return record, reveal


def _contract_path(repo_root: Path) -> Path:
    return repo_root / (
        "artifacts/experiments/prepush-bugfix-20260724/candidate/"
        "gate3-protocol-contract-external-pin-v2.json"
    )


def _load_runtime_modules(repo_root: Path) -> tuple[Any, Any]:
    chain = _module(
        repo_root
        / "artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/"
        "gate3_evidence_chain.py",
        "c1_gate3_evidence_chain_runtime",
    )
    guard = _module(
        repo_root / "governance_tools/external_tree_inventory_guard.py",
        "c1_external_inventory_guard_runtime",
    )
    return chain, guard


def _terminal(
    *,
    status: str,
    freeze_commit: str | None,
    diagnostic: str,
    randomization_created: bool,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "chain_state": "randomization_committed" if randomization_created else "empty",
        "diagnostic": diagnostic,
        "event_count": 1 if randomization_created else 0,
        "freeze_commit": freeze_commit,
        "pair_id": PAIR_ID,
        "randomization_created": randomization_created,
        "schema": TERMINAL_SCHEMA,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "status": status,
    }
    if extra:
        value.update(extra)
    return value


def _create_publication_staging(final_root: Path) -> Path:
    final_root.parent.mkdir(parents=True, exist_ok=True)
    staging = final_root.parent / f".{final_root.name}.publication-staging"
    try:
        staging.mkdir()
    except FileExistsError as exc:
        raise InfrastructureError("publication staging path already exists") from exc
    return staging


def _publish_terminal_only(final_root: Path, terminal: Mapping[str, object]) -> None:
    staging = _create_publication_staging(final_root)
    try:
        _write_create_once(staging / "terminal.json", canonical_json_bytes(terminal))
        os.rename(staging, final_root)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _existing_terminal(final_root: Path) -> dict[str, Any] | None:
    terminal_path = final_root / "terminal.json"
    if not terminal_path.is_file():
        return None
    value = load_json(terminal_path)
    if value.get("schema") != TERMINAL_SCHEMA:
        return None
    return value


def execute_randomization(
    *,
    repo_root: Path,
    final_root: Path,
    owner_authorized_commit: str,
    staged_executable: Path | None = None,
    launch_probe: Callable[[Path], dict[str, object]] | None = None,
    runtime_probe: Callable[[Path, Mapping[str, object]], dict[str, object]] | None = None,
    admission_probe: Callable[
        [Path, Mapping[str, object], Path], dict[str, object]
    ] | None = None,
    rng: Callable[[int], bytes] = secrets.token_bytes,
    now: Callable[[], datetime] = utc_now,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    supplied_final_root = final_root.resolve()
    if launch_probe is None:
        if staged_executable is None:
            launch_probe = lambda root: validate_executable_launch(root)  # type: ignore[call-arg]
        else:
            launch_probe = lambda root: validate_executable_launch(
                root, staged_executable
            )
    runtime_probe = runtime_probe or measure_client_identity
    admission_probe = admission_probe or validate_full_admission

    freeze_commit: str | None = None
    manifest: dict[str, Any] | None = None
    failure: BaseException | None = None
    final_root_validated = False
    try:
        manifest = load_json(MANIFEST_PATH)
        _validate_frozen_files(manifest)
        _validate_source_bindings(repo_root, manifest)
        evidence_root, final_root = _frozen_publication_roots(repo_root, manifest)
        if supplied_final_root != final_root:
            raise OutputRootError("supplied output root differs from the frozen root")
        final_root_validated = True
        freeze_commit = validate_authority(
            repo_root, manifest, owner_authorized_commit
        )
        if final_root.exists():
            existing = _existing_terminal(final_root)
            if existing is not None:
                return _terminal(
                    status=STATUS_EXISTS,
                    freeze_commit=freeze_commit,
                    diagnostic="a create-once attempt terminal already exists",
                    randomization_created=bool(existing.get("randomization_created")),
                    extra={
                        "existing_terminal_sha256": sha256_file(
                            final_root / "terminal.json"
                        )
                    },
                )
            return _terminal(
                status=STATUS_AMBIGUOUS,
                freeze_commit=freeze_commit,
                diagnostic="attempt path exists without a valid unique terminal",
                randomization_created=False,
            )
        _validate_no_prior_pair_state(evidence_root)
        treatment_inputs = validate_treatment_bindings(repo_root)
        launch = launch_probe(repo_root)
        runtime = runtime_probe(repo_root, launch)
        admission_probe(
            repo_root,
            runtime,
            final_root / "evidence" / "randomization-record.json",
        )
        admission_time = now()
        batch = build_batch_admission(
            runtime=runtime, freeze_commit=freeze_commit, now=admission_time
        )
        chain, guard = _load_runtime_modules(repo_root)
        record, reveal = build_randomization_documents(
            chain=chain, treatment_inputs=treatment_inputs, rng=rng
        )
        staging = _create_publication_staging(final_root)
        try:
            evidence = staging / "evidence"
            chain_dir = evidence / "chain"
            record_path = evidence / "randomization-record.json"
            reveal_path = staging / "control" / "mapping-reveal.json"
            batch_path = staging / "batch-admission.json"
            _write_create_once(batch_path, canonical_json_bytes(batch))
            _write_create_once(record_path, chain._json_bytes(record))
            _write_create_once(reveal_path, chain._json_bytes(reveal))
            event_path = chain.commit_randomization(
                chain_dir, _contract_path(repo_root), record_path
            )
            report = chain.verify_chain(chain_dir, _contract_path(repo_root))
            if (
                report.get("event_count") != 1
                or report.get("state") != "randomization_committed"
            ):
                raise BindingError("event-1 chain verification failed")
            terminal = _terminal(
                status=STATUS_COMMITTED,
                freeze_commit=freeze_commit,
                diagnostic="event 1 committed; no producer, scorer, arm, mapping release, or POST executed",
                randomization_created=True,
                extra={
                    "admission_at_utc": batch["admission_at_utc"],
                    "batch_admission_sha256": sha256_file(batch_path),
                    "client_runtime_projection_sha256": batch[
                        "client_runtime_projection_sha256"
                    ],
                    "event_sha256": sha256_file(event_path),
                    "mapping_reveal_sha256": sha256_file(reveal_path),
                    "randomization_record_sha256": sha256_file(record_path),
                    "window_expires_at_utc": batch["window_expires_at_utc"],
                },
            )
            public_documents = (
                batch_path,
                record_path,
                event_path,
            )
            for path in public_documents:
                _validate_public_json(path.read_bytes(), guard=guard, repo_root=repo_root)
            _validate_public_json(
                canonical_json_bytes(terminal), guard=guard, repo_root=repo_root
            )
            _write_create_once(
                staging / "terminal.json", canonical_json_bytes(terminal)
            )
            if len(list(chain_dir.glob("*.json"))) != 1:
                raise BindingError("chain contains more than event 1")
            os.rename(staging, final_root)
            return terminal
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging)
            raise
    except AuthorityError as exc:
        status = STATUS_AUTHORITY
        failure = exc
    except InfrastructureError as exc:
        status = STATUS_INFRASTRUCTURE
        failure = exc
    except IdentityError as exc:
        status = STATUS_IDENTITY
        failure = exc
    except WindowError as exc:
        status = STATUS_WINDOW
        failure = exc
    except TreatmentError as exc:
        status = STATUS_TREATMENT
        failure = exc
    except OutputRootError as exc:
        status = STATUS_OUTPUT_ROOT
        failure = exc
    except PriorPairError as exc:
        status = STATUS_PRIOR_PAIR
        failure = exc
    except OSError as exc:
        status = STATUS_INFRASTRUCTURE
        failure = exc
    except BaseException as exc:
        status = STATUS_BINDING
        failure = exc

    if failure is None:  # pragma: no cover - defensive invariant
        raise AssertionError("failed execution did not retain its exception")

    terminal = _terminal(
        status=status,
        freeze_commit=freeze_commit,
        diagnostic=_bounded_diagnostic(failure),
        randomization_created=False,
    )
    if final_root_validated and not final_root.exists():
        _publish_terminal_only(final_root, terminal)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute the frozen C1 event-1-only randomization."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--staged-executable", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    terminal = execute_randomization(
        repo_root=Path(args.repo_root),
        final_root=Path(args.output_root),
        staged_executable=Path(args.staged_executable),
        owner_authorized_commit=args.owner_authorized_freeze_commit,
    )
    print(json.dumps(terminal, ensure_ascii=False, sort_keys=True))
    return 0 if terminal["status"] == STATUS_COMMITTED else 1


if __name__ == "__main__":
    raise SystemExit(main())
