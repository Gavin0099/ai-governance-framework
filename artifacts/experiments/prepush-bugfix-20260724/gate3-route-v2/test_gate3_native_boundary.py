"""Focused tests for tranche N1: declarations and the SDK layout gate.

The gate exists to catch a wrong declaration, so the test that matters is the
one proving a wrong declaration fails. Everything else here guards the path
that gets it there: the artifact must be the pinned one, verified before it is
parsed, and validated before any value in it is trusted.

N2 loads two System32 libraries and binds eleven target exports; a test
asserts none of those exports is called. Loading a DLL does run native code in
the Windows loader, so that is not claimed here.
"""

from __future__ import annotations

import copy
import ctypes
import hashlib
import json
import pathlib
import sys

import pytest

import gate3_native_boundary as boundary


REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
ARTIFACT = REPO_ROOT / boundary.EXPECTED_LAYOUT_PATH


@pytest.fixture(scope="module")
def document():
    return boundary.validate_expected_layout(boundary.read_expected_layout())


def _rewritten(tmp_path, mutate):
    """A repo-shaped tree whose artifact has been altered, with digest fixed up."""

    target = tmp_path / boundary.EXPECTED_LAYOUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    mutate(payload)
    target.write_bytes(
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    extractor = tmp_path / boundary.EXTRACTOR_PATH
    extractor.parent.mkdir(parents=True, exist_ok=True)
    extractor.write_bytes((REPO_ROOT / boundary.EXTRACTOR_PATH).read_bytes())
    return tmp_path


# --- the gate itself --------------------------------------------------------


def test_the_declarations_match_the_independent_oracle():
    if not boundary.platform_supported():
        pytest.fail("this suite is expected to run on admitted Windows amd64")
    assert boundary.verify_layout() is not None


def test_a_wrong_declaration_fails_the_gate(monkeypatch):
    """The whole point. A self-derived oracle could not detect this."""

    class WRONG_UNICODE_STRING(ctypes.Structure):
        _pack_ = 8
        _fields_ = [
            ("Length", ctypes.c_ulong),  # should be USHORT
            ("MaximumLength", ctypes.c_ushort),
            ("Buffer", ctypes.c_wchar_p),
        ]

    monkeypatch.setitem(
        boundary.DECLARED_TYPES, "UNICODE_STRING", WRONG_UNICODE_STRING
    )
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_layout()
    assert caught.value.code in {
        "LAYOUT_SIZE_MISMATCH",
        "LAYOUT_FIELD_MISMATCH",
        "LAYOUT_ALIGNMENT_MISMATCH",
    }


def test_a_renamed_field_fails_the_gate(monkeypatch):
    class RENAMED(ctypes.Structure):
        _pack_ = 8
        _fields_ = [("Flags2", ctypes.c_ulong)]

    monkeypatch.setitem(boundary.DECLARED_TYPES, "FILE_DISPOSITION_INFO_EX", RENAMED)
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_layout()
    assert caught.value.code == "LAYOUT_FIELD_SEQUENCE_MISMATCH"


def test_a_union_declared_as_a_structure_fails_the_gate(monkeypatch):
    class NOT_A_UNION(ctypes.Structure):
        _pack_ = 8
        _fields_ = [("Status", ctypes.c_long), ("Pointer", ctypes.c_void_p)]

    monkeypatch.setitem(
        boundary.DECLARED_TYPES, "IO_STATUS_BLOCK_UNION", NOT_A_UNION
    )
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_layout()
    assert caught.value.code in {"LAYOUT_KIND_MISMATCH", "LAYOUT_SIZE_MISMATCH"}


def test_the_declared_layout_reader_reports_what_ctypes_produces():
    layout = boundary.declared_layout(boundary.FILE_DISPOSITION_INFO)
    assert layout == {
        "kind": "structure",
        "size": 1,
        "alignment": 1,
        "fields": [{"name": "DeleteFile", "offset": 0, "size": 1}],
    }


# --- artifact authority -----------------------------------------------------


def test_a_substituted_artifact_is_refused(tmp_path):
    root = _rewritten(tmp_path, lambda d: d["types"].pop("FILE_ID_INFO"))
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.read_expected_layout(root)
    assert caught.value.code == "EXPECTED_LAYOUT_DIGEST_MISMATCH"


def test_the_artifact_is_not_parsed_before_its_digest_is_checked(
    tmp_path, monkeypatch
):
    """Ordering, proven by making a parse fatal rather than by reading source."""

    parsed: list[object] = []

    def blocked(*args, **kwargs):
        parsed.append(args)
        raise AssertionError("artifact parsed before its digest was verified")

    root = _rewritten(tmp_path, lambda d: d["provenance"].__setitem__("pack", 4))
    monkeypatch.setattr(boundary.json, "loads", blocked)
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.read_expected_layout(root)
    assert caught.value.code == "EXPECTED_LAYOUT_DIGEST_MISMATCH"
    assert parsed == []


def test_a_missing_artifact_is_refused(tmp_path):
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.read_expected_layout(tmp_path)
    assert caught.value.code == "EXPECTED_LAYOUT_UNREADABLE"


def test_duplicate_keys_are_refused():
    with pytest.raises(boundary.LayoutError) as caught:
        json.loads(
            '{"schema":"a","schema":"b"}',
            object_pairs_hook=boundary._reject_duplicate_keys,
        )
    assert caught.value.code == "EXPECTED_LAYOUT_DUPLICATE_KEY"


def test_nan_and_infinity_are_refused():
    for token in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(boundary.LayoutError):
            json.loads(
                '{"size": %s}' % token,
                object_pairs_hook=boundary._reject_duplicate_keys,
                parse_constant=boundary._reject_constants,
            )


def _repinned(tmp_path, payload):
    """Write an artifact and pin its digest, so the tail rule is what is tested."""

    import hashlib

    target = tmp_path / boundary.EXPECTED_LAYOUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(
    ("tail", "accepted"),
    [
        (b"\n", True),
        (b"", False),
        (b"\n\n", False),
        (b" \n", False),
        (b"\t\n", False),
        (b"\r\n", False),
        (b"\n ", False),
    ],
)
def test_the_json_tail_rule_is_exactly_one_final_lf(
    tmp_path, monkeypatch, tail, accepted
):
    """`json.loads` accepts arbitrary trailing whitespace; the bytes decide.

    The design said "no trailing bytes after the top-level object", which the
    committed artifact — LF-terminated like every other pinned file here — did
    not satisfy. The rule is settled as exactly one final LF.
    """

    payload = ARTIFACT.read_bytes()[:-1] + tail
    monkeypatch.setattr(
        boundary, "EXPECTED_LAYOUT_SHA256", _repinned(tmp_path, payload)
    )
    if accepted:
        assert boundary.read_expected_layout(tmp_path) is not None
    else:
        with pytest.raises(boundary.LayoutError):
            boundary.read_expected_layout(tmp_path)


def test_a_second_document_after_the_first_is_refused(tmp_path, monkeypatch):
    payload = ARTIFACT.read_bytes()[:-1] + b'{"second":1}\n'
    monkeypatch.setattr(
        boundary, "EXPECTED_LAYOUT_SHA256", _repinned(tmp_path, payload)
    )
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.read_expected_layout(tmp_path)
    assert caught.value.code == "EXPECTED_LAYOUT_INVALID"


def test_the_committed_artifact_ends_with_exactly_one_lf():
    payload = ARTIFACT.read_bytes()
    assert payload.endswith(b"\n")
    assert not payload[:-1].endswith((b"\n", b" ", b"\t", b"\r"))


def test_the_committed_artifact_digest_matches_the_pin():
    assert (
        hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        == boundary.EXPECTED_LAYOUT_SHA256
    )


# --- extractor verification -------------------------------------------------


def test_the_extractor_is_hashed_as_data_not_imported():
    assert boundary.verify_extractor() == boundary.EXTRACTOR_SHA256

    import ast

    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(name.startswith("gate3_") for name in imported), imported


def test_a_tampered_extractor_is_refused(tmp_path):
    root = _rewritten(tmp_path, lambda d: None)
    (root / boundary.EXTRACTOR_PATH).write_bytes(b"# altered\n")
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_extractor(root)
    assert caught.value.code == "EXTRACTOR_DIGEST_MISMATCH"


def test_a_missing_extractor_is_refused(tmp_path):
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_extractor(tmp_path)
    assert caught.value.code == "EXTRACTOR_UNREADABLE"


# --- closed schema ----------------------------------------------------------


def _mutated(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("extra top-level key", lambda d: d.update({"extra": 1})),
        ("missing top-level key", lambda d: d.pop("types")),
        ("wrong schema token", lambda d: d.update({"schema": "other"})),
        ("extra provenance key", lambda d: d["provenance"].update({"x": 1})),
        ("missing provenance key", lambda d: d["provenance"].pop("abi")),
        (
            "unknown extraction method",
            lambda d: d["provenance"].update({"extraction_method": "guessed"}),
        ),
        (
            "unknown measurement class",
            lambda d: d["provenance"].update({"measurement_class": "measured"}),
        ),
        ("wrong abi token", lambda d: d["provenance"].update({"abi": "32/x86/CDLL"})),
        ("wrong pack", lambda d: d["provenance"].update({"pack": 4})),
        (
            "boolean where an integer belongs",
            lambda d: d["provenance"].update({"pack": True}),
        ),
        (
            "url not derived from id and version",
            lambda d: d["provenance"].update(
                {"package_source_url": "https://example.invalid/x.nupkg"}
            ),
        ),
        (
            "header path with a traversal component",
            lambda d: d["provenance"]["header_digests"][0].update(
                {"path": "c/Include/../secret.h"}
            ),
        ),
        (
            "header path with a backslash",
            lambda d: d["provenance"]["header_digests"][0].update(
                {"path": "c\\Include\\x.h"}
            ),
        ),
        (
            "header digests out of order",
            lambda d: d["provenance"]["header_digests"].reverse(),
        ),
        (
            "extra key in a header digest record",
            lambda d: d["provenance"]["header_digests"][0].update({"note": "x"}),
        ),
        (
            "short type table",
            lambda d: d["provenance"]["fundamental_type_table"].pop("char"),
        ),
        (
            "non-power-of-two alignment in a type table",
            lambda d: d["provenance"]["fundamental_type_table"].update({"char": [1, 3]}),
        ),
        ("extra type", lambda d: d["types"].update({"BOGUS": d["types"]["FILE_ID_INFO"]})),
        ("missing type", lambda d: d["types"].pop("EXCEPTION_RECORD")),
        ("extra key in a type", lambda d: d["types"]["FILE_ID_INFO"].update({"x": 1})),
        (
            "unknown kind",
            lambda d: d["types"]["FILE_ID_INFO"].update({"kind": "enum"}),
        ),
        (
            "empty field list",
            lambda d: d["types"]["FILE_ID_INFO"].update({"fields": []}),
        ),
        (
            "extra key in a field",
            lambda d: d["types"]["FILE_ID_INFO"]["fields"][0].update({"x": 1}),
        ),
        (
            "negative offset",
            lambda d: d["types"]["FILE_ID_INFO"]["fields"][0].update({"offset": -1}),
        ),
        # Values a review found the earlier validator accepting. Each was a
        # real hole: the schema was described as closed and was not.
        ("sdk_version is prose", lambda d: d["provenance"].update({"sdk_version": "banana"})),
        ("sdk_version is empty", lambda d: d["provenance"].update({"sdk_version": ""})),
        (
            "sdk_version is non-ascii",
            lambda d: d["provenance"].update({"sdk_version": "\uff11.\uff10"}),
        ),
        ("package_id is empty", lambda d: d["provenance"].update({"package_id": ""})),
        (
            "package_id is some other package",
            lambda d: d["provenance"].update({"package_id": "Evil.Package"}),
        ),
        (
            "package_version is empty",
            lambda d: d["provenance"].update({"package_version": ""}),
        ),
        (
            "package_version is non-ascii",
            lambda d: d["provenance"].update({"package_version": "\uff11"}),
        ),
        (
            "package_version is not a version",
            lambda d: d["provenance"].update({"package_version": "latest"}),
        ),
        (
            "a header path outside the closed inventory",
            lambda d: d["provenance"]["header_digests"][0].update(
                {"path": "c/Include/10.0.26100.0/um/other.h"}
            ),
        ),
        (
            "fundamental table sized right but named wrong",
            lambda d: d["provenance"].update(
                {"fundamental_type_table": {f"k{i}": [1, 1] for i in range(18)}}
            ),
        ),
        (
            "preprocessor table sized right but named wrong",
            lambda d: d["provenance"].update(
                {
                    "preprocessor_dependent_type_table": {
                        f"k{i}": [8, 8] for i in range(10)
                    }
                }
            ),
        ),
        (
            "duplicate field names within a type",
            lambda d: d["types"]["FILE_ATTRIBUTE_TAG_INFO"]["fields"][1].update(
                {"name": "FileAttributes"}
            ),
        ),
        (
            "sdk_version with a trailing newline",
            lambda d: d["provenance"].update({"sdk_version": "1.2\n"}),
        ),
        (
            "package_version with a trailing newline",
            lambda d: d["provenance"].update(
                {
                    "package_version": "1.2\n",
                    "package_source_url": (
                        "https://api.nuget.org/v3-flatcontainer/"
                        "microsoft.windows.sdk.cpp/1.2\n/"
                        "microsoft.windows.sdk.cpp.1.2\n.nupkg"
                    ),
                }
            ),
        ),
        (
            "fundamental table in reverse key order",
            lambda d: d["provenance"].update(
                {
                    "fundamental_type_table": dict(
                        reversed(list(d["provenance"]["fundamental_type_table"].items()))
                    )
                }
            ),
        ),
        (
            "preprocessor table in reverse key order",
            lambda d: d["provenance"].update(
                {
                    "preprocessor_dependent_type_table": dict(
                        reversed(
                            list(
                                d["provenance"][
                                    "preprocessor_dependent_type_table"
                                ].items()
                            )
                        )
                    )
                }
            ),
        ),
        (
            "extractor digest that is well formed but not the real one",
            lambda d: d["provenance"].update({"extractor_sha256": "0" * 64}),
        ),
        (
            "non-ascii field name",
            lambda d: d["types"]["FILE_DISPOSITION_INFO_EX"]["fields"][0].update(
                {"name": "\uff26lags"}
            ),
        ),
    ],
)
def test_the_closed_schema_refuses(document, label, mutate):
    with pytest.raises(boundary.LayoutError):
        boundary.validate_expected_layout(_mutated(document, mutate))


