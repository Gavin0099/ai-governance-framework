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


def test_public_api_diff_checker_classifies_added_overload_as_non_breaking():
    root = _reset_fixture("added_overload")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(
        before_file,
        """
public class Service
{
    public int Run(int value) => value;
}
""".strip(),
    )
    _write(
        after_file,
        """
public class Service
{
    public int Run(int value) => value;
    public int Run(string value) => value.Length;
}
""".strip(),
    )

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is True
    assert result["compatibility_risk"] == "low"
    assert any("overload or expansion" in warning for warning in result["warnings"])
    assert result["non_breaking_changes"]


def test_public_api_diff_checker_classifies_signature_change_as_breaking():
    root = _reset_fixture("signature_change")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(
        before_file,
        """
public class Service
{
    public int Run(int value) => value;
}
""".strip(),
    )
    _write(
        after_file,
        """
public class Service
{
    public string Run(int value) => value.ToString();
}
""".strip(),
    )

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is False
    assert result["compatibility_risk"] == "high"
    assert any("signature changed" in error for error in result["errors"])
    assert result["breaking_changes"]


def test_public_api_diff_checker_classifies_property_accessor_loss_as_breaking():
    root = _reset_fixture("property_accessor_change")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(
        before_file,
        """
public class Service
{
    public int Status { get; set; }
}
""".strip(),
    )
    _write(
        after_file,
        """
public class Service
{
    public int Status { get; }
}
""".strip(),
    )

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is False
    assert result["compatibility_risk"] == "high"
    assert any("property:Service.Status" in error for error in result["errors"])


def test_public_api_diff_checker_classifies_constructor_overload_as_non_breaking():
    root = _reset_fixture("constructor_overload")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(
        before_file,
        """
public class Service
{
    public Service(int value) {}
}
""".strip(),
    )
    _write(
        after_file,
        """
public class Service
{
    public Service(int value) {}
    public Service(string value) {}
}
""".strip(),
    )

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is True
    assert result["compatibility_risk"] == "low"
    assert any("constructor:Service" in warning for warning in result["warnings"])


def test_public_api_diff_checker_treats_parameter_modifier_change_as_breaking():
    root = _reset_fixture("param_modifier_change")
    before_file = root / "before.cs"
    after_file = root / "after.cs"
    _write(
        before_file,
        """
public class Service
{
    public void Run(int value) {}
}
""".strip(),
    )
    _write(
        after_file,
        """
public class Service
{
    public void Run(ref int value) {}
}
""".strip(),
    )

    result = check_public_api_diff([before_file], [after_file])

    assert result["ok"] is False
    assert result["compatibility_risk"] == "high"
    assert any("method:Service.Run" in error for error in result["errors"])
