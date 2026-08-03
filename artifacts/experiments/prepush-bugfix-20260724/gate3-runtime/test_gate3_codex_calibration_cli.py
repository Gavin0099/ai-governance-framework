"""Tests for the calibration probe CLI.

The CLI is the one seam that supplies a real runner, so what matters is that it
cannot be pointed at anything else: a pair authorization must not reach the
orchestrator, and the route plan it writes must pin every executable the runner
will load.

No test here starts a session. The runner is replaced wherever a session would
otherwise happen.
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_calibration as calibration  # noqa: E402
import gate3_codex_calibration_cli as cli  # noqa: E402
import gate3_codex_calibration_probe as probe  # noqa: E402
import gate3_codex_live_canary as live  # noqa: E402

PAIR_AUTHORIZATION = "non_counted_codex_live_canary_only"


def _prompt(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.txt"
    path.write_bytes(b"calibration prompt\n")
    return path


def test_a_pair_authorization_never_reaches_the_orchestrator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("orchestrate must not be reached")

    monkeypatch.setattr(probe, "orchestrate", explode)
    report = tmp_path / "report.json"
    code = cli._main(
        [
            "--authorization", PAIR_AUTHORIZATION,
            "--run-id", "calibration-test",
            "--out", str(tmp_path / "receipt.json"),
            "--prompt", str(_prompt(tmp_path)),
            "--json-out", str(report),
        ]
    )
    assert code == 2
    parsed = json.loads(report.read_text(encoding="utf-8"))
    assert parsed["status"] == "FAIL"
    assert "authorization is invalid" in parsed["error"]
    assert not (tmp_path / "receipt.json").exists()


def test_the_cli_passes_the_calibration_authorization_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def capture(success_path: Path, **kwargs: object):
        seen.update(kwargs)
        seen["success_path"] = success_path
        return probe.ProbeResult(tmp_path / "private.json", tmp_path / "pub.json")

    monkeypatch.setattr(probe, "orchestrate", capture)
    code = cli._main(
        [
            "--authorization", calibration.AUTHORIZATION,
            "--run-id", "calibration-test",
            "--out", str(tmp_path / "receipt.json"),
            "--prompt", str(_prompt(tmp_path)),
        ]
    )
    assert code == 0
    assert seen["authorization"] == calibration.AUTHORIZATION
    assert seen["expected_prompt"] == b"calibration prompt\n"
    assert set(seen["signed_identity"]) == {
        "cli_version",
        "comp_hash",
        "effort",
        "model",
    }
    assert seen["implementation_identity"] == cli._implementation_identity()
    assert callable(seen["runner"])


def test_the_route_plan_pins_every_executable(tmp_path: Path) -> None:
    """Including the shared credential file the runner dot-sources."""
    plan_path = tmp_path / "route-plan.json"
    cli._route_plan(plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["schema"] == cli.ROUTE_PLAN_SCHEMA
    assert plan["authorization"] == calibration.AUTHORIZATION
    frozen = plan["frozen_route"]
    assert set(frozen) == {
        "calibration_runner_implementation_sha256",
        "credential_common_implementation_sha256",
        "launcher_implementation_sha256",
    }
    assert frozen["calibration_runner_implementation_sha256"] == (
        live._sha256_file(cli.CALIBRATION_RUNNER)
    )
    assert frozen["credential_common_implementation_sha256"] == (
        live._sha256_file(live.DEFAULT_CREDENTIAL_COMMON)
    )
    assert frozen["launcher_implementation_sha256"] == (
        live._sha256_file(live.DEFAULT_SESSION_LAUNCHER)
    )
    assert cli._route_plan(plan_path) == live._sha256_file(plan_path)
    assert set(cli._implementation_identity()) == probe.IMPLEMENTATION_FIELDS


@pytest.mark.parametrize(
    ("session_invocations", "schema"),
    [
        (2, cli.RUNNER_RECEIPT_SCHEMA),
        (1, "gate3-codex-calibration-runner-receipt.v1"),
    ],
    ids=["two-sessions", "superseded-schema"],
)
def test_an_invalid_runner_receipt_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_invocations: int,
    schema: str,
) -> None:
    """The CLI re-checks the count rather than trusting the runner's exit."""
    receipt = {
        "auth_files_removed": True,
        "authorization": calibration.AUTHORIZATION,
        "implementation": {
            "calibration_runner_sha256": cli._implementation_identity()[
                "calibration_runner_sha256"
            ],
            "credential_common_sha256": cli._implementation_identity()[
                "credential_common_sha256"
            ],
            "launcher_sha256": cli._implementation_identity()[
                "session_launcher_sha256"
            ],
        },
        "replacement_sessions": 0,
        "route_plan_sha256": cli._implementation_identity()["route_plan_sha256"],
        "schema": schema,
        "secret_material_retained": False,
        "session_invocations": session_invocations,
    }

    class _Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    real_run = cli.subprocess.run

    def fake_run(args, *rest, **kwargs):
        # Intercept only the calibration runner. Everything else, including the
        # workspace git init, must still really happen.
        text = [str(item) for item in args]
        if not any(cli.CALIBRATION_RUNNER.name in item for item in text):
            return real_run(args, *rest, **kwargs)
        for index, item in enumerate(text):
            if item == "-PrivateReceiptPath":
                target = Path(text[index + 1])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(receipt), encoding="utf-8")
        return _Completed()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    runner = cli._live_runner(
        _prompt(tmp_path),
        "codex",
        cli._implementation_identity(),
        _acl_setter=lambda _path, _container: None,
    )
    with pytest.raises(probe.ProbeError, match="receipt is invalid"):
        runner()