def test_the_unmodified_document_validates(document):
    assert boundary.validate_expected_layout(copy.deepcopy(document)) is not None


# --- what this tranche does NOT do -----------------------------------------


def test_no_native_library_is_loaded(monkeypatch):
    """N1 declares and compares. It calls nothing."""

    calls: list[object] = []

    def blocked(*args, **kwargs):
        calls.append(args)
        raise AssertionError("tranche N1 must not load a native library")

    for name in ("WinDLL", "CDLL", "OleDLL", "PyDLL"):
        if hasattr(ctypes, name):
            monkeypatch.setattr(ctypes, name, blocked)
    boundary.verify_layout()
    assert calls == []


def test_there_is_exactly_one_load_path():
    """N1 asserted the module bound nothing; N2 deliberately binds.

    What still has to hold is narrower and more useful: every load goes through
    `system_library`, which enforces the allowlist, the platform probe and the
    System32 search. A second `WinDLL` call anywhere would bypass all three.
    """

    import ast

    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    loaders = {"WinDLL", "CDLL", "OleDLL", "PyDLL", "windll", "cdll", "oledll"}
    sites: list[str] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            hit = (
                isinstance(node, ast.Attribute) and node.attr in loaders
            ) or (isinstance(node, ast.Name) and node.id in loaders)
            if hit:
                sites.append(function.name)

    assert sites == ["_load"], sites


