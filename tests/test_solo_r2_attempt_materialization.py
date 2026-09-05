from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tarfile
from unittest import mock

import pytest

from governance_tools import solo_r2_attempt_materialization as subject


PACKET = Path("artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md")


def _acl(generation: str = "generation-1"):
    def probe(path: Path) -> subject.LeafAclObservation:
        return subject.LeafAclObservation(
            leaf=path,
            sandbox_principal="CodexSandboxOffline",
            sandbox_account_generation=generation,
            sandbox_writable=True,
            credentials_denied=True,
        )

    return probe


def _archive() -> bytes:
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        payload = b"frozen-base\n"
        info = tarfile.TarInfo("source.txt")
        info.size = len(payload)
        archive.addfile(info, BytesIO(payload))
    return output.getvalue()


def _binding(root: Path) -> subject.RepositoryBinding:
    return subject.RepositoryBinding(root, root, root)


def test_packet_identity_is_frozen_and_not_a_snapshot_file() -> None:
    packet = subject.TreatmentInstruction.load(PACKET)
    assert packet.sha256 == subject.TREATMENT_PACKET_SHA256
    assert packet.git_blob == subject.TREATMENT_PACKET_GIT_BLOB
    assert len(packet.payload) == 1_373


def test_pinned_executable_rejects_byte_drift(tmp_path: Path) -> None:
    executable = tmp_path / "runner.bin"
    executable.write_bytes(b"first")
    binding = subject.PinnedExecutable.capture(executable.resolve())
    executable.write_bytes(b"second")
    with pytest.raises(subject.MaterializationError) as caught:
        binding.verify()
    assert caught.value.code == subject.MATERIALIZATION_FAILURE


def test_leaf_manager_enforces_one_active_and_create_once(tmp_path: Path) -> None:
    manager = subject.LeafWorkspaceManager((tmp_path / "leaves").resolve(), acl_probe=_acl())
    first = manager.create("pair-1")
    with pytest.raises(subject.MaterializationError):
        manager.create("pair-2")
    manager.release(first)
    with pytest.raises(subject.MaterializationError):
        manager.create("pair-1")


def _generation(value: str = "generation-1") -> SimpleNamespace:
    generation = SimpleNamespace(
        offline_sid="S-1-5-21-1-2-3-1003",
        value=value,
    )
    generation.validate = lambda: None
    return generation


def _acl_projection(
    launcher_sid: str,
    offline_sid: str,
    *,
    protected: bool = True,
) -> bytes:
    return json.dumps(
        {
            "protected": protected,
            "sandbox_group_sid": "S-1-5-21-1-2-3-1005",
            "offline_member": True,
            "rules": [
                {
                    "sid": "S-1-5-18",
                    "rights": 2_032_127,
                    "access_type": 0,
                    "inheritance": 3,
                    "propagation": 0,
                    "inherited": False,
                },
                {
                    "sid": "S-1-5-32-544",
                    "rights": 2_032_127,
                    "access_type": 0,
                    "inheritance": 3,
                    "propagation": 0,
                    "inherited": False,
                },
                {
                    "sid": launcher_sid,
                    "rights": 2_032_127,
                    "access_type": 0,
                    "inheritance": 3,
                    "propagation": 0,
                    "inherited": False,
                },
                {
                    "sid": "S-1-5-21-1-2-3-1005",
                    "rights": 1_245_631,
                    "access_type": 0,
                    "inheritance": 3,
                    "propagation": 0,
                    "inherited": False,
                },
            ],
        },
        separators=(",", ":"),
    ).encode("ascii")


