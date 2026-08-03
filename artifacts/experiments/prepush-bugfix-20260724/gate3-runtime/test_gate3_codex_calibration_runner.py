"""Tests for the single-session calibration runner.

The two things that matter here are that a calibration authorization cannot
spend a pair's worth of sessions, and that a pair authorization cannot be spent
here at all. Credential handling itself is shared with the pair runner rather
than reimplemented, so it is covered once, there; what is covered here is that
the sharing did not create a new unpinned execution surface.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_live_canary as live  # noqa: E402

RUNNER = HERE / "gate3_codex_calibration_runner.ps1"
CALIBRATION_AUTHORIZATION = "non_counted_codex_calibration_probe_only"
PAIR_AUTHORIZATION = "non_counted_codex_live_canary_only"
PRODUCTION_BINDING = (
    "$credentialSource = Join-Path "
    "([Environment]::GetFolderPath('UserProfile')) "
    "'.codex\\auth.json'"
)


def _fake_codex(path: Path) -> None:
    """A stand-in that records every invocation, so they can be counted."""
    path.write_text(
        "@echo off\r\n"
        'echo %CODEX_HOME%>>"%FAKE_CODEX_LOG%"\r\n'
        'if /I "%1"=="login" (\r\n'
        "  echo Logged in using ChatGPT\r\n"
        "  exit /b 0\r\n"
        ")\r\n"
        "exit /b 0\r\n",
        encoding="ascii",
        newline="",
    )


@pytest.fixture
def rig():
    root = Path(tempfile.mkdtemp(prefix="gate3-calibration-test-"))
    runtime = root / "runtime"
    runtime.mkdir()
    runner = runtime / RUNNER.name
    launcher = runtime / live.DEFAULT_SESSION_LAUNCHER.name
    common = runtime / live.DEFAULT_CREDENTIAL_COMMON.name

    credential = root / "private-auth.json"
    credential.write_text('{"fake":"credential"}\n', encoding="utf-8")
    source = RUNNER.read_text(encoding="utf-8")
    assert PRODUCTION_BINDING in source
    runner.write_text(
        source.replace(
            PRODUCTION_BINDING,
            "$credentialSource = " + repr(str(credential)),
            1,
        ),
        encoding="utf-8",
        newline="\n",
    )
    launcher.write_bytes(live.DEFAULT_SESSION_LAUNCHER.read_bytes())
    common.write_bytes(live.DEFAULT_CREDENTIAL_COMMON.read_bytes())

    fake = root / "fake-codex.cmd"
    _fake_codex(fake)
    private = root / "private"
    private.mkdir()
    workspace = root / "workspace"
    workspace.mkdir()
    live._git(workspace, "init", "-q")
    home = root / "codex-home"
    home.mkdir()
    prompt = root / "prompt.txt"
    prompt.write_text("calibration prompt\n", encoding="utf-8")

    plan = root / "route-plan.json"
    state = {
        "root": root,
        "runner": runner,
        "common": common,
        "launcher": launcher,
        "fake": fake,
        "log": root / "calls.txt",
        "plan": plan,
        "workspace": workspace,
        "home": home,
        "prompt": prompt,
        "private": private,
        "receipt": private / "calibration-runner-receipt.json",
    }
    _write_plan(state)
    yield state
    shutil.rmtree(root, ignore_errors=True)


def _write_plan(state, **overrides) -> None:
    frozen = {
        "calibration_runner_implementation_sha256": live._sha256_file(
            state["runner"]
        ),
        "credential_common_implementation_sha256": live._sha256_file(
            state["common"]
        ),
        "launcher_implementation_sha256": live._sha256_file(state["launcher"]),
    }
    frozen.update(overrides.pop("frozen_route", {}))
    plan = {
        "authorization": CALIBRATION_AUTHORIZATION,
        "frozen_route": frozen,
        "schema": "gate3-codex-calibration-route-plan.v2",
    }
    plan.update(overrides)
    state["plan"].write_bytes(live._json_bytes(plan))


def _run(state, *, authorization: str = CALIBRATION_AUTHORIZATION):
    env = os.environ.copy()
    env["FAKE_CODEX_LOG"] = str(state["log"])
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(state["runner"]),
            "-Authorization",
            authorization,
            "-CodexCommand",
            str(state["fake"]),
            "-RoutePlanPath",
            str(state["plan"]),
            "-Workspace",
            str(state["workspace"]),
            "-PromptPath",
            str(state["prompt"]),
            "-CodexHome",
            str(state["home"]),
            "-StdoutPath",
            str(state["private"] / "out"),
            "-StderrPath",
            str(state["private"] / "err"),
            "-ExitCodePath",
            str(state["private"] / "exit"),
            "-PrivateReceiptPath",
            str(state["receipt"]),
        ],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=180,
    )


def test_exactly_one_session_is_invoked(rig) -> None:
    result = _run(rig)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(rig["receipt"].read_text(encoding="utf-8"))
    assert receipt["session_invocations"] == 1
    assert receipt["replacement_sessions"] == 0
    assert receipt["authorization"] == CALIBRATION_AUTHORIZATION
    assert receipt["schema"] == "gate3-codex-calibration-runner-receipt.v2"
    assert receipt["login_status"] == "PASS"
    # One login preflight plus one session. A pair would show three.
    assert len(rig["log"].read_text(encoding="utf-8").splitlines()) == 2


def test_a_pair_authorization_cannot_be_spent_here(rig) -> None:
    """The reason this is a separate script and not a mode switch.

    One executable carrying both authorizations is one defect away from
    letting a calibration authorization spend a pair's worth of sessions.
    """
    result = _run(rig, authorization=PAIR_AUTHORIZATION)
    assert result.returncode == 2
    assert "authorization is invalid" in result.stderr
    assert not rig["log"].exists()
    assert not rig["receipt"].exists()


def test_authorization_is_checked_before_any_credential_is_touched(
    rig,
) -> None:
    result = _run(rig, authorization="")
    assert result.returncode != 0
    assert not rig["log"].exists()
    assert not rig["receipt"].exists()


def test_the_route_plan_must_pin_this_runner(rig) -> None:
    _write_plan(
        rig,
        frozen_route={"calibration_runner_implementation_sha256": "0" * 64},
    )
    result = _run(rig)
    # The preflight throws before the try block, so PowerShell exits 1 here,
    # the same convention the pair runner uses. What matters is that nothing ran.
    assert result.returncode != 0
    assert not rig["log"].exists()


def test_the_route_plan_must_pin_the_shared_credential_file(rig) -> None:
    _write_plan(
        rig,
        frozen_route={"credential_common_implementation_sha256": "0" * 64},
    )
    result = _run(rig)
    # The preflight throws before the try block, so PowerShell exits 1 here,
    # the same convention the pair runner uses. What matters is that nothing ran.
    assert result.returncode != 0
    assert not rig["log"].exists()


def test_a_tampered_shared_credential_file_is_refused(rig) -> None:
    """Sharing must not create an unpinned execution surface.

    Extracting the credential primitives is only safe if the extracted file is
    pinned as tightly as the runner that dot-sources it.
    """
    rig["common"].write_text(
        rig["common"].read_text(encoding="utf-8") + "\n# tampered\n",
        encoding="utf-8",
        newline="\n",
    )
    result = _run(rig)
    # The preflight throws before the try block, so PowerShell exits 1 here,
    # the same convention the pair runner uses. What matters is that nothing ran.
    assert result.returncode != 0
    assert not rig["log"].exists()


def test_tampered_shared_code_cannot_execute_before_digest_refusal(rig) -> None:
    marker = rig["root"] / "common-executed.txt"
    escaped = str(marker).replace("'", "''")
    rig["common"].write_text(
        f"Set-Content -LiteralPath '{escaped}' -Value 'executed'\n"
        + rig["common"].read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    result = _run(rig)
    assert result.returncode != 0
    assert not marker.exists()
    assert not rig["log"].exists()


def test_concurrent_source_swap_cannot_change_locked_snapshot(rig) -> None:
    """Swap both originals after snapshot lock; only frozen copies may run."""
    marker = rig["root"] / "concurrent-marker.txt"
    safe_common_sha = live._sha256_file(rig["common"])
    safe_launcher_sha = live._sha256_file(rig["launcher"])
    # Keep the runner alive after publishing snapshot-ready.json.
    fake_text = rig["fake"].read_text(encoding="ascii")
    rig["fake"].write_text(
        fake_text.replace("@echo off\n", "@echo off\nping -n 3 127.0.0.1 >nul\n"),
        encoding="ascii",
        newline="",
    )
    observed: dict[str, object] = {}

    def invoke() -> None:
        observed["result"] = _run(rig)

    thread = threading.Thread(target=invoke)
    thread.start()
    deadline = time.monotonic() + 20
    snapshot: Path | None = None
    while time.monotonic() < deadline:
        candidates = list(rig["private"].glob(".implementation-snapshot-*"))
        if candidates and (candidates[0] / "snapshot-ready.json").exists():
            snapshot = candidates[0]
            break
        time.sleep(0.01)
    assert snapshot is not None, "runner did not publish its locked snapshot"
    escaped = str(marker).replace("'", "''")
    rig["common"].write_text(
        f"Set-Content -LiteralPath '{escaped}' -Value 'common'\n",
        encoding="utf-8",
        newline="\n",
    )
    rig["launcher"].write_text(
        f"Set-Content -LiteralPath '{escaped}' -Value 'launcher'\nexit 0\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(OSError):
        (snapshot / live.DEFAULT_CREDENTIAL_COMMON.name).write_text(
            "unverified\n", encoding="utf-8"
        )
    thread.join(timeout=30)
    assert not thread.is_alive()
    result = observed["result"]
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    receipt = json.loads(rig["receipt"].read_text(encoding="utf-8"))
    assert receipt["implementation"] == {
        "calibration_runner_sha256": live._sha256_file(rig["runner"]),
        "credential_common_sha256": safe_common_sha,
        "launcher_sha256": safe_launcher_sha,
    }


def test_the_route_plan_authorization_must_also_be_calibration(rig) -> None:
    _write_plan(rig, authorization=PAIR_AUTHORIZATION)
    result = _run(rig)
    # The preflight throws before the try block, so PowerShell exits 1 here,
    # the same convention the pair runner uses. What matters is that nothing ran.
    assert result.returncode != 0
    assert not rig["log"].exists()


def test_the_superseded_route_plan_schema_is_refused(rig) -> None:
    _write_plan(rig, schema="gate3-codex-calibration-route-plan.v1")
    result = _run(rig)
    assert result.returncode != 0
    assert not rig["log"].exists()


def test_the_runner_binds_production_credentials_and_user_temp() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "[string]$CredentialSource" not in source
    assert PRODUCTION_BINDING in source
    assert "Get-UserTempRoot" in source
    assert "Assert-UserTempPath" in source


def test_credential_logic_is_shared_rather_than_copied() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    common = live.DEFAULT_CREDENTIAL_COMMON.read_text(encoding="utf-8")
    for name in (
        "function Assert-UserTempPath",
        "function Copy-PrivateCredential",
        "function Set-CurrentUserOnlyAcl",
        "function Test-ChatGptLogin",
        "function Test-ExactBytes",
    ):
        assert name not in source, name
        assert name in common, name
    pair = live.DEFAULT_PAIR_RUNNER.read_text(encoding="utf-8")
    for name in ("function Copy-PrivateCredential", "function Test-ChatGptLogin"):
        assert name not in pair, name


def test_the_runner_admits_nothing() -> None:
    """It produces a rollout and an exit code. It does not judge them.

    Comment lines are stripped first. Grepping prose would let the test pass
    or fail on wording rather than on what the script does.
    """
    code = chr(10).join(
        line
        for line in RUNNER.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ).lower()
    for forbidden in ("admission", "scorer", "packet", "qualifying"):
        assert forbidden not in code, forbidden
