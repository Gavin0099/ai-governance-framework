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

# The real `RaiseFailFastException` address, read once at import through the
# approved loader and before any spy exists. A test must not open its own
# `WinDLL` to obtain it: that would bypass the platform probe, the fixed entry
# point and the System32-only search — the controls the owner attached to the
# §3.3 deviation, which bind test scaffolding too. Only the address is read;
# the export is never called here.
_REAL_FAIL_FAST_ADDRESS = ctypes.cast(
    boundary.load_bindings().kernel32.RaiseFailFastException, ctypes.c_void_p
).value

# Callbacks must outlive the instances they are bound to. A ctypes callback
# collected while still bound leaves a dangling function pointer, and the
# module-scoped bindings survive every individual test.
_SPY_KEEPALIVE: list = []


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


def test_historical_candidate_does_not_reference_native_boundary():
    """One committed file, read unconditionally.

    The earlier version looped over two names behind `if path.exists()` and was
    named for materialization coverage it did not have:
    `gate3_historical_materialize.py` is untracked, so in a clean checkout that
    half was skipped in silence while the name still claimed it. The candidate
    half did run — the weakness was the claim, not the whole assertion.

    No `exists()` guard here. A missing file is a failure, not a pass, and the
    name now says only what is checked. M2's own wiring assertion belongs to the
    M2 or M4 slice, once there is a committed file to assert against.
    """

    candidate = (
        pathlib.Path(__file__).resolve().parent / "gate3_route_v2_ab_candidate.py"
    )
    assert "gate3_native_boundary" not in candidate.read_text(encoding="utf-8")


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


def test_the_runtime_facts_arrived_only_after_the_fail_fast_boundary():
    """N2 deferred these; N3a built the exit; N3b added them behind it.

    The one still deferred is the filesystem, and its absence must stay visible
    rather than being quietly filled from a path.
    """

    for name in ("runtime_facts", "os_build", "library_paths"):
        assert hasattr(boundary, name), name
    doc = boundary.__doc__ or ""
    assert "Still deferred" in doc
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


# ===========================================================================
# Tranche N3a — the fail-fast boundary
# ===========================================================================
#
# `fail_fast` terminates the process, so it is never called in this pytest
# parent. Every test that exercises termination runs it in a disposable child
# and inspects the exit code. A test that called it here would take the whole
# suite down with it.

STATUS_FAIL_FAST_EXCEPTION = 0xC0000602
"""What the OS reports when `RaiseFailFastException` is given no record."""

# Measured, not assumed: supplying a record makes the process exit with that
# record's own ExceptionCode, while the parameterless fallback exits with
# STATUS_FAIL_FAST_EXCEPTION. The two paths are therefore distinguishable from
# outside the process, which is worth stating precisely rather than treating
# both as "terminated somehow".
RECORD_PATH_EXIT = 0xE3A70001

# Every child loads through `boundary.load_bindings()` and reuses the kernel32
# it returns. An earlier version called `ctypes.WinDLL("kernel32.dll")`
# directly, which bypassed LOAD_LIBRARY_SEARCH_SYSTEM32, the single approved
# load path, and signature declaration — test scaffolding is not exempt from
# the compensating controls the owner attached to the §3.3 deviation.
CHILD_PROLOGUE = (
    "import ctypes, sys\n"
    "sys.path.insert(0, r'{directory}')\n"
    "import gate3_native_boundary as boundary\n"
    "bindings = boundary.load_bindings()\n"
    # Suppress the Windows Error Reporting dialog so an unhandled fault cannot
    # block this child forever. Declared before it is called, like every other
    # binding.
    "bindings.kernel32.SetErrorMode.argtypes = [ctypes.c_ulong]\n"
    "bindings.kernel32.SetErrorMode.restype = ctypes.c_ulong\n"
    "bindings.kernel32.SetErrorMode(0x0001 | 0x0002)\n"
)

CHILD = CHILD_PROLOGUE + (
    "boundary.fail_fast(bindings, {stage!r}, {code!r})\n"
    "print('RETURNED', flush=True)\n"
)


def _run_child(stage, code):
    import subprocess

    source = CHILD.format(
        directory=str(pathlib.Path(boundary.__file__).resolve().parent),
        stage=stage,
        code=code,
    )
    completed = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=120
    )
    return completed


def test_frozen_stage_ordinals():
    assert boundary.FAIL_FAST_STAGES == {
        "CHAIN": 1,
        "CREATE_DIRECTORY": 2,
        "CREATE_FILE": 3,
        "WRITE": 4,
        "IDENTITY": 5,
        "REVALIDATE": 6,
        "REMOVE": 7,
        "PROBE": 8,
        "ABSENCE_PROBE": 9,
        "CLOSE": 10,
    }


# The ten that existed before N3c-2. Held separately so the append test below
# can prove each one is still on the value it was assigned, which is the whole
# point of the no-renumbering rule: an ordinal already captured in a crash dump
# must not come to mean something else.
_CODES_BEFORE_N3C2 = {
    "UNEXPECTED_EXCEPTION": 1,
    "MATERIALIZE_PATH_EXISTS": 2,
    "MATERIALIZE_WRITE_FAILED": 3,
    "PATH_IS_REPARSE_POINT": 4,
    "PATH_INVALID": 5,
    "ROOT_IDENTITY_UNAVAILABLE": 6,
    "ROOT_IDENTITY_CHANGED": 7,
    "CLEANUP_INCOMPLETE": 8,
    "CLOSE_FAILED": 9,
    "HANDLE_BOUNDARY_UNAVAILABLE": 10,
}


def test_frozen_code_ordinals():
    assert boundary.FAIL_FAST_CODES == {
        **_CODES_BEFORE_N3C2,
        "BASE_NOT_FOUND": 11,
        "BASE_NOT_ADMISSIBLE": 12,
    }


@pytest.mark.parametrize("name,ordinal", sorted(_CODES_BEFORE_N3C2.items()))
def test_n3c2_appended_without_renumbering(name: str, ordinal: int):
    """Asserted one code at a time, so a failure names the one that moved."""

    assert boundary.FAIL_FAST_CODES[name] == ordinal


def test_ordinals_are_unique_and_contiguous():
    for table in (boundary.FAIL_FAST_STAGES, boundary.FAIL_FAST_CODES):
        values = sorted(table.values())
        assert values == list(range(1, len(table) + 1))


def test_every_record_field_is_set_as_specified(bindings):
    """Built in-process. Building a record calls nothing and terminates nothing."""

    record = boundary.build_fail_fast_record(
        bindings, "ABSENCE_PROBE", "CLEANUP_INCOMPLETE"
    )
    assert record.ExceptionCode == 0xE3A70001
    assert record.ExceptionFlags == boundary.EXCEPTION_NONCONTINUABLE == 1
    assert record.ExceptionRecord is None
    assert record.ExceptionAddress, "ExceptionAddress must never be NULL"
    assert record.NumberParameters == 2
    assert record.ExceptionInformation[0] == 9
    assert record.ExceptionInformation[1] == 8
    assert all(
        record.ExceptionInformation[i] == 0
        for i in range(2, boundary.EXCEPTION_MAXIMUM_PARAMETERS)
    )


def test_the_exception_code_carries_the_customer_bit():
    """Bit 29 set, so it cannot collide with a Microsoft-defined status."""

    code = boundary.FAIL_FAST_EXCEPTION_CODE
    assert code >> 30 == 0b11, "severity must be error"
    assert code & (1 << 29), "customer bit must be set"
    assert not code & (1 << 28), "bit 28 is reserved and must be clear"


@pytest.mark.parametrize(
    ("stage", "code"),
    [("NOT_A_STAGE", "CLEANUP_INCOMPLETE"), ("CLOSE", "NOT_A_CODE")],
)
def test_an_unknown_ordinal_refuses_to_invent_one(bindings, stage, code):
    with pytest.raises(KeyError):
        boundary.build_fail_fast_record(bindings, stage, code)


def test_the_payload_cannot_hold_anything_but_ordinals(bindings):
    """The content boundary is structural, not a rule to remember."""

    record = boundary.build_fail_fast_record(bindings, "WRITE", "PATH_INVALID")
    field_types = dict(boundary.EXCEPTION_RECORD._fields_)
    assert field_types["ExceptionInformation"]._type_ is boundary.ULONG_PTR
    for index in range(boundary.EXCEPTION_MAXIMUM_PARAMETERS):
        assert type(record.ExceptionInformation[index]) is int


# --- real termination, disposable children only ----------------------------


def test_fail_fast_terminates_the_process_with_a_record():
    completed = _run_child("WRITE", "MATERIALIZE_WRITE_FAILED")
    assert completed.returncode & 0xFFFFFFFF == RECORD_PATH_EXIT
    assert "RETURNED" not in completed.stdout, "fail_fast must never return"


def test_the_two_paths_are_distinguishable_from_outside_the_process():
    """The exit code says which one ran, which is the only externally visible
    difference between carrying the payload and not carrying it."""

    with_record = _run_child("WRITE", "MATERIALIZE_WRITE_FAILED")
    without_record = _run_child("NOT_A_STAGE", "MATERIALIZE_WRITE_FAILED")
    assert with_record.returncode & 0xFFFFFFFF == RECORD_PATH_EXIT
    assert without_record.returncode & 0xFFFFFFFF == STATUS_FAIL_FAST_EXCEPTION
    assert with_record.returncode != without_record.returncode


def test_fail_fast_still_terminates_when_the_record_cannot_be_built():
    """The fallback path: parameterless call, no payload, still fatal."""

    completed = _run_child("NOT_A_STAGE", "MATERIALIZE_WRITE_FAILED")
    assert completed.returncode & 0xFFFFFFFF == STATUS_FAIL_FAST_EXCEPTION
    assert "RETURNED" not in completed.stdout


def test_termination_is_not_recoverable_from_python():
    """A child wrapping the call in try/except still dies."""

    import subprocess

    source = (
        CHILD_PROLOGUE
        + "try:\n"
        "    boundary.fail_fast(bindings, 'CLOSE', 'CLOSE_FAILED')\n"
        "except BaseException as error:\n"
        "    print('CAUGHT', type(error).__name__, flush=True)\n"
        "print('SURVIVED', flush=True)\n"
    ).format(directory=str(pathlib.Path(boundary.__file__).resolve().parent))
    completed = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=120
    )
    assert completed.returncode & 0xFFFFFFFF == RECORD_PATH_EXIT
    assert "CAUGHT" not in completed.stdout
    assert "SURVIVED" not in completed.stdout