def test_windows_leaf_acl_probe_prepares_and_reads_exact_safe_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leaf = (tmp_path / "leaf").resolve()
    temp = (tmp_path / "temp").resolve()
    leaf.mkdir()
    temp.mkdir()
    launcher_sid = "S-1-5-21-1-2-3-1001"
    generation = _generation()
    calls: list[tuple[object, ...]] = []

    def run(command, **kwargs):
        calls.append(tuple(command))
        assert kwargs["shell"] is False
        assert kwargs["cwd"] == leaf
        assert "PATH" not in kwargs["env"]
        return SimpleNamespace(
            returncode=0,
            stdout=_acl_projection(launcher_sid, generation.offline_sid),
            stderr=b"",
        )

    monkeypatch.setattr(subject.subprocess, "run", run)
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        launcher_sid=launcher_sid,
        generation_probe=lambda: generation,
        credentials_denied=lambda observed: observed is generation,
        temp_root=temp,
    )
    observation = probe(leaf)
    observation.validate(leaf)
    assert observation.sandbox_principal == generation.offline_sid
    assert observation.sandbox_account_generation == generation.value
    assert len(calls) == 1
    assert calls[0][1:5] == (
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
    )
    script = base64.b64decode(calls[0][5]).decode("utf-16-le")
    assert "CodexSandboxUsers" in script
    assert generation.offline_sid in script


@pytest.mark.parametrize("returncode,stderr", [(0, b"real failure"), (1, b"")])
def test_windows_leaf_acl_probe_preserves_process_failure_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: bytes
) -> None:
    leaf = tmp_path / "leaf"
    leaf.mkdir()
    generation = _generation()
    launcher_sid = "S-1-5-21-1-2-3-1001"
    monkeypatch.setattr(subject.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=returncode,
        stdout=_acl_projection(launcher_sid, generation.offline_sid),
        stderr=stderr,
    ))
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        launcher_sid=launcher_sid, generation_probe=lambda: generation,
        credentials_denied=lambda _: pytest.fail("Failure must stop before credential check"),
        temp_root=tmp_path,
    )
    with pytest.raises(subject.MaterializationError) as caught:
        probe(leaf)
    assert caught.value.code == subject.MATERIALIZATION_FAILURE


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell 5.1")
def test_windows_leaf_probe_prefix_suppresses_real_progress_only(tmp_path: Path) -> None:
    powershell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(powershell),
        launcher_sid="S-1-5-21-1-2-3-1001", generation_probe=_generation,
        credentials_denied=lambda _: True, temp_root=tmp_path,
    )
    command = probe._command(tmp_path / "not-created", _generation().offline_sid)
    script = base64.b64decode(command[-1]).decode("utf-16-le")
    prefix = script.split("$path=", 1)[0]
    assert prefix == "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
    environment = {"TEMP": str(tmp_path), "TMP": str(tmp_path)}
    for key in ("COMSPEC", "SYSTEMROOT", "WINDIR"):
        if os.environ.get(key):
            environment[key] = os.environ[key]
    body = (
        "if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) { throw '5.1 required' };"
        "Write-Progress -Activity 'fixture progress' -Status 'running' -PercentComplete 50;"
        "[Console]::Out.Write('{\"probe\":\"ok\"}');"
    )
    for emit_error in (False, True):
        payload = prefix + body + ("[Console]::Error.Write('real failure');" if emit_error else "")
        result = subject.subprocess.run(
            [*command[:-1], base64.b64encode(payload.encode("utf-16-le")).decode("ascii")],
            cwd=tmp_path, env=environment, stdin=subject.subprocess.DEVNULL,
            capture_output=True, timeout=30, check=False, shell=False,
        )
        assert result.returncode == 0
        assert result.stdout == b'{"probe":"ok"}'
        assert result.stderr == (b"real failure" if emit_error else b"")


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell 5.1 and Codex sandbox accounts")
def test_windows_leaf_acl_real_filesystem_roundtrip(tmp_path: Path) -> None:
    leaf = tmp_path / "acl-roundtrip"
    leaf.mkdir()
    powershell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    quoted_leaf = "'" + str(leaf).replace("'", "''") + "'"

    def run_script(script: str) -> bytes:
        result = subject.subprocess.run(
            [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand",
             base64.b64encode(script.encode("utf-16-le")).decode("ascii")],
            capture_output=True, timeout=30, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stderr == b""
        return result.stdout

    setup = run_script(
        "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
        "if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) { throw '5.1 required' };"
        "$offline=$null;try {$offline=([Security.Principal.NTAccount]::new('CodexSandboxOffline')).Translate([Security.Principal.SecurityIdentifier]).Value} catch [Security.Principal.IdentityNotMappedException] {};"
        "$sections=[Security.AccessControl.AccessControlSections]::Access;"
        f"$original=[IO.Directory]::GetAccessControl({quoted_leaf});"
        "[ordered]@{offline=$offline;owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "sddl=$original.GetSecurityDescriptorSddlForm($sections);protected=$original.AreAccessRulesProtected}|ConvertTo-Json -Compress"
    )
    identity = json.loads(setup)
    if identity["offline"] is None:
        pytest.skip("CodexSandboxOffline account not installed; no ACL mutation performed")
    generation = _generation()
    generation.offline_sid = identity["offline"]
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(powershell),
        launcher_sid=identity["owner"], generation_probe=lambda: generation,
        credentials_denied=lambda _: True, temp_root=tmp_path,
    )
    try:
        # Runs the unmodified production command and filesystem readback verifier.
        observation = probe(leaf)
        observation.validate(leaf)
        observed = json.loads(run_script(
            "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
            f"$acl=[IO.Directory]::GetAccessControl({quoted_leaf});"
            "$rows=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|ForEach-Object{"
            "[ordered]@{rights=[int]$_.FileSystemRights;allow=[int]$_.AccessControlType;inheritance=[int]$_.InheritanceFlags;propagation=[int]$_.PropagationFlags;inherited=$_.IsInherited}});"
            "[ordered]@{protected=$acl.AreAccessRulesProtected;rows=$rows}|ConvertTo-Json -Depth 4 -Compress"
        ))
        assert observed["protected"] is True
        assert sorted(row["rights"] for row in observed["rows"]) == [1_245_631, 2_032_127, 2_032_127, 2_032_127]
        assert all((row["allow"], row["inheritance"], row["propagation"], row["inherited"]) == (0, 3, 0, False) for row in observed["rows"])
    finally:
        sddl = identity["sddl"].replace("'", "''")
        restored = json.loads(run_script(
            "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
            "$sections=[Security.AccessControl.AccessControlSections]::Access;"
            "$acl=[Security.AccessControl.DirectorySecurity]::new();"
            f"$acl.SetSecurityDescriptorSddlForm('{sddl}',$sections);"
            f"[IO.Directory]::SetAccessControl({quoted_leaf},$acl);"
            f"$actual=[IO.Directory]::GetAccessControl({quoted_leaf});"
            "[ordered]@{sddl=$actual.GetSecurityDescriptorSddlForm($sections);protected=$actual.AreAccessRulesProtected}|ConvertTo-Json -Compress"
        ))
        # Ignore only Windows' auto-inherited bookkeeping flag; compare all ACEs.
        assert restored["sddl"][restored["sddl"].index("("):] == identity["sddl"][identity["sddl"].index("("):]
        assert restored["protected"] == identity["protected"]


