from __future__ import annotations

import dataclasses
import logging
import pprint
from dataclasses import dataclass, field, fields
from typing import Mapping

import pytest

import gate3_final_message_runner_integration as integration
import gate3_private_rendering as private_rendering
import gate3_route_v2 as route
import gate3_route_v2_codex as codex


pytest_plugins = ("pytester",)

CANARY = b"PRIVATE_STDOUT_CANARY"
STDERR_CANARY = b"PRIVATE_STDERR_CANARY"

# The design named three types.  The census found two more on its first run:
# CodexExecRunner holds auth_payload and prompt, and RunnerIntegrationCoordinator
# holds the workspace baseline and its admitted snapshot.  Both are in scope.
IN_SCOPE = (
    route.SyntheticResult,
    codex._ContainedResult,
    integration.InjectedContainedResult,
    codex.CodexExecRunner,
    integration.RunnerIntegrationCoordinator,
)


def synthetic() -> route.SyntheticResult:
    return route.SyntheticResult(
        exit_code=0, stdout=CANARY, final_message=CANARY, workspace=None
    )


def contained() -> codex._ContainedResult:
    return codex._ContainedResult(
        returncode=0,
        stdout=CANARY,
        stderr=STDERR_CANARY,
        timed_out=False,
        tree_terminated=True,
    )


def injected() -> integration.InjectedContainedResult:
    return integration.InjectedContainedResult(
        returncode=0, stdout=CANARY, stderr=STDERR_CANARY
    )


SAMPLES = (synthetic, contained, injected)


# --- rendering --------------------------------------------------------------


@pytest.mark.parametrize("build", SAMPLES)
def test_every_rendering_path_is_closed(build) -> None:
    value = build()
    rendered = [
        repr(value),
        str(value),
        f"{value}",
        f"{value!r}",
        f"{value:>40}",
        "%s" % (value,),
        "{}".format(value),
        pprint.pformat(value),
    ]
    for text in rendered:
        assert CANARY.decode() not in text
        assert STDERR_CANARY.decode() not in text
    assert repr(value) == f"<{type(value).__name__} redacted>"


