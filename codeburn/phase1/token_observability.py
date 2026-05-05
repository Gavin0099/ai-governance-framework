from __future__ import annotations

from collections.abc import Iterable, Mapping


def _row_value(row: Mapping[str, object], key: str) -> object:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def token_observability_level(rows: Iterable[Mapping[str, object]]) -> str:
    has_provider_tokens = False
    has_coarse_signal = False

    for row in rows:
        token_source = str(_row_value(row, "token_source") or "").strip()
        total_tokens = _row_value(row, "total_tokens")

        if token_source == "provider" and total_tokens is not None:
            has_provider_tokens = True
            break

        if token_source == "provider":
            has_coarse_signal = True
        elif token_source == "estimated" and total_tokens is not None:
            has_coarse_signal = True

    if has_provider_tokens:
        return "step_level"
    if has_coarse_signal:
        return "coarse"
    return "none"