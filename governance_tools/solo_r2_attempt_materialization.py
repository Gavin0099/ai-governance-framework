"""Fail-closed, pre-Attempt materialization for Solo Evaluation R2.

The module creates disposable leaf snapshots from one pinned Git commit.  It
does not generate an Attempt handle, expose a task, or touch the public ledger.
Treatment bytes are returned as an instruction attachment and are never
written into the consumer snapshot.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
from typing import Any, Callable, Iterable, Mapping, Sequence


MATERIALIZATION_FAILURE = "PRE_ATTEMPT_INFRA_FAILURE / STOP"
PAIR_INVALID = "PAIR_INVALID / STOP"
FROZEN_BASE_COMMIT = "e478409971dd8e72335966350fcfaee2a6cdb8b0"
FROZEN_FIX_COMMIT = "c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b"
TREATMENT_PACKET_SHA256 = (
    "f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14"
)
TREATMENT_PACKET_GIT_BLOB = "a37320e37f587fc45f9fd5797d91bb9f2762ac71"
HIDDEN_ORACLE_GIT_BLOB = "93ad7d9d56b1534bd180af83ba69ad23e64f3c6b"
TREATMENT_PACKET_BYTES = 1_373
TREATMENT_PACKET_LF = 24


class MaterializationError(RuntimeError):
    """A frozen, non-sensitive pre-Attempt failure."""

    def __init__(self, code: str = MATERIALIZATION_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = MATERIALIZATION_FAILURE) -> None:
    raise MaterializationError(code)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_blob_sha1(value: bytes) -> str:
    return hashlib.sha1(f"blob {len(value)}\0".encode("ascii") + value).hexdigest()


def _is_reparse(value: os.stat_result) -> bool:
    return bool(getattr(value, "st_file_attributes", 0) & 0x400)


def _regular_unlinked_path(path: Path) -> os.stat_result:
    try:
        value = os.lstat(path)
    except OSError:
        _fail()
    if not stat.S_ISREG(value.st_mode) or _is_reparse(value):
        _fail()
    return value


@dataclass(frozen=True)
class PinnedExecutable:
    """Absolute executable identity verified again immediately before use."""

    path: Path
    byte_length: int
    sha256: str

    @classmethod
    def capture(cls, path: Path | str) -> "PinnedExecutable":
        candidate = Path(path)
        if not candidate.is_absolute():
            _fail()
        value = _regular_unlinked_path(candidate)
        try:
            payload = candidate.read_bytes()
            resolved = candidate.resolve(strict=True)
        except OSError:
            _fail()
        if os.path.normcase(str(resolved)) != os.path.normcase(str(candidate.absolute())):
            _fail()
        return cls(resolved, value.st_size, _sha256_bytes(payload))

    def verify(self) -> Path:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            _fail()
        value = _regular_unlinked_path(self.path)
        try:
            resolved = self.path.resolve(strict=True)
            payload = self.path.read_bytes()
        except OSError:
            _fail()
        if (
            os.path.normcase(str(resolved)) != os.path.normcase(str(self.path))
            or type(self.byte_length) is not int
            or value.st_size != self.byte_length
            or not isinstance(self.sha256, str)
            or _sha256_bytes(payload) != self.sha256
        ):
            _fail()
        return resolved


@dataclass(frozen=True)
class RepositoryBinding:
    root: Path
    git_dir: Path
    common_dir: Path

    def __post_init__(self) -> None:
        for value in (self.root, self.git_dir, self.common_dir):
            if not isinstance(value, Path) or not value.is_absolute():
                _fail()
            try:
                resolved = value.resolve(strict=True)
                path_stat = os.lstat(resolved)
            except OSError:
                _fail()
            if (
                os.path.normcase(str(resolved)) != os.path.normcase(str(value))
                or not stat.S_ISDIR(path_stat.st_mode)
                or _is_reparse(path_stat)
            ):
                _fail()


class HostLocalEndpointDisposition(str, Enum):
    """Behavioral result of the qualification-only same-host TCP probe."""

    REACHABLE = "REACHABLE"
    BLOCKED = "BLOCKED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class HostLocalIsolation:
    """Observed same-host TCP behavior with every runtime endpoint removed."""

    host_local_endpoint_reachable: HostLocalEndpointDisposition
    observed_host_listener_count: int
    runtime_endpoint_inputs: tuple[str, ...] = ()

    def validate(self) -> None:
        if (
            not isinstance(
                self.host_local_endpoint_reachable, HostLocalEndpointDisposition
            )
            or self.host_local_endpoint_reachable
            is HostLocalEndpointDisposition.UNRESOLVED
            or type(self.observed_host_listener_count) is not int
            or self.observed_host_listener_count != 0
            or not isinstance(self.runtime_endpoint_inputs, tuple)
            or self.runtime_endpoint_inputs
        ):
            _fail()


@dataclass(frozen=True)
class LeafAclObservation:
    leaf: Path
    sandbox_principal: str
    sandbox_account_generation: str
    sandbox_writable: bool
    credentials_denied: bool

    def validate(self, expected_leaf: Path) -> None:
        if (
            not isinstance(self.leaf, Path)
            or self.leaf.resolve() != expected_leaf.resolve()
            or not isinstance(self.sandbox_principal, str)
            or not self.sandbox_principal
            or not isinstance(self.sandbox_account_generation, str)
            or not self.sandbox_account_generation
            or self.sandbox_writable is not True
            or self.credentials_denied is not True
        ):
            _fail()


AclProbe = Callable[[Path], LeafAclObservation]


_WINDOWS_SID = re.compile(r"S-1-(?:\d+-)+\d+\Z")
_WINDOWS_FULL_CONTROL = 2_032_127
# .NET FileSystemAccessRule adds Synchronize to a Modify Allow ACE.
_WINDOWS_MODIFY_ALLOW = 197_055 | 1_048_576


class WindowsLeafAclProbe:
    """Prepare and read back one canonical, run-owned Windows leaf DACL.

    This is deliberately narrower than token simulation.  Only the protected,
    non-inherited four-ACE shape created here is admissible.  Credential denial
    must be supplied by the child-side boundary producer for the same sandbox
    generation; it is never inferred from the leaf DACL.
    """

    def __init__(
        self,
        *,
        powershell: PinnedExecutable,
        launcher_sid: str,
        generation_probe: Callable[[], Any],
        credentials_denied: Callable[[Any], bool],
        temp_root: Path | str,
    ) -> None:
        self.powershell = powershell
        self.launcher_sid = launcher_sid
        self.generation_probe = generation_probe
        self.credentials_denied = credentials_denied
        self.temp_root = Path(temp_root)
        if (
            _WINDOWS_SID.fullmatch(launcher_sid) is None
            or not callable(generation_probe)
            or not callable(credentials_denied)
            or not self.temp_root.is_absolute()
        ):
            _fail(PAIR_INVALID)
        try:
            temp_stat = os.lstat(self.temp_root)
            resolved_temp = self.temp_root.resolve(strict=True)
        except OSError:
            _fail()
        if (
            resolved_temp != self.temp_root.resolve()
            or not stat.S_ISDIR(temp_stat.st_mode)
            or _is_reparse(temp_stat)
        ):
            _fail(PAIR_INVALID)
        self.temp_root = resolved_temp
        self.powershell.verify()

    @staticmethod
    def _quote(value: str) -> str:
        if not value or any(character in value for character in "'\r\n"):
            _fail(PAIR_INVALID)
        return f"'{value}'"

    def _command(self, leaf: Path, offline_sid: str) -> tuple[str, ...]:
        if _WINDOWS_SID.fullmatch(offline_sid) is None:
            _fail(PAIR_INVALID)
        fixed_rules = (
            ("S-1-5-18", "FullControl"),
            ("S-1-5-32-544", "FullControl"),
            (self.launcher_sid, "FullControl"),
        )
        additions = "".join(
            "$sid=New-Object System.Security.Principal.SecurityIdentifier("
            f"{self._quote(sid)});"
            "$rule=New-Object System.Security.AccessControl.FileSystemAccessRule("
            "$sid,"
            f"[System.Security.AccessControl.FileSystemRights]::{right},"
            "([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor "
            "[System.Security.AccessControl.InheritanceFlags]::ObjectInherit),"
            "[System.Security.AccessControl.PropagationFlags]::None,"
            "[System.Security.AccessControl.AccessControlType]::Allow);"
            "$acl.AddAccessRule($rule)|Out-Null;"
            for sid, right in fixed_rules
        )
        script = (
            "$ErrorActionPreference='Stop';"
            "$ProgressPreference='SilentlyContinue';"
            f"$path={self._quote(str(leaf))};"
            f"$offlineSidValue={self._quote(offline_sid)};"
            "$sandboxGroupName='CodexSandboxUsers';"
            "$sandboxGroupAccount=New-Object System.Security.Principal.NTAccount("
            "$sandboxGroupName);"
            "$sandboxGroupSid=$sandboxGroupAccount.Translate("
            "[System.Security.Principal.SecurityIdentifier]);"
            "Add-Type -AssemblyName System.DirectoryServices.AccountManagement;"
            "$principalContext=New-Object "
            "System.DirectoryServices.AccountManagement.PrincipalContext("
            "[System.DirectoryServices.AccountManagement.ContextType]::Machine);"
            "$groupPrincipal=[System.DirectoryServices.AccountManagement.GroupPrincipal]"
            "::FindByIdentity($principalContext,$sandboxGroupSid.Value);"
            "if($null -eq $groupPrincipal){throw 'sandbox group missing'};"
            "$memberSids=@($groupPrincipal.GetMembers($true)|ForEach-Object{"
            "if($null -ne $_.Sid){$_.Sid.Value}});"
            "$directory=New-Object System.IO.DirectoryInfo($path);"
            "$acl=New-Object System.Security.AccessControl.DirectorySecurity;"
            "$acl.SetAccessRuleProtection($true,$false);"
            + additions
            + "$groupRule=New-Object System.Security.AccessControl.FileSystemAccessRule("
            "$sandboxGroupSid,[System.Security.AccessControl.FileSystemRights]::Modify,"
            "([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor "
            "[System.Security.AccessControl.InheritanceFlags]::ObjectInherit),"
            "[System.Security.AccessControl.PropagationFlags]::None,"
            "[System.Security.AccessControl.AccessControlType]::Allow);"
            "$acl.AddAccessRule($groupRule)|Out-Null;"
            + "$directory.SetAccessControl($acl);"
            "$observed=$directory.GetAccessControl("
            "[System.Security.AccessControl.AccessControlSections]::Access);"
            "$rows=@($observed.GetAccessRules($true,$true,"
            "[System.Security.Principal.SecurityIdentifier])|ForEach-Object{"
            "[ordered]@{sid=$_.IdentityReference.Value;"
            "rights=[int]$_.FileSystemRights;access_type=[int]$_.AccessControlType;"
            "inheritance=[int]$_.InheritanceFlags;"
            "propagation=[int]$_.PropagationFlags;inherited=[bool]$_.IsInherited}});"
            "[ordered]@{protected=[bool]$observed.AreAccessRulesProtected;"
            "sandbox_group_sid=$sandboxGroupSid.Value;"
            "offline_member=[bool]($memberSids -contains $offlineSidValue);rules=$rows}"
            "|ConvertTo-Json -Compress -Depth 4"
        )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return (
            str(self.powershell.verify()),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        )

    def __call__(self, leaf: Path) -> LeafAclObservation:
        try:
            resolved_leaf = leaf.resolve(strict=True)
            value = os.lstat(resolved_leaf)
            generation = self.generation_probe()
            generation.validate()
            offline_sid = generation.offline_sid
            generation_value = generation.value
        except (AttributeError, OSError):
            _fail()
        if (
            resolved_leaf != leaf.resolve()
            or not stat.S_ISDIR(value.st_mode)
            or _is_reparse(value)
            or _WINDOWS_SID.fullmatch(offline_sid) is None
            or not isinstance(generation_value, str)
            or not generation_value
        ):
            _fail(PAIR_INVALID)
        environment = {"TEMP": str(self.temp_root), "TMP": str(self.temp_root)}
        for key in ("COMSPEC", "SYSTEMROOT", "WINDIR"):
            if os.environ.get(key):
                environment[key] = os.environ[key]
        try:
            completed = subprocess.run(
                self._command(resolved_leaf, offline_sid),
                cwd=resolved_leaf,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError):
            _fail()
        self.powershell.verify()
        if (
            completed.returncode != 0
            or completed.stderr
            or not completed.stdout
            or len(completed.stdout) > 65_536
        ):
            _fail()
        try:
            projection = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail(PAIR_INVALID)
        if not isinstance(projection, dict) or set(projection) != {
            "protected",
            "sandbox_group_sid",
            "offline_member",
            "rules",
        }:
            _fail(PAIR_INVALID)
        sandbox_group_sid = projection["sandbox_group_sid"]
        rows = projection["rules"]
        if (
            _WINDOWS_SID.fullmatch(sandbox_group_sid) is None
            or sandbox_group_sid in {self.launcher_sid, offline_sid}
            or projection["offline_member"] is not True
            or not isinstance(rows, list)
        ):
            _fail(PAIR_INVALID)
        expected = {
            ("S-1-5-18", _WINDOWS_FULL_CONTROL, 0, 3, 0, False),
            ("S-1-5-32-544", _WINDOWS_FULL_CONTROL, 0, 3, 0, False),
            (self.launcher_sid, _WINDOWS_FULL_CONTROL, 0, 3, 0, False),
            (sandbox_group_sid, _WINDOWS_MODIFY_ALLOW, 0, 3, 0, False),
        }
        observed: set[tuple[object, ...]] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "sid",
                "rights",
                "access_type",
                "inheritance",
                "propagation",
                "inherited",
            }:
                _fail(PAIR_INVALID)
            observed.add(tuple(row[key] for key in (
                "sid", "rights", "access_type", "inheritance", "propagation", "inherited"
            )))
        if (
            projection["protected"] is not True
            or len(rows) != len(expected)
            or observed != expected
        ):
            _fail(PAIR_INVALID)
        try:
            denied = self.credentials_denied(generation)
            generation_after = self.generation_probe()
        except Exception:
            _fail()
        if denied is not True or generation_after != generation:
            _fail(PAIR_INVALID)
        return LeafAclObservation(
            resolved_leaf,
            offline_sid,
            generation_value,
            True,
            True,
        )


@dataclass(frozen=True)
class TreatmentInstruction:
    payload: bytes
    sha256: str
    git_blob: str

    @classmethod
    def load(cls, path: Path | str) -> "TreatmentInstruction":
        source = Path(path)
        try:
            _regular_unlinked_path(source)
            payload = source.read_bytes()
        except OSError:
            _fail(PAIR_INVALID)
        blob = _git_blob_sha1(payload)
        if (
            len(payload) != TREATMENT_PACKET_BYTES
            or payload.count(b"\n") != TREATMENT_PACKET_LF
            or b"\r" in payload
            or _sha256_bytes(payload) != TREATMENT_PACKET_SHA256
            or blob != TREATMENT_PACKET_GIT_BLOB
        ):
            _fail(PAIR_INVALID)
        return cls(payload, TREATMENT_PACKET_SHA256, TREATMENT_PACKET_GIT_BLOB)


@dataclass(frozen=True)
class LeafWorkspace:
    path: Path
    token: str
    acl: LeafAclObservation


class LeafWorkspaceManager:
    """Create-once leaves with at most one active leaf in this process."""

    @classmethod
    def for_windows_runtime(
        cls,
        root: Path | str,
        *,
        powershell: PinnedExecutable,
        launcher_sid: str,
        generation_probe: Callable[[], Any],
        credentials_denied: Callable[[Any], bool],
        temp_root: Path | str,
    ) -> "LeafWorkspaceManager":
        """Compose the production leaf manager with the concrete ACL probe."""

        return cls(
            root,
            acl_probe=WindowsLeafAclProbe(
                powershell=powershell,
                launcher_sid=launcher_sid,
                generation_probe=generation_probe,
                credentials_denied=credentials_denied,
                temp_root=temp_root,
            ),
        )

    def __init__(self, root: Path | str, *, acl_probe: AclProbe) -> None:
        self.root = Path(root)
        self._acl_probe = acl_probe
        self._active: LeafWorkspace | None = None
        self._issued: set[str] = set()
        if not self.root.is_absolute() or not callable(acl_probe):
            _fail()
        if self.root.exists():
            try:
                value = os.lstat(self.root)
            except OSError:
                _fail()
            if not stat.S_ISDIR(value.st_mode) or _is_reparse(value):
                _fail()
            try:
                if any(self.root.iterdir()):
                    _fail()
            except OSError:
                _fail()
        else:
            try:
                self.root.mkdir(parents=True, exist_ok=False)
            except OSError:
                _fail()

    def create(self, token: str) -> LeafWorkspace:
        if (
            self._active is not None
            or not isinstance(token, str)
            or not token
            or not token.isascii()
            or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in token)
            or token in self._issued
        ):
            _fail()
        leaf = self.root / token
        try:
            leaf.mkdir(exist_ok=False)
        except OSError:
            _fail()
        try:
            observation = self._acl_probe(leaf)
            observation.validate(leaf)
        except BaseException:
            shutil.rmtree(leaf, ignore_errors=True)
            raise
        workspace = LeafWorkspace(leaf, token, observation)
        self._issued.add(token)
        self._active = workspace
        return workspace

    def release(self, workspace: LeafWorkspace) -> None:
        if self._active is not workspace:
            _fail()
        try:
            if os.path.lexists(workspace.path):
                value = os.lstat(workspace.path)
                if not stat.S_ISDIR(value.st_mode) or _is_reparse(value):
                    _fail()
                _remove_tree_without_following_links(workspace.path)
        except OSError:
            _fail()
        self._active = None

    @property
    def active(self) -> LeafWorkspace | None:
        return self._active


def _remove_tree_without_following_links(path: Path) -> None:
    value = os.lstat(path)
    if _is_reparse(value) or not stat.S_ISDIR(value.st_mode):
        _fail()
    try:
        children = tuple(path.iterdir())
    except OSError:
        _fail()
    for child in children:
        child_stat = os.lstat(child)
        if _is_reparse(child_stat) or stat.S_ISLNK(child_stat.st_mode):
            if stat.S_ISDIR(child_stat.st_mode):
                os.rmdir(child)
            else:
                child.unlink()
        elif stat.S_ISDIR(child_stat.st_mode):
            _remove_tree_without_following_links(child)
        elif stat.S_ISREG(child_stat.st_mode):
            child.unlink()
        else:
            _fail()
    path.rmdir()


def _closed_git_environment(temp_root: Path) -> dict[str, str]:
    # Inherited Git selectors/configuration are deliberately not copied.  The
    # exact executable, ``-C`` repository selector and config-null policy below
    # therefore dominate even when the operator environment is poisoned.
    env: dict[str, str] = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "NUL" if os.name == "nt" else "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": str(temp_root),
        "LC_ALL": "C",
    }
    for key in ("COMSPEC", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
        if key in os.environ and os.environ[key]:
            env[key] = os.environ[key]
    return env


def _run_git(
    executable: PinnedExecutable,
    binding: RepositoryBinding,
    args: Sequence[str],
    *,
    temp_root: Path,
) -> bytes:
    program = executable.verify()
    command = [str(program), "-C", str(binding.root), *args]
    environment = _closed_git_environment(temp_root)
    # The low-privilege sandbox account is intentionally not the workspace
    # owner.  Admit only this exact, already-bound repository; never inherit a
    # broader operator safe.directory list.
    environment.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": str(binding.root.resolve()),
        }
    )
    try:
        completed = subprocess.run(
            command,
            cwd=binding.root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        _fail()
    if completed.returncode != 0 or len(completed.stderr) > 1_048_576:
        _fail()
    return completed.stdout


def _canonical_reported_path(raw: bytes, *, relative_to: Path | None = None) -> Path:
    try:
        text = raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        _fail()
    if not text or "\n" in text or "\r" in text:
        _fail()
    value = Path(text)
    if not value.is_absolute():
        if relative_to is None:
            _fail()
        value = relative_to / value
    try:
        return value.resolve(strict=True)
    except OSError:
        _fail()


def verify_repository_binding(
    executable: PinnedExecutable,
    binding: RepositoryBinding,
    *,
    temp_root: Path,
) -> None:
    try:
        root = binding.root.resolve(strict=True)
        root_stat = os.lstat(root)
    except OSError:
        _fail()
    if not stat.S_ISDIR(root_stat.st_mode) or _is_reparse(root_stat):
        _fail()
    observed_root = _canonical_reported_path(
        _run_git(executable, binding, ("rev-parse", "--show-toplevel"), temp_root=temp_root)
    )
    observed_git = _canonical_reported_path(
        _run_git(executable, binding, ("rev-parse", "--absolute-git-dir"), temp_root=temp_root)
    )
    observed_common = _canonical_reported_path(
        _run_git(executable, binding, ("rev-parse", "--git-common-dir"), temp_root=temp_root),
        relative_to=root,
    )
    expected = tuple(path.resolve(strict=True) for path in (binding.root, binding.git_dir, binding.common_dir))
    if (observed_root, observed_git, observed_common) != expected:
        _fail()


def _safe_extract_archive(payload: bytes, destination: Path) -> None:
    try:
        archive = tarfile.open(fileobj=BytesIO(payload), mode="r:")
    except tarfile.TarError:
        _fail()
    with archive:
        members = archive.getmembers()
        normalized_names: set[str] = set()
        for member in members:
            pure = PurePosixPath(member.name)
            normalized = member.name.casefold() if os.name == "nt" else member.name
            if (
                not member.name
                or pure.is_absolute()
                or ".." in pure.parts
                or normalized in normalized_names
                or any(
                    not part
                    or (os.name == "nt" and (":" in part or part.endswith((".", " "))))
                    for part in pure.parts
                )
                or member.issym()
                or member.islnk()
                or not (member.isdir() or member.isfile())
            ):
                _fail()
            normalized_names.add(normalized)
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                _fail()
            try:
                target.write_bytes(source.read())
            except OSError:
                _fail()


def workspace_inventory(root: Path) -> tuple[tuple[str, int, str], ...]:
    rows: list[tuple[str, int, str]] = []
    try:
        paths = sorted(root.rglob("*"), key=lambda item: item.as_posix())
    except OSError:
        _fail()
    for path in paths:
        try:
            value = os.lstat(path)
        except OSError:
            _fail()
        if _is_reparse(value) or not (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)):
            _fail()
        if stat.S_ISREG(value.st_mode):
            payload = path.read_bytes()
            rows.append((path.relative_to(root).as_posix(), len(payload), _sha256_bytes(payload)))
    return tuple(rows)


def inventory_sha256(rows: Iterable[tuple[str, int, str]]) -> str:
    payload = json.dumps(list(rows), ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return _sha256_bytes(payload)


@dataclass(frozen=True)
class ArmMaterializationEvidence:
    ordinal: int
    base_commit: str
    inventory: tuple[tuple[str, int, str], ...]
    inventory_sha256: str
    sandbox_principal: str
    sandbox_account_generation: str
    treatment_instruction_sha256: str | None
    fresh_leaf_destroyed: bool


@dataclass(frozen=True)
class PairMaterializationEvidence:
    control: ArmMaterializationEvidence
    treatment: ArmMaterializationEvidence
    host_local: HostLocalIsolation

    def validate(self) -> None:
        self.host_local.validate()
        if (
            self.control.ordinal != 1
            or self.treatment.ordinal != 2
            or self.control.base_commit != FROZEN_BASE_COMMIT
            or self.treatment.base_commit != FROZEN_BASE_COMMIT
            or self.control.inventory != self.treatment.inventory
            or self.control.inventory_sha256 != self.treatment.inventory_sha256
            or self.control.inventory_sha256 != inventory_sha256(self.control.inventory)
            or self.treatment.inventory_sha256 != inventory_sha256(self.treatment.inventory)
            or self.control.treatment_instruction_sha256 is not None
            or self.treatment.treatment_instruction_sha256 != TREATMENT_PACKET_SHA256
            or self.control.sandbox_principal != self.treatment.sandbox_principal
            or self.control.sandbox_account_generation
            != self.treatment.sandbox_account_generation
            or not self.control.fresh_leaf_destroyed
            or not self.treatment.fresh_leaf_destroyed
        ):
            _fail(PAIR_INVALID)


class FrozenGitMaterializer:
    """Materialize and destroy two qualification leaves before Attempt admission."""

    def __init__(
        self,
        *,
        git: PinnedExecutable,
        repository: RepositoryBinding,
        leaves: LeafWorkspaceManager,
        packet: TreatmentInstruction,
        forbidden_snapshot_paths: Sequence[str] = (),
    ) -> None:
        self.git = git
        self.repository = repository
        self.leaves = leaves
        self.packet = packet
        self.forbidden_snapshot_paths = tuple(forbidden_snapshot_paths)

    def _one(self, pair_id: str, ordinal: int, treatment: bool) -> ArmMaterializationEvidence:
        leaf = self.leaves.create(f"{pair_id}-{ordinal}")
        try:
            verify_repository_binding(
                self.git, self.repository, temp_root=self.leaves.root
            )
            resolved = _run_git(
                self.git,
                self.repository,
                ("rev-parse", "--verify", f"{FROZEN_BASE_COMMIT}^{{commit}}"),
                temp_root=self.leaves.root,
            ).decode("ascii", errors="strict").strip()
            if resolved != FROZEN_BASE_COMMIT:
                _fail(PAIR_INVALID)
            archive = _run_git(
                self.git,
                self.repository,
                ("archive", "--format=tar", FROZEN_BASE_COMMIT),
                temp_root=self.leaves.root,
            )
            _safe_extract_archive(archive, leaf.path)
            for relative in self.forbidden_snapshot_paths:
                pure = PurePosixPath(relative)
                if pure.is_absolute() or ".." in pure.parts:
                    _fail()
                if leaf.path.joinpath(*pure.parts).exists():
                    _fail(PAIR_INVALID)
            inventory = workspace_inventory(leaf.path)
            for path in leaf.path.rglob("*"):
                if path.is_file() and _git_blob_sha1(path.read_bytes()) in {
                    HIDDEN_ORACLE_GIT_BLOB,
                    TREATMENT_PACKET_GIT_BLOB,
                }:
                    _fail(PAIR_INVALID)
            evidence = ArmMaterializationEvidence(
                ordinal=ordinal,
                base_commit=FROZEN_BASE_COMMIT,
                inventory=inventory,
                inventory_sha256=inventory_sha256(inventory),
                sandbox_principal=leaf.acl.sandbox_principal,
                sandbox_account_generation=leaf.acl.sandbox_account_generation,
                treatment_instruction_sha256=(self.packet.sha256 if treatment else None),
                fresh_leaf_destroyed=True,
            )
        finally:
            self.leaves.release(leaf)
        return evidence

    def qualify_pair(
        self, pair_id: str, host_local: HostLocalIsolation
    ) -> PairMaterializationEvidence:
        if not isinstance(pair_id, str) or not pair_id:
            _fail()
        host_local.validate()
        control = self._one(pair_id, 1, False)
        treatment = self._one(pair_id, 2, True)
        result = PairMaterializationEvidence(control, treatment, host_local)
        result.validate()
        return result