# --- what the boundary does not do -----------------------------------------


def test_fail_fast_performs_no_io_and_has_no_sink():
    """No writer, no buffer, no reader.

    That is the whole claim, and revision 16 withdrew the broader one: the OS
    termination path, an attached debugger or Windows Error Reporting may still
    stall after `RaiseFailFastException` is called. What holds here is only
    that there is no independent pre-fail-fast diagnostic I/O or sink.
    """

    import ast, inspect

    tree = ast.parse(inspect.getsource(boundary.fail_fast))
    forbidden = {"open", "print", "write", "OutputDebugStringW", "flush"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden, node.attr
        elif isinstance(node, ast.Name):
            assert node.id not in forbidden, node.id


def test_fail_fast_yields_nothing_a_caller_could_branch_on():
    import ast, inspect

    tree = ast.parse(inspect.getsource(boundary.fail_fast))
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            assert node.value is None, "must not return a value"


def test_the_claim_ceiling_is_stated_and_conditional():
    doc = boundary.fail_fast.__doc__ or ""
    assert "if" in doc and "construction fails" in doc
    assert "carries no payload" in doc
    assert "not claimed" in doc
    assert "independent durable diagnostic record" in doc
    assert "ruling 8" in doc


def test_the_real_fail_fast_is_unreachable_in_this_process(
    bindings, fail_fast_calls
):
    """Proven by surviving the call, not by introspecting the fixture.

    This line invokes the bound export directly. If the guard were not in
    place — or were opt-in and this test had forgotten to opt in — the process
    would die here rather than fail.

    An earlier version asked each test to install the spy itself and policed
    that with an AST scan over direct `fail_fast` calls. It missed the case
    that actually happened: a test stubbed a bound export badly, the stub
    raised, `_guarded` routed the unexplained exception to fail-fast, and the
    run died at `0xE3A70001`. Opt-in is not a safety property.
    """

    bindings.kernel32.RaiseFailFastException(
        None, None, boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS
    )
    assert len(fail_fast_calls) == 1, "the guard recorded the call"
    had_record, record, _context, flags = fail_fast_calls[0]
    assert not had_record and record is None
    assert flags == boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS


@pytest.mark.parametrize(
    "table_name", ["FAIL_FAST_STAGES", "FAIL_FAST_CODES"]
)
def test_the_ordinal_tables_cannot_be_mutated_at_runtime(table_name):
    """A source-only rule does not stop a caller writing a new ordinal.

    Plain dicts allowed exactly that, so the same stage could have produced
    different ordinals at different times.
    """

    table = getattr(boundary, table_name)
    key = next(iter(table))
    with pytest.raises(TypeError):
        table[key] = 99
    with pytest.raises(TypeError):
        table["INVENTED"] = 42
    assert not hasattr(table, "update")
    assert not hasattr(table, "clear")


@pytest.mark.parametrize(
    "leaked_name", ["_FAIL_FAST_STAGES", "_FAIL_FAST_CODES"]
)
def test_the_backing_dict_is_not_bound_to_a_module_name(leaked_name):
    """A proxy over a dict something else still names is not immutable.

    An earlier revision kept the originals as underscore-prefixed module
    attributes, and writing through one changed the public proxy immediately.
    """

    assert not hasattr(boundary, leaked_name)


def test_no_module_attribute_exposes_a_mutable_ordinal_table():
    """Checked by value, so renaming the leak would not hide it."""

    frozen = [dict(boundary.FAIL_FAST_STAGES), dict(boundary.FAIL_FAST_CODES)]
    for name, value in vars(boundary).items():
        if isinstance(value, dict) and value in frozen:
            pytest.fail(f"{name} exposes a mutable ordinal table")


# The hostile mutation below writes into every reachable dict, which reaches
# `builtins`, `DECLARED_TYPES` and the module's `__annotations__`. Run in this
# process it left `WRITE` behind in all three, so every later test ran in a
# contaminated interpreter and 117 green results proved less than they looked.
# It runs in a disposable child instead.
MUTATION_CHILD = (
    "import sys\n"
    "sys.path.insert(0, r'{directory}')\n"
    "import gate3_native_boundary as boundary\n"
    "leaked = [n for n in dir(boundary) if n in ('_FAIL_FAST_STAGES', '_FAIL_FAST_CODES')]\n"
    "for value in list(vars(boundary).values()):\n"
    "    if isinstance(value, dict):\n"
    "        try:\n"
    "            value['WRITE'] = 99\n"
    "            value['PATH_INVALID'] = 77\n"
    "        except TypeError:\n"
    "            pass\n"
    "print(leaked,\n"
    "      boundary.FAIL_FAST_STAGES['WRITE'],\n"
    "      boundary.FAIL_FAST_CODES['PATH_INVALID'], flush=True)\n"
)


def test_writing_through_any_reachable_dict_cannot_change_an_ordinal():
    """The property that matters, stated as an outcome rather than a shape.

    Run in a child: the mutation is deliberately indiscriminate, so it must not
    be allowed to leave anything behind in the process running the suite.
    """

    import subprocess

    source = MUTATION_CHILD.format(
        directory=str(pathlib.Path(boundary.__file__).resolve().parent)
    )
    completed = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=120
    )
    assert completed.returncode == 0, completed.stderr[-400:]
    assert completed.stdout.strip() == "[] 4 5"


def test_the_mutation_probe_left_nothing_behind_in_this_process():
    """The contamination the child exists to avoid, asserted directly."""

    import builtins

    assert not hasattr(builtins, "WRITE")
    assert "WRITE" not in boundary.DECLARED_TYPES
    assert "WRITE" not in getattr(boundary, "__annotations__", {})
    assert boundary.FAIL_FAST_STAGES["WRITE"] == 4
    assert boundary.FAIL_FAST_CODES["PATH_INVALID"] == 5


def test_the_exception_address_is_exactly_the_bound_thunk(bindings):
    """Truthy is not enough: it must be that function's address."""

    record = boundary.build_fail_fast_record(bindings, "PROBE", "PATH_INVALID")
    expected = ctypes.cast(
        bindings.kernel32.RaiseFailFastException, boundary.PVOID
    ).value
    assert expected
    assert record.ExceptionAddress == expected


@pytest.fixture(autouse=True)
def fail_fast_calls(bindings, monkeypatch):
    """Make the real `RaiseFailFastException` unreachable in this process.

    Autouse, and installed at the *factory* rather than on one instance. An
    earlier version patched only the module-scoped `bindings`, so any test
    calling `boundary.load_bindings()` again got a fresh object still pointing
    at the real export — the address probe showed `FRESH_IS_REAL True`. The
    accident that killed a pytest run was therefore still reproducible.

    Patching the factory means every instance a test can obtain is spied,
    however it was obtained. Real termination is still exercised in disposable
    children, which is the only place it belongs.
    """

    calls: list = []

    # Patched at `_Bindings.__init__`, the lowest construction layer. Patching
    # `load_bindings` alone left a direct `_Bindings()` unspied, so an instance
    # pointing at the real export was still obtainable and the accident that
    # killed a pytest run stayed reproducible.
    real_init = boundary._Bindings.__init__

    def guarded_init(instance):
        real_init(instance)
        _install_fail_fast_spy(instance, calls, _SPY_KEEPALIVE)

    monkeypatch.setattr(boundary._Bindings, "__init__", guarded_init)

    # The module-scoped instance was constructed before this fixture existed.
    _install_fail_fast_spy(bindings, calls, _SPY_KEEPALIVE)
    return calls


def _install_fail_fast_spy(bindings, calls, keepalive):
    """Replace the bound export with a real ctypes callback that records.

    A callback, not a Python function: `build_fail_fast_record` takes the
    address of whatever is bound there, and a plain callable has none. Nothing
    terminates, so this runs safely in the parent.

    `keepalive` holds the callback: a ctypes callback that is garbage collected
    while still bound leaves a dangling function pointer.
    """

    prototype = ctypes.WINFUNCTYPE(
        None,
        ctypes.POINTER(boundary.EXCEPTION_RECORD),
        ctypes.c_void_p,
        ctypes.c_ulong,
    )

    def spy(record_pointer, context_record, flags):
        # Copy the record *now*. In production `fail_fast` never returns, so
        # the record outlives every reader; here it does return, its local goes
        # out of scope, and reading `.contents` afterwards is a use-after-free
        # that produced convincing garbage until this snapshot was added.
        snapshot = None
        if record_pointer:
            snapshot = boundary.EXCEPTION_RECORD()
            ctypes.memmove(
                ctypes.byref(snapshot), record_pointer, ctypes.sizeof(snapshot)
            )
        calls.append((bool(record_pointer), snapshot, context_record, flags))

    callback = prototype(spy)
    keepalive.append(callback)
    bindings.kernel32.RaiseFailFastException = callback
    return calls, callback


def test_the_record_path_passes_the_exact_three_arguments(bindings, monkeypatch, fail_fast_calls):
    boundary.fail_fast(bindings, "REMOVE", "CLOSE_FAILED")

    assert len(fail_fast_calls) == 1
    had_record, record, context_record, flags = fail_fast_calls[0]
    assert had_record, "pExceptionRecord must be the record"
    assert context_record is None, "pContextRecord must be NULL"
    assert flags == boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS == 1

    assert record.ExceptionCode == boundary.FAIL_FAST_EXCEPTION_CODE
    assert record.ExceptionFlags == boundary.EXCEPTION_NONCONTINUABLE
    assert record.NumberParameters == 2
    assert record.ExceptionInformation[0] == boundary.FAIL_FAST_STAGES["REMOVE"]
    assert record.ExceptionInformation[1] == boundary.FAIL_FAST_CODES["CLOSE_FAILED"]


def test_the_fallback_path_passes_a_null_record(bindings, monkeypatch, fail_fast_calls):
    boundary.fail_fast(bindings, "NOT_A_STAGE", "CLOSE_FAILED")

    assert len(fail_fast_calls) == 1
    had_record, record, context_record, flags = fail_fast_calls[0]
    assert not had_record, "fallback must pass NULL, carrying no payload"
    assert record is None
    assert context_record is None
    assert flags == boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS


def test_the_flags_argument_is_never_zero(bindings, monkeypatch, fail_fast_calls):
    """dwFlags == 0 would leave ExceptionAddress unset by the OS."""

    boundary.fail_fast(bindings, "CHAIN", "HANDLE_BOUNDARY_UNAVAILABLE")
    boundary.fail_fast(bindings, "BAD_STAGE", "HANDLE_BOUNDARY_UNAVAILABLE")
    assert [flags for *_, flags in fail_fast_calls] == [1, 1]


