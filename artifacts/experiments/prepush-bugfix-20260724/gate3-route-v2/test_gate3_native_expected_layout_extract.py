"""Focused tests for the SDK expected-layout extractor.

Two kinds of test, because the extractor has two kinds of risk.

The parser is exercised against **synthetic headers** written per test. Four
real parsing defects were found while building it — a legacy `#else` typedef
branch, a function parameter read as a declarator, preprocessor lines swallowing
the typedefs that followed them, and equivalent spellings reported as a
conflict — and each has a test here that fails if the fix is removed.

The artifact is locked by **independently written fixtures**. The eleven
expected layouts below were typed from the C declarations, not copied from the
extractor's output, so a change in the extractor that moves a number has to
disagree with them. This is the part that matters: the artifact is the oracle
the native layout gate will trust, and an oracle nothing checks is just an
assertion with a digest.

Neither kind needs the Windows SDK present. The real headers live outside the
repository; the committed artifact is what these tests read.
"""

from __future__ import annotations

import json
import pathlib

import pytest

import gate3_native_expected_layout_extract as extract


ARTIFACT = (
    pathlib.Path(__file__).resolve().parent / "gate3-native-expected-layout.json"
)

# Provenance fixtures, recorded here independently of the extractor's constants.
# Asserting the artifact against `extract.HEADER_ENTRIES` would let a single
# edit change the production constant and the artifact together and still pass,
# which is the same self-referential trap the oracle itself exists to avoid.
PACKAGE_SHA256 = "f8787b2f6678164ae789bdca6247e696c2a0f529a39ceb969d6ef3d69a987131"
PACKAGE_SOURCE_URL = (
    "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.cpp/"
    "10.0.26100.8249/microsoft.windows.sdk.cpp.10.0.26100.8249.nupkg"
)
PACKAGE_VERSION = "10.0.26100.8249"
SDK_VERSION = "10.0.26100.0"

# (canonical package entry, bytes, sha256) for each header actually read.
HEADER_FIXTURES = [
    (
        "c/Include/10.0.26100.0/shared/basetsd.h",
        11448,
        "d35b73f885d7ef7dfd27fce3762c190c1c952a21e10a3945bcb3d1860c673b12",
    ),
    (
        "c/Include/10.0.26100.0/shared/minwindef.h",
        6876,
        "a9cf08be8407a196104124d5ade2308e204e47d3252bcd2ad20d0f2137843d62",
    ),
    (
        "c/Include/10.0.26100.0/shared/ntdef.h",
        119564,
        "2b6ffe6140fa9dbb23a5bba88c7b177cf88d255c98ca8639ff456e2ae377a93c",
    ),
    (
        "c/Include/10.0.26100.0/shared/windef.h",
        7362,
        "040535b19a60264e5fe6971f7cb13cbf24be17abeeaa8acd21e44f5d7dfe8d22",
    ),
    (
        "c/Include/10.0.26100.0/um/WinBase.h",
        271704,
        "ec538199f5ebe8cec2dfd4f1ba48316ef776c82d37277aed3a677965e494f192",
    ),
    (
        "c/Include/10.0.26100.0/um/fileapi.h",
        40460,
        "f8927178c75de487c0e57f044a215e455522bf6eaa0b660421be09cd06ae05a1",
    ),
    (
        "c/Include/10.0.26100.0/um/minwinbase.h",
        13973,
        "7d1408f4b8eeba96ae45892209132258cde80cab6dab192b4cceea591972c78b",
    ),
    (
        "c/Include/10.0.26100.0/um/winnt.h",
        876258,
        "bc603675b330e624fd6f3de9ed3497ed6101e4c56e12cf819a9ef7c41f1c78d8",
    ),
    (
        "c/Include/10.0.26100.0/um/winternl.h",
        30360,
        "a43424486349c38f697c009512dfe4eb8fca733d7665afab42f50752170b9785",
    ),
]

