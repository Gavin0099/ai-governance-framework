from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.public_api_diff_checker import (
    check_public_api_diff,
    extract_public_api_manifest,
)


FIXTURE_ROOT = Path("tests/_tmp_public_api_diff")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_extract_public_api_manifest_csharp():
    root = _reset_fixture("csharp")
    file_path = root / "Service.cs"
    _write(
        file_path,
        """
public class Service
{
    public int Run(int value) => value;
    internal void Hidden() {}
}
""".strip(),
    )

    manifest = extract_public_api_manifest([file_path])

    assert manifest["entries"]
    signatures = manifest["entries"][0]["signatures"]
    assert any("public class Service" in item for item in signatures)


def test_public_api_diff_checker_flags_removed_signature():
    root = _reset_fixture("removed_signature")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(before_file, "public class Service { public int Run(int value) => value; }")
    _write(after_file, "public class Service { internal int Run(int value) => value; }")

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is False
    assert any("Public API surface removed or changed." in error for error in result["errors"])


def test_public_api_diff_checker_warns_on_added_signature():
    root = _reset_fixture("added_signature")
    before_file = root / "before.swift"
    after_file = root / "after.swift"
    _write(before_file, "public struct ApiSurface {}")
    _write(after_file, "public struct ApiSurface {}\npublic func newEndpoint() {}")

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is True
    assert result["added"]
    assert any("Public API surface added or changed." in warning for warning in result["warnings"])
