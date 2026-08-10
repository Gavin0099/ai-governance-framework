from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route
import gate3_route_v2_ab as pair
import gate3_route_v2_ab_live as live
import gate3_route_v2_codex as codex


PAIR_ID = "gate3-v2-live-ab-synthetic-0001"
RUN_IDS = (
    "gate3-v2-live-ab-synthetic-arm-a-0001",
    "gate3-v2-live-ab-synthetic-arm-b-0001",
)
MODEL_ID = "owner-selected-model-v1"
TREATMENT = b"synthetic skill packet\n"


def _contained(*, stdout: bytes, returncode: int = 0) -> codex._ContainedResult:
    return codex._ContainedResult(
        returncode=returncode,
        stdout=stdout,
        stderr=b"",
        timed_out=False,
        tree_terminated=True,
    )


def _probe(
    command: list[str] | tuple[str, ...], cwd: Path, env: dict[str, str]
) -> codex._ContainedResult:
    if command[-1] == "--version":
        return _contained(stdout=(codex.PINNED_CLI_VERSION + "\n").encode())
    return _contained(stdout=(" ".join(codex.AB_REQUIRED_FLAGS) + "\n").encode())


def _preflight(tmp_path: Path, arm: str, run_id: str) -> tuple[bytes, Path]:
    return codex._measure_ab_preflight(
        run_id=run_id,
        executable=Path(sys.executable),
        expected_executable_sha256=route._sha256_file(Path(sys.executable)),
        preflight_root=tmp_path / f"preflight-{arm}",
        probe=_probe,
    )


def _staged() -> dict[str, dict[str, bytes]]:
    packet_digest = route._sha256_bytes(TREATMENT)
    common = dict(codex.BASELINE_WORKSPACE)
    return {
        "A": {
            **common,
            "treatment-manifest.json": pair.treatment_manifest(
                "absent", "absent"
            ),
        },
        "B": {
            **common,
            "skill.packet": TREATMENT,
            "treatment-manifest.json": pair.treatment_manifest(
                "present", packet_digest
            ),
        },
    }


def _manifest(tmp_path: Path) -> tuple[bytes, dict[str, bytes], dict[str, Path], dict[str, bytes]]:
    preflight_a, executable_a = _preflight(tmp_path, "a", RUN_IDS[0])
    preflight_b, executable_b = _preflight(tmp_path, "b", RUN_IDS[1])
    staged = _staged()
    manifest = live.build_live_contract_manifest(
        pair_id=PAIR_ID,
        model_id=MODEL_ID,
        run_ids=RUN_IDS,
        context_tokens=("ARM_A_CONTEXT", "ARM_B_CONTEXT"),
        preflight=preflight_a,
        prompt=codex.PROMPT,
        output_schema=codex.OUTPUT_SCHEMA,
        baseline_workspace=codex.BASELINE_WORKSPACE,
        expected_workspace=codex.EXPECTED_WORKSPACE,
        arm_a_files=staged["A"],
        arm_b_files=staged["B"],
        treatment_packet_sha256=route._sha256_bytes(TREATMENT),
    )
    return (
        manifest,
        {"A": preflight_a, "B": preflight_b},
        {"A": executable_a, "B": executable_b},
        staged,
    )


def _auth(tmp_path: Path) -> Path:
    auth = tmp_path / "auth.json"
    auth.write_bytes(b"{}\n")
    route._current_user_only(auth, False)
    return auth


def _owner_pin(manifest: bytes) -> live.OwnerManifestPin:
    return live._owner_pin_from_bytes(
        route._json_bytes(
            {
                "manifest_sha256": route._sha256_bytes(manifest),
                "schema": live.OWNER_PIN_SCHEMA,
                "status": "SIGNED_AND_PROMOTED",
            }
        )
    )


def test_live_adapter_runs_exactly_two_synthetic_subprocess_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: list[str],
        *,
        input_bytes: bytes,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> codex._ContainedResult:
        calls.append(tuple(command))
        assert command[command.index("--model") + 1] == MODEL_ID
        assert input_bytes == codex.PROMPT
        (cwd / "result.txt").write_bytes(b"CALIBRATION_OK\n")
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_bytes(b'{"status":"ok"}')
        return _contained(stdout=b'{"type":"turn.completed"}\n')

    monkeypatch.setattr(codex, "_run_contained", fake_run)
    output = tmp_path / "pair-public"
    result = live._orchestrate_pinned_pair(
        output,
        contract_manifest=manifest,
        owner_pin=_owner_pin(manifest),
        executable_snapshots=executables,
        measured_preflights=preflights,
        staged_files=staged,
        auth_file=_auth(tmp_path),
    )
    assert result.decision == "SUCCESS"
    assert len(calls) == 2
    assert pair.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=result.pins,
    ) == {
        "claim": "live_non_counted_route_qualification_only",
        "decision": "SUCCESS",
        "pair_id": PAIR_ID,
        "status": "PASS",
    }