def test_availability_is_still_false_and_this_tranche_did_not_move_it():
    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False


def test_the_boundary_is_not_wired_into_materialization():
    here = pathlib.Path(__file__).resolve().parent
    for name in ("gate3_historical_materialize.py", "gate3_route_v2_ab_candidate.py"):
        path = here / name
        if path.exists():
            assert "gate3_native_boundary" not in path.read_text(encoding="utf-8")


def test_off_platform_refuses_rather_than_reporting_a_mismatch(monkeypatch):
    """c_wchar is 2 bytes on Windows and 4 elsewhere; a comparison there is noise."""

    monkeypatch.setattr(boundary, "platform_supported", lambda: False)
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.verify_layout()
    assert caught.value.code == "LAYOUT_PLATFORM_UNSUPPORTED"


def test_errors_carry_no_path_or_content(tmp_path):
    with pytest.raises(boundary.LayoutError) as caught:
        boundary.read_expected_layout(tmp_path)
    rendered = str(caught.value) + repr(caught.value)
    assert str(tmp_path) not in rendered
    assert "gate3-native-expected-layout" not in rendered


# ===========================================================================
# Tranche N2 — loading and binding only
# ===========================================================================


@pytest.fixture(scope="module")
def bindings():
    return boundary.load_bindings()


