#!/usr/bin/env python3
"""Build a byte-stable, pure-Python pytest payload for the pinned Gate 2 image.

The image is immutable and intentionally is not rebuilt.  This builder copies
only the installed files belonging to the fixed pytest runtime closure into a
ZIP that can be placed on PYTHONPATH.  ZIP timestamps, permissions, ordering,
and compression are fixed so the resulting SHA-256 is an execution constant.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import zipfile


PACKAGES = ("pytest", "pluggy", "iniconfig", "packaging", "pygments")
ALLOWED_SUFFIXES = {
    ".py",
    ".typed",
    ".txt",
    ".rst",
    ".md",
    ".json",
}
ALLOWED_METADATA_NAMES = {
    "INSTALLER",
    "LICENSE",
    "LICENSE.txt",
    "METADATA",
    "RECORD",
    "REQUESTED",
    "WHEEL",
    "entry_points.txt",
    "top_level.txt",
}
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def include(path: PurePosixPath) -> bool:
    if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
        return False
    if ".dist-info" in path.as_posix():
        return path.name in ALLOWED_METADATA_NAMES or path.suffix in ALLOWED_SUFFIXES
    return path.suffix in ALLOWED_SUFFIXES


def build(output: Path, manifest_path: Path) -> dict[str, object]:
    entries: dict[str, Path] = {}
    versions: dict[str, str] = {}
    for package in PACKAGES:
        distribution = importlib.metadata.distribution(package)
        versions[package] = distribution.version
        root = Path(distribution.locate_file(""))
        for installed in distribution.files or ():
            relative = PurePosixPath(str(installed).replace("\\", "/"))
            source = root.joinpath(*relative.parts)
            if include(relative) and source.is_file():
                entries[relative.as_posix()] = source

    output.parent.mkdir(parents=True, exist_ok=True)
    file_digests: dict[str, str] = {}
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for relative in sorted(entries):
            content = entries[relative].read_bytes()
            info = zipfile.ZipInfo(relative, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compresslevel=9)
            file_digests[relative] = hashlib.sha256(content).hexdigest()

    payload_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest: dict[str, object] = {
        "format": "gate2-offline-pytest-payload-v1",
        "packages": versions,
        "payload_file": output.name,
        "payload_sha256": payload_sha256,
        "pythonpath_target": "/work/vendor/offline-pytest.zip",
        "file_count": len(file_digests),
        "files": file_digests,
    }
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.output, args.manifest)
    print(json.dumps({
        "file_count": manifest["file_count"],
        "payload_sha256": manifest["payload_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