def test_live_probe_stderr_difference_publishes_offline_verifiable_non_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    arm_b_preflight = json.loads(preflights["B"])
    for observation in arm_b_preflight["probe_outputs"].values():
        observation["stderr_sha256"] = "0" * 64
    preflights["B"] = route._json_bytes(arm_b_preflight)

    def fake_run(
        command: list[str],
        *,
        input_bytes: bytes,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> codex._ContainedResult:
        (cwd / "result.txt").write_bytes(b"CALIBRATION_OK\n")
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_bytes(b'{"status":"ok"}')
        return _contained(stdout=b'{"type":"turn.completed"}\n')

    monkeypatch.setattr(codex, "_run_contained", fake_run)
    output = tmp_path / "pair-public"
    result = live._orchestrate_pinned_pair(
        output,
        contract_manifest=manifest,
        owner_pin=_owner_pin(manifest),
        executable_snapshots=executables,
        measured_preflights=preflights,
        staged_files=staged,
        auth_file=_auth(tmp_path),
    )

    receipt = json.loads(result.receipt.read_text(encoding="utf-8"))
    assert receipt["checks"]["cross_arm_equality"] == "FAIL"
    assert result.decision == "NON_SUCCESS"
    assert pair.verify_pair(
        output,
        contract_manifest=manifest,
        expected_manifest_sha256=route._sha256_bytes(manifest),
        expected_pins=result.pins,
    )["decision"] == "NON_SUCCESS"


def test_model_and_build_mismatch_fail_before_auth_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    value = json.loads(preflights["B"])
    value["execution_identity"]["command_contract_sha256"] = "0" * 64
    preflights["B"] = route._json_bytes(value)
    auth = tmp_path / "missing-auth.json"
    with pytest.raises(route.RouteV2Error, match="execution identities differ"):
        live._orchestrate_pinned_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            owner_pin=_owner_pin(manifest),
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=auth,
        )
    assert not auth.exists()


def test_zero_session_preflight_verifies_signed_identity_without_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    monkeypatch.setattr(live, "_load_owner_pin", lambda: _owner_pin(manifest))

    receipt = live.verify_live_pair_preflight(
        tmp_path / "pair-public",
        contract_manifest=manifest,
        executable_snapshots=executables,
        measured_preflights=preflights,
        staged_files=staged,
    )

    assert receipt["schema"] == live.PREFLIGHT_RECEIPT_SCHEMA
    assert receipt["authorization"] == live.PREFLIGHT_AUTHORIZATION
    assert set(receipt["checks"].values()) == {"PASS"}
    assert receipt["contract_manifest_sha256"] == route._sha256_bytes(manifest)
    assert receipt["pair_id"] == PAIR_ID
    assert receipt["run_ids"] == list(RUN_IDS)
    assert not (tmp_path / "pair-public").exists()


def test_zero_session_preflight_rejects_coherent_identity_drift_without_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    for arm_id in ("A", "B"):
        value = json.loads(preflights[arm_id])
        value["execution_identity"]["command_contract_sha256"] = "0" * 64
        preflights[arm_id] = route._json_bytes(value)
    monkeypatch.setattr(live, "_load_owner_pin", lambda: _owner_pin(manifest))

    with pytest.raises(
        route.RouteV2Error, match="execution identity differs from manifest"
    ):
        live.verify_live_pair_preflight(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
        )

    assert not (tmp_path / "pair-public").exists()


def test_zero_session_preflight_rejects_current_interpreter_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    monkeypatch.setattr(live, "_load_owner_pin", lambda: _owner_pin(manifest))
    monkeypatch.setattr(codex, "_ab_command_contract_sha256", lambda: "0" * 64)

    with pytest.raises(
        route.RouteV2Error, match="interpreter differs from signed manifest"
    ):
        live.verify_live_pair_preflight(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
        )

    assert not (tmp_path / "pair-public").exists()


def test_live_pair_rejects_current_interpreter_drift_before_auth_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    auth = tmp_path / "missing-auth.json"
    monkeypatch.setattr(codex, "_ab_command_contract_sha256", lambda: "0" * 64)

    with pytest.raises(
        route.RouteV2Error, match="interpreter differs from signed manifest"
    ):
        live._orchestrate_pinned_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            owner_pin=_owner_pin(manifest),
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=auth,
        )

    assert not auth.exists()
    assert not (tmp_path / "pair-public").exists()


