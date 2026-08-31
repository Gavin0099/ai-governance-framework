from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from uuid import uuid4

import pytest

from governance_tools import solo_r2_blind_scoring_bundle as bundle
from governance_tools import solo_r2_random_domains as random_domains


REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_KEYS = {
    "schema_version",
    "artifact_type",
    "evaluation_id",
    "pair_id",
    "slot",
    "rubric_id",
    "presentation_order",
    "outputs",
}
OUTPUT_KEYS = {"presentation_key", "output_payload"}


def _label(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _valid_bundle(*, entropy: bytes = bytes(range(32))) -> dict[str, object]:
    return bundle.build_blind_scoring_bundle(
        evaluation_id=str(uuid4()),
        pair_id="r2-pair-synthetic",
        slot="R2-SHAKEDOWN",
        rubric_id="rubric-v1",
        outputs_by_label={
            _label("label-a"): "first identity-stripped output",
            _label("label-b"): "second identity-stripped output",
        },
        presentation_entropy=entropy,
    )


def test_exact_l09_keysets_cardinality_and_round_trip() -> None:
    value = _valid_bundle()
    encoded = bundle.encode_blind_scoring_bundle(value)
    parsed = bundle.parse_blind_scoring_bundle(encoded)

    assert parsed == value
    assert set(parsed) == BUNDLE_KEYS
    assert len(parsed["presentation_order"]) == 2
    assert len(set(parsed["presentation_order"])) == 2
    assert len(parsed["outputs"]) == 2
    assert all(set(output) == OUTPUT_KEYS for output in parsed["outputs"])
    assert [output["presentation_key"] for output in parsed["outputs"]] == parsed[
        "presentation_order"
    ]
    assert encoded.endswith(b"\n")
    assert b"\r" not in encoded
    assert not encoded.startswith(b"\xef\xbb\xbf")


def test_builder_uses_only_presentation_entropy_for_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bytes] = []

    def observe(entropy: bytes) -> int:
        calls.append(entropy)
        return 1

    monkeypatch.setattr(
        bundle, "presentation_order_bit_from_entropy", observe
    )
    entropy = bytes(reversed(range(32)))
    value = _valid_bundle(entropy=entropy)

    assert calls == [entropy]
    assert value["presentation_order"] == sorted(
        [_label("label-a"), _label("label-b")], reverse=True
    )


def test_presentation_sampling_is_regression_only_not_proof() -> None:
    observed: set[tuple[str, ...]] = set()
    for index in range(64):
        entropy = hashlib.sha256(index.to_bytes(4, "big")).digest()
        value = _valid_bundle(entropy=entropy)
        observed.add(tuple(value["presentation_order"]))

    assert len(observed) == 2
    assert bundle.SAMPLING_ROLE == "REGRESSION_ONLY_NOT_PROOF"


def test_builder_signature_has_no_execution_or_lifecycle_order_input() -> None:
    parameters = set(inspect.signature(bundle.build_blind_scoring_bundle).parameters)
    assert parameters == {
        "evaluation_id",
        "pair_id",
        "slot",
        "rubric_id",
        "outputs_by_label",
        "presentation_entropy",
    }
    assert parameters.isdisjoint(
        {
            "execution_order",
            "realized_order",
            "arm",
            "attempt_handle",
            "event_seq",
            "timestamp_utc",
            "ledger",
            "chronology",
        }
    )