@pytest.mark.parametrize("build", SAMPLES)
def test_logging_does_not_render_the_payload(build, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("gate3.private").debug("value=%s", build())
    assert CANARY.decode() not in caplog.text


@pytest.mark.parametrize("build", SAMPLES)
def test_token_is_constant_across_payloads(build) -> None:
    short = repr(build())
    value = build()
    grown = dataclasses.replace(value, stdout=CANARY * 100)
    assert repr(grown) == short


@pytest.mark.parametrize("build", SAMPLES)
def test_traceback_locals_do_not_render_the_payload(build) -> None:
    import traceback

    def boom(value: object) -> None:
        raise RuntimeError("closed")

    try:
        boom(build())
    except RuntimeError:
        rendered = "".join(traceback.format_exc())
    assert CANARY.decode() not in rendered


# --- pytest comparator ------------------------------------------------------


@pytest.mark.parametrize("build", SAMPLES)
def test_private_fields_are_excluded_from_the_dataclass_comparator(build) -> None:
    value = build()
    private = {
        item.name
        for item in fields(value)
        if private_rendering.has_private_marker(item)
    }
    assert private, "each in-scope type must mark at least one private field"
    for item in fields(value):
        if item.name in private:
            assert item.compare is False
            assert item.repr is False


def test_assertion_failure_report_carries_no_payload(pytester) -> None:
    """The payload is bound to a name, which is the practice the design requires."""

    here = str(__import__("pathlib").Path(__file__).parent)
    pytester.makepyfile(
        "import sys\n"
        f"sys.path.insert(0, r{here!r})\n"
        "import gate3_final_message_runner_integration as integration\n"
        "\n"
        "def test_fails():\n"
        "    payload = bytes.fromhex('50524956415445')  # 'PRIVATE'\n"
        "    payload += b'_STDOUT_CANARY'\n"
        "    left = integration.InjectedContainedResult(0, payload, b'')\n"
        "    right = integration.InjectedContainedResult(0, b'DIFFERENT', b'')\n"
        "    assert left == right\n"
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    assert "PRIVATE_STDOUT_CANARY" not in "\n".join(result.outlines)


def test_inline_literal_in_an_assert_is_still_revealed(pytester) -> None:
    """The documented residual, asserted rather than implied.

    No property of the type closes this: pytest renders the assert expression's
    own source.  It is closed only by binding the payload to a name first.
    """

    here = str(__import__("pathlib").Path(__file__).parent)
    pytester.makepyfile(
        "import sys\n"
        f"sys.path.insert(0, r{here!r})\n"
        "import gate3_final_message_runner_integration as integration\n"
        "\n"
        "def test_fails():\n"
        "    right = integration.InjectedContainedResult(0, b'DIFFERENT', b'')\n"
        "    assert integration.InjectedContainedResult(\n"
        "        0, b'INLINE_LITERAL_CANARY', b''\n"
        "    ) == right\n"
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    assert "INLINE_LITERAL_CANARY" in "\n".join(result.outlines)


# --- equality and hash, reproduced not redefined ----------------------------


@dataclass(frozen=True)
class ReferenceSynthetic:
    exit_code: int
    stdout: bytes | None
    final_message: bytes | None
    workspace: Mapping[str, bytes] | None
    exit_classification: str | None = None
    stdout_capture: str | None = None
    final_capture: str | None = None
    workspace_capture: str | None = None


REFERENCE_FIELD_NAMES = (
    "exit_code",
    "stdout",
    "final_message",
    "workspace",
    "exit_classification",
    "stdout_capture",
    "final_capture",
    "workspace_capture",
)


def test_reference_inventory_matches_production() -> None:
    """A field added without updating the reference inventory fails here."""

    assert tuple(item.name for item in fields(route.SyntheticResult)) == (
        REFERENCE_FIELD_NAMES
    )
    assert tuple(item.name for item in fields(ReferenceSynthetic)) == (
        REFERENCE_FIELD_NAMES
    )


@pytest.mark.parametrize("index", range(len(REFERENCE_FIELD_NAMES)))
def test_equality_matches_the_generated_reference_field_by_field(index: int) -> None:
    values = {
        "exit_code": 0,
        "stdout": CANARY,
        "final_message": None,
        "workspace": None,
        "exit_classification": "zero",
        "stdout_capture": "captured",
        "final_capture": "captured",
        "workspace_capture": "captured",
    }
    name = REFERENCE_FIELD_NAMES[index]
    altered = dict(values)
    altered[name] = 1 if name == "exit_code" else b"OTHER" if isinstance(
        values[name], bytes
    ) else ("other" if values[name] is not None else "now-set")

    production_equal = route.SyntheticResult(**values) == route.SyntheticResult(**altered)
    reference_equal = ReferenceSynthetic(**values) == ReferenceSynthetic(**altered)
    assert production_equal is reference_equal is False


def test_equal_objects_hash_equally_without_claiming_the_converse() -> None:
    left = route.SyntheticResult(0, CANARY, None, None)
    right = route.SyntheticResult(0, CANARY, None, None)
    assert left == right and hash(left) == hash(right)
    assert hash(left) == hash(ReferenceSynthetic(0, CANARY, None, None))


def test_synthetic_result_stays_unhashable_with_a_dict_workspace() -> None:
    production = route.SyntheticResult(0, CANARY, None, {"a": b"b"})
    reference = ReferenceSynthetic(0, CANARY, None, {"a": b"b"})
    with pytest.raises(TypeError) as production_error:
        hash(production)
    with pytest.raises(TypeError) as reference_error:
        hash(reference)
    assert str(production_error.value) == str(reference_error.value)


def test_the_other_two_types_remain_hashable() -> None:
    assert isinstance(hash(contained()), int)
    assert isinstance(hash(injected()), int)


# --- census -----------------------------------------------------------------


IN_SCOPE_MODULES = (route, codex, integration)


@pytest.mark.parametrize("module", IN_SCOPE_MODULES)
def test_no_flagged_type_sits_outside_the_boundary(module) -> None:
    assert private_rendering.outside_boundary(module) == set()


def test_marker_census_catches_a_non_bytes_private_field() -> None:
    class Probe:
        pass

    @dataclass(frozen=True, repr=False, eq=False)
    class NonceHolder(private_rendering.PrivateRendering):
        tag: str
        nonce: object = private_rendering.private_field()

    Probe.NonceHolder = NonceHolder  # type: ignore[attr-defined]
    assert NonceHolder in private_rendering.types_with_private_fields(Probe)
    assert NonceHolder not in private_rendering.types_with_bytes_hints(Probe)


@pytest.mark.parametrize(
    "annotation",
    ["bytes", "bytes | None", "Mapping[str, bytes]"],
)
def test_bytes_backstop_resolves_postponed_annotations(annotation: str) -> None:
    """The backstop must survive postponed annotations, unions and generics."""

    import types as _types

    import sys as _sys

    module = _types.ModuleType("probe_module")
    _sys.modules["probe_module"] = module
    lines = [
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "from typing import Mapping",
        "@dataclass(frozen=True)",
        "class Unmarked:",
        f"    payload: {annotation}",
    ]
    try:
        exec(compile("\n".join(lines), "<probe>", "exec"), module.__dict__)
        assert module.Unmarked in private_rendering.types_with_bytes_hints(module)
    finally:
        _sys.modules.pop("probe_module", None)


def test_census_cannot_see_an_unmarked_non_bytes_private_field() -> None:
    """The residual, asserted rather than implied."""

    class Probe:
        pass

    @dataclass(frozen=True)
    class Invisible:
        secret: object

    Probe.Invisible = Invisible  # type: ignore[attr-defined]
    assert Invisible not in private_rendering.types_with_private_fields(Probe)
    assert Invisible not in private_rendering.types_with_bytes_hints(Probe)
    assert Invisible not in private_rendering.outside_boundary(Probe)


# --- documented non-goals ---------------------------------------------------


# --- the wiring must not relax the constructor ------------------------------
#
# `private_field()` carries no default, so nothing about the rendering boundary
# required one on the fields below. Adding defaults there turned a missing
# argument into a silent safe-looking value — "did not time out", "the process
# tree was fully terminated", "there is no cleanup callback" — which is the
# wrong direction for exactly those three.


@pytest.mark.parametrize(
    "missing", ["timed_out", "tree_terminated", "stdout", "stderr", "returncode"]
)
def test_contained_result_requires_every_field(missing: str) -> None:
    complete = dict(
        returncode=0,
        stdout=b"out",
        stderr=b"err",
        timed_out=False,
        tree_terminated=True,
    )
    complete.pop(missing)
    with pytest.raises(TypeError) as excinfo:
        codex._ContainedResult(**complete)
    assert missing in str(excinfo.value)


@pytest.mark.parametrize("field_name", ["timed_out", "tree_terminated"])
def test_the_process_state_flags_have_no_default(field_name: str) -> None:
    """Asserted against the dataclass, not inferred from a TypeError."""

    declared = {item.name: item for item in fields(codex._ContainedResult)}
    item = declared[field_name]
    assert item.default is dataclasses.MISSING
    assert item.default_factory is dataclasses.MISSING


def test_the_coordinator_requires_a_cleanup_callable() -> None:
    declared = {item.name: item for item in fields(integration.RunnerIntegrationCoordinator)}
    cleanup = declared["cleanup"]
    assert cleanup.default is dataclasses.MISSING
    assert cleanup.default_factory is dataclasses.MISSING


def test_the_production_contained_result_call_passes_the_flags() -> None:
    """The one production construction site, checked structurally.

    A restored requirement only helps if the caller was not relying on the
    default it used to get.
    """

    import ast
    import pathlib as _pathlib

    source = (_pathlib.Path(codex.__file__)).read_text(encoding="utf-8")
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_ContainedResult"
    ]
    assert len(calls) == 1
    supplied = {keyword.arg for keyword in calls[0].keywords}
    assert supplied == {
        "returncode",
        "stdout",
        "stderr",
        "timed_out",
        "tree_terminated",
    }
    assert calls[0].args == []  # keyword-only at the call site, so order cannot drift


def test_asdict_still_exposes_the_payload() -> None:
    """Explicit non-goal, asserted so it cannot be mistaken for closed."""

    @dataclass(frozen=True, repr=False, eq=False)
    class Container(private_rendering.PrivateRendering):
        inner: integration.InjectedContainedResult

    exposed = dataclasses.asdict(Container(injected()))
    assert exposed["inner"]["stdout"] == CANARY


def test_direct_field_access_still_works() -> None:
    assert injected().stdout == CANARY
    assert route.SyntheticResult(0, CANARY, None, None).stdout == CANARY