def test_no_child_loads_a_library_outside_the_approved_path():
    """Scaffolding is not exempt from the compensating controls.

    Checked against the child source itself rather than by searching this file
    for a literal, which would match the assertion doing the searching.
    """

    import ast

    prologue = CHILD_PROLOGUE.format(directory="X")
    assert "boundary.load_bindings()" in prologue

    loaders = {"WinDLL", "CDLL", "OleDLL", "PyDLL", "windll", "cdll", "oledll"}
    for node in ast.walk(ast.parse(prologue)):
        if isinstance(node, ast.Attribute):
            assert node.attr not in loaders, node.attr
        elif isinstance(node, ast.Name):
            assert node.id not in loaders, node.id


def test_n3a_did_not_move_availability():
    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False


# ===========================================================================
# Tranche N3b — runtime facts, behind the fail-fast boundary
# ===========================================================================
#
# The first tranche that calls bound exports. Every test that could reach a
# real fail-fast installs the spy first, so nothing terminates this process.


def test_the_os_build_comes_from_rtlgetversion(bindings):
    build = boundary.os_build(bindings)
    assert type(build) is int and build > 0
    assert build == sys.getwindowsversion().build


def test_the_version_struct_size_is_set_before_the_call(bindings, monkeypatch):
    """`RtlGetVersion` is undefined if `dwOSVersionInfoSize` is not set."""

    seen = []

    def recording(pointer):
        # `byref()` yields a CArgObject, which has `_obj` and no `.contents`.
        # Reading `.contents` here raised AttributeError, `_guarded` correctly
        # treated it as unexplained, and the real fail-fast took the suite down.
        info = pointer._obj
        seen.append(info.dwOSVersionInfoSize)
        info.dwBuildNumber = 12345
        return 0

    monkeypatch.setattr(bindings.ntdll, "RtlGetVersion", recording)
    assert boundary.os_build(bindings) == 12345
    assert seen == [ctypes.sizeof(boundary.OSVERSIONINFOEXW)]


def test_a_negative_ntstatus_is_a_documented_failure_not_a_panic(
    bindings, monkeypatch, fail_fast_calls
):
    """A negative NTSTATUS is a value the boundary read, so it is explained.

    It is also truthy, which is why success is tested as `>= 0`.
    """

    mapped = []
    monkeypatch.setattr(bindings.ntdll, "RtlGetVersion", lambda p: -1073741823)
    monkeypatch.setattr(
        bindings.ntdll,
        "RtlNtStatusToDosError",
        lambda status: mapped.append(status) or 87,
    )
    with pytest.raises(boundary.NativeError) as caught:
        boundary.os_build(bindings)
    assert caught.value.code == "ROOT_IDENTITY_UNAVAILABLE"
    assert mapped == [-1073741823], "NTSTATUS must go through RtlNtStatusToDosError"
    assert fail_fast_calls == [], "a documented failure must not terminate"


def test_library_paths_resolve_from_the_system_directory(bindings):
    paths = boundary.library_paths(bindings)
    assert set(paths) == {"kernel32.dll", "ntdll.dll"}
    for value in paths.values():
        assert value.lower().startswith("c:\\windows\\system32\\"), value


def test_a_truncated_module_path_is_refused(bindings, monkeypatch, fail_fast_calls):
    """Returning exactly the buffer size means truncated, not fitted.

    A truncated path names a different file, and accepting it as loader
    provenance would evidence the wrong one.
    """

    monkeypatch.setattr(
        bindings.kernel32,
        "GetModuleFileNameW",
        lambda handle, buffer, capacity: capacity,
    )
    with pytest.raises(boundary.NativeError) as caught:
        boundary.library_paths(bindings)
    assert caught.value.code == "ROOT_IDENTITY_UNAVAILABLE"
    assert fail_fast_calls == []


def test_a_zero_length_module_path_is_refused(bindings, monkeypatch, fail_fast_calls):
    """A zero return is documented as "call GetLastError", so it must be read.

    Read immediately, before anything else can overwrite the thread-local
    value — which is why the assertion below is on the order of events, not
    merely on the resulting code.
    """

    read = []
    monkeypatch.setattr(
        bindings.kernel32, "GetModuleFileNameW", lambda handle, buffer, capacity: 0
    )
    monkeypatch.setattr(
        boundary.ctypes, "get_last_error", lambda: read.append("read") or 126
    )
    with pytest.raises(boundary.NativeError) as caught:
        boundary.library_paths(bindings)
    assert caught.value.code == "ROOT_IDENTITY_UNAVAILABLE"
    assert read == ["read"], "the last error must be read on a zero return"
    assert fail_fast_calls == []


def test_a_path_one_short_of_the_buffer_is_accepted(bindings, monkeypatch):
    """The boundary is `>= capacity`, so `capacity - 1` must still pass."""

    def almost_full(handle, buffer, capacity):
        buffer.value = "C:" + chr(92) + "x" * 16
        return capacity - 1

    monkeypatch.setattr(bindings.kernel32, "GetModuleFileNameW", almost_full)
    paths = boundary.library_paths(bindings)
    assert set(paths) == {"kernel32.dll", "ntdll.dll"}


# --- the fail-fast exit is actually wired in -------------------------------


@pytest.mark.parametrize(
    ("function", "target_library", "target_export"),
    [
        ("os_build", "ntdll", "RtlGetVersion"),
        ("library_paths", "kernel32", "GetModuleFileNameW"),
    ],
)
def test_an_escaping_exception_reaches_fail_fast(
    bindings, monkeypatch, fail_fast_calls, function, target_library, target_export
):
    """An OSError out of a ctypes call cannot be told from an ABI fault.

    The spy stops the process from dying, so what is observed here is that the
    fail-fast path was taken with the right ordinals.
    """


    def exploding(*args, **kwargs):
        raise OSError("exception: access violation reading 0x0")

    monkeypatch.setattr(
        getattr(bindings, target_library), target_export, exploding
    )
    with pytest.raises(OSError):
        getattr(boundary, function)(bindings)

    assert len(fail_fast_calls) == 1
    had_record, record, _context, flags = fail_fast_calls[0]
    assert had_record
    assert record.ExceptionInformation[0] == boundary.FAIL_FAST_STAGES["IDENTITY"]
    assert (
        record.ExceptionInformation[1]
        == boundary.FAIL_FAST_CODES["UNEXPECTED_EXCEPTION"]
    )
    assert flags == boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS


@pytest.mark.parametrize(
    "control_flow", [KeyboardInterrupt, SystemExit, GeneratorExit]
)
def test_control_flow_does_not_trigger_fail_fast(
    bindings, monkeypatch, fail_fast_calls, control_flow
):
    """A keystroke is not an ABI fault, and must not terminate the boundary."""


    def failing(*args, **kwargs):
        raise control_flow()

    monkeypatch.setattr(bindings.ntdll, "RtlGetVersion", failing)
    with pytest.raises(control_flow):
        boundary.os_build(bindings)
    assert fail_fast_calls == [], "control flow must propagate, not fail fast"


# `_guarded` is the guard, and `fail_fast` is the exit the guard jumps to;
# neither can route through itself. Everything else in the module must.
_UNGUARDED_BY_DESIGN = frozenset({"_guarded", "fail_fast"})


def _unguarded_calls(source: str) -> list[str]:
    """Names of bound exports called directly anywhere in `source`."""

    import ast

    exports = {name for _, name in boundary._Bindings.BOUND}
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name in _UNGUARDED_BY_DESIGN:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if isinstance(func, ast.Attribute) and func.attr in exports:
                found.append(f"{node.name} calls {func.attr} directly")
    return found


def test_no_bound_export_is_invoked_outside_the_guard():
    """Structural: a direct call would bypass the fail-fast exit entirely.

    Scoped to the whole module, not to a hand-written pair of functions. The
    earlier version listed `os_build` and `library_paths` only, so when N3c-1
    added two direct `CloseHandle` calls it kept passing — the check was
    narrower than the invariant it was named after.
    """

    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    assert _unguarded_calls(source) == []


def test_the_structural_check_would_catch_a_direct_call():
    """The check is load-bearing, not decorative.

    Written against a synthetic source rather than the real module, so proving
    the detector works does not require reintroducing the defect.
    """

    offending = (
        "def cleanup(bindings, handle):\n"
        "    bindings.kernel32.CloseHandle(handle)\n"
    )
    assert _unguarded_calls(offending) == ["cleanup calls CloseHandle directly"]


def test_the_unguarded_exemption_list_stays_minimal():
    """Two names, and both are part of the guard itself."""

    assert _UNGUARDED_BY_DESIGN == {"_guarded", "fail_fast"}


# --- the facts themselves ---------------------------------------------------


def test_runtime_facts_come_from_four_sources(bindings):
    facts = boundary.runtime_facts(bindings)
    assert facts["arch"] == "AMD64"
    assert facts["pointer_bits"] == 64
    assert facts["abi"] == boundary.ADMITTED_ABI == "64/win64/WinDLL"
    assert facts["os_build_source"] == "RtlGetVersion"
    assert facts["os_build"] == sys.getwindowsversion().build


def test_the_filesystem_fact_is_absent_rather_than_substituted(bindings):
    """The design reads it from a held base handle; N3b opens no handle.

    Reporting it from a path instead would be a different fact under the same
    name, which is the failure this absence exists to avoid.
    """

    facts = boundary.runtime_facts(bindings)
    assert facts["filesystem"] is None
    assert "held base handle" in facts["filesystem_reason"]


def test_runtime_facts_refuse_on_an_unadmitted_platform(bindings, monkeypatch):
    monkeypatch.setattr(boundary, "platform_supported", lambda: False)
    with pytest.raises(boundary.NativeError) as caught:
        boundary.runtime_facts(bindings)
    assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"


def test_no_handle_or_filesystem_object_is_touched(bindings, tmp_path):
    before = sorted(tmp_path.rglob("*"))
    boundary.runtime_facts(bindings)
    boundary.library_paths(bindings)
    assert sorted(tmp_path.rglob("*")) == before


def test_the_volume_export_is_still_never_called(bindings, monkeypatch):
    """`GetVolumeInformationByHandleW` is bound and stays uncalled in N3b."""

    called = []
    monkeypatch.setattr(
        bindings.kernel32,
        "GetVolumeInformationByHandleW",
        lambda *args: called.append(args),
    )
    boundary.runtime_facts(bindings)
    boundary.library_paths(bindings)
    assert called == []


