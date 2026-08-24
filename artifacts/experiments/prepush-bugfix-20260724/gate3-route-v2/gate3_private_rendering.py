"""Structural rendering boundary for types holding private payloads.

Rendering happens on failure — an assertion, a traceback, a debug print added
while diagnosing — which is when discipline is least likely to hold.  This
module makes accidental disclosure structurally impossible rather than
forbidden by convention.

It closes rendering, not access.  ``vars()``, ``__dict__``,
``dataclasses.asdict()``, direct field reads and a debugger all still expose the
payload.  **This is not a confidentiality guarantee.**
"""

from __future__ import annotations

import types
import typing
from dataclasses import Field, dataclass, fields, is_dataclass
from typing import Any, Mapping


PRIVATE_METADATA_KEY = "private"


def private_field(**kwargs: object) -> Any:
    """Declare a field holding a private payload.

    ``compare=False`` keeps the value out of pytest's dataclass comparator,
    which reads ``dataclasses.fields()`` and prints a per-field diff without
    consulting ``__repr__``.  ``repr=False`` removes it from any generated
    repr.  The metadata marker is what the census reads, and it works for
    payloads that are not bytes-shaped.
    """

    from dataclasses import field as _field

    metadata = dict(kwargs.pop("metadata", {}) or {})  # type: ignore[arg-type]
    metadata[PRIVATE_METADATA_KEY] = True
    return _field(compare=False, repr=False, metadata=metadata, **kwargs)  # type: ignore[arg-type]


class PrivateRendering:
    """Constant-token rendering plus generated-equivalent equality.

    ``__repr__``, ``__str__`` and ``__format__`` are all required: overriding
    ``__repr__`` alone leaves ``str()`` falling back to it, and an explicit
    format spec still routes through ``__format__``.

    The token is constant.  It carries no field, length, count or digest,
    because a length is itself a private observation.

    Equality and hashing are derived from ``dataclasses.fields()`` rather than
    hand-listed, so they reproduce what ``eq=True`` would have generated and
    cannot drift when a field is added later.  A type that already raises on
    ``hash()`` — such as one holding a plain ``dict`` — keeps raising, because
    the tuple it hashes contains the same unhashable value.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} redacted>"

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, format_spec: str) -> str:
        return self.__repr__()

    def _field_values(self) -> tuple[object, ...]:
        return tuple(getattr(self, item.name) for item in fields(self))

    def __eq__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return NotImplemented
        return self._field_values() == other._field_values()

    def __hash__(self) -> int:
        return hash(self._field_values())


def _hint_mentions_bytes(hint: object) -> bool:
    if hint is bytes:
        return True
    origin = typing.get_origin(hint)
    if origin is not None or isinstance(hint, types.UnionType):
        return any(_hint_mentions_bytes(arg) for arg in typing.get_args(hint))
    return False


def _resolved_hints(candidate: type) -> Mapping[str, object]:
    """Resolve postponed annotations; unresolvable hints are reported empty."""

    try:
        return typing.get_type_hints(candidate)
    except Exception:
        return {}


def _dataclasses_in(module: object) -> list[type]:
    found: list[type] = []
    for name in dir(module):
        value = getattr(module, name, None)
        if isinstance(value, type) and is_dataclass(value):
            found.append(value)
    return found


def has_private_marker(item: Field) -> bool:
    return bool(item.metadata.get(PRIVATE_METADATA_KEY, False))


def types_with_private_fields(module: object) -> set[type]:
    """Primary census: any dataclass owning a marked field, whatever its type."""

    return {
        candidate
        for candidate in _dataclasses_in(module)
        if any(has_private_marker(item) for item in fields(candidate))
    }


def types_with_bytes_hints(module: object) -> set[type]:
    """Backstop census: a payload field whose author forgot the marker.

    Resolves postponed annotations and walks unions, aliases and nested
    generics.  It cannot see a private field that is not bytes-shaped, which is
    why the marker is primary.
    """

    found: set[type] = set()
    for candidate in _dataclasses_in(module):
        hints = _resolved_hints(candidate)
        names = {item.name for item in fields(candidate)}
        if any(
            _hint_mentions_bytes(hint) for name, hint in hints.items() if name in names
        ):
            found.add(candidate)
    return found


def outside_boundary(module: object) -> set[type]:
    """Types the census flags that are not inside the rendering boundary."""

    flagged = types_with_private_fields(module) | types_with_bytes_hints(module)
    return {
        candidate
        for candidate in flagged
        if not issubclass(candidate, PrivateRendering)
    }