def test_windows_leaf_manager_factory_uses_concrete_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temp = (tmp_path / "temp").resolve()
    temp.mkdir()
    launcher_sid = "S-1-5-21-1-2-3-1001"
    generation = _generation()
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=_acl_projection(launcher_sid, generation.offline_sid),
            stderr=b"",
        ),
    )
    manager = subject.LeafWorkspaceManager.for_windows_runtime(
        (tmp_path / "leaves").resolve(),
        powershell=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        launcher_sid=launcher_sid,
        generation_probe=lambda: generation,
        credentials_denied=lambda observed: observed is generation,
        temp_root=temp,
    )
    leaf = manager.create("pair-1")
    assert isinstance(manager._acl_probe, subject.WindowsLeafAclProbe)
    leaf.acl.validate(leaf.path)
    manager.release(leaf)


@pytest.mark.parametrize(
    "failure",
    ("unprotected", "extra_ace", "offline_not_member", "credential_visible",
     "missing_synchronize", "extra_right", "inheritance", "propagation",
     "deny_type", "inherited", "full_control_changed"),
)
def test_windows_leaf_acl_probe_fails_closed_on_untrusted_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    leaf = (tmp_path / "leaf").resolve()
    temp = (tmp_path / "temp").resolve()
    leaf.mkdir()
    temp.mkdir()
    launcher_sid = "S-1-5-21-1-2-3-1001"
    generation = _generation()
    projection = json.loads(_acl_projection(launcher_sid, generation.offline_sid))
    if failure == "unprotected":
        projection["protected"] = False
    elif failure == "extra_ace":
        projection["rules"].append(dict(projection["rules"][0]))
    elif failure == "offline_not_member":
        projection["offline_member"] = False
    elif failure == "missing_synchronize":
        projection["rules"][3]["rights"] = 197_055
    elif failure == "extra_right":
        projection["rules"][3]["rights"] |= 262_144  # ChangePermissions
    elif failure == "inheritance":
        projection["rules"][3]["inheritance"] = 1
    elif failure == "propagation":
        projection["rules"][3]["propagation"] = 1
    elif failure == "deny_type":
        projection["rules"][3]["access_type"] = 1
    elif failure == "inherited":
        projection["rules"][3]["inherited"] = True
    elif failure == "full_control_changed":
        projection["rules"][0]["rights"] = 1_245_631

    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(projection, separators=(",", ":")).encode("ascii"),
            stderr=b"",
        ),
    )
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        launcher_sid=launcher_sid,
        generation_probe=lambda: generation,
        credentials_denied=lambda observed: failure != "credential_visible",
        temp_root=temp,
    )
    with pytest.raises(subject.MaterializationError):
        probe(leaf)


