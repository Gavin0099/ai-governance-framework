#!/usr/bin/env python3
"""One-shot C1 Stryker sidecar attempt-04 runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any

from raw_git_materialize import MaterializationError, materialize, write_json


PROBE_ID = "c1-stryker-sidecar-raw-object-20260822-04"
FRAMEWORK_BASE_COMMIT = "eb66464dbe34eca1efae04d856cb752fefde475e"
BASELINE_COMMIT = "15d5d51356b4808e5fb12782961a94d9985b2ae6"
BASELINE_TREE = "a6946a0ba48f161f40e7ae7e3a4322bdef704e9a"
BASELINE_GITLINKS = {
    "ai-governance-framework": "74b70252fdf6eaac23e427470a88c246c3be888e"
}
REUSED_COMMIT = "f7831551e2988e590734288de66fff2db1c5369c"
IMAGE = "docker.io/library/node@sha256:d649c27dae7ba0137b3cef5dd75baa422c08dc3d9e3fc0c23dfb172dc3cc6436"
ALLOWED_TERMINALS = {
    "SIDECAR_BOUNDARY_PASSED",
    "CONSUMER_GRAPH_CHANGED",
    "SIDECAR_RESOLUTION_FAILED",
    "SIDECAR_LEAKAGE_BLOCKED",
    "SIDECAR_COST_BLOCKED",
}
DENIED_LITERALS = (
    "a607564",
    "softmap",
    "softmissbooks",
    "master-existing",
    "mixed-batch",
    "attempt-c1",
    "oracle_does_not_discriminate",
    "gate3-c1-method-sensitivity",
    "gate1-c1-bugfix-skill-proposal",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(relative_to).as_posix() if relative_to else path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def run_capture(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = None
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return {
        "command": command,
        "exit_code": returncode,
        "timed_out": timed_out,
        "wall_seconds": round(time.monotonic() - started, 3),
        "stdout": stdout_path.name,
        "stderr": stderr_path.name,
    }


def require_pass(step: dict[str, Any], label: str) -> None:
    if step["timed_out"] or step["exit_code"] != 0:
        raise RuntimeError(
            f"SIDECAR_RESOLUTION_FAILED:{label}:exit={step['exit_code']}:timeout={step['timed_out']}"
        )


def resolve_attempt_materialized_root(
    framework_projection_root: Path,
    attempt_repo_relative_path: str,
    runner_file: Path,
) -> Path:
    failure = "SIDECAR_RESOLUTION_FAILED:HARNESS_MATERIALIZED_ROOT_PATH_CONTRACT"
    if not attempt_repo_relative_path or "\\" in attempt_repo_relative_path:
        raise RuntimeError(f"{failure}:NON_CANONICAL_REPO_RELATIVE_PATH")
    relative = PurePosixPath(attempt_repo_relative_path)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or (relative.parts and ":" in relative.parts[0])
    ):
        raise RuntimeError(f"{failure}:UNSAFE_REPO_RELATIVE_PATH")

    projection_root = framework_projection_root.resolve()
    attempt_root = projection_root.joinpath(*relative.parts).resolve()
    try:
        attempt_root.relative_to(projection_root)
    except ValueError as exc:
        raise RuntimeError(f"{failure}:OUTSIDE_PROJECTION_ROOT") from exc

    expected_runner = attempt_root / "run_sidecar_probe.py"
    if runner_file.resolve() != expected_runner:
        raise RuntimeError(f"{failure}:RUNNER_LOCATION_MISMATCH")
    return attempt_root


class Probe:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = args.run_root.resolve()
        self.framework_projection_root = args.framework_projection_root.resolve()
        if self.framework_projection_root != (self.root / "framework-input").resolve():
            raise RuntimeError(
                "SIDECAR_RESOLUTION_FAILED:HARNESS_MATERIALIZED_ROOT_PATH_CONTRACT:"
                "PROJECTION_ROOT_MISMATCH"
            )
        self.attempt_materialized_root = resolve_attempt_materialized_root(
            self.framework_projection_root,
            args.attempt_repo_relative_path,
            Path(__file__),
        )
        self.baseline = self.root / "baseline"
        self.consumer = self.root / "consumer"
        self.tool = self.root / "tool"
        self.probe_input = self.root / "probe-input"
        self.evidence = self.root / "evidence"
        self.steps: dict[str, Any] = {}
        self.docker_phases: list[dict[str, Any]] = []
        self.functional_failure: str | None = None
        self.graph_changed = False
        self.leakage_blocked = False
        self.cost_blocked = False
        self.mount_violation = False
        self.attempt_start_epoch = args.attempt_start_epoch

    def git_output(self, repo: Path, *arguments: str) -> str:
        result = subprocess.run(
            [
                str(self.args.git),
                "-c",
                f"safe.directory={repo.resolve().as_posix()}",
                "-C",
                str(repo),
                *arguments,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"SIDECAR_RESOLUTION_FAILED:GIT:{arguments!r}:"
                f"{result.stderr.decode('utf-8', 'replace').strip()}"
            )
        return result.stdout.decode("utf-8").strip()

    def docker_phase(
        self,
        *,
        name: str,
        network: str,
        workdir: str,
        environment: list[str],
        command: list[str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        container = f"c1-sidecar-a04-{name}-{uuid.uuid4().hex[:10]}"
        docker_command = [
            str(self.args.docker),
            "run",
            "--name",
            container,
            "--platform",
            "linux/amd64",
            "--network",
            network,
            "--cpus",
            "2",
            "--memory",
            "2g",
            "--pids-limit",
            "512",
            "--mount",
            f"type=bind,source={self.consumer},target=/consumer",
            "--mount",
            f"type=bind,source={self.tool},target=/tool",
            "--mount",
            f"type=bind,source={self.probe_input},target=/probe-input,readonly",
            "--mount",
            f"type=bind,source={self.evidence},target=/evidence",
            "--workdir",
            workdir,
        ]
        for item in environment:
            docker_command.extend(["--env", item])
        docker_command.extend([IMAGE, *command])
        stdout_path = self.evidence / f"{name}.stdout.txt"
        stderr_path = self.evidence / f"{name}.stderr.txt"
        started = time.monotonic()
        timed_out = False
        process = subprocess.Popen(
            docker_command,
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(
                [str(self.args.docker), "kill", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            stdout, stderr = process.communicate(timeout=30)
        stdout_path.write_bytes(stdout)
        stderr_path.write_bytes(stderr)

        state_path = self.evidence / f"{name}.container-state.json"
        mounts_path = self.evidence / f"{name}.container-mounts.json"
        state = run_capture(
            [str(self.args.docker), "inspect", container, "--format", "{{json .State}}"],
            cwd=self.root,
            stdout_path=state_path,
            stderr_path=self.evidence / f"{name}.container-state.stderr.txt",
            timeout_seconds=30,
        )
        mounts = run_capture(
            [str(self.args.docker), "inspect", container, "--format", "{{json .Mounts}}"],
            cwd=self.root,
            stdout_path=mounts_path,
            stderr_path=self.evidence / f"{name}.container-mounts.stderr.txt",
            timeout_seconds=30,
        )
        subprocess.run(
            [str(self.args.docker), "rm", "-f", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        oom_killed = False
        if state["exit_code"] == 0:
            try:
                oom_killed = bool(json.loads(state_path.read_text(encoding="utf-8"))["OOMKilled"])
            except (KeyError, json.JSONDecodeError):
                oom_killed = False
        result = {
            "command": docker_command,
            "container_name": container,
            "exit_code": process.returncode,
            "timed_out": timed_out,
            "oom_killed": oom_killed,
            "wall_seconds": round(time.monotonic() - started, 3),
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
            "state_inspect_exit_code": state["exit_code"],
            "mount_inspect_exit_code": mounts["exit_code"],
        }
        self.docker_phases.append(result)
        return result

    def check_mounts(self) -> None:
        expected = ["/consumer", "/evidence", "/probe-input", "/tool"]
        consumer_repo = os.path.normcase(str(self.args.consumer_repo.resolve()))
        for phase in self.docker_phases:
            short = phase["stdout"].removesuffix(".stdout.txt")
            path = self.evidence / f"{short}.container-mounts.json"
            try:
                mounts = json.loads(path.read_text(encoding="utf-8"))
                destinations = sorted(item["Destination"] for item in mounts)
                if destinations != expected:
                    self.mount_violation = True
                for mount in mounts:
                    if os.path.normcase(os.path.abspath(mount["Source"])) == consumer_repo:
                        self.mount_violation = True
            except (OSError, KeyError, json.JSONDecodeError, TypeError):
                self.mount_violation = True

    def execute(self) -> None:
        manifest_path = self.attempt_materialized_root / "validator-sidecar-probe-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["probe_id"] != PROBE_ID:
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:PROBE_ID")
        if manifest["framework_base_commit"] != FRAMEWORK_BASE_COMMIT:
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:FRAMEWORK_BASE_COMMIT_BINDING")

        path_contract_test = run_capture(
            [
                str(self.args.python),
                str(self.attempt_materialized_root / "test_materialized_root_contract.py"),
                "--output",
                str(self.evidence / "materialized-root-contract-self-test.json"),
            ],
            cwd=self.attempt_materialized_root,
            stdout_path=self.evidence / "materialized-root-contract-self-test.stdout.txt",
            stderr_path=self.evidence / "materialized-root-contract-self-test.stderr.txt",
            timeout_seconds=60,
        )
        self.steps["materialized_root_contract_self_test"] = path_contract_test
        require_pass(path_contract_test, "MATERIALIZED_ROOT_CONTRACT_SELF_TEST")
        if json.loads(
            (self.evidence / "materialized-root-contract-self-test.json").read_text(
                encoding="utf-8"
            )
        )["status"] != "PASS":
            raise RuntimeError(
                "SIDECAR_RESOLUTION_FAILED:MATERIALIZED_ROOT_CONTRACT_SELF_TEST_STATUS"
            )

        for label, path, binding in (
            ("GIT", self.args.git, manifest["tcb"]["git"]),
            ("PYTHON", self.args.python, manifest["tcb"]["python"]),
            ("DOCKER", self.args.docker, manifest["execution_environment"]["docker"]),
        ):
            if not path.is_file() or sha256(path) != binding["sha256"] or path.stat().st_size != binding["bytes"]:
                raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:{label}_EXECUTABLE_BINDING")

        version_commands = (
            ("git-version", [str(self.args.git), "--version"], manifest["tcb"]["git"]["version"]),
            ("python-version", [str(self.args.python), "--version"], manifest["tcb"]["python"]["version"]),
        )
        for name, command, expected in version_commands:
            step = run_capture(
                command,
                cwd=self.root,
                stdout_path=self.evidence / f"{name}.stdout.txt",
                stderr_path=self.evidence / f"{name}.stderr.txt",
                timeout_seconds=30,
            )
            self.steps[name.replace("-", "_")] = step
            require_pass(step, name.upper().replace("-", "_"))
            actual = ((self.evidence / f"{name}.stdout.txt").read_text(encoding="utf-8") + (self.evidence / f"{name}.stderr.txt").read_text(encoding="utf-8")).strip()
            if actual != expected:
                raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:{name.upper().replace('-', '_')}_BINDING:{actual}")

        docker_version = run_capture(
            [str(self.args.docker), "version", "--format", "{{json .}}"],
            cwd=self.root,
            stdout_path=self.evidence / "docker-version.json",
            stderr_path=self.evidence / "docker-version.stderr.txt",
            timeout_seconds=60,
        )
        self.steps["docker_version"] = docker_version
        require_pass(docker_version, "DOCKER_VERSION")
        docker_facts = json.loads((self.evidence / "docker-version.json").read_text(encoding="utf-8"))
        docker_binding = manifest["execution_environment"]["docker"]
        if (
            docker_facts["Client"]["Version"] != docker_binding["client_version"]
            or docker_facts["Server"]["Version"] != docker_binding["server_version"]
            or docker_facts["Server"]["Platform"]["Name"] != docker_binding["server_platform"]
        ):
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:DOCKER_VERSION_BINDING")

        remote = run_capture(
            [str(self.args.git), "-C", str(self.args.framework_repo), "ls-remote", "origin", f"refs/heads/{self.args.remote_branch}"],
            cwd=self.root,
            stdout_path=self.evidence / "remote-binding.stdout.txt",
            stderr_path=self.evidence / "remote-binding.stderr.txt",
            timeout_seconds=60,
        )
        self.steps["remote_binding"] = remote
        require_pass(remote, "REMOTE_BINDING_COMMAND")
        remote_head = (self.evidence / "remote-binding.stdout.txt").read_text(encoding="utf-8").split()[0]
        if remote_head != self.args.framework_commit:
            raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:REMOTE_BINDING:{remote_head}")

        actual_tree = self.git_output(self.args.consumer_repo, "rev-parse", f"{BASELINE_COMMIT}^{{tree}}")
        if actual_tree != BASELINE_TREE:
            raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:BASELINE_TREE:{actual_tree}")

        selftest = run_capture(
            [
                str(self.args.python),
                str(self.attempt_materialized_root / "test_raw_git_materialize.py"),
                "--git",
                str(self.args.git),
                "--output",
                str(self.evidence / "raw-materializer-self-test.json"),
            ],
            cwd=self.attempt_materialized_root,
            stdout_path=self.evidence / "raw-materializer-self-test.stdout.txt",
            stderr_path=self.evidence / "raw-materializer-self-test.stderr.txt",
            timeout_seconds=60,
        )
        self.steps["raw_materializer_self_test"] = selftest
        require_pass(selftest, "RAW_MATERIALIZER_SELF_TEST")
        if json.loads((self.evidence / "raw-materializer-self-test.json").read_text(encoding="utf-8"))["status"] != "PASS":
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:RAW_MATERIALIZER_SELF_TEST_STATUS")

        for destination, label in ((self.baseline, "baseline"), (self.consumer, "consumer")):
            record = materialize(
                git=self.args.git,
                repo=self.args.consumer_repo,
                commit=BASELINE_COMMIT,
                destination=destination,
                allowed_gitlinks=BASELINE_GITLINKS,
            )
            write_json(self.evidence / f"{label}-raw-object-inventory.json", record)
            if record["materialized_blob_count"] != 1869 or record["recorded_gitlink_count"] != 1:
                raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:{label.upper()}_PROJECTION_COUNTS")

        reused_paths = [item["source_path"] for item in manifest["reused_input_bindings"]]
        input_source = self.root / "input-source"
        reused = materialize(
            git=self.args.git,
            repo=self.args.framework_repo,
            commit=REUSED_COMMIT,
            destination=input_source,
            paths=reused_paths,
        )
        write_json(self.evidence / "reused-input-raw-object-inventory.json", reused)
        for binding in manifest["reused_input_bindings"]:
            source = input_source.joinpath(*binding["source_path"].split("/"))
            if sha256(source) != binding["sha256"] or source.stat().st_size != binding["bytes"]:
                raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:REUSED_INPUT_BINDING:{binding['source_path']}")
            destination = self.probe_input.joinpath(*binding["materialized_path"].split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        shutil.copyfile(self.probe_input / "tool" / "package.json", self.tool / "package.json")
        shutil.copyfile(self.probe_input / "tool" / "package-lock.json", self.tool / "package-lock.json")
        (self.consumer / "src" / "__tests__").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.probe_input / "probe-fixture" / "src" / "validator-probe-fixture.ts", self.consumer / "src" / "validator-probe-fixture.ts")
        shutil.copyfile(self.probe_input / "probe-fixture" / "src" / "__tests__" / "validator-probe-fixture.test.ts", self.consumer / "src" / "__tests__" / "validator-probe-fixture.test.ts")
        shutil.copyfile(self.probe_input / "vitest.sidecar-probe.config.mjs", self.consumer / "vitest.sidecar-probe.config.mjs")

        range_step = run_capture(
            [
                str(self.args.python),
                str(self.probe_input / "diff_to_mutation_ranges.py"),
                "--baseline-root",
                str(self.baseline),
                "--candidate-root",
                str(self.consumer),
                "--output",
                str(self.evidence / "mutation-ranges.json"),
            ],
            cwd=self.root,
            stdout_path=self.evidence / "range-adapter.stdout.txt",
            stderr_path=self.evidence / "range-adapter.stderr.txt",
            timeout_seconds=60,
        )
        self.steps["mutation_range"] = range_step
        require_pass(range_step, "MUTATION_RANGE")
        range_record = json.loads((self.evidence / "mutation-ranges.json").read_text(encoding="utf-8"))
        ranges = range_record["mutate_ranges"]
        excluded = range_record["excluded_changed_paths"]
        if ranges != ["src/validator-probe-fixture.ts:1-4"]:
            raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:MUTATION_RANGE_VALUE:{ranges!r}")
        if excluded != ["src/__tests__/validator-probe-fixture.test.ts", "vitest.sidecar-probe.config.mjs"]:
            raise RuntimeError(f"SIDECAR_RESOLUTION_FAILED:MUTATION_EXCLUSION_VALUE:{excluded!r}")
        range_json = json.dumps(ranges, separators=(",", ":"))

        phases = (
            ("tool-npm-ci", "bridge", "/tool", [], ["npm", "ci"], 300),
            ("consumer-npm-ci", "bridge", "/consumer", [], ["npm", "ci"], 600),
            ("consumer-graph-before", "none", "/consumer", [], ["node", "/probe-input/dependency-graph-fingerprint.mjs"], 120),
            ("resolution-probe", "none", "/consumer", [], ["node", "/probe-input/resolution-probe.mjs"], 120),
        )
        for name, network, workdir, environment, command, timeout in phases:
            result = self.docker_phase(name=name, network=network, workdir=workdir, environment=environment, command=command, timeout_seconds=timeout)
            self.steps[name.replace("-", "_")] = result
            require_pass(result, name.upper().replace("-", "_"))

        timeout_result = self.docker_phase(
            name="timeout-sentinel",
            network="none",
            workdir="/consumer",
            environment=[],
            command=["node", "-e", "setTimeout(() => {}, 10000)"],
            timeout_seconds=2,
        )
        self.steps["timeout_sentinel"] = timeout_result
        if not timeout_result["timed_out"] or timeout_result["oom_killed"]:
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:TIMEOUT_SENTINEL")

        for name, dry in (("stryker-dry-run", "1"), ("stryker-mutation", "0")):
            result = self.docker_phase(
                name=name,
                network="none",
                workdir="/consumer",
                environment=[
                    f"C1_SIDECAR_MUTATE_RANGES_JSON={range_json}",
                    f"C1_SIDECAR_DRY_RUN_ONLY={dry}",
                    "C1_SIDECAR_RUNTIME_EVIDENCE_DIR=/evidence",
                    f"C1_SIDECAR_RUNTIME_PHASE={'dry-run' if dry == '1' else 'mutation'}",
                ],
                command=["node", "/tool/node_modules/@stryker-mutator/core/bin/stryker.js", "run", "/probe-input/stryker.sidecar.config.mjs"],
                timeout_seconds=300,
            )
            self.steps[name.replace("-", "_")] = result
            require_pass(result, name.upper().replace("-", "_"))

        after = self.docker_phase(
            name="consumer-graph-after",
            network="none",
            workdir="/consumer",
            environment=[],
            command=["node", "/probe-input/dependency-graph-fingerprint.mjs"],
            timeout_seconds=120,
        )
        self.steps["consumer_graph_after"] = after
        require_pass(after, "CONSUMER_GRAPH_AFTER")
        before_graph = json.loads((self.evidence / "consumer-graph-before.stdout.txt").read_text(encoding="utf-8"))
        after_graph = json.loads((self.evidence / "consumer-graph-after.stdout.txt").read_text(encoding="utf-8"))
        graph_fields = (
            "package_json_sha256",
            "package_lock_sha256",
            "node_modules_package_lock_sha256",
            "npm_ls_exit_code",
            "npm_ls_canonical_sha256",
            "npm_ls_stderr_sha256",
        )
        self.graph_changed = any(before_graph[field] != after_graph[field] for field in graph_fields)
        if len(list(self.evidence.glob("vitest-runtime-resolution-*.json"))) < 2:
            raise RuntimeError("SIDECAR_RESOLUTION_FAILED:VITEST_RUNTIME_RECORD_COUNT")

    def finish(self) -> str:
        self.check_mounts()
        if any(item["oom_killed"] for item in self.docker_phases):
            self.cost_blocked = True
        elapsed = time.time() - self.attempt_start_epoch
        if elapsed > 900:
            self.cost_blocked = True

        denied_hits: list[dict[str, str]] = []
        for path in sorted(self.evidence.iterdir()):
            if not path.is_file() or path.name in {"non-leakage-scan.json", "probe-terminal.json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            for literal in DENIED_LITERALS:
                if literal.lower() in text:
                    denied_hits.append({"file": path.name, "literal": literal})
        self.leakage_blocked = bool(denied_hits) or self.mount_violation
        write_json(
            self.evidence / "non-leakage-scan.json",
            {
                "schema": "c1-stryker-sidecar-non-leakage.v1",
                "scanned_surface_count": len([p for p in self.evidence.iterdir() if p.is_file()]),
                "denied_match_count": len(denied_hits),
                "denied_matches": denied_hits,
                "mount_violation": self.mount_violation,
                "consumer_worktree_mounted": self.mount_violation,
            },
        )

        if self.leakage_blocked:
            terminal = "SIDECAR_LEAKAGE_BLOCKED"
        elif self.graph_changed:
            terminal = "CONSUMER_GRAPH_CHANGED"
        elif self.cost_blocked:
            terminal = "SIDECAR_COST_BLOCKED"
        elif self.functional_failure is not None:
            terminal = "SIDECAR_RESOLUTION_FAILED"
        else:
            terminal = "SIDECAR_BOUNDARY_PASSED"
        if terminal not in ALLOWED_TERMINALS:
            raise AssertionError(f"TERMINAL_OUTSIDE_CLOSED_SET:{terminal}")

        artifacts = [
            file_record(path, relative_to=self.evidence)
            for path in sorted(self.evidence.iterdir())
            if path.is_file() and path.name != "probe-terminal.json"
        ]
        manifest_path = self.attempt_materialized_root / "validator-sidecar-probe-manifest.json"
        terminal_record = {
            "schema": "c1-stryker-sidecar-probe-terminal.v3",
            "probe_id": PROBE_ID,
            "terminal": terminal,
            "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bindings": {
                "framework_commit": self.args.framework_commit,
                "remote_branch": self.args.remote_branch,
                "source_baseline_commit": BASELINE_COMMIT,
                "source_baseline_tree": BASELINE_TREE,
                "source_gitlink": {"path": "ai-governance-framework", "mode": "160000", "type": "commit", "oid": BASELINE_GITLINKS["ai-governance-framework"], "materialized": False},
                "reused_design_commit": REUSED_COMMIT,
                "image": IMAGE,
                "manifest_sha256": sha256(manifest_path),
                "manifest_bytes": manifest_path.stat().st_size,
            },
            "raw_object_materialization": {
                "working_tree_conversion_used": False,
                "consumer_and_framework_inputs_covered": True,
                "unsupported_modes_fail_closed": True,
                "gitlink_dereferenced": False,
                "tcb_conditioned": True,
            },
            "steps": self.steps,
            "functional_failure": self.functional_failure,
            "classification": {
                "leakage_blocked": self.leakage_blocked,
                "consumer_graph_changed": self.graph_changed,
                "cost_blocked": self.cost_blocked,
                "resolution_failed": self.functional_failure is not None,
                "selected_terminal": terminal,
            },
            "resources": {
                "total_wall_seconds": round(elapsed, 3),
                "ceiling_seconds": 900,
                "docker_phase_count": len(self.docker_phases),
                "any_oom_killed": any(item["oom_killed"] for item in self.docker_phases),
            },
            "repair_in_place": False,
            "retry_authorized": False,
            "artifacts": artifacts,
            "claim_ceiling": "Conditional on the declared TCB, this attempt may establish only whether the materialized projection equals the committed bytes of the specified Git objects and whether this exact C1/Stryker sidecar boundary passes its frozen technical checks. It cannot establish correctness of Git, Python, or the bootstrap launcher; validator effect; Skill effect; general reuse; Gate 1 readiness; preregistration; freeze; or an A/B/C/D result.",
            "not_claimed": [
                "Git/Python/bootstrap correctness",
                "validator effect",
                "Skill effect",
                "general raw-object materializer reuse",
                "general sidecar reuse",
                "Gate 1 readiness",
                "preregistration",
                "Gate 1 freeze",
                "A/B/C/D result",
            ],
        }
        write_json(self.evidence / "probe-terminal.json", terminal_record)
        return terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework-repo", required=True, type=Path)
    parser.add_argument("--consumer-repo", required=True, type=Path)
    parser.add_argument("--framework-commit", required=True)
    parser.add_argument("--remote-branch", required=True)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--framework-projection-root", required=True, type=Path)
    parser.add_argument("--attempt-repo-relative-path", required=True)
    parser.add_argument("--attempt-start-epoch", required=True, type=float)
    parser.add_argument("--git", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--docker", required=True, type=Path)
    args = parser.parse_args(argv)
    probe = Probe(args)
    for directory in (probe.baseline, probe.consumer, probe.tool, probe.probe_input, probe.evidence):
        directory.mkdir(parents=True, exist_ok=True)
    try:
        probe.execute()
    except Exception as exc:
        probe.functional_failure = f"{type(exc).__name__}:{exc}"
    terminal = probe.finish()
    print(f"terminal={terminal}")
    print(f"terminal_path={probe.evidence / 'probe-terminal.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