@pytest.mark.parametrize("attempt", [1, 2, 3])
def test_a_freshly_loaded_bindings_is_also_spied(bindings, attempt):
    """The earlier guard covered one instance; a fresh load escaped it.

    The address probe showed a new `load_bindings()` still pointing at the real
    export, so the accident that killed a pytest run stayed reproducible.
    """

    real = _REAL_FAIL_FAST_ADDRESS
    assert real

    def address_of(instance):
        return ctypes.cast(
            instance.kernel32.RaiseFailFastException, ctypes.c_void_p
        ).value

    fresh = boundary.load_bindings()
    assert address_of(fresh) != real, "a fresh instance still pointed at the real export"
    assert address_of(bindings) != real

    # Each instance gets its own callback, so the addresses differ from each
    # other too; what matters is that neither is the real one. Proven by
    # surviving the call.
    fresh.kernel32.RaiseFailFastException(
        None, None, boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS
    )


def test_a_directly_constructed_bindings_is_also_spied(bindings):
    """`load_bindings()` is not the only way to get one.

    Patching the factory left `_Bindings()` untouched, so the guard was not at
    the construction boundary it claimed to be at.
    """

    direct = boundary._Bindings()
    address = ctypes.cast(
        direct.kernel32.RaiseFailFastException, ctypes.c_void_p
    ).value
    assert address != _REAL_FAIL_FAST_ADDRESS

    # Proven by surviving the call.
    direct.kernel32.RaiseFailFastException(
        None, None, boundary.FAIL_FAST_GENERATE_EXCEPTION_ADDRESS
    )


def test_the_tests_open_no_library_outside_the_approved_loader():
    """Scaffolding is bound by the same compensating controls."""

    import ast

    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    loaders = {"WinDLL", "CDLL", "OleDLL", "PyDLL", "windll", "cdll", "oledll"}
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        assert name not in loaders, f"{name} opens a library outside the loader"


# --- N3c-1: the pinned ancestor chain ---------------------------------------


def test_the_ancestor_mask_is_revision_17s(bindings):
    """Design evidence 19v: asserted against the constants, not against luck.

    Reading the mask off a call that happened to succeed would prove only that
    this directory allowed it today.
    """

    assert boundary.ANCESTOR_ACCESS == (
        boundary.FILE_LIST_DIRECTORY
        | boundary.FILE_READ_ATTRIBUTES
        | boundary.SYNCHRONIZE
    )
    assert boundary.FILE_READ_ATTRIBUTES == 0x0080
    assert boundary.ANCESTOR_ACCESS & boundary.FILE_READ_ATTRIBUTES


def test_a_borrowed_ancestor_asks_for_no_delete_and_no_share_delete():
    """Design evidence 19x: the pin comes from withholding, not from DELETE.

    Asserted against the constants so a later widening cannot slip through on
    the strength of the tests still passing.
    """

    DELETE = 0x00010000
    FILE_WRITE_ATTRIBUTES = 0x0100
    assert not boundary.ANCESTOR_ACCESS & DELETE
    assert not boundary.ANCESTOR_ACCESS & FILE_WRITE_ATTRIBUTES
    assert not boundary.ANCESTOR_SHARE & boundary.FILE_SHARE_DELETE


def test_a_handle_without_read_attributes_cannot_read_the_reparse_tag(
    bindings, monkeypatch
):
    """Design evidence 19w: the amendment is load-bearing.

    Opens one real directory twice — the repository's own volume root, read
    only, creating and deleting nothing — under revision 16's mask and then
    under revision 17's. If both worked, the amendment would be decoration.
    """

    volume_root, _ = boundary.split_base_path(str(REPO_ROOT))

    monkeypatch.setattr(
        boundary,
        "ANCESTOR_ACCESS",
        boundary.FILE_LIST_DIRECTORY | boundary.SYNCHRONIZE,
    )
    handle = boundary._open_directory(bindings, volume_root, None)
    try:
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary._reparse_tag(bindings, handle)
        assert excinfo.value.args[0] == "ROOT_IDENTITY_UNAVAILABLE"
    finally:
        assert boundary._close_handle(bindings, handle)

    monkeypatch.undo()
    handle = boundary._open_directory(bindings, volume_root, None)
    try:
        assert boundary._reparse_tag(bindings, handle) == 0
    finally:
        assert boundary._close_handle(bindings, handle)


def test_the_chain_pins_every_component_and_revalidates(bindings):
    """One real chain: volume root down to the repository, opened and held.

    Read only. No directory or file is created, renamed or removed.
    """

    chain = boundary.open_chain(bindings, str(REPO_ROOT))
    try:
        _, components = boundary.split_base_path(str(REPO_ROOT))
        assert len(chain.anchors) == len(components) + 1
        assert all(len(anchor.identity) == 64 for anchor in chain.anchors)
        assert len({anchor.identity for anchor in chain.anchors}) == len(
            chain.anchors
        )
        for anchor in chain.anchors:
            boundary.revalidate(bindings, anchor)  # unchanged, so it returns
    finally:
        boundary.close_chain(bindings, chain)
    assert all(anchor.closed for anchor in chain.anchors)


def test_a_closed_anchor_is_refused_rather_than_queried(bindings):
    chain = boundary.open_chain(bindings, str(REPO_ROOT))
    boundary.close_chain(bindings, chain)
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.revalidate(bindings, chain.base)
    assert excinfo.value.args[0] == "ROOT_IDENTITY_CHANGED"


def test_closing_twice_is_a_no_op(bindings):
    chain = boundary.open_chain(bindings, str(REPO_ROOT))
    boundary.close_chain(bindings, chain)
    boundary.close_chain(bindings, chain)  # must not double-close a handle


# --- N3c-1: an unwind must not eat the error that caused it -----------------


def test_a_failing_close_does_not_replace_the_anchor_error(
    bindings, monkeypatch
):
    """The reparse rejection is the finding; CLOSE_FAILED is noise beside it."""

    monkeypatch.setattr(boundary, "_open_directory", lambda *a: 0x1234)
    monkeypatch.setattr(boundary, "_reparse_tag", lambda *a: 0xA000_0003)
    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)

    with pytest.raises(boundary.NativeError) as excinfo:
        boundary._anchor(bindings, "child", None)

    assert excinfo.value.args[0] == "PATH_IS_REPARSE_POINT"
    assert any("CLOSE_FAILED" in note for note in excinfo.value.__notes__)


def test_a_failing_close_does_not_replace_the_chain_error(
    bindings, monkeypatch
):
    """A mid-chain failure survives a cleanup that also fails.

    `open_chain` used to call `close_chain`, which raises; the `CLOSE_FAILED`
    from unwinding arrived at the caller in place of the reason the chain was
    being unwound at all.
    """

    opened: list[boundary.Anchor] = []

    def fake_anchor(_bindings, name, _parent):
        if len(opened) >= 1:
            raise boundary.NativeError("PATH_IS_REPARSE_POINT")
        anchor = boundary.Anchor(_bindings, 0x1234, "identity")
        opened.append(anchor)
        return anchor

    monkeypatch.setattr(boundary, "_anchor", fake_anchor)
    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)

    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.open_chain(bindings, str(REPO_ROOT))

    assert excinfo.value.args[0] == "PATH_IS_REPARSE_POINT"
    assert any("CLOSE_FAILED" in note for note in excinfo.value.__notes__)
    assert opened[0].closed  # attempted, and not retried later


def test_the_quiet_close_still_attempts_every_anchor(bindings, monkeypatch):
    """Stopping at the first failure would leak the handles beneath it."""

    attempts: list[int] = []

    def failing_close(_bindings, handle):
        attempts.append(handle)
        return False

    monkeypatch.setattr(boundary, "_close_handle", failing_close)
    anchors = [
        boundary.Anchor(bindings, handle, f"id{handle}") for handle in (1, 2, 3)
    ]

    failure = boundary._close_chain_quietly(anchors)

    assert failure is not None and failure.args[0] == "CLOSE_FAILED"
    assert attempts == [3, 2, 1]  # reverse acquisition order, none skipped


def test_close_chain_still_raises_when_called_deliberately(
    bindings, monkeypatch
):
    """The quiet variant is for unwinding only, not a general softening."""

    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)
    chain = boundary.PinnedChain(
        [boundary.Anchor(bindings, 0x1234, "identity")]
    )
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.close_chain(bindings, chain)
    assert excinfo.value.args[0] == "CLOSE_FAILED"


def _invoked_exports(source: str) -> set[str]:
    """Every bound export this source can actually invoke.

    Two shapes count, and the first version of this check only saw one:

    * `bindings.kernel32.CloseHandle(handle)` — a direct call;
    * `_guarded(bindings, "CLOSE", bindings.kernel32.CloseHandle, handle)` —
      the export handed to the guard as a callable, which is the *normal* shape
      in this module and contains no `CloseHandle(` text at all.

    Searching for `ntdll.NtCreateFile(` therefore proved nothing: the compliant
    way to call it would never match, so neither would a new violation.
    """

    import ast

    exports = {name for _, name in boundary._Bindings.BOUND}
    invoked: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in exports:
            invoked.add(func.attr)
        for argument in node.args:
            if isinstance(argument, ast.Attribute) and argument.attr in exports:
                invoked.add(argument.attr)
    return invoked


def test_the_invocation_detector_sees_a_guarded_call():
    """Sensitivity check on synthetic source, so nothing is reintroduced here."""

    guarded = (
        "def create(bindings, attrs):\n"
        "    return _guarded(bindings, 'CREATE_FILE',"
        " bindings.ntdll.NtCreateFile, attrs)\n"
    )
    direct = (
        "def create(bindings, attrs):\n"
        "    return bindings.ntdll.NtCreateFile(attrs)\n"
    )
    assert _invoked_exports(guarded) == {"NtCreateFile"}
    assert _invoked_exports(direct) == {"NtCreateFile"}


def test_pinning_a_chain_creates_and_removes_nothing(bindings, tmp_path):
    """N3c-1's operations, still creating nothing now that N3c-2 exists.

    The tranche-wide claim this replaced — that the module invokes no creation
    export at all — was true of N3c-1 and is deliberately false of N3c-2. What
    survives is the narrower statement: pinning a chain touches no object.
    """

    before = sorted(tmp_path.iterdir())
    with boundary.open_chain(bindings, str(REPO_ROOT)):
        pass
    assert sorted(tmp_path.iterdir()) == before