# The two tables that are ABI inputs rather than header facts.
FUNDAMENTAL_FIXTURE = {
    "POINTER": [8, 8],
    "__int64": [8, 8],
    "char": [1, 1],
    "double": [8, 8],
    "float": [4, 4],
    "int": [4, 4],
    "long": [4, 4],
    "long long": [8, 8],
    "short": [2, 2],
    "signed char": [1, 1],
    "unsigned __int64": [8, 8],
    "unsigned char": [1, 1],
    "unsigned int": [4, 4],
    "unsigned long": [4, 4],
    "unsigned long long": [8, 8],
    "unsigned short": [2, 2],
    "void": [1, 1],
    "wchar_t": [2, 2],
}
PREPROCESSOR_FIXTURE = {
    "DWORDLONG": [8, 8],
    "DWORD_PTR": [8, 8],
    "INT_PTR": [8, 8],
    "LONGLONG": [8, 8],
    "LONG_PTR": [8, 8],
    "SIZE_T": [8, 8],
    "SSIZE_T": [8, 8],
    "UINT_PTR": [8, 8],
    "ULONGLONG": [8, 8],
    "ULONG_PTR": [8, 8],
}

# Written from the C declarations, deliberately not from extractor output.
# (size, alignment, [(field, offset, size), ...])
EXPECTED: dict[str, tuple[int, int, list[tuple[str, int, int]]]] = {
    "UNICODE_STRING": (
        16,
        8,
        [("Length", 0, 2), ("MaximumLength", 2, 2), ("Buffer", 8, 8)],
    ),
    "OBJECT_ATTRIBUTES": (
        48,
        8,
        [
            ("Length", 0, 4),
            ("RootDirectory", 8, 8),
            ("ObjectName", 16, 8),
            ("Attributes", 24, 4),
            ("SecurityDescriptor", 32, 8),
            ("SecurityQualityOfService", 40, 8),
        ],
    ),
    "IO_STATUS_BLOCK_UNION": (8, 8, [("Status", 0, 4), ("Pointer", 0, 8)]),
    "IO_STATUS_BLOCK": (16, 8, [("u", 0, 8), ("Information", 8, 8)]),
    "FILE_ID_INFO": (24, 8, [("VolumeSerialNumber", 0, 8), ("FileId", 8, 16)]),
    "FILE_ATTRIBUTE_TAG_INFO": (
        8,
        4,
        [("FileAttributes", 0, 4), ("ReparseTag", 4, 4)],
    ),
    "FILE_DISPOSITION_INFO": (1, 1, [("DeleteFile", 0, 1)]),
    "FILE_DISPOSITION_INFO_EX": (4, 4, [("Flags", 0, 4)]),
    "FILE_BASIC_INFO": (
        40,
        8,
        [
            ("CreationTime", 0, 8),
            ("LastAccessTime", 8, 8),
            ("LastWriteTime", 16, 8),
            ("ChangeTime", 24, 8),
            ("FileAttributes", 32, 4),
        ],
    ),
    "EXCEPTION_RECORD": (
        152,
        8,
        [
            ("ExceptionCode", 0, 4),
            ("ExceptionFlags", 4, 4),
            ("ExceptionRecord", 8, 8),
            ("ExceptionAddress", 16, 8),
            ("NumberParameters", 24, 4),
            ("ExceptionInformation", 32, 120),
        ],
    ),
    "OSVERSIONINFOEXW": (
        284,
        4,
        [
            ("dwOSVersionInfoSize", 0, 4),
            ("dwMajorVersion", 4, 4),
            ("dwMinorVersion", 8, 4),
            ("dwBuildNumber", 12, 4),
            ("dwPlatformId", 16, 4),
            ("szCSDVersion", 20, 256),
            ("wServicePackMajor", 276, 2),
            ("wServicePackMinor", 278, 2),
            ("wSuiteMask", 280, 2),
            ("wProductType", 282, 1),
            ("wReserved", 283, 1),
        ],
    ),
}


@pytest.fixture
def headers():
    """Build a header set through the production loading pipeline.

    Every file the extractor requires is supplied, so a test only has to give
    the fragment it cares about.
    """

    def build(**fragments: str):
        contents = {
            name: fragments.get(name, "").encode("utf-8")
            for name in extract.HEADER_FILES
        }
        return extract.load_headers(contents)

    return build


