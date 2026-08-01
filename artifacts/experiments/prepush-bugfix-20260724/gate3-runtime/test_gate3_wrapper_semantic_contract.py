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


def test_no_tolerated_field_has_a_preregistered_value_yet() -> None:
    assert set(contract.TOLERATED_FIELD_VALUES) == {"timeout_ms"}
    assert all(
        value is None for value in contract.TOLERATED_FIELD_VALUES.values()
    )


def test_every_tolerable_field_declares_a_range() -> None:
    assert set(contract.TOLERATED_FIELD_RANGES) == set(
        contract.TOLERATED_FIELD_VALUES
    )
    for low, high in contract.TOLERATED_FIELD_RANGES.values():
        assert isinstance(low, int) and not isinstance(low, bool)
        assert isinstance(high, int) and not isinstance(high, bool)
        assert 0 < low <= high


# --- the declaration is validated, not only the input ---------------------


@pytest.mark.parametrize(
    ("label", "declared"),
    [
        ("bool_true", True),
        ("bool_false", False),
        ("zero", 0),
        ("negative", -1),
        ("above_range", 3_600_001),
        ("float", 120000.0),
        ("string", "120000"),
        ("none_explicit", None),
    ],
)
def test_an_invalid_declaration_leaves_the_field_untolerated(
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    declared: object,
) -> None:
    """A misconfiguration must narrow acceptance, never widen it.

    bool is the one that would actually slip: it is a subclass of int, so a
    naive isinstance check passes and True then matches a literal 1.
    """
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": declared}
    )
    assert contract.preregistered_value("timeout_ms") is None, label
    for literal in ("1", "0", "120000", "-1"):
        result = _evaluate(_with_timeout(literal))
        assert result["accepted"] is False, (label, literal)
        assert result["reason"] == "tolerated_field_value_rejected"
        assert result["detail"] == "no usable preregistered value"


def test_a_field_without_a_declared_range_cannot_be_tolerated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    monkeypatch.setattr(contract, "TOLERATED_FIELD_RANGES", {})
    assert contract.preregistered_value("timeout_ms") is None


@pytest.mark.parametrize(
    ("label", "bounds"),
    [
        ("string_bounds", ("1", "3600000")),
        ("single_element", (1,)),
        ("three_elements", (1, 10, 100)),
        ("not_a_tuple", 1),
        ("list_not_tuple", [1, 3600000]),
        ("none", None),
        ("low_is_zero", (0, 10)),
        ("low_above_high", (10, 1)),
        ("bool_low", (True, 10)),
        ("bool_high", (1, True)),
        ("float_bounds", (1.0, 10.0)),
    ],
)
def test_a_malformed_range_declaration_refuses_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    bounds: object,
) -> None:
    """A broken config must narrow acceptance, not crash the analyzer.

    Unpacking the range before checking its shape turned a misconfiguration
    into a TypeError or ValueError out of the function that was asked to judge
    a wrapper.
    """
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_RANGES", {"timeout_ms": bounds}
    )
    assert contract.preregistered_value("timeout_ms") is None, label
    result = _evaluate(_with_timeout("120000"))
    assert result["accepted"] is False, label
    assert result["reason"] == "tolerated_field_value_rejected", label


# --- only ASCII decimal digits count as digits ----------------------------


@pytest.mark.parametrize(
    ("label", "literal"),
    [
        ("full_width_tail", "1２００００"),
        ("arabic_indic_tail", "1٢٠٠٠٠"),
        ("full_width_whole", "１２００００"),
        ("devanagari_tail", "1२००००"),
        ("nd_superscript", "1²2⁰⁰⁰"),
    ],
)
def test_non_ascii_digits_cannot_impersonate_the_preregistered_value(
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    literal: str,
) -> None:
    """Python's \\d spans Unicode, and int() parses those digits too.

    Each of these evaluates to a number a naive check would compare equal to
    the preregistered one. Accepting them would be text normalization widening
    the route by accident.
    """
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    result = _evaluate(_with_timeout(literal))
    assert result["accepted"] is False, label
    assert result["reason"] == "tolerated_field_value_rejected", label


def test_the_literal_pattern_itself_is_ascii_only() -> None:
    for literal in ("1２０", "１２", "1٢٠"):
        assert contract._INTEGER_LITERAL_RE.fullmatch(literal) is None
    for literal in ("0", "1", "120000", "3600000"):
        assert contract._INTEGER_LITERAL_RE.fullmatch(literal)


@pytest.mark.parametrize("declared", [1, 120000, 3_600_000])
def test_a_valid_declaration_is_accepted_at_its_bounds(
    monkeypatch: pytest.MonkeyPatch,
    declared: int,
) -> None:
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": declared}
    )
    assert contract.preregistered_value("timeout_ms") == declared
    assert _reason(_with_timeout(str(declared))) == "accepted"


# --- only one numeric spelling is admitted --------------------------------