def test_windows_leaf_acl_probe_rejects_generation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leaf = (tmp_path / "leaf").resolve()
    temp = (tmp_path / "temp").resolve()
    leaf.mkdir()
    temp.mkdir()
    launcher_sid = "S-1-5-21-1-2-3-1001"
    before = _generation("generation-1")
    after = _generation("generation-2")
    generations = iter((before, after))
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=_acl_projection(launcher_sid, before.offline_sid),
            stderr=b"",
        ),
    )
    probe = subject.WindowsLeafAclProbe(
        powershell=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        launcher_sid=launcher_sid,
        generation_probe=lambda: next(generations),
        credentials_denied=lambda observed: True,
        temp_root=temp,
    )
    with pytest.raises(subject.MaterializationError) as caught:
        probe(leaf)
    assert caught.value.code == subject.PAIR_INVALID


def test_host_local_tri_state_requires_resolved_zero_listener_and_zero_inputs() -> None:
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation(
            subject.HostLocalEndpointDisposition.REACHABLE, 1
        ).validate()
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation(
            subject.HostLocalEndpointDisposition.BLOCKED,
            0,
            ("http://127.0.0.1:9000",),
        ).validate()
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation(
            subject.HostLocalEndpointDisposition.UNRESOLVED, 0
        ).validate()
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation("REACHABLE", 0).validate()  # type: ignore[arg-type]
    subject.HostLocalIsolation(
        subject.HostLocalEndpointDisposition.REACHABLE, 0
    ).validate()
    subject.HostLocalIsolation(
        subject.HostLocalEndpointDisposition.BLOCKED, 0
    ).validate()


def test_git_environment_drops_path_and_rejects_authority_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "attacker"))
    env = subject._closed_git_environment(tmp_path.resolve())
    assert "PATH" not in env
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "other.git"))
    env = subject._closed_git_environment(tmp_path.resolve())
    assert "GIT_DIR" not in env