def test_import_graph_excludes_controller_crypto_ledger_and_secret_sources() -> None:
    source_path = Path(bundle.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert imported == {
        "__future__",
        "json",
        "re",
        "typing",
        "unicodedata",
        "uuid",
        "governance_tools.solo_r2_random_domains",
    }
    assert all(
        token not in module_name
        for module_name in imported
        for token in (
            "cryptography",
            "solo_r2_controller_state",
            "solo_attempt_ledger",
            "pathlib",
            "subprocess",
            "os",
        )
    )
    assert importlib.util.find_spec("cryptography") is not None


@pytest.mark.parametrize(
    "field",
    [
        "attempt_handle",
        "event_seq",
        "timestamp_utc",
        "filesystem_path",
        "output_hash",
        "attempt_commit",
        "result_branch",
        "arm",
        "skill_identity",
        "first_marker",
        "second_marker",
        "execution_order",
        "sealed_package_digest",
    ],
)
def test_every_top_level_lifecycle_or_git_join_field_is_rejected(field: str) -> None:
    value = _valid_bundle()
    value[field] = "sentinel"
    with pytest.raises(bundle.BlindScoringBundleError) as caught:
        bundle.validate_blind_scoring_bundle(value)
    assert caught.value.code == bundle.BUNDLE_SCHEMA_FAILURE


@pytest.mark.parametrize(
    "field",
    [
        "attempt_handle",
        "timestamp_utc",
        "path",
        "hash",
        "commit",
        "arm",
        "first",
        "second",
    ],
)
def test_every_output_level_join_field_is_rejected(field: str) -> None:
    value = _valid_bundle()
    value["outputs"][0][field] = "sentinel"  # type: ignore[index]
    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.validate_blind_scoring_bundle(value)


def _json_escape_ascii(value: str) -> str:
    return "".join(f"\\u{ord(character):04x}" for character in value)


def _fullwidth_ascii(value: str) -> str:
    return "".join(chr(ord(character) + 0xFEE0) for character in value)


@pytest.mark.parametrize(
    "payload",
    [
        _label("public-attempt-handle"),
        f"attempt_handle={_label('public-attempt-handle')}",
        json.dumps(
            {"attempt_handle": _label("public-attempt-handle")},
            separators=(",", ":"),
        ),
        _label("public-attempt-handle").upper(),
        _json_escape_ascii(_label("public-attempt-handle")),
        _json_escape_ascii(_json_escape_ascii(_label("public-attempt-handle"))),
        _fullwidth_ascii(_label("public-attempt-handle")),
        "timestamp_utc=2026-08-31T12:34:56Z",
        'arm:"CONTROL"',
    ],
)
def test_payload_rejects_lifecycle_identity_material_and_wrappers(
    payload: str,
) -> None:
    labels = (_label("label-a"), _label("label-b"))
    with pytest.raises(bundle.BlindScoringBundleError) as caught:
        bundle.build_blind_scoring_bundle(
            evaluation_id=str(uuid4()),
            pair_id="r2-pair-synthetic",
            slot="R2-SHAKEDOWN",
            rubric_id="rubric-v1",
            outputs_by_label={labels[0]: "ordinary", labels[1]: payload},
            presentation_entropy=bytes(range(32)),
        )
    assert caught.value.code == bundle.BUNDLE_SCHEMA_FAILURE

    value = _valid_bundle()
    value["outputs"][0]["output_payload"] = payload  # type: ignore[index]
    manually_encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.parse_blind_scoring_bundle(manually_encoded)


def test_payload_identity_grammar_does_not_reject_near_miss_text() -> None:
    value = _valid_bundle()
    value["outputs"][0]["output_payload"] = "f" * 63  # type: ignore[index]
    assert bundle.validate_blind_scoring_bundle(value) is value


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("rubric_id"),
        lambda value: value.update({"presentation_order": [_label("label-a")]}),
        lambda value: value.update({"presentation_order": [_label("label-a")] * 2}),
        lambda value: value.update({"outputs": value["outputs"][:1]}),
        lambda value: value["outputs"][0].update({"presentation_key": _label("other")}),
        lambda value: value.update({"slot": "Pair0"}),
    ],
)
def test_missing_duplicate_mismatch_and_invalid_values_are_rejected(mutation) -> None:
    value = _valid_bundle()
    mutation(value)
    with pytest.raises(bundle.BlindScoringBundleError) as caught:
        bundle.validate_blind_scoring_bundle(value)
    assert str(caught.value) == bundle.BUNDLE_SCHEMA_FAILURE


@pytest.mark.parametrize(
    "outputs",
    [
        {_label("only-one"): "payload"},
        {_label("one"): "payload", "not-a-label": "payload"},
        {_label("one"): "payload", _label("two"): ""},
        {_label("one"): "payload", 7: "payload"},
    ],
)
def test_builder_requires_exactly_two_valid_labels_and_outputs(
    outputs: dict[str, str],
) -> None:
    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.build_blind_scoring_bundle(
            evaluation_id=str(uuid4()),
            pair_id="pair",
            slot="A1",
            rubric_id="rubric-v1",
            outputs_by_label=outputs,
            presentation_entropy=bytes(32),
        )


def test_builder_rejects_invalid_presentation_entropy_with_bundle_safe_error() -> None:
    with pytest.raises(bundle.BlindScoringBundleError) as caught:
        bundle.build_blind_scoring_bundle(
            evaluation_id=str(uuid4()),
            pair_id="pair",
            slot="A1",
            rubric_id="rubric-v1",
            outputs_by_label={
                _label("one"): "first",
                _label("two"): "second",
            },
            presentation_entropy=bytes(31),
        )
    assert caught.value.code == bundle.BUNDLE_SCHEMA_FAILURE


def test_parser_rejects_duplicate_keys_and_noncanonical_encoding() -> None:
    value = _valid_bundle()
    encoded = bundle.encode_blind_scoring_bundle(value)
    duplicate = encoded[:-2] + b',"slot":"A1"}\n'
    pretty = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode(
        "utf-8"
    ) + b"\n"

    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.parse_blind_scoring_bundle(duplicate)
    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.parse_blind_scoring_bundle(pretty)


def test_scorer_round_trip_has_no_controller_secret_or_join_identity() -> None:
    secret = "controller-secret-" + uuid4().hex
    value = _valid_bundle()
    encoded = bundle.encode_blind_scoring_bundle(value)
    parsed = bundle.parse_blind_scoring_bundle(encoded)

    assert secret.encode("utf-8") not in encoded
    assert set(parsed) == BUNDLE_KEYS
    assert "attempt_handle" not in encoded.decode("utf-8")
    assert "CONTROL" not in encoded.decode("utf-8")
    assert "TREATMENT" not in encoded.decode("utf-8")


def test_bundle_failure_paths_create_no_repo_artifact() -> None:
    prospective = REPO_ROOT / "blind-scoring-bundle.synthetic.json"
    assert not prospective.exists()
    invalid = copy.deepcopy(_valid_bundle())
    invalid["attempt_handle"] = _label("forbidden")
    with pytest.raises(bundle.BlindScoringBundleError):
        bundle.encode_blind_scoring_bundle(invalid)
    assert not prospective.exists()