# --- the four parsing defects, each locked ---------------------------------


def test_preprocessor_dependent_branch_is_not_guessed(headers):
    """winnt.h carries `double` and `__int64` arms for ULONGLONG."""

    loaded = headers(
        **{"winnt.h": "typedef __int64 LONGLONG;\n#else\ntypedef double LONGLONG;\n"}
    )
    assert extract.resolve_typedef(loaded, "LONGLONG") == {"__int64", "double"}
    # The explicit x64 table settles it before the ambiguity can be reached.
    assert extract.type_metrics(loaded, "LONGLONG", frozenset()) == (8, 8)
    assert extract.PREPROCESSOR_DEPENDENT["ULONG_PTR"] == (8, 8)


def test_a_function_parameter_is_not_a_declarator(headers):
    """`(DWORD)` as a parameter says nothing about DWORD."""

    loaded = headers(
        **{
            "windef.h": "typedef unsigned long DWORD;\n"
            "typedef int (WINAPI *PCALLBACK)(DWORD);\n"
        }
    )
    assert extract.resolve_typedef(loaded, "DWORD") == {"unsigned long"}
    assert extract.resolve_typedef(loaded, "PCALLBACK") == {"POINTER"}


def test_directives_cannot_swallow_a_following_typedef(headers):
    """A directive line has no `;`, so a scan can run straight through it."""

    loaded = headers(
        **{
            "winnt.h": "typedef struct _X {\n int a;\n} X;\n"
            "#if defined(_SOMETHING)\n"
            "#define NOISE(e) something_without_a_semicolon\n"
            "#endif\n"
            "typedef void *PVOID;\n"
        }
    )
    assert extract.resolve_typedef(loaded, "PVOID") == {"POINTER"}


def test_equivalent_spellings_are_not_a_conflict(headers):
    """HANDLE is spelled both `void *` and `PVOID`; those are one type."""

    loaded = headers(
        **{
            "winnt.h": "typedef void *PVOID;\n"
            "typedef void *HANDLE;\n"
            "#else\n"
            "typedef PVOID HANDLE;\n"
        }
    )
    assert extract.resolve_typedef(loaded, "HANDLE") == {"POINTER", "PVOID"}
    assert extract.type_metrics(loaded, "HANDLE", frozenset()) == (8, 8)


def test_a_real_metric_conflict_still_fails_closed(headers):
    loaded = headers(
        **{"winnt.h": "typedef unsigned long T;\n#else\ntypedef unsigned __int64 T;\n"}
    )
    with pytest.raises(extract.ExtractionError) as caught:
        extract.type_metrics(loaded, "T", frozenset())
    assert "conflicting typedefs" in str(caught.value)


# --- SAL, constants, layout rules ------------------------------------------


def test_sal_annotations_do_not_look_like_function_pointers(headers):
    loaded = headers(
        **{
            "ntdef.h": "typedef _Return_type_success_(return >= 0) long NTSTATUS;\n"
        }
    )
    assert extract.resolve_typedef(loaded, "NTSTATUS") == {"long"}


def test_array_bounds_resolve_through_a_define(headers):
    loaded = headers(
        **{
            "winnt.h": "#define N_SLOTS 15\n"
            "typedef unsigned long ULONG;\n"
            "typedef struct _A { ULONG items[N_SLOTS]; } A;\n"
        }
    )
    _, body = extract.find_body(loaded, "winnt.h", "_A")
    fields = extract.parse_fields(loaded, body)
    assert fields[0]["size"] == 60


def test_pack_caps_alignment_and_size_rounds_up():
    fields = [
        {"name": "a", "size": 1, "alignment": 1},
        {"name": "b", "size": 8, "alignment": 8},
    ]
    size, alignment, placed = extract.lay_out("struct", fields)
    assert (size, alignment) == (16, 8)
    assert [f["offset"] for f in placed] == [0, 8]

    size, alignment, placed = extract.lay_out("union", fields)
    assert (size, alignment) == (8, 8)
    assert [f["offset"] for f in placed] == [0, 0]


