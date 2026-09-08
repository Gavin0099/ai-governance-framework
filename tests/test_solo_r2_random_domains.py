from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap

import pytest

from governance_tools import solo_r2_random_domains as domains


KNOWN_ENTROPY = bytes(range(32))
KNOWN_ATTEMPT_HANDLE = (
    "36c358856c1dae9a447b6efa70c2405b1129807a9d89a9a354fa2a6bec1f065d"
)
KNOWN_SCORING_LABEL = (
    "2d2df2a4a05accbed775f9a0ab889bc17a7459a68eac39b9fa8cec29fecdde0c"
)


def test_known_vectors_and_domain_separation() -> None:
    attempt = domains.derive_opaque_identifier(
        domains.ATTEMPT_HANDLE_DOMAIN, KNOWN_ENTROPY
    )
    label = domains.derive_opaque_identifier(
        domains.SCORING_LABEL_DOMAIN, KNOWN_ENTROPY
    )

    assert attempt == KNOWN_ATTEMPT_HANDLE
    assert label == KNOWN_SCORING_LABEL
    assert attempt != label
    assert domains.derive_order_bit(domains.ARM_ORDER_DOMAIN, KNOWN_ENTROPY) == 1
    assert domains.arm_order_from_entropy(KNOWN_ENTROPY) == (
        "TREATMENT",
        "CONTROL",
    )
    assert domains.presentation_order_bit_from_entropy(KNOWN_ENTROPY) == 0


@pytest.mark.parametrize(
    "domain_tag",
    ["", "solo-r2-unknown-v1", domains.ARM_ORDER_DOMAIN, None],
)
def test_opaque_generator_rejects_invalid_domain(domain_tag: object) -> None:
    with pytest.raises(domains.RandomDomainError) as caught:
        domains.derive_opaque_identifier(domain_tag, KNOWN_ENTROPY)  # type: ignore[arg-type]
    assert caught.value.code == domains.INVALID_RANDOM_DOMAIN


@pytest.mark.parametrize(
    "entropy",
    [b"", bytes(31), bytes(33), bytearray(32), None],
)
def test_generators_require_exact_bytes32(entropy: object) -> None:
    with pytest.raises(domains.RandomDomainError) as caught:
        domains.derive_order_bit(domains.ARM_ORDER_DOMAIN, entropy)  # type: ignore[arg-type]
    assert caught.value.code == domains.INVALID_RANDOM_ENTROPY


def test_collision_is_terminal_and_has_no_replacement() -> None:
    registry = domains.OpaqueIdentifierRegistry()

    first = registry.admit(domains.ATTEMPT_HANDLE_DOMAIN, KNOWN_ENTROPY)
    assert first == KNOWN_ATTEMPT_HANDLE
    assert registry.count == 1

    with pytest.raises(domains.RandomDomainError) as caught:
        registry.admit(domains.ATTEMPT_HANDLE_DOMAIN, KNOWN_ENTROPY)
    assert caught.value.code == domains.OPAQUE_ID_COLLISION
    assert registry.count == 1


def test_generator_input_surface_is_structurally_closed() -> None:
    assert tuple(inspect.signature(domains.derive_opaque_identifier).parameters) == (
        "domain_tag",
        "entropy",
    )
    assert tuple(inspect.signature(domains.derive_order_bit).parameters) == (
        "domain_tag",
        "entropy",
    )

    inspected = (
        domains.derive_opaque_identifier,
        domains.derive_order_bit,
        domains._digest_for_domain,
        domains._validate_domain,
        domains._validate_entropy,
    )
    tree = ast.parse(
        "\n".join(textwrap.dedent(inspect.getsource(fn)) for fn in inspected)
    )
    referenced_names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
    prohibited = {
        "arm",
        "treatment_state",
        "realized_order",
        "event_seq",
        "timestamp_utc",
        "pair_id",
        "slot",
        "parity",
        "counter",
        "os",
        "random",
        "secrets",
        "time",
        "uuid",
    }
    assert referenced_names.isdisjoint(prohibited)


def test_sampling_is_explicitly_regression_only() -> None:
    attempt_ids: set[str] = set()
    scoring_ids: set[str] = set()
    for index in range(128):
        entropy = hashlib.sha256(index.to_bytes(4, "big")).digest()
        attempt_ids.add(
            domains.derive_opaque_identifier(domains.ATTEMPT_HANDLE_DOMAIN, entropy)
        )
        scoring_ids.add(
            domains.derive_opaque_identifier(domains.SCORING_LABEL_DOMAIN, entropy)
        )

    assert len(attempt_ids) == 128
    assert len(scoring_ids) == 128
    assert attempt_ids.isdisjoint(scoring_ids)
    assert domains.SAMPLING_ROLE == "REGRESSION_ONLY_NOT_PROOF"