def test_the_cli_starts_no_session_of_its_own() -> None:
    """Session invocation belongs to the runner script, not to this module."""
    code = chr(10).join(
        line
        for line in Path(cli.__file__).read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "gate3_codex_pair_runner" not in code
    assert str(cli.CALIBRATION_RUNNER.name) in code


def test_private_root_acl_is_applied_before_any_bytes_are_written(
    tmp_path: Path,
) -> None:
    observed: list[tuple[Path, bool]] = []

    def refuse_after_inspection(path: Path, container: bool) -> None:
        assert path.is_dir()
        assert list(path.iterdir()) == []
        observed.append((path, container))
        raise probe.ProbeError("synthetic ACL refusal")

    runner = cli._live_runner(
        _prompt(tmp_path),
        "codex",
        cli._implementation_identity(),
        _acl_setter=refuse_after_inspection,
    )
    with pytest.raises(probe.ProbeError, match="synthetic ACL refusal"):
        runner()
    assert len(observed) == 1
    assert observed[0][1] is True


def test_runner_private_cleanup_failure_is_visible_and_fail_closed(
    tmp_path: Path,
) -> None:
    def never_cleans(_path: Path) -> None:
        raise probe.ProbeError(
            "calibration runner private cleanup failed",
            residue_classes=("runner_private_runtime",),
        )

    runner = cli._live_runner(
        _prompt(tmp_path),
        "codex",
        cli._implementation_identity(),
        _acl_setter=lambda _path, _container: (_ for _ in ()).throw(
            probe.ProbeError("synthetic runner stop")
        ),
        _cleanup=never_cleans,
    )
    with pytest.raises(probe.ProbeError) as caught:
        runner()
    assert caught.value.residue_classes == ("runner_private_runtime",)


def test_concurrent_source_swap_executes_the_locked_python_snapshot(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "executed-sha256.txt"
    marker = tmp_path / "malicious-marker.txt"
    safe_cli = (
        "import hashlib, pathlib, sys\n"
        "data = pathlib.Path(__file__).read_bytes()\n"
        "pathlib.Path(sys.argv[1]).write_text("
        "hashlib.sha256(data).hexdigest(), encoding='ascii')\n"
    ).encode("utf-8")
    for name in cli.SNAPSHOT_FILES:
        (source / name).write_bytes(
            safe_cli if name == Path(cli.__file__).name else b"# frozen\n"
        )
    expected = hashlib.sha256(safe_cli).hexdigest()

    def swap_after_lock(snapshot: Path) -> None:
        (source / Path(cli.__file__).name).write_text(
            "import pathlib\n"
            f"pathlib.Path({str(marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )
        with pytest.raises(OSError):
            (snapshot / Path(cli.__file__).name).write_text(
                "unverified\n", encoding="utf-8"
            )

    code = cli._run_from_runtime_snapshot(
        [str(output)],
        _source_root=source,
        _after_locked=swap_after_lock,
    )
    assert code == 0
    assert output.read_text(encoding="ascii") == expected
    assert not marker.exists()


def test_script_entry_reexecutes_from_a_verified_snapshot(tmp_path: Path) -> None:
    prompt = _prompt(tmp_path)
    before = set(
        Path(tempfile.gettempdir()).glob("gate3-calibration-runtime-*")
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(cli.__file__)),
            "--authorization",
            "invalid-calibration-authorization",
            "--run-id",
            "snapshot-entry-test",
            "--out",
            str(tmp_path / "receipt.json"),
            "--prompt",
            str(prompt),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 2
    assert "authorization is invalid" in completed.stderr
    assert set(Path(tempfile.gettempdir()).glob("gate3-calibration-runtime-*")) == before


def test_imported_main_cannot_bypass_the_snapshot() -> None:
    prior = cli._SNAPSHOT_VERIFIED
    cli._SNAPSHOT_VERIFIED = False
    try:
        with pytest.raises(RuntimeError, match="snapshot is required"):
            cli.main([])
    finally:
        cli._SNAPSHOT_VERIFIED = prior


def test_matching_manifest_environment_without_parent_lock_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = Path(cli.__file__).parent / "snapshot-manifest.json"
    manifest.write_bytes(cli._snapshot_payload(Path(cli.__file__).parent))
    try:
        monkeypatch.setenv(cli.SNAPSHOT_MANIFEST_ENV, str(manifest))
        forged = {
            name: 99999999
            for name in (*cli.SNAPSHOT_FILES, "snapshot-manifest.json")
        }
        monkeypatch.setenv(
            cli.SNAPSHOT_LOCK_HANDLES_ENV,
            json.dumps(forged, sort_keys=True, separators=(",", ":")),
        )
        with pytest.raises(RuntimeError, match="snapshot lock is invalid"):
            cli._verify_runtime_snapshot()
    finally:
        manifest.unlink()