# --- fail-closed inputs -----------------------------------------------------


def test_a_missing_header_fails_closed():
    with pytest.raises(extract.ExtractionError) as caught:
        extract.load_headers({"winnt.h": b""})
    assert "missing header" in str(caught.value)


def test_an_absent_definition_fails_closed(headers):
    loaded = headers()
    with pytest.raises(extract.ExtractionError) as caught:
        extract.find_body(loaded, "winnt.h", "_NOT_THERE")
    assert "definition not found" in str(caught.value)


def test_an_unknown_typedef_fails_closed(headers):
    loaded = headers()
    with pytest.raises(extract.ExtractionError) as caught:
        extract.resolve_typedef(loaded, "NO_SUCH_TYPE")
    assert "typedef not found" in str(caught.value)


def test_an_unknown_constant_fails_closed(headers):
    headers()
    with pytest.raises(extract.ExtractionError) as caught:
        extract.resolve_constant({}, "NO_SUCH_CONSTANT")
    assert "constant not found" in str(caught.value)


def test_an_empty_aggregate_fails_closed():
    with pytest.raises(extract.ExtractionError):
        extract.lay_out("struct", [])


# --- provenance is verified, not asserted ----------------------------------


def _minimal_package(tmp_path, entries):
    import zipfile

    package = tmp_path / "probe.nupkg"
    with zipfile.ZipFile(package, "w") as archive:
        for entry, payload in entries.items():
            archive.writestr(entry, payload)
    return package


def test_a_package_that_is_not_the_pinned_one_is_refused(tmp_path):
    """The whole-file digest is checked before the archive is opened."""

    package = _minimal_package(
        tmp_path, {entry: "" for entry in extract.HEADER_ENTRIES.values()}
    )
    with pytest.raises(extract.ExtractionError) as caught:
        extract.read_package(package)
    assert "package digest mismatch" in str(caught.value)


def test_a_missing_package_is_refused(tmp_path):
    with pytest.raises(extract.ExtractionError) as caught:
        extract.read_package(tmp_path / "absent.nupkg")
    assert "package not found" in str(caught.value)


def test_a_directory_input_is_refused_by_the_public_entry_point(tmp_path):
    """A directory would let any headers be stamped with official provenance.

    Exercised through `build`, not by reading the source: an introspection test
    passes on code that merely mentions the right name.
    """

    directory = tmp_path / "headers"
    directory.mkdir()
    for name in extract.HEADER_FILES:
        (directory / name).write_text("", encoding="utf-8")

    with pytest.raises(extract.ExtractionError) as caught:
        extract.build(directory, "irrelevant")
    assert "package not found" in str(caught.value)


def test_the_archive_is_never_opened_when_the_digest_is_wrong(tmp_path, monkeypatch):
    """Ordering is the property here, and the message alone does not prove it.

    If `ZipFile` were ever moved above the digest comparison, an
    error-text assertion would still pass while a substituted package got read.
    """

    opened: list[object] = []

    def blocked(*args, **kwargs):
        opened.append(args)
        raise AssertionError("archive opened before the digest was verified")

    package = _minimal_package(
        tmp_path, {entry: "" for entry in extract.HEADER_ENTRIES.values()}
    )
    monkeypatch.setattr(extract.zipfile, "ZipFile", blocked)
    with pytest.raises(extract.ExtractionError) as caught:
        extract.read_package(package)
    assert "package digest mismatch" in str(caught.value)
    assert opened == []


