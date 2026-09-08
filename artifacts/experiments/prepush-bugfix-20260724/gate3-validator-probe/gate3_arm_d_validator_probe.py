#!/usr/bin/env python3
"""Bounded, task-neutral StrykerJS/Vitest compatibility probe.

The probe creates only a synthetic consumer beneath a caller-supplied external
workspace.  It never reads a real consumer checkout, historical correction,
scorer bundle, or experiment attempt.  Only aggregate output is retained in
the repository; raw validator output is deleted with the owned workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Mapping, Sequence


PASSED = "VALIDATOR_PROBE_PASSED"
FAILED = "VALIDATOR_PROBE_FAILED"
PIN_UNAVAILABLE = "ENVIRONMENT_OR_PACKAGE_PIN_UNAVAILABLE"
LEAKAGE_REVIEW_REQUIRED = "LEAKAGE_REVIEW_REQUIRED"

RESULT_SCHEMA = "gate3-arm-d-validator-probe-result/1"
OWNERSHIP_MARKER = ".gate3-arm-d-validator-probe-owned"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HUNK_RE = re.compile(
    r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@"
)

BASELINE_SOURCE = """export function classify(value: number): string {
  if (value > 0) return \"positive\";
  return \"negative\";
}
"""

PRODUCER_SOURCE = """export function classify(value: number): string {
  if (value === 0) return \"zero\";
  if (value > 0) return \"positive\";
  return \"negative\";
}
"""

BASELINE_TEST = """import { describe, expect, it } from \"vitest\";
import { classify } from \"../src/classify\";

describe(\"classify\", () => {
  it(\"keeps the positive path\", () => {
    expect(classify(2)).toBe(\"positive\");
  });
});
"""

PRODUCER_TEST = """import { describe, expect, it } from \"vitest\";
import { classify } from \"../src/classify\";

describe(\"classify\", () => {
  it(\"returns a string for zero\", () => {
    expect(typeof classify(0)).toBe(\"string\");
  });

  it(\"keeps the positive path\", () => {
    expect(classify(2)).toBe(\"positive\");
  });
});
"""


class ProbeFailure(RuntimeError):
    """A fail-closed terminal result with a bounded public reason."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    duration_ms: int
    timed_out: bool = False


@dataclass(frozen=True)
class ChangedRange:
    path: str
    start_line: int
    end_line: int

    def stryker_target(self) -> str:
        return f"{self.path}:{self.start_line}-{self.end_line}"


Runner = Callable[..., CommandResult]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeFailure(PIN_UNAVAILABLE, f"invalid JSON input: {path.name}") from exc


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ProbeFailure(PIN_UNAVAILABLE, f"{label} must be an object")
    return value


