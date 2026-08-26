"""Exact, disposable npm distribution materialization for C1 pair-02.

The module downloads only two frozen tarball URLs, verifies every retained
archive binding before extraction, extracts an allowlisted native executable,
and leaves cleanup to the caller.  It performs no work on import.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable


VERSION = "0.148.0-alpha.9"
CLI_VERSION = "codex-cli 0.148.0-alpha.9"
CLI_VERSION_STDOUT = b"codex-cli 0.148.0-alpha.9\n"
NATIVE_MEMBER = "package/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
PACKAGE_JSON_MEMBER = "package/package.json"


@dataclass(frozen=True)
class ArchiveBinding:
    name: str
    url: str
    size: int
    sha1: str
    sha256: str
    integrity: str
    package_json_size: int
    package_json_sha256: str


MAIN = ArchiveBinding(
    name="@openai/codex",
    url="https://registry.npmjs.org/@openai/codex/-/codex-0.148.0-alpha.9.tgz",
    size=4_503,
    sha1="10f80c5d6b94a3a583ea14e6f8ddaa113217f11f",
    sha256="6b1b8445a6c4401373b4a506a4ca16436344bbaacc6487230e1a0c09f52049d1",
    integrity="sha512-SemrHW/3t1LkZLZbBOuNyhAOngfC7+43ytL3Ic2qnw0I+5MIhpxg7IbamQVUr1oL1TUhssK/XQkw17ZUtYVkWg==",
    package_json_size=1_138,
    package_json_sha256="92a7607ce715f77a62c66dd092eba2ba10848355aad5dd364319e3ee1c941157",
)

WINDOWS_X64 = ArchiveBinding(
    name="@openai/codex-win32-x64",
    url="https://registry.npmjs.org/@openai/codex/-/codex-0.148.0-alpha.9-win32-x64.tgz",
    size=132_147_990,
    sha1="5b24e1a4b9cfd39e1d7f012e27a7514f918aa84a",
    sha256="d9ccfc635364c7387e7078a540d646b0c3f118cf50f1bb99f8828796f29ee324",
    integrity="sha512-2PKkm3xE6mM1bXeVaUoG0RdYowosfODxLy0Wta93hRcybV9m38H2RJ8UQEZJQYPu1dX092PhkAKZRMF9oYPFXA==",
    package_json_size=519,
    package_json_sha256="dccbbeb5a5271f99c387ab9a83e6170932d17010b69684dd579bad75a377abb4",
)

NATIVE_BYTES = 295_151_920
NATIVE_SHA256 = "88aa986d1405d41dcc9c2f777d7b028de07edc33b6468a8dd8db6a0cc62c315f"


class DistributionError(RuntimeError):
    """The exact npm distribution cannot be safely materialized."""


def _digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _verify_archive(path: Path, binding: ArchiveBinding) -> None:
    if not path.is_file() or path.stat().st_size != binding.size:
        raise DistributionError(f"{binding.name} tarball byte count differs")
    if _digest(path, "sha1") != binding.sha1:
        raise DistributionError(f"{binding.name} tarball SHA-1 differs")
    if _digest(path, "sha256") != binding.sha256:
        raise DistributionError(f"{binding.name} tarball SHA-256 differs")
    expected_sri = "sha512-" + base64.b64encode(
        bytes.fromhex(_digest(path, "sha512"))
    ).decode("ascii")
    if expected_sri != binding.integrity:
        raise DistributionError(f"{binding.name} tarball integrity differs")


def _read_member(archive: Path, member_name: str, *, maximum: int) -> bytes:
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            member = bundle.getmember(member_name)
            if not member.isfile() or member.size > maximum:
                raise DistributionError(f"tar member is invalid: {member_name}")
            stream = bundle.extractfile(member)
            if stream is None:
                raise DistributionError(f"tar member is unreadable: {member_name}")
            raw = stream.read(maximum + 1)
    except (KeyError, OSError, tarfile.TarError) as exc:
        raise DistributionError(f"tar member is unavailable: {member_name}") from exc
    if len(raw) != member.size or len(raw) > maximum:
        raise DistributionError(f"tar member byte count differs: {member_name}")
    return raw


def _verify_package_json(archive: Path, binding: ArchiveBinding) -> None:
    raw = _read_member(archive, PACKAGE_JSON_MEMBER, maximum=16_384)
    if len(raw) != binding.package_json_size or hashlib.sha256(raw).hexdigest() != binding.package_json_sha256:
        raise DistributionError(f"{binding.name} package.json differs")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DistributionError(f"{binding.name} package.json is invalid") from exc
    expected_version = VERSION if binding is MAIN else VERSION + "-win32-x64"
    if value.get("version") != expected_version:
        raise DistributionError(f"{binding.name} package version differs")
    if binding is MAIN:
        if value.get("name") != "@openai/codex" or value.get("bin") != {"codex": "bin/codex.js"}:
            raise DistributionError("main package identity differs")
        expected = "npm:@openai/codex@0.148.0-alpha.9-win32-x64"
        if value.get("optionalDependencies", {}).get("@openai/codex-win32-x64") != expected:
            raise DistributionError("main package platform binding differs")
    elif value.get("name") != "@openai/codex":
        raise DistributionError("platform package identity differs")


def _extract_native(archive: Path, destination: Path) -> None:
    digest = hashlib.sha256()
    total = 0
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            member = bundle.getmember(NATIVE_MEMBER)
            if not member.isfile() or member.size != NATIVE_BYTES:
                raise DistributionError("native executable member differs")
            stream = bundle.extractfile(member)
            if stream is None:
                raise DistributionError("native executable member is unreadable")
            with destination.open("xb") as output:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > NATIVE_BYTES:
                        raise DistributionError("native executable exceeded its byte ceiling")
                    digest.update(chunk)
                    output.write(chunk)
    except DistributionError:
        raise
    except (KeyError, OSError, tarfile.TarError) as exc:
        raise DistributionError("native executable extraction failed") from exc
    if total != NATIVE_BYTES or digest.hexdigest() != NATIVE_SHA256:
        raise DistributionError("native executable differs")


def _default_download(url: str, destination: Path, maximum: int) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "c1-gate1-freeze/1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, destination.open("xb") as handle:
            total = 0
            while True:
                chunk = response.read(min(1024 * 1024, maximum + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    raise DistributionError("tarball exceeded frozen byte ceiling")
                handle.write(chunk)
    except DistributionError:
        raise
    except OSError as exc:
        raise DistributionError("exact npm tarball download failed") from exc


def _materialize_created_root(
    scratch_root: Path,
    *,
    downloader: Callable[[str, Path, int], None] = _default_download,
) -> dict[str, object]:
    """Materialize inside a newly-created root."""

    main_path = scratch_root / "main.tgz"
    platform_path = scratch_root / "win32-x64.tgz"
    downloader(MAIN.url, main_path, MAIN.size)
    downloader(WINDOWS_X64.url, platform_path, WINDOWS_X64.size)
    _verify_archive(main_path, MAIN)
    _verify_archive(platform_path, WINDOWS_X64)
    _verify_package_json(main_path, MAIN)
    _verify_package_json(platform_path, WINDOWS_X64)
    executable = scratch_root / "codex.exe"
    _extract_native(platform_path, executable)
    main_path.unlink()
    platform_path.unlink()
    return {
        "executable": executable,
        "main_tarball_sha256": MAIN.sha256,
        "native_bytes": NATIVE_BYTES,
        "native_sha256": NATIVE_SHA256,
        "platform_tarball_sha256": WINDOWS_X64.sha256,
        "scratch_root": scratch_root,
    }


def materialize_exact_distribution(
    scratch_root: Path,
    *,
    downloader: Callable[[str, Path, int], None] = _default_download,
) -> dict[str, object]:
    """Materialize the exact native binary without retaining npm payloads."""

    if scratch_root.exists():
        raise DistributionError("distribution scratch already exists")
    scratch_root.mkdir(parents=True)
    try:
        return _materialize_created_root(scratch_root, downloader=downloader)
    except BaseException as original:
        try:
            shutil.rmtree(scratch_root)
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "distribution materialization and cleanup both failed",
                [original, cleanup],
            ) from original
        raise


def cleanup_distribution(observation: dict[str, object]) -> None:
    root = observation.get("scratch_root")
    if isinstance(root, Path) and root.exists():
        shutil.rmtree(root)