@pytest.mark.parametrize(
    "literal",
    ["+120000", "0120000", "00120000", "1_20_000", "0x1D4C0", "120000.",
     "1.2e5", " +120000"],
)
def test_alternative_spellings_of_the_right_number_are_refused(
    monkeypatch: pytest.MonkeyPatch,
    literal: str,
) -> None:
    """Same value, different spelling. Not a form the route emits."""
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    result = _evaluate(_with_timeout(literal))
    assert result["accepted"] is False, literal
    assert result["reason"] == "tolerated_field_value_rejected"


# --- the envelope must be validated end to end ----------------------------
#
# Finding one call and reading its argument says nothing about what surrounds
# it. Each of these has a correct-looking middle.


def _call() -> str:
    return (
        f"tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"workdir:{json.dumps(WORKSPACE)}}})"
    )


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("leading_statement", f"doSomething();\nconst r = await {_call()};"
         " text(r);\n"),
        ("trailing_statement", f"const r = await {_call()}; text(r);"
         " cleanup();\n"),
        ("wrong_consumer", f"const r = await {_call()}; consume(r);\n"),
        ("no_consumer", f"const r = await {_call()};\n"),
        ("truncated", f"const r = await {_call()}"),
        ("consumer_of_other_variable",
         f"const r = await {_call()}; text(other);\n"),
        ("unclosed_text", f"text(await {_call()};\n"),
        ("assigned_but_awaited_elsewhere",
         f"let r; r = await {_call()}; text(r);\n"),
    ],
)
def test_an_unvalidated_envelope_is_refused(label: str, source: str) -> None:
    result = _evaluate(source)
    assert result["accepted"] is False, label
    assert result["reason"] in {
        "envelope_not_validated",
        "not_single_frozen_call",
    }, label


def test_only_route_validated_envelopes_can_reach_field_checks() -> None:
    """A refusal reason about fields implies the envelope already passed."""
    source = f"doSomething();\nconst r = await {_call()}; text(r);\n"
    assert _reason(source) == "envelope_not_validated"


# --- a tolerated field needs an exact value, not just a name --------------


def _with_timeout(value: str) -> str:
    return (
        f"const r = await tools.shell_command({{command:{json.dumps(COMMAND)},"
        f"timeout_ms:{value},workdir:{json.dumps(WORKSPACE)}}}); text(r)\n"
    )


@pytest.mark.parametrize(
    "value",
    ["-1", "0", "999999999999", '"not-a-number"', "computeTimeout()",
     "true", "120000.5", "0x1E848", "null"],
)
def test_naming_a_field_tolerated_does_not_admit_arbitrary_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Name-only tolerance would accept every one of these."""
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    result = _evaluate(_with_timeout(value))
    assert result["accepted"] is False, value
    assert result["reason"] == "tolerated_field_value_rejected"
    assert result["fields"] == ["timeout_ms"]


def test_a_tolerated_field_is_inert_without_a_preregistered_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    result = _evaluate(_with_timeout("120000"))
    assert result["reason"] == "tolerated_field_value_rejected"
    assert result["detail"] == "no usable preregistered value"


def test_the_exact_preregistered_value_is_the_only_one_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    assert _reason(_with_timeout("120000")) == "accepted"
    assert _reason(_with_timeout(" 120000 ")) == "accepted"
    assert _reason(_with_timeout("120001")) == (
        "tolerated_field_value_rejected"
    )


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
        f"const r = await tools.shell_command({json.dumps(COMMAND)}); text(r)\n"
    ) == "argument_not_object"
    # An argument bound to a variable beforehand is refused earlier still: the
    # extra statement means the envelope itself is not one the route validates.
    assert _reason(
        "const a = {command:'x'}; const r = await tools.shell_command(a);"
        " text(r)\n"
    ) == "envelope_not_validated"


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


# --- review proof-of-concept regressions ----------------------------------
#
# Verbatim from the review that found the contract accepted them. Kept as
# their own test so a future refactor of the envelope or value checks cannot
# quietly re-open either hole.

_POC_CALL = (
    'tools.shell_command({command:"git rev-parse HEAD",'
    'workdir:"C:/workspace"})'
)


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("statement_before_wrapper",
         f"doSomething();\nconst r = await {_POC_CALL};\ntext(r);\n"),
        ("result_passed_to_another_consumer",
         f"const r = await {_POC_CALL};\nconsume(r);\n"),
        ("wrapper_without_a_consumer", f"const r = await {_POC_CALL}\n"),
    ],
)
def test_envelope_proof_of_concepts_stay_refused(
    label: str,
    source: str,
) -> None:
    result = _evaluate(source)
    assert result["accepted"] is False, label
    assert result["reason"] == "envelope_not_validated", label


@pytest.mark.parametrize(
    "value", ["-1", "0", "999999999999", '"not-a-number"', "computeTimeout()"]
)
def test_value_proof_of_concepts_stay_refused(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Each of these was accepted when timeout_ms was tolerated by name."""
    monkeypatch.setattr(contract, "TOLERATED_FIELDS", ("timeout_ms",))
    monkeypatch.setattr(
        contract, "TOLERATED_FIELD_VALUES", {"timeout_ms": 120000}
    )
    result = _evaluate(_with_timeout(value))
    assert result["accepted"] is False, value
    assert result["reason"] == "tolerated_field_value_rejected", value


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