def _bounded_diagnostic(text: str, *, maximum: int) -> str:
    single_line = " ".join(text.replace("\x1b", "").split())
    if len(single_line) <= maximum:
        return single_line
    return single_line[: maximum - 3] + "..."


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Run one command, killing its process tree on timeout."""

    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        start_new_session = True

    started = time.monotonic()
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=None if env is None else dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/pid", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()

    return CommandResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout,
        stderr=stderr,
        duration_ms=round((time.monotonic() - started) * 1000),
        timed_out=timed_out,
    )


def classify_execution(
    result: CommandResult,
    *,
    report_exists: bool,
) -> str:
    """Classify validator execution without treating partial output as success."""

    if result.timed_out:
        return "TIMEOUT"
    if result.returncode != 0:
        return "ERROR"
    if not report_exists:
        return "PARTIAL"
    return "COMPLETE"


def _is_production_path(path: str, policy: Mapping[str, object]) -> bool:
    normalized = PurePosixPath(path)
    roots = tuple(str(item) for item in policy["production_roots"])
    suffixes = tuple(str(item) for item in policy["source_suffixes"])
    rejected = {str(item) for item in policy["rejected_path_segments"]}
    return (
        path.startswith(roots)
        and path.endswith(suffixes)
        and not any(part in rejected for part in normalized.parts)
    )


def parse_changed_production_ranges(
    diff_text: str,
    *,
    policy: Mapping[str, object],
) -> tuple[ChangedRange, ...]:
    """Parse zero-context Git diff hunks into production-only line ranges."""

    current_path: str | None = None
    ranges: list[ChangedRange] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        match = HUNK_RE.match(line)
        if match is None or current_path is None:
            continue
        count = int(match.group("count") or "1")
        if count == 0 or not _is_production_path(current_path, policy):
            continue
        start = int(match.group("start"))
        ranges.append(
            ChangedRange(
                path=current_path,
                start_line=start,
                end_line=start + count - 1,
            )
        )

    deduplicated = tuple(
        sorted(set(ranges), key=lambda item: (item.path, item.start_line, item.end_line))
    )
    if not deduplicated:
        raise ProbeFailure(FAILED, "producer diff yielded no production mutation range")
    return deduplicated


def derive_changed_production_ranges(
    repository: Path,
    *,
    baseline_commit: str,
    policy: Mapping[str, object],
    runner: Runner = run_command,
) -> tuple[ChangedRange, ...]:
    result = runner(
        [
            "git",
            "diff",
            "--unified=0",
            "--no-ext-diff",
            "--no-renames",
            f"{baseline_commit}..HEAD",
            "--",
            "*.ts",
        ],
        cwd=repository,
        timeout_seconds=30,
    )
    if result.timed_out or result.returncode != 0:
        raise ProbeFailure(FAILED, "producer diff enumeration failed")
    return parse_changed_production_ranges(
        result.stdout.decode("utf-8", errors="strict"),
        policy=policy,
    )


def build_stryker_config(
    template: Mapping[str, object],
    ranges: Iterable[ChangedRange],
) -> bytes:
    config = dict(template)
    targets = [item.stryker_target() for item in ranges]
    if not targets:
        raise ProbeFailure(FAILED, "empty Stryker mutation target set")
    config["mutate"] = targets
    return json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def summarize_mutation_report(report: Mapping[str, object]) -> dict[str, object]:
    files = _require_mapping(report.get("files"), label="mutation report files")
    statuses: Counter[str] = Counter()
    mutator_names: Counter[str] = Counter()
    for file_payload in files.values():
        file_mapping = _require_mapping(file_payload, label="mutation report file")
        mutants = file_mapping.get("mutants")
        if not isinstance(mutants, list):
            raise ProbeFailure(FAILED, "mutation report mutants must be a list")
        for mutant in mutants:
            mutant_mapping = _require_mapping(mutant, label="mutation report mutant")
            status = mutant_mapping.get("status")
            mutator_name = mutant_mapping.get("mutatorName")
            if not isinstance(status, str) or not isinstance(mutator_name, str):
                raise ProbeFailure(FAILED, "mutation report aggregate fields are invalid")
            statuses[status] += 1
            mutator_names[mutator_name] += 1
    return {
        "file_count": len(files),
        "mutant_count": sum(statuses.values()),
        "status_counts": dict(sorted(statuses.items())),
        "mutator_counts": dict(sorted(mutator_names.items())),
        "surviving_feedback_observed": statuses["Survived"] > 0,
    }


def _walk_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_output_policy(
    result: Mapping[str, object],
    policy: Mapping[str, object],
) -> None:
    allowed = {str(item) for item in policy["allowed_result_fields"]}
    forbidden = {str(item) for item in policy["forbidden_detail_fields"]}
    unexpected = set(result) - allowed
    if unexpected:
        raise ProbeFailure(
            LEAKAGE_REVIEW_REQUIRED,
            "result contains fields outside the aggregate output policy",
        )
    found_forbidden = forbidden.intersection(_walk_keys(result))
    if found_forbidden:
        raise ProbeFailure(
            LEAKAGE_REVIEW_REQUIRED,
            "result contains forbidden detail fields",
        )


def audit_forbidden_markers(
    payloads: Iterable[bytes],
    *,
    markers: Iterable[str],
) -> tuple[str, ...]:
    combined = b"\n".join(payloads).decode("utf-8", errors="replace").casefold()
    return tuple(sorted(marker for marker in markers if marker.casefold() in combined))


def merkle_root(named_digests: Mapping[str, str]) -> str:
    leaves = []
    for name, digest in sorted(named_digests.items()):
        if HEX_SHA256.fullmatch(digest) is None:
            raise ValueError(f"invalid digest for {name}")
        leaves.append(hashlib.sha256(f"leaf\0{name}\0{digest}".encode()).digest())
    if not leaves:
        return hashlib.sha256(b"empty").hexdigest()
    while len(leaves) > 1:
        if len(leaves) % 2:
            leaves.append(leaves[-1])
        leaves = [
            hashlib.sha256(b"node\0" + leaves[index] + leaves[index + 1]).digest()
            for index in range(0, len(leaves), 2)
        ]
    return leaves[0].hex()


def _git(repository: Path, *arguments: str) -> str:
    result = run_command(
        ["git", *arguments],
        cwd=repository,
        timeout_seconds=30,
    )
    if result.timed_out or result.returncode != 0:
        raise ProbeFailure(FAILED, "synthetic Git operation failed")
    return result.stdout.decode("utf-8").strip()


def materialize_synthetic_repository(
    workspace: Path,
    *,
    package_root: Path,
) -> str:
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / OWNERSHIP_MARKER).write_text("owned\n", encoding="utf-8")
    shutil.copy2(package_root / "package.json", workspace / "package.json")
    shutil.copy2(package_root / "package-lock.json", workspace / "package-lock.json")
    (workspace / "src").mkdir()
    (workspace / "test").mkdir()
    (workspace / "src" / "classify.ts").write_text(BASELINE_SOURCE, encoding="utf-8")
    (workspace / "test" / "classify.test.ts").write_text(
        BASELINE_TEST,
        encoding="utf-8",
    )
    _git(workspace, "init", "-q")
    _git(workspace, "config", "user.name", "Gate3 Synthetic Probe")
    _git(workspace, "config", "user.email", "synthetic-probe@example.invalid")
    _git(workspace, "add", "--", "package.json", "package-lock.json", "src", "test")
    _git(workspace, "commit", "-q", "-m", "synthetic baseline")
    baseline = _git(workspace, "rev-parse", "HEAD")

    (workspace / "src" / "classify.ts").write_text(PRODUCER_SOURCE, encoding="utf-8")
    (workspace / "test" / "classify.test.ts").write_text(
        PRODUCER_TEST,
        encoding="utf-8",
    )
    _git(workspace, "add", "--", "src", "test")
    _git(workspace, "commit", "-q", "-m", "synthetic producer change")
    return baseline


def _verify_package_lock(
    package_lock: Mapping[str, object],
    contract_packages: Mapping[str, object],
) -> None:
    lock_packages = _require_mapping(package_lock.get("packages"), label="lock packages")
    for name, expected_payload in contract_packages.items():
        expected = _require_mapping(expected_payload, label=f"package pin {name}")
        installed = _require_mapping(
            lock_packages.get(f"node_modules/{name}"),
            label=f"locked package {name}",
        )
        for lock_key, contract_key in (
            ("version", "version"),
            ("resolved", "tarball"),
            ("integrity", "integrity"),
        ):
            if installed.get(lock_key) != expected.get(contract_key):
                raise ProbeFailure(PIN_UNAVAILABLE, f"package pin mismatch: {name}")


def _npm_command(node: Path, *arguments: str) -> list[str]:
    npm_cli = node.parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
    if not npm_cli.is_file():
        raise ProbeFailure(PIN_UNAVAILABLE, "portable npm CLI is unavailable")
    return [str(node), str(npm_cli), *arguments]


def _stryker_command(workspace: Path, node: Path, *arguments: str) -> list[str]:
    cli = workspace / "node_modules" / "@stryker-mutator" / "core" / "bin" / "stryker.js"
    if not cli.is_file():
        raise ProbeFailure(PIN_UNAVAILABLE, "pinned Stryker CLI is unavailable")
    return [str(node), str(cli), "run", "stryker.config.json", *arguments]


def _write_result(path: Path, payload: Mapping[str, object]) -> None:
    path.write_bytes(_canonical_json_bytes(payload))


def remove_owned_workspace(workspace: Path) -> None:
    """Remove only a workspace carrying this probe's ownership marker."""

    marker = workspace / OWNERSHIP_MARKER
    if not workspace.exists():
        return
    if not marker.is_file():
        raise ProbeFailure(FAILED, "refusing to remove an unowned workspace")

    def make_writable_and_retry(
        function: Callable[[str], object],
        path: str,
        _error: BaseException,
    ) -> None:
        os.chmod(path, stat.S_IWRITE)
        function(path)

    try:
        shutil.rmtree(workspace, onexc=make_writable_and_retry)
    except OSError as exc:
        raise ProbeFailure(FAILED, "synthetic workspace cleanup failed") from exc
    if workspace.exists():
        raise ProbeFailure(FAILED, "synthetic workspace cleanup was incomplete")