def test_a_verified_package_missing_a_closed_entry_is_refused(tmp_path, monkeypatch):
    """Digest valid, inventory incomplete: the entry check must still fire."""

    import hashlib

    entries = {
        entry: "" for entry in extract.HEADER_ENTRIES.values()
    }
    dropped = extract.HEADER_ENTRIES["winternl.h"]
    del entries[dropped]
    package = _minimal_package(tmp_path, entries)

    # Pin the digest to this synthetic package so the check passes and the
    # inventory check is the thing under test.
    monkeypatch.setattr(
        extract, "PACKAGE_SHA256", hashlib.sha256(package.read_bytes()).hexdigest()
    )
    with pytest.raises(extract.ExtractionError) as caught:
        extract.read_package(package)
    assert "missing package entry" in str(caught.value)
    assert dropped in str(caught.value)


# --- unmapped anonymous members --------------------------------------------


def test_an_unregistered_anonymous_placeholder_is_refused():
    """`.get(name, name)` would pass an unknown placeholder straight through."""

    assert "DUMMYUNIONNAME2" not in extract.ANONYMOUS_MEMBER_NAMES
    with pytest.raises(extract.ExtractionError) as caught:
        extract.canonical_field_names(
            [{"name": "DUMMYUNIONNAME2", "offset": 0, "size": 8, "anonymous": True}]
        )
    assert "unmapped anonymous member" in str(caught.value)


def test_the_registered_placeholder_is_mapped():
    mapped = extract.canonical_field_names(
        [{"name": "DUMMYUNIONNAME", "offset": 0, "size": 8, "anonymous": True}]
    )
    assert mapped == [{"name": "u", "offset": 0, "size": 8}]


def test_a_named_nested_union_keeps_its_name(headers):
    """Nesting does not make a member anonymous; the declarator decides.

    Parsed through `parse_fields`, because the defect this locks was in the
    parser: it marked every nested aggregate anonymous, so `} named;` was
    rejected as an unmapped placeholder.
    """

    loaded = headers(
        **{
            "winnt.h": "typedef unsigned long ULONG;\n"
            "typedef struct _S {\n"
            "  union { ULONG X; } named;\n"
            "  ULONG After;\n"
            "} S;\n"
        }
    )
    _, body = extract.find_body(loaded, "winnt.h", "_S")
    fields = extract.parse_fields(loaded, body)
    assert [f["name"] for f in fields] == ["named", "After"]
    assert fields[0]["anonymous"] is False

    _, _, placed = extract.lay_out("struct", fields)
    assert [f["name"] for f in extract.canonical_field_names(placed)] == [
        "named",
        "After",
    ]


def test_a_placeholder_declarator_is_recognised_as_anonymous(headers):
    loaded = headers(
        **{
            "winnt.h": "typedef unsigned long ULONG;\n"
            "typedef struct _T {\n"
            "  union { ULONG X; } DUMMYUNIONNAME;\n"
            "} T;\n"
        }
    )
    _, body = extract.find_body(loaded, "winnt.h", "_T")
    fields = extract.parse_fields(loaded, body)
    assert fields[0]["anonymous"] is True

    _, _, placed = extract.lay_out("struct", fields)
    assert extract.canonical_field_names(placed)[0]["name"] == "u"


def test_an_unregistered_placeholder_spelling_still_fails_closed(headers):
    loaded = headers(
        **{
            "winnt.h": "typedef unsigned long ULONG;\n"
            "typedef struct _U {\n"
            "  union { ULONG X; } DUMMYUNIONNAME2;\n"
            "} U;\n"
        }
    )
    _, body = extract.find_body(loaded, "winnt.h", "_U")
    fields = extract.parse_fields(loaded, body)
    assert fields[0]["anonymous"] is True, "recognised as a placeholder"
    _, _, placed = extract.lay_out("struct", fields)
    with pytest.raises(extract.ExtractionError) as caught:
        extract.canonical_field_names(placed)
    assert "unmapped anonymous member" in str(caught.value)


def test_anonymity_recognition_is_declarator_based():
    assert extract.is_anonymous_declarator("") is True
    assert extract.is_anonymous_declarator("DUMMYUNIONNAME") is True
    assert extract.is_anonymous_declarator("DUMMYSTRUCTNAME3") is True
    assert extract.is_anonymous_declarator("named") is False
    assert extract.is_anonymous_declarator("u") is False


# --- the committed artifact -------------------------------------------------