def test_real_git_outer_entrypoint_ignores_path_and_git_dir_poison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git_path = Path(
        r"C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime"
        r"\dependencies\native\git\mingw64\bin\git.exe"
    )
    if not git_path.is_file():
        pytest.skip("bundled exact Git executable is unavailable")
    repository_root = Path(__file__).resolve().parents[1]
    git_dir = (repository_root / ".git").resolve(strict=True)
    binding = subject.RepositoryBinding(repository_root, git_dir, git_dir)
    attacker = tmp_path / "attacker"
    attacker.mkdir()
    (attacker / "git.cmd").write_text("exit /b 99\n", encoding="ascii")
    monkeypatch.setenv("PATH", str(attacker))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong.git"))
    subject.verify_repository_binding(
        subject.PinnedExecutable.capture(git_path),
        binding,
        temp_root=tmp_path.resolve(),
    )


def test_pair_materialization_is_byte_identical_and_sequential(tmp_path: Path) -> None:
    generations: list[str] = []

    def probe(path: Path) -> subject.LeafAclObservation:
        generations.append(path.name)
        return _acl()(path)

    root = (tmp_path / "repo").resolve()
    root.mkdir()
    manager = subject.LeafWorkspaceManager((tmp_path / "leaves").resolve(), acl_probe=probe)
    materializer = subject.FrozenGitMaterializer(
        git=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        repository=_binding(root),
        leaves=manager,
        packet=subject.TreatmentInstruction.load(PACKET),
        forbidden_snapshot_paths=("hidden-oracle.txt",),
    )
    host_local = subject.HostLocalIsolation(
        subject.HostLocalEndpointDisposition.REACHABLE, 0
    )

    def fake_git(executable, binding, args, *, temp_root):
        if args[:2] == ("rev-parse", "--verify"):
            return (subject.FROZEN_BASE_COMMIT + "\n").encode("ascii")
        if args[:2] == ("archive", "--format=tar"):
            return _archive()
        raise AssertionError(args)

    with mock.patch.object(subject, "verify_repository_binding"), mock.patch.object(
        subject, "_run_git", side_effect=fake_git
    ):
        evidence = materializer.qualify_pair("pair-id", host_local)

    assert evidence.control.inventory == evidence.treatment.inventory
    assert evidence.control.treatment_instruction_sha256 is None
    assert evidence.treatment.treatment_instruction_sha256 == subject.TREATMENT_PACKET_SHA256
    assert generations == ["pair-id-1", "pair-id-2"]
    assert manager.active is None
    assert not any((tmp_path / "leaves").iterdir())


def test_pair_materialization_rejects_sandbox_account_generation_drift(
    tmp_path: Path,
) -> None:
    call = 0

    def probe(path: Path) -> subject.LeafAclObservation:
        nonlocal call
        call += 1
        return _acl(f"generation-{call}")(path)

    root = (tmp_path / "repo").resolve()
    root.mkdir()
    materializer = subject.FrozenGitMaterializer(
        git=subject.PinnedExecutable.capture(Path(sys.executable).resolve()),
        repository=_binding(root),
        leaves=subject.LeafWorkspaceManager((tmp_path / "leaves").resolve(), acl_probe=probe),
        packet=subject.TreatmentInstruction.load(PACKET),
    )
    host_local = subject.HostLocalIsolation(
        subject.HostLocalEndpointDisposition.REACHABLE, 0
    )

    def fake_git(executable, binding, args, *, temp_root):
        return (
            (subject.FROZEN_BASE_COMMIT + "\n").encode("ascii")
            if args[:2] == ("rev-parse", "--verify")
            else _archive()
        )

    with mock.patch.object(subject, "verify_repository_binding"), mock.patch.object(
        subject, "_run_git", side_effect=fake_git
    ), pytest.raises(subject.MaterializationError) as caught:
        materializer.qualify_pair("pair-id", host_local)
    assert caught.value.code == subject.PAIR_INVALID


def test_archive_rejects_symlink(tmp_path: Path) -> None:
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        info = tarfile.TarInfo("escape")
        info.type = tarfile.SYMTYPE
        info.linkname = "../outside"
        archive.addfile(info)
    with pytest.raises(subject.MaterializationError):
        subject._safe_extract_archive(output.getvalue(), tmp_path)