def execute_probe(
    *,
    probe_root: Path,
    node_root: Path,
    node_archive: Path,
    npm_cache: Path,
    workspace: Path,
    result_path: Path,
) -> dict[str, object]:
    contract_path = probe_root / "probe-contract.json"
    output_policy_path = probe_root / "output-policy.json"
    template_path = probe_root / "stryker.config.template.json"
    package_root = probe_root / "synthetic-consumer"
    package_lock_path = package_root / "package-lock.json"
    adapter_path = Path(__file__).resolve()

    contract = _require_mapping(_read_json(contract_path), label="probe contract")
    output_policy = _require_mapping(
        _read_json(output_policy_path),
        label="output policy",
    )
    template = _require_mapping(_read_json(template_path), label="Stryker template")
    package_lock = _require_mapping(_read_json(package_lock_path), label="package lock")
    runtime = _require_mapping(contract.get("runtime"), label="runtime pin")
    packages = _require_mapping(contract.get("packages"), label="package pins")
    scope_policy = _require_mapping(contract.get("scope_policy"), label="scope policy")
    leakage_policy = _require_mapping(
        contract.get("leakage_policy"),
        label="leakage policy",
    )
    maximum_diagnostic = int(leakage_policy["maximum_diagnostic_characters"])
    markers = tuple(str(item) for item in leakage_policy["forbidden_markers"])

    node = node_root / "node.exe"
    if not node.is_file() or not node_archive.is_file():
        raise ProbeFailure(PIN_UNAVAILABLE, "portable Node runtime is unavailable")
    if _sha256_bytes(node_archive.read_bytes()) != runtime["archive_sha256"]:
        raise ProbeFailure(PIN_UNAVAILABLE, "portable Node archive checksum mismatch")
    version = run_command([str(node), "--version"], cwd=probe_root, timeout_seconds=10)
    if version.returncode != 0 or version.stdout.decode().strip() != runtime["node_version"]:
        raise ProbeFailure(PIN_UNAVAILABLE, "portable Node version mismatch")
    _verify_package_lock(package_lock, packages)

    if workspace.exists():
        raise ProbeFailure(FAILED, "external workspace must not already exist")
    if probe_root.resolve() in workspace.resolve().parents or workspace.resolve() == probe_root.resolve():
        raise ProbeFailure(FAILED, "synthetic workspace must be outside the repository")

    raw_outputs: list[bytes] = []
    generated_config = b""
    raw_report = b""
    dry_run_duration = 0
    mutation_duration = 0
    ranges: tuple[ChangedRange, ...] = ()
    mutation_summary: dict[str, object] = {}
    completed_result: dict[str, object] | None = None
    try:
        baseline = materialize_synthetic_repository(workspace, package_root=package_root)
        ranges = derive_changed_production_ranges(
            workspace,
            baseline_commit=baseline,
            policy=scope_policy,
        )
        if any(not _is_production_path(item.path, scope_policy) for item in ranges):
            raise ProbeFailure(FAILED, "non-production mutation target derived")
        generated_config = build_stryker_config(template, ranges)
        (workspace / "stryker.config.json").write_bytes(generated_config)

        install = run_command(
            _npm_command(
                node,
                "ci",
                "--no-audit",
                "--no-fund",
                "--cache",
                str(npm_cache),
            ),
            cwd=workspace,
            timeout_seconds=180,
        )
        raw_outputs.extend((install.stdout, install.stderr))
        if install.timed_out or install.returncode != 0:
            raise ProbeFailure(PIN_UNAVAILABLE, "pinned package installation failed")

        dry_run = run_command(
            _stryker_command(workspace, node, "--dryRunOnly"),
            cwd=workspace,
            timeout_seconds=120,
        )
        raw_outputs.extend((dry_run.stdout, dry_run.stderr))
        dry_run_duration = dry_run.duration_ms
        if dry_run.timed_out or dry_run.returncode != 0:
            raise ProbeFailure(FAILED, "Stryker dry run failed")

        mutation = run_command(
            _stryker_command(workspace, node),
            cwd=workspace,
            timeout_seconds=180,
        )
        raw_outputs.extend((mutation.stdout, mutation.stderr))
        mutation_duration = mutation.duration_ms
        report_path = workspace / "reports" / "mutation.json"
        if classify_execution(mutation, report_exists=report_path.is_file()) != "COMPLETE":
            raise ProbeFailure(FAILED, "mutation execution was not complete")
        raw_report = report_path.read_bytes()
        try:
            mutation_report = json.loads(raw_report.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProbeFailure(FAILED, "mutation report is unreadable") from exc
        mutation_summary = summarize_mutation_report(
            _require_mapping(mutation_report, label="mutation report")
        )
        if not mutation_summary["surviving_feedback_observed"]:
            raise ProbeFailure(FAILED, "no surviving-mutant feedback was observed")

        timeout_result = run_command(
            [str(node), "-e", "setTimeout(() => {}, 60000)"],
            cwd=workspace,
            timeout_seconds=0.2,
        )
        if classify_execution(timeout_result, report_exists=False) != "TIMEOUT":
            raise ProbeFailure(FAILED, "timeout did not fail closed")
        partial_result = CommandResult(0, b"", b"", 0)
        error_result = CommandResult(7, b"", b"", 0)
        if classify_execution(partial_result, report_exists=False) != "PARTIAL":
            raise ProbeFailure(FAILED, "partial execution did not fail closed")
        if classify_execution(error_result, report_exists=False) != "ERROR":
            raise ProbeFailure(FAILED, "error execution did not fail closed")

        audit_payloads = [
            output_policy_path.read_bytes(),
            template_path.read_bytes(),
            package_lock_path.read_bytes(),
            generated_config,
            BASELINE_SOURCE.encode(),
            PRODUCER_SOURCE.encode(),
            BASELINE_TEST.encode(),
            PRODUCER_TEST.encode(),
            raw_report,
            *raw_outputs,
        ]
        marker_hits = audit_forbidden_markers(audit_payloads, markers=markers)
        if marker_hits:
            raise ProbeFailure(
                LEAKAGE_REVIEW_REQUIRED,
                "forbidden marker detected in bounded probe inputs or raw output",
            )

        named_digests = {
            "adapter": _sha256_bytes(adapter_path.read_bytes()),
            "generated_config": _sha256_bytes(generated_config),
            "output_policy": _sha256_bytes(output_policy_path.read_bytes()),
            "package_lock": _sha256_bytes(package_lock_path.read_bytes()),
            "probe_contract": _sha256_bytes(contract_path.read_bytes()),
            "raw_mutation_report": _sha256_bytes(raw_report),
            "stryker_config_template": _sha256_bytes(template_path.read_bytes()),
        }
        completed_result = {
            "schema_version": RESULT_SCHEMA,
            "status": PASSED,
            "runtime": {
                "node_version": runtime["node_version"],
                "node_archive_sha256": runtime["archive_sha256"],
                "package_count": len(packages),
            },
            "scope": {
                "changed_production_file_count": len({item.path for item in ranges}),
                "changed_production_range_count": len(ranges),
                "target_digest": _sha256_bytes(
                    _canonical_json_bytes([item.stryker_target() for item in ranges])
                ),
                "tests_or_generated_target_count": 0,
            },
            "mutation": {
                **mutation_summary,
                "dry_run_duration_ms": dry_run_duration,
                "mutation_duration_ms": mutation_duration,
            },
            "failure_probes": {
                "timeout": "FAIL_CLOSED",
                "partial": "FAIL_CLOSED",
                "error": "FAIL_CLOSED",
            },
            "digests": named_digests,
            "merkle_root": merkle_root(named_digests),
            "diagnostics": [
                "portable Node checksum and version matched the frozen contract",
                "Stryker dry run and bounded mutation run completed",
                "surviving-mutant feedback was observed and retained only as aggregates",
                "raw validator output and synthetic workspace were not retained in-repository",
            ],
            "claim_ceiling": (
                "Updated-ref-independent synthetic compatibility and non-leakage probe only; "
                "not preregistration, arm execution, effectiveness, or wire/runtime integration."
            ),
        }
    finally:
        remove_owned_workspace(workspace)

    if completed_result is None:
        raise ProbeFailure(FAILED, "probe completed without an aggregate result")
    validate_output_policy(completed_result, output_policy)
    _write_result(result_path, completed_result)
    return completed_result


def _failure_result(status: str, reason: str, *, maximum: int) -> dict[str, object]:
    return {
        "schema_version": RESULT_SCHEMA,
        "status": status,
        "runtime": {},
        "scope": {},
        "mutation": {},
        "failure_probes": {},
        "digests": {},
        "merkle_root": hashlib.sha256(b"empty").hexdigest(),
        "diagnostics": [_bounded_diagnostic(reason, maximum=maximum)],
        "claim_ceiling": "Probe did not establish compatibility or non-leakage.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-root", type=Path, required=True)
    parser.add_argument("--node-archive", type=Path, required=True)
    parser.add_argument("--npm-cache", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)

    probe_root = Path(__file__).resolve().parent
    policy = _require_mapping(_read_json(probe_root / "probe-contract.json"), label="contract")
    leakage = _require_mapping(policy["leakage_policy"], label="leakage policy")
    maximum = int(leakage["maximum_diagnostic_characters"])
    try:
        result = execute_probe(
            probe_root=probe_root,
            node_root=args.node_root.resolve(),
            node_archive=args.node_archive.resolve(),
            npm_cache=args.npm_cache.resolve(),
            workspace=args.workspace.resolve(),
            result_path=args.result.resolve(),
        )
    except ProbeFailure as exc:
        result = _failure_result(exc.status, exc.reason, maximum=maximum)
        _write_result(args.result.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
