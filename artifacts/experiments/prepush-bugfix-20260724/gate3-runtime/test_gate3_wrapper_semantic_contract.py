"""Tests for the proposed semantic-equivalence contract.

The contract is a proposal. These tests are what a reviewer reads to decide
whether it is safe to wire it into acceptance, so they are written as claims
about the contract rather than as coverage of the implementation.

Synthetic inputs only. Nothing here reads a corpus or invokes a session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402
import gate3_wrapper_semantic_contract as contract  # noqa: E402

WORKSPACE = "C:/workspace"
COMMAND = "git rev-parse HEAD"


def _evaluate(source: str) -> dict[str, object]:
    return contract.evaluate(source, expected_workspace=WORKSPACE)


def _reason(source: str) -> str:
    return _evaluate(source)["reason"]


def _frozen() -> str:
    return (
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)}}}); text(r)\n"
    )


# --- the contract is not wired into acceptance ----------------------------


def test_contract_is_not_reachable_from_the_live_route() -> None:
    """A proposal must not change what the route admits by being imported."""
    source = Path(live.__file__).read_text(encoding="utf-8")
    assert "gate3_wrapper_semantic_contract" not in source
    assert "semantic_contract" not in source


def test_tolerated_fields_is_empty_by_default() -> None:
    """Adding a name here widens the route. It must not happen silently."""
    assert contract.TOLERATED_FIELDS == ()


# --- what the contract accepts --------------------------------------------


def test_the_frozen_shape_is_accepted() -> None:
    assert _reason(_frozen()) == "accepted"
    assert live.SHELL_WRAPPER_RE.fullmatch(_frozen())


@pytest.mark.parametrize(
    ("label", "source"),
    [
        (
            "spacing",
            f"const r = await tools.shell_command({{ command: "
            f"{json.dumps(COMMAND)} , workdir: {json.dumps(WORKSPACE)} }}); "
            "text(r)\n",
        ),
        (
            "key_order",
            f"const r = await tools.shell_command({{workdir:"
            f"{json.dumps(WORKSPACE)},command:{json.dumps(COMMAND)}}}); "
            "text(r)\n",
        ),
        (
            "quoted_keys",
            f'const r = await tools.shell_command({{"command":'
            f'{json.dumps(COMMAND)},"workdir":{json.dumps(WORKSPACE)}}}); '
            "text(r)\n",
        ),
        (
            "variable_name",
            f"const outcome = await tools.shell_command({{command:"
            f"{json.dumps(COMMAND)},workdir:{json.dumps(WORKSPACE)}}}); "
            "text(outcome)\n",
        ),
        (
            "trailing_semicolon",
            f"const r = await tools.shell_command({{command:"
            f"{json.dumps(COMMAND)},workdir:{json.dumps(WORKSPACE)}}}); "
            "text(r);\n",
        ),
        (
            "direct_text_await",
            f"text(await tools.shell_command({{command:"
            f"{json.dumps(COMMAND)},workdir:{json.dumps(WORKSPACE)}}}));\n",
        ),
        (
            "crlf",
            f"const r = await tools.shell_command({{command:"
            f"{json.dumps(COMMAND)},workdir:{json.dumps(WORKSPACE)}}}); "
            "text(r)\r\n",
        ),
    ],
)
def test_cosmetic_differences_are_accepted(label: str, source: str) -> None:
    """Each of these runs the same command in the same place."""
    assert _reason(source) == "accepted", label


def test_every_cosmetic_form_accepted_here_is_rejected_today() -> None:
    """Establish that the contract is a widening, not a restatement."""
    variants = [
        f"const r = await tools.shell_command({{ command: "
        f"{json.dumps(COMMAND)} , workdir: {json.dumps(WORKSPACE)} }}); "
        "text(r)\n",
        f"const r = await tools.shell_command({{workdir:"
        f"{json.dumps(WORKSPACE)},command:{json.dumps(COMMAND)}}}); text(r)\n",
    ]
    for source in variants:
        assert _reason(source) == "accepted"
        assert not live.SHELL_WRAPPER_RE.fullmatch(source)


# --- what the contract refuses, and under which name ----------------------


def test_privilege_affecting_fields_are_refused_by_name() -> None:
    for field, value in (
        ("sandbox_permissions", "[]"),
        ("prefix_rule", json.dumps("git")),
        ("login", "true"),
        ("justification", json.dumps("needed")),
    ):
        source = (
            f"const r = await tools.shell_command({{command:"
            f"{json.dumps(COMMAND)},workdir:{json.dumps(WORKSPACE)},"
            f"{field}:{value}}}); text(r)\n"
        )
        result = _evaluate(source)
        assert result["reason"] == "privilege_affecting_field", field
        assert result["fields"] == [field]


def test_an_execution_bound_is_refused_as_an_extra_field() -> None:
    """The dominant real-world rejection, and the open owner decision.

    It is refused as extra_field rather than privilege_affecting_field, so a
    reviewer can see it is a different question from a sandbox grant.
    """
    source = (
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"timeout_ms:120000,workdir:{json.dumps(WORKSPACE)}}}); text(r)\n"
    )
    result = _evaluate(source)
    assert result["reason"] == "extra_field"
    assert result["fields"] == ["timeout_ms"]


def test_unknown_fields_are_refused(_unused: None = None) -> None:
    source = (
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)},brand_new_field:1}}); text(r)\n"
    )
    assert _reason(source) == "extra_field"


def test_multiple_calls_and_out_of_route_tools_are_refused() -> None:
    call = (
        f"await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)}}})"
    )
    assert _reason(f"const a = {call}; const b = {call}; text(a+b)\n") == (
        "not_single_frozen_call"
    )
    assert _reason(
        "const r = await tools.update_plan({plan:[]}); text(r)\n"
    ) == "not_single_frozen_call"
    assert _reason("text('nothing')\n") == "not_single_frozen_call"


def test_a_missing_core_field_is_refused() -> None:
    source = (
        f"const r = await tools.shell_command({{command:"
        f"{json.dumps(COMMAND)}}}); text(r)\n"
    )
    result = _evaluate(source)
    assert result["reason"] == "core_field_missing"
    assert result["missing"] == ["workdir"]


def test_a_duplicate_field_is_refused_rather_than_last_one_winning() -> None:
    source = (
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)},command:{json.dumps('rm -rf /')}}}); "
        "text(r)\n"
    )
    assert _reason(source) == "duplicate_field"


def test_a_non_object_argument_is_refused() -> None:
    assert _reason(
        "const a = {command:'x'}; const r = await tools.shell_command(a);"
        " text(r)\n"
    ) == "argument_not_object"
    assert _reason(
        f"const r = await tools.shell_command({json.dumps(COMMAND)}); text(r)\n"
    ) == "argument_not_object"


def test_computed_values_do_not_slip_through_as_an_object() -> None:
    """An object the contract cannot fully read must not read as clean."""
    source = (
        "const r = await tools.shell_command({command:cmd(),workdir:"
        + json.dumps(WORKSPACE)
        + "}); text(r)\n"
    )
    assert _reason(source) in {"value_rejected_by_route", "argument_not_object"}


# --- the route's own validation still applies ------------------------------


def test_the_routes_command_validation_is_not_bypassed() -> None:
    """Cosmetic tolerance must not become tolerance of the command itself."""
    source = (
        "const r = await tools.shell_command({ command: "
        + json.dumps("git add calc.py; git commit -m chained")
        + " , workdir: "
        + json.dumps(WORKSPACE)
        + " }); text(r)\n"
    )
    assert _reason(source) == "value_rejected_by_route"


def test_a_workdir_outside_the_workspace_is_refused() -> None:
    source = (
        "const r = await tools.shell_command({ command: "
        + json.dumps(COMMAND)
        + " , workdir: "
        + json.dumps("C:/elsewhere")
        + " }); text(r)\n"
    )
    assert _reason(source) == "value_rejected_by_route"


def test_a_tool_token_inside_the_command_string_is_not_a_second_call() -> None:
    """It reaches command validation, so it was read as one call, not two.

    The command itself is then refused on its own merits, which is the route's
    existing judgement and not the contract's business.
    """
    source = (
        "const r = await tools.shell_command({ command: "
        + json.dumps("echo await tools.shell_command({})")
        + " , workdir: "
        + json.dumps(WORKSPACE)
        + " }); text(r)\n"
    )
    assert _reason(source) == "value_rejected_by_route"


# --- verdict shape ---------------------------------------------------------


def test_every_verdict_uses_a_declared_reason() -> None:
    sources = [
        _frozen(),
        "text('nothing')\n",
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)},timeout_ms:1}}); text(r)\n",
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)},login:true}}); text(r)\n",
        f"const r = await tools.shell_command({json.dumps(COMMAND)}); text(r)\n",
    ]
    for source in sources:
        result = _evaluate(source)
        assert result["reason"] in contract.REFUSAL_REASONS
        assert result["accepted"] is (result["reason"] == "accepted")
        assert result["schema"] == contract.CONTRACT_SCHEMA


def test_evaluate_never_raises_on_hostile_input() -> None:
    for source in [
        "",
        "{",
        "await tools.shell_command({",
        "const r = await tools.shell_command({command:'\\'}); text(r)\n",
        "\x00\x01\x02",
        "await tools.shell_command(" + "{" * 200,
    ]:
        result = _evaluate(source)
        assert result["accepted"] is False
        assert result["reason"] in contract.REFUSAL_REASONS
