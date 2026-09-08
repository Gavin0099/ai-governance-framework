#!/usr/bin/env python3
"""Pure, domain-separated randomness primitives for Solo R2.

The digest generators intentionally accept only a frozen domain tag and an
already-drawn 32-byte entropy value.  CSPRNG access and evaluation state live
at later controller boundaries, not in these functions.
"""

from __future__ import annotations

import hashlib
from typing import Final


ENTROPY_BYTES: Final = 32

ATTEMPT_HANDLE_DOMAIN: Final = "solo-r2-attempt-handle-v1"
SCORING_LABEL_DOMAIN: Final = "solo-r2-scoring-label-v1"
ARM_ORDER_DOMAIN: Final = "solo-r2-arm-order-v1"
PRESENTATION_ORDER_DOMAIN: Final = "solo-r2-presentation-order-v1"

OPAQUE_ID_DOMAINS: Final = frozenset(
    {ATTEMPT_HANDLE_DOMAIN, SCORING_LABEL_DOMAIN}
)
ORDER_DOMAINS: Final = frozenset(
    {ARM_ORDER_DOMAIN, PRESENTATION_ORDER_DOMAIN}
)

SAMPLING_ROLE: Final = "REGRESSION_ONLY_NOT_PROOF"

INVALID_RANDOM_DOMAIN: Final = "INVALID_RANDOM_DOMAIN / STOP"
INVALID_RANDOM_ENTROPY: Final = "INVALID_RANDOM_ENTROPY / STOP"
OPAQUE_ID_COLLISION: Final = "OPAQUE_ID_COLLISION / STOP"


class RandomDomainError(RuntimeError):
    """Fail-closed error carrying only a fixed, non-secret reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validate_domain(domain_tag: str, allowed: frozenset[str]) -> None:
    if type(domain_tag) is not str or domain_tag not in allowed:
        raise RandomDomainError(INVALID_RANDOM_DOMAIN)


def _validate_entropy(entropy: bytes) -> None:
    if type(entropy) is not bytes or len(entropy) != ENTROPY_BYTES:
        raise RandomDomainError(INVALID_RANDOM_ENTROPY)


def _digest_for_domain(domain_tag: str, entropy: bytes) -> bytes:
    _validate_entropy(entropy)
    return hashlib.sha256(domain_tag.encode("utf-8") + b"\x00" + entropy).digest()


def derive_opaque_identifier(domain_tag: str, entropy: bytes) -> str:
    """Return one lowercase SHA-256 identifier for an admitted opaque domain."""

    _validate_domain(domain_tag, OPAQUE_ID_DOMAINS)
    return _digest_for_domain(domain_tag, entropy).hex()


def derive_order_bit(domain_tag: str, entropy: bytes) -> int:
    """Return the frozen low-bit binary-order decision for an order domain."""

    _validate_domain(domain_tag, ORDER_DOMAINS)
    return _digest_for_domain(domain_tag, entropy)[0] & 1


def arm_order_from_entropy(entropy: bytes) -> tuple[str, str]:
    """Apply the E05 binary-order result to the two arm names."""

    if derive_order_bit(ARM_ORDER_DOMAIN, entropy) == 0:
        return ("CONTROL", "TREATMENT")
    return ("TREATMENT", "CONTROL")


def presentation_order_bit_from_entropy(entropy: bytes) -> int:
    """Return an order bit independent from the arm-order domain."""

    return derive_order_bit(PRESENTATION_ORDER_DOMAIN, entropy)


class OpaqueIdentifierRegistry:
    """Evaluation-local collision guard with no retry or replacement path."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    @property
    def count(self) -> int:
        return len(self._seen)

    def admit(self, domain_tag: str, entropy: bytes) -> str:
        identifier = derive_opaque_identifier(domain_tag, entropy)
        if identifier in self._seen:
            raise RandomDomainError(OPAQUE_ID_COLLISION)
        self._seen.add(identifier)
        return identifier