def test_the_volume_export_is_bound_and_still_never_invoked():
    """The one export N3c-2 did not start using, asserted structurally.

    `GetVolumeInformationByHandleW` is bound and reads from a held base handle
    that now exists, so nothing technical stops it being called. It is absent
    because it belongs to a later tranche, and the absence is a choice rather
    than an accident.
    """

    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    bound = {name for _, name in boundary._Bindings.BOUND}
    assert "GetVolumeInformationByHandleW" in bound
    assert "GetVolumeInformationByHandleW" not in _invoked_exports(source)


def test_creation_and_deletion_are_invoked_only_from_the_n3c2_surface():
    """Which functions may touch the creation and deletion exports.

    Naming the callers is the point: a create appearing in a helper nobody
    reviewed for it is exactly the drift this check exists to catch.
    """

    import ast

    source = pathlib.Path(boundary.__file__).read_text(encoding="utf-8")
    restricted = {"NtCreateFile", "WriteFile", "SetFileInformationByHandle"}
    # `remove` delegates to `_mark_deleted`, which is the single place the
    # deletion classes are set — the rollback path uses it too, so there is one
    # deletion implementation rather than two that can drift.
    permitted = {"_create", "_write_all", "_mark_deleted"}

    callers: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            for argument in inner.args:
                if (
                    isinstance(argument, ast.Attribute)
                    and argument.attr in restricted
                ):
                    callers.setdefault(argument.attr, set()).add(node.name)

    assert set(callers) == restricted
    for export, names in callers.items():
        assert names <= permitted, f"{export} reached from {names - permitted}"


# --- N3c-1 rev2: ownership, sentinels, and the actual OS error --------------


def test_the_chain_closes_itself_on_context_exit(bindings):
    """Design: ownership is dropped by a context manager."""

    with boundary.open_chain(bindings, str(REPO_ROOT)) as chain:
        assert not any(anchor.closed for anchor in chain.anchors)
    assert all(anchor.closed for anchor in chain.anchors)


def test_the_context_manager_does_not_swallow_the_body_error(bindings):
    """`__exit__` returns False, so an error inside the block still escapes."""

    with pytest.raises(ZeroDivisionError):
        with boundary.open_chain(bindings, str(REPO_ROOT)) as chain:
            1 / 0
    assert all(anchor.closed for anchor in chain.anchors)


def test_an_anchor_is_its_own_context_manager(bindings):
    with boundary.open_chain(bindings, str(REPO_ROOT)) as chain:
        anchor = chain.anchors[0]
        with anchor:
            assert not anchor.closed
        assert anchor.closed


def test_the_finalizer_releases_a_chain_the_caller_forgot(bindings, monkeypatch):
    """The safety net the design requires, observed rather than assumed."""

    import gc

    closed: list[int] = []
    monkeypatch.setattr(
        boundary,
        "_close_handle",
        lambda _bindings, handle: closed.append(handle) or True,
    )

    def leak():
        chain = boundary.PinnedChain(
            [boundary.Anchor(bindings, 0x4321, "identity")]
        )
        assert chain.base.closed is False

    leak()
    gc.collect()
    assert closed == [0x4321]


def test_the_finalizer_stays_silent_when_the_close_fails(bindings, monkeypatch):
    """A finalizer that raised would print and be ignored anyway."""

    import gc

    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)
    anchor = boundary.Anchor(bindings, 0x4321, "identity")
    del anchor
    gc.collect()  # must not raise CLOSE_FAILED out of __del__


def test_a_success_status_with_an_invalid_handle_is_refused(
    bindings, monkeypatch
):
    """`INVALID_HANDLE_VALUE` is truthy, so a NULL-only test let it through."""

    assert boundary.INVALID_HANDLE_VALUE == 0xFFFF_FFFF_FFFF_FFFF

    def fake_open(_handle_ref, *_args):
        _handle_ref._obj.value = boundary.INVALID_HANDLE_VALUE
        return 0  # STATUS_SUCCESS

    monkeypatch.setattr(bindings.ntdll, "NtOpenFile", fake_open, raising=False)
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary._open_directory(bindings, "\\??\\C:\\", None)
    assert excinfo.value.args[0] == "HANDLE_BOUNDARY_UNAVAILABLE"


def test_a_success_status_with_a_null_handle_is_also_refused(
    bindings, monkeypatch
):
    def fake_open(_handle_ref, *_args):
        _handle_ref._obj.value = None
        return 0

    monkeypatch.setattr(bindings.ntdll, "NtOpenFile", fake_open, raising=False)
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary._open_directory(bindings, "\\??\\C:\\", None)
    assert excinfo.value.args[0] == "HANDLE_BOUNDARY_UNAVAILABLE"


def test_the_missing_read_right_fails_with_access_denied(bindings, monkeypatch):
    """Design evidence 19w, stated as the OS states it.

    Asserting only that the query failed would have been satisfied by any
    failure at all; revision 17 rests on the failure being ERROR_ACCESS_DENIED.
    """

    ERROR_ACCESS_DENIED = 5
    volume_root, _ = boundary.split_base_path(str(REPO_ROOT))

    monkeypatch.setattr(
        boundary,
        "ANCESTOR_ACCESS",
        boundary.FILE_LIST_DIRECTORY | boundary.SYNCHRONIZE,
    )
    handle = boundary._open_directory(bindings, volume_root, None)
    try:
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary._reparse_tag(bindings, handle)
        assert excinfo.value.args[0] == "ROOT_IDENTITY_UNAVAILABLE"
        assert excinfo.value.__notes__ == [
            f"FileAttributeTagInfo: last_error={ERROR_ACCESS_DENIED}"
        ]
    finally:
        assert boundary._close_handle(bindings, handle)


def test_a_failing_close_does_not_replace_a_body_error_on_a_chain(
    bindings, monkeypatch
):
    """Both fail at once: the body error is the finding, the close is a note.

    `__exit__` used to call `close()` unconditionally, so `CLOSE_FAILED` was
    raised out of the `with` and the ValueError never reached the caller.
    """

    chain = boundary.PinnedChain(
        [boundary.Anchor(bindings, 0x1234, "identity")]
    )
    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)

    with pytest.raises(ValueError) as excinfo:
        with chain:
            raise ValueError("the body failed first")

    assert excinfo.value.args[0] == "the body failed first"
    assert any("CLOSE_FAILED" in note for note in excinfo.value.__notes__)
    assert chain.base.closed  # attempted, and not retried afterwards


def test_a_failing_close_does_not_replace_a_body_error_on_an_anchor(
    bindings, monkeypatch
):
    anchor = boundary.Anchor(bindings, 0x1234, "identity")
    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)

    with pytest.raises(ValueError) as excinfo:
        with anchor:
            raise ValueError("the body failed first")

    assert excinfo.value.args[0] == "the body failed first"
    assert any("CLOSE_FAILED" in note for note in excinfo.value.__notes__)
    assert anchor.closed


@pytest.mark.parametrize("owner", ["anchor", "chain"])
def test_a_clean_body_still_reports_a_failed_close(
    bindings, monkeypatch, owner
):
    """No prior error means nothing to mask, so the failure must surface."""

    anchor = boundary.Anchor(bindings, 0x1234, "identity")
    subject = anchor if owner == "anchor" else boundary.PinnedChain([anchor])
    monkeypatch.setattr(boundary, "_close_handle", lambda *a: False)

    with pytest.raises(boundary.NativeError) as excinfo:
        with subject:
            pass
    assert excinfo.value.args[0] == "CLOSE_FAILED"


# --- N3c-2: creation, deletion and the absence probe ------------------------
#
# The real-Windows tests below create and delete objects. Every one of them
# lives under a base the *test* creates and pytest removes; the boundary only
# pins that base, and each test asserts it survives with the identity it was
# pinned with. That split is the owner ruling made executable: a created object
# must be deleted, a borrowed one must never be, and no object may carry both
# obligations.


class _RecordedCreate:
    """Capture `NtCreateFile` arguments without creating anything.

    Returns a failure status, so the call site refuses and no object exists. The
    arguments are what the test is about: reading them off a successful call
    would mean the check only works when the thing already works.
    """

    STATUS_ACCESS_DENIED = -1073741790  # 0xC0000022

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(
        self,
        handle_ref,
        access,
        object_attributes,
        status_block,
        allocation,
        attributes,
        share,
        disposition,
        options,
        ea_buffer,
        ea_length,
    ):
        self.calls.append(
            {
                "access": access,
                "attributes": attributes,
                "share": share,
                "disposition": disposition,
                "options": options,
                "allocation": allocation,
                "ea_buffer": ea_buffer,
                "ea_length": ea_length,
            }
        )
        return self.STATUS_ACCESS_DENIED


@pytest.fixture
def recorded_create(bindings, monkeypatch):
    recorder = _RecordedCreate()
    monkeypatch.setattr(bindings.ntdll, "NtCreateFile", recorder, raising=False)
    return recorder


def _detached_anchor(bindings):
    """An anchor over a handle nothing will ever use, for offline argument tests."""

    return boundary.Anchor(bindings, 0x1234, "identity")


# Copied from revision 17's per-role table, deliberately as literals. Comparing
# the recorded arguments against the module's own constants would pass for any
# self-consistent implementation, including one that changed both sides.
_SPEC = {
    "role2": {
        "access": 0x0001 | 0x0080 | 0x00100000 | 0x00010000 | 0x0100,
        "attributes": 0x00000080,  # FILE_ATTRIBUTE_NORMAL
        "share": 0x00000001 | 0x00000002,
        "disposition": 0x00000002,  # FILE_CREATE
        "options": 0x00000001 | 0x00000020,
    },
    "role3": {
        "access": 0x0002 | 0x0080 | 0x0100 | 0x00010000 | 0x00100000,
        "attributes": 0x00000001,  # FILE_ATTRIBUTE_READONLY
        "share": 0x00000001,
        "disposition": 0x00000002,
        "options": 0x00000040 | 0x00000020,
    },
}


def test_role_2_arguments_are_exactly_the_design_table(bindings, recorded_create):
    with pytest.raises(boundary.NativeError):
        boundary.create_directory(bindings, _detached_anchor(bindings), "dir")

    assert len(recorded_create.calls) == 1
    call = recorded_create.calls[0]
    for field, expected in _SPEC["role2"].items():
        assert call[field] == expected, field
    assert call["allocation"] is None
    assert call["ea_buffer"] is None and call["ea_length"] == 0