@pytest.fixture(scope="module")
def artifact():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_the_anonymous_member_maps_to_the_ctypes_name(artifact):
    """The SDK spells it `DUMMYUNIONNAME`; the declarations under test say `u`."""

    assert extract.ANONYMOUS_MEMBER_NAMES["DUMMYUNIONNAME"] == "u"
    names = [f["name"] for f in artifact["types"]["IO_STATUS_BLOCK"]["fields"]]
    assert names == ["u", "Information"]
    assert "DUMMYUNIONNAME" not in json.dumps(artifact)


@pytest.mark.parametrize("type_name", sorted(EXPECTED))
def test_every_type_matches_its_independent_fixture(artifact, type_name):
    expected_size, expected_alignment, expected_fields = EXPECTED[type_name]
    actual = artifact["types"][type_name]
    assert actual["size"] == expected_size
    assert actual["alignment"] == expected_alignment
    assert [
        (f["name"], f["offset"], f["size"]) for f in actual["fields"]
    ] == expected_fields


def test_the_artifact_covers_exactly_the_declared_types(artifact):
    assert set(artifact["types"]) == set(EXPECTED)
    assert set(artifact["types"]) == {name for name, _, _ in extract.TARGETS}


def test_header_digests_match_independent_fixtures(artifact):
    records = artifact["provenance"]["header_digests"]
    assert [
        (r["path"], r["bytes"], r["sha256"]) for r in records
    ] == HEADER_FIXTURES
    paths = [record["path"] for record in records]
    assert paths == sorted(paths), "must be deterministic"
    assert len(paths) == len(set(paths))
    for path in paths:
        assert path.startswith("c/Include/")
        assert "\\" not in path and not path.startswith("/")
        assert all(part not in ("", ".", "..") for part in path.split("/"))


def test_provenance_names_its_official_source_chain(artifact):
    provenance = artifact["provenance"]
    assert provenance["package_id"] == "Microsoft.Windows.SDK.CPP"
    assert provenance["package_version"] == PACKAGE_VERSION
    assert provenance["package_sha256"] == PACKAGE_SHA256
    assert provenance["package_source_url"] == PACKAGE_SOURCE_URL
    assert provenance["sdk_version"] == SDK_VERSION
    assert provenance["abi"] == "64/win64/WinDLL"
    assert provenance["pack"] == 8


def test_the_abi_input_tables_match_independent_fixtures(artifact):
    provenance = artifact["provenance"]
    assert provenance["fundamental_type_table"] == FUNDAMENTAL_FIXTURE
    assert provenance["preprocessor_dependent_type_table"] == PREPROCESSOR_FIXTURE


def test_provenance_has_exactly_the_closed_key_set(artifact):
    assert sorted(artifact["provenance"]) == [
        "abi",
        "extraction_method",
        "extractor_path",
        "extractor_sha256",
        "fundamental_type_table",
        "header_digests",
        "measurement_class",
        "pack",
        "package_id",
        "package_sha256",
        "package_source_url",
        "package_version",
        "preprocessor_dependent_type_table",
        "sdk_version",
    ]
    assert sorted(artifact) == ["provenance", "schema", "types"]


def test_the_artifact_does_not_claim_to_be_a_compiled_measurement(artifact):
    assert artifact["provenance"]["measurement_class"] == "computed-not-compiled"
    assert artifact["provenance"]["extraction_method"] == "headers-parsed"


def test_the_extractor_digest_matches_the_extractor(artifact):
    import hashlib

    recorded = artifact["provenance"]["extractor_sha256"]
    actual = hashlib.sha256(
        pathlib.Path(extract.__file__).read_bytes()
    ).hexdigest()
    assert recorded == actual, "regenerate the artifact after editing the extractor"


def test_numeric_fields_are_integers_not_booleans(artifact):
    for spec in artifact["types"].values():
        assert type(spec["size"]) is int
        assert type(spec["alignment"]) is int
        for field in spec["fields"]:
            assert type(field["offset"]) is int
            assert type(field["size"]) is int
