import json
from pathlib import Path
import subprocess
import sys

import pytest

from governance_tools.self_smoke_capability_reader import (
    interpret_self_smoke_capability,
    read_self_smoke_capability,
)


ROOT = Path(__file__).resolve().parents[1]
KEY = "default_self_smoke_contract_dependency"
REQUIRED = f"{KEY}: required\n".encode()
NOT_APPLICABLE = f"{KEY}: not_applicable\n".encode()
METADATA = b'schema_version: "1.0"\nlast_updated: "2026-04-24"\nhook_wiring_version: 1.1.0\n'
VALID = [
    (REQUIRED, "required"),
    (NOT_APPLICABLE, "not_applicable"),
    (REQUIRED.replace(b"\n", b"\r\n"), "required"),
    (METADATA.replace(b"\n", b"\r\n") + REQUIRED, "required"),
    (b"# whole-line comment\n   \n" + METADATA + NOT_APPLICABLE, "not_applicable"),
    (b"schema_version: '1.0'\n" + REQUIRED.rstrip(b"\n"), "required"),
]
INVALID = [
    b"", METADATA, f"{KEY}: future_mode\n".encode(), b"# " + REQUIRED,
    REQUIRED + REQUIRED, REQUIRED + NOT_APPLICABLE,
    REQUIRED + b"schema_version: 1.0\nschema_version: 2.0\n",
    b"some_section:\n  " + REQUIRED,
    f'{KEY}: "required"\n'.encode(), f"{KEY}: 'required'\n".encode(),
    REQUIRED.rstrip() + b" # inline\n",
    b"\t" + REQUIRED, REQUIRED + b"# tab\tcomment\n",
    REQUIRED.replace(b"\n", b"\r"), b"\xef\xbb\xbf" + REQUIRED,
    b'other_key: "unterminated\n' + NOT_APPLICABLE,
    b"other_key: *ref\n", b"other_key: &ref 1.0\n",
    b"other_key: !!str 1.0\n", b"other_key: {nested: 1}\n",
    b"other_key: [1, 2]\n", b"other_key: |\n  1.0\n",
    b"other_key: >\n  1.0\n", b"---\n", b"...\n",
    b"other_key: \"1\\n0\"\n", b"  # indented comment\n",
    b"schema: 1.0\n", b"Schema_version: 1.0\n",
    b"other_key: 2026-99-99\n", b"other_key: null\n",
    b"\xff", b"\x00", b"\x0b", b"\x7f", "\u0085".encode(),
    "\u2028".encode(), "\ufffe".encode(),
]


@pytest.mark.parametrize("data,expected", VALID)
def test_supported_whole_documents(data, expected):
    assert interpret_self_smoke_capability(data) == expected


@pytest.mark.parametrize("bad", INVALID)
def test_unsupported_document_never_partially_accepts_target(bad):
    assert interpret_self_smoke_capability(bad) == "UNKNOWN"
    # Valid declarations on either side must not hide malformed other content.
    if bad not in {b"", METADATA, b"# " + REQUIRED}:
        assert interpret_self_smoke_capability(REQUIRED + bad) == "UNKNOWN"
        assert interpret_self_smoke_capability(bad + REQUIRED) == "UNKNOWN"


@pytest.mark.parametrize("relative", [
    ".governance/version_manifest.yaml",
    "examples/usb-hub-contract/.governance/version_manifest.yaml",
    "artifacts/ab-live/2026-04-29-round2b-live-001/usb-hub-contract/workspace/group-b/.governance/version_manifest.yaml",
])
def test_shipped_metadata_is_supported_without_rewriting_files(relative):
    original = (ROOT / relative).read_bytes()
    # Old manifests legitimately lack the capability. Add it only in memory to
    # distinguish supported metadata from an accidentally rejected document.
    if KEY.encode() not in original:
        assert interpret_self_smoke_capability(original) == "UNKNOWN"
        original += b"\n" + REQUIRED
    assert interpret_self_smoke_capability(original) == "required"


def test_current_canonical_version_fixture_metadata_is_supported():
    yaml = pytest.importorskip("yaml")
    from tests.test_governance_version_check import _VERSION_MANIFEST_FULL
    data = yaml.dump(_VERSION_MANIFEST_FULL).encode() + REQUIRED
    assert interpret_self_smoke_capability(data) == "required"


def test_pyyaml_agrees_on_accepted_subset():
    yaml = pytest.importorskip("yaml")
    for data, expected in VALID:
        assert yaml.safe_load(data)[KEY] == expected
        assert interpret_self_smoke_capability(data) == expected


def test_unreadable_or_missing_manifest_is_unknown(tmp_path, monkeypatch):
    assert read_self_smoke_capability(tmp_path) == "UNKNOWN"
    def denied(_path):
        raise PermissionError("fixture unreadable")
    monkeypatch.setattr(Path, "read_bytes", denied)
    assert read_self_smoke_capability(tmp_path) == "UNKNOWN"


def test_same_bytes_without_site_packages_and_without_git(tmp_path):
    git_root, plain_root = tmp_path / "git", tmp_path / "plain"
    for root in (git_root, plain_root):
        (root / ".governance").mkdir(parents=True)
    subprocess.run(["git", "init", str(git_root)], check=True, capture_output=True)
    corpus = VALID + [(data, "UNKNOWN") for data in INVALID]
    script = (
        "import json,sys; from pathlib import Path; "
        "from governance_tools.self_smoke_capability_reader import read_self_smoke_capability as read; "
        "print(json.dumps([read(Path(p)) for p in sys.argv[1:]]))"
    )
    for data, expected in corpus:
        for root in (git_root, plain_root):
            (root / ".governance/version_manifest.yaml").write_bytes(data)
            assert read_self_smoke_capability(root) == expected
        result = subprocess.run(
            [sys.executable, "-S", "-c", script, str(git_root), str(plain_root)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        assert json.loads(result.stdout) == [expected, expected]