def test_the_public_entry_takes_no_arguments():
    """"No caller-supplied library name" is not an allowlist check.

    An allowlist applied *after* a caller hands a name over still leaves a
    reusable string-to-loader primitive exposed. The control is that no such
    entry point exists.
    """

    import inspect

    assert not hasattr(boundary, "system_library")
    assert inspect.signature(boundary.load_bindings).parameters == {}


def test_the_private_loader_still_refuses_a_name_outside_the_allowlist():
    for name in ("evil.dll", "user32.dll", "ntdll", "", "kernel32.DLL"):
        with pytest.raises(boundary.NativeError) as caught:
            boundary._load(name)
        assert caught.value.code == "LIBRARY_NOT_ALLOWED"


def test_the_allowlist_has_no_exception():
    assert boundary.ALLOWED_LIBRARIES == ("kernel32.dll", "ntdll.dll")


def test_no_bound_export_is_called_in_this_tranche():
    """N2 binds eleven target exports and invokes none of them.

    Binding is not calling, and nothing here sits behind a fail-fast boundary,
    so nothing here may cross one. This is deliberately *not* a claim that no
    native code runs: loading the libraries enters the Windows loader.
    """

    bound = boundary.load_bindings()
    called: list[str] = []

    for library_name, function_name in boundary._Bindings.BOUND:
        library = getattr(bound, library_name)

        def blocker(*args, _name=function_name, **kwargs):
            called.append(_name)
            raise AssertionError(f"N2 must not call {_name}")

        setattr(library, function_name, blocker)

    boundary.verify_layout()
    assert boundary.handle_boundary_available() is False
    assert called == []


