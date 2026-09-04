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
                    "rights": 197_055,
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
    ("unprotected", "extra_ace", "offline_not_member", "credential_visible"),
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


def test_host_local_reachability_requires_zero_listener_and_zero_inputs() -> None:
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation(True, 1).validate()
    with pytest.raises(subject.MaterializationError):
        subject.HostLocalIsolation(True, 0, ("http://127.0.0.1:9000",)).validate()
    subject.HostLocalIsolation(True, 0).validate()


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
        host_local=subject.HostLocalIsolation(True, 0),
        forbidden_snapshot_paths=("hidden-oracle.txt",),
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
        evidence = materializer.qualify_pair("pair-id")

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
        host_local=subject.HostLocalIsolation(True, 0),
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
        materializer.qualify_pair("pair-id")
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