def test_role_3_arguments_are_exactly_the_design_table(bindings, recorded_create):
    with pytest.raises(boundary.NativeError):
        boundary.create_file(bindings, _detached_anchor(bindings), "f.bin", b"x")

    assert len(recorded_create.calls) == 1
    call = recorded_create.calls[0]
    for field, expected in _SPEC["role3"].items():
        assert call[field] == expected, field


@pytest.mark.parametrize(
    "constant,replacement",
    [
        ("FILE_ATTRIBUTE_READONLY", 0x00000080),  # the named mutation
        ("CREATED_FILE_SHARE", 0x00000001 | 0x00000002),  # share widened
        ("CREATED_FILE_ACCESS", 0x0002 | 0x00100000),  # DELETE dropped
        # Mutate the derived constant, not its input: `CREATED_FILE_OPTIONS` is
        # folded at import, so patching `FILE_NON_DIRECTORY_FILE` afterwards
        # changes nothing that reaches the call.
        ("CREATED_FILE_OPTIONS", 0x00000001 | 0x00000020),  # as a directory
    ],
)
def test_the_role_3_argument_check_fails_under_mutation(
    bindings, recorded_create, monkeypatch, constant, replacement
):
    """Design evidence 9, offline half: the check must actually fire.

    Each mutation is applied to the production constant and the *real*
    assertion is then re-run and required to fail. An earlier version asserted
    that the recorded value differed from a literal, which is what a broken
    implementation produces — so it passed precisely when it should not have.
    """

    monkeypatch.setattr(boundary, constant, replacement)
    with pytest.raises(boundary.NativeError):
        boundary.create_file(bindings, _detached_anchor(bindings), "f.bin", b"x")

    call = recorded_create.calls[0]
    with pytest.raises(AssertionError):
        for field, expected in _SPEC["role3"].items():
            assert call[field] == expected, field


def test_no_created_role_shares_delete_and_no_borrowed_role_asks_for_delete():
    """Design evidence 19x and 12, asserted against the constants."""

    assert not boundary.ANCESTOR_ACCESS & boundary.DELETE
    assert not boundary.ANCESTOR_SHARE & boundary.FILE_SHARE_DELETE
    assert not boundary.CREATED_DIRECTORY_SHARE & boundary.FILE_SHARE_DELETE
    assert not boundary.CREATED_FILE_SHARE & boundary.FILE_SHARE_DELETE
    assert boundary.ABSENCE_SHARE & boundary.FILE_SHARE_DELETE
    assert boundary.CREATED_DIRECTORY_ACCESS & boundary.DELETE
    assert boundary.CREATED_FILE_ACCESS & boundary.DELETE


@pytest.mark.parametrize(
    "name",
    [
        "a/b",
        "a\\b",
        "..",
        ".",
        "name:stream",
        "trailing.",
        "trailing ",
        "",
        "x" * 256,
        "nul",
        "NUL.txt",
        "com1",
        "LPT9.log",
        "star*",
        "quote\"",
    ],
)
def test_a_refused_name_never_reaches_a_native_call(bindings, monkeypatch, name):
    """Design evidence 4, invalid-path anchor: refusal precedes any native call."""

    def forbidden(*_args, **_kwargs):
        pytest.fail("a refused name reached a native call")

    monkeypatch.setattr(bindings.ntdll, "NtCreateFile", forbidden, raising=False)
    monkeypatch.setattr(bindings.ntdll, "NtOpenFile", forbidden, raising=False)

    parent = _detached_anchor(bindings)
    for operation in (
        lambda: boundary.create_directory(bindings, parent, name),
        lambda: boundary.create_file(bindings, parent, name, b""),
        lambda: boundary.confirm_absent(bindings, parent, name),
    ):
        with pytest.raises(boundary.NativeError) as excinfo:
            operation()
        assert excinfo.value.args[0] == "PATH_INVALID"


def test_a_missing_base_is_not_a_platform_failure(bindings, tmp_path):
    """Design evidence 4, missing-base anchor.

    The parent is controlled and pre-existing, so it can be enumerated; the
    assertion is that the name under it is still absent afterwards.
    """

    absent = tmp_path / "no-such-base"
    before = sorted(tmp_path.iterdir())

    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.open_chain(bindings, str(absent))
    assert excinfo.value.args[0] == "BASE_NOT_FOUND"

    assert sorted(tmp_path.iterdir()) == before
    assert not absent.exists()