def test_zero_session_preflight_rejects_executable_snapshot_drift_without_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    executables["A"].write_bytes(b"mutated executable")
    monkeypatch.setattr(live, "_load_owner_pin", lambda: _owner_pin(manifest))

    with pytest.raises(route.RouteV2Error, match="executable snapshot differs"):
        live.verify_live_pair_preflight(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
        )

    assert not (tmp_path / "pair-public").exists()


def test_zero_session_preflight_rejects_staged_input_drift_without_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    staged["B"]["task.md"] = b"mutated task\n"
    monkeypatch.setattr(live, "_load_owner_pin", lambda: _owner_pin(manifest))

    with pytest.raises(route.RouteV2Error, match="staged input differs from manifest"):
        live.verify_live_pair_preflight(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
        )

    assert not (tmp_path / "pair-public").exists()


def test_completed_nonzero_first_arm_still_runs_exactly_two_without_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    calls = 0

    def fake_run(
        command: list[str],
        *,
        input_bytes: bytes,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> codex._ContainedResult:
        nonlocal calls
        calls += 1
        (cwd / "result.txt").write_bytes(b"CALIBRATION_OK\n")
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_bytes(b'{"status":"ok"}')
        return _contained(
            stdout=b'{"type":"turn.completed"}\n',
            returncode=7 if calls == 1 else 0,
        )

    monkeypatch.setattr(codex, "_run_contained", fake_run)
    result = live._orchestrate_pinned_pair(
        tmp_path / "pair-public",
        contract_manifest=manifest,
        owner_pin=_owner_pin(manifest),
        executable_snapshots=executables,
        measured_preflights=preflights,
        staged_files=staged,
        auth_file=_auth(tmp_path),
    )
    assert calls == 2
    assert result.decision == "NON_SUCCESS"


def test_output_collision_fails_before_auth_read(tmp_path: Path) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    output = tmp_path / "pair-public"
    output.mkdir()
    auth = tmp_path / "missing-auth.json"
    with pytest.raises(route.RouteV2Error, match="output collision"):
        live._orchestrate_pinned_pair(
            output,
            contract_manifest=manifest,
            owner_pin=_owner_pin(manifest),
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=auth,
        )
    assert not auth.exists()


def test_coherent_manifest_rewrite_is_rejected_by_owner_pin(tmp_path: Path) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    value = json.loads(manifest)
    value["model_build_identity"]["model_id"] = "attacker-selected-model"
    rewritten = route._json_bytes(value)
    auth = tmp_path / "missing-auth.json"
    with pytest.raises(route.RouteV2Error, match="contract manifest is invalid"):
        live._orchestrate_pinned_pair(
            tmp_path / "pair-public",
            contract_manifest=rewritten,
            owner_pin=_owner_pin(manifest),
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=auth,
        )
    assert not auth.exists()


def test_public_orchestrator_rejects_caller_supplied_forged_matching_pin(
    tmp_path: Path,
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    value = json.loads(manifest)
    value["model_build_identity"]["model_id"] = "attacker-selected-model"
    rewritten = route._json_bytes(value)
    forged_pin = _owner_pin(rewritten)
    with pytest.raises(TypeError, match="owner_pin"):
        live.orchestrate_live_pair(
            tmp_path / "pair-public",
            contract_manifest=rewritten,
            owner_pin=forged_pin,  # type: ignore[call-arg]
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=tmp_path / "missing-auth.json",
        )


def test_coherent_codex_class_replacement_is_rejected_by_registered_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    original = codex.CodexABArmRunner

    class Replacement(original):
        pass

    monkeypatch.setattr(codex, "CodexABArmRunner", Replacement)
    with pytest.raises(route.RouteV2Error, match="runner provenance"):
        live._orchestrate_pinned_pair(
            tmp_path / "pair-public",
            contract_manifest=manifest,
            owner_pin=_owner_pin(manifest),
            executable_snapshots=executables,
            measured_preflights=preflights,
            staged_files=staged,
            auth_file=_auth(tmp_path),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_staged_input_junction_is_rejected_before_traversal(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "secret.txt").write_text("must not be read", encoding="utf-8")
    junction = tmp_path / "junction"
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("junction creation is unavailable")
    try:
        with pytest.raises(route.RouteV2Error, match="reparse point"):
            live._load_staged(junction)
    finally:
        os.rmdir(junction)
    assert (target / "secret.txt").read_text(encoding="utf-8") == "must not be read"


def test_direct_file_subprocess_does_not_reimport_replaceable_main(
    tmp_path: Path,
) -> None:
    sentinel = "CANONICAL_LIVE_AB_MAIN_SELECTED"
    (tmp_path / "sitecustomize.py").write_text(
        "import gate3_route_v2_ab_live as canonical\n"
        "def fake_main(*args, **kwargs):\n"
        f"    print({sentinel!r})\n"
        "    return 29\n"
        "canonical.main = fake_main\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(HERE)))
    completed = subprocess.run(
        [sys.executable, str(Path(live.__file__).resolve())],
        cwd=HERE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 29
    assert sentinel not in completed.stdout
    assert "required" in completed.stderr


def test_wrong_authorization_subprocess_never_reads_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(live.__file__).resolve()),
            "--authorization",
            "wrong",
            "--manifest",
            str(missing),
            "--output-root",
            str(tmp_path / "out"),
            "--auth-file",
            str(missing),
            "--arm-a-executable",
            str(missing),
            "--arm-a-preflight",
            str(missing),
            "--arm-a-staged",
            str(missing),
            "--arm-b-executable",
            str(missing),
            "--arm-b-preflight",
            str(missing),
            "--arm-b-staged",
            str(missing),
        ],
        cwd=HERE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "live A/B authorization is invalid" in completed.stderr
    assert not missing.exists()


def test_zero_session_preflight_subprocess_rejects_credentials_before_inputs(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(live.__file__).resolve()),
            "--preflight-only",
            "--authorization",
            live.PREFLIGHT_AUTHORIZATION,
            "--manifest",
            str(missing),
            "--output-root",
            str(tmp_path / "out"),
            "--auth-file",
            str(missing),
            "--arm-a-executable",
            str(missing),
            "--arm-a-preflight",
            str(missing),
            "--arm-a-staged",
            str(missing),
            "--arm-b-executable",
            str(missing),
            "--arm-b-preflight",
            str(missing),
            "--arm-b-staged",
            str(missing),
        ],
        cwd=HERE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "zero-session preflight must not receive credentials" in completed.stderr
    assert not missing.exists()


def test_zero_session_preflight_subprocess_dispatches_successfully(
    tmp_path: Path,
) -> None:
    manifest, preflights, executables, staged = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(manifest)
    preflight_paths: dict[str, Path] = {}
    staged_roots: dict[str, Path] = {}
    for arm_id in ("A", "B"):
        preflight_path = tmp_path / f"preflight-{arm_id}.json"
        preflight_path.write_bytes(preflights[arm_id])
        preflight_paths[arm_id] = preflight_path
        staged_root = tmp_path / f"staged-{arm_id}"
        for relative, payload in staged[arm_id].items():
            target = staged_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        staged_roots[arm_id] = staged_root

    driver = (
        "import sys\n"
        "import gate3_route_v2 as route\n"
        "import gate3_route_v2_ab_live as live\n"
        f"manifest_sha256 = {route._sha256_bytes(manifest)!r}\n"
        "pin = route._json_bytes({"
        "'manifest_sha256': manifest_sha256, "
        "'schema': live.OWNER_PIN_SCHEMA, "
        "'status': 'SIGNED_AND_PROMOTED'})\n"
        "live._load_owner_pin = lambda: live._owner_pin_from_bytes(pin)\n"
        "raise SystemExit(live.main(sys.argv[1:]))\n"
    )
    output_root = tmp_path / "pair-public"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            driver,
            "--preflight-only",
            "--authorization",
            live.PREFLIGHT_AUTHORIZATION,
            "--manifest",
            str(manifest_path),
            "--output-root",
            str(output_root),
            "--arm-a-executable",
            str(executables["A"]),
            "--arm-a-preflight",
            str(preflight_paths["A"]),
            "--arm-a-staged",
            str(staged_roots["A"]),
            "--arm-b-executable",
            str(executables["B"]),
            "--arm-b-preflight",
            str(preflight_paths["B"]),
            "--arm-b-staged",
            str(staged_roots["B"]),
        ],
        cwd=HERE,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    route._validate_public_payload(completed.stdout)
    assert completed.stdout.endswith(b"\n")
    assert not completed.stdout.endswith(b"\r\n")
    receipt = json.loads(completed.stdout)
    assert receipt["schema"] == live.PREFLIGHT_RECEIPT_SCHEMA
    assert receipt["authorization"] == live.PREFLIGHT_AUTHORIZATION
    assert receipt["checks"]["manifest_identity"] == "PASS"
    assert not output_root.exists()

    with pytest.raises(route.PublicPrivacyError, match="canonical JSON"):
        route._validate_public_payload(completed.stdout.replace(b"\n", b"\r\n"))
