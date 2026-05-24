"""
Regression fixture test: canonical gate-input digest must not drift.

Any change to _build_canonical_gate_input (field ordering, normalization,
bool coercion, json.dumps separators, sort_keys, encoding) will change these
digests. A failure here means the promotion_gate_contract_version must be
bumped and the fixture updated deliberately — NOT silently patched.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_control_summary import _build_canonical_gate_input

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "promotion_gate_digest_v0_1.json"


def _digest(gate_input: dict) -> str:
    return hashlib.sha256(
        json.dumps(gate_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_file_exists():
    assert FIXTURE_PATH.exists(), f"Regression fixture missing: {FIXTURE_PATH}"


def test_contract_version_matches():
    fixture = _load_fixture()
    assert fixture["_contract_version"] == "0.1"


def test_canonical_digests_stable():
    """
    For each fixture case, recompute the digest via _build_canonical_gate_input
    and assert it matches the frozen value.

    Failure = canonicalization logic changed without a version bump.
    """
    fixture = _load_fixture()
    failures = []

    for case in fixture["cases"]:
        name = case["name"]
        inputs = case["inputs"]
        expected_digest = case["digest"]

        gate_input = _build_canonical_gate_input(
            signal_profile=inputs.get("signal_profile", {}),
            task_provenance=inputs.get("task_provenance", {}),
            runtime=inputs.get("runtime", {}),
            requested_promoted=inputs.get("requested_promoted", False),
        )
        actual_digest = _digest(gate_input)

        if actual_digest != expected_digest:
            failures.append(
                f"  case={name!r}\n"
                f"    expected: {expected_digest}\n"
                f"    actual:   {actual_digest}\n"
                f"    gate_input: {json.dumps(gate_input, sort_keys=True)}"
            )

    assert not failures, (
        "Canonical gate-input digest regression — promotion_gate_contract_version must be bumped:\n"
        + "\n".join(failures)
    )


def test_canonical_gate_input_fields_present():
    """The canonical gate input must contain exactly the expected top-level keys."""
    gate_input = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted=False,
    )
    expected_keys = {
        "task_provenance_status",
        "requested_promoted",
        "runtime_promoted_reported",
        "runtime_public_api_diff_reported",
        "signal_profile",
    }
    assert set(gate_input.keys()) == expected_keys, (
        f"Unexpected gate_input keys: {set(gate_input.keys()) ^ expected_keys}"
    )


def test_unknown_fields_excluded_from_digest():
    """Extra fields on signal_profile entries must not appear in canonical output."""
    gate_input = _build_canonical_gate_input(
        signal_profile={
            "some.signal": {
                "signal_class": "enforcement",
                "decision_effect": "routing",
                "unexpected_extra": "should_be_dropped",
            }
        },
        task_provenance={"status": "", "extra_field": "ignored"},
        runtime={"promoted_reported": True, "other": "ignored"},
        requested_promoted=True,
    )
    profile_entry = gate_input["signal_profile"]["some.signal"]
    assert "unexpected_extra" not in profile_entry, "Unknown signal_profile fields must be excluded from digest input"
    assert set(profile_entry.keys()) == {"signal_class", "decision_effect"}


def test_bool_normalization_int_true():
    """Integer 1 must normalize to True — digest must match requested_promoted=True case."""
    gate_int = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted=1,
    )
    gate_bool = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted=True,
    )
    assert _digest(gate_int) == _digest(gate_bool), "Integer 1 and True must produce same digest"


def test_bool_normalization_string_false():
    """String 'false' must normalize to False."""
    gate_str = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted="false",
    )
    gate_bool = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted=False,
    )
    assert _digest(gate_str) == _digest(gate_bool), "String 'false' and False must produce same digest"


def test_signal_profile_ordering_invariant():
    """Insertion order of signal_profile keys must not affect digest."""
    gate_ab = _build_canonical_gate_input(
        signal_profile={
            "a.signal": {"signal_class": "enforcement", "decision_effect": "routing"},
            "b.signal": {"signal_class": "advisory", "decision_effect": "routing"},
        },
        task_provenance={},
        runtime={},
        requested_promoted=False,
    )
    gate_ba = _build_canonical_gate_input(
        signal_profile={
            "b.signal": {"signal_class": "advisory", "decision_effect": "routing"},
            "a.signal": {"signal_class": "enforcement", "decision_effect": "routing"},
        },
        task_provenance={},
        runtime={},
        requested_promoted=False,
    )
    assert _digest(gate_ab) == _digest(gate_ba), "Signal profile key insertion order must not affect digest"


def test_none_task_provenance_status_normalizes_to_empty():
    """None status must normalize to '' — same digest as missing status."""
    gate_none = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={"status": None},
        runtime={},
        requested_promoted=False,
    )
    gate_missing = _build_canonical_gate_input(
        signal_profile={},
        task_provenance={},
        runtime={},
        requested_promoted=False,
    )
    assert _digest(gate_none) == _digest(gate_missing), "None and missing status must produce same digest"