@pytest.mark.parametrize("base", ["relative/path", "\\\\server\\share", "CON:"])
def test_an_unusable_base_path_is_refused_before_any_open(
    bindings, monkeypatch, base
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("an invalid base reached a native call")

    monkeypatch.setattr(bindings.ntdll, "NtOpenFile", forbidden, raising=False)
    monkeypatch.setattr(bindings.ntdll, "NtCreateFile", forbidden, raising=False)

    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.open_chain(bindings, base)
    assert excinfo.value.args[0] == "PATH_INVALID"


def test_an_unopenable_base_reports_admissibility_not_absence(
    bindings, monkeypatch, tmp_path
):
    """Design evidence 4, unopenable-base anchor: inventory plus no create."""

    def denied(handle_ref, *_args):
        return _RecordedCreate.STATUS_ACCESS_DENIED

    def forbidden_create(*_args, **_kwargs):
        pytest.fail("a refused base reached the create surface")

    monkeypatch.setattr(bindings.ntdll, "NtOpenFile", denied, raising=False)
    monkeypatch.setattr(
        bindings.ntdll, "NtCreateFile", forbidden_create, raising=False
    )

    before = sorted(tmp_path.iterdir())
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.open_chain(bindings, str(tmp_path))
    assert excinfo.value.args[0] == "BASE_NOT_ADMISSIBLE"
    assert sorted(tmp_path.iterdir()) == before


def test_a_write_reporting_no_progress_is_a_failure(bindings, monkeypatch):
    """Looping on a zero-byte write would spin forever."""

    def zero_progress(_handle, _buffer, _count, written_ref, _overlapped):
        written_ref._obj.value = 0
        return 1

    monkeypatch.setattr(
        bindings.kernel32, "WriteFile", zero_progress, raising=False
    )
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary._write_all(bindings, 0x1234, b"payload")
    assert excinfo.value.args[0] == "MATERIALIZE_WRITE_FAILED"


# --- real Windows, under a test-owned base ----------------------------------


@pytest.fixture
def owned_base(bindings, tmp_path):
    """A base the test creates, and the boundary may only borrow."""

    base = tmp_path / "owned-base"
    base.mkdir()
    yield base


def test_a_created_tree_is_written_removed_and_confirmed_absent(
    bindings, owned_base
):
    payload = b"materialized bytes\n" * 4

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        base_identity = chain.base.identity

        directory = boundary.create_directory(bindings, chain.base, "root-01")
        try:
            leaf = boundary.create_file(bindings, directory, "payload.bin", payload)
            with pytest.raises(PermissionError):
                # Held with FILE_WRITE_DATA and DELETE under a FILE_SHARE_READ
                # mask, so an ordinary opener cannot get in. The bytes are
                # therefore not observable here; that is checked separately by a
                # fixture that owns its own cleanup.
                (owned_base / "root-01" / "payload.bin").read_bytes()

            boundary.remove(bindings, leaf)
            leaf.close()
            boundary.confirm_absent(bindings, directory, "payload.bin")
        finally:
            boundary.remove(bindings, directory)
            directory.close()
        boundary.confirm_absent(bindings, chain.base, "root-01")

        boundary.revalidate(bindings, chain.base)
        assert chain.base.identity == base_identity

    assert owned_base.is_dir()  # borrowed, and still there
    assert sorted(owned_base.iterdir()) == []


def _create_control_leaf(bindings, parent, name):
    """A file created exactly like role 3 but with the NORMAL attribute.

    Built through `_create` so the control travels the same code path, and
    wrapped in a `Leaf` so it is queried through the same surface. An earlier
    version made the control with `pathlib` and read it with `stat()`, which
    left the two sides incomparable: a `file_attributes` that always answered
    "read-only" would have passed.
    """

    handle = boundary._create(
        bindings,
        parent,
        name,
        boundary.CREATED_FILE_ACCESS,
        boundary.CREATED_FILE_SHARE,
        boundary.FILE_ATTRIBUTE_NORMAL,
        boundary.CREATED_FILE_OPTIONS,
    )
    return boundary.Leaf(bindings, handle, "control")


def test_the_created_file_is_read_only_and_the_control_is_not(
    bindings, owned_base
):
    """Design evidence 9, online half: what the kernel retained, with a control.

    The offline half showed what was *requested*. This shows what survived.
    Both files are created the same way and read through the same
    `file_attributes` call, so the only difference between them is the
    attribute — which is what makes the comparison mean anything.
    """

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        leaf = boundary.create_file(bindings, chain.base, "readonly.bin", b"x")
        control = _create_control_leaf(bindings, chain.base, "control.bin")
        try:
            observed = boundary.file_attributes(bindings, leaf)
            control_observed = boundary.file_attributes(bindings, control)
            assert observed & boundary.FILE_ATTRIBUTE_READONLY
            assert not control_observed & boundary.FILE_ATTRIBUTE_READONLY
        finally:
            for held, name in ((leaf, "readonly.bin"), (control, "control.bin")):
                boundary.remove(bindings, held)
                held.close()
                boundary.confirm_absent(bindings, chain.base, name)


def test_the_attribute_comparison_fails_if_the_query_returns_a_constant(
    bindings, owned_base, monkeypatch
):
    """The control is load-bearing, shown by breaking the query.

    With `file_attributes` answering the same word for everything, the two sides
    become equal and the comparison above must fail.
    """

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        leaf = boundary.create_file(bindings, chain.base, "readonly.bin", b"x")
        control = _create_control_leaf(bindings, chain.base, "control.bin")
        try:
            monkeypatch.setattr(
                boundary,
                "file_attributes",
                lambda _bindings, _held: boundary.FILE_ATTRIBUTE_READONLY,
            )
            with pytest.raises(AssertionError):
                assert boundary.file_attributes(bindings, leaf) & (
                    boundary.FILE_ATTRIBUTE_READONLY
                )
                assert not boundary.file_attributes(bindings, control) & (
                    boundary.FILE_ATTRIBUTE_READONLY
                )
        finally:
            monkeypatch.undo()
            for held, name in ((leaf, "readonly.bin"), (control, "control.bin")):
                boundary.remove(bindings, held)
                held.close()
                boundary.confirm_absent(bindings, chain.base, name)


def test_a_read_only_file_is_still_deletable_through_its_own_handle(
    bindings, owned_base
):
    """`IGNORE_READONLY_ATTRIBUTE` is what makes born-read-only survivable."""

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        leaf = boundary.create_file(bindings, chain.base, "locked.bin", b"x")
        assert boundary.file_attributes(bindings, leaf) & (
            boundary.FILE_ATTRIBUTE_READONLY
        )
        boundary.remove(bindings, leaf)
        leaf.close()
        boundary.confirm_absent(bindings, chain.base, "locked.bin")
    assert not (owned_base / "locked.bin").exists()


def test_a_present_name_is_not_confirmed_absent(bindings, owned_base):
    """Only `STATUS_OBJECT_NAME_NOT_FOUND` counts, and success does not."""

    (owned_base / "present.bin").write_bytes(b"x")
    with boundary.open_chain(bindings, str(owned_base)) as chain:
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.confirm_absent(bindings, chain.base, "present.bin")
        assert excinfo.value.args[0] == "CLEANUP_INCOMPLETE"
    (owned_base / "present.bin").unlink()


def test_an_occupied_name_is_refused_rather_than_opened(bindings, owned_base):
    """`FILE_CREATE` is what `O_EXCL` was, without the path lookup."""

    (owned_base / "taken.bin").write_bytes(b"pre-existing")
    with boundary.open_chain(bindings, str(owned_base)) as chain:
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.create_file(bindings, chain.base, "taken.bin", b"ours")
        assert excinfo.value.args[0] == "MATERIALIZE_PATH_EXISTS"
        with pytest.raises(boundary.NativeError):
            boundary.create_directory(bindings, chain.base, "taken.bin")
    assert (owned_base / "taken.bin").read_bytes() == b"pre-existing"
    (owned_base / "taken.bin").unlink()


def test_the_boundary_never_deletes_or_replaces_the_base(bindings, owned_base):
    """The owner ruling, stated as a test.

    A full create-and-cleanup cycle runs, and the base is the same object
    afterwards — not merely a directory with the same name.
    """

    before = owned_base.stat().st_ino
    with boundary.open_chain(bindings, str(owned_base)) as chain:
        pinned = chain.base.identity
        directory = boundary.create_directory(bindings, chain.base, "cycle")
        boundary.remove(bindings, directory)
        directory.close()
        boundary.confirm_absent(bindings, chain.base, "cycle")
        boundary.revalidate(bindings, chain.base)
        assert chain.base.identity == pinned
    assert owned_base.is_dir()
    assert owned_base.stat().st_ino == before


def test_a_held_created_file_is_not_readable_by_an_ordinary_open(
    bindings, owned_base
):
    """Role 3's share mask, observed rather than read off the constant.

    `FILE_SHARE_READ` alone, against a handle holding `FILE_WRITE_DATA` and
    `DELETE`, means no other opener gets in while the leaf is held. The control
    is a plain file in the same directory, which opens without complaint.
    """

    control = owned_base / "control.bin"
    control.write_bytes(b"readable")

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        leaf = boundary.create_file(bindings, chain.base, "held.bin", b"x")
        try:
            with pytest.raises(PermissionError):
                (owned_base / "held.bin").read_bytes()
            assert control.read_bytes() == b"readable"
        finally:
            boundary.remove(bindings, leaf)
            leaf.close()
        boundary.confirm_absent(bindings, chain.base, "held.bin")
    control.unlink()


def test_the_written_bytes_are_the_payload(bindings, owned_base):
    """Characterization fixture, and deliberately not the role 3 lifecycle.

    The production path holds the leaf until it removes it through that same
    handle, and the share mask means the bytes are never observable while it is
    held — so proving what was written requires stepping outside that path. This
    fixture closes the leaf *without* marking it for deletion, reads the file
    with ordinary Python, and unlinks it itself.

    It therefore evidences the write, and nothing about ownership, deletion or
    the cleanup contract. It must not be cited for those.
    """

    payload = bytes(range(256)) * 8 + b"tail"

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        leaf = boundary.create_file(bindings, chain.base, "written.bin", payload)
        leaf.close()  # released, not removed — this is the deviation
    written = owned_base / "written.bin"
    try:
        assert written.read_bytes() == payload
    finally:
        written.chmod(0o600)  # born read-only, so clear it before unlinking
        written.unlink()


def test_a_large_payload_crosses_the_write_chunk_boundary(bindings, owned_base):
    """Same deviation as above, for the multi-chunk path.

    The chunk size is patched down rather than writing a megabyte, so the loop,
    the offset arithmetic and the short-write continuation are all exercised
    without the test depending on how much memory it may allocate.
    """

    payload = bytes(range(256)) * 40  # 10,240 bytes

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        original = boundary.WRITE_CHUNK
        try:
            boundary.WRITE_CHUNK = 1000  # forces eleven passes, last one partial
            leaf = boundary.create_file(bindings, chain.base, "big.bin", payload)
        finally:
            boundary.WRITE_CHUNK = original
        leaf.close()
    written = owned_base / "big.bin"
    try:
        assert written.read_bytes() == payload
    finally:
        written.chmod(0o600)
        written.unlink()


def _without_disposition_ex(bindings, monkeypatch):
    """Make the preferred deletion class unavailable, and only that class.

    Everything else still goes to the real export, so the fallback performs a
    genuine deletion rather than a simulated one.
    """

    real = bindings.kernel32.SetFileInformationByHandle

    def selective(handle, info_class, buffer, size):
        if info_class == boundary.FILE_DISPOSITION_INFO_EX_CLASS:
            return 0
        return real(handle, info_class, buffer, size)

    monkeypatch.setattr(
        bindings.kernel32, "SetFileInformationByHandle", selective, raising=False
    )


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_deletion_completes_through_the_fallback(
    bindings, owned_base, monkeypatch, kind
):
    """Design evidence 10: the fallback path, actually taken.

    Without forcing it, a passing deletion test says nothing about the fallback
    — every deletion would go through `FileDispositionInfoEx` and the older
    path would never run.
    """

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        name = "fallback.bin" if kind == "file" else "fallback-dir"
        if kind == "file":
            held = boundary.create_file(bindings, chain.base, name, b"x")
            assert boundary.file_attributes(bindings, held) & (
                boundary.FILE_ATTRIBUTE_READONLY
            )
        else:
            held = boundary.create_directory(bindings, chain.base, name)

        _without_disposition_ex(bindings, monkeypatch)
        boundary.remove(bindings, held)
        held.close()
        monkeypatch.undo()

        boundary.confirm_absent(bindings, chain.base, name)
    assert not (owned_base / name).exists()


@pytest.mark.parametrize(
    "status",
    [
        0,  # opened successfully: it is still there
        -1073741738,  # STATUS_DELETE_PENDING
        -1073741757,  # STATUS_SHARING_VIOLATION
        -1073741790,  # STATUS_ACCESS_DENIED
    ],
)
def test_only_name_not_found_counts_as_absent(
    bindings, owned_base, monkeypatch, status
):
    """Design evidence 11: the whole matrix, not just the two easy answers.

    Delete-pending in particular reads like success to a careless check — the
    object is on its way out — and is exactly the case where proceeding to the
    parent would be wrong.
    """

    def injected(handle_ref, _access, _attrs, _iosb, _share, _options):
        if status >= 0:
            handle_ref._obj.value = 0x1234
        return status

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        monkeypatch.setattr(
            bindings.kernel32, "CloseHandle", lambda _handle: 1, raising=False
        )
        monkeypatch.setattr(
            bindings.ntdll, "NtOpenFile", injected, raising=False
        )
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.confirm_absent(bindings, chain.base, "anything.bin")
        assert excinfo.value.args[0] == "CLEANUP_INCOMPLETE"
        monkeypatch.undo()


def test_a_short_write_is_continued_rather_than_truncating_the_payload(
    bindings, owned_base, monkeypatch
):
    """Design evidence: short-write continuation, forced rather than hoped for.

    A large payload alone only proves the loop runs more than once. This makes
    every write report less than it was asked for, so the offset arithmetic and
    the continuation both have to be right for the bytes to land.
    """

    payload = bytes(range(256)) * 12  # 3,072 bytes
    real_write = bindings.kernel32.WriteFile
    requests: list[int] = []

    def short(handle, buffer, count, written_ref, overlapped):
        requests.append(count)
        partial = max(1, count // 3)
        return real_write(handle, buffer, partial, written_ref, overlapped)

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        monkeypatch.setattr(
            bindings.kernel32, "WriteFile", short, raising=False
        )
        leaf = boundary.create_file(bindings, chain.base, "short.bin", payload)
        monkeypatch.undo()
        leaf.close()  # released, not removed, so the bytes can be read back

    assert len(requests) > 3  # genuinely many passes, none of them complete
    assert sum(requests) > len(payload)  # each pass re-asked for the remainder
    written = owned_base / "short.bin"
    try:
        assert written.read_bytes() == payload
    finally:
        written.chmod(0o600)
        written.unlink()


# --- rollback: a create that succeeded, then a later step that did not -------


@pytest.mark.parametrize("failing", ["identity", "write"])
def test_a_failure_after_create_leaves_no_object_behind(
    bindings, owned_base, monkeypatch, failing
):
    """Design evidence 1: no residue, and the original error survives.

    Before the rollback existed, a failure between `FILE_CREATE` and the
    returned ownership object left the name on disk with nothing holding it —
    the caller never got an object, so nothing would ever clean it up.
    """

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        before = sorted(owned_base.iterdir())

        if failing == "identity":
            monkeypatch.setattr(
                boundary,
                "_identity_of",
                lambda *_a: (_ for _ in ()).throw(
                    boundary.NativeError("ROOT_IDENTITY_UNAVAILABLE")
                ),
            )
            expected = "ROOT_IDENTITY_UNAVAILABLE"
        else:
            monkeypatch.setattr(
                boundary,
                "_write_all",
                lambda *_a: (_ for _ in ()).throw(
                    boundary.NativeError("MATERIALIZE_WRITE_FAILED")
                ),
            )
            expected = "MATERIALIZE_WRITE_FAILED"

        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.create_file(bindings, chain.base, "doomed.bin", b"x")
        assert excinfo.value.args[0] == expected

        monkeypatch.undo()
        assert sorted(owned_base.iterdir()) == before
        boundary.confirm_absent(bindings, chain.base, "doomed.bin")


def test_a_directory_whose_identity_fails_is_rolled_back(
    bindings, owned_base, monkeypatch
):
    with boundary.open_chain(bindings, str(owned_base)) as chain:
        before = sorted(owned_base.iterdir())
        monkeypatch.setattr(
            boundary,
            "_identity_of",
            lambda *_a: (_ for _ in ()).throw(
                boundary.NativeError("ROOT_IDENTITY_UNAVAILABLE")
            ),
        )
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.create_directory(bindings, chain.base, "doomed-dir")
        assert excinfo.value.args[0] == "ROOT_IDENTITY_UNAVAILABLE"
        monkeypatch.undo()
        assert sorted(owned_base.iterdir()) == before
        boundary.confirm_absent(bindings, chain.base, "doomed-dir")


def test_a_close_failure_during_removal_reports_incomplete_cleanup(
    bindings, monkeypatch
):
    """The design's mapping: during removal the finding is the removal.

    `CLOSE_FAILED` is for releasing the borrowed chain after an otherwise
    successful run. Reporting it here would name the wrong problem: the object
    is delete-pending and may still be there.
    """

    held = boundary.Leaf(bindings, 0x1234, "identity")
    monkeypatch.setattr(boundary, "_mark_deleted", lambda *_a: None)
    monkeypatch.setattr(boundary, "_close_handle", lambda *_a: False)

    boundary.remove(bindings, held)
    with pytest.raises(boundary.NativeError) as excinfo:
        held.close()
    assert excinfo.value.args[0] == "CLEANUP_INCOMPLETE"


def test_a_close_failure_outside_removal_is_still_a_close_failure(
    bindings, monkeypatch
):
    held = boundary.Anchor(bindings, 0x1234, "identity")
    monkeypatch.setattr(boundary, "_close_handle", lambda *_a: False)
    with pytest.raises(boundary.NativeError) as excinfo:
        held.close()
    assert excinfo.value.args[0] == "CLOSE_FAILED"


@pytest.mark.parametrize(
    "status,expected",
    [
        (-1073741771, "MATERIALIZE_PATH_EXISTS"),  # STATUS_OBJECT_NAME_COLLISION
        (-1073741790, "MATERIALIZE_WRITE_FAILED"),  # STATUS_ACCESS_DENIED
        (-1073741757, "MATERIALIZE_WRITE_FAILED"),  # STATUS_SHARING_VIOLATION
        (-1073741823, "MATERIALIZE_WRITE_FAILED"),  # STATUS_UNSUCCESSFUL
    ],
)
def test_only_a_collision_is_reported_as_a_taken_name(
    bindings, monkeypatch, status, expected
):
    """Every creation failure used to answer "the name is taken".

    That tells a caller to pick another name when the parent was deleted
    underneath them, the volume is full, or access was refused.
    """

    monkeypatch.setattr(
        bindings.ntdll, "NtCreateFile", lambda *_a: status, raising=False
    )
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.create_file(bindings, _detached_anchor(bindings), "x.bin", b"")
    assert excinfo.value.args[0] == expected


def test_removal_state_is_set_before_marking_not_after(bindings, monkeypatch):
    """The ordering inside `remove`, pinned by making marking fail.

    With `_mark_deleted` succeeding, an implementation that set `_removing`
    *after* the mark behaves identically, so the existing test passes either
    way. Making the mark raise separates them: the object may already be
    delete-pending, and a close that then fails must report the removal, not
    the handle.
    """

    held = boundary.Leaf(bindings, 0x1234, "identity")

    def failing_mark(*_args):
        raise boundary.NativeError("CLEANUP_INCOMPLETE")

    monkeypatch.setattr(boundary, "_mark_deleted", failing_mark)
    with pytest.raises(boundary.NativeError) as excinfo:
        boundary.remove(bindings, held)
    assert excinfo.value.args[0] == "CLEANUP_INCOMPLETE"
    assert held._removing is True  # set before the call that raised

    monkeypatch.setattr(boundary, "_close_handle", lambda *_a: False)
    with pytest.raises(boundary.NativeError) as close_error:
        held.close()
    assert close_error.value.args[0] == "CLEANUP_INCOMPLETE"


class _DispositionSpy:
    """Record every information class set, and optionally refuse some of them."""

    def __init__(self, real, refuse=()):
        self.real = real
        self.refuse = set(refuse)
        self.classes: list[int] = []

    def __call__(self, handle, info_class, buffer, size):
        self.classes.append(info_class)
        if info_class in self.refuse:
            return 0
        return self.real(handle, info_class, buffer, size)


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_the_preferred_disposition_is_the_one_normally_used(
    bindings, owned_base, monkeypatch, kind
):
    """rev17 evidence: preferred, and *only* preferred, on the ordinary path.

    A deletion test that merely succeeds cannot tell the two paths apart, so a
    silent fall-through to the older class would stay green. This asserts the
    fallback classes were never touched.
    """

    real = bindings.kernel32.SetFileInformationByHandle
    spy = _DispositionSpy(real)
    monkeypatch.setattr(
        bindings.kernel32, "SetFileInformationByHandle", spy, raising=False
    )

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        name = "preferred.bin" if kind == "file" else "preferred-dir"
        held = (
            boundary.create_file(bindings, chain.base, name, b"x")
            if kind == "file"
            else boundary.create_directory(bindings, chain.base, name)
        )
        boundary.remove(bindings, held)
        held.close()
        monkeypatch.undo()
        boundary.confirm_absent(bindings, chain.base, name)

    assert spy.classes == [boundary.FILE_DISPOSITION_INFO_EX_CLASS]
    assert boundary.FILE_DISPOSITION_INFO_CLASS not in spy.classes
    assert boundary.FILE_BASIC_INFO_CLASS not in spy.classes


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_the_fallback_sequence_is_exactly_clear_then_dispose(
    bindings, owned_base, monkeypatch, kind
):
    """rev17 evidence: which classes the fallback uses, and in what order.

    Clearing the attribute has to come first — the older disposition class has
    no flag that ignores read-only, which is the whole reason the sequence has
    two steps.
    """

    real = bindings.kernel32.SetFileInformationByHandle
    spy = _DispositionSpy(real, refuse={boundary.FILE_DISPOSITION_INFO_EX_CLASS})
    monkeypatch.setattr(
        bindings.kernel32, "SetFileInformationByHandle", spy, raising=False
    )

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        name = "fb.bin" if kind == "file" else "fb-dir"
        held = (
            boundary.create_file(bindings, chain.base, name, b"x")
            if kind == "file"
            else boundary.create_directory(bindings, chain.base, name)
        )
        boundary.remove(bindings, held)
        held.close()
        monkeypatch.undo()
        boundary.confirm_absent(bindings, chain.base, name)

    assert spy.classes == [
        boundary.FILE_DISPOSITION_INFO_EX_CLASS,
        boundary.FILE_BASIC_INFO_CLASS,
        boundary.FILE_DISPOSITION_INFO_CLASS,
    ]
    assert not (owned_base / name).exists()


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_both_dispositions_failing_leaves_the_object_and_reports_incomplete(
    bindings, owned_base, monkeypatch, kind
):
    """rev17 evidence: the case where deletion simply does not happen.

    Untested until now. The object must still be there afterwards — reporting
    `CLEANUP_INCOMPLETE` while the name had in fact gone would be the more
    dangerous failure, because a caller would stop looking.
    """

    real = bindings.kernel32.SetFileInformationByHandle
    spy = _DispositionSpy(
        real,
        refuse={
            boundary.FILE_DISPOSITION_INFO_EX_CLASS,
            boundary.FILE_DISPOSITION_INFO_CLASS,
        },
    )

    with boundary.open_chain(bindings, str(owned_base)) as chain:
        name = "stuck.bin" if kind == "file" else "stuck-dir"
        held = (
            boundary.create_file(bindings, chain.base, name, b"x")
            if kind == "file"
            else boundary.create_directory(bindings, chain.base, name)
        )
        monkeypatch.setattr(
            bindings.kernel32, "SetFileInformationByHandle", spy, raising=False
        )
        with pytest.raises(boundary.NativeError) as excinfo:
            boundary.remove(bindings, held)
        assert excinfo.value.args[0] == "CLEANUP_INCOMPLETE"
        monkeypatch.undo()

        assert (owned_base / name).exists()  # still there, as reported
        with pytest.raises(boundary.NativeError) as absent_error:
            boundary.confirm_absent(bindings, chain.base, name)
        assert absent_error.value.args[0] == "CLEANUP_INCOMPLETE"

        # The test created it, so the test clears it before leaving.
        held._removing = False
        boundary.remove(bindings, held)
        held.close()
        boundary.confirm_absent(bindings, chain.base, name)

    assert spy.classes == [
        boundary.FILE_DISPOSITION_INFO_EX_CLASS,
        boundary.FILE_BASIC_INFO_CLASS,
        boundary.FILE_DISPOSITION_INFO_CLASS,
    ]


@pytest.mark.parametrize(
    "kind,expected_stage",
    [("file", "CREATE_FILE"), ("directory", "CREATE_DIRECTORY")],
)
def test_a_failed_create_reports_the_stage_it_was_in(
    bindings, monkeypatch, kind, expected_stage
):
    """The stage carried into the diagnostic, per role.

    It was hard-coded to `CREATE_FILE` before, and every test still passed: a
    directory failure produced a file's stage ordinal, which is exactly the
    field a crash dump would be read for.
    """

    stages: list[str] = []
    real_guarded = boundary._guarded

    def recording(bindings_, stage, call, *args):
        stages.append(stage)
        return real_guarded(bindings_, stage, call, *args)

    monkeypatch.setattr(boundary, "_guarded", recording)
    monkeypatch.setattr(
        bindings.ntdll,
        "NtCreateFile",
        lambda *_a: -1073741790,  # STATUS_ACCESS_DENIED
        raising=False,
    )

    parent = _detached_anchor(bindings)
    with pytest.raises(boundary.NativeError):
        if kind == "file":
            boundary.create_file(bindings, parent, "x.bin", b"")
        else:
            boundary.create_directory(bindings, parent, "x-dir")

    # Both the create and the status translation carry the same stage, and no
    # other stage appears between them.
    assert stages == [expected_stage, expected_stage]


def test_n3c2_did_not_move_availability(bindings):
    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False


def test_n3c1_did_not_move_availability(bindings):
    """Pinning a chain is not admission, and does not pretend to be."""

    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False


def test_n3b_did_not_move_availability(bindings):
    boundary.runtime_facts(bindings)
    assert boundary.handle_boundary_available() is False
    assert boundary.ACTIVE is False