def test_every_bound_function_declares_its_signature(bindings):
    """An undeclared call marshals through the default int and truncates a
    handle on 64-bit, which is the exact corruption this boundary prevents."""

    assert len(boundary._Bindings.BOUND) == 11
    for library_name, function_name in boundary._Bindings.BOUND:
        function = getattr(getattr(bindings, library_name), function_name)
        assert function.argtypes, f"{function_name} has no argtypes"


def test_the_platform_probe_runs_before_any_load(monkeypatch):
    loaded = []

    def blocked(*args, **kwargs):
        loaded.append(args)
        raise AssertionError("library loaded before the probe passed")

    monkeypatch.setattr(boundary, "platform_supported", lambda: False)
    monkeypatch.setattr(ctypes, "WinDLL", blocked)
    with pytest.raises(boundary.NativeError) as caught:
        boundary.load_bindings()
    assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"
    assert loaded == []


@pytest.mark.parametrize(
    ("label", "failure"),
    [
        ("probe raises", None),
        ("load raises OSError", OSError("simulated")),
        ("load raises something else", RuntimeError("simulated")),
    ],
)
def test_every_failure_in_this_phase_is_the_same_closed_failure(
    monkeypatch, label, failure
):
    """The boundary is where execution is, not which class was raised.

    An earlier draft had three different behaviours inside one stage the design
    defines as uniformly recoverable: the probe outside any `try`, the load
    catching only `OSError`, and broad translation on the declaration step
    alone.
    """

    if failure is None:
        def raising_probe():
            raise RuntimeError("probe blew up")

        monkeypatch.setattr(boundary, "platform_supported", raising_probe)
    else:
        def failing(*args, **kwargs):
            raise failure

        monkeypatch.setattr(ctypes, "WinDLL", failing)

    with pytest.raises(boundary.NativeError) as caught:
        boundary.load_bindings()
    assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"


@pytest.mark.parametrize(
    "control_flow",
    [KeyboardInterrupt, SystemExit, GeneratorExit],
)
def test_interpreter_control_flow_propagates_untouched(monkeypatch, control_flow):
    """These are not probe, load or binding failures.

    Catching `BaseException` rewrote a Ctrl-C into "this platform is
    unavailable" — a false answer to a question nobody asked, and one that
    would make the boundary uninterruptible.
    """

    def failing(*args, **kwargs):
        raise control_flow()

    monkeypatch.setattr(ctypes, "WinDLL", failing)
    with pytest.raises(control_flow):
        boundary.load_bindings()


def test_a_binding_failure_is_also_recoverable(monkeypatch):
    def failing_declare(self):
        raise AttributeError("no such export")

    monkeypatch.setattr(boundary._Bindings, "_declare", failing_declare)
    with pytest.raises(boundary.NativeError) as caught:
        boundary.load_bindings()
    assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"


def test_the_system32_search_flag_is_used():
    assert boundary.LOAD_LIBRARY_SEARCH_SYSTEM32 == 0x00000800
    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    assert "winmode=LOAD_LIBRARY_SEARCH_SYSTEM32" in source


def test_runtime_facts_are_deferred_not_quietly_dropped():
    """They need a fail-fast boundary first; absence must be visible."""

    for name in ("runtime_facts", "os_build", "library_paths"):
        assert not hasattr(boundary, name), name
    doc = boundary.__doc__ or ""
    assert "Deferred to that tranche" in doc
    assert "GetVolumeInformationByHandleW" in doc


def test_native_errors_carry_no_path_handle_or_status():
    with pytest.raises(boundary.NativeError) as caught:
        boundary._load("evil.dll")
    rendered = str(caught.value) + repr(caught.value)
    assert rendered.count("LIBRARY_NOT_ALLOWED") >= 1
    assert "evil.dll" not in rendered


def test_n2_did_not_move_availability(bindings):
    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False
